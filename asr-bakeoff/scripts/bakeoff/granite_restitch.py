#!/usr/bin/env python3
"""granite_restitch.py - re-run the seam stitcher over saved raw chunk decodes.

`granite_run.py` persists every chunk's RAW model text under <out>/raw-chunks/,
so a change to `dedup_seam` can be re-derived without touching the GPU. Writes
the hypothesis JSONs in place (or to --dest) and prints the per-file word delta.

NOT COMMITTED. Bake-off scratch tool.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "granite_run", Path(__file__).resolve().parent / "granite_run.py")
_gr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path, help="bake-off run dir")
    ap.add_argument("--subdir", default="pairs")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--dest", type=Path, default=None)
    a = ap.parse_args()

    dest = a.dest or (a.run / a.subdir)
    dest.mkdir(parents=True, exist_ok=True)
    kinds: Counter[str] = Counter()
    for cf in sorted((a.run / "raw-chunks").glob("*_chunks.json")):
        fid = cf.name[: -len("_chunks.json")]
        d = json.loads(cf.read_text())
        spans, raws = d["spans"], d["raw"]
        overlap, chunk = d["overlap_seconds"], d["chunk_seconds"]
        segments, prev = [], ""
        for ci, ((s, e), raw) in enumerate(zip(spans, raws)):
            if ci == 0:
                kept, kind = raw, "first"
            else:
                kept, kind, _ = _gr.dedup_seam(prev, raw, overlap, chunk)
            kinds[kind] += 1
            segments.append({"startTime": round(s if ci == 0 else s + overlap, 3),
                             "endTime": round(e, 3), "text": kept})
            prev = raw
        out = dest / f"{fid}{a.suffix}.json"
        before = 0
        if out.exists():
            before = sum(len(x["text"].split())
                         for x in json.loads(out.read_text())["segments"])
        after = sum(len(x["text"].split()) for x in segments)
        out.write_text(json.dumps({"segments": segments}, indent=2))
        print(f"{fid}: {before} -> {after} words  (raw {sum(len(r.split()) for r in raws)})")
    print("seam kinds:", dict(kinds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
