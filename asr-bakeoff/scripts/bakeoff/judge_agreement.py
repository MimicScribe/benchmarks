#!/usr/bin/env python3
"""judge_agreement.py — compare two blind-judge runs over the SAME windows.

WHAT THIS ANSWERS
-----------------
The bake-off's rubric grades come from one LLM judge, so a reader cannot tell
a property of the transcripts from a property of that judge. Running a second,
different-vendor judge over byte-identical prompts (`judge_transcripts.py
--windows-from`) makes the judge's own contribution visible: where the two
agree, the number is about the ASR arms; where they disagree, it is about the
judge.

INPUTS are two `grades.jsonl` files from `judge_transcripts.py`. Rows are
paired on (window_id, pass) — a replay run reproduces both — and cells on
(window_id, pass, arm). A cell missing from either side is dropped from the
paired statistics and counted, never imputed.

WHAT IT REPORTS
---------------
* Per-arm and per-corpus means of every criterion, for run B (run A's are
  re-derived the same way so the two tables are computed by one code path).
* Self-consistency of run B on the repeated windows (pass 1 vs pass 2).
* Parse failures in run B (rows whose body was not valid JSON — see
  `judge_transcripts.call_openrouter_judge`).
* AGREEMENT: per-criterion Spearman of the per-cell scores between the two
  judges, exact-match rate, mean absolute difference, and — separately —
  whether the two judges put the ARMS in the same order on that criterion.
  Those are different questions: judges can rank the arms identically while
  correlating weakly cell by cell, and a cell-level correlation says nothing
  about the ordering a reader takes away.

A per-criterion Spearman is computed only when BOTH sides vary; a criterion
that is nearly all zeros (wrong_figures on conversational AMI) yields a
degenerate or unstable rho and is reported with its n so the reader can
discount it.

Usage
  python3 scripts/bakeoff/judge_agreement.py \\
      --run-a <gemini grades.jsonl> --label-a gemini-3.1-flash-lite \\
      --run-b <openrouter grades.jsonl> --label-b anthropic/claude-haiku-4.5 \\
      --out benchmark/results/asr-bakeoff/judge_second_model.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Optional

CRITERIA = ("wrong_figures", "wrong_names_terms", "dropped_content", "added_content")
ALL_FIELDS = CRITERIA + ("readability",)


def load(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        sys.exit(f"{path}: no rows")
    return rows


def _mean(xs: list[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def spearman(xs: list[float], ys: list[float]) -> Optional[float]:
    """Rank correlation with average ranks for ties (the criteria are small
    integers, so ties dominate and a naive rank would be wrong)."""
    n = len(xs)
    if n < 2:
        return None

    def ranks(vals: list[float]) -> list[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def arm_means(rows: list[dict], corpus: Optional[str] = None,
              per_window: bool = True) -> dict[str, dict]:
    """arm -> {n, <criterion>: mean, readability: mean}.

    PRIMARY basis is per UNIQUE WINDOW: a window graded twice is averaged
    first, then the windows are averaged. Over 92 calls the 12 repeated
    windows counted twice, which is enough to move an ordering — Gemini
    run 3 read Cohere's added content 0.424 against the pipeline's 0.435
    per call and 0.481 against 0.444 per window. `per_window=False` gives
    the old per-call basis, kept as a secondary field.
    """
    out: dict[str, dict] = {}
    subset = [r for r in rows if corpus is None or r.get("corpus") == corpus]
    arms = sorted({a for r in subset for a in (r.get("grades") or {})})
    for arm in arms:
        if per_window:
            by_w: dict[str, list[dict]] = {}
            for r in subset:
                if arm in (r.get("grades") or {}):
                    by_w.setdefault(r["window_id"], []).append(r["grades"][arm])
            groups = list(by_w.values())
        else:
            groups = [[r["grades"][arm]] for r in subset if arm in (r.get("grades") or {})]
        rec: dict = {"n": len(groups)}
        for f in ALL_FIELDS:
            per_group = [_mean([v[f] for v in g if isinstance(v.get(f), (int, float))])
                         for g in groups]
            rec[f] = _mean([x for x in per_group if x is not None])
        out[arm] = rec
    return out


def cohens_kappa(xs: list[float], ys: list[float]) -> Optional[float]:
    """Chance-corrected agreement between two integer-valued raters, treating
    the values as nominal categories.

    Needed because most of these criteria are ALMOST ALWAYS ZERO: a
    wrong-figures column that reads 0 on 90% of cells agrees with itself
    ~88% of the time by chance alone, so a raw exact-match rate flatters it
    and is not comparable across criteria. Returns None when one rater is
    constant (kappa is undefined there) — reported as such rather than as
    perfect or zero agreement.
    """
    n = len(xs)
    if n == 0:
        return None
    cats = sorted(set(xs) | set(ys))
    if len(cats) < 2:
        return None
    po = sum(1 for x, y in zip(xs, ys) if x == y) / n
    pe = sum((xs.count(c) / n) * (ys.count(c) / n) for c in cats)
    if pe >= 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def figure_events(rows: list[dict]) -> dict[str, dict]:
    """Per arm: how many CELLS carried a non-zero wrong-figures count and how
    many wrong figures that is in total.

    The wrong-figures column is 10-17 events per arm over the whole run. A
    mean of 0.11 against 0.15 is a difference of a handful of events on
    conversational audio that mostly contains no figures at all, so the
    column is published as counts and no ordering is claimed from it.
    """
    out: dict[str, dict] = {}
    arms = sorted({a for r in rows for a in (r.get("grades") or {})})
    for arm in arms:
        vals = [r["grades"][arm].get("wrong_figures") for r in rows
                if arm in (r.get("grades") or {})]
        vals = [v for v in vals if isinstance(v, (int, float))]
        out[arm] = {"cells": len(vals),
                    "cells_nonzero": sum(1 for v in vals if v),
                    "events": int(sum(vals))}
    return out


def position_effect(rows: list[dict]) -> dict[str, dict]:
    """criterion -> letter -> {mean, n}: the grade a prompt POSITION attracts,
    pooled over arms. Both run-3 judges penalized position C, and run 3's
    random shuffle put one arm there 32 times and another 17, so part of the
    per-arm spread was positional. This is what a balanced rotation is meant
    to make harmless — it does not remove the effect, it stops it landing
    unevenly."""
    letters = sorted({L for r in rows for L in (r.get("shuffle") or {})})
    out: dict[str, dict] = {}
    for f in ALL_FIELDS:
        cell: dict[str, dict] = {}
        for L in letters:
            vals = []
            for r in rows:
                arm = (r.get("shuffle") or {}).get(L)
                g = (r.get("grades") or {}).get(arm) if arm else None
                if g and isinstance(g.get(f), (int, float)):
                    vals.append(float(g[f]))
            cell[L] = {"mean": _mean(vals), "n": len(vals)}
        out[f] = cell
    return out


def position_balance(rows: list[dict]) -> dict[str, dict]:
    """arm -> letter -> how many calls it wore that letter. A balanced run
    reads 20/20/20/20 per arm over 80 windows plus its repeats."""
    out: dict[str, dict] = {}
    for r in rows:
        for L, arm in (r.get("shuffle") or {}).items():
            out.setdefault(arm, {})
            out[arm][L] = out[arm].get(L, 0) + 1
    return out


def excerpt_stats(rows: list[dict]) -> dict[str, dict]:
    """arm -> {n, median, mean, max, capped, pre_cap_max} of `excerpt_ratio`.

    The median alone is what hid the run-3 leak: the published 0.97 / 0.99
    was true while the same arm carried a 10.39x window. Max and the capped
    count are the cells that make the tail visible."""
    out: dict[str, dict] = {}
    per_arm: dict[str, list[float]] = {}
    capped: dict[str, int] = {}
    pre_max: dict[str, float] = {}
    for r in rows:
        for arm, loc in (r.get("local") or {}).items():
            ratio = loc.get("excerpt_ratio")
            if ratio is not None:
                per_arm.setdefault(arm, []).append(float(ratio))
            if loc.get("capped"):
                capped[arm] = capped.get(arm, 0) + 1
            pcr = loc.get("pre_cap_ratio")
            if pcr is not None:
                pre_max[arm] = max(pre_max.get(arm, 0.0), float(pcr))
    for arm in sorted(set(per_arm) | set(capped)):
        vals = sorted(per_arm.get(arm, []))
        med = None
        if vals:
            mid = len(vals) // 2
            med = vals[mid] if len(vals) % 2 else 0.5 * (vals[mid - 1] + vals[mid])
        out[arm] = {"n": len(vals), "median": med, "mean": _mean(vals),
                    "max": vals[-1] if vals else None,
                    "capped": capped.get(arm, 0),
                    "pre_cap_max": pre_max.get(arm)}
    return out


def dropped_vs_excerpt_ratio(rows: list[dict]) -> dict[str, dict]:
    """Per arm, the Spearman between the judge's dropped-content count and
    that cell's excerpt ratio. It runs about -0.3 to -0.4 in every arm on
    both run-3 judges: a shorter excerpt is graded as having dropped more.
    That is partly the truth (a shorter transcript really did drop more) and
    partly the same shortness word error rate already reads, so the
    dropped-content column is not an independent measurement of it."""
    out: dict[str, dict] = {}
    arms = sorted({a for r in rows for a in (r.get("grades") or {})})
    for arm in arms:
        xs: list[float] = []
        ys: list[float] = []
        for r in rows:
            g = (r.get("grades") or {}).get(arm)
            loc = (r.get("local") or {}).get(arm)
            if not g or not loc or loc.get("excerpt_ratio") is None:
                continue
            v = g.get("dropped_content")
            if isinstance(v, (int, float)):
                xs.append(float(v))
                ys.append(float(loc["excerpt_ratio"]))
        out[arm] = {"n": len(xs), "spearman": spearman(xs, ys)}
    return out


def unanchored_windows(rows: list[dict], max_anchor_wer: float) -> set[str]:
    """Windows where at least one arm could not be ANCHORED into the audio at
    all, identified by that arm's local content-word WER exceeding
    `max_anchor_wer` — more content-word errors than the window has content
    words, i.e. the anchored span shares essentially nothing with the window.

    This is not a quality filter and it is not tuned: it separates "this arm
    transcribed the window badly" from "the harness aligned this arm to a
    different part of the meeting". `--min-confidence` was supposed to catch
    it and does not — the failing cells here read confidence 0.55 to 0.83
    against a 0.3 floor, because confidence is computed from the same
    over-wide match set that produced the bad span and so cannot catch its
    own failure.

    Both judges name these cells in their own notes ("completely unrelated to
    the reference excerpt"), and the rubric tells a judge facing one to
    "use high dropped_content" — an instruction on an UNBOUNDED scale. Gemini
    answered 5 and 10; Claude Haiku answered 100, twice, both on the same arm.
    Two cells then carried 200 of that arm's 333 dropped-content points over
    92 calls. A mean containing an answer that is not a count is not a
    measurement, which is why these windows come out before any mean is taken.

    Run 3 had the same broken windows and they were equally uncounted there:
    its second judge answered them with added_content 35 and 45 rather than
    100, so they inflated a different column instead of this one.

    The whole WINDOW is dropped, not just the offending cell, so every arm
    stays on one common substrate — and because the failures cluster by
    window (crosstalk-heavy AMI stretches where several arms mis-anchor at
    once) rather than by arm. Scoring per-cell instead moves no published
    mean by more than 0.03.
    """
    if max_anchor_wer <= 0:
        return set()
    bad: set[str] = set()
    for r in rows:
        for loc in (r.get("local") or {}).values():
            w = loc.get("content_word_wer")
            if isinstance(w, (int, float)) and w > max_anchor_wer:
                bad.add(r["window_id"])
                break
    return bad


def drop_windows(rows: list[dict], window_ids: set[str]) -> list[dict]:
    return [r for r in rows if r["window_id"] not in window_ids]


def drop_arms(rows: list[dict], names: list[str]) -> list[dict]:
    """Remove an arm from every row: its grades, its calibration block, and
    its letter. Used for `granite`, which has 3 unique windows all on one
    Earnings-21 file its own model card puts in its training data."""
    if not names:
        return rows
    out = []
    for r in rows:
        r = dict(r)
        r["grades"] = {k: v for k, v in (r.get("grades") or {}).items() if k not in names}
        r["local"] = {k: v for k, v in (r.get("local") or {}).items() if k not in names}
        r["shuffle"] = {L: a for L, a in (r.get("shuffle") or {}).items() if a not in names}
        out.append(r)
    return out


def self_consistency(rows: list[dict]) -> dict[str, dict]:
    by_key = {(r["window_id"], r["pass"]): r for r in rows}
    repeated = {r["window_id"] for r in rows if r["pass"] == 2}
    out: dict[str, dict] = {}
    for f in ALL_FIELDS:
        diffs: list[float] = []
        v1s: list[float] = []
        v2s: list[float] = []
        exact = 0
        for wid in sorted(repeated):
            r1, r2 = by_key.get((wid, 1)), by_key.get((wid, 2))
            if not r1 or not r2:
                continue
            for arm in sorted(set(r1.get("grades") or {}) & set(r2.get("grades") or {})):
                v1, v2 = r1["grades"][arm].get(f), r2["grades"][arm].get(f)
                if not isinstance(v1, (int, float)) or not isinstance(v2, (int, float)):
                    continue
                diffs.append(abs(v1 - v2))
                v1s.append(float(v1))
                v2s.append(float(v2))
                if v1 == v2:
                    exact += 1
        out[f] = {
            "n_pairs": len(diffs),
            "n_windows": len({w for w in repeated
                              if by_key.get((w, 1)) and by_key.get((w, 2))}),
            "exact_match": (exact / len(diffs)) if diffs else None,
            "kappa": cohens_kappa(v1s, v2s),
            "mean_abs_diff": _mean(diffs),
        }
    return out


def paired_cells(a: list[dict], b: list[dict]) -> tuple[dict[str, list[tuple[float, float]]], dict]:
    """(criterion -> [(a_score, b_score)], coverage report), paired on
    (window_id, pass, arm). Cells present on only one side are counted, not
    imputed — a judge that returned no grade for a label leaves a hole, and
    filling it would invent agreement."""
    ai = {(r["window_id"], r["pass"]): r for r in a}
    bi = {(r["window_id"], r["pass"]): r for r in b}
    shared_rows = sorted(set(ai) & set(bi))
    pairs: dict[str, list[tuple[float, float]]] = {f: [] for f in ALL_FIELDS}
    a_only = b_only = 0
    n_cells = 0
    for key in shared_rows:
        ga = ai[key].get("grades") or {}
        gb = bi[key].get("grades") or {}
        a_only += len(set(ga) - set(gb))
        b_only += len(set(gb) - set(ga))
        for arm in sorted(set(ga) & set(gb)):
            n_cells += 1
            for f in ALL_FIELDS:
                va, vb = ga[arm].get(f), gb[arm].get(f)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    pairs[f].append((float(va), float(vb)))
    coverage = {
        "rows_run_a": len(a), "rows_run_b": len(b),
        "rows_paired": len(shared_rows),
        "rows_only_in_a": len(set(ai) - set(bi)),
        "rows_only_in_b": len(set(bi) - set(ai)),
        "cells_paired": n_cells,
        "cells_only_in_a": a_only, "cells_only_in_b": b_only,
    }
    return pairs, coverage


def shuffle_identity(a: list[dict], b: list[dict]) -> dict:
    """Did run B actually see run A's TEXT? Checks, per paired row, that
    every arm's excerpt is byte-identical and reports separately whether the
    label -> arm map matched.

    THE EXCERPTS MUST MATCH — that is what `--windows-from` claims, and a
    mismatch means the two judges were not asked the same question, so no
    agreement number below means anything. THE LETTER MAPS SHOULD NOT, from
    run 4 on: both judges penalize prompt position C, and run 3's second
    judge replayed the first judge's shuffle, so their agreement carried a
    shared positional component. Run 4 gives each judge its own balanced
    rotation (`--position-offset`), and `label_maps_differing` counting
    every row is the evidence that it did."""
    ai = {(r["window_id"], r["pass"]): r for r in a}
    bi = {(r["window_id"], r["pass"]): r for r in b}
    shared = sorted(set(ai) & set(bi))
    shuffle_same = excerpt_same = 0
    mismatches: list[str] = []
    for key in shared:
        ra, rb = ai[key], bi[key]
        if (ra.get("shuffle") or {}) == (rb.get("shuffle") or {}):
            shuffle_same += 1
        else:
            mismatches.append(f"shuffle {key}")
        la, lb = ra.get("local") or {}, rb.get("local") or {}
        arms = set(la) & set(lb)
        if arms and all(la[k].get("excerpt") == lb[k].get("excerpt") for k in arms):
            excerpt_same += 1
        elif arms:
            mismatches.append(f"excerpt {key}")
    return {
        "rows_compared": len(shared),
        "identical_label_shuffle": shuffle_same,
        "label_maps_differing": len(shared) - shuffle_same,
        "identical_excerpts": excerpt_same,
        "excerpt_mismatches": len([m for m in mismatches if m.startswith("excerpt")]),
        "mismatches": mismatches[:10],
    }


def rank_agreement(means_a: dict[str, dict], means_b: dict[str, dict],
                   min_n: int) -> dict[str, dict]:
    """Per criterion: each judge's arm ORDER (best first — lowest mean for
    the four error counts, highest for readability) and whether they match.
    Arms with fewer than `min_n` graded windows are excluded: an arm judged
    on 4 windows has a mean that cannot be ordered against one judged on 92."""
    arms = sorted(set(means_a) & set(means_b))
    arms = [a for a in arms if (means_a[a]["n"] >= min_n and means_b[a]["n"] >= min_n)]
    out: dict[str, dict] = {}
    for f in ALL_FIELDS:
        higher_is_better = (f == "readability")
        def order(m: dict[str, dict]) -> list[str]:
            vals = [(a, m[a][f]) for a in arms if m[a][f] is not None]
            return [a for a, _ in sorted(vals, key=lambda t: (-t[1] if higher_is_better else t[1]))]
        oa, ob = order(means_a), order(means_b)
        rho = None
        if len(arms) >= 2:
            xs = [means_a[a][f] for a in arms if means_a[a][f] is not None and means_b[a][f] is not None]
            ys = [means_b[a][f] for a in arms if means_a[a][f] is not None and means_b[a][f] is not None]
            rho = spearman(xs, ys)
        out[f] = {
            "arms_ranked": arms,
            "order_run_a": oa, "order_run_b": ob,
            "same_order": oa == ob,
            "spearman_of_arm_means": rho,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-a", required=True, type=Path, help="first judge's grades.jsonl")
    ap.add_argument("--run-b", required=True, type=Path, help="second judge's grades.jsonl")
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    ap.add_argument("--min-rank-n", type=int, default=20,
                    help="an arm needs this many graded windows in BOTH runs to enter the "
                         "arm-ranking comparison (default 20; keeps a 4-window partial arm "
                         "from being ranked against a 92-window one)")
    ap.add_argument("--price-prompt", type=float, default=None,
                    help="run B's USD per prompt token, for the recorded spend")
    ap.add_argument("--price-completion", type=float, default=None,
                    help="run B's USD per completion token, for the recorded spend")
    ap.add_argument("--max-anchor-wer", type=float, default=1.0,
                    help="drop any WINDOW in which some arm's local content-word WER "
                         "exceeds this — the harness anchored that arm to a different "
                         "part of the meeting, so its grade measures the anchor and not "
                         "the arm (see `unanchored_windows`). 0 disables. Default 1.0: "
                         "more content-word errors than the window has content words.")
    ap.add_argument("--skip-arm", action="append", default=[], metavar="NAME",
                    help="drop an arm from both runs before anything is computed. "
                         "Repeatable. `granite` is dropped from the published tables: "
                         "3 unique windows, all on one Earnings-21 file its own model "
                         "card puts in its training data.")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    a, b = load(args.run_a), load(args.run_b)
    a_all, b_all = a, b
    if args.skip_arm:
        a, b = drop_arms(a, args.skip_arm), drop_arms(b, args.skip_arm)
        a_all, b_all = a, b
        print(f"dropped arm(s) {args.skip_arm} from both runs")
    unanchored = sorted(unanchored_windows(a, args.max_anchor_wer)
                        | unanchored_windows(b, args.max_anchor_wer))
    if unanchored:
        a, b = drop_windows(a, set(unanchored)), drop_windows(b, set(unanchored))
        print(f"dropped {len(unanchored)} window(s) no arm could be anchored into "
              f"(local content-word WER > {args.max_anchor_wer}): {', '.join(unanchored)}")
    label_a = args.label_a or next((r.get("model") for r in a if r.get("model")), "run-a")
    label_b = args.label_b or next((r.get("model") for r in b if r.get("model")), "run-b")

    pairs, coverage = paired_cells(a, b)
    agreement = {}
    for f in ALL_FIELDS:
        xs = [p[0] for p in pairs[f]]
        ys = [p[1] for p in pairs[f]]
        exact = sum(1 for x, y in zip(xs, ys) if x == y)
        agreement[f] = {
            "n_cells": len(xs),
            "spearman": spearman(xs, ys),
            "exact_match": (exact / len(xs)) if xs else None,
            "kappa": cohens_kappa(xs, ys),
            "mean_abs_diff": _mean([abs(x - y) for x, y in zip(xs, ys)]),
            "mean_run_a": _mean(xs), "mean_run_b": _mean(ys),
        }

    means_a, means_b = arm_means(a), arm_means(b)
    corpora = sorted({r.get("corpus") for r in b if r.get("corpus")})

    # Spend is what the RUN cost — every call it made, including the calls on
    # windows that were later dropped as unanchored. Billing does not care
    # which rows the scoring kept.
    prompt_tokens = sum((r.get("usage") or {}).get("prompt_tokens") or 0 for r in b_all)
    completion_tokens = sum((r.get("usage") or {}).get("candidates_tokens") or 0 for r in b_all)
    spend = None
    if args.price_prompt is not None and args.price_completion is not None:
        spend = round(prompt_tokens * args.price_prompt
                      + completion_tokens * args.price_completion, 4)

    doc = {
        "generated": date.today().isoformat(),
        "basis": {
            "means_over": "unique windows (a window graded twice is averaged first)",
            "max_anchor_wer": args.max_anchor_wer,
            "windows_dropped_unanchored": unanchored,
            "windows_scored": len({r["window_id"] for r in a}),
            "windows_collected": len({r["window_id"] for r in a_all}),
            "arms_dropped": args.skip_arm,
        },
        "unfiltered": {
            "note": "every collected cell, no unanchored-window exclusion — published "
                    "so the exclusion is auditable, not as the reading of the run",
            "run_a_per_arm_means": arm_means(a_all),
            "run_b_per_arm_means": arm_means(b_all),
        },
        "run_b": {
            "model": label_b,
            "grades": str(args.run_b),
            "windows": len({r["window_id"] for r in b}),
            "calls": len(b),
            "calls_made": len(b_all),
            "parse_failures": sum(1 for r in b_all if r.get("parse_error")),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "usd_per_prompt_token": args.price_prompt,
            "usd_per_completion_token": args.price_completion,
            "estimated_spend_usd": spend,
            "per_arm_means": means_b,
            "per_arm_means_per_call": arm_means(b, per_window=False),
            "per_corpus_means": {c: arm_means(b, c) for c in corpora},
            "self_consistency": self_consistency(b),
            "wrong_figure_events": figure_events(b),
            "position_effect": position_effect(b),
            "position_balance": position_balance(b),
            "excerpt_ratio": excerpt_stats(b),
            "dropped_vs_excerpt_ratio": dropped_vs_excerpt_ratio(b),
        },
        "run_a": {
            "model": label_a,
            "grades": str(args.run_a),
            "windows": len({r["window_id"] for r in a}),
            "calls": len(a),
            "per_arm_means": means_a,
            "per_arm_means_per_call": arm_means(a, per_window=False),
            "per_corpus_means": {c: arm_means(a, c) for c in corpora},
            "self_consistency": self_consistency(a),
            "wrong_figure_events": figure_events(a),
            "position_effect": position_effect(a),
            "position_balance": position_balance(a),
            "excerpt_ratio": excerpt_stats(a),
            "dropped_vs_excerpt_ratio": dropped_vs_excerpt_ratio(a),
        },
        "prompt_identity": shuffle_identity(a, b),
        "coverage": coverage,
        "agreement_per_cell": agreement,
        "agreement_arm_ranking": rank_agreement(means_a, means_b, args.min_rank_n),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")

    pid = doc["prompt_identity"]
    print(f"prompt identity: {pid['identical_excerpts']}/{pid['rows_compared']} rows with "
          f"IDENTICAL EXCERPTS (mismatches {pid['excerpt_mismatches']}); "
          f"{pid['label_maps_differing']} rows carry a DIFFERENT arm->letter map "
          f"(intended from run 4: each judge gets its own balanced rotation)")
    print(f"paired cells: {coverage['cells_paired']} "
          f"(only-in-a {coverage['cells_only_in_a']}, only-in-b {coverage['cells_only_in_b']})")

    def fmt(x, spec="{:.3f}"):
        return spec.format(x) if isinstance(x, (int, float)) else "n/a"

    for tag, rows_, means in (("A " + label_a, a, means_a), ("B " + label_b, b, means_b)):
        print(f"\n=== {tag} ===")
        print("per-arm means (UNIQUE WINDOWS):")
        for arm in sorted(means):
            m = means[arm]
            print(f"  {arm:22s} n={m['n']:3d} " +
                  " ".join(f"{f}={fmt(m[f], '{:.3f}')}" for f in ALL_FIELDS))
        fe = figure_events(rows_)
        print("wrong-figures EVENT counts (no ordering is claimed from this column):")
        for arm in sorted(fe):
            e = fe[arm]
            print(f"  {arm:22s} {e['events']} events in {e['cells_nonzero']}/{e['cells']} cells")
        sc = self_consistency(rows_)
        print("self-consistency (pass 1 vs pass 2 on the repeat windows):")
        for f in ALL_FIELDS:
            s = sc[f]
            em = f"{s['exact_match']:.0%}" if s["exact_match"] is not None else "n/a"
            print(f"  {f:20s} n={s['n_pairs']:3d} pairs over {s['n_windows']} windows  "
                  f"exact={em:>4s}  kappa={fmt(s['kappa'])}  |d|={fmt(s['mean_abs_diff'], '{:.2f}')}")
        pe = position_effect(rows_)
        letters = sorted(pe["added_content"])
        print("position effect (mean by prompt letter, pooled over arms):")
        print("  " + " " * 20 + "  " + "  ".join(f"{L:>12s}" for L in letters))
        for f in ALL_FIELDS:
            print(f"  {f:20s}  " + "  ".join(
                f"{fmt(pe[f][L]['mean'], '{:.3f}'):>7s}(n={pe[f][L]['n']:>3d})" for L in letters))
        pb = position_balance(rows_)
        print("position balance (calls per arm per letter):")
        for arm in sorted(pb):
            print(f"  {arm:22s} " + " ".join(f"{L}={pb[arm].get(L, 0)}" for L in letters))
        es = excerpt_stats(rows_)
        print("excerpt ratio (excerpt words / reference window words):")
        for arm in sorted(es):
            s = es[arm]
            print(f"  {arm:22s} n={s['n']:3d} median={fmt(s['median'])} mean={fmt(s['mean'])} "
                  f"max={fmt(s['max'])} capped={s['capped']} pre-cap max={fmt(s['pre_cap_max'])}")
        dv = dropped_vs_excerpt_ratio(rows_)
        print("spearman(dropped_content, excerpt_ratio) within arm — how much of the "
              "dropped-content column is shortness:")
        for arm in sorted(dv):
            print(f"  {arm:22s} n={dv[arm]['n']:3d} rho={fmt(dv[arm]['spearman'])}")

    print("\nper-cell agreement between the judges (Spearman / exact / kappa / mean|diff|):")
    for f in ALL_FIELDS:
        g = agreement[f]
        rho = f"{g['spearman']:.3f}" if g["spearman"] is not None else "n/a"
        print(f"  {f:20s} n={g['n_cells']:4d} rho={rho:>6s} "
              f"exact={g['exact_match']:.0%} kappa={fmt(g['kappa'])} "
              f"|d|={g['mean_abs_diff']:.2f} "
              f"(A {g['mean_run_a']:.2f} vs B {g['mean_run_b']:.2f})")
    print("\narm ranking (best first; lowest error count, highest readability):")
    for f in ALL_FIELDS:
        r = doc["agreement_arm_ranking"][f]
        print(f"  {f:20s} same_order={r['same_order']}  A={r['order_run_a']}  B={r['order_run_b']}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
