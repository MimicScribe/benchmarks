#!/usr/bin/env python3
"""judge_transcripts.py — blind LLM-judge bake-off for ASR transcript arms.

WHAT THIS DOES
---------------
Takes N corpus runs ("arms" — different ASR models/builds decoded over the
same audio, e.g. Parakeet v3, Parakeet v3 int8v2, Parakeet v2, Cohere,
Granite), slices the shared reference into ~60s text windows, locates the
matching span in each arm's hypothesis by TEXT alignment (no shared
timestamps between arms and reference), and asks a Gemini judge to grade
each arm's excerpt against the reference — blind to which arm is which
(labels are shuffled per window/pass and the map is recorded so grades can
be traced back afterwards).

WHY TEXT-ALIGNED WINDOWS, NOT TIME-ALIGNED
-------------------------------------------
The reference (AMI word XML / earnings21 .nlp) and each arm's hypothesis
dump carry their own, unrelated notion of "segment" — different models
segment differently, and the corpus-run dumps this reads
(`<run>/per-file/<id>_after_orphan.json`) do not carry a shared clock across
arms. So a window is defined on the REFERENCE word stream (by count, not
time), and each arm's matching span is located by finding the longest
matching text blocks (`difflib.SequenceMatcher`) between the window's words
and that arm's full normalized word stream. The confidence of that
match (fraction of the window's words that landed inside a matching block)
is recorded per (window, arm); a window an arm cannot be anchored into at
all is skipped for that arm only (not for the whole window — see
`--min-confidence`).

TWO WORD BASES, ON PURPOSE
---------------------------
* Windowing + anchoring + the calibration WER use the ITN-NORMALIZED word
  streams from `scripts/score_corpus_wer.py` (`reference()` / `hypothesis()`
  logic, reimplemented here at window granularity — see
  `itn_normalize_tokens`) — the same basis every other WER instrument in the
  repo uses, so a window's local WER is comparable to the corpus numbers.
* What the JUDGE reads is the RAW per-file segment text (original casing,
  punctuation, digit-vs-word spelling) reconstructed from
  `<run>/per-file/<id>_after_orphan.json` for a hypothesis, and from the
  raw AMI XML / earnings21 .nlp token+punctuation columns for the
  reference — because that is what a reader actually sees, and an
  ITN-normalized stream reads like a wire transcript, not a transcript.
  The mapping from an anchored NORMALIZED hyp word span back to RAW segment
  text is done by tracking, for every normalized hyp word, which raw
  segment produced it (`hypothesis_with_segments`) — segment-granularity,
  not word-granularity, which is enough at a ~150-word window size.

TWO JUDGES, AND WHY `--seed` CANNOT GIVE YOU THE SAME WINDOWS TWICE
--------------------------------------------------------------------
`--provider gemini|openrouter` picks which judge grades. The prompt, the
response schema, the temperature and the rate limiter are shared; only the
transport differs, so a difference in the grades is a difference between the
two MODELS.

To compare two judges you must show them the SAME prompts, and re-running
with the same `--seed` does NOT do that: the per-window letter shuffle is
seeded with `hash((seed, window_id, pass))`, and Python randomizes `str`
hashing per process, so a second process shuffles the arm letters
differently even with every flag identical. `--windows-from <grades.jsonl>`
replays a previous run's calls exactly: the label -> arm map and each arm's
excerpt are taken VERBATIM from the recorded rows, and the reference excerpt
is rebuilt by the same pure token chunking that produced it
(`rebuild_ref_chunks` — no ITN, so a replay needs neither the arm run
directories nor a `--itn-text` binary). `scripts/bakeoff/judge_agreement.py`
then scores the two runs against each other and re-verifies, row by row,
that the shuffles and excerpts really were identical.

RATE LIMITING (the owner's explicit requirement — read before raising
--concurrency or --min-interval)
------------------------------------------------------------------------
Sequential by default (`--concurrency 1`, hard-capped at 2). Every call
goes through one shared rate limiter: a global minimum spacing between
call STARTS (`--min-interval`, default 1.0s) plus exponential backoff with
jitter on HTTP 429/503 and on a body carrying RESOURCE_EXHAUSTED (2s base,
60s cap, 8 tries). On the FIRST 429 seen in the whole run, the run prints
that it saw one and DOUBLES the min-interval for every call after that —
the interval never recovers within a run. The API key is read from
`.env`/env and is NEVER put in a URL, printed, or logged — it travels only
in the `x-goog-api-key` request header.

RESUME
------
Every completed window+pass judge call is appended to `<out>/grades.jsonl`
immediately (one JSON object per line, flushed before the next call
starts). `--resume` re-reads that file, rebuilds the same deterministic
window sample (same `--seed`, `--per-corpus`, `--file-ids`, `--arms` must
be passed again — the sample is NOT itself persisted), and skips every
(window_id, pass) already on disk. A run that dies mid-way never re-pays
for a finished window.

OUTPUTS
-------
`--out <dir>/grades.jsonl` — one row per judge call (a window+pass), with
the shuffle map, the raw grades, each arm's locally-computed calibration
content-word WER + anchor confidence for that window, and token usage.
`--out <dir>/summary.md` — per-arm and per-corpus means/totals of every
criterion, readability mean, repeat-window self-consistency, and the
Spearman correlation between judge error totals and local content-word
WER. Never written under `benchmark/results` (the script refuses).

STATUS (2026-09-01) — TWO EXCERPT-TRIM DEFECTS FIXED, FULL RUN DONE (v3)
--------------------------------------------------------------------------
FIRST DEFECT: `anchor_window` handed the judge the WHOLE raw segment from
`seg_lo` to `seg_hi`, not the anchored word span — the production arm's
long diarization segments (10-30s) leaked far past the 150-word window
while the batch arms' short chunks did not. Fixed by `trim_excerpt_to_anchor`
locating the anchor's boundary words inside the raw token stream.

SECOND DEFECT, found by re-checking Earnings21 after the first fix: the
boundary picker took the EARLIEST match of the start n-gram and the LATEST
match of the end n-gram inside the whole segment — on a long production
segment a short n-gram ("uh the and", "in the quarter") recurs, so the
trim still opened onto the widest pair even though the anchored WORD span
agreed with the batch arm to a handful of words. Fixed by `_pick_boundary`:
try a 5-word boundary n-gram first, then 4, then 3, and among every match
at that length pick the one CLOSEST to an EXPECTED raw-token position
(the anchor's fractional position inside the segment range, scaled onto
the raw token count — normalized-to-raw word ratio is close to 1 outside
number spans) rather than blindly first/last. Every row now also carries
`excerpt_word_count` / `excerpt_ratio` (excerpt words / reference window
words) per arm, printed as a distribution after every run and listed in
`summary.md` for any (window, arm) pair over `EXCERPT_RATIO_LEAK` (1.5x) —
with both excerpts printed verbatim whenever `PRODUCTION_ARM` itself is
still one of them, so a residual leak is visible, not just a mean.

Two full runs redone with the fix in place, same seed/settings each time
(`--per-corpus 40 --repeat-fraction 0.15`): v2 (first fix only) had
`parakeet_v3` added_content 1.99 -> 0.96, readability 3.05 -> 3.74 — better,
but still visibly worse than every batch arm. v3 (both fixes) closed the
rest of the gap: added_content 0.96 -> 0.43 (batch arms sit at 0.42-0.68),
readability 3.74 -> 3.99 (batch arms 3.91-4.20) — production is now ON PAR
with the batch arms rather than measurably worse. The excerpt-ratio
distribution in v3 has `parakeet_v3` mean 1.044 / p90 1.026 / max 4.250,
statistically indistinguishable from the batch arms (`parakeet_v2` mean
1.157 / p90 1.952, `cohere` mean 1.085 / p90 1.000) — the few remaining
>1.5x cases are windows where BOTH arms independently anchor to an
unusually wide span (verified: `EN2006b#26` shows `parakeet_v3`=680w vs
`parakeet_v3_int8v2`=655w on the SAME stretch of dialogue), not a
trim defect. Granite still carries only 1 of 27 per-file dumps.

Usage (smoke)
  PY=python3   # stdlib only
  $PY scripts/bakeoff/judge_transcripts.py \\
      --arms parakeet_v3=<repo>/benchmark/output/swift_pipeline_2026-08-30T021253Z \\
             parakeet_v3_int8v2=<repo>/benchmark/output/bakeoff-parakeet-v3-int8v2 \\
             parakeet_v2=<repo>/benchmark/output/bakeoff-parakeet-v2 \\
             cohere=<repo>/benchmark/output/bakeoff-cohere \\
      --per-corpus 3 --repeat-fraction 0.34 \\
      --out /tmp/bakeoff-judge-smoke

Full run — add `granite=<path>` to --arms once it has all 27 files (it can
also run partial, as above; Granite is simply skipped per window it lacks),
and point --out somewhere durable (never `benchmark/results`). `--resume`
is safe to pass unconditionally — it is a no-op on a fresh `--out` dir.

Second judge over run 3's exact windows (no arm dirs, no ITN binary needed)
  $PY scripts/bakeoff/judge_transcripts.py \\
      --provider openrouter --model anthropic/claude-haiku-4.5 \\
      --windows-from <run3>/grades.jsonl --resume \\
      --out benchmark/output/bakeoff-judge-openrouter-claude-haiku-4.5

STATUS (2026-09-03) — RUN 4: FOUR MORE DEFECTS REMOVED
-------------------------------------------------------
An external review of run 3 found three defects in this harness and a
fourth was found while fixing them. All four charged particular arms for
something that was not their transcription.

(a) EXCERPT LEAK TAIL. `_best_cluster` + `trim_excerpt_to_anchor` bound the
    common case, not the tail: run 3 still had excerpt_ratio > 1.5 on 3
    pipeline / 6 v3-batch / 12 v2 / 6 Cohere windows, with maxima 4.25 /
    4.09 / 4.13 / 10.39 — a 1,558-word Cohere excerpt against a 150-word
    window. Surplus words read as added content. FIX: `cap_excerpt`, a hard
    cap at `--max-excerpt-ratio` (default 1.5) centered on the anchor's
    best-matching region. The published "median 0.97 / 0.99" hid this
    entirely, which is why the summary now prints median AND mean AND max
    AND the capped count per arm.
(b) POSITION BIAS. Both judges penalize prompt position C (Gemini
    added-content by letter A/B/C/D 0.51/0.48/0.70/0.53; Haiku
    0.88/0.89/1.63/0.73) and the recorded random shuffle put Cohere in C 32
    times against v2's 17. The second judge REPLAYED that shuffle, so the
    two judges' agreement was not independent of position either. FIX:
    `--balanced-positions` (Latin-square rotation, every arm in every
    position exactly 20 times over 80 windows) plus `--position-offset` for
    an independent rotation on the second judge. `position_table` in the
    summary prints the residual effect either way.
(c) DOUBLE COUNTING. Means were taken over 92 CALLS, so each of the 12
    repeat windows counted twice. Over the 80 unique windows Gemini's
    Cohere-vs-pipeline order FLIPS on added content (0.481 vs 0.444) and on
    wrong figures (0.113 vs 0.106). FIX: `arm_table` averages a window's
    passes first; the 92-call table is kept as a secondary section.
(d) GRANITE. 3 unique windows, all on Earnings-21 file 4387332, which
    Granite's own card puts in its training data. Dropped with
    `--skip-arm granite` rather than published as a 4-window row.

A FIFTH difference is not a defect in this script: run 4 reads every arm's
rows from ITN-NORMALIZED copies, because the two FluidAudio batch arms
rendered numbers as words ("eighty percent") while the pipeline, Cohere and
the reference rendered digits — a spelling difference the judge could see
and charge.

Run 4 (2026-09-03), first judge — fresh anchoring over the normalized arms:
  $PY scripts/bakeoff/judge_transcripts.py \\
      --arms parakeet_v3=<...>/swift_pipeline_2026-08-30T021253Z \\
             parakeet_v3_int8v2=<...>/bakeoff-itn/bakeoff-parakeet-v3-int8v2 \\
             parakeet_v2=<...>/bakeoff-itn/bakeoff-parakeet-v2 \\
             cohere=<...>/bakeoff-itn/audit-cohere-loopfix \\
      --balanced-positions --position-offset 0 --resume \\
      --out benchmark/output/bakeoff-judge-gemini-run4

Run 4, second judge — same excerpts verbatim, rotated one position:
  $PY scripts/bakeoff/judge_transcripts.py \\
      --provider openrouter --model anthropic/claude-haiku-4.5 \\
      --windows-from benchmark/output/bakeoff-judge-gemini-run4/grades.jsonl \\
      --balanced-positions --position-offset 1 --resume \\
      --out benchmark/output/bakeoff-judge-openrouter-claude-haiku-4.5-run2
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent  # scripts/
sys.path.insert(0, str(SCRIPTS_DIR))
import score_corpus_wer as scw  # noqa: E402  (reference/hypothesis/FILLERS/score/itn_lines)


# ─────────────────────────────────────────────────────────────────────────
# Corpus roster (task-specified default set)
# ─────────────────────────────────────────────────────────────────────────

EARNINGS21_IDS = [
    "4320211", "4341191", "4346818", "4359971", "4365024", "4366522",
    "4366893", "4367535", "4383161", "4384964", "4387332",
]
AMI_IDS = [
    "EN2002a", "EN2002b", "EN2006b", "ES2002a", "ES2004c", "ES2008c",
    "ES2013b", "ES2016a", "IS1000a", "IS1003b", "IS1006c", "IS1009a",
    "IS1009b", "TS3005a", "TS3009c", "TS3012b",
]
DEFAULT_FILE_IDS = EARNINGS21_IDS + AMI_IDS

WINDOW_SIZE = 150          # reference words per window (~60s of speech)
MIN_TAIL_WINDOW = 50       # a trailing remainder shorter than this merges into the previous window
MIN_WINDOW_FOR_JUDGING = 30  # a window smaller than this (short file) is dropped entirely


# ─────────────────────────────────────────────────────────────────────────
# API key — never printed, never logged, never put in a URL
# ─────────────────────────────────────────────────────────────────────────

def _repo_roots() -> list[Path]:
    """This worktree's root, then the MAIN checkout's root (`.env` is
    gitignored and only exists in the main checkout; mirrors
    `score_corpus_wer._data_root`'s git-common-dir resolution)."""
    roots = [SCRIPTS_DIR.parent]
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, check=True,
        ).stdout.strip()
        root = (SCRIPTS_DIR / common).resolve().parent
        if root not in roots:
            roots.append(root)
    except Exception:
        pass
    return roots


