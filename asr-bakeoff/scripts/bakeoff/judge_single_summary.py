#!/usr/bin/env python3
"""judge_single_summary.py -- the published judge tables for ONE judge run.

`judge_agreement.py` needs two runs. A section that is graded by a single judge
(the Nemotron section: one judge, four arms, no second vendor) still needs the
same anchor check and the same per-window means, and this runs them through the
same functions: drop every window where any arm's excerpt is not the same
stretch of the meeting (`--max-anchor-wer`), then per-arm means over unique
windows (a repeated window is averaged first), wrong-figure EVENT counts, the
judge's agreement with itself on the repeated windows, and the mean grade each
prompt position attracts.

Usage: python3 scripts/bakeoff/judge_single_summary.py <grades.jsonl> [--max-anchor-wer 1.0]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_agreement as J  # noqa: E402


def fmt(v):
    return "-" if v is None else f"{v:.2f}"


def table(rows, corpus=None):
    means = J.arm_means(rows, corpus)
    ev = J.figure_events(rows if corpus is None else [r for r in rows if r.get("corpus") == corpus])
    print("| arm | windows | wrong figures (events) | wrong names / terms | dropped | added | readability |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for arm, m in means.items():
        print(f"| {arm} | {m['n']} | {ev[arm]['events']} | {fmt(m['wrong_names_terms'])} | "
              f"{fmt(m['dropped_content'])} | {fmt(m['added_content'])} | {fmt(m['readability'])} |")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("grades", type=Path)
    ap.add_argument("--max-anchor-wer", type=float, default=1.0)
    a = ap.parse_args()
    rows = J.load(a.grades)
    bad = J.unanchored_windows(rows, a.max_anchor_wer)
    all_w = {r["window_id"] for r in rows}
    fails = [r for r in rows if r.get("parse_error")]
    print(f"windows graded {len(all_w)}, calls {len(rows)}, parse failures {len(fails)}, "
          f"unanchored windows dropped {len(bad)}")
    unanch = {}
    for r in rows:
        for arm, loc in (r.get("local") or {}).items():
            w = loc.get("content_word_wer")
            if isinstance(w, (int, float)) and w > a.max_anchor_wer:
                unanch.setdefault(arm, set()).add(r["window_id"])
    print("unanchored windows by arm:", {k: len(v) for k, v in sorted(unanch.items())})
    kept = J.drop_windows([r for r in rows if not r.get("parse_error")], bad)
    print(f"kept windows {len({r['window_id'] for r in kept})}, calls {len(kept)}\n")
    print("### all kept windows\n")
    table(kept)
    for c in ("ami", "earnings21"):
        print(f"\n### {c}\n")
        table(kept, c)
    print("\n### self-consistency on repeated windows\n")
    for f, v in J.self_consistency(kept).items():
        print(f"{f}: pairs {v['n_pairs']} exact {fmt(v['exact_match'])} kappa {fmt(v['kappa'])}")
    print("\n### mean grade by prompt position\n")
    for f, cell in J.position_effect(kept).items():
        print(f"{f}: " + " / ".join(f"{L} {fmt(c['mean'])}" for L, c in sorted(cell.items())))
    print("\n### position balance\n", json.dumps(J.position_balance(kept)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
