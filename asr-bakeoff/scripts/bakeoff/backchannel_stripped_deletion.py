#!/usr/bin/env python3
"""backchannel_stripped_deletion.py — clean-speech deletion with fillers and
backchannels removed from BOTH sides, for the single-file ASR probes.

Why: `score_corpus_wer.py --stratify` reports deletion on clean (non-overlapped)
speech over EVERY reference word. A transcriber that does not write "yeah",
"mm", "uh" loses those words there too, so the raw figure mixes two things — a
transcription CONVENTION and real content loss. On IS1009a more than half of
Moonshine's and Voxtral's clean-speech deletions were backchannels (2026-09-21).

What it does: drops every token in the scorer's own `FILLERS` set from the
reference (keeping each surviving word's overlap flag) and from the hypothesis,
aligns the two stripped sequences with the scorer's own alignment convention
(a replace block's surplus reference words are deletions), and counts deleted
reference words that are NOT overlapped. Reference, hypothesis, normalization
and overlap flags all come from `score_corpus_wer.py`, so the basis is the one
the headline numbers use. AMI only (overlap flags need the word annotations).

Basis: set `MIMICSCRIBE_ITN_NUMBERS=1` (see the public page's Reproducing
section) and give the run its own ITN cache via `MIMICSCRIBE_CORPUS_DATA`.

    MIMICSCRIBE_ITN_NUMBERS=1 python3 scripts/bakeoff/backchannel_stripped_deletion.py \\
        --file IS1009a --arms pipeline=<dir> batch=<dir> voxtral=<dir> moonshine=<dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import score_corpus_wer as S  # noqa: E402


def deleted_flags(ref: list[str], hyp: list[str]) -> list[bool]:
    out = [False] * len(ref)
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
        if tag == "delete":
            for i in range(i1, i2):
                out[i] = True
        elif tag == "replace":
            # Same convention as score_corpus_wer.stratify: the unmatched
            # surplus of a replace block is its FIRST reference words.
            for i in range(i1, i1 + max(0, (i2 - i1) - (j2 - j1))):
                out[i] = True
    return out


def measure(file_id: str, arm: Path) -> dict:
    rows = S._ami_rows(file_id)
    ref = [w for _, _, w, _ in rows]
    ov = S.overlap_flags(file_id)
    hyp = S.hypothesis(arm, file_id)
    if hyp is None or len(ov) != len(ref):
        raise SystemExit(f"{arm}: no hypothesis or overlap flags for {file_id}")

    raw_del = deleted_flags(ref, hyp)
    clean_n = sum(1 for o in ov if not o)
    clean_d = sum(1 for d, o in zip(raw_del, ov) if d and not o)
    bc_share = (sum(1 for w, d, o in zip(ref, raw_del, ov) if d and not o and w in S.FILLERS)
                / clean_d) if clean_d else 0.0

    keep = [i for i, w in enumerate(ref) if w not in S.FILLERS]
    ref_s = [ref[i] for i in keep]
    ov_s = [ov[i] for i in keep]
    hyp_s = [w for w in hyp if w not in S.FILLERS]
    s_del = deleted_flags(ref_s, hyp_s)
    s_clean_n = sum(1 for o in ov_s if not o)
    s_clean_d = sum(1 for d, o in zip(s_del, ov_s) if d and not o)
    sc = S.score(ref_s, hyp_s)

    return {
        "clean_ref_words": clean_n, "clean_deleted": clean_d,
        "clean_deletion": round(clean_d / clean_n, 4) if clean_n else None,
        "backchannel_share_of_clean_deletions": round(bc_share, 3),
        "stripped_clean_ref_words": s_clean_n, "stripped_clean_deleted": s_clean_d,
        "stripped_clean_deletion": round(s_clean_d / s_clean_n, 4) if s_clean_n else None,
        "stripped_wer": round(sc["wer"], 4),
        "stripped_sub_del_ins": [sc["sub"], sc["del"], sc["ins"]],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="AMI meeting id, e.g. IS1009a")
    ap.add_argument("--arms", nargs="+", required=True, help="label=<run dir with per-file/>")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    S._itn_bin()
    print(f"basis: ITN binary {S.itn_bin_id()}; strip set = score_corpus_wer.FILLERS ({len(S.FILLERS)} tokens)")
    out = {"file": args.file, "strip_set": sorted(S.FILLERS), "arms": {}}
    print(f"{'arm':<14}{'clean del':>10}{'bc share':>10}{'stripped del':>14}{'stripped WER':>14}")
    for spec in args.arms:
        label, _, d = spec.partition("=")
        m = measure(args.file, Path(d))
        out["arms"][label] = {"dir": d, **m}
        print(f"{label:<14}{m['clean_deletion']:>10.1%}{m['backchannel_share_of_clean_deletions']:>10.0%}"
              f"{m['stripped_clean_deletion']:>14.1%}{m['stripped_wer']:>14.1%}"
              f"   ({m['stripped_clean_deleted']}/{m['stripped_clean_ref_words']})")
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