def _load_env_key(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value:
        return value
    for root in _repo_roots():
        env_path = root / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# Read once, checked LAZILY in `main` against the chosen --provider: an
# OpenRouter run must not require a Gemini key and vice versa. (This used to
# be a module-level `sys.exit`; the Gemini path still exits with the same
# message, just after argument parsing.)
GEMINI_API_KEY = _load_env_key("GEMINI_API_KEY")
OPENROUTER_API_KEY = _load_env_key("OPENROUTER_API_KEY")


# ─────────────────────────────────────────────────────────────────────────
# Model naming — same alias convention as scripts/test_transform.py
# ─────────────────────────────────────────────────────────────────────────

MODEL_ALIASES = {
    "flash-lite": "gemini-3.1-flash-lite",
    "flash35-lite": "gemini-3.5-flash-lite",
}
DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get(name, name)


# ─────────────────────────────────────────────────────────────────────────
# Reference: raw display tokens (AMI XML / earnings21 .nlp), kept separate
# from score_corpus_wer's NORMALIZED reference() — see module docstring.
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class RefToken:
    text: str          # raw, original casing
    speaker: str
    punc: Optional[str]  # trailing punctuation mark, or None


def _ami_raw_tokens(file_id: str) -> list[RefToken]:
    rows: list[tuple[float, RefToken]] = []
    for p in sorted(scw.AMI_WORDS.glob(f"{file_id}.*.words.xml")):
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
            mid = 0.5 * (float(st) + float(el.get("endtime") or st))
            mark = None
            if i + 1 < n and elems[i + 1].get("punc") == "true":
                m = (elems[i + 1].text or "").strip()
                mark = m or None
            rows.append((mid, RefToken(text=text, speaker=spk, punc=mark)))
            i += 1
    rows.sort(key=lambda r: r[0])
    return [tok for _, tok in rows]


def _e21_raw_tokens(file_id: str) -> list[RefToken] | None:
    p = scw.E21_REF / f"{file_id}.nlp"
    if not p.exists():
        return None
    out: list[RefToken] = []
    with p.open() as fh:
        for row in csv.DictReader(fh, delimiter="|"):
            tok = (row.get("token") or "").strip()
            if not tok:
                continue
            mark = (row.get("punctuation") or "").strip() or None
            out.append(RefToken(text=tok, speaker=row.get("speaker") or "?", punc=mark))
    return out


def load_ref_tokens(file_id: str) -> tuple[str, list[RefToken]] | None:
    """(corpus, raw display tokens), or None if this file has no reference."""
    ami = _ami_raw_tokens(file_id)
    if ami:
        return "ami", ami
    e21 = _e21_raw_tokens(file_id)
    if e21:
        return "earnings21", e21
    return None


def render_tokens(tokens: list[RefToken]) -> str:
    """Raw display text: punctuation attaches to its word, words space-joined."""
    pieces = [t.text + (t.punc or "") for t in tokens]
    return " ".join(pieces)


def _runs_for_tokens(tokens: list[RefToken]) -> list[str]:
    """Group a token span into runs of consecutive same-speaker text — the
    same grouping `score_corpus_wer.reference()` uses before ITN, so a run
    never usefully spans a speaker change."""
    runs: list[str] = []
    cur: list[str] = []
    cur_spk: Optional[str] = None
    for t in tokens:
        if cur and t.speaker != cur_spk:
            runs.append(" ".join(cur))
            cur = []
        cur_spk = t.speaker
        cur.append(t.text)
    if cur:
        runs.append(" ".join(cur))
    return runs


def itn_normalize_tokens(tokens: list[RefToken]) -> list[str]:
    """ITN-normalize a token span in ISOLATION: one `itn_lines` (one
    subprocess spawn of the mimicscribe binary) per call. Used only for a
    single ad-hoc window (see the module docstring's note on the window-
    boundary approximation this implies); `build_windows` below does NOT
    call this per window — it batches every window's runs into ONE spawn
    per file, because ~50 windows/file x 27 files x one spawn each measured
    at several minutes wall clock on a cold disk cache (each spawn pays a
    Swift process launch), even though the OUTPUT is cached forever by
    content hash afterwards.
    """
    out: list[str] = []
    for line in scw.itn_lines(_runs_for_tokens(tokens)):
        out.extend(scw.norm(line))
    return out


# ─────────────────────────────────────────────────────────────────────────
# Hypothesis: normalized word stream + which raw segment each word came from
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class ArmFile:
    norm_words: list[str]
    word_seg_idx: list[int]
    segments: list[dict]  # raw, time-sorted; segments[i]["text"] is what a reader sees


_ARM_FILE_CACHE: dict[tuple[Path, str], Optional[ArmFile]] = {}


def load_arm_file(arm_dir: Path, file_id: str) -> Optional[ArmFile]:
    key = (arm_dir, file_id)
    if key in _ARM_FILE_CACHE:
        return _ARM_FILE_CACHE[key]
    p = arm_dir / "per-file" / f"{file_id}_after_orphan.json"
    if not p.exists():
        _ARM_FILE_CACHE[key] = None
        return None
    d = json.loads(p.read_text())
    items = d.get("segments") or d.get("sentences") or []
    key_field = "startTime" if "segments" in d else "start"
    ordered = sorted(items, key=lambda s: s.get(key_field, 0.0))
    raw_texts = [s.get("text") or "" for s in ordered]
    itned = scw.itn_lines(raw_texts)
    norm_words: list[str] = []
    word_seg_idx: list[int] = []
    for i, line in enumerate(itned):
        ws = scw.norm(line)
        norm_words.extend(ws)
        word_seg_idx.extend([i] * len(ws))
    result = ArmFile(norm_words=norm_words, word_seg_idx=word_seg_idx, segments=ordered)
    _ARM_FILE_CACHE[key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────
# Windows
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class Window:
    file_id: str
    corpus: str
    window_index: int
    tokens: list[RefToken]
    ref_excerpt: str
    norm_ref_words: list[str]

    @property
    def window_id(self) -> str:
        return f"{self.file_id}#{self.window_index}"


def build_windows(file_id: str) -> list[Window]:
    """Chunk one file's reference into windows, ITN-normalizing all of them
    in a SINGLE `itn_lines` call (one subprocess spawn for the whole file):
    every window's runs are flattened into one big line list, split back up
    by the per-window run count afterwards. See `itn_normalize_tokens`'s
    docstring for why this matters (spawn cost, not correctness — the
    normalized text for a given run is identical either way)."""
    loaded = load_ref_tokens(file_id)
    if not loaded:
        return []
    corpus, tokens = loaded
    if not tokens:
        return []
    chunks: list[list[RefToken]] = [tokens[i:i + WINDOW_SIZE] for i in range(0, len(tokens), WINDOW_SIZE)]
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_TAIL_WINDOW:
        tail = chunks.pop()
        chunks[-1] = chunks[-1] + tail
    kept = [(idx, chunk) for idx, chunk in enumerate(chunks) if len(chunk) >= MIN_WINDOW_FOR_JUDGING]
    if not kept:
        return []

    per_window_runs = [_runs_for_tokens(chunk) for _, chunk in kept]
    flat_runs = [r for runs in per_window_runs for r in runs]
    flat_itned = scw.itn_lines(flat_runs) if flat_runs else []
    windows: list[Window] = []
    pos = 0
    for (idx, chunk), runs in zip(kept, per_window_runs):
        lines = flat_itned[pos:pos + len(runs)]
        pos += len(runs)
        norm_words: list[str] = []
        for line in lines:
            norm_words.extend(scw.norm(line))
        windows.append(Window(
            file_id=file_id, corpus=corpus, window_index=idx, tokens=chunk,
            ref_excerpt=render_tokens(chunk), norm_ref_words=norm_words,
        ))
    return windows


def sample_windows(windows_by_corpus: dict[str, dict[str, list[Window]]], per_corpus: int, seed: int) -> list[Window]:
    """Stratified across files within each corpus: round-robin one window per
    file (shuffled per-file order) until `per_corpus` is reached or the
    corpus is exhausted."""
    rng = random.Random(seed)
    selected: list[Window] = []
    for corpus in sorted(windows_by_corpus):
        by_file = windows_by_corpus[corpus]
        file_ids = sorted(by_file)
        shuffled = {}
        for fid in file_ids:
            lst = by_file[fid][:]
            rng.shuffle(lst)
            shuffled[fid] = lst
        picked: list[Window] = []
        col = 0
        while len(picked) < per_corpus:
            progressed = False
            for fid in file_ids:
                if col < len(shuffled[fid]):
                    picked.append(shuffled[fid][col])
                    progressed = True
                    if len(picked) >= per_corpus:
                        break
            if not progressed:
                break
            col += 1
        selected.extend(picked)
    return selected


# ─────────────────────────────────────────────────────────────────────────
# Anchoring a window into one arm's hypothesis
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class AnchorResult:
    excerpt: str
    confidence: float
    hyp_norm_words: list[str]
    hyp_span: tuple[int, int]
    seg_span: tuple[int, int]
    trim_removed_start: int
    trim_removed_end: int
    trim_fallback: bool
    excerpt_word_count: int
    excerpt_ratio: Optional[float]  # excerpt words / window's reference word count
    capped: bool                    # the hard cap fired (see `cap_excerpt`)
    pre_cap_word_count: int         # excerpt words BEFORE the cap
    pre_cap_ratio: Optional[float]  # ratio before the cap — what run 3 published


# Matching blocks more than this many hyp-words apart are treated as
# belonging to DIFFERENT locations in the hypothesis, not one contiguous
# span. Needed because `get_matching_blocks()` on conversational text finds
# plenty of genuine but SCATTERED single-word matches ("yeah", "okay", "so")
# throughout the whole file — measured 2026-09-01 on an AMI window: taking
# the naive min/max over every matched block stretched a 150-word window's
# span to 4,555 hyp words (confidence still read 0.82, computed from the
# SAME over-wide match set, so it did not catch its own failure). Set well
# above WINDOW_SIZE so a genuine span with insertions/deletions is never
# split, and well below "spans most of a 27-file corpus arm".
CLUSTER_GAP = WINDOW_SIZE * 4

# Production/batch names used by the trim-parity self-check and by the
# leak reporting in `write_summary` — the two runs of the SAME underlying
# model whose excerpt sizes must agree once trimming is correct.
PRODUCTION_ARM = "parakeet_v3"
PRODUCTION_BATCH_COUNTERPART = "parakeet_v3_int8v2"

# A trimmed excerpt more than this multiple of the reference window's own
# word count is reported as a possible leak (2026-09-01, second pass: the
# 5/4/3-gram earliest/latest boundary picker still opened onto a RECURRING
# n-gram inside a long production segment on Earnings21 — "uh the and",
# "in the quarter" — even though the anchored WORD span matched the batch
# arm to a handful of words. See `trim_excerpt_to_anchor`'s closest-match
# fix and `write_summary`'s "Excerpts exceeding" section).
EXCERPT_RATIO_LEAK = 1.5

# The HARD cap (2026-09-03, external review defect (a)). `_best_cluster` +
# `trim_excerpt_to_anchor` reduce the leak but do not bound it: run 3's
# >1.5x tail was 3 windows on the pipeline arm, 6 on the v3 batch arm, 12
# on v2 and 6 on Cohere, with maxima 4.25 / 4.09 / 4.13 / 10.39 — one
# Cohere excerpt (TS3012b#33) ran 1,558 words for a 150-word window. Every
# surplus word is content the reference window never contains, so the judge
# reads it as added content and the arm is charged for a HARNESS artifact.
# The published median (0.97 / 0.99) hid the tail entirely. See
# `cap_excerpt` for the rule.
DEFAULT_MAX_EXCERPT_RATIO = 1.5


def _best_cluster(blocks: list) -> list:
    """`blocks` are matching blocks in increasing (a, b) order (guaranteed
    by `get_matching_blocks`). Split wherever the gap in `b` exceeds
    CLUSTER_GAP, then return the cluster with the most matched words —
    i.e. the one contiguous region of the hypothesis this window's text
    actually lives in, not every place a common word also occurs."""
    clusters: list[list] = [[blocks[0]]]
    for prev, blk in zip(blocks, blocks[1:]):
        gap = blk.b - (prev.b + prev.size)
        if gap > CLUSTER_GAP:
            clusters.append([blk])
        else:
            clusters[-1].append(blk)
    return max(clusters, key=lambda c: sum(b.size for b in c))


def _flatten_raw_tokens(text: str) -> tuple[list[str], list[str], list[int]]:
    """Whitespace-split raw tokens (punctuation attached, original casing),
    plus a FLATTENED normalized-key stream and an owner index back to the
    raw token each key came from. Normalization here is per-token, with NO
    ITN pass — a raw token can still yield 0 keys (pure punctuation like
    "--") or more than 1 (a hyphenated compound like "non-GAAP" ->
    ["non", "gaap"]), so this cannot be a straight zip with `raw_tokens`;
    the owner index is what lets a match in key-space point back to an
    exact raw-token boundary."""
    raw_tokens = text.split()
    flat_keys: list[str] = []
    flat_owner: list[int] = []
    for i, tok in enumerate(raw_tokens):
        for k in scw.norm(tok):
            flat_keys.append(k)
            flat_owner.append(i)
    return raw_tokens, flat_keys, flat_owner


def _find_ngram_candidates(flat_keys: list[str], probe: list[str], max_mismatch: int = 1) -> list[int]:
    """Every index into `flat_keys` where `probe` matches within
    `max_mismatch` positions (ITN can merge or split number words, e.g.
    "twenty twenty" vs "2020", so an exact match is too strict right at a
    number boundary). Returns ALL matches, not just the first/last — a
    30s production segment routinely repeats a short n-gram ("uh the and",
    "in the quarter"), and picking earliest/latest blindly opens the
    excerpt onto the WIDEST such pair instead of the true occurrence
    (2026-09-01, second pass); the caller picks by proximity to an
    expected position instead."""
    plen = len(probe)
    if plen == 0 or len(flat_keys) < plen:
        return []
    out = []
    for start in range(0, len(flat_keys) - plen + 1):
        mismatches = sum(1 for a, b in zip(flat_keys[start:start + plen], probe) if a != b)
        if mismatches <= max_mismatch:
            out.append(start)
    return out


def _pick_boundary(flat_keys: list[str], flat_owner: list[int], probe_words: list[str],
                    expected_raw_pos: float, from_start: bool) -> Optional[tuple[int, int]]:
    """Try a 5-word boundary n-gram, then 4, then 3 (longer n-grams are
    exponentially less likely to recur inside one segment); among the
    matches at the first length that finds any, keep the one whose RAW
    TOKEN position (via `flat_owner`, not the raw `flat_keys` index — a
    raw token can own more than one flattened key) is CLOSEST to
    `expected_raw_pos`. Returns (flat_index, ngram_length) or None."""
    for plen in (5, 4, 3):
        if len(probe_words) < plen:
            continue
        probe = probe_words[:plen] if from_start else probe_words[-plen:]
        candidates = _find_ngram_candidates(flat_keys, probe)
        if candidates:
            best = min(candidates, key=lambda c: abs(flat_owner[c] - expected_raw_pos))
            return best, plen
    return None


def trim_excerpt_to_anchor(seg_text: str, hyp_norm_words: list[str],
                            expected_start_frac: float, expected_end_frac: float
                            ) -> tuple[str, int, int, bool]:
    """Trim a WHOLE-SEGMENT-CONCATENATED excerpt down to the anchored word
    span, so a long production-pipeline diarization segment (10-30s, can
    overlap another channel on AMI) doesn't hand the judge everything the
    segment said instead of just what the reference window covers.

    `expected_start_frac`/`expected_end_frac` are the anchor's fractional
    position (0..1) inside the concatenated segment range, computed by the
    caller from where `lo`/`hi` sit within the normalized words that range
    covers — the normalized-to-raw word-count ratio is close to 1 outside
    number spans, so scaling that fraction by the raw token count gives a
    good EXPECTED boundary position. `_pick_boundary` then picks, among
    every place the anchor's boundary n-gram recurs in the segment, the
    occurrence closest to that expected position — not the first or last
    occurrence, which on a long segment can be the wrong one entirely (a
    recurring "uh the and" opened the excerpt onto the whole segment even
    though the anchored WORD span itself was tight; 2026-09-01, second
    pass on Earnings21).

    Falls back to the UNTRIMMED whole-segment text — not a partial trim on
    only one side — whenever either boundary can't be found at all.

    Returns (excerpt, words_removed_at_start, words_removed_at_end, fell_back).
    """
    raw_tokens, flat_keys, flat_owner = _flatten_raw_tokens(seg_text)
    if not raw_tokens or not hyp_norm_words:
        return seg_text, 0, 0, True
    n_raw = len(raw_tokens)
    expected_start = expected_start_frac * n_raw
    expected_end = expected_end_frac * n_raw

    start_hit = _pick_boundary(flat_keys, flat_owner, hyp_norm_words, expected_start, from_start=True)
    end_hit = _pick_boundary(flat_keys, flat_owner, hyp_norm_words, expected_end, from_start=False)
    if start_hit is None or end_hit is None:
        return seg_text, 0, 0, True
    start_flat, _ = start_hit
    end_flat, end_plen = end_hit
    raw_start = flat_owner[start_flat]
    raw_end = flat_owner[end_flat + end_plen - 1]
    if raw_start > raw_end:
        return seg_text, 0, 0, True
    removed_start = raw_start
    removed_end = n_raw - 1 - raw_end
    excerpt = " ".join(raw_tokens[raw_start:raw_end + 1])
    return excerpt, removed_start, removed_end, False


def cap_excerpt(excerpt: str, ref_display_excerpt: str, ref_word_count: int,
                 max_ratio: float) -> tuple[str, bool]:
    """THE HARD CAP. After anchoring and trimming, an excerpt longer than
    `max_ratio` x the reference window's word count is cut down to the
    CONTIGUOUS run of exactly `ceil(max_ratio * ref_word_count)` raw excerpt
    tokens CENTERED on the anchor's best-matching region, clamped to the
    excerpt's own ends. Anything shorter than the cap is returned untouched
    — the cap only ever removes words, never adds or reorders them.

    "Best-matching region" is located exactly the way `anchor_window` locates
    a span: `difflib.SequenceMatcher` matching blocks (size >= 2, falling
    back to singletons) between the excerpt's per-token normalized keys and
    the reference window's, clustered by `_best_cluster`, and the centre is
    the midpoint of the winning cluster mapped back to a RAW token index
    through `flat_owner`. If no block matches at all the excerpt's own
    midpoint is used, so a badly-aligned excerpt is still bounded.

    The reference side is the RAW DISPLAY excerpt normalized per token (no
    ITN pass), not `Window.norm_ref_words`, so the identical rule runs in a
    fresh anchoring run and in a `--windows-from` replay, which has no
    normalized reference stream. The THRESHOLD, however, is the ITN-basis
    `ref_word_count` that `excerpt_ratio` is already reported against, so
    "capped" and "ratio > max_ratio" mean the same thing in the output.

    Why it exists (2026-09-03): `_best_cluster` (CLUSTER_GAP = 600 words)
    plus `trim_excerpt_to_anchor` bound the COMMON case and not the tail —
    run 3 still handed the judge a 1,558-word Cohere excerpt for a 150-word
    window. Surplus words are content the reference window does not contain,
    so the judge grades them as added content and the arm is charged for a
    harness artifact rather than for its transcription.
    """
    from difflib import SequenceMatcher
    if max_ratio <= 0 or ref_word_count <= 0:
        return excerpt, False
    raw_tokens, flat_keys, flat_owner = _flatten_raw_tokens(excerpt)
    n_raw = len(raw_tokens)
    max_words = math.ceil(max_ratio * ref_word_count)
    if n_raw <= max_words:
        return excerpt, False
    ref_keys = _flatten_raw_tokens(ref_display_excerpt)[1]
    center: Optional[float] = None
    if ref_keys and flat_keys:
        sm = SequenceMatcher(a=ref_keys, b=flat_keys, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size >= 2]
        if not blocks:
            blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
        if blocks:
            best = _best_cluster(blocks)
            lo = min(b.b for b in best)
            hi = min(max(b.b + b.size - 1 for b in best), len(flat_owner) - 1)
            center = 0.5 * (flat_owner[lo] + flat_owner[hi])
    if center is None:
        center = n_raw / 2.0
    start = int(round(center - max_words / 2.0))
    start = max(0, min(start, n_raw - max_words))
    return " ".join(raw_tokens[start:start + max_words]), True


def anchor_window(window: Window, armfile: ArmFile,
                   max_excerpt_ratio: float = DEFAULT_MAX_EXCERPT_RATIO) -> Optional[AnchorResult]:
    from difflib import SequenceMatcher
    ref = window.norm_ref_words
    if not ref or not armfile.norm_words:
        return None
    sm = SequenceMatcher(a=ref, b=armfile.norm_words, autojunk=False)
    # Single-word matches are the dominant source of scattered false
    # anchors (common short words/backchannels repeat everywhere); prefer
    # blocks of 2+ words and only fall back to singletons if that finds
    # nothing (e.g. a very short or badly garbled excerpt).
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 2]
    if not blocks:
        blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not blocks:
        return None
    best = _best_cluster(blocks)
    matched = sum(b.size for b in best)
    confidence = matched / len(ref)
    lo = min(b.b for b in best)
    hi = max(b.b + b.size - 1 for b in best)
    seg_lo = armfile.word_seg_idx[lo]
    seg_hi = armfile.word_seg_idx[min(hi, len(armfile.word_seg_idx) - 1)]
    whole_excerpt = " ".join((armfile.segments[i].get("text") or "").strip() for i in range(seg_lo, seg_hi + 1))
    hyp_norm_words = armfile.norm_words[lo:hi + 1]

    # Where lo/hi sit, as a FRACTION, inside the normalized words that the
    # seg_lo..seg_hi segment range covers — `word_seg_idx` is sorted, so
    # its span for one segment-index value is a contiguous bisect range.
    norm_range_start = bisect.bisect_left(armfile.word_seg_idx, seg_lo)
    norm_range_end = bisect.bisect_right(armfile.word_seg_idx, seg_hi) - 1
    range_len = max(1, norm_range_end - norm_range_start + 1)
    expected_start_frac = (lo - norm_range_start) / range_len
    expected_end_frac = (hi - norm_range_start + 1) / range_len

    excerpt, removed_start, removed_end, fell_back = trim_excerpt_to_anchor(
        whole_excerpt, hyp_norm_words, expected_start_frac, expected_end_frac)
    ref_n = len(window.norm_ref_words)
    pre_cap_word_count = len(excerpt.split())
    pre_cap_ratio = pre_cap_word_count / ref_n if ref_n else None
    excerpt, capped = cap_excerpt(excerpt, window.ref_excerpt, ref_n, max_excerpt_ratio)
    excerpt_word_count = len(excerpt.split())
    excerpt_ratio = excerpt_word_count / ref_n if ref_n else None
    return AnchorResult(
        excerpt=excerpt, confidence=confidence, hyp_norm_words=hyp_norm_words,
        hyp_span=(lo, hi + 1), seg_span=(seg_lo, seg_hi),
        trim_removed_start=removed_start, trim_removed_end=removed_end, trim_fallback=fell_back,
        excerpt_word_count=excerpt_word_count, excerpt_ratio=excerpt_ratio,
        capped=capped, pre_cap_word_count=pre_cap_word_count, pre_cap_ratio=pre_cap_ratio,
    )


def content_word_wer(ref_words: list[str], hyp_words: list[str]) -> tuple[float, int]:
    rf = [w for w in ref_words if w not in scw.FILLERS]
    hf = [w for w in hyp_words if w not in scw.FILLERS]
    s = scw.score(rf, hf)
    return s["wer"], s["n"]


# ─────────────────────────────────────────────────────────────────────────
# Judge prompt + schema
# ─────────────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_INSTRUCTION = """You are grading automatic speech recognition (ASR) transcript excerpts against a reference transcript of the same audio. You will see one REFERENCE excerpt and several labeled HYPOTHESIS excerpts (A, B, C, ...), one per ASR system. You do not know which system produced which excerpt.

For EACH hypothesis, count these as non-negative integers:
- wrong_figures: a number a reader would act on (dollar amount, percentage, date, quantity, count, phone/ticker/ID number) that differs from the reference's number. Count each distinct wrong figure once.
- wrong_names_terms: a proper name (person, company, product), place, or technical acronym/term that differs from the reference and would mislead a reader about who or what was mentioned.
- dropped_content: a word or phrase present in the reference whose absence in the hypothesis changes the meaning of what was said. Do NOT count a missing filler word, a missing repeated word, or a missing function word (a/the/and/of and similar) that carries no meaning on its own.
- added_content: a word or phrase in the hypothesis that the reference never says and that adds a claim, fact, or detail not actually spoken. Do NOT count added or missing punctuation.

Also give:
- readability: an integer 1 (unreadable) to 5 (reads as cleanly as the reference) for how easy the hypothesis is to read and understand on its own.
- note: one short sentence on the single most notable difference, or "no notable differences" if there is none.

THESE ARE NOT ERRORS, under any of the four counts above:
- Filler words and backchannels: "yeah", "um", "uh", "okay", "mm", "right", "well", "like", "you know", and similar, whether present, absent, or in a different amount.
- "gonna" vs "going to", "wanna" vs "want to", and similar casual contractions/expansions.
- British vs American spelling (e.g. "colour"/"color", "recognise"/"recognize").
- Punctuation differences of any kind (periods, commas, quotes, capitalization, dashes).
- A repeated word or stutter that both excerpts handle differently, as long as the underlying content is the same.

If a hypothesis excerpt is empty or clearly unrelated to the reference (a bad alignment, not a transcription error), still grade it: use high dropped_content, readability 1, and say so in the note.

Return grades for every hypothesis label you were given, in the order given."""

GRADE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "wrong_figures": {"type": "integer"},
        "wrong_names_terms": {"type": "integer"},
        "dropped_content": {"type": "integer"},
        "added_content": {"type": "integer"},
        "readability": {"type": "integer"},
        "note": {"type": "string"},
    },
    "propertyOrdering": [
        "label", "wrong_figures", "wrong_names_terms", "dropped_content",
        "added_content", "readability", "note",
    ],
    "required": [
        "label", "wrong_figures", "wrong_names_terms", "dropped_content",
        "added_content", "readability", "note",
    ],
}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"grades": {"type": "array", "items": GRADE_ITEM_SCHEMA}},
    "propertyOrdering": ["grades"],
    "required": ["grades"],
}

CRITERIA = ("wrong_figures", "wrong_names_terms", "dropped_content", "added_content")


def _openai_schema(node: dict) -> dict:
    """The SAME response schema, restated in the dialect an OpenAI-compatible
    `response_format: json_schema` host accepts: `propertyOrdering` is a
    Gemini-only key (a strict validator rejects the whole schema over it),
    and strict structured outputs require `additionalProperties: false` on
    every object. Field names, types and `required` are untouched, so the
    two providers are asked for the identical object."""
    out: dict = {}
    for k, v in node.items():
        if k == "propertyOrdering":
            continue
        if isinstance(v, dict):
            out[k] = _openai_schema(v)
        elif isinstance(v, list):
            out[k] = [_openai_schema(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    if out.get("type") == "object":
        out["additionalProperties"] = False
    return out


OPENAI_RESPONSE_SCHEMA = _openai_schema(RESPONSE_SCHEMA)


def escape_content(s: str) -> str:
    """Mirror PromptSanitizer.escapeContent — replace </ with < /."""
    return s.replace("</", "< /")


def wrap_tag(tag: str, content: str) -> str:
    return f"<{tag}>\n{escape_content(content)}\n</{tag}>"


def build_user_message(ref_excerpt: str, labeled_excerpts: list[tuple[str, str]]) -> str:
    parts = [wrap_tag("REFERENCE_EXCERPT", ref_excerpt)]
    for label, excerpt in labeled_excerpts:
        parts.append(wrap_tag(f"HYPOTHESIS_{label}", excerpt if excerpt.strip() else "(empty)"))
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────
# Rate-limited Gemini call
# ─────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Shared across worker threads: a global minimum spacing between call
    STARTS, doubled permanently the first time any call sees a 429."""

    def __init__(self, min_interval: float):
        self._lock = threading.Lock()
        self._min_interval = min_interval
        self._last_start = 0.0
        self._seen_429 = False

    def wait_slot(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_start)
            if wait > 0:
                sleep_for = wait
            else:
                sleep_for = 0.0
            self._last_start = max(now, self._last_start) + sleep_for
        if sleep_for > 0:
            time.sleep(sleep_for)

    def note_429(self) -> None:
        with self._lock:
            if not self._seen_429:
                self._seen_429 = True
                self._min_interval *= 2.0
                print(f"! first HTTP 429 seen — doubling min-interval to {self._min_interval:.2f}s "
                      f"for the rest of this run", file=sys.stderr)


class TokenTotal:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.prompt = 0
        self.candidates = 0
        self.total = 0

    def add(self, usage: dict) -> tuple[int, int]:
        p = int(usage.get("promptTokenCount") or 0)
        c = int(usage.get("candidatesTokenCount") or 0)
        t = int(usage.get("totalTokenCount") or (p + c))
        with self._lock:
            self.prompt += p
            self.candidates += c
            self.total += t
            return t, self.total


BACKOFF_BASE = 2.0
BACKOFF_CAP = 60.0
BACKOFF_TRIES = 8


def _gemini_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def call_gemini_judge(
    user_message: str,
    *,
    model: str,
    thinking_level: str,
    temperature: float,
    max_output_tokens: int,
    limiter: RateLimiter,
    timeout: float = 90.0,
) -> tuple[dict, dict, int]:
    """One rate-limited, retried judge call. Returns (parsed_json, usage, latency_ms).

    The API key is sent ONLY in the `x-goog-api-key` header — never in the
    URL, never in an f-string that gets printed, never in an exception
    message (HTTPError bodies from Google do not echo the request headers).
    """
    body = {
        "system_instruction": {"parts": [{"text": JUDGE_SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "thinkingConfig": {"thinkingLevel": thinking_level},
        },
    }
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    last_err: Optional[Exception] = None
    for attempt in range(1, BACKOFF_TRIES + 1):
        limiter.wait_slot()
        req = urllib.request.Request(_gemini_url(model), data=data, headers=headers)
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode()
            latency_ms = int((time.monotonic() - t0) * 1000)
            payload = json.loads(raw)
            candidates = payload.get("candidates") or []
            if not candidates:
                raise RuntimeError(f"no candidates (finishReason={payload.get('promptFeedback')})")
            parts = candidates[0].get("content", {}).get("parts", [])
            text_part = next((p for p in parts if "text" in p and "thought" not in p), None)
            if not text_part:
                raise RuntimeError("no text part in response")
            parsed = json.loads(text_part["text"])
            usage = payload.get("usageMetadata") or {}
            return parsed, usage, latency_ms
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()[:500]
            except Exception:
                pass
            retryable = e.code in (429, 503) or "RESOURCE_EXHAUSTED" in body_text
            if e.code == 429:
                limiter.note_429()
            last_err = RuntimeError(f"HTTP {e.code}: {body_text}")
            if not retryable or attempt == BACKOFF_TRIES:
                raise last_err
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            if attempt == BACKOFF_TRIES:
                raise
        delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** (attempt - 1)))
        delay += random.uniform(0, delay * 0.25)
        print(f"  retry {attempt}/{BACKOFF_TRIES} after {delay:.1f}s ({last_err})", file=sys.stderr)
        time.sleep(delay)
    raise last_err or RuntimeError("judge call failed with no captured error")


# ─────────────────────────────────────────────────────────────────────────
# Rate-limited OpenRouter call — the SECOND, non-Google judge
# ─────────────────────────────────────────────────────────────────────────
#
# Same system instruction, same user message, same response schema, same
# temperature, same limiter/backoff object as the Gemini path — only the
# transport and the wire dialect differ, so a difference in the grades is a
# difference between the two MODELS and not between two prompts.
#
# Reasoning is deliberately NOT requested (no `reasoning` field): the Gemini
# arm ran `thinkingLevel: minimal`, and an Anthropic model with no thinking
# block set is the nearest analogue. `parse_failures` counts every response
# whose body was not valid JSON of the expected shape after one fenced-code
# rescue; those rows are written with `grades: {}` and a `parse_error` note
# rather than silently dropped.

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class _Retry(Exception):
    """Internal control flow for a retryable HTTP-200 error envelope."""


class ParseFailures:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.n = 0

    def bump(self) -> int:
        with self._lock:
            self.n += 1
            return self.n


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[: -3]
    return t.strip()


def call_openrouter_judge(
    user_message: str,
    *,
    model: str,
    temperature: float,
    max_output_tokens: int,
    limiter: RateLimiter,
    timeout: float = 180.0,
) -> tuple[dict, dict, int]:
    """One rate-limited, retried judge call against an OpenAI-compatible
    chat-completions endpoint. Returns (parsed_json, usage-in-Gemini-shape,
    latency_ms) so every downstream consumer (TokenTotal, the row writer,
    the summary) is unchanged. Raises `ValueError` on an unparseable body,
    which the caller counts as a parse failure rather than a run failure.

    The API key travels only in the `Authorization` header — never in the
    URL, never printed, never in an exception message.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("no OPENROUTER_API_KEY (env var, or .env in this worktree "
                           "or the main checkout)")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "asr_grades", "strict": True,
                            "schema": OPENAI_RESPONSE_SCHEMA},
        },
    }
    data = json.dumps(body).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        # Attribution headers OpenRouter asks callers to send; no secrets.
        "HTTP-Referer": "https://mimicscribe.app",
        "X-Title": "mimicscribe ASR bake-off judge",
    }

    last_err: Optional[Exception] = None
    for attempt in range(1, BACKOFF_TRIES + 1):
        limiter.wait_slot()
        req = urllib.request.Request(OPENROUTER_URL, data=data, headers=headers)
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode()
            latency_ms = int((time.monotonic() - t0) * 1000)
            payload = json.loads(raw)
            # OpenRouter reports upstream failures with HTTP 200 + an `error`
            # object; treat it like the HTTP error it stands for.
            if payload.get("error") and not payload.get("choices"):
                err = payload["error"]
                code = err.get("code")
                last_err = RuntimeError(f"openrouter error {code}: {str(err.get('message'))[:300]}")
                if code in (429, 502, 503) and attempt < BACKOFF_TRIES:
                    if code == 429:
                        limiter.note_429()
                    raise _Retry()
                raise last_err
            choices = payload.get("choices") or []
            if not choices:
                raise RuntimeError("no choices in response")
            content = (choices[0].get("message") or {}).get("content") or ""
            u = payload.get("usage") or {}
            usage = {
                "promptTokenCount": u.get("prompt_tokens"),
                "candidatesTokenCount": u.get("completion_tokens"),
                "totalTokenCount": u.get("total_tokens"),
            }
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                try:
                    parsed = json.loads(_strip_code_fence(content))
                except json.JSONDecodeError:
                    raise ValueError(f"unparseable judge body (first 200 chars): {content[:200]!r}")
            if not isinstance(parsed, dict) or not isinstance(parsed.get("grades"), list):
                raise ValueError(f"judge body has no `grades` array: {content[:200]!r}")
            return parsed, usage, latency_ms
        except _Retry:
            pass
        except ValueError:
            raise
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()[:500]
            except Exception:
                pass
            retryable = e.code in (408, 429, 500, 502, 503, 504)
            if e.code == 429:
                limiter.note_429()
            last_err = RuntimeError(f"HTTP {e.code}: {body_text}")
            if not retryable or attempt == BACKOFF_TRIES:
                raise last_err
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            if attempt == BACKOFF_TRIES:
                raise
        delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** (attempt - 1)))
        delay += random.uniform(0, delay * 0.25)
        print(f"  retry {attempt}/{BACKOFF_TRIES} after {delay:.1f}s ({last_err})", file=sys.stderr)
        time.sleep(delay)
    raise last_err or RuntimeError("judge call failed with no captured error")


# ─────────────────────────────────────────────────────────────────────────
# One unit of work: a window judged once (pass 1 or pass 2/repeat)
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class ReplaySpec:
    """A judge call REPLAYED from a previous run's `grades.jsonl` (see
    `--windows-from`). Everything the judge reads is carried over rather
    than re-derived: the label -> arm map (so the blind letters are the
    SAME letters), each arm's excerpt verbatim, and the previous run's
    per-arm calibration block, which is a property of the anchoring and not
    of the judge. The only piece rebuilt is the REFERENCE excerpt, and it is
    rebuilt by the same pure token chunking that produced it (`render_tokens`
    over `tokens[i:i+WINDOW_SIZE]` with the short-tail merge) — no ITN, no
    binary, no arm directories, so a replay cannot drift with a rebuilt
    normalizer or a re-decoded corpus run."""
    label_of_arm: dict[str, str]
    local: dict[str, dict]
    skipped: dict[str, str]
    ref_word_count: int


@dataclass
class JudgeJob:
    window: Window
    pass_no: int
    shuffle_seed: int
    replay: Optional[ReplaySpec] = None
    # Latin-square rotation ordinal for this window when --balanced-positions
    # is on (see `latin_square_labels`); None = the legacy random shuffle.
    position_ordinal: Optional[int] = None


def latin_square_labels(arm_names: list[str], ordinal: int, offset: int) -> dict[str, str]:
    """BALANCED POSITIONS (2026-09-03, external review defect (b)).

    Assign the blind letters by a Latin-square rotation over the window's
    ordinal instead of by a random shuffle: with the run's arms in a fixed
    order (sorted by name, so it does not depend on the order of `--arms`),
    arm `i` takes position `(i + ordinal + offset) mod k`. Walking `ordinal`
    over the window list therefore gives every arm every position an equal
    number of times — 4 arms x 80 windows = 20 each, exactly, rather than
    the random shuffle run 3 actually drew, which put Cohere in position C
    32 times and Parakeet v2 there only 17.

    That mattered because BOTH judges penalize position C: on run 3's rows,
    Gemini's added-content mean by position was A 0.51 / B 0.48 / C 0.70 /
    D 0.53 and Haiku's A 0.88 / B 0.89 / C 1.63 / D 0.73. A per-arm mean
    over an unbalanced shuffle carries part of that positional penalty as
    if it were a property of the arm. And because the second judge REPLAYED
    the first judge's shuffle, the two judges' agreement was not independent
    of position either — hence `--position-offset`, which rotates the whole
    square by a fixed number of places so the second judge sees a DIFFERENT
    arm->letter map on every window while staying exactly as balanced.

    Returns {letter: arm_name}. Both passes of a repeated window get the
    same map on purpose: self-consistency should measure the judge repeating
    itself, not the judge reacting to a moved excerpt.
    """
    k = len(arm_names)
    if k == 0:
        return {}
    out: dict[str, str] = {}
    for i, name in enumerate(arm_names):
        pos = (i + ordinal + offset) % k
        out[chr(ord("A") + pos)] = name
    return out


def rebuild_ref_chunks(file_id: str) -> tuple[str, list[list[RefToken]]] | None:
    """`build_windows`'s chunking, WITHOUT the ITN pass — the reference
    excerpt a judge sees is `render_tokens(chunk)`, which never touches ITN;
    only `norm_ref_words` (anchoring + calibration WER) does. Keeping the two
    apart is what lets `--windows-from` reproduce a run's prompts on a
    machine with no `--itn-text` binary."""
    loaded = load_ref_tokens(file_id)
    if not loaded:
        return None
    corpus, tokens = loaded
    if not tokens:
        return None
    chunks = [tokens[i:i + WINDOW_SIZE] for i in range(0, len(tokens), WINDOW_SIZE)]
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_TAIL_WINDOW:
        tail = chunks.pop()
        chunks[-1] = chunks[-1] + tail
    return corpus, chunks


def load_replay_jobs(path: Path) -> list[JudgeJob]:
    """Rebuild the EXACT job list of a previous run from its `grades.jsonl`.

    Rows are replayed in file order. A row that made no call (empty
    `shuffle`) is replayed as a no-call row so the two runs' window sets
    stay identical. Refuses rather than guesses if a window id no longer
    resolves against the reference on disk, or if the reconstructed chunk's
    corpus disagrees with the recorded one."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        sys.exit(f"--windows-from {path}: no rows")
    cache: dict[str, tuple[str, list[list[RefToken]]] | None] = {}
    jobs: list[JudgeJob] = []
    for r in rows:
        fid = r["file_id"]
        try:
            idx = int(str(r["window_id"]).split("#", 1)[1])
        except (IndexError, ValueError):
            sys.exit(f"--windows-from: unparseable window_id {r['window_id']!r}")
        if fid not in cache:
            cache[fid] = rebuild_ref_chunks(fid)
        built = cache[fid]
        if built is None:
            sys.exit(f"--windows-from: no reference on disk for {fid} "
                     f"(window {r['window_id']}) — cannot reproduce that prompt")
        corpus, chunks = built
        if idx >= len(chunks):
            sys.exit(f"--windows-from: {r['window_id']} is past this file's {len(chunks)} "
                     f"window(s) — the reference data has changed since that run")
        if corpus != r["corpus"]:
            sys.exit(f"--windows-from: {r['window_id']} rebuilds as corpus {corpus!r}, "
                     f"recorded as {r['corpus']!r}")
        chunk = chunks[idx]
        window = Window(file_id=fid, corpus=corpus, window_index=idx, tokens=chunk,
                        ref_excerpt=render_tokens(chunk), norm_ref_words=[])
        shuffle = r.get("shuffle") or {}
        local = {name: dict(d) for name, d in (r.get("local") or {}).items()}
        missing = [n for n in shuffle.values() if n not in local or "excerpt" not in local[n]]
        if missing:
            sys.exit(f"--windows-from: {r['window_id']} pass={r['pass']} has no stored "
                     f"excerpt for {missing} — that run cannot be replayed")
        jobs.append(JudgeJob(
            window=window, pass_no=int(r["pass"]), shuffle_seed=0,
            replay=ReplaySpec(label_of_arm=dict(shuffle), local=local,
                              skipped=dict(r.get("skipped_arms") or {}),
                              ref_word_count=int(r.get("ref_word_count") or 0)),
        ))
    return jobs


