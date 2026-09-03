#!/usr/bin/env python3
"""Re-decode ONLY the 6 corpus chunks that hit max_new_tokens, with
no_repeat_ngram_size=5, and write a corrected copy of the whole bake-off run.
Every other chunk is copied byte-for-byte, so the delta is attributable.

Every path is an argument. The values used for the published run were:

    --run-dir   <repo>/benchmark/output/bakeoff-cohere
    --out       <repo>/benchmark/output/audit-cohere-loopfix
    --audio-root <repo>/benchmark/data          (the default)

so the published invocation is

    python3 scripts/bakeoff/cohere_patch_loops.py \\
        --run-dir benchmark/output/bakeoff-cohere \\
        --out benchmark/output/audit-cohere-loopfix

The runner it reuses (`run_cohere_transcribe.py`, for `audio_path` and
`chunk_bounds`) is imported from THIS script's own directory; until 2026-09-03
it was loaded from an absolute worktree path that no longer exists.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import soundfile as sf
import torch
from transformers import AutoProcessor, CohereAsrForConditionalGeneration

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_cohere_transcribe as rct  # noqa: E402

# The six chunks that ran into max_new_tokens in the published run.
TARGETS = [("EN2002b", 54), ("EN2006b", 47), ("ES2004c", 21),
           ("IS1006c", 15), ("IS1006c", 46), ("TS3009c", 63)]

M = "evewashere/cohere-transcribe-03-2026-ungated"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True,
                    help="the Cohere run directory to patch, read-only "
                         "(published run: benchmark/output/bakeoff-cohere)")
    ap.add_argument("--out", required=True,
                    help="destination for the corrected copy; REPLACED if it "
                         "exists (published run: "
                         "benchmark/output/audit-cohere-loopfix)")
    ap.add_argument("--audio-root", default=str(rct.AUDIO_ROOT),
                    help="corpus root holding ami/audio and earnings21/audio "
                         f"(default: {rct.AUDIO_ROOT})")
    ap.add_argument("--model", default=M, help=f"HF model id (default: {M})")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--max-new-tokens", type=int, default=448)
    ap.add_argument("--no-repeat-ngram-size", type=int, default=5)
    args = ap.parse_args()

    src = Path(args.run_dir)
    dst = Path(args.out)

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    proc = AutoProcessor.from_pretrained(args.model)
    model = CohereAsrForConditionalGeneration.from_pretrained(
        args.model, dtype=torch.float16).to(args.device).eval()
    fe = proc.feature_extractor
    by_file = {}
    for fid, ci in TARGETS:
        by_file.setdefault(fid, []).append(ci)

    for fid, cis in by_file.items():
        d, sr = sf.read(str(rct.audio_path(fid, args.audio_root)), dtype="float32")
        wav = torch.from_numpy(d)
        bounds = rct.chunk_bounds(fe, wav)
        p = dst / "per-file" / f"{fid}_after_orphan.json"
        obj = json.loads(p.read_text())
        assert len(obj["segments"]) == len(bounds), (fid, len(obj["segments"]), len(bounds))
        for ci in cis:
            s, e = bounds[ci]
            inp = proc([wav[s:e]], sampling_rate=16000, return_tensors="pt", language="en")
            inp.pop("audio_chunk_index", None)
            inp = inp.to(args.device)
            inp["input_features"] = inp["input_features"].to(torch.float16)
            with torch.inference_mode():
                out = model.generate(**inp, max_new_tokens=args.max_new_tokens,
                                     no_repeat_ngram_size=args.no_repeat_ngram_size)
            txt = proc.tokenizer.batch_decode(out, skip_special_tokens=True)[0].strip()
            before = len(obj["segments"][ci]["text"].split())
            obj["segments"][ci]["text"] = txt
            print(f"{fid} chunk{ci}: {before} -> {len(txt.split())} words", flush=True)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    print("PATCHED", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
