#!/usr/bin/env python3
"""cohere_repeat_probe.py - do the degenerate looping chunks break under
repetition control?

Loads the Cohere Transcribe model once, finds the looping chunks in the existing
run output (dominant token repeated >40x in a single segment), re-decodes just
those audio windows under three settings, and prints the token/word counts so we
can see whether the loop is a decode-setting artifact or the model's real
behavior on that audio.

Read-only: it writes nothing, it only prints.

Every path is an argument. The values used for the published run were:

    --run-dir    <repo>/benchmark/output/bakeoff-cohere
    --audio-root <repo>/benchmark/data          (the default)

so the published invocation is

    python3 scripts/bakeoff/cohere_repeat_probe.py \\
        --run-dir benchmark/output/bakeoff-cohere

Until 2026-09-03 this script took no arguments and carried an absolute path to
the author's checkout.
"""
from __future__ import annotations

import argparse
import json
import os
import glob
import sys
from collections import Counter
from pathlib import Path

import soundfile as sf
import torch
from transformers import AutoProcessor, CohereAsrForConditionalGeneration

# Repo root, derived from this file's own location (scripts/bakeoff/<this>).
REPO = Path(__file__).resolve().parents[2]
AUDIO_ROOT = REPO / "benchmark" / "data"
MODEL_ID = "evewashere/cohere-transcribe-03-2026-ungated"


def audio_path(fid: str, audio_root: Path | str | None = None) -> Path:
    root = Path(audio_root) if audio_root is not None else AUDIO_ROOT
    if fid.startswith(("EN", "ES", "IS", "TS")):
        return root / "ami/audio" / f"{fid}.wav"
    return root / "earnings21/audio" / f"{fid}.wav"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True,
                    help="the Cohere run directory to scan for looping chunks "
                         "(published run: benchmark/output/bakeoff-cohere)")
    ap.add_argument("--audio-root", default=str(AUDIO_ROOT),
                    help="corpus root holding ami/audio and earnings21/audio "
                         f"(default: {AUDIO_ROOT})")
    ap.add_argument("--model", default=MODEL_ID,
                    help=f"HF model id (default: {MODEL_ID})")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--max-new-tokens", type=int, default=448)
    args = ap.parse_args()

    run = Path(args.run_dir) / "per-file"

    # find looping chunks from existing output
    loops = []
    for f in sorted(glob.glob(str(run / "*_after_orphan.json"))):
        fid = Path(f).name[: -len("_after_orphan.json")]
        d = json.load(open(f))
        for s in d["segments"]:
            toks = s["text"].split()
            if len(toks) < 40:
                continue
            c = Counter(toks)
            top, cnt = c.most_common(1)[0]
            if cnt > 40:
                loops.append((fid, s["startTime"], s["endTime"], s["text"], top, cnt))

    processor = AutoProcessor.from_pretrained(args.model)
    model = CohereAsrForConditionalGeneration.from_pretrained(args.model, dtype=torch.float16)
    model.to(args.device)
    model.eval()

    for fid, s, e, orig, top, cnt in loops:
        wav = audio_path(fid, args.audio_root)
        data, sr = sf.read(str(wav), dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        a = data[int(s * sr):int(e * sr)]
        wf = torch.from_numpy(a).to(torch.float32)

        print(f"=== {fid} [{s:.1f}-{e:.1f}s] orig {len(orig.split())} words, "
              f"dominant '{top}' x{cnt} ===")
        for label, kw in [
            ("greedy (baseline)", {}),
            ("no_repeat_ngram_size=3", {"no_repeat_ngram_size": 3}),
            ("rep_penalty=1.2", {"repetition_penalty": 1.2}),
        ]:
            inputs = processor([wf], sampling_rate=16000, return_tensors="pt", language="en")
            inputs.pop("audio_chunk_index", None)
            inputs = inputs.to(args.device)
            inputs["input_features"] = inputs["input_features"].to(torch.float16)
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, **kw)
            text = processor.tokenizer.batch_decode(out, skip_special_tokens=True)[0].strip()
            toks = text.split()
            c = Counter(toks)
            top2, cnt2 = (c.most_common(1)[0] if c else ("(empty)", 0))
            print(f"  {label:<26} {len(toks):>4} words  top '{top2}' x{cnt2}")
            print(f"      {text[:90]}")


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.exit(main())