def prepare_call(job: JudgeJob, arms: dict[str, Path], min_confidence: float,
                  max_excerpt_ratio: float, position_offset: int
                  ) -> tuple[dict[str, str], dict[str, dict], dict[str, str]]:
    """Returns (label -> arm_name, arm_name -> local calibration dict,
    arm_name -> skip reason) for the arms actually usable in this window.

    Positions come from `latin_square_labels` when `job.position_ordinal` is
    set (`--balanced-positions`) and from the legacy per-window random
    shuffle otherwise. An arm that cannot be anchored into this window is
    dropped from the map and the survivors are RE-LETTERED contiguously in
    their rotated order, so the judge always sees A, B, C, ... with no gap
    and the rotation still decides who is where.
    """
    if job.position_ordinal is not None:
        rotated = latin_square_labels(sorted(arms), job.position_ordinal, position_offset)
        names = [rotated[chr(ord("A") + i)] for i in range(len(rotated))]
    else:
        rng = random.Random(job.shuffle_seed)
        names = list(arms)
        rng.shuffle(names)
    labels = [chr(ord("A") + i) for i in range(len(names))]

    label_of_arm: dict[str, str] = {}
    local: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    label_iter = iter(labels)
    for name in names:
        armfile = load_arm_file(arms[name], job.window.file_id)
        if armfile is None:
            skipped[name] = "no per-file dump for this file"
            continue
        anchor = anchor_window(job.window, armfile, max_excerpt_ratio)
        if anchor is None:
            skipped[name] = "no matching text block against this arm's hypothesis"
            continue
        if anchor.confidence < min_confidence:
            skipped[name] = f"anchor confidence {anchor.confidence:.2f} < {min_confidence}"
            continue
        label = next(label_iter)
        label_of_arm[label] = name
        wer, n = content_word_wer(job.window.norm_ref_words, anchor.hyp_norm_words)
        local[name] = {
            "excerpt": anchor.excerpt,
            "confidence": round(anchor.confidence, 4),
            "content_word_wer": round(wer, 4),
            "content_word_n": n,
            "hyp_span": list(anchor.hyp_span),
            "seg_span": list(anchor.seg_span),
            "trim_removed_start": anchor.trim_removed_start,
            "trim_removed_end": anchor.trim_removed_end,
            "trim_fallback": anchor.trim_fallback,
            "excerpt_word_count": anchor.excerpt_word_count,
            "excerpt_ratio": round(anchor.excerpt_ratio, 4) if anchor.excerpt_ratio is not None else None,
            "capped": anchor.capped,
            "pre_cap_word_count": anchor.pre_cap_word_count,
            "pre_cap_ratio": round(anchor.pre_cap_ratio, 4) if anchor.pre_cap_ratio is not None else None,
        }
    return label_of_arm, local, skipped


