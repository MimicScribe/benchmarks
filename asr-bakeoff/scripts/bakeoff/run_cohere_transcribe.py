#!/usr/bin/env python3
"""Cohere Transcribe bake-off runner.

Transcribes the repo's 27-file ASR benchmark corpus with
CohereLabs/cohere-transcribe-03-2026 (via the ungated mirror
evewashere/cohere-transcribe-03-2026-ungated, byte-identical files, because the
canonical repo is gate-restricted for this HF account) and writes hypotheses in
the repo's run-dir shape so scripts/score_corpus_wer.py and
scripts/score_number_fidelity.py read them directly.

Chunking: the model's own long-form scheme, straight out of the transformers
CohereAsrFeatureExtractor. Nominal chunk 35 s; the cut point is the quietest
1024-sample window inside the last 5 s of the nominal chunk (an energy search
band, NOT duplicated audio), so chunks are 30-35 s, contiguous and
non-overlapping. Stitching is therefore a plain join with a single space, which
is what CohereAsrProcessor._reassemble_chunk_texts does. Each chunk becomes one
output segment carrying its real audio bounds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from transformers import AutoProcessor, CohereAsrForConditionalGeneration

# Repo root, derived from this file's own location (scripts/bakeoff/<this>).
# It was an absolute path to the author's checkout until 2026-09-03.
REPO = Path(__file__).resolve().parents[2]
# Default corpus root. `scripts/bakeoff/fetch_corpus.py` fetches into the same
# place by default; --audio-root points at a different one.
AUDIO_ROOT = REPO / "benchmark" / "data"
MODEL_ID = "evewashere/cohere-transcribe-03-2026-ungated"
CANONICAL_ID = "CohereLabs/cohere-transcribe-03-2026"

EARNINGS21 = [
    "4320211", "4341191", "4346818", "4359971", "4365024", "4366522",
    "4366893", "4367535", "4383161", "4384964", "4387332",
]
AMI = [
    "EN2002a", "EN2002b", "EN2006b", "ES2002a", "ES2004c", "ES2008c",
    "ES2013b", "ES2016a", "IS1000a", "IS1003b", "IS1006c", "IS1009a",
    "IS1009b", "TS3005a", "TS3009c", "TS3012b",
]


def audio_path(file_id: str, audio_root: Path | str | None = None) -> Path:
    root = Path(audio_root) if audio_root is not None else AUDIO_ROOT
    if file_id in EARNINGS21:
        return root / "earnings21/audio" / f"{file_id}.wav"
    return root / "ami/audio" / f"{file_id}.wav"


def chunk_bounds(fe, waveform: torch.Tensor) -> list[tuple[int, int]]:
    """Sample (start, end) pairs, mirroring _split_audio_chunks_energy."""
    chunk_size = max(1, int(round(fe.max_audio_clip_s * fe.sampling_rate)))
    ctx = max(1, int(round(fe.overlap_chunk_second * fe.sampling_rate)))
    total = waveform.shape[0]
    if total <= chunk_size:
        return [(0, total)]
    out: list[tuple[int, int]] = []
    idx = 0
    while idx < total:
        if idx + chunk_size >= total:
            out.append((idx, total))
            break
        search_start = max(idx, idx + chunk_size - ctx)
        search_end = min(idx + chunk_size, total)
        if search_end <= search_start:
            split = idx + chunk_size
        else:
            split = fe._find_split_point_energy(waveform, search_start, search_end)
        split = max(idx + 1, min(split, total))
        out.append((idx, split))
        idx = split
    return [(s, e) for s, e in out if e > s]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "benchmark/output/bakeoff-cohere"))
    ap.add_argument("--audio-root", default=str(AUDIO_ROOT),
                    help="corpus root holding ami/audio and earnings21/audio "
                         f"(default: {AUDIO_ROOT})")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=448)
    ap.add_argument("--files", nargs="*", default=None)
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    out_root = Path(args.out)
    per_file = out_root / "per-file"
    per_file.mkdir(parents=True, exist_ok=True)

    file_ids = args.files if args.files else EARNINGS21 + AMI
    device = torch.device(args.device)
    dtype = getattr(torch, args.dtype)

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = CohereAsrForConditionalGeneration.from_pretrained(MODEL_ID, dtype=dtype)
    model.to(device)
    model.eval()
    load_s = time.time() - t0
    print(f"[load] {load_s:.1f}s device={device} dtype={dtype}", flush=True)

    fe = processor.feature_extractor
    manifest_path = out_root / "manifest.json"
    timings: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            timings = json.loads(manifest_path.read_text()).get("files", {})
        except Exception:
            timings = {}

    for file_id in file_ids:
        dest = per_file / f"{file_id}_after_orphan.json"
        if args.skip_existing and dest.exists():
            print(f"[skip] {file_id}", flush=True)
            continue
        wav = audio_path(file_id, args.audio_root)
        data, sr = sf.read(str(wav), dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        assert sr == 16000, f"{wav} is {sr} Hz, expected 16000"
        waveform = torch.from_numpy(data)
        duration_s = waveform.shape[0] / sr

        bounds = chunk_bounds(fe, waveform)
        segments = []
        t_file = time.time()
        for i in range(0, len(bounds), args.batch):
            group = bounds[i : i + args.batch]
            audios = [waveform[s:e] for s, e in group]
            inputs = processor(audios, sampling_rate=16000, return_tensors="pt", language="en")
            inputs.pop("audio_chunk_index", None)
            inputs = inputs.to(device)
            inputs["input_features"] = inputs["input_features"].to(dtype)
            with torch.inference_mode():
                outputs = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
            texts = processor.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            for (s, e), text in zip(group, texts):
                segments.append(
                    {
                        "startTime": round(s / sr, 3),
                        "endTime": round(e / sr, 3),
                        "text": text.strip(),
                    }
                )
            done = min(i + args.batch, len(bounds))
            el = time.time() - t_file
            covered = segments[-1]["endTime"]
            print(
                f"  [{file_id}] {done}/{len(bounds)} chunks  {el:.0f}s  rtf={covered / max(el, 1e-6):.2f}x",
                flush=True,
            )
        wall = time.time() - t_file
        dest.write_text(json.dumps({"segments": segments}, ensure_ascii=False, indent=1))
        timings[file_id] = {
            "wall_s": round(wall, 2),
            "audio_s": round(duration_s, 2),
            "rtf_x": round(duration_s / wall, 2),
            "chunks": len(bounds),
            "words": sum(len(s["text"].split()) for s in segments),
        }
        print(
            f"[done] {file_id} {duration_s:.0f}s audio in {wall:.0f}s "
            f"(RTFx {duration_s / wall:.2f}) {timings[file_id]['words']} words",
            flush=True,
        )
        manifest_path.write_text(
            json.dumps(
                {
                    "model_id": CANONICAL_ID,
                    "weights_source": MODEL_ID,
                    "weights_revision": "29b9036c65620e1a148127c6147543b52358da6a",
                    "canonical_revision": "b1eacc2686a3d08ceaae5f24a88b1d519620bc09",
                    "note": (
                        "canonical CohereLabs repo is gate-restricted for this HF account; "
                        "weights pulled from the ungated public mirror"
                    ),
                    "runtime": {
                        "python": sys.version.split()[0],
                        "transformers": __import__("transformers").__version__,
                        "torch": torch.__version__,
                        "device": str(device),
                        "dtype": str(dtype),
                        "batch_chunks": args.batch,
                        "max_new_tokens": args.max_new_tokens,
                        "load_s": round(load_s, 1),
                    },
                    "chunking": {
                        "scheme": "CohereAsrFeatureExtractor energy-boundary split (model's own long-form path)",
                        "max_audio_clip_s": fe.max_audio_clip_s,
                        "overlap_chunk_second": fe.overlap_chunk_second,
                        "overlap_is_real_audio_overlap": False,
                        "overlap_meaning": (
                            "search band: the cut is the quietest 1024-sample window in the last 5 s "
                            "of the nominal 35 s chunk, so chunks are contiguous and non-overlapping"
                        ),
                        "stitch": "join chunk texts with a single space (processor._reassemble_chunk_texts)",
                        "decoder_prompt": "<|en|><|en|><|pnc|><|noitn|><|notimestamp|><|nodiarize|>",
                    },
                    "files": timings,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.exit(main())
