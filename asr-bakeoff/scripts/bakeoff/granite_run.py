#!/usr/bin/env python3
"""granite_run.py - IBM Granite Speech over the 27-file ASR bake-off corpus.

Writes hypotheses in the repo's run-dir shape so scripts/score_corpus_wer.py and
scripts/score_number_fidelity.py read them without adaptation:

    <out>/per-file/<id>_after_orphan.json  = {"segments": [{startTime, endTime, text}]}
    <out>/manifest.json                    = provenance + timing + chunking

Text written is RAW model output (the scorers normalize and ITN both sides).

Chunking: Granite's card states the model "works well with audio segments up to
9 minutes long for ASR". We cut fixed windows of --chunk seconds that OVERLAP by
--overlap seconds, decode each independently, and stitch by deleting the leading
words of chunk i+1 that the seam window shows were already emitted at the tail of
chunk i. See `dedup_seam` for the rule and for the two defects that shaped it.
When the two decodes share no 2-gram inside the plausible overlap region the
chunk is kept WHOLE and the seam is recorded as "no-overlap" in the manifest,
because a seam that falls in silence has nothing to dedupe and a proportional
drop there deletes real speech.

Every chunk's raw decode is also written to <out>/raw-chunks/, so a change to the
seam rule can be re-derived by scripts/bakeoff/granite_restitch.py with no GPU.

NOT COMMITTED. Bake-off scratch tool.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

SR = 16000
MIN_BLOCK = 3          # words; shortest common block trusted as a real seam match
SEAM_SLACK = 1.8       # seam search window = overlap * SEAM_SLACK seconds of words
WORDS_PER_SEC = 3.2    # rough English speech rate, used only to size seam windows

ASR_PROMPT = "<|audio|>transcribe the speech with proper punctuation and capitalization."
_NORM = re.compile(r"[^a-z0-9']+")


def norm_words(text: str) -> list[str]:
    return [w for w in _NORM.sub(" ", text.lower()).split() if w]


def dedup_seam(prev_text: str, new_text: str, overlap_s: float, chunk_s: float):
    """Drop the head of new_text already present at the tail of prev_text.

    Returns (kept_text, seam_kind, n_dropped)."""
    prev_w = prev_text.split()
    new_w = new_text.split()
    if not prev_w or not new_w:
        return new_text, "empty", 0

    win = max(12, int(overlap_s * WORDS_PER_SEC * SEAM_SLACK))
    tail = prev_w[-win:]
    head = new_w[: win * 2]
    tail_n = norm_words(" ".join(tail))
    head_n = norm_words(" ".join(head))
    # normalization can merge/drop tokens; keep an index map from normalized
    # position back to raw-word position for the head side.
    head_map = []
    for i, w in enumerate(head):
        for _ in norm_words(w) or [None]:
            head_map.append(i)
    head_map = head_map[: len(head_n)]

    # How many words of THIS chunk can plausibly be re-decoded overlap, from the
    # chunk's own measured speech rate rather than a global constant. A silent
    # channel gets a small budget and a dense one a large one.
    expect = len(new_w) * (overlap_s / chunk_s)
    max_cut = int(round(2 * expect)) + 5

    sm = difflib.SequenceMatcher(None, tail_n, head_n, autojunk=False)
    ops = sm.get_opcodes()
    # Anchor on the LAST equal run of >= MIN_BLOCK words that STARTS inside the
    # plausible overlap region. Both halves are load-bearing:
    #   - shorter than MIN_BLOCK is a stopword coincidence, and difflib will
    #     happily pair three scattered "the"s across the whole window;
    #   - a run starting past `max_cut` is a phrase the speaker repeated LATER
    #     in the chunk, not the seam. On a sparse mic channel that cost 44 real
    #     words in one seam: chunk i ended "...decision is cover pro, good" and
    #     chunk i+1 said "the template is cover pro not form flow" 44 words in,
    #     so the cut landed there and deleted everything before it.
    anchors = [(a1, a2, b1, b2) for tag, a1, a2, b1, b2 in ops
               if tag == "equal" and (a2 - a1) >= MIN_BLOCK and b1 <= max_cut]
    if not anchors:
        # Weaker evidence, same positional guard: a 2-word run inside the
        # overlap region still beats guessing.
        anchors = [(a1, a2, b1, b2) for tag, a1, a2, b1, b2 in ops
                   if tag == "equal" and (a2 - a1) >= 2 and b1 <= max_cut]
    if anchors:
        a1, a2, b1, b2 = anchors[-1]
        # Cut where the END of the previous tail lands, carrying the unmatched
        # tail remainder across 1:1 — a numeral or filler the two decodes spelled
        # differently sits after the anchor and would otherwise survive as a
        # duplicate ("twelve percent" + "12 percent"). Never trust difflib's own
        # trailing `replace`: it can pair 3 leftover tail words against 30 head
        # words and swallow the whole chunk.
        cut_norm = b2 + (len(tail_n) - a2)
        cut_norm = max(0, min(cut_norm, len(head_n), win, max_cut))
        cut_raw = head_map[cut_norm - 1] + 1 if 0 < cut_norm <= len(head_map) else 0
        return " ".join(new_w[cut_raw:]), "matched", cut_raw

    # No shared 2-gram anywhere in the overlap region. The two decodes are then
    # most likely NOT covering the same speech (a seam that falls in silence),
    # so dropping a proportional slice would delete rather than dedupe. Keep the
    # chunk whole and let the seam be counted as it falls.
    return new_text, "no-overlap", 0


def plan_chunks(total_s: float, chunk_s: float, overlap_s: float):
    spans, start = [], 0.0
    step = chunk_s - overlap_s
    while start < total_s:
        end = min(start + chunk_s, total_s)
        spans.append((start, end))
        if end >= total_s - 0.05:
            break
        start += step
    return spans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ibm-granite/granite-speech-4.1-2b")
    ap.add_argument("--out", required=True)
    ap.add_argument("--files", nargs="+", required=True,
                    help="wav paths; stem is the run-dir file id")
    ap.add_argument("--out-names", nargs="+", default=None,
                    help="output basename per --files entry (golden-pair layout)")
    ap.add_argument("--subdir", default="per-file",
                    help="subdirectory under --out for the hypothesis JSONs")
    ap.add_argument("--suffix", default="_after_orphan",
                    help="basename suffix before .json")
    ap.add_argument("--chunk", type=float, default=480.0)
    ap.add_argument("--overlap", type=float, default=15.0)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--batch", type=int, default=1,
                    help="chunks decoded per generate() call")
    ap.add_argument("--tokens-per-sec", type=float, default=6.0,
                    help="max_new_tokens budget per second of chunk audio")
    ap.add_argument("--budget-hours", type=float, default=0.0,
                    help="stop before starting a file once elapsed exceeds this")
    a = ap.parse_args()

    out = Path(a.out)
    (out / a.subdir).mkdir(parents=True, exist_ok=True)
    if a.out_names and len(a.out_names) != len(a.files):
        raise SystemExit("--out-names must have one entry per --files entry")
    name_of = dict(zip(a.files, a.out_names)) if a.out_names else {}
    manifest_path = out / "manifest.json"

    t_load = time.time()
    proc = AutoProcessor.from_pretrained(a.model)
    tok = proc.tokenizer
    model = AutoModelForSpeechSeq2Seq.from_pretrained(a.model, dtype=getattr(torch, a.dtype))
    model.to(a.device)
    model.eval()
    load_s = time.time() - t_load
    print(f"[granite] model loaded in {load_s:.1f}s on {a.device}/{a.dtype}", flush=True)

    prompt = tok.apply_chat_template([{"role": "user", "content": ASR_PROMPT}],
                                     tokenize=False, add_generation_prompt=True)

    manifest = {
        "model_id": a.model,
        "revision": None,
        "runtime": {
            "framework": "transformers",
            "transformers": __import__("transformers").__version__,
            "torch": torch.__version__,
            "device": a.device,
            "dtype": a.dtype,
            "decoding": "greedy (do_sample=False, num_beams=1)",
            "prompt": ASR_PROMPT,
            "model_load_seconds": round(load_s, 1),
        },
        "chunking": {
            "chunk_seconds": a.chunk,
            "overlap_seconds": a.overlap,
            "stitch": "difflib alignment over case/punctuation-normalized words in the seam window; anchor = LAST equal run of >=3 (else >=2) words STARTING within 2x the chunk's own expected overlap words + 5; cut at where the previous tail's END aligns, clamped to that same bound; no qualifying anchor => chunk kept whole (seam kind `no-overlap`), never a proportional drop",
            "max_new_tokens_per_chunk_second": a.tokens_per_sec,
            "batch": a.batch,
        },
        "files": {},
        "stopped_early": False,
    }
    try:
        from huggingface_hub import HfApi
        manifest["revision"] = HfApi().model_info(a.model).sha
    except Exception as exc:  # offline / rate limited
        manifest["revision"] = f"unresolved: {exc.__class__.__name__}"

    def flush():
        manifest_path.write_text(json.dumps(manifest, indent=2))

    flush()
    t_run = time.time()

    for wav_path in a.files:
        fid = name_of.get(wav_path, Path(wav_path).stem)
        if a.budget_hours and (time.time() - t_run) / 3600.0 > a.budget_hours:
            print(f"[granite] budget {a.budget_hours}h exhausted before {fid}; stopping", flush=True)
            manifest["stopped_early"] = True
            flush()
            break

        info = sf.info(wav_path)
        assert info.samplerate == SR, f"{wav_path} is {info.samplerate} Hz, expected {SR}"
        total_s = info.frames / info.samplerate
        spans = plan_chunks(total_s, a.chunk, a.overlap)

        t_file = time.time()
        # Decode chunks in batches. Only EQUAL-duration chunks share a batch, so
        # every sample in a batch has the same audio-embedding count and the
        # tokenizer never has to pad the prompt; the short final chunk of a file
        # therefore runs alone.
        raws: list[str] = [""] * len(spans)
        caps: list[bool] = [False] * len(spans)
        groups: list[list[int]] = []
        for ci in range(len(spans)):
            dur = round(spans[ci][1] - spans[ci][0], 3)
            if (groups and len(groups[-1]) < a.batch
                    and round(spans[groups[-1][0]][1] - spans[groups[-1][0]][0], 3) == dur):
                groups[-1].append(ci)
            else:
                groups.append([ci])

        done = 0
        for grp in groups:
            wavs = []
            for ci in grp:
                s, e = spans[ci]
                data, _ = sf.read(wav_path, start=int(s * SR), frames=int((e - s) * SR),
                                  dtype="float32", always_2d=True)
                wavs.append(torch.from_numpy(np.ascontiguousarray(data[:, 0])[None, :]))
            bs = len(grp)
            if bs == 1:
                inputs = proc(prompt, wavs[0], device=a.device, return_tensors="pt").to(a.device)
            else:
                inputs = proc([prompt] * bs, wavs, device=a.device, return_tensors="pt").to(a.device)
            dur = spans[grp[0]][1] - spans[grp[0]][0]
            budget = int(dur * a.tokens_per_sec)
            with torch.inference_mode():
                gen = model.generate(**inputs, max_new_tokens=budget,
                                     do_sample=False, num_beams=1)
            n_in = inputs["input_ids"].shape[-1]
            texts = tok.batch_decode(gen[:, n_in:], add_special_tokens=False,
                                     skip_special_tokens=True)
            for k, ci in enumerate(grp):
                raws[ci] = texts[k].strip()
                caps[ci] = int((gen[k, n_in:] != tok.pad_token_id).sum().item()) >= budget - 1
            done += bs
            print(f"[granite] {fid} {done}/{len(spans)} chunks "
                  f"[{spans[grp[0]][0]:.0f}-{spans[grp[-1]][1]:.0f}s] bs={bs} "
                  f"({time.time()-t_file:.0f}s elapsed)", flush=True)

        segments, seam_kinds = [], []
        prev_text = ""
        for ci, (s, e) in enumerate(spans):
            raw = raws[ci]
            if ci == 0:
                kept, kind, dropped = raw, "first", 0
            else:
                kept, kind, dropped = dedup_seam(prev_text, raw, a.overlap, a.chunk)
            seam_kinds.append(kind)
            seg_start = s if ci == 0 else s + a.overlap
            segments.append({"startTime": round(seg_start, 3),
                             "endTime": round(e, 3),
                             "text": kept})
            prev_text = raw
            if caps[ci]:
                print(f"[granite] {fid} chunk {ci} HIT max_new_tokens", flush=True)

        wall = time.time() - t_file
        (out / a.subdir / f"{fid}{a.suffix}.json").write_text(
            json.dumps({"segments": segments}, indent=2))
        # raw, unstitched chunk decodes: lets the seam rule be re-derived
        # offline. Kept OUT of per-file/ so the scorers' glob cannot see it.
        (out / "raw-chunks").mkdir(parents=True, exist_ok=True)
        (out / "raw-chunks" / f"{fid}_chunks.json").write_text(json.dumps(
            {"chunk_seconds": a.chunk, "overlap_seconds": a.overlap,
             "spans": [[round(x, 3), round(y, 3)] for x, y in spans],
             "raw": raws}, indent=2))
        words = sum(len(sg["text"].split()) for sg in segments)
        manifest["files"][fid] = {
            "audio_seconds": round(total_s, 2),
            "wall_seconds": round(wall, 1),
            "rtf": round(wall / total_s, 4),
            "chunks": len(spans),
            "words": words,
            "seams": seam_kinds[1:],
        }
        flush()
        print(f"[granite] === {fid}: {total_s:.0f}s audio in {wall:.0f}s "
              f"RTF={wall/total_s:.3f} words={words} "
              f"(run {(time.time()-t_run)/60:.0f} min) ===", flush=True)

    manifest["total_wall_seconds"] = round(time.time() - t_run, 1)
    flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