def run_job(job: JudgeJob, arms: dict[str, Path], args: argparse.Namespace,
            limiter: RateLimiter, tokens: TokenTotal,
            parse_failures: ParseFailures) -> dict:
    if job.replay is not None:
        label_of_arm = dict(job.replay.label_of_arm)
        local = {name: dict(d) for name, d in job.replay.local.items()}
        skipped = dict(job.replay.skipped)
        ref_word_count = job.replay.ref_word_count
        # A replay carries every arm's EXCERPT verbatim (that is the point:
        # two judges must read byte-identical text). What it may re-decide
        # is which LETTER each arm wears — `--balanced-positions
        # --position-offset N` rotates the square so the second judge sees a
        # different map on every window while both stay balanced.
        if job.position_ordinal is not None:
            names = sorted(label_of_arm.values())
            rotated = latin_square_labels(names, job.position_ordinal, args.position_offset)
            label_of_arm = {chr(ord("A") + i): rotated[chr(ord("A") + i)]
                            for i in range(len(rotated))}
        if args.recap_replay:
            for name, d in local.items():
                text = d.get("excerpt") or ""
                pre_n = len(text.split())
                text, capped = cap_excerpt(text, job.window.ref_excerpt,
                                           ref_word_count, args.max_excerpt_ratio)
                d["excerpt"] = text
                d["pre_cap_word_count"] = pre_n
                d["pre_cap_ratio"] = round(pre_n / ref_word_count, 4) if ref_word_count else None
                d["excerpt_word_count"] = len(text.split())
                d["excerpt_ratio"] = (round(len(text.split()) / ref_word_count, 4)
                                      if ref_word_count else None)
                d["capped"] = capped
    else:
        label_of_arm, local, skipped = prepare_call(
            job, arms, args.min_confidence, args.max_excerpt_ratio, args.position_offset)
        ref_word_count = len(job.window.norm_ref_words)
    ts = datetime.now(timezone.utc).isoformat()
    if not label_of_arm:
        return {
            "window_id": job.window.window_id, "pass": job.pass_no,
            "position_ordinal": job.position_ordinal,
            "position_scheme": ("balanced" if job.position_ordinal is not None else "shuffle"),
            "position_offset": args.position_offset,
            "file_id": job.window.file_id, "corpus": job.window.corpus,
            "ref_word_count": ref_word_count,
            "shuffle": {}, "skipped_arms": skipped, "grades": {}, "local": {},
            "usage": None, "model": None, "latency_ms": 0, "timestamp": ts,
            "note": "no arm could be anchored into this window — no call made",
        }
    # Explicitly by LETTER: the prompt must read A, B, C, D in order however
    # the map was built (rotation, replay, or legacy shuffle).
    labeled_excerpts = [(label, local[label_of_arm[label]]["excerpt"])
                        for label in sorted(label_of_arm)]
    user_message = build_user_message(job.window.ref_excerpt, labeled_excerpts)
    parse_error: Optional[str] = None
    if args.provider == "openrouter":
        try:
            parsed, usage, latency_ms = call_openrouter_judge(
                user_message, model=args.model_resolved, temperature=args.temperature,
                max_output_tokens=args.max_output_tokens, limiter=limiter,
            )
        except ValueError as e:
            n = parse_failures.bump()
            parse_error = str(e)[:400]
            print(f"  ! [{job.window.window_id} pass={job.pass_no}] parse failure "
                  f"#{n}: {parse_error}", file=sys.stderr)
            return {
                "window_id": job.window.window_id, "pass": job.pass_no,
            "position_ordinal": job.position_ordinal,
            "position_scheme": ("balanced" if job.position_ordinal is not None else "shuffle"),
            "position_offset": args.position_offset,
                "file_id": job.window.file_id, "corpus": job.window.corpus,
                "ref_word_count": ref_word_count,
                "shuffle": label_of_arm, "skipped_arms": skipped, "grades": {},
                "local": {name: dict(d) for name, d in local.items()},
                "usage": None, "model": args.model_resolved, "latency_ms": 0,
                "timestamp": ts, "parse_error": parse_error,
            }
    else:
        parsed, usage, latency_ms = call_gemini_judge(
            user_message, model=args.model_resolved, thinking_level=args.thinking,
            temperature=args.temperature, max_output_tokens=args.max_output_tokens,
            limiter=limiter,
        )
    call_tokens, cum = tokens.add(usage)
    grades_by_label = {g.get("label"): g for g in parsed.get("grades", []) if isinstance(g, dict)}
    grades_by_arm: dict[str, dict] = {}
    for label, name in label_of_arm.items():
        g = grades_by_label.get(label)
        if g is None:
            skipped[name] = "judge did not return a grade for this label"
            continue
        grades_by_arm[name] = {k: g.get(k) for k in ("wrong_figures", "wrong_names_terms",
                                                       "dropped_content", "added_content",
                                                       "readability", "note")}
    # `excerpt` text is KEPT here (not stripped) — the excerpt-ratio leak
    # report needs to print it verbatim for windows over EXCERPT_RATIO_LEAK,
    # and re-deriving it later would mean re-running the anchor+trim pass
    # against a possibly-changed corpus run.
    local_out = {name: dict(d) for name, d in local.items() if name in grades_by_arm}
    print(f"  [{job.window.window_id} pass={job.pass_no}] +{call_tokens} tok (cum {cum}) "
          f"arms={list(grades_by_arm)} skipped={list(skipped)}")
    return {
        "window_id": job.window.window_id, "pass": job.pass_no,
            "position_ordinal": job.position_ordinal,
            "position_scheme": ("balanced" if job.position_ordinal is not None else "shuffle"),
            "position_offset": args.position_offset,
        "file_id": job.window.file_id, "corpus": job.window.corpus,
        "ref_word_count": ref_word_count,
        "shuffle": label_of_arm, "skipped_arms": skipped,
        "grades": grades_by_arm, "local": local_out,
        "usage": {"prompt_tokens": usage.get("promptTokenCount"),
                  "candidates_tokens": usage.get("candidatesTokenCount"),
                  "total_tokens": usage.get("totalTokenCount")},
        "model": args.model_resolved, "latency_ms": latency_ms, "timestamp": ts,
    }


