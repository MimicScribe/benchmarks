#!/usr/bin/env python3
"""ami_punctuation_accuracy.py — terminal-punctuation P/R/F1 on AMI.

WHY THIS EXISTS. `scripts/punctuation_accuracy.py` scores terminal marks
against earnings21's Rev.com `.nlp` references — prepared remarks read from a
page. MimicScribe's speaker attribution is built on sentence boundaries in
CONVERSATIONAL meeting speech, which earnings21 does not contain. The Voxtral
probe originally reported AMI terminal DENSITY (marks per 1k words) instead,
and two independent methodology reviews (2026-09-06) correctly called that
vacuous: density cannot tell a correct sentence end from a period after every
hesitation, and a model that deletes half the words scores HIGHER on it.

The ground truth was already there. AMI's word XML carries `punc="true"`
elements, and `score_corpus_wer._ami_rows_with_punc` already extracts the mark
following each word, per channel, with timings. This file adds the SCORER on
top of that extractor rather than writing a second XML parser — the reference
extraction has one implementation and one place to be wrong.

METHOD, deliberately the same shape as `punctuation_accuracy.py` so the two
numbers are read the same way: normalize both token streams (lowercase,
alphanumeric), align with `difflib.SequenceMatcher`, and score terminal
presence ONLY on 1:1 EQUAL-aligned pairs. Substitutions/inserts/deletes are WER
noise and get no punctuation verdict; coverage is reported so a low-coverage
arm cannot look good by aligning almost nothing.

    TP   ref terminal &  hyp terminal
    FP  !ref terminal &  hyp terminal   (spurious period)
    FN   ref terminal & !hyp terminal   (missed sentence end)

TWO THINGS THIS IS NOT.

1. NOT a gate. It prints a table and exits 0. `punctuation_accuracy.py
   --compare` is a must-not-worsen gate for two builds of OUR pipeline; between
   two different MODELS a drop is the finding, not a failure.
2. NOT overlap-aware. The AMI reference is the time-ordered union of every
   speaker's channel, so where two people talk at once it interleaves words no
   single-stream decoder can emit in order. Those regions produce alignment
   noise for EVERY arm equally. Differences between arms are meaningful; the
   absolute level is not comparable to any published punctuation figure.

NEW METHODOLOGY as of 2026-09-06 and not itself reviewed — read it as secondary
to the earnings21 number from the established instrument.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

TERMINAL_MARKS = {".", "?", "!"}
_NORM = re.compile(r"[^a-z0-9']+")


def norm_tokens(text: str) -> list[str]:
    return [t for t in _NORM.sub(" ", text.lower()).split() if t]


def hyp_stream(run_dir: Path, file_id: str):
    """(token, has_terminal_after) for an arm's rows, in time order."""
    p = run_dir / "per-file" / f"{file_id}_after_orphan.json"
    if not p.exists():
        return None
    segs = json.loads(p.read_text())["segments"]
    segs = sorted(segs, key=lambda s: (s.get("startTime", 0.0), s.get("endTime", 0.0)))
    out = []
    for s in segs:
        for raw in s["text"].split():
            toks = norm_tokens(raw)
            if not toks:
                continue
            # The mark rides the LAST normalized token of the whitespace word,
            # so "end." -> ("end", True) and "5.4" -> ("5", False), ("4", False).
            term = raw.rstrip("\"'”’)]").endswith(tuple(TERMINAL_MARKS))
            for t in toks[:-1]:
                out.append((t, False))
            out.append((toks[-1], term))
    return out


def ref_stream(file_id: str):
    """(token, has_terminal_after, is_turn_final) from the AMI annotations."""
    import score_corpus_wer as S

    rows = S._ami_rows_with_punc(file_id)
    if not rows:
        return None
    out = []
    for i, (_s, _e, word, spk, mark) in enumerate(rows):
        toks = norm_tokens(word)
        if not toks:
            continue
        nxt_spk = rows[i + 1][3] if i + 1 < len(rows) else None
        turn_final = nxt_spk is not None and nxt_spk != spk
        for t in toks[:-1]:
            out.append((t, False, False))
        out.append((toks[-1], mark in TERMINAL_MARKS, turn_final))
    return out


def score(run_dir: Path, file_ids: list[str]):
    tp = fp = fn = 0
    aligned = ref_total = hyp_total = 0
    turn_tp = turn_fn = 0
    per_file = {}

    for fid in file_ids:
        hyp = hyp_stream(run_dir, fid)
        ref = ref_stream(fid)
        if not hyp or not ref:
            continue
        h_words = [t for t, _ in hyp]
        r_words = [t for t, _, _ in ref]
        f_tp = f_fp = f_fn = f_al = 0
        sm = difflib.SequenceMatcher(a=h_words, b=r_words, autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                h_term = hyp[blk.a + k][1]
                r_term, r_turn = ref[blk.b + k][1], ref[blk.b + k][2]
                f_al += 1
                if r_term and h_term:
                    f_tp += 1
                elif h_term and not r_term:
                    f_fp += 1
                elif r_term and not h_term:
                    f_fn += 1
                if r_term and r_turn:
                    if h_term:
                        turn_tp += 1
                    else:
                        turn_fn += 1
        tp += f_tp; fp += f_fp; fn += f_fn
        aligned += f_al; ref_total += len(ref); hyp_total += len(hyp)
        per_file[fid] = {
            "aligned": f_al, "ref_words": len(ref), "hyp_words": len(hyp),
            "tp": f_tp, "fp": f_fp, "fn": f_fn,
            "precision": round(f_tp / (f_tp + f_fp), 4) if f_tp + f_fp else None,
            "recall": round(f_tp / (f_tp + f_fn), 4) if f_tp + f_fn else None,
        }

    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
    return {
        "arm": run_dir.name,
        "files": len(per_file),
        "ref_words": ref_total, "hyp_words": hyp_total,
        "aligned_pairs": aligned,
        "coverage": round(aligned / ref_total, 4) if ref_total else None,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(prec, 4) if prec is not None else None,
        "recall": round(rec, 4) if rec is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "turn_final_recall": round(turn_tp / (turn_tp + turn_fn), 4) if turn_tp + turn_fn else None,
        "turn_final_support": turn_tp + turn_fn,
        "per_file": per_file,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--files", nargs="+", required=True, help="AMI meeting ids")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    results = [score(Path(d), args.files) for d in args.run_dirs]

    hdr = f"{'arm':<24}{'cov':>7}{'P':>8}{'R':>8}{'F1':>8}{'TP':>7}{'FP':>7}{'FN':>7}{'turnR':>8}"
    print(hdr); print("-" * len(hdr))
    for r in results:
        def s(v, w=8, p=3):
            return f"{v:>{w}.{p}f}" if isinstance(v, float) else f"{'—':>{w}}"
        print(f"{r['arm'][:23]:<24}{s(r['coverage'],7)}{s(r['precision'])}{s(r['recall'])}"
              f"{s(r['f1'])}{r['tp']:>7}{r['fp']:>7}{r['fn']:>7}{s(r['turn_final_recall'])}")
    print("\ncoverage = 1:1 equal-aligned pairs / reference words. A LOW-coverage arm's")
    print("P/R is computed on the fraction of the transcript it got right, so read")
    print("coverage first. Levels are not comparable to published figures (the AMI")
    print("reference interleaves overlapped speakers); differences between arms are.")
    if results and results[0]["turn_final_support"]:
        print(f"turnR = recall on reference terminals at a SPEAKER CHANGE "
              f"(support {results[0]['turn_final_support']}) — the boundary "
              f"speaker attribution actually consumes.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
