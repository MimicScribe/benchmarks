#!/usr/bin/env python3
"""itn_normalize_arm.py -- step 6b of the report's Reproducing section, as a command.

Puts every row of one arm through the same persisted-row normalizer the saved
transcript goes through (`mimicscribe --itn-text`, via score_corpus_wer.itn_lines),
line for line, and writes the arm back out in the same JSON shape, so the number
scorer and the blind judge read every arm on one basis. Row times are untouched.

Needs MIMICSCRIBE_ITN_NUMBERS=1 and a mimicscribe binary (MIMICSCRIBE_BIN).

Usage: python3 scripts/bakeoff/itn_normalize_arm.py <arm dir> <out dir>
       (reads <arm dir>/per-file/<id>_after_orphan.json, writes the same names)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import score_corpus_wer as S  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]) / "per-file", Path(sys.argv[2]) / "per-file"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(src.glob("*_after_orphan.json")):
        d = json.loads(p.read_text())
        key = "segments" if "segments" in d else "sentences"
        rows = d[key]
        texts = S.itn_lines([r.get("text") or "" for r in rows])
        for r, t in zip(rows, texts):
            r["text"] = t
        (dst / p.name).write_text(json.dumps(d, indent=1))
        n += 1
    print(f"{n} files normalized: {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