# ─────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def _percentile(sorted_vals: list[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def excerpt_ratio_report(rows: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    """Per arm: n / mean / median / p90 / max of `excerpt_ratio` (excerpt
    words / reference window words) plus a count of trim fallbacks. Also
    every (window, pass, arm) row whose ratio exceeds EXCERPT_RATIO_LEAK —
    a still-too-wide excerpt, reported rather than silently accepted, since
    the 2026-09-01 defect was found exactly this way (production's ratio
    sitting far above every batch arm's on the same window)."""
    per_arm: dict[str, list[float]] = {}
    fallback_n: dict[str, int] = {}
    capped_n: dict[str, int] = {}
    pre_cap_max: dict[str, float] = {}
    leaks: list[dict] = []
    for r in rows:
        for arm, loc in r.get("local", {}).items():
            if loc.get("capped"):
                capped_n[arm] = capped_n.get(arm, 0) + 1
            pcr = loc.get("pre_cap_ratio")
            if pcr is not None:
                pre_cap_max[arm] = max(pre_cap_max.get(arm, 0.0), pcr)
            if loc.get("trim_fallback"):
                fallback_n[arm] = fallback_n.get(arm, 0) + 1
                continue
            ratio = loc.get("excerpt_ratio")
            if ratio is None:
                continue
            per_arm.setdefault(arm, []).append(ratio)
            # A CAPPED cell always lands ON the cap (`ceil` of a ratio taken
            # against the ITN word count, measured against the raw one), so
            # it would list here as a 1.50 "leak" forever. It is accounted
            # for by `capped` and `pre_cap_max`; a LEAK is a cell the cap did
            # not reach.
            if ratio > EXCERPT_RATIO_LEAK and not loc.get("capped"):
                leaks.append({
                    "window_id": r["window_id"], "pass": r["pass"], "arm": arm,
                    "ratio": ratio, "excerpt_word_count": loc.get("excerpt_word_count"),
                    "ref_word_count": r.get("ref_word_count"),
                })
    stats: dict[str, dict] = {}
    for arm, vals in per_arm.items():
        sv = sorted(vals)
        stats[arm] = {
            "n": len(sv), "fallbacks": fallback_n.get(arm, 0),
            "capped": capped_n.get(arm, 0), "pre_cap_max": pre_cap_max.get(arm),
            "mean": _mean(sv), "median": _percentile(sv, 0.5),
            "p90": _percentile(sv, 0.9), "max": sv[-1],
        }
    for arm in set(fallback_n) | set(capped_n):
        stats.setdefault(arm, {"n": 0, "fallbacks": fallback_n.get(arm, 0),
                                "capped": capped_n.get(arm, 0),
                                "pre_cap_max": pre_cap_max.get(arm),
                                "mean": None, "median": None, "p90": None, "max": None})
    return stats, leaks


def print_excerpt_ratio_report(rows: list[dict]) -> None:
    stats, leaks = excerpt_ratio_report(rows)
    print("excerpt ratio (excerpt words / reference window words), per arm:")
    for arm in sorted(stats):
        s = stats[arm]
        pcm = s.get("pre_cap_max")
        tail = (f" capped={s.get('capped', 0)}"
                + (f" pre-cap max={pcm:.3f}" if pcm is not None else ""))
        if s["n"] == 0:
            print(f"  {arm}: n=0 fallbacks={s['fallbacks']}{tail}")
            continue
        print(f"  {arm}: n={s['n']} fallbacks={s['fallbacks']} "
              f"mean={s['mean']:.3f} median={s['median']:.3f} p90={s['p90']:.3f} "
              f"max={s['max']:.3f}{tail}")
    if not leaks:
        print(f"no window exceeded {EXCERPT_RATIO_LEAK}x the reference window's word count")
        return
    print(f"{len(leaks)} (window, arm) pair(s) exceeded {EXCERPT_RATIO_LEAK}x:")
    for lk in leaks:
        print(f"  {lk['window_id']} pass={lk['pass']} {lk['arm']}: "
              f"ratio={lk['ratio']:.2f} ({lk['excerpt_word_count']}w vs ref {lk['ref_word_count']}w)")
    prod_leaks = [lk for lk in leaks if lk["arm"] == PRODUCTION_ARM]
    if prod_leaks:
        print(f"{PRODUCTION_ARM} (production) still leaks on {len(prod_leaks)} window(s) — "
              f"excerpts for both arms follow:")
        by_window: dict[tuple[str, int], dict] = {(r["window_id"], r["pass"]): r for r in rows}
        for lk in prod_leaks:
            r = by_window.get((lk["window_id"], lk["pass"]))
            if not r:
                continue
            prod_loc = r.get("local", {}).get(PRODUCTION_ARM, {})
            batch_loc = r.get("local", {}).get(PRODUCTION_BATCH_COUNTERPART, {})
            print(f"--- {lk['window_id']} pass={lk['pass']} ---")
            print(f"  {PRODUCTION_ARM} ({prod_loc.get('excerpt_word_count')}w): {prod_loc.get('excerpt', '')[:800]}")
            if batch_loc:
                print(f"  {PRODUCTION_BATCH_COUNTERPART} ({batch_loc.get('excerpt_word_count')}w): "
                      f"{batch_loc.get('excerpt', '')[:800]}")


def spearman(xs: list[float], ys: list[float]) -> Optional[float]:
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
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg_rank
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


def write_summary(rows: list[dict], out_path: Path, args: argparse.Namespace) -> None:
    arms_seen: set[str] = set()
    for r in rows:
        arms_seen.update(r.get("grades", {}))
    arms_seen_sorted = sorted(arms_seen)

    def arm_table(subset: list[dict], per_window: bool = True) -> str:
        """Per-arm means. PRIMARY basis is per UNIQUE WINDOW (2026-09-03,
        external review defect (c)): a window graded twice contributed TWICE
        to the published run-3 means, so the 12 repeat windows carried 1.15x
        the weight of the other 68. Averaging a window's passes first and
        then averaging over windows removes that weighting — and it MOVED an
        ordering: Gemini's added-content read Cohere 0.424 vs pipeline 0.435
        over 92 calls and Cohere 0.481 vs pipeline 0.444 over 80 windows.
        `per_window=False` reproduces the old 92-call basis, published
        alongside as a secondary field."""
        unit = "windows" if per_window else "calls"
        lines = ["| arm | n " + unit + " | " + " | ".join(f"mean {c}" for c in CRITERIA)
                 + " | mean readability |",
                 "|---" * (2 + len(CRITERIA) + 1) + "|"]
        for arm in arms_seen_sorted:
            if per_window:
                by_w: dict[str, list[dict]] = {}
                for r in subset:
                    if arm in r.get("grades", {}):
                        by_w.setdefault(r["window_id"], []).append(r["grades"][arm])
                if not by_w:
                    continue
                groups = list(by_w.values())
            else:
                vals = [r["grades"][arm] for r in subset if arm in r.get("grades", {})]
                if not vals:
                    continue
                groups = [[v] for v in vals]
            cells = [arm, str(len(groups))]
            for c in CRITERIA + ("readability",):
                per_group = [_mean([v[c] for v in g if isinstance(v.get(c), (int, float))])
                             for g in groups]
                m = _mean([x for x in per_group if x is not None])
                cells.append(f"{m:.2f}" if m is not None else "n/a")
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def position_table(subset: list[dict]) -> str:
        """Mean grade by PROMPT POSITION (the blind letter), pooled over
        arms — the residual position effect. Run 3 read Gemini added-content
        A 0.51 / B 0.48 / C 0.70 / D 0.53 and Haiku A 0.88 / B 0.89 / C 1.63
        / D 0.73, on a shuffle that put one arm in C nearly twice as often as
        another. Balanced positions do not remove the effect; they stop it
        from landing unevenly on the arms."""
        letters = sorted({L for r in subset for L in (r.get("shuffle") or {})})
        lines = ["| criterion | " + " | ".join(letters) + " |",
                 "|---" * (1 + len(letters)) + "|"]
        for c in CRITERIA + ("readability",):
            cells = [c]
            for L in letters:
                vals = []
                for r in subset:
                    arm = (r.get("shuffle") or {}).get(L)
                    g = (r.get("grades") or {}).get(arm) if arm else None
                    if g and isinstance(g.get(c), (int, float)):
                        vals.append(g[c])
                m = _mean(vals)
                cells.append(f"{m:.2f} (n={len(vals)})" if m is not None else "n/a")
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    # self-consistency: pair pass=1 and pass=2 rows sharing a window_id, per arm
    by_window_pass: dict[tuple[str, int], dict] = {(r["window_id"], r["pass"]): r for r in rows}
    window_ids_with_repeat = {r["window_id"] for r in rows if r["pass"] == 2}
    consist_lines = []
    for c in CRITERIA + ("readability",):
        diffs: list[float] = []
        exact = 0
        total = 0
        for wid in window_ids_with_repeat:
            r1, r2 = by_window_pass.get((wid, 1)), by_window_pass.get((wid, 2))
            if not r1 or not r2:
                continue
            for arm in set(r1.get("grades", {})) & set(r2.get("grades", {})):
                v1, v2 = r1["grades"][arm].get(c), r2["grades"][arm].get(c)
                if not isinstance(v1, (int, float)) or not isinstance(v2, (int, float)):
                    continue
                total += 1
                if v1 == v2:
                    exact += 1
                diffs.append(abs(v1 - v2))
        if total:
            consist_lines.append(f"| {c} | {total} | {exact / total:.0%} | {_mean(diffs):.2f} |")
        else:
            consist_lines.append(f"| {c} | 0 | n/a | n/a |")

    # spearman: judge error total vs local content-word WER, per (window,arm,pass) row
    xs, ys = [], []
    for r in rows:
        for arm, g in r.get("grades", {}).items():
            loc = r.get("local", {}).get(arm)
            if not loc or "content_word_wer" not in loc:
                continue
            total_errors = sum(g.get(c) or 0 for c in CRITERIA if isinstance(g.get(c), (int, float)))
            xs.append(total_errors)
            ys.append(loc["content_word_wer"])
    rho = spearman(xs, ys)

    lines = [
        "# Bake-off judge summary", "",
        f"Generated {datetime.now(timezone.utc).isoformat()} — provider `{args.provider}`, "
        f"model `{args.model_resolved}`, "
        + (f"thinking `{args.thinking}`, " if args.provider == "gemini" else "no reasoning block, ")
        + f"temperature {args.temperature}."
        + (f" Windows replayed from `{args.windows_from}`." if args.windows_from else ""),
        f"Windows judged: {len({r['window_id'] for r in rows})}; judge calls: {len(rows)}; "
        f"parse failures: {sum(1 for r in rows if r.get('parse_error'))}.",
        (f"Excerpt cap: {'off' if args.max_excerpt_ratio <= 0 else f'{args.max_excerpt_ratio}x'}"
         f" the reference window. Positions: "
         + ("balanced Latin square, offset " + str(args.position_offset)
            if args.balanced_positions else "random per-window shuffle")
         + (f". Arms dropped: {', '.join(args.skip_arm)}." if args.skip_arm else ".")),
        "", "## Overall (per unique window — the published basis)", "",
        arm_table(rows), "",
        "## Overall (per judge call — secondary, double-counts repeat windows)", "",
        arm_table(rows, per_window=False), "",
        "## Position effect (mean by prompt letter, pooled over arms)", "",
        position_table(rows), "",
        "## Per corpus (per unique window)", "",
    ]
    for corpus in sorted({r["corpus"] for r in rows}):
        subset = [r for r in rows if r["corpus"] == corpus]
        lines += [f"### {corpus}", "", arm_table(subset), ""]
    # excerpt trim (raw whole-segment text -> anchored word span; see
    # `trim_excerpt_to_anchor`): per arm, how many raw words were cut off
    # each end, and how often no boundary was found so the whole segment
    # was kept untrimmed.
    trim_rows: dict[str, list[dict]] = {}
    for r in rows:
        for arm, loc in r.get("local", {}).items():
            if "trim_removed_start" not in loc:
                continue
            trim_rows.setdefault(arm, []).append(loc)
    trim_lines = ["| arm | n | mean removed (start) | mean removed (end) | fallbacks |",
                  "|---|---|---|---|---|"]
    for arm in sorted(trim_rows):
        recs = trim_rows[arm]
        n = len(recs)
        fb = sum(1 for d in recs if d.get("trim_fallback"))
        ms = _mean([d["trim_removed_start"] for d in recs])
        me = _mean([d["trim_removed_end"] for d in recs])
        trim_lines.append(f"| {arm} | {n} | {ms:.1f} | {me:.1f} | {fb} ({fb / n:.0%}) |")

    lines += [
        "## Self-consistency (pass 1 vs pass 2, repeated windows)", "",
        "| criterion | n pairs | exact match | mean abs diff |", "|---|---|---|---|",
        *consist_lines, "",
        "## Judge error total vs local content-word WER", "",
        f"Spearman rho = {rho:.3f} (n={len(xs)})" if rho is not None else f"n/a (n={len(xs)})",
        "",
        "## Excerpt trim (whole segment -> anchored span)", "",
        *trim_lines, "",
    ]

    ratio_stats, ratio_leaks = excerpt_ratio_report(rows)
    ratio_lines = ["| arm | n | fallbacks | capped | mean | median | p90 | max | pre-cap max |",
                   "|---|---|---|---|---|---|---|---|---|"]
    for arm in sorted(ratio_stats):
        s = ratio_stats[arm]
        pcm = s.get("pre_cap_max")
        pcm_s = f"{pcm:.3f}" if pcm is not None else "n/a"
        if s["n"] == 0:
            ratio_lines.append(f"| {arm} | 0 | {s['fallbacks']} | {s.get('capped', 0)} | "
                                f"n/a | n/a | n/a | n/a | {pcm_s} |")
        else:
            ratio_lines.append(f"| {arm} | {s['n']} | {s['fallbacks']} | {s.get('capped', 0)} | "
                                f"{s['mean']:.3f} | {s['median']:.3f} | {s['p90']:.3f} | "
                                f"{s['max']:.3f} | {pcm_s} |")
    lines += [
        "## Excerpt ratio (excerpt words / reference window words)", "",
        *ratio_lines, "",
        f"## Excerpts exceeding {EXCERPT_RATIO_LEAK}x the reference window", "",
    ]
    if not ratio_leaks:
        lines.append(f"(none — no window/arm exceeded {EXCERPT_RATIO_LEAK}x)")
    else:
        lines.append("| window | pass | arm | ratio | excerpt words | ref words |")
        lines.append("|---|---|---|---|---|---|")
        for lk in ratio_leaks:
            lines.append(f"| {lk['window_id']} | {lk['pass']} | {lk['arm']} | {lk['ratio']:.2f} | "
                         f"{lk['excerpt_word_count']} | {lk['ref_word_count']} |")
        lines.append("")
        prod_leaks = [lk for lk in ratio_leaks if lk["arm"] == PRODUCTION_ARM]
        if prod_leaks:
            lines += ["", f"### {PRODUCTION_ARM} (production) still leaks — excerpts for both arms", ""]
            by_window: dict[tuple[str, int], dict] = {(r["window_id"], r["pass"]): r for r in rows}
            for lk in prod_leaks:
                r = by_window.get((lk["window_id"], lk["pass"]))
                if not r:
                    continue
                prod_loc = r.get("local", {}).get(PRODUCTION_ARM, {})
                batch_loc = r.get("local", {}).get(PRODUCTION_BATCH_COUNTERPART, {})
                lines.append(f"**{lk['window_id']} pass={lk['pass']}**")
                lines.append(f"- `{PRODUCTION_ARM}` ({prod_loc.get('excerpt_word_count')}w): "
                              f"{prod_loc.get('excerpt', '')}")
                if batch_loc:
                    lines.append(f"- `{PRODUCTION_BATCH_COUNTERPART}` ({batch_loc.get('excerpt_word_count')}w): "
                                  f"{batch_loc.get('excerpt', '')}")
                lines.append("")

    lines += ["## Skipped arms (by reason, first 20)", ""]
    skip_examples: list[str] = []
    for r in rows:
        for arm, reason in r.get("skipped_arms", {}).items():
            skip_examples.append(f"- {r['window_id']} pass={r['pass']} `{arm}`: {reason}")
    lines += skip_examples[:20] if skip_examples else ["(none)"]
    out_path.write_text("\n".join(lines) + "\n")


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────

def parse_arms(pairs: list[str]) -> dict[str, Path]:
    arms: dict[str, Path] = {}
    for pair in pairs:
        if "=" not in pair:
            sys.exit(f"--arms entries must be NAME=PATH, got: {pair!r}")
        name, path = pair.split("=", 1)
        arms[name] = Path(path)
    if len(arms) < 2:
        sys.exit("need at least 2 --arms to judge blind (need something to compare)")
    return arms


def self_check_trim_parity(arms: dict[str, Path]) -> None:
    """One-shot sanity check for the whole-segment-excerpt trim defect (fixed
    2026-09-01): the production arm's `_after_orphan.json` rows are long
    diarization segments (10-30s, can overlap another channel on AMI) while
    the batch arms' rows are short per-utterance chunks, so an UNTRIMMED
    excerpt let the production arm's excerpt run far past a batch arm's for
    the same window even though both anchor to the same word span. Compares
    `parakeet_v3` (production) against `parakeet_v3_int8v2` (its batch
    counterpart, same underlying model) when both are present in `--arms`.

    Trimming only tightens a WHOLE-SEGMENT excerpt down to an already-chosen
    anchor span — it cannot fix a genuinely wide anchor (repetitive
    backchannel-heavy AMI dialogue occasionally clusters the matching
    blocks too loosely, a separate, pre-existing anchoring-quality question
    from the one this fix addresses). So this scans a handful of windows
    for one where BOTH arms anchor reasonably tightly (hyp_span within 3x
    the window's own word count) before comparing excerpt word counts —
    otherwise a coincidentally hard window would fail the check for a
    reason unrelated to the trim. Prints PASS/FAIL either way; never aborts
    the run (diagnostic, not a gate)."""
    prod, batch = "parakeet_v3", "parakeet_v3_int8v2"
    if prod not in arms or batch not in arms:
        return
    prod_dir, batch_dir = arms[prod], arms[batch]
    for ami_file in AMI_IDS:
        loaded = load_ref_tokens(ami_file)
        if not loaded:
            continue
        wins = build_windows(ami_file)
        prod_file = load_arm_file(prod_dir, ami_file)
        batch_file = load_arm_file(batch_dir, ami_file)
        if not prod_file or not batch_file:
            continue
        for window in wins:
            a_prod = anchor_window(window, prod_file)
            a_batch = anchor_window(window, batch_file)
            if not a_prod or not a_batch:
                continue
            nref = len(window.norm_ref_words)
            tight = (a_prod.hyp_span[1] - a_prod.hyp_span[0] <= 3 * nref
                     and a_batch.hyp_span[1] - a_batch.hyp_span[0] <= 3 * nref)
            if not tight:
                continue
            n_prod, n_batch = len(a_prod.excerpt.split()), len(a_batch.excerpt.split())
            if n_batch == 0:
                continue
            ratio = n_prod / n_batch
            ok = 0.8 <= ratio <= 1.25
            print(f"self-check (excerpt trim parity, {ami_file}#{window.window_index}): "
                  f"{prod}={n_prod}w {batch}={n_batch}w ratio={ratio:.2f} "
                  f"({'PASS' if ok else 'FAIL — trim did not normalize excerpt size'})")
            return
    print("self-check (excerpt trim parity): no tightly-anchored AMI window found to check")


def guard_out_path(out: Path) -> None:
    resolved = out.resolve()
    if "benchmark" in resolved.parts and "results" in resolved.parts:
        sys.exit(f"refusing to write under a benchmark/results path: {resolved}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="+", metavar="NAME=PATH",
                     help="e.g. parakeet_v3=/path/to/run cohere=/path/to/other/run "
                          "(required unless --windows-from is given, which carries every "
                          "arm's excerpt with it)")
    ap.add_argument("--windows-from", type=Path, metavar="GRADES_JSONL",
                     help="replay a previous run's EXACT judge calls from its grades.jsonl: "
                          "same windows, same excerpts verbatim, same label shuffles. Use this "
                          "and not --seed to compare two judge MODELS — the shuffle seed is "
                          "`hash((seed, window_id, pass))` and Python randomizes str hashing "
                          "per process, so the same --seed does NOT reproduce the same letters "
                          "in a new process. --per-corpus / --repeat-fraction / --seed / "
                          "--file-ids / --min-confidence are all ignored in this mode.")
    ap.add_argument("--provider", choices=["gemini", "openrouter"], default="gemini",
                     help="gemini = Google generativelanguage; openrouter = any "
                          "OpenAI-compatible model on openrouter.ai (the second, non-Google "
                          "judge). Same prompt, same schema, same temperature either way.")
    ap.add_argument("--file-ids", nargs="+", default=DEFAULT_FILE_IDS)
    ap.add_argument("--per-corpus", type=int, default=40)
    ap.add_argument("--repeat-fraction", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--min-confidence", type=float, default=0.3,
                     help="minimum fraction of a window's ref words that must land in a "
                          "matching block against an arm's hypothesis, else that arm is "
                          "skipped for that window")
    ap.add_argument("--model", default=None,
                     help=f"default {DEFAULT_MODEL} for --provider gemini, "
                          f"{DEFAULT_OPENROUTER_MODEL} for --provider openrouter")
    ap.add_argument("--thinking", default="minimal")
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--max-output-tokens", type=int, default=2048)
    ap.add_argument("--concurrency", type=int, default=1, choices=[1, 2])
    ap.add_argument("--min-interval", type=float, default=1.0,
                     help="minimum seconds between call starts, shared across all workers")
    ap.add_argument("--max-excerpt-ratio", type=float, default=DEFAULT_MAX_EXCERPT_RATIO,
                     help="HARD CAP on an arm's excerpt: excerpt words / reference window "
                          "words. Over this, the excerpt is cut to that many words centered "
                          "on the anchor's best-matching region (see `cap_excerpt`). "
                          f"Default {DEFAULT_MAX_EXCERPT_RATIO}; pass --no-excerpt-cap for "
                          "the uncapped run-3 behaviour.")
    ap.add_argument("--no-excerpt-cap", action="store_true",
                     help="disable the hard excerpt cap (the run-1..3 path, kept for "
                          "comparability with the published run-3 numbers)")
    ap.add_argument("--balanced-positions", action="store_true",
                     help="assign the blind letters by a deterministic Latin-square rotation "
                          "over the window index instead of a random per-window shuffle, so "
                          "every arm sits in every position an equal number of times "
                          "(4 arms x 80 windows = 20 each). Without it the legacy random "
                          "shuffle is used, which is what run 3 published.")
    ap.add_argument("--position-offset", type=int, default=0,
                     help="rotate the Latin square by this many places. A SECOND judge "
                          "replaying the first judge's excerpts passes a different offset so "
                          "its arm->letter map differs on every window while staying balanced "
                          "— without it the two judges share the first judge's positions and "
                          "their agreement is not independent of position.")
    ap.add_argument("--skip-arm", action="append", default=[], metavar="NAME",
                     help="drop an arm from this run entirely — from --arms, and from the "
                          "rows a --windows-from replay carries. Repeatable. Used to drop "
                          "`granite`, which has 3 unique windows all on one Earnings-21 file "
                          "that its own model card puts in its training data.")
    ap.add_argument("--recap-replay", action="store_true",
                     help="apply --max-excerpt-ratio to the excerpts a --windows-from replay "
                          "carries. OFF by default: a replay exists to show two judges "
                          "byte-identical text, and the second judge should read exactly what "
                          "the first one read.")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.no_excerpt_cap:
        args.max_excerpt_ratio = 0.0
    if args.model is None:
        args.model = DEFAULT_OPENROUTER_MODEL if args.provider == "openrouter" else DEFAULT_MODEL
    # Aliases are Gemini-only; an OpenRouter id (`vendor/model`) passes through.
    args.model_resolved = args.model if args.provider == "openrouter" else resolve_model(args.model)
    if args.provider == "gemini" and not GEMINI_API_KEY:
        sys.exit("no GEMINI_API_KEY (env var, or .env in this worktree or the main checkout)")
    if args.provider == "openrouter" and not OPENROUTER_API_KEY:
        sys.exit("no OPENROUTER_API_KEY (env var, or .env in this worktree or the main checkout)")

    guard_out_path(args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    grades_path = args.out / "grades.jsonl"
    summary_path = args.out / "summary.md"

    # ── replay mode: windows, excerpts and letter shuffles come from a
    # previous run's grades.jsonl, so the two judges see byte-identical
    # prompts. No arm directories, no window sampling, no ITN pass.
    if args.windows_from:
        if args.arms:
            sys.exit("--arms and --windows-from are mutually exclusive: a replay carries "
                     "every arm's excerpt with it, and re-deriving them could differ")
        if not args.windows_from.exists():
            sys.exit(f"--windows-from {args.windows_from}: no such file")
        arms = {}
        jobs = load_replay_jobs(args.windows_from)
        if args.skip_arm:
            for j in jobs:
                if not j.replay:
                    continue
                kept = [n for _, n in sorted(j.replay.label_of_arm.items())
                        if n not in args.skip_arm]
                j.replay.label_of_arm = {chr(ord("A") + i): n for i, n in enumerate(kept)}
                j.replay.local = {n: d for n, d in j.replay.local.items() if n in kept}
                j.replay.skipped = {n: r for n, r in j.replay.skipped.items()
                                    if n not in args.skip_arm}
            print(f"dropped arm(s) {args.skip_arm} from every replayed row")
        replay_arms = sorted({a for j in jobs if j.replay for a in j.replay.label_of_arm.values()})
        selected_ids = {j.window.window_id for j in jobs}
        repeat_ids = {j.window.window_id for j in jobs if j.pass_no != 1}
        print(f"replay: {len(jobs)} call(s) from {args.windows_from}")
        print(f"arms (from the replayed rows): {replay_arms}")
        selected, repeat_windows = list(selected_ids), repeat_ids
    else:
        if not args.arms:
            sys.exit("--arms is required (or pass --windows-from to replay a previous run)")
        arms = parse_arms(args.arms)
        for name in args.skip_arm:
            if arms.pop(name, None) is not None:
                print(f"dropped arm {name} (--skip-arm)")
        if len(arms) < 2:
            sys.exit("fewer than 2 arms left after --skip-arm")
        for name, path in arms.items():
            if not (path / "per-file").is_dir():
                sys.exit(f"--arms {name}={path}: no per-file/ directory there")

        print(f"basis: reference/hypothesis normalization via {scw.itn_bin_id()}")
        print(f"arms: {list(arms)}")
        self_check_trim_parity(arms)

        windows_by_corpus: dict[str, dict[str, list[Window]]] = {}
        for fid in args.file_ids:
            wins = build_windows(fid)
            if not wins:
                print(f"  ! {fid}: no reference found, skipped", file=sys.stderr)
                continue
            corpus = wins[0].corpus
            windows_by_corpus.setdefault(corpus, {})[fid] = wins

        selected = sample_windows(windows_by_corpus, args.per_corpus, args.seed)
        if not selected:
            sys.exit("no windows selected — check --file-ids and benchmark/data")
        rng = random.Random(args.seed + 1)
        n_repeat = math.ceil(args.repeat_fraction * len(selected)) if args.repeat_fraction > 0 else 0
        repeat_windows = set(rng.sample(range(len(selected)), min(n_repeat, len(selected))))

        jobs = []
        for i, w in enumerate(selected):
            jobs.append(JudgeJob(window=w, pass_no=1, shuffle_seed=hash((args.seed, w.window_id, 1)) & 0xFFFFFFFF))
            if i in repeat_windows:
                jobs.append(JudgeJob(window=w, pass_no=2, shuffle_seed=hash((args.seed, w.window_id, 2)) & 0xFFFFFFFF))

    # Latin-square ordinals: the window's rank in the sorted list of the run's
    # unique window ids. Sorted, not sampled order, so the SAME 80 windows get
    # the same ordinals in a fresh run and in a replay of it — which is what
    # makes `--position-offset` a clean one-place rotation between two judges
    # rather than two unrelated maps. Stable under `--resume` for the same
    # reason. Both passes of a repeated window share an ordinal on purpose.
    if args.balanced_positions:
        ordinal_of = {wid: i for i, wid in
                      enumerate(sorted({j.window.window_id for j in jobs}))}
        for j in jobs:
            j.position_ordinal = ordinal_of[j.window.window_id]
        print(f"balanced positions: Latin square over {len(ordinal_of)} windows, "
              f"offset {args.position_offset}")

    done: set[tuple[str, int]] = set()
    existing_rows: list[dict] = []
    if args.resume and grades_path.exists():
        for line in grades_path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            existing_rows.append(r)
            done.add((r["window_id"], r["pass"]))
        jobs = [j for j in jobs if (j.window.window_id, j.pass_no) not in done]
        print(f"resume: {len(done)} already done, {len(jobs)} remaining")

    print(f"{len(selected)} windows selected ({len(repeat_windows)} repeated), "
          f"{len(jobs)} judge call(s) to make")

    limiter = RateLimiter(args.min_interval)
    tokens = TokenTotal()
    parse_failures = ParseFailures()
    new_rows: list[dict] = []
    lock = threading.Lock()

    def handle(job: JudgeJob) -> None:
        row = run_job(job, arms, args, limiter, tokens, parse_failures)
        with lock:
            new_rows.append(row)
            with grades_path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")

    if args.concurrency == 1:
        for job in jobs:
            handle(job)
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = [ex.submit(handle, job) for job in jobs]
            for f in as_completed(futs):
                f.result()  # surface exceptions

    print(f"tokens: prompt={tokens.prompt} candidates={tokens.candidates} total={tokens.total}")
    print(f"parse failures: {parse_failures.n}")

    all_rows = existing_rows + new_rows
    print_excerpt_ratio_report(all_rows)
    write_summary(all_rows, summary_path, args)
    print(f"wrote {grades_path} ({len(all_rows)} rows) and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
