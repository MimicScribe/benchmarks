#!/usr/bin/env python3
"""score_corpus_wer.py — FULL-VOCABULARY WER over a --benchmark-pipeline-corpus run.

WHY THIS EXISTS, AND WHY THE EXISTING INSTRUMENTS CANNOT ANSWER IT
------------------------------------------------------------------
`scripts/score_wer.py` and `scripts/score_merge_timed.py` both route every word
through `score_merge_timed.content_words()`, whose stop set is:

    a an the and or but if of to in on at for with as is are was were be been
    being i you he she it we they me him her us them my your his its our their
    this that these those so uh um er ah oh YEAH YES NO OK OKAY well like just
    MM HMM MHM

So `yeah / yes / no / ok / okay / uh / um / mm / hmm / mhm` are DISCARDED before
scoring. A filler hallucination or a filler deletion is invisible to every merge
and WER instrument in the repo BY CONSTRUCTION. That blind spot was found on
2026-07-29 while chasing a field report of "Parakeet adds the word yeah a lot":
nothing in the repo could measure the claim, in either direction.

It also consumes a different substrate. `score_wer.py` reads `--save-transcript`
token JSON, which only the 3-meeting merge probe produces. This reads the corpus
run's own `_after_orphan.json` per-stage dumps (the canonical final stage that
`bench-eval` globs), so it covers all 27 text-referenced files of the 57-file
canonical set with no extra decoding: 16 AMI (word XML) + 11 earnings21 (.nlp).

READ THIS BEFORE QUOTING A NUMBER
---------------------------------
Absolute WER here is INFLATED and is NOT comparable to any published AMI figure,
for the same two structural reasons `score_wer.py` documents:

  1. The AMI reference is the time-ordered UNION of per-speaker channels. Under
     overlapping speech it interleaves words no single-stream decoder can emit
     in order, and every such word scores as an error.
  2. Published AMI numbers use properly segmented per-channel audio and a
     scoring recipe (NIST/asclite, specific normalization) this does not
     implement.

Both biases are CONSTANT across arms decoded from the same audio, so an A/B
delta is meaningful even though the absolute level is not. Treat it as "which
arm is better, by how much", never as "our WER is X%".

TWO FURTHER TRAPS THIS SCRIPT DOES NOT HIDE FROM YOU
----------------------------------------------------
* NUMERAL VERBALIZATION accounts for ~30% of insertions on this corpus. The
  earnings21 references carry digits (`19`, `2020`, `30`) while the ASR spells
  them out (`nineteen`, `twenty twenty`, `thirty`), so every such token scores
  as one substitution plus one insertion. Those are scoring artifacts, not
  hallucinations. Read the insertion histogram, never the bare `ins` total.
* OVERLAP DOMINATES DELETIONS. Use `--stratify` before drawing any conclusion
  about recognition quality: on AMI, 28.2% of reference words are spoken while
  another speaker is active, and 76.5% of all deletions come from that 28%.
  Blended deletion rate reports mostly "can one stream emit two people at once"
  (structurally: no). The clean-speech rate is the recognition signal.

Usage
  PY=benchmark/.venv313/bin/python3
  $PY scripts/score_corpus_wer.py --arms benchmark/output/<runA> benchmark/output/<runB> \
      --labels baseline change --per-file --stratify
  $PY scripts/score_corpus_wer.py --arms benchmark/output/<run>        # single arm
  $PY scripts/score_corpus_wer.py --arms benchmark/output/<run> --onset \
      --onset-sites sites.json    # turn-onset arm; see the block above onset_profile

TURN-ONSET ARM (--onset). Answers "does the decoder drop the first words of a
speaker's turn?" and carries the three controls without which the raw number is
unreadable: per-word standardization (turn-initial words are disproportionately
short fillers), a within-turn split by turn length (a one-word turn's only word
is ALWAYS rank 0, so "short turns lost whole" and "turn openings clipped" score
identically without it), and a reordering check applied to BOTH populations.
Findings and pins: `benchmark/results/turn-onset-loss/RESULTS.md`.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

def _data_root() -> Path:
    """Locate the corpus tree. `MIMICSCRIBE_CORPUS_DATA=<dir>` (a tree laid out
    by `scripts/bakeoff/fetch_corpus.py --dest <dir>`) wins; otherwise
    `benchmark/data`, which is GITIGNORED and so exists only in the
    MAIN checkout, never in a worktree. `git rev-parse --git-common-dir` points
    at the shared `.git`, whose parent is that checkout. Same resolver shape as
    `score_live_vs_offline.py`.
    """
    import os
    env = os.environ.get("MIMICSCRIBE_CORPUS_DATA")
    if env and (Path(env) / "ami").is_dir():
        return Path(env)
    here = Path(__file__).resolve().parent.parent
    if (here / "benchmark" / "data" / "ami").is_dir():
        return here / "benchmark" / "data"
    import subprocess
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=here, capture_output=True, text=True, check=True,
        ).stdout.strip()
        root = (here / common).resolve().parent
        if (root / "benchmark" / "data" / "ami").is_dir():
            return root / "benchmark" / "data"
    except Exception:
        pass
    return here / "benchmark" / "data"


PROJ = Path(__file__).resolve().parent.parent
DATA = _data_root()
AMI_WORDS = DATA / "ami" / "annotations" / "words"
E21_REF = DATA / "earnings21" / "nlp_references"

# Filler / backchannel vocabulary the repo's other scorers discard. Reported as
# its own column precisely because it is the population they cannot see.
FILLERS = {
    "yeah", "yes", "yep", "yup", "no", "okay", "ok", "right", "uh", "um", "er",
    "ah", "oh", "mm", "hmm", "mhm", "mmhmm", "huh", "hm", "sure", "well",
}
# Assent/dissent tokens — the subset of FILLERS (plus a few not in that set)
# that carries a semantic payload when it answers a question, as opposed to
# a pure acknowledgement noise ("mm", "uh"). Used by the --onset-harm arm.
ASSENT_DISSENT = {
    "yes", "yeah", "yep", "yup", "no", "nope", "okay", "ok", "right",
    "exactly", "sure", "correct", "agreed", "definitely", "absolutely",
    "mhm", "mm", "mmhmm", "hmm", "uhhuh",
}

# Number/currency words that collide with digit-bearing references. NOT a
# hallucination population — see the numeral-verbalization note above.
NUMERALS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "billion", "percent", "dollar", "dollars", "euro",
    "euros", "cent", "cents", "point",
}


def norm(text: str) -> list[str]:
    """Lowercase, drop apostrophes, split on non-alphanumerics. NO stop set.

    Deliberately minimal and identical on both sides. No contraction folding —
    that is a separate axis and baking it in here would hide it.
    """
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("'", ""))


# --- the ITN basis ----------------------------------------------------------
#
# BOTH sides go through the app's OWN persisted-row text pass
# (`InverseTextNormalizer.normalizeRow`, reached through `mimicscribe
# --itn-text`) before tokenization. The rows a corpus run dumps have been
# normalized inside the pipeline since 2026-08-27 ("2020", "$5 million",
# "Q3", "dx" for a spelled D X) while the AMI reference is verbalized
# ("twenty twenty") and spells acronyms letter by letter (`D_X_`), so a raw
# compare charged every correctly transcribed number and acronym as errors:
# AMI WER rose +0.71pp between the 2026-08-25 pin and row ITN with no word
# lost (release review, 2026-08-28; 101 of 202 sampled edit regions carried
# digits, the rest were letter joins). Running the SAME transform over both
# sides makes the score ITN-invariant: what is left is recognition.
#
# A Python mirror of the normalizer was rejected -- a second copy drifts and
# the row-ITN campaign already showed the fixed-point property is measured,
# not proven. So this shells out to the binary, once per file, and caches by
# (binary identity, content). The pre-2026-08-29 basis is `--raw`; the pins
# under benchmark/results/live-transcription-public/pins.json name which
# basis they were measured on.
ITN_ENABLED = True
ITN_BIN_OVERRIDE: str | None = None
ITN_CACHE_DIR = DATA.parent / "cache" / "itn_text"
_ITN_BIN: Path | None = None
_ITN_BIN_ID: str | None = None
_ACRONYM = re.compile(r"^(?:[A-Za-z]_)+$")


def _itn_bin() -> Path:
    """The mimicscribe binary that implements `--itn-text`.

    A binary that PREDATES the mode would launch the app on the live database
    instead of normalizing text, so a candidate is accepted only if the flag's
    literal is in it. No fallback to a raw compare: that is a different basis
    and a number on it would be read against a pin it does not match.
    """
    global _ITN_BIN, _ITN_BIN_ID
    if _ITN_BIN is not None:
        return _ITN_BIN
    cands: list[Path] = []
    if ITN_BIN_OVERRIDE:
        cands.append(Path(ITN_BIN_OVERRIDE))
    if os.environ.get("MIMICSCRIBE_BIN"):
        cands.append(Path(os.environ["MIMICSCRIBE_BIN"]))
    for root in (PROJ, DATA.parent.parent):
        cands.append(root / ".build" / "release" / "mimicscribe")
        cands.append(root / ".build" / "debug" / "mimicscribe")
    seen: set[Path] = set()
    for c in cands:
        c = c.resolve()
        if c in seen or not c.is_file() or not os.access(c, os.X_OK):
            continue
        seen.add(c)
        if b"--itn-text" not in c.read_bytes():
            print(f"! {c}: no --itn-text mode (older build), skipped", file=sys.stderr)
            continue
        st = c.stat()
        _ITN_BIN, _ITN_BIN_ID = c, f"{st.st_size}-{st.st_mtime_ns}"
        return c
    sys.exit("❌ no mimicscribe binary with --itn-text found (swift build, or pass --itn-bin / "
             "MIMICSCRIBE_BIN). Refusing to score on the raw basis by accident; pass --raw to mean it.")


def itn_bin_id() -> str:
    _itn_bin()
    return _ITN_BIN_ID or "?"


def itn_lines(lines: list[str]) -> list[str]:
    """Every line through the persisted-row normalizer, 1:1.

    Disk-cached by (binary identity, content): re-scoring an arm costs nothing,
    a rebuilt binary invalidates every entry. Line count is checked on both the
    cache and the binary's output -- a short answer would silently misalign
    every token after it.
    """
    if not ITN_ENABLED or not lines:
        return list(lines)
    clean = [(l or "").replace("\r", " ").replace("\n", " ") for l in lines]
    binp = _itn_bin()
    key = hashlib.sha1((str(_ITN_BIN_ID) + "\0" + "\n".join(clean)).encode("utf-8")).hexdigest()
    ITN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = ITN_CACHE_DIR / f"{key}.txt"
    if cache.exists():
        out = cache.read_text(encoding="utf-8").split("\n")
        if out and out[-1] == "":
            out.pop()
        if len(out) == len(clean):
            return out
    with tempfile.TemporaryDirectory(dir=ITN_CACHE_DIR) as td:
        src, dst = Path(td) / "in.txt", Path(td) / "out.txt"
        src.write_text("\n".join(clean) + "\n", encoding="utf-8")
        env = dict(os.environ, MIMICSCRIBE_LOG_QUIET="1")
        r = subprocess.run([str(binp), "--itn-text", "--in", str(src), "--out", str(dst)],
                           capture_output=True, text=True, timeout=900, env=env)
        if r.returncode != 0 or not dst.exists():
            sys.exit(f"❌ {binp} --itn-text failed (rc={r.returncode}):\n{r.stdout[-600:]}\n{r.stderr[-600:]}")
        out = dst.read_text(encoding="utf-8").split("\n")
        if out and out[-1] == "":
            out.pop()
        if len(out) != len(clean):
            sys.exit(f"❌ --itn-text returned {len(out)} line(s) for {len(clean)} — refusing a misaligned basis")
        cache.write_text("\n".join(out) + "\n", encoding="utf-8")
    return out


def _acronym_join(text: str) -> str:
    """AMI writes a spelled acronym as one token, `D_N_L_G_`; the persisted row
    carries the letters joined (`dnlg`), which is also what a reader sees."""
    return text.replace("_", "") if _ACRONYM.match(text) else text


def _retime(src: list[tuple[float, float, str]], dst: list[str], spk: str
            ) -> list[tuple[float, float, str, str]]:
    """Carry (start, end) from the raw tokens onto the normalized ones. Equal
    tokens keep their own times; a rewritten span ("twenty twenty" -> "2020")
    gives every output token the span's extent, so overlap flags and onset
    ranks still land on the right instant."""
    a = [w for _, _, w in src]
    out: list[tuple[float, float, str, str]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=a, b=dst, autojunk=False).get_opcodes():
        if tag == "equal":
            out.extend((src[i][0], src[i][1], dst[j], spk)
                       for i, j in zip(range(i1, i2), range(j1, j2)))
        elif tag == "delete":
            continue
        else:
            if i2 > i1:
                s0, e0 = src[i1][0], src[i2 - 1][1]
            elif i1 > 0:
                s0, e0 = src[i1 - 1][0], src[i1 - 1][1]
            elif src:
                s0, e0 = src[0][0], src[0][1]
            else:
                s0 = e0 = 0.0
            out.extend((s0, e0, dst[j], spk) for j in range(j1, j2))
    return out


def _itn_rows(raw: list[tuple[float, float, str, str]]) -> list[tuple[float, float, str, str]]:
    """Normalize the union in runs of consecutive same-speaker words (a number
    phrase never usefully spans a speaker change), then re-time."""
    runs: list[list[int]] = []
    for i, r in enumerate(raw):
        if runs and raw[runs[-1][-1]][3] == r[3]:
            runs[-1].append(i)
        else:
            runs.append([i])
    texts = [" ".join(_acronym_join(raw[i][2]) for i in run) for run in runs]
    out: list[tuple[float, float, str, str]] = []
    for run, t in zip(runs, itn_lines(texts)):
        src = [(raw[i][0], raw[i][1], w) for i in run for w in norm(_acronym_join(raw[i][2]))]
        out.extend(_retime(src, norm(t), raw[run[0]][3]))
    return out


_AMI_ROWS_CACHE: dict[str, list[tuple[float, float, str, str]]] = {}


def _ami_rows(meeting: str) -> list[tuple[float, float, str, str]]:
    """(start, end, word, speaker) for one AMI meeting, time-sorted, on the
    ITN basis unless `ITN_ENABLED` is off (see the block above `_itn_bin`)."""
    if meeting in _AMI_ROWS_CACHE:
        return list(_AMI_ROWS_CACHE[meeting])
    raw: list[tuple[float, float, str, str]] = []
    for p in sorted(AMI_WORDS.glob(f"{meeting}.*.words.xml")):
        spk = p.name.split(".")[1]
        for el in ET.parse(p).getroot().iter():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            # punc = punctuation node; trunc = AMI-annotated cut-off word a
            # complete-word hypothesis should not be expected to match.
            if tag != "w" or el.get("punc") == "true" or el.get("trunc") == "true":
                continue
            st = el.get("starttime")
            if st is None:
                continue
            text = (el.text or "").strip()
            if not text:
                continue
            s0 = float(st)
            e0 = float(el.get("endtime") or st)
            raw.append((s0, e0, text, spk))
    raw.sort(key=lambda r: 0.5 * (r[0] + r[1]))
    if ITN_ENABLED:
        rows = _itn_rows(raw)
    else:
        rows = [(s0, e0, w, spk) for s0, e0, text, spk in raw for w in norm(text)]
    _AMI_ROWS_CACHE[meeting] = rows
    return list(rows)


def reference(file_id: str) -> tuple[str, list[str]] | None:
    """(corpus, reference words) or None when the file has no text truth."""
    rows = _ami_rows(file_id)
    if rows:
        return "ami", [w for _, _, w, _ in rows]
    p = E21_REF / f"{file_id}.nlp"
    if p.exists():
        out: list[str] = []
        with p.open() as fh:
            nlp = list(csv.DictReader(fh, delimiter="|"))
        if not ITN_ENABLED:
            for row in nlp:
                out.extend(norm(row.get("token") or ""))
            return "earnings21", out
        # Same transform as the rows: runs of consecutive same-speaker tokens.
        # The Rev.com reference is already digit-form, so this is mostly the
        # fixed point -- applied anyway so the two sides share one pass.
        runs: list[str] = []
        cur: list[str] = []
        spk = None
        for row in nlp:
            tok = (row.get("token") or "").strip()
            if not tok:
                continue
            if cur and row.get("speaker") != spk:
                runs.append(" ".join(cur))
                cur = []
            spk = row.get("speaker")
            cur.append(tok)
        if cur:
            runs.append(" ".join(cur))
        for t in itn_lines(runs):
            out.extend(norm(t))
        return "earnings21", out
    return None


# Per-file stage dumps a corpus run writes, in pipeline order. Reading the same
# metric at each one localizes a word loss to the stage that caused it WITHOUT
# re-decoding anything: present at `sentences` and absent at `after_orphan`
# means the decoder produced it and a post-ASR pass removed it.
STAGES = ("sentences", "after_sentenceCentroid", "after_junkDissolve", "after_orphan")
STAGE = "after_orphan"


def hypothesis(arm: Path, file_id: str, stage: str | None = None) -> list[str] | None:
    """Words from one per-file stage dump, in time order.

    Defaults to the canonical final stage (`after_orphan`), which is what
    `bench-eval`, `asr_bench.py` and `over_split_diagnostic.py` all read, so
    arms cannot drift. `sentences` is the pre-merge ASR substrate and carries
    `sentences`/`start` where the later stages carry `segments`/`startTime`.
    """
    st = stage or STAGE
    p = arm / "per-file" / f"{file_id}_{st}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    items = d.get("segments") or d.get("sentences") or []
    key = "startTime" if "segments" in d else "start"
    ordered = sorted(items, key=lambda s: s.get(key, 0.0))
    out: list[str] = []
    # Rows dumped since 2026-08-27 are already normalized (this is the fixed
    # point for them); an OLDER arm's verbalized rows are brought onto the
    # same basis, which is what makes a cross-build compare meaningful.
    for t in itn_lines([s.get("text") or "" for s in ordered]):
        out.extend(norm(t))
    return out


def score(ref: list[str], hyp: list[str]) -> dict:
    """Edit script with the insertion/deletion/substitution populations kept.

    `autojunk=False` matters: SequenceMatcher otherwise treats common words
    ("the") as junk on long inputs and silently inflates the error count.
    """
    sub = dele = ins = 0
    ins_words: list[str] = []
    del_words: list[str] = []
    sub_pairs: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
        if tag == "replace":
            nr, nh = i2 - i1, j2 - j1
            sub += min(nr, nh)
            sub_pairs.extend(zip(ref[i1:i1 + min(nr, nh)], hyp[j1:j1 + min(nr, nh)]))
            if nr > nh:
                dele += nr - nh
                del_words.extend(ref[i1 + nh:i2])
            elif nh > nr:
                ins += nh - nr
                ins_words.extend(hyp[j1 + nr:j2])
        elif tag == "delete":
            dele += i2 - i1
            del_words.extend(ref[i1:i2])
        elif tag == "insert":
            ins += j2 - j1
            ins_words.extend(hyp[j1:j2])
    n = len(ref)
    return {
        "n": n, "hyp_n": len(hyp), "sub": sub, "del": dele, "ins": ins,
        "wer": (sub + dele + ins) / n if n else 0.0,
        "ins_words": ins_words, "del_words": del_words, "sub_pairs": sub_pairs,
    }


def overlap_flags_for_rows(rows: list[tuple[float, float, str, str]]) -> list[bool]:
    """Per AMI reference word: is a DIFFERENT speaker active at the same instant?

    Word order must match `reference()`'s exactly (same filters, same time sort)
    or the flags misalign against the union sequence.

    MERGED intervals + an exact bisect, not a neighbour scan. The previous
    implementation probed only `range(i-2, i+2)` of each other speaker's
    UNMERGED span list, which misses an overlap whose span STARTED well before
    the probe point — a long utterance from another speaker is only represented
    by its own start index, so a word landing deep inside it falls outside the
    4-neighbour window. Measured 2026-08-03: it under-reported overlap on every
    meeting checked and always in the same direction (ES2004c 1545 vs 1548,
    EN2002a 3332 vs 3340, TS3012d 2336 vs 2351 — ~0.2%, too small to move any
    conclusion already drawn from `--stratify`, but wrong).

    Merging first makes the check exact: merged spans are disjoint and sorted,
    so the ONLY candidate that can overlap `[s,e]` is the last one starting at
    or before `e`, and it overlaps iff its end is past `s`.
    """
    spans: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
    for s0, e0, _, spk in rows:
        spans[spk].append((s0, e0))
    merged: dict[str, list[tuple[float, float]]] = {}
    for spk, iv in spans.items():
        iv.sort()
        out: list[tuple[float, float]] = []
        for s0, e0 in iv:
            if out and s0 <= out[-1][1]:
                out[-1] = (out[-1][0], max(out[-1][1], e0))
            else:
                out.append((s0, e0))
        merged[spk] = out
    starts = {spk: [s for s, _ in iv] for spk, iv in merged.items()}

    flags = []
    for s0, e0, _, spk in rows:
        hit = False
        for other, iv in merged.items():
            if other == spk:
                continue
            i = bisect.bisect_right(starts[other], e0)
            # BOTH conditions. `bisect_right` only guarantees the candidate
            # starts <= e0, so a word ENDING exactly when another speaker's
            # word starts (e0 == other_start) is a touch, not an overlap, and
            # testing only `end > s0` flags it. Measured across the full AMI
            # corpus: 1248 false-positive overlap flags, 0 false negatives, in
            # 973,423 words. Each one silently removes a genuinely CLEAN word
            # from the hard-gate population.
            if i > 0 and iv[i - 1][1] > s0 and iv[i - 1][0] < e0:
                hit = True
                break
        flags.append(hit)
    return flags


def overlap_flags(meeting: str) -> list[bool]:
    return overlap_flags_for_rows(_ami_rows(meeting))


# --- turn-onset arm --------------------------------------------------------
#
# Question: does the decoder lose the FIRST words of a speaker's turn? Surfaced
# by the punctuation/casing work (2026-08-10, `feat/punctuation-casing-bench`),
# which found earnings21 rows opening mid-sentence because the turn's opening
# words were never transcribed.
#
# The onset is defined on the REFERENCE ALONE, never on our own segmentation.
# The prior measurement asked "did we lose words at a row boundary WE drew",
# which cannot separate a decode failure from a diarization artifact. Here the
# reference decides where a turn starts and the arm only reports whether we
# emitted those words.
#
# THE TWO CORPORA USE DIFFERENT DEFINITIONS AND MUST NOT BE POOLED:
#
#   AMI — words carry (start, end, speaker), so an onset is GAP-BASED: a word
#     by speaker S whose previous S-word ended more than ONSET_GAP ago. It is
#     deliberately NOT "the speaker changed vs the previous word of the union"
#     — the AMI reference is the time-ordered union of per-speaker channels, so
#     that test fires on every interleave inside overlapped speech and would
#     measure overlap rather than turn-taking.
#
#   earnings21 — the .nlp references carry a speaker column but NO timestamps
#     (verified 2026-08-10: 96,681 of 96,681 tokens have an empty `ts`), so a
#     gap is not computable. An onset is a token whose predecessor carries a
#     different speaker label. Sound there because that reference is a single
#     linear reading order with no interleaving, but it is a different unit —
#     report the two side by side, never as one rate.
ONSET_GAP = 0.5
# Another speaker active within this window before the onset ⇒ HANDOVER (the
# floor was just taken from someone). Otherwise COLD (starting out of silence).
# The split matters because the two have different suspects: a handover stresses
# diarization and the decode window; a cold start stresses VAD speech onset.
HANDOVER_WINDOW = 1.0
# Reported ranks. 0 = the turn's first word. Beyond this the word is "mid-turn"
# and forms the comparison population.
ONSET_RANKS = 4
# Half-width of the hypothesis window searched for a supposedly deleted word.
NEARBY_WORDS = 10


def _lengths_from_turn_ids(turn_ids: list[int]) -> list[int]:
    """Per word: how many words its turn contains.

    CRITICAL CONTROL. A one-word turn's only word is ALWAYS rank 0, so "the
    first word of a turn is deleted more often" and "short turns are lost
    entirely" produce the same onset+0 number. On AMI the deleted onsets are
    dominated by `mm` / `yeah` backchannels, which ARE one-word turns — without
    this split the two mechanisms are indistinguishable and the headline is
    unreadable. Only the LONG-turn rows answer "do we clip what someone says".

    Counted from explicit per-speaker turn ids, NOT from runs in the word
    sequence: the AMI reference is the interleaved union of per-speaker
    channels, so one turn's words are not contiguous in it and a run-length
    count would chop every turn at the first interjection from anyone else.
    """
    sizes = collections.Counter(turn_ids)
    return [sizes[t] for t in turn_ids]


def onset_profile(file_id: str) -> tuple[list[int], list[bool], list[int]] | None:
    """Per reference word: (onset rank, handover flag, turn word count), 1:1
    with `reference()`.

    Rank is ONSET_RANKS for every mid-turn word — the baseline population.
    `handover` is meaningful only at rank 0 and only on AMI (earnings21 has no
    times, so it is always False there). Turn length is the control described
    on `_lengths_from_turn_ids`.
    """
    rows = _ami_rows(file_id)
    if rows:
        # Merged per-speaker spans, reused for the handover test.
        spans: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
        for s0, e0, _, spk in rows:
            spans[spk].append((s0, e0))
        merged: dict[str, list[tuple[float, float]]] = {}
        for spk, iv in spans.items():
            iv.sort()
            out: list[tuple[float, float]] = []
            for s0, e0 in iv:
                if out and s0 <= out[-1][1]:
                    out[-1] = (out[-1][0], max(out[-1][1], e0))
                else:
                    out.append((s0, e0))
            merged[spk] = out
        starts = {spk: [s for s, _ in iv] for spk, iv in merged.items()}

        last_end: dict[str, float] = {}
        ranks: list[int] = []
        hand: list[bool] = []
        turn_ids: list[int] = []
        rank_of: dict[str, int] = {}
        turn_of: dict[str, int] = {}
        next_turn = 0
        for s0, e0, _, spk in rows:
            prev = last_end.get(spk)
            if prev is None or s0 - prev > ONSET_GAP:
                rank_of[spk] = 0
                turn_of[spk] = next_turn
                next_turn += 1
                # Was anyone else talking in the window just before this onset?
                h = False
                for other, iv in merged.items():
                    if other == spk:
                        continue
                    i = bisect.bisect_right(starts[other], s0)
                    if i > 0 and iv[i - 1][1] > s0 - HANDOVER_WINDOW:
                        h = True
                        break
                hand.append(h)
            else:
                rank_of[spk] = min(rank_of.get(spk, ONSET_RANKS) + 1, ONSET_RANKS)
                hand.append(False)
            ranks.append(rank_of[spk])
            turn_ids.append(turn_of[spk])
            last_end[spk] = max(prev or e0, e0)
        return ranks, hand, _lengths_from_turn_ids(turn_ids)

    p = E21_REF / f"{file_id}.nlp"
    if not p.exists():
        return None
    ranks = []
    turn_ids = []
    prev_spk = None
    rank = ONSET_RANKS
    turn = -1
    with p.open() as fh:
        for row in csv.DictReader(fh, delimiter="|"):
            spk = row.get("speaker")
            for _ in norm(row.get("token") or ""):
                if spk != prev_spk:
                    rank = 0
                    prev_spk = spk
                    turn += 1
                else:
                    rank = min(rank + 1, ONSET_RANKS)
                ranks.append(rank)
                turn_ids.append(turn)
    return ranks, [False] * len(ranks), _lengths_from_turn_ids(turn_ids)


def hypothesis_spans(arm: Path, file_id: str) -> list[tuple[float, float]] | None:
    """(start, end) of every emitted segment, time-sorted and merged.

    Used to ask the stage question: when we lost a turn's first word, had the
    pipeline emitted ANY text covering that instant? No coverage means nothing
    reached the decoder's output for that moment (a segmentation/VAD-shaped
    drop); coverage means a segment exists there but its text is missing the
    word (a decode- or merge-shaped drop). The two have different owners.
    """
    p = arm / "per-file" / f"{file_id}_after_orphan.json"
    if not p.exists():
        return None
    segs = json.loads(p.read_text()).get("segments") or []
    iv = sorted((float(s.get("startTime") or 0.0), float(s.get("endTime") or 0.0))
                for s in segs)
    out: list[tuple[float, float]] = []
    for s0, e0 in iv:
        if out and s0 <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e0))
        else:
            out.append((s0, e0))
    return out


def onset_sites(arm: Path, scored: list[tuple[str, tuple[str, list[str]]]]) -> list[dict]:
    """One record per DELETED turn-onset word on AMI (the corpus with times).

    earnings21 is excluded on purpose: its .nlp reference has no timestamps, so
    there is no way to ask where in the audio the word sat.
    """
    sites: list[dict] = []
    for fid, (corpus, ref) in scored:
        if corpus != "ami":
            continue
        hyp = hypothesis(arm, fid)
        spans = hypothesis_spans(arm, fid)
        prof = onset_profile(fid)
        if hyp is None or spans is None or prof is None:
            continue
        ranks, hand, _tlen = prof
        rows = _ami_rows(fid)
        ov = overlap_flags_for_rows(rows)
        deleted = [False] * len(ref)
        for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
            if tag == "delete":
                for i in range(i1, i2):
                    deleted[i] = True
            elif tag == "replace":
                for i in range(i1, i1 + max(0, (i2 - i1) - (j2 - j1))):
                    deleted[i] = True
        starts = [s for s, _ in spans]
        for i, r in enumerate(ranks):
            if r != 0 or not deleted[i] or ov[i]:
                continue
            s0, e0, w, spk = rows[i]
            k = bisect.bisect_right(starts, e0)
            covered = k > 0 and spans[k - 1][1] > s0
            # How late did the covering span open relative to the lost word?
            # A consistently POSITIVE value means the word was clipped in TIME
            # (the pipeline began transcribing after the word had started); a
            # negative one means the word sat well inside an emitted span and
            # was simply not transcribed.
            cover_delta = round(spans[k - 1][0] - s0, 3) if covered else None
            # Distance to the nearest segment start AFTER this word begins —
            # a late VAD/segment open shows up as a small positive number.
            nxt = next((s for s in starts if s >= s0), None)
            sites.append({
                "file": fid, "word": w, "speaker": spk, "start": s0,
                "handover": hand[i], "covered": covered,
                "cover_delta": cover_delta,
                "next_start_delta": None if nxt is None else round(nxt - s0, 3),
            })
    return sites


# --- turn-onset HARM arm (defect 2: one-word turns lost whole) -------------
#
# Direction C of the campaign (2026-08-11). Defect 2 is invisible to every
# merge/WER instrument in the repo (it IS mm/yeah/uh — see FILLERS above), so
# nobody has ever quantified whether losing it is a real user-visible harm or
# just noise-word cleanup. This classifies each DELETED clean one-word turn
# (tlen==1, onset rank 0, not overlapped — the exact "1" row of
# `onset_stratify`'s WITHIN-TURN table) lexically, and flags whether the
# IMMEDIATELY PRECEDING reference word carries a trailing "?": a cheap,
# defensible proxy for "the previous turn asked a question", because in both
# reference formats a "?" mark only ever appears at a genuine utterance
# boundary, never mid-utterance. A deleted assent/dissent token (yes/no/
# yeah/okay/right/...) in that context is an ANSWER MOMENT: losing it erases
# a recorded response to a question, not just an acknowledgement noise word.
# Never pooled across corpora, never pooled with defect 1.


def _ami_rows_with_punc(file_id: str) -> list[tuple[float, float, str, str, str | None]]:
    """Like `_ami_rows` but each row also carries the trailing punctuation
    mark immediately following that word in ITS OWN channel's raw XML
    (None if none) — `_ami_rows` drops punc nodes entirely, so the onset arm
    has never had a way to ask "did the previous turn end in a question".

    Same filters as `_ami_rows` (skip punc/trunc nodes when collecting real
    words); the caller in `onset_harm` verifies word-for-word alignment
    against `reference()` before trusting this, since the two functions walk
    the XML independently and must not silently diverge.
    """
    rows: list[tuple[float, float, str, str, str | None]] = []
    for p in sorted(AMI_WORDS.glob(f"{file_id}.*.words.xml")):
        spk = p.name.split(".")[1]
        elems = []
        for el in ET.parse(p).getroot().iter():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if tag != "w" or el.get("trunc") == "true":
                continue
            elems.append(el)
        n = len(elems)
        i = 0
        while i < n:
            el = elems[i]
            if el.get("punc") == "true":
                i += 1
                continue
            st = el.get("starttime")
            text = (el.text or "").strip()
            if st is None or not text:
                i += 1
                continue
            s0 = float(st)
            e0 = float(el.get("endtime") or st)
            mark = None
            if i + 1 < n and elems[i + 1].get("punc") == "true":
                m = (elems[i + 1].text or "").strip()
                mark = m if m in ("?", ".", ",") else None
            ws = norm(text)
            for w in ws[:-1]:
                rows.append((s0, e0, w, spk, None))
            if ws:
                rows.append((s0, e0, ws[-1], spk, mark))
            i += 1
    rows.sort(key=lambda r: 0.5 * (r[0] + r[1]))
    return rows


def _e21_marks(file_id: str) -> list[str | None] | None:
    """Per normalized earnings21 reference word: trailing punctuation mark
    for that token's row (None if none), 1:1 with `reference()`'s word list
    (same per-row `norm()` extension, so the two stay aligned by construction).
    """
    p = E21_REF / f"{file_id}.nlp"
    if not p.exists():
        return None
    out: list[str | None] = []
    with p.open() as fh:
        for row in csv.DictReader(fh, delimiter="|"):
            ws = norm(row.get("token") or "")
            mark = (row.get("punctuation") or "").strip()
            mark = mark if mark in ("?", ".", ",") else None
            for _ in ws[:-1]:
                out.append(None)
            if ws:
                out.append(mark)
    return out


def onset_harm(arm: Path, scored: list[tuple[str, tuple[str, list[str]]]]) -> dict:
    """Per corpus: lexical census + answer-moment classification of DELETED
    clean one-word turns. See module comment above for the method and why.
    """
    per_corpus: dict[str, dict] = {
        c: {
            "total_oneword": 0, "total_deleted": 0,
            "census": collections.Counter(), "census_seen": collections.Counter(),
            "filler_deleted": 0, "numeral_deleted": 0, "content_deleted": 0,
            "answer_moment_deleted": 0, "answer_moment_total": 0,
            "pure_backchannel_deleted": 0, "assent_total": 0,
            "content_word_sites": [], "numeral_sites": [],
            "files": set(), "duration_s": 0.0,
        }
        for c in ("ami", "earnings21")
    }
    ami_duration_done: set[str] = set()
    for fid, (corpus, ref) in scored:
        hyp = hypothesis(arm, fid)
        prof = onset_profile(fid)
        if hyp is None or prof is None:
            continue
        ranks, hand, tlen = prof
        if len(ranks) != len(ref):
            sys.exit(f"onset/ref length mismatch on {fid}: {len(ranks)} vs {len(ref)}")
        pc = per_corpus[corpus]
        if corpus == "ami":
            rows_p = _ami_rows_with_punc(fid)
            if [w for _, _, w, _, _ in rows_p] != ref:
                sys.exit(f"--onset-harm: punc-row/ref word mismatch on {fid} "
                         "— alignment broken, refusing to score")
            marks = [m for *_, m in rows_p]
            ov = overlap_flags_for_rows([(s, e, w, spk) for s, e, w, spk, _ in rows_p])
            if fid not in ami_duration_done:
                pc["duration_s"] += max((e for _, e, *_ in rows_p), default=0.0)
                ami_duration_done.add(fid)
        else:
            marks = _e21_marks(fid)
            if marks is None or len(marks) != len(ref):
                sys.exit(f"--onset-harm: punc-row/ref length mismatch on {fid} "
                         "— alignment broken, refusing to score")
            ov = [False] * len(ref)
        deleted = [False] * len(ref)
        for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
            if tag == "delete":
                for i in range(i1, i2):
                    deleted[i] = True
            elif tag == "replace":
                for i in range(i1, i1 + max(0, (i2 - i1) - (j2 - j1))):
                    deleted[i] = True
        file_has_onset = False
        for i, r in enumerate(ranks):
            if r != 0 or tlen[i] != 1 or ov[i]:
                continue
            file_has_onset = True
            w = ref[i]
            pc["total_oneword"] += 1
            pc["census_seen"][w] += 1
            prev_q = i > 0 and marks[i - 1] == "?"
            is_assent = w in ASSENT_DISSENT
            if is_assent:
                pc["assent_total"] += 1
                if prev_q:
                    pc["answer_moment_total"] += 1
            if not deleted[i]:
                continue
            pc["total_deleted"] += 1
            pc["census"][w] += 1
            if w in FILLERS:
                pc["filler_deleted"] += 1
            elif w.isdigit() or w in NUMERALS:
                pc["numeral_deleted"] += 1
                pc["numeral_sites"].append((fid, w))
            else:
                pc["content_deleted"] += 1
                pc["content_word_sites"].append((fid, w))
            if is_assent and prev_q:
                pc["answer_moment_deleted"] += 1
            elif is_assent:
                pc["pure_backchannel_deleted"] += 1
        if file_has_onset:
            pc["files"].add(fid)
    return per_corpus


def onset_stratify(arm: Path, scored: list[tuple[str, tuple[str, list[str]]]]) -> dict:
    """Deletion counts bucketed by (corpus, onset rank) and, on AMI, by whether
    the word itself sits under overlapped speech and whether the onset was a
    handover.

    Overlap is carried through because it DOMINATES AMI deletions (76.5% of them
    per --stratify) and a turn onset is exactly where a second speaker is most
    likely still finishing. Reading an onset rate without splitting on overlap
    would re-report the overlap effect under a new name.
    """
    buckets: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
    # Per WORD IDENTITY, clean speech only, onset+0 vs mid-turn. Turn-initial
    # words are disproportionately short fillers ("yeah", "uh", "so"), which are
    # deleted more often WHEREVER they appear — so a raw onset rate cannot tell
    # "position causes loss" from "onsets carry harder words". This is the
    # matched control: direct standardization of the onset population onto the
    # mid-turn per-word rates.
    by_word: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0, 0])
    # WITHIN-TURN comparison, clean speech only: a turn's first word against the
    # SAME turn's remaining words, bucketed by turn length. Turn length is then
    # fully controlled, so a gap here cannot be "short turns are lost entirely"
    # wearing a costume.
    by_turnlen: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
    # ALIGNMENT-ARTIFACT CHECK, restricted to the first word of a long turn.
    # SequenceMatcher scores a REORDERING as deletion+insertion, and a turn
    # start is exactly where our time-ordered rows can disagree with the
    # reference's order — so "deleted" there could mean "emitted, elsewhere".
    # [genuinely absent, present within NEARBY_WORDS of the alignment anchor]
    nearby: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    checked = 0
    for fid, (corpus, ref) in scored:
        hyp = hypothesis(arm, fid)
        if hyp is None:
            continue
        prof = onset_profile(fid)
        if prof is None:
            continue
        ranks, hand, tlen = prof
        if len(ranks) != len(ref):
            # HARD failure, not a skip: a silent skip here reports a clean run
            # over a population that was never scored.
            sys.exit(f"onset/ref length mismatch on {fid}: {len(ranks)} vs {len(ref)}")
        ov = overlap_flags(fid) if corpus == "ami" else [False] * len(ref)
        if len(ov) != len(ref):
            sys.exit(f"overlap/ref length mismatch on {fid}: {len(ov)} vs {len(ref)}")
        deleted = [False] * len(ref)
        # Approximate hypothesis position for every reference index, so a
        # deleted word can be looked for in the neighbourhood it should occupy.
        anchor = [0] * len(ref)
        for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
            for i in range(i1, i2):
                anchor[i] = min(len(hyp), j1 + (i - i1))
            if tag == "delete":
                for i in range(i1, i2):
                    deleted[i] = True
            elif tag == "replace":
                for i in range(i1, i1 + max(0, (i2 - i1) - (j2 - j1))):
                    deleted[i] = True
        checked += 1
        for i, r in enumerate(ranks):
            key = (corpus, r, ov[i], hand[i] if r == 0 else False)
            b = buckets[key]
            b[0] += 1
            b[1] += deleted[i]
            if not ov[i]:
                tb = ("1", "2-3", "4-9", "10+")[
                    0 if tlen[i] <= 1 else 1 if tlen[i] <= 3 else 2 if tlen[i] <= 9 else 3]
                t = by_turnlen[(corpus, tb, r == 0)]
                t[0] += 1
                t[1] += deleted[i]
                if tlen[i] >= 10 and deleted[i]:
                    a = anchor[i]
                    win = hyp[max(0, a - NEARBY_WORDS):a + NEARBY_WORDS]
                    nearby[(corpus, r == 0)][1 if ref[i] in win else 0] += 1
                w = by_word[(corpus, ref[i])]
                if r == 0:
                    w[0] += 1
                    w[1] += deleted[i]
                elif r >= ONSET_RANKS:
                    w[2] += 1
                    w[3] += deleted[i]
    return {"buckets": buckets, "files": checked, "by_word": by_word,
            "by_turnlen": by_turnlen, "nearby": nearby}


def stratify(arm: Path, meetings: list[str]) -> dict:
    ov_n = ov_d = cl_n = cl_d = 0
    for m in meetings:
        hyp = hypothesis(arm, m)
        if hyp is None:
            continue
        rows = _ami_rows(m)
        if not rows:
            continue
        ref = [w for _, _, w, _ in rows]
        fl = overlap_flags(m)
        if len(fl) != len(ref):
            print(f"  ! {m}: flag/ref mismatch ({len(fl)} vs {len(ref)}) — skipped")
            continue
        deleted = [False] * len(ref)
        for tag, i1, i2, j1, j2 in SequenceMatcher(a=ref, b=hyp, autojunk=False).get_opcodes():
            if tag == "delete":
                for i in range(i1, i2):
                    deleted[i] = True
            elif tag == "replace":
                # only the unmatched surplus of a replace is a deletion
                for i in range(i1, i1 + max(0, (i2 - i1) - (j2 - j1))):
                    deleted[i] = True
        for i, f in enumerate(fl):
            if f:
                ov_n += 1
                ov_d += deleted[i]
            else:
                cl_n += 1
                cl_d += deleted[i]
    return {"ov_n": ov_n, "ov_d": ov_d, "cl_n": cl_n, "cl_d": cl_d}


def main() -> int:
    global STAGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", required=True,
                    help="benchmark/output/<run> dirs; the first is the baseline")
    ap.add_argument("--labels", nargs="*", default=None)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--per-file", action="store_true")
    ap.add_argument("--stratify", action="store_true",
                    help="AMI deletion rate split by overlapped vs clean speech")
    ap.add_argument("--stage", default=STAGE, choices=STAGES,
                    help="which per-file stage dump to score (default the "
                         "canonical final one); use to localize a loss")
    ap.add_argument("--onset-sites", default=None,
                    help="write per-deleted-onset-word records (AMI only) to JSON")
    ap.add_argument("--onset", action="store_true",
                    help="deletion rate by reference-side turn-onset rank "
                         "(does the decoder lose a turn's first words?)")
    ap.add_argument("--onset-harm", action="store_true",
                    help="defect-2 harm quantification: lexical census + "
                         "answer-moment classification of deleted one-word "
                         "turns (last arm scored, like --onset-sites)")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--raw", action="store_true",
                    help="the pre-2026-08-29 basis: verbalized reference vs rows as dumped, "
                         "no ITN on either side (continuity with older pins only)")
    ap.add_argument("--itn-bin", default=None,
                    help="mimicscribe binary implementing --itn-text (default: "
                         "$MIMICSCRIBE_BIN, then .build/release then .build/debug)")
    args = ap.parse_args()
    STAGE = args.stage
    global ITN_ENABLED, ITN_BIN_OVERRIDE
    ITN_ENABLED = not args.raw
    ITN_BIN_OVERRIDE = args.itn_bin

    arms = [Path(a) for a in args.arms]
    labels = args.labels or [a.name for a in arms]
    if len(labels) != len(arms):
        sys.exit("--labels must have one entry per --arms")

    per_arm = {a: {p.name[: -len("_after_orphan.json")]
                   for p in (a / "per-file").glob("*_after_orphan.json")} for a in arms}
    # FILE-SET PARITY (audit 2026-08-24, ported from asr_bench.py): the two
    # arms must have dumped the SAME files. Without this a 27-file base
    # against a 5-file arm printed a plausible "+1.483pp" regression with
    # nothing on screen to say the arm was a fifth of the corpus.
    if len(arms) > 1:
        union = set().union(*per_arm.values())
        gaps = {a.name: sorted(union - fs) for a, fs in per_arm.items() if union - fs}
        if gaps:
            for name, missing in gaps.items():
                print(f"   {name}: missing {len(missing)} file(s): {', '.join(missing[:8])}"
                      f"{' …' if len(missing) > 8 else ''}", file=sys.stderr)
            sys.exit("❌ ARMS SCORED DIFFERENT FILE SETS — comparison refused")
    ids = sorted(set().union(*per_arm.values()))
    scored = [(f, r) for f, r in ((f, reference(f)) for f in ids) if r]
    n_ami = sum(1 for _, (c, _) in scored if c == "ami")
    if ITN_ENABLED:
        print(f"basis: ITN-NORMALIZED — reference AND rows through InverseTextNormalizer.normalizeRow "
              f"via {_itn_bin()} (id {itn_bin_id()}); AMI spelled acronyms joined")
    else:
        print("basis: RAW — verbalized reference vs rows as dumped (--raw; the pre-2026-08-29 basis)")
    print(f"{len(scored)} of {len(ids)} corpus files have a text reference "
          f"({n_ami} ami, {len(scored) - n_ami} earnings21)\n")
    if not scored:
        sys.exit("no scoreable files — is benchmark/data present? (main checkout only)")

    results: dict[str, dict] = {}
    for arm, label in zip(arms, labels):
        agg = collections.Counter()
        by_corpus = collections.defaultdict(collections.Counter)
        ins_h, del_h, sub_h = collections.Counter(), collections.Counter(), collections.Counter()
        per_file = {}
        for fid, (corpus, ref) in scored:
            hyp = hypothesis(arm, fid)
            if hyp is None:
                continue
            s = score(ref, hyp)
            per_file[fid] = {k: s[k] for k in ("n", "hyp_n", "sub", "del", "ins", "wer")}
            for k in ("n", "sub", "del", "ins", "hyp_n"):
                agg[k] += s[k]
                by_corpus[corpus][k] += s[k]
            ins_h.update(s["ins_words"])
            del_h.update(s["del_words"])
            sub_h.update(f"{a}->{b}" for a, b in s["sub_pairs"])
        results[label] = {
            "agg": dict(agg), "by_corpus": {c: dict(v) for c, v in by_corpus.items()},
            "ins_hist": ins_h, "del_hist": del_h, "sub_hist": sub_h, "per_file": per_file,
        }

    def wer_of(c):
        return (c["sub"] + c["del"] + c["ins"]) / c["n"] if c.get("n") else 0.0

    base = labels[0]
    print(f"{'arm':<22}{'refW':>9}{'hypW':>9}{'WER':>9}{'sub':>8}{'del':>8}{'ins':>8}")
    for label in labels:
        a = results[label]["agg"]
        d = ""
        if label != base:
            d = f"   {(wer_of(a) - wer_of(results[base]['agg'])) * 100:+.3f}pp"
        print(f"{label:<22}{a['n']:>9}{a['hyp_n']:>9}{wer_of(a) * 100:>8.2f}%"
              f"{a['sub']:>8}{a['del']:>8}{a['ins']:>8}{d}")
    print("\ndel = reference words we dropped (never-drop axis)"
          "\nins = words we produced the reference lacks (hallucination axis;"
          " ~30% is numeral verbalization on this corpus — read the histogram)\n")

    for corpus in ("ami", "earnings21"):
        if not any(results[l]["by_corpus"].get(corpus) for l in labels):
            continue
        print(f"-- {corpus}")
        for label in labels:
            c = results[label]["by_corpus"].get(corpus)
            if not c:
                continue
            print(f"   {label:<22} refW {c['n']:>7}  WER {wer_of(c) * 100:>6.2f}%  "
                  f"sub {c['sub']:>6}  del {c['del']:>6}  ins {c['ins']:>6}")
    print()

    print("FILLER / BACKCHANNEL AXIS — the population every other scorer discards")
    print(f"{'arm':<32} {'word':<9}{'inserted':>10}{'deleted':>9}")
    for label in labels:
        ih, dh = results[label]["ins_hist"], results[label]["del_hist"]
        for w in ("yeah", "uh", "um", "mm", "hmm", "okay", "right", "no", "oh"):
            print(f"{label:<32} {w:<9}{ih[w]:>10}{dh[w]:>9}")
        ti = sum(n for w, n in ih.items() if w in FILLERS)
        td = sum(n for w, n in dh.items() if w in FILLERS)
        print(f"{label:<32} {'ALL':<9}{ti:>10}{td:>9}\n")

    for label in labels:
        print(f"===== {label}: top {args.top} INSERTED words")
        h = results[label]["ins_hist"]
        tot = sum(h.values()) or 1
        for w, n in h.most_common(args.top):
            kind = "numeral" if (w in NUMERALS or w.isdigit()) else ("filler" if w in FILLERS else "")
            d = f"  ({n - results[base]['ins_hist'][w]:+d})" if label != base else ""
            print(f"   {w:<16}{n:>6}  {n / tot * 100:>5.2f}%  {kind:<8}{d}")
        num = sum(n for w, n in h.items() if w in NUMERALS or w.isdigit())
        fil = sum(n for w, n in h.items() if w in FILLERS)
        print(f"   -> numeral {num} ({num / tot * 100:.0f}%)  filler {fil} "
              f"({fil / tot * 100:.0f}%)  other {tot - num - fil}\n")

    last = labels[-1]
    print(f"===== {last}: top {args.top} DELETED reference words (missing speech)")
    for w, n in results[last]["del_hist"].most_common(args.top):
        d = f"  ({n - results[base]['del_hist'][w]:+d})" if len(labels) > 1 else ""
        print(f"   {w:<16}{n:>6}{d}")
    print()
    print(f"===== {last}: top {args.top} SUBSTITUTIONS (ref->hyp)")
    for w, n in results[last]["sub_hist"].most_common(args.top):
        print(f"   {w:<34}{n:>6}")
    print()

    if args.stratify:
        print("DELETION RATE BY OVERLAP (AMI only) — the two failure modes, separated.")
        print("  overlapped = another speaker was talking at the same instant, so a")
        print("  single-stream decoder cannot emit both and loss there is STRUCTURAL.")
        print("  Clean-speech deletion is the recognition-quality signal.")
        ami = [f for f, (c, _) in scored if c == "ami"]
        print(f"{'arm':<22}{'ovlpShare':>11}{'del|ovlp':>10}{'del|clean':>11}")
        for label, arm in zip(labels, arms):
            s = stratify(arm, ami)
            tot = s["ov_n"] + s["cl_n"]
            if not tot:
                continue
            print(f"{label:<22}{s['ov_n'] / tot * 100:>10.1f}%"
                  f"{s['ov_d'] / max(1, s['ov_n']) * 100:>9.1f}%"
                  f"{s['cl_d'] / max(1, s['cl_n']) * 100:>10.1f}%")
        print()

    if args.onset:
        print("DELETION RATE BY TURN-ONSET RANK (reference-side onsets).")
        print("  rank 0 = a speaker's first word after ONSET_GAP of their own silence")
        print(f"  (AMI, gap {ONSET_GAP}s) or after a speaker-label change (earnings21,")
        print("  which has no timestamps). mid = every later word of the turn.")
        print("  AMI onsets split handover (someone else was talking within "
              f"{HANDOVER_WINDOW}s) vs cold.")
        for label, arm in zip(labels, arms):
            res = onset_stratify(arm, scored)
            if not res["files"]:
                sys.exit(f"--onset scored 0 files for {label} — nothing was measured")
            print(f"\n-- {label}  ({res['files']} files)")
            print(f"{'corpus':<11}{'bucket':<22}{'refW':>9}{'del':>8}{'del rate':>10}")
            for corpus in ("ami", "earnings21"):
                rows_out = []
                for (c, r, ov, hand), (n, d) in sorted(res["buckets"].items()):
                    if c != corpus:
                        continue
                    name = "mid-turn" if r >= ONSET_RANKS else f"onset+{r}"
                    if r == 0 and corpus == "ami":
                        name += " handover" if hand else " cold"
                    name += " / ovlp" if ov else " / clean"
                    rows_out.append((name, n, d))
                for name, n, d in rows_out:
                    print(f"{corpus:<11}{name:<22}{n:>9}{d:>8}{d / max(1, n) * 100:>9.1f}%")

                print("\n  WITHIN-TURN, BY TURN LENGTH — a turn's first word vs its own rest")
                print(f"  {'turnWords':<11}{'firstN':>8}{'first%':>8}{'restN':>8}{'rest%':>8}{'ratio':>8}")
                for tb in ("1", "2-3", "4-9", "10+"):
                    f = res["by_turnlen"].get((corpus, tb, True), [0, 0])
                    o = res["by_turnlen"].get((corpus, tb, False), [0, 0])
                    if not f[0]:
                        continue
                    fr = f[1] / f[0]
                    rr = o[1] / o[0] if o[0] else 0.0
                    ratio = f"{fr / rr:.1f}x" if rr else "-"
                    print(f"  {tb:<11}{f[0]:>8}{fr * 100:>7.1f}%{o[0]:>8}{rr * 100:>7.1f}%{ratio:>8}")

                nf = res["nearby"].get((corpus, True), [0, 0])
                nr = res["nearby"].get((corpus, False), [0, 0])
                if sum(nf) and sum(nr):
                    # A word can be scored "deleted" while sitting a few words
                    # away in our output. Both populations are corrected, not
                    # just the numerator — a one-sided correction manufactures
                    # whichever ratio the correction favours.
                    ff = res["by_turnlen"][(corpus, "10+", True)]
                    rr = res["by_turnlen"][(corpus, "10+", False)]
                    a = ff[1] * nf[0] / sum(nf) / ff[0]
                    b = rr[1] * nr[0] / sum(nr) / rr[0]
                    print(f"  reordering share of those deletions: first {nf[1] / sum(nf) * 100:.0f}%"
                          f", rest {nr[1] / sum(nr) * 100:.0f}%")
                    print(f"  10+ turns, GENUINELY ABSENT only: first {a * 100:.1f}%"
                          f"  rest {b * 100:.1f}%  ratio {a / b:.1f}x")

                bw = {k[1]: v for k, v in res["by_word"].items() if k[0] == corpus}
                n_on = sum(v[0] for v in bw.values())
                d_on = sum(v[1] for v in bw.values())
                # Standardized: what onset+0 would have lost if each word were
                # deleted at ITS OWN mid-turn rate. Words absent mid-turn are
                # dropped from both sides so the comparison stays matched.
                exp = matched = 0.0
                for v in bw.values():
                    if v[0] and v[2]:
                        exp += v[0] * (v[3] / v[2])
                        matched += v[0]
                print("\n  MATCHED CONTROL — same word identity, clean speech only")
                print(f"  onset+0 words {n_on}, actually deleted {d_on} "
                      f"({d_on / max(1, n_on) * 100:.1f}%)")
                print(f"  matched subset {matched:.0f}; expected at their own mid-turn "
                      f"rates {exp:.0f} ({exp / max(1.0, matched) * 100:.1f}%)")
                print("  excess is what POSITION costs, over and above vocabulary")
                print(f"\n  {'word':<12}{'onsetN':>8}{'onset%':>8}{'midN':>8}{'mid%':>7}"
                      f"{'excessDel':>11}")
                rank = sorted(
                    ((w, v) for w, v in bw.items() if v[0] >= 20 and v[2] >= 20),
                    key=lambda kv: -(kv[1][1] - kv[1][0] * kv[1][3] / kv[1][2]))
                for w, v in rank[:12]:
                    print(f"  {w:<12}{v[0]:>8}{v[1] / v[0] * 100:>7.1f}%{v[2]:>8}"
                          f"{v[3] / v[2] * 100:>6.1f}%"
                          f"{v[1] - v[0] * v[3] / v[2]:>+11.1f}")
        print()

    if args.onset_sites:
        sites = onset_sites(arms[-1], scored)
        if not sites:
            sys.exit("--onset-sites found 0 deleted onsets — nothing was measured")
        Path(args.onset_sites).write_text(json.dumps(sites, indent=1))
        cov = sum(1 for s in sites if s["covered"])
        print(f"onset sites (AMI, clean, deleted): {len(sites)}")
        print(f"  covered by an emitted segment : {cov} "
              f"({cov / len(sites) * 100:.0f}%)  -> decode/merge shaped")
        print(f"  no segment at that instant    : {len(sites) - cov} "
              f"({(len(sites) - cov) / len(sites) * 100:.0f}%)  -> segmentation shaped")
        print(f"wrote {args.onset_sites}\n")

    if args.onset_harm:
        print("DEFECT-2 HARM (Direction C): lexical census + answer-moment "
              "classification of deleted CLEAN one-word turns.")
        print("  'answer moment' = a deleted assent/dissent token whose "
              "IMMEDIATELY PRECEDING reference word ends in '?' — a proxy for")
        print("  'this was a response to a question', since '?' only marks a "
              "genuine utterance boundary in both reference formats.\n")
        harm = onset_harm(arms[-1], scored)
        for corpus in ("ami", "earnings21"):
            pc = harm[corpus]
            if not pc["total_oneword"]:
                continue
            n_files = len(pc["files"])
            print(f"-- {corpus}  ({n_files} contributing files)")
            print(f"  one-word turns (clean speech): {pc['total_oneword']}  "
                  f"deleted: {pc['total_deleted']} "
                  f"({pc['total_deleted'] / pc['total_oneword'] * 100:.1f}%)")
            td = max(1, pc["total_deleted"])
            print(f"  of deleted: filler-class {pc['filler_deleted']} "
                  f"({pc['filler_deleted'] / td * 100:.0f}%)  "
                  f"numeral-class {pc['numeral_deleted']} "
                  f"({pc['numeral_deleted'] / td * 100:.0f}%)  "
                  f"other-content {pc['content_deleted']} "
                  f"({pc['content_deleted'] / td * 100:.0f}%)")
            print(f"\n  LEXICAL CENSUS — top {args.top} deleted one-word-turn words")
            print(f"  {'word':<14}{'del':>6}{'seen':>6}{'del%':>7}  class")
            for w, n in pc["census"].most_common(args.top):
                seen = pc["census_seen"][w]
                kind = ("numeral" if (w.isdigit() or w in NUMERALS)
                        else "filler" if w in FILLERS else "content")
                print(f"  {w:<14}{n:>6}{seen:>6}{n / seen * 100:>6.1f}%  {kind}")
            if pc["content_word_sites"]:
                print(f"\n  content-class deleted sites (file, word), first 20:")
                for fid, w in pc["content_word_sites"][:20]:
                    print(f"    {fid:<10}{w}")
            am_tot, am_del = pc["answer_moment_total"], pc["answer_moment_deleted"]
            bc_del = pc["pure_backchannel_deleted"]
            print(f"\n  ANSWER MOMENTS (assent/dissent after a '?'-marked prior "
                  f"word): {am_tot} occur, {am_del} lost "
                  f"({am_del / max(1, am_tot) * 100:.1f}%)")
            print(f"  PURE BACKCHANNELS (assent/dissent, no question context) "
                  f"lost: {bc_del}  ({pc['assent_total']} total assent-class "
                  f"one-word turns)")
            if pc["duration_s"]:
                hrs = pc["duration_s"] / 3600.0
                print(f"\n  RATE (reference-duration proxy, {n_files} files, "
                      f"{hrs:.2f}h pooled):")
                print(f"    answer moments LOST per meeting-hour: "
                      f"{am_del / hrs:.2f}")
                print(f"    answer moments LOST per meeting: "
                      f"{am_del / max(1, n_files):.2f}")
            else:
                print(f"\n  RATE: no timestamps in this reference format — "
                      f"per-hour not computable. Per-meeting (file-averaged): "
                      f"answer moments lost {am_del / max(1, n_files):.2f}/file, "
                      f"content-class words lost "
                      f"{pc['content_deleted'] / max(1, n_files):.2f}/file")
            print()

    if len(labels) > 1 and args.per_file:
        pa, pb = results[base]["per_file"], results[last]["per_file"]
        shared = [f for f in pb if f in pa]
        print(f"===== per-file WER, {base} -> {last} (worst delta first)")
        print(f"{'file':<12}{'refW':>8}{'WER_a':>8}{'WER_b':>8}{'d(pp)':>8}"
              f"{'dIns':>7}{'dDel':>7}{'dSub':>7}")
        for f in sorted(shared, key=lambda f: pb[f]["wer"] - pa[f]["wer"], reverse=True):
            a, b = pa[f], pb[f]
            print(f"{f:<12}{b['n']:>8}{a['wer'] * 100:>7.2f}%{b['wer'] * 100:>7.2f}%"
                  f"{(b['wer'] - a['wer']) * 100:>+8.2f}{b['ins'] - a['ins']:>+7}"
                  f"{b['del'] - a['del']:>+7}{b['sub'] - a['sub']:>+7}")
        moved = [pb[f]["wer"] - pa[f]["wer"] for f in shared]
        print(f"\nfiles changed: {sum(1 for f in shared if pa[f] != pb[f])}/{len(shared)}"
              f"   median delta {statistics.median(moved) * 100:+.3f}pp")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            label: {"agg": r["agg"], "by_corpus": r["by_corpus"], "per_file": r["per_file"],
                    "ins_top": r["ins_hist"].most_common(300),
                    "del_top": r["del_hist"].most_common(300),
                    "sub_top": r["sub_hist"].most_common(150)}
            for label, r in results.items()}, indent=2))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
