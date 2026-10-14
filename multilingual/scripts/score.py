#!/usr/bin/env python3
"""Score the published app transcripts against FLEURS references (paired, two models).

Usage:
  python3 scripts/fetch_fleurs.py --langs <25 configs> --minutes 10 --min-utterances 60 --seed 1337
  python3 scripts/score.py [--no-digit-refs]

Reads data/<lang>/manifest.jsonl (written by fetch_fleurs.py) and
results/transcripts_{released,next}.jsonl. Both sides: lowercase, every
non-alphanumeric character becomes a space; a decoder `<unk>` becomes "ς"
(Greek final sigma, the one letter the model's vocabulary lacks).
--no-digit-refs keeps only sentences whose reference has no digit (the
number-neutral basis). Change = next - released, 95% paired bootstrap.
Requires: jiwer.
"""

import json
import random
import sys
from pathlib import Path

import jiwer

SUITE = Path(__file__).resolve().parents[1]
ARMS = ("released", "next")


def norm(t: str) -> list[str]:
    t = t.replace("<unk>", "ς").lower()
    return "".join(c if (c.isalnum() or c.isspace()) else " " for c in t).split()


def main() -> None:
    no_digits = "--no-digit-refs" in sys.argv
    hyp = {a: {} for a in ARMS}
    for a in ARMS:
        for line in open(SUITE / "results" / f"transcripts_{a}.jsonl", encoding="utf-8"):
            r = json.loads(line)
            hyp[a][r["id"]] = r["text"]
    means = {a: [] for a in ARMS}
    print(f"{'lang':8}{'n':>5}{'released':>10}{'next':>8}{'change':>9}   95% CI")
    for d in sorted(p for p in (SUITE / "data").iterdir() if (p / "manifest.jsonl").exists()):
        rows = []
        for line in open(d / "manifest.jsonl", encoding="utf-8"):
            m = json.loads(line)
            if no_digits and any(c.isdigit() for c in m["raw_transcription"]):
                continue
            ref = norm(m["transcription"])
            if not ref or any(m["id"] not in hyp[a] for a in ARMS):
                continue
            errs = []
            for a in ARMS:
                o = jiwer.process_words(" ".join(ref), " ".join(norm(hyp[a][m["id"]])) or "x")
                errs.append(o.substitutions + o.deletions + o.insertions)
            rows.append((len(ref), errs))
        if not rows:
            continue

        def wer(rs, i):
            return 100 * sum(r[1][i] for r in rs) / sum(r[0] for r in rs)

        rnd = random.Random(1)
        boot = sorted(wer(s, 1) - wer(s, 0) for s in ([rnd.choice(rows) for _ in rows] for _ in range(2000)))
        w = [wer(rows, i) for i in range(2)]
        for i, a in enumerate(ARMS):
            means[a].append(w[i])
        print(f"{d.name:8}{len(rows):>5}{w[0]:>10.2f}{w[1]:>8.2f}{w[1] - w[0]:>+9.2f}   [{boot[50]:+.2f}, {boot[1949]:+.2f}]")
    for a in ARMS:
        print(f"mean WER {a}: {sum(means[a]) / len(means[a]):.2f}% over {len(means[a])} languages")


if __name__ == "__main__":
    main()
