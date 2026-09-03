#!/usr/bin/env python3
"""score_number_fidelity.py — numeric fidelity of the LIVE render (INV-NUM).

The question this answers: does a number the speaker said reach the user's
screen as the SAME quantity, and does the render ever show a number nobody
said? `score_live_invariants.py` cannot answer it — INV-2/4/5 all run every
token through `is_numberish()` and discount it, precisely so a digit-vs-word
spelling difference would not read as a hallucination. That discount is a hole
exactly the size of this check.

SUBSTRATE — read before trusting a number out of this script.
    The hypothesis is the LAST TICK of `live-ticks.jsonl`, i.e. the text a user
    actually read. It is NOT `post-diarization-segments.json`: that file is a
    diarization dump taken BEFORE `InverseTextNormalizer.normalize`
    (`StreamingMeetingWorker.swift:397`, `FileImportProcessor.swift:615`), so
    it carries "one hundred fifteen million dollars" where the render carries
    "$115 million". Scoring it against a digit-form script measures the ITN
    stage that production already ran, and reports every correct number as a
    corruption. `--hypothesis segments` exists for triage of the pre-ITN text
    and prints a PRE-ITN banner; it is never the gate. This is the same
    digit-vs-word artifact `docs/BENCHMARKS.md` records under
    `primary-window-alignment` (+306 number-words / -120 digit tokens on
    earnings21).

WHAT IS MEASURED
  1. VALUE FIDELITY — every script number canonicalized to a float + unit and
     matched in order against the render's. `$115 million` == `one hundred and
     fifteen million dollars` == 115000000.0 USD; `140 basis points` == `1.4%`;
     `twenty twenty` == 2020. Mismatch at the same site = CORRUPTION.
  2. SPLICE / INSERTION DEFECTS — the class a value comparison structurally
     cannot see, because the mangled token is not a wrong VALUE, it is a
     number that was never a number. Measured on this fixture's own render:
     `Q3` -> `Q33`, `Q3 2020` -> `Q 300 million`, `late 2018` -> `late 20 2018`,
     `to Taylor` -> `to the 1st time`, `$91 million` -> `91%`. Reported for the
     FINAL render (survived) and separately across every tick (shown then
     repaired — the user still saw it).
  3. HALLUCINATED NUMBERS — a render number with no script counterpart, split
     by severity: a fabricated SCALED quantity ("300 million") is not the same
     event as a stray "19".
  4. DROPPED — a script number the render never showed.

GATEABILITY — a result is only a gate when the replay played the whole file.
    Completeness comes from the CLOCK (last tick `audioPos` vs the audio's
    duration), never from the scorer's own matches. Derive it from the matches
    and the metric inverts: losing render content moves the "how far did we
    get" line back and excuses exactly the numbers that went missing. That bug
    was here — halving the render took `droppedFromRender` from 1 to 0, and an
    empty render scored 0 on every gated counter. A short replay is now marked
    `gateable: false` (its counters read None to the ratchet) rather than
    quietly forgiven, and `vacuousRender` fires when nothing was compared.

BLIND SPOTS
  - Order-sensitive. Matching is LCS-anchored on exact canonical hits so one
    error stays local to its gap, but a genuine REORDERING still reads as one
    drop plus one invention rather than as a move.
  - Approximate spoken ranges ("mid-30s", "high 20s to low $30 million") are
    extracted as APPROX and reported, never gated — there is no single value
    to compare.
  - A number the ASR loses inside a word it also lost is invisible here; that
    is INV-5's job.
  - Single fixture. earnings21 is prepared remarks read from a page: dense,
    fluent, one voice. It is not evidence about numbers in crosstalk.

  - Needs a PERFORMED script, the same bar INV-4/5 apply via
    `golden_pair_attribution.load_script`. A pair whose script.txt is a
    placeholder is skipped, not scored against its own prose.

Usage — this script PRINTS and dumps detail; the GATE is
`score_live_invariants.py --all` + `--compare`, which owns the INV-NUM ratchet.
  scripts/score_number_fidelity.py <replay-out-dir> [--script <script.txt>]
      [--hypothesis ticks|segments|auto] [--json-out <out.json>]
  scripts/score_number_fidelity.py --all <replay-root>
      [--pairs-root Tests/Fixtures/golden_pairs] [--json-out combined.json]
"""
from __future__ import annotations

import os

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------

TEXT_NUMBERS = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# Scale words, singular AND plural. The plural forms are load-bearing: the
# earnings21 script says "$94 millions" (the speaker's own slip, preserved in
# the verbatim reference). Without them "$94 millions" canonicalizes to 94 and
# the CORRECT render "ninety four million dollars" reads as a 1,000,000x
# corruption — a false positive that fires on working code.
SCALES = {
    "hundred": 100, "hundreds": 100,
    "thousand": 1000, "thousands": 1000,
    "million": 1_000_000, "millions": 1_000_000,
    "billion": 1_000_000_000, "billions": 1_000_000_000,
    "trillion": 1_000_000_000_000, "trillions": 1_000_000_000_000,
}

FRACTIONS = {"half": 0.5, "quarter": 0.25, "third": 1.0 / 3.0, "quarters": 0.25}

ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "twentieth": 20, "thirtieth": 30,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6, "7th": 7,
    "8th": 8, "9th": 9, "10th": 10, "11th": 11, "12th": 12, "13th": 13,
    "14th": 14, "15th": 15, "20th": 20,
}

CURRENCIES = {
    "$": "USD", "dollar": "USD", "dollars": "USD",
    "€": "EUR", "euro": "EUR", "euros": "EUR",
    "£": "GBP", "pound": "GBP", "pounds": "GBP",
    "cent": "CENT", "cents": "CENT",
}

_NUMWORD_ALT = "|".join(sorted(TEXT_NUMBERS, key=len, reverse=True))
_SCALE_ALT = "|".join(sorted(SCALES, key=len, reverse=True))
_FRAC_ALT = "|".join(sorted(FRACTIONS, key=len, reverse=True))

# A spoken number phrase. Deliberately does NOT admit a bare \d+ as a
# continuation: "twenty 2018" must surface as a SPLICE DEFECT, not silently
# canonicalize to 2038, and admitting digits also let "$5.4 million and 140
# basis points" merge across the "and". `and` is admitted only when a number
# word follows it, which is what makes "one hundred and fifteen million" parse
# as 115,000,000 instead of 100 + 15,000,000.
_SPOKEN = (
    rf"(?:{_NUMWORD_ALT}|{_SCALE_ALT})"
    rf"(?:[\s\-]+(?:and[\s\-]+)?(?:{_NUMWORD_ALT}|{_SCALE_ALT}|point|"
    rf"a[\s\-]+(?:{_FRAC_ALT})))*"
)

_UNIT = r"%|percent|percentage\s+points|basis\s+points|bps|days|years|months|units|shares|dollars|dollar|cents|euros|pounds"

NUMBER_ENTITY_RE = re.compile(
    rf"""(?xi)
    # A LEADING MINUS SIGN, not any dash. `InverseTextNormalizer` renders a
    # negative as ASCII "-" + digits (see its cardinal/decimal/measure cases), so
    # the render CAN carry "-11 million" against a script that says "negative 11
    # million" -- without this the scorer reports a phantom corruption on every
    # such pair. The lookaround is load-bearing and was measured: a bare
    # `[-–—−]\s*` alternative flipped 13 numbers negative across 5 of the 7
    # golden scripts (an em dash before "one", a markdown bullet before "1",
    # "2005-06"). Requiring a non-word/non-dot on the left and a digit or "$"
    # IMMEDIATELY on the right leaves all 7 scripts byte-identical to the
    # words-only form, and en/em dashes stay out because prose uses them.
    (?:(?P<neg>negative|minus)\s+|(?P<negsym>(?<![\w.])[-−](?=[$€£]?\d)))?
    (?:
      # Approximate decade ranges: "mid-30s", "high 20s", "low $30s".
      (?P<approx>(?:mid|high|low|early|late)[\s\-]+\$?\d{{1,3}}0s)
      |
      # Formatted currency: $115 million, $5.4M, €81 millions
      (?P<curr_sym>[\$€£])\s*(?P<curr_val>\d+(?:,\d{{3}})*(?:\.\d+)?)
        (?:\s*(?P<curr_scale>{_SCALE_ALT})\b)?
      |
      # Mixed fractions, spoken or written: "five and five eighths percent",
      # "5 5/8%" — a bond coupon; read as 10 by the spoken-number branch before
      # (2026-08-27, 4359971). Only the eighths/quarters/halves family.
      (?:(?P<frac_whole>\d+|{_NUMWORD_ALT})\s+(?:and\s+)?)?(?P<frac_num>\d|one|two|three|four|five|six|seven)\s*(?:/\s*(?P<frac_den_d>2|4|8|16)|\s(?P<frac_den_w>halves?|half|quarters?|eighths?|sixteenths?))(?:\s*(?:of\s+a\s+)?(?P<frac_unit>%|percent))?(?!\w)
      |
      # Percentages and basis points: 21%, 21 percent, 140 basis points
      (?P<pct_val>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?P<pct_unit>%|percent|basis\s+points|bps)
      |
      # Explicit scale cardinals: 115 million, 80 millions
      (?P<scale_val>\d+(?:,\d{{3}})*(?:\.\d+)?)\s+(?P<scale_unit>{_SCALE_ALT})\b
      |
      # Quarters: Q3, Q3 2020, Q three, fourth quarter
      (?P<quarter>Q\s?(?:[1-4]|one|two|three|four)|\b(?:[1-4]|one|two|three|four)\s?Q(?![A-Za-z])|(?:first|second|third|fourth)\s+quarter)\b
        (?:\s+(?P<q_year>\d{{4}}))?
      |
      \b(?P<year>19\d\d|20\d\d)\b
      |
      # Digit ordinals: 30th, 1st, 22nd — the render's DateTagger writes
      # "June 30th" and the reader never extracted it (8 dropped `30`s in the
      # 2026-08-27 fast arm).
      \b(?P<ord_digit>\d{{1,2}})(?:st|nd|rd|th)\b
      |
      \b(?P<ord_word>{"|".join(sorted(ORDINALS, key=len, reverse=True))})\b
      |
      # Spoken phrases: "twenty one percent", "one hundred and fifteen million
      # dollars", "three and a half million", "twenty twenty"
      \b(?P<spoken_num>{_SPOKEN})(?:\s+(?P<spoken_unit>{_UNIT}))?\b
      |
      # Plain quantities: 87 days, or a bare number
      \b(?P<num_val>\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?P<num_unit>{_UNIT})?\b
    )
    """
)

# `two-fold`, `three fold`: a multiplier, not a quantity in the transcript's
# sense. Extracting it produced a false hallucination on every occurrence.
_FOLD_RE = re.compile(rf"\b(?:{_NUMWORD_ALT}|\d+)[\s\-]*fold\b", re.I)

# Alphanumeric ENTITY names — COVID-19, MP3, G7. Masked on BOTH sides before
# extraction, because the asymmetry is otherwise the dominant signal: the
# script writes `COVID-19` (hyphen) and the render writes `COVID 19` or `COVID
# nineteen`, and 8 of 12 "hallucinated numbers" on this fixture were that one
# entity.
#
# TWO patterns, and the split is load-bearing. The hyphen form must be
# case-insensitive (`covid-19`) but must NOT swallow `twenty-one` or
# `two-fold`, hence the number-word lookahead on the stem. The space form must
# be case-SENSITIVE — a single `re.I` over `[A-Z]{3,}\s+<numword>` matches
# `ninety four`, `and fifteen`, `late 20`, and `twenty twenty`, which silently
# deleted most of the corpus's numbers on the first cut of this file.
_STEM = rf"(?!(?:{_NUMWORD_ALT}|{_SCALE_ALT}|and|point)\b)[A-Za-z]{{3,}}"
# SEC filing forms — `10-K`, `8-K`, `10-Q`, `20-F`, and the render's `10K` /
# `8Ks`: a digit stem with a single-letter suffix is a form name, and the
# reference reader extracted the `10` / `8` as counts (2026-08-27 audit).
# `Phase III`, `Part II`, `Tier 1` vs the render's `phase three`: the reference
# writes the roman numeral, the render the word (6 inventions + drops on
# 4366522, 2026-08-27). Rewritten to the digit on both sides before extraction.
_ROMAN_VALUES = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
_ROMAN_AFTER_NOUN_RE = re.compile(
    r"\b(?P<noun>phase|part|tier|class|type|stage|title|chapter|article|section)\s+"
    r"(?P<roman>I{1,3}|IV|V|VI{1,3}|IX|X)\b(?![-\w])", re.I)


def _roman_to_digit(m: "re.Match[str]") -> str:
    return f"{m.group('noun')} {_ROMAN_VALUES[m.group('roman').lower()]}"


_SEC_FORM_RE = re.compile(r"\b(?:Forms?\s+)?(?:8|10|20)[-‑]?[KQF]s?\b")
_ALNUM_HYPHEN_RE = re.compile(
    rf"\b({_STEM})[-‑](?:\d{{1,4}}|(?:{_NUMWORD_ALT}))\b", re.I)
# Case-SENSITIVE stem, case-INSENSITIVE number word, so `COVID Nineteen` at a
# sentence start masks like `COVID nineteen`. The stem stays all-caps because
# a title-case stem would swallow "The nineteen people".
_ALNUM_CAPS_RE = re.compile(
    rf"\b[A-Z]{{3,}}\s+(?:\d{{1,4}}|(?i:{_NUMWORD_ALT}))\b")


def collect_entity_stems(*texts: str) -> frozenset[str]:
    """Stems that appear HYPHENATED to a number on any side — `COVID` from
    `COVID-19`. Masking is then driven by the data instead of by capitalization,
    which is what closes the last asymmetry: the script's `COVID-19` teaches the
    masker that `Covid nineteen` in the render is the same entity, and neither
    side contributes a number the other cannot. Shape rules alone could not do
    this — an all-caps stem misses `Covid nineteen`, and a title-case stem hits
    ordinary prose."""
    stems: set[str] = set()
    for text in texts:
        for m in _ALNUM_HYPHEN_RE.finditer(text or ""):
            stems.add(m.group(1).lower())
    return frozenset(stems)


def _stem_pattern(stems: frozenset[str]) -> re.Pattern[str] | None:
    if not stems:
        return None
    alt = "|".join(re.escape(s) for s in sorted(stems, key=len, reverse=True))
    return re.compile(
        rf"\b(?:{alt})[-‑\s](?:\d{{1,4}}|(?:{_NUMWORD_ALT}))\b", re.I)

_TAG_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]|<[^>]*>")
_SCRIPT_LINE_RE = re.compile(
    r"^(?:\*\*)?(?P<spk>[A-Z][A-Za-z0-9 .'-]{0,30}?):(?:\*\*)?\s+(?P<text>.*)$")


def script_refusal(path: Path) -> str | None:
    """The SAME performed-script check INV-4/5 apply, or None if the file is a
    real script.

    `golden_pair_attribution.load_script` refuses a file that is not a performed
    script — the grantham pair ships a README-shaped placeholder and is refused
    with "6 words, 1 speaker(s)". INV-4/5 degrade on that refusal; INV-NUM only
    checked `path.exists()` and cheerfully extracted 15 "numbers" from that
    file's prose (`~232.8 s`, `2026-06-30`, a UUID), which on a 6-pair `--all`
    run is one pair feeding noise straight into a pinned baseline.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import golden_pair_attribution as gpa
    return gpa.load_script(path)[1]


def script_body_text(path: Path) -> str:
    """The SPOKEN text of a performed script, speaker headers removed.

    Not `golden_pair_attribution.load_script` — that returns `[a-z0-9]+` tokens,
    which shreds `$5.4` into `5` and `4` and drops every `$`/`%`. This keeps
    punctuation and strips only what was never spoken. Callers must clear
    `script_refusal` first: a file with no `**Name:**` lines is returned whole,
    which is right for a headerless performed script and wrong for a README.
    """
    kept: list[str] = []
    saw_header = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        m = _SCRIPT_LINE_RE.match(line)
        if m:
            saw_header = True
            kept.append(m.group("text"))
        else:
            kept.append(line)
    if not saw_header:
        return path.read_text()
    return " ".join(kept)


def _prepare(text: str, stems: frozenset[str] = frozenset()) -> str:
    """The one normalization both sides get. Asymmetry here is how a scorer
    invents findings — every substitution below MUST apply to script and
    hypothesis alike, with the SAME `stems` set derived from both."""
    text = _TAG_RE.sub(" ", text)
    text = _ROMAN_AFTER_NOUN_RE.sub(_roman_to_digit, text)
    text = _SEC_FORM_RE.sub(" ␣ ", text)
    text = _ALNUM_HYPHEN_RE.sub(" ␣ ", text)
    text = _ALNUM_CAPS_RE.sub(" ␣ ", text)
    stem_re = _stem_pattern(stems)
    if stem_re is not None:
        text = stem_re.sub(" ␣ ", text)
    text = _FOLD_RE.sub(" ␣ ", text)
    return text


@dataclass
class NumberEntity:
    raw_text: str
    category: str  # CURRENCY PERCENTAGE BASIS_POINTS YEAR QUARTER ORDINAL QUANTITY CARDINAL APPROX
    canonical_value: float
    unit: str
    start_char: int = 0
    end_char: int = 0


def parse_spoken_number_value(phrase: str) -> tuple[float, str]:
    """'one hundred and fifteen million' -> (115000000.0, 'CARDINAL');
    'twenty twenty' -> (2020.0, 'YEAR'); 'three and a half million' -> 3.5e6."""
    tokens = [t for t in re.split(r"[\s\-]+", phrase.lower()) if t]
    tokens = [t.strip(",.$%€£") for t in tokens]
    tokens = [t for t in tokens if t and t != "and"]

    # Year-shape: "twenty twenty" (2020), "nineteen ninety five" (1995). Only
    # for a 2-3 token phrase with no scale word, so "twenty million" and
    # "twenty one percent" stay cardinals.
    if 2 <= len(tokens) <= 3 and tokens[0] in ("twenty", "nineteen") \
            and not any(t in SCALES for t in tokens):
        rest = tokens[1:]
        if all(t in TEXT_NUMBERS for t in rest):
            base = 2000 if tokens[0] == "twenty" else 1900
            y_val = sum(TEXT_NUMBERS[t] for t in rest)
            if 10 <= y_val < 100:
                return float(base + y_val), "YEAR"

    # Implied hundreds: "two fifty" = 250, "one twenty five million" = 125e6.
    # A ones word followed DIRECTLY by a tens word is the spoken hundreds
    # idiom, not an addition -- summing it read "two fifty" as 52 and charged
    # the render a corruption against a script that said 250 (2026-08-28).
    # Only the leading pair, only 1-19 then tens (20-90), so "fifty
    # two", "two hundred fifty" and the year shapes above are untouched.
    if (len(tokens) >= 2 and tokens[0] in TEXT_NUMBERS and tokens[1] in TEXT_NUMBERS
            and 1 <= TEXT_NUMBERS[tokens[0]] <= 19
            and 20 <= TEXT_NUMBERS[tokens[1]] <= 90 and TEXT_NUMBERS[tokens[1]] % 10 == 0):
        tokens = [tokens[0], "hundred", *tokens[1:]]

    total = 0.0
    current = 0.0
    is_fractional = False
    frac_div = 10.0
    pending_a = False

    for tok in tokens:
        if tok == "a":
            pending_a = True
            continue
        if tok in FRACTIONS:
            # "three and a half million": the fraction attaches to `current`
            # BEFORE the scale multiplies it, so 3 + 0.5 -> 3.5 -> 3,500,000.
            if pending_a or current:
                current += FRACTIONS[tok]
            pending_a = False
            continue
        pending_a = False
        if tok in ("point", "dot"):
            is_fractional = True
            continue
        if tok in TEXT_NUMBERS:
            val = float(TEXT_NUMBERS[tok])
            if is_fractional:
                current += val / frac_div
                frac_div *= 10.0
            else:
                current += val
        elif tok in SCALES:
            scale = float(SCALES[tok])
            if current == 0.0:
                current = 1.0
            if scale >= 1000.0:
                total += current * scale
                current = 0.0
            else:
                current *= scale

    return total + current, "CARDINAL"


# ---------------------------------------------------------------------------
# Non-numeric senses of number words — the interjection / adverb / "another"
# families. Measured 2026-08-24 over the last tick of all six golden pairs:
# 14 of 141 extracted entities (10%) were one of these, and inspecting every
# occurrence found ZERO true positives among them.
#
#   oh     7/7  "Oh, that's so sad" / "Oh got it" / "oh last thing"
#   first  5/5  "At first it was a disaster" / "on the format first, attach…"
#   second 2/2  "I'll make a second pan" (= another) / "the second question"
#
# They inflate `hallucinatedNumbers`, which is a GATED counter, so a build that
# merely says "oh" one more time than the script reads as inventing a number.
#
# SAFETY ARGUMENT for filtering rather than tuning the regex: this runs inside
# extract_number_entities, which is the single door both the script and the
# hypothesis go through, so a drop is always symmetric. Dropping a genuine
# ordinal therefore costs COVERAGE (that number stops being scored) and can
# never flip a verdict — the failure mode is a missed defect, not a false one.
# That is the right direction to err for a gated counter, and it is why these
# rules lean toward dropping when the sense is ambiguous.

# `first`/`second` used adverbially or as a discourse marker rather than as a
# rank. Matched against the text FOLLOWING the entity.
_ORD_DISCOURSE_AFTER = re.compile(
    r"^\s*(?:of\s+all\b|off\b|and\s+foremost\b|,|\.|;|:|!|\?|$)", re.I)
# "a second pan", "another second" — the "one more" sense, not the 2nd item.
# `the second question` keeps its ordinal reading and is NOT matched here.
_ORD_ANOTHER_BEFORE = re.compile(r"(?:^|\W)(?:a|an|another)\s+$", re.I)
# "At first", "at first glance".
_ORD_ADVERBIAL_BEFORE = re.compile(r"(?:^|\W)at\s+$", re.I)


# The digit spellings of the two idioms above. Written as one span so a single
# entity that is only PART of it (`9` of `9-11`) is filtered too.
_IDIOM_DIGIT_RE = re.compile(r"\b(?:9\s*[-/]\s*11|24\s*[-/]\s*7)\b")
_IDIOM_PAD = 6


def _in_idiom_digits(ent: "NumberEntity", clean: str) -> bool:
    """This entity lies wholly inside a digit-form idiom span (`9-11`, `24/7`)."""
    # The entity's own extent, TRIMMED: `NUMBER_ENTITY_RE` lets `\s*` before the
    # optional unit into the match, so `11 ` ends one char past the idiom span
    # and an untrimmed containment test fails on exactly half of `9-11`.
    lo = max(0, ent.start_char - _IDIOM_PAD)
    end = ent.start_char + len(ent.raw_text)
    local = clean[lo:end + _IDIOM_PAD]
    a, b = ent.start_char - lo, end - lo
    return any(m.start() <= a and m.end() >= b
               for m in _IDIOM_DIGIT_RE.finditer(local))


def _is_nonnumeric_sense(ent: "NumberEntity", clean: str) -> bool:
    """True when this entity is a number WORD carrying a non-numeric sense."""
    raw = ent.raw_text.strip().lower()
    before = clean[:ent.start_char]
    after = clean[ent.end_char:]

    # Bare interjection "oh". A digit-string `oh` ("four oh three", "five five
    # five oh one") is matched as a MULTI-token spoken phrase, so it never
    # reaches here as a lone `oh` and is untouched.
    if raw == "oh":
        return True
    # "managing through nine eleven", "working twenty four seven": an event
    # and an idiom, never a count (2026-08-27 audit: one corruption and one
    # drop charged to the render for reading them as `9-11` / `24/7`).
    if raw in ("nine eleven", "twenty four seven", "twenty-four seven"):
        return True
    # ...AND THE DIGIT FORM, which is what the RENDER writes (2026-09-01). The
    # rule above was one-sided: the reference's `nine eleven` was dropped and
    # the render's `9-11` was extracted as two CARDINALs, so a correct render
    # scored two hallucinations. Four such on the pinned Earnings21 run
    # (`9-11` on 4341191, `24/7` on 4346818). A filter that runs on one side
    # only is not a filter, it is a bias.
    if _in_idiom_digits(ent, clean):
        return True

    if ent.category == "ORDINAL" and raw in ("first", "second", "third"):
        # "first of all", "second off", "the format first,", "At first"
        if _ORD_DISCOURSE_AFTER.match(after):
            return True
        if _ORD_ADVERBIAL_BEFORE.search(before):
            return True
        # "a second pan" == another pan
        if raw == "second" and _ORD_ANOTHER_BEFORE.search(before):
            return True
    return False


# Per-call tally of entities `_is_nonnumeric_sense` removed; the scorer reads
# and clears it around its two extractions.
_NONNUMERIC_FILTERED: list[int] = []


def extract_number_entities(text: str, prepared: bool = False,
                            stems: frozenset[str] = frozenset(),
                            reference: bool = False) -> list[NumberEntity]:
    """Every numeric entity in `text`, canonicalized to a float + unit.

    Entities carrying a non-numeric sense (the "oh"/"first"/"second"
    interjection-adverb-another families) are dropped — see
    `_is_nonnumeric_sense` for the measurement and the safety argument."""
    clean = text if prepared else _prepare(text, stems)
    entities: list[NumberEntity] = []

    for m in NUMBER_ENTITY_RE.finditer(clean):
        raw = m.group(0).strip()
        d = m.groupdict()
        neg = -1.0 if (d.get("neg") or d.get("negsym")) else 1.0

        def add(category: str, value: float, unit: str) -> None:
            entities.append(NumberEntity(raw_text=raw, category=category,
                                         canonical_value=value, unit=unit,
                                         start_char=m.start(), end_char=m.end()))

        if d.get("approx"):
            digits = re.search(r"(\d+)", d["approx"])
            add("APPROX", float(digits.group(1)) if digits else 0.0, "approx")
        elif d.get("frac_num"):
            whole_raw = (d.get("frac_whole") or "").lower()
            whole = 0.0 if not whole_raw else (float(whole_raw) if whole_raw.isdigit() else parse_spoken_number_value(whole_raw)[0])
            num_raw = d["frac_num"].lower()
            numer = float(num_raw) if num_raw.isdigit() else parse_spoken_number_value(num_raw)[0]
            den_w = (d.get("frac_den_w") or "").lower()
            denom = float(d["frac_den_d"]) if d.get("frac_den_d") else \
                {"half": 2, "halves": 2, "quarter": 4, "quarters": 4, "eighth": 8, "eighths": 8,
                 "sixteenth": 16, "sixteenths": 16}[den_w]
            # A BARE "two quarters" / "six quarters" (no whole part, no percent
            # unit) is a COUNT of fiscal quarters on an earnings call, not 2/4
            # (final review 2026-08-27). Halves the same. Eighths/sixteenths
            # stay fractions — nobody counts eighths.
            if not whole_raw and not d.get("frac_unit") and den_w in ("quarter", "quarters", "half", "halves"):
                add("CARDINAL", neg * numer, "")
                continue
            val = neg * (whole + numer / denom)
            if d.get("frac_unit"):
                add("PERCENTAGE", val, "%")
            else:
                add("CARDINAL", val, "")
        elif d.get("curr_sym"):
            scale = SCALES.get((d.get("curr_scale") or "").lower(), 1.0)
            add("CURRENCY", neg * float(d["curr_val"].replace(",", "")) * scale,
                CURRENCIES.get(d["curr_sym"], "USD"))
        elif d.get("pct_val"):
            val = neg * float(d["pct_val"].replace(",", ""))
            unit_str = d["pct_unit"].lower()
            if "basis" in unit_str or "bps" in unit_str:
                add("BASIS_POINTS", val, "bps")
            else:
                add("PERCENTAGE", val, "%")
        elif d.get("scale_val"):
            scale = SCALES.get((d.get("scale_unit") or "").lower(), 1.0)
            add("CARDINAL", neg * float(d["scale_val"].replace(",", "")) * scale, "")
        elif d.get("ord_digit"):
            add("ORDINAL", neg * float(d["ord_digit"]), "ordinal")
        elif d.get("quarter"):
            q = d["quarter"].lower()
            q_num = next((n for n, keys in
                          ((1, ("1", "one", "first")), (2, ("2", "two", "second")),
                           (3, ("3", "three", "third")), (4, ("4", "four", "fourth")))
                          if any(k in q for k in keys)), 0)
            q_year = d.get("q_year") or ""
            add("QUARTER", float(q_num), q_year)
            # THE YEAR IS ITS OWN QUANTITY. It used to ride in the QUARTER's
            # `unit` and was compared only when BOTH sides carried one, so a
            # render that DROPPED the year fell through to "match" — "Q3 2020"
            # spoken, "Q three." shown, scored PERFECT. That is the exact
            # failure this instrument exists to catch, and it certified the
            # 2026-08-24 seam arm at 100.0% while the year was missing from the
            # render (benchmark/results/seam-stitching/RESULTS.md, RETRACTION).
            #
            # Emitting it as a separate entity — rather than tightening the
            # QUARTER comparison — is what keeps a legitimately RE-SPLIT render
            # correct: "Q3" + "2020" as two tokens still matches, because the
            # alignment is an LCS over entities, while a render missing the year
            # is simply one entity short and reads as DROPPED.
            if q_year:
                add("YEAR", float(q_year), "year")
        elif d.get("year"):
            add("YEAR", float(d["year"]), "year")
        elif d.get("ord_word"):
            val = float(ORDINALS.get(d["ord_word"].lower(), 0))
            if val > 0:
                add("ORDINAL", val, "ordinal")
        elif d.get("spoken_num"):
            unit_raw = (d.get("spoken_unit") or "").lower()
            phrase = d["spoken_num"].strip()
            # A verbatim STUTTER — "one one other point", "two two" — is the
            # same small number twice, not their sum (2026-08-27, 4341191 /
            # 4365024 read `one one` as 2 and charged a corruption of `one`).
            # Two entities of that value; a genuine "twenty twenty" is a year
            # and never reaches this branch as a repeat of a units word.
            stutter = re.fullmatch(r"(\w+)\s+\1", phrase.lower())
            if stutter and TEXT_NUMBERS.get(stutter.group(1), 100) < 20 and not unit_raw:
                v = float(TEXT_NUMBERS[stutter.group(1)])
                add("CARDINAL", neg * v, "")
                add("CARDINAL", neg * v, "")
                continue
            val, inferred = parse_spoken_number_value(phrase)
            if "percent" in unit_raw or "%" in unit_raw:
                add("PERCENTAGE", neg * val, "%")
            elif "basis" in unit_raw or "bps" in unit_raw:
                add("BASIS_POINTS", neg * val, "bps")
            elif any(k in unit_raw for k in ("dollar", "cent", "euro", "pound")):
                add("CURRENCY", neg * val, CURRENCIES.get(unit_raw, "USD"))
            elif unit_raw:
                add("QUANTITY", neg * val, unit_raw)
            else:
                add(inferred, neg * val, "year" if inferred == "YEAR" else "")
        elif d.get("num_val"):
            val = neg * float(d["num_val"].replace(",", ""))
            unit_raw = (d.get("num_unit") or "").lower()
            if unit_raw in CURRENCIES:
                add("CURRENCY", val, CURRENCIES[unit_raw])
            elif unit_raw:
                add("QUANTITY", val, unit_raw)
            elif re.fullmatch(r"20[12]|19[5-9]", d["num_val"]) and neg > 0:
                # A bare "201" / "202" is a TRUNCATED YEAR, not a count: four
                # Rev.com references carry "first quarter of 201." and "all of
                # 202." (28 tokens across 4366522-era calls, 2026-08-27), and
                # scoring them as CARDINAL 201 charged the render with DROPPING
                # a number nobody could match and INVENTING the 2019 / 2020 it
                # actually heard — 28 drops + 22 inventions from one reference
                # defect. Category YEAR, unit "year-prefix": a hyp year whose
                # first three digits agree is a match; an unmatched one is
                # reported and never gated (`truncatedYearUnmatched`), like an
                # APPROX range.
                add("YEAR", val, "year-prefix")
            else:
                add("CARDINAL", val, "")

    entities = _reconcile_reference_shapes(entities, clean, reference=reference)
    kept = [e for e in entities if not _is_nonnumeric_sense(e, clean)]
    # The filter is a silent exclusion otherwise (audit 2026-08-24): APPROX
    # and not-reached are counted and printed, this was not. Recorded per
    # call so the scorer can report it beside "N scored".
    _NONNUMERIC_FILTERED.append(len(entities) - len(kept))
    return kept


_CURRENCY_WORD_AFTER_RE = re.compile(r"\s*(euros?|dollars?|pounds?)\b", re.I)
_CURRENCY_WORD_UNIT = {"euro": "EUR", "euros": "EUR", "dollar": "USD", "dollars": "USD",
                       "pound": "GBP", "pounds": "GBP"}


def _reconcile_reference_shapes(entities: list[NumberEntity], clean: str,
                                reference: bool = False) -> list[NumberEntity]:
    """Two shapes the Rev.com reference writes that the extractor read as
    different quantities from the render (2026-08-27 audit, 4367535 / 4320211):

    * `$20.8 million Euros` — a dollar sign in front of a euro amount. The
      currency WORD after the amount is what the speaker said; it overrides
      the symbol, so the render's `€20.8 million` is a match and a genuine
      `$` vs `€` disagreement (no word) is still a corruption.
    * `$1 billion $275 million` / `1 billion $290 million` — the compound
      "one billion two hundred seventy five million dollars" written as two
      amounts. Adjacent billion + million (nothing but whitespace or a `$`
      between them, million part under a billion) is ONE amount, 1.275
      billion, which is how ITN renders it. REFERENCE side only (review
      2026-08-27): a render that splits the amount the same way is an ITN
      miss and must stay visible as one."""
    out: list[NumberEntity] = []
    for e in entities:
        if e.category == "CURRENCY":
            m = _CURRENCY_WORD_AFTER_RE.match(clean, e.end_char)
            if m:
                unit = _CURRENCY_WORD_UNIT[m.group(1).lower()]
                if unit != e.unit:
                    e = NumberEntity(e.raw_text + m.group(0), e.category, e.canonical_value,
                                     unit, e.start_char, m.end())
        out.append(e)
    if not reference:
        return out
    # `0.72 cents` / `0.75 cents` (4341191): Rev.com writes a cents amount as
    # the DOLLAR fraction with the word "cents" — the speaker said "seventy
    # two cents" and the render's `72 cents` is right. Reference side only: a
    # render that wrote `0.72 cents` would be an ITN defect and stays visible.
    # Two-decimal form only: `0.5 cents per share` is a real sub-cent fee.
    out = [
        NumberEntity(e.raw_text, e.category, round(e.canonical_value * 100, 6), e.unit,
                     e.start_char, e.end_char)
        if e.category == "CURRENCY" and e.unit == "CENT" and 0 < e.canonical_value < 1
        and re.match(r"0\.\d\d\b", e.raw_text.strip())
        else e
        for e in out
    ]
    merged: list[NumberEntity] = []
    i = 0
    while i < len(out):
        e = out[i]
        if i + 1 < len(out):
            n = out[i + 1]
            between = clean[e.end_char:n.start_char].strip()
            big = e.category in ("CURRENCY", "CARDINAL") and e.canonical_value >= 1e9 \
                and abs(e.canonical_value) % 1e9 == 0
            small = n.category in ("CURRENCY", "CARDINAL") and 0 < abs(n.canonical_value) < 1e9 \
                and abs(n.canonical_value) % 1e6 == 0
            if big and small and between in ("", "$", "€", "£"):
                unit = e.unit or n.unit
                cat = "CURRENCY" if (e.category == "CURRENCY" or n.category == "CURRENCY") else "CARDINAL"
                merged.append(NumberEntity(clean[e.start_char:n.end_char], cat,
                                           e.canonical_value + n.canonical_value,
                                           unit if cat == "CURRENCY" else "",
                                           e.start_char, n.end_char))
                i += 2
                continue
        merged.append(e)
        i += 1
    return merged


# ---------------------------------------------------------------------------
# Splice / insertion defects — the class a value comparison cannot see
# ---------------------------------------------------------------------------
# A merge seam does not usually produce a WRONG number, it produces a token
# that was never a number at all: `Q3` re-committed as `Q33`, `Q3 2020`
# collapsed to `Q 300`, `twenty eighteen` half-normalized to `20 2018`,
# `Taylor` decoded as `1st`. Each of these has a SHAPE, and the shape is what
# is detectable without knowing the truth — which is why these fire on every
# tick, not just where a script exists.

_NW = _NUMWORD_ALT
_SC = _SCALE_ALT

SPLICE_RULES: list[tuple[str, re.Pattern[str], str]] = [
    # "one 137", "twenty 2018" — a number WORD butted against a digit form.
    # `digit + scale word` ("$115 million") is the legitimate shape and is not
    # matched, because the word must come FIRST here.
    # A spoken quarter marker ("Q three 2020", "Q three, 2020") is the one
    # legitimate number-word-then-digits phrase: the extractor reads it as
    # QUARTER+YEAR and the value matcher scores it correctly, so the shape
    # rule must not charge it (audit 2026-08-24: it fired on a CORRECT render
    # of the earnings21 fixture).
    ("WORD_DIGIT_SPLICE",
     re.compile(rf"(?<!\bQ\s)(?<!\bQ)\b(?:{_NW})\s+\$?\d[\d,.]*", re.I),
     "a spoken number word immediately followed by a digit form"),
    # "137 one" — the mirror. Scale words excluded ("115 million" is correct),
    # and so is a following `one`: "in 2020 one of our customers" is ordinary
    # English, and `one` is the only number word frequent enough as a pronoun
    # to make that a real false-positive source.
    ("DIGIT_WORD_SPLICE",
     re.compile(rf"\d\s+(?!one\b)(?:{_NW})\b(?!\s*(?:{_SC})\b)", re.I),
     "a digit form immediately followed by a spoken number word"),
    # "Q33", "Q 300" — a quarter marker carrying more digits than a quarter has.
    ("QUARTER_DIGIT_SPLICE",
     re.compile(r"\bQ\s?\d{2,}", re.I),
     "a quarter marker with 2+ digits (Q3 -> Q33 / Q 300)"),
    # ". million." / "and million" — a scale word with no cardinal in front.
    # "Millions of people" / "hundreds of orders" is the quantifier sense, not
    # a splice, so a following `of` disqualifies it.
    ("ORPHAN_SCALE",
     re.compile(rf"(?:(?<=[.,;:!?])\s+|^|\band\s+)(?:{_SC})\b(?!\s+of\b)", re.I),
     "a scale word with no quantity in front of it"),
    # "115 115", "$77 million $77 million" — the same figure committed twice.
    # The figure must be a WHOLE number token: the first draft's `\d[\d,.]*`
    # backtracked on a plain decimal (group `9`, separator `.`, backref `9`)
    # and charged `9.9`, `2.2`, `1.1` as duplicates — 13 of the 17 hits in the
    # 2026-08-27 pin were this. A digit or point may not follow the group, and
    # the separator is whitespace (optionally after the figure's own closing
    # mark: `2028. 2028`), never a bare point.
    ("DUPLICATED_NUMBER",
     re.compile(rf"(?<![\w$.,])(\$?\d+(?:[,.]\d+)*(?:\s*(?:{_SC}))?)(?![\d,.]?\d)"
                rf"[.,]?\s+\1\b", re.I),
     "the same figure rendered twice back to back"),
    # "115 137" — two bare digit runs adjacent with nothing between them.
    # The first run may carry thousands commas (`1,300`) but may not END on a
    # comma: `September 30, 2020`, `March 31, 2019`, `in 2021, 1.9 billion` are
    # a date or a clause boundary, not a splice — 10 of the 17 hits in the
    # 2026-08-27 pin were dates.
    ("ADJACENT_DIGIT_RUNS",
     re.compile(rf"\b\d+(?:,\d{{3}})*(?:\.\d+)?\.?\s+\d+(?:,\d{{3}})*(?:\.\d+)?(?![,.]?\d)\b(?!\s*(?:{_SC}|%))", re.I),
     "two digit runs adjacent with no unit between them"),
]


def find_splice_defects(text: str, stems: frozenset[str] = frozenset(),
                        *, prepared: bool = False, char_offset: int = 0,
                        word_offset: int = 0) -> list[dict]:
    """Shape-level number defects in one rendering. Truth-free by design: these
    fire on the render alone, so they also work on a pair with no script.

    `char_offset` / `word_offset` describe where `text` sits inside a larger
    rendering, so a caller scanning only the CHANGED tail of a tick still
    reports positions in whole-transcript coordinates. Those offsets MUST be
    measured on prepared text (pass `prepared=True`) — mixing a raw offset with
    a prepared local position drifts the word index by however many entities
    the mask collapsed, which is enough to shift a defect into another bucket.
    """
    clean = text if prepared else _prepare(text, stems)
    out: list[dict] = []
    # One textual defect must count ONCE. "115 115" satisfies both
    # DUPLICATED_NUMBER and ADJACENT_DIGIT_RUNS, and counting it twice would
    # make the metric a function of how many rules happen to overlap rather
    # than of how bad the render is. Rules are tried in SPLICE_RULES order
    # (most specific first) and a match overlapping a claimed span is dropped.
    claimed: list[tuple[int, int]] = []
    for kind, pattern, why in SPLICE_RULES:
        for m in pattern.finditer(clean):
            if any(m.start() < e and s < m.end() for s, e in claimed):
                continue
            claimed.append((m.start(), m.end()))
            out.append({
                "kind": kind,
                "match": m.group(0).strip(),
                "why": why,
                "wordIndex": word_offset + clean.count(" ", 0, m.start()),
                "charPos": char_offset + m.start(),
                "context": " ".join(
                    clean[max(0, m.start() - 60):m.end() + 40].split()),
            })
    return out


# One defect must count ONCE across the whole tick series. Keying on the
# surrounding text does not achieve that: the 60 chars before a settled defect
# keep churning as the ASR revises nearby words, so a single `". million."` was
# counted four times at 58/61/63/66 s as its context went "Girls"->"gross"->"Q33".
# A ratchet keyed that way moves when UNRELATED text changes. Key on the match
# plus its approximate position instead — the bucket absorbs the ±few-word drift
# a re-flow causes while still separating two genuinely different sites (the two
# `Q33`s, 110 words apart, stay two).
_POS_BUCKET = 15


def _defect_key(d: dict) -> tuple[str, str, int]:
    return (d["kind"], d["match"].lower(), d["wordIndex"] // _POS_BUCKET)


def _common_prefix_len(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    lo, hi = 0, limit
    while lo < hi:  # binary search — the strings are near-identical every tick
        mid = (lo + hi + 1) // 2
        if a[:mid] == b[:mid]:
            lo = mid
        else:
            hi = mid - 1
    return lo


def scan_tick_splices(ticks: list[dict], final_text: str,
                      stems: frozenset[str] = frozenset()
                      ) -> tuple[list[dict], list[dict]]:
    """(defects in `final_text`, defects seen in an EARLIER tick then repaired).

    `final_text` is passed in rather than read off `ticks[-1]` so the two halves
    of the report can never describe different substrates: with
    `--hypothesis segments` the value metrics scored the segment dump while the
    splice list came from the ticks, and printed `Q 300` / `20 2018` — strings
    absent from the text it claimed to be scoring.

    A repaired defect is not harmless (the user read it) but it is a different
    event from one that ships, so the two are counted apart.
    """
    final = find_splice_defects(final_text, stems)
    final_keys = {_defect_key(d) for d in final}
    if not ticks:
        return final, []

    # Each tick's text is the previous one plus an edited tail, so scanning the
    # whole accumulated string every tick is quadratic (measured: 240 ticks
    # 0.21 s, 1200 ticks 3.05 s, and a real meeting is several thousand). Scan
    # only from a little before the divergence point.
    # Word indices are anchored on RAW text (`word_offset`) with the local
    # position measured inside the prepared slice. The masks are 1-word-for-
    # 1-word substitutions, so drift between the two is at most a word or two
    # across a few hundred characters — an order of magnitude inside the
    # bucket. Preparing only the slice is what keeps this out of O(n^2).
    transient: dict[tuple[str, str, int], dict] = {}
    prev = ""
    for tick in ticks[:-1]:
        raw = " ".join(r.get("text", "") for r in tick.get("rows", []))
        if raw == prev:
            continue
        start = max(0, _common_prefix_len(prev, raw) - 160)
        prev = raw
        for d in find_splice_defects(raw[start:], stems, char_offset=start,
                                     word_offset=raw.count(" ", 0, start)):
            k = _defect_key(d)
            if k in final_keys or k in transient:
                continue
            transient[k] = {**d, "audioPos": tick.get("audioPos")}
    return final, list(transient.values())


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

_INTERCHANGEABLE = ({"CARDINAL", "QUANTITY"}, {"CARDINAL", "YEAR"},
                    {"CARDINAL", "CURRENCY"}, {"ORDINAL", "QUARTER"})


def is_canonical_match(ref: NumberEntity, hyp: NumberEntity) -> bool:
    """Same quantity, allowing for the spellings ITN legitimately produces."""
    if ref.category == "APPROX" or hyp.category == "APPROX":
        return ref.category == hyp.category and \
            abs(ref.canonical_value - hyp.canonical_value) < 1e-4
    if ref.unit == "year-prefix" and hyp.unit != "year-prefix":
        # Reference "201." (truncated) vs render "2019": the render is right.
        return hyp.category in ("YEAR", "CARDINAL") and \
            int(hyp.canonical_value) // 10 == int(ref.canonical_value)

    pair = {ref.category, hyp.category}
    # A day of the month is the same quantity as `1st` or `1` (2026-08-27: the
    # seam pick keeping a digit window turned `January 1st` into `January 1`,
    # scored as a dropped ORDINAL plus an invented CARDINAL). Value-level, so a
    # render whose day follows a comma or a re-split row is covered too.
    if pair == {"ORDINAL", "CARDINAL"} and ref.unit in ("", "ordinal") and hyp.unit in ("", "ordinal") \
            and 1 <= ref.canonical_value <= 31 \
            and abs(ref.canonical_value - hyp.canonical_value) < 1e-4:
        return True
    if not (ref.category == hyp.category or any(pair <= s for s in _INTERCHANGEABLE)):
        # bps <-> % is a UNIT conversion, checked below, so admit the pair here.
        if pair != {"BASIS_POINTS", "PERCENTAGE"}:
            return False

    # UNIT CONVERSION FIRST (audit 2026-08-24): this branch used to sit below
    # the raw-value equality, so "21%" vs "21 basis points" — a 100x error
    # whose digits happen to coincide — returned True before it was reached.
    if pair == {"BASIS_POINTS", "PERCENTAGE"}:
        bps = ref if ref.category == "BASIS_POINTS" else hyp
        pct = hyp if ref.category == "BASIS_POINTS" else ref
        return abs(bps.canonical_value - pct.canonical_value * 100.0) < 1e-3

    # THE UNIT IS PART OF THE QUANTITY (audit 2026-08-24). "$77 million"
    # rendered as "€77 million", or "87 days" as "87 shares", scored as a
    # perfect match because only the value was compared. Same-category only:
    # CARDINAL carries no unit, so the deliberate CURRENCY<->CARDINAL
    # interchange ("we lost 11 million" for "$11 million") is untouched.
    if ref.category == hyp.category and ref.category in ("CURRENCY", "QUANTITY"):
        if ref.unit and hyp.unit and ref.unit != hyp.unit:
            return False

    if abs(ref.canonical_value - hyp.canonical_value) < 1e-4:
        # The year is scored as its own YEAR entity (see the extraction site).
        # Comparing it HERE too double-counts: a wrong year would report a
        # corrupt QUARTER *and* a corrupt YEAR for one error. The quarter
        # number is all this comparison owns.
        return True

    return False


def _lcs_anchors(ref: list[NumberEntity],
                 hyp: list[NumberEntity]) -> list[tuple[int, int]]:
    """Longest common subsequence of EXACT canonical matches, as (ref_i, hyp_j).

    Exact value matches take priority over fuzzy year-prefix matches so a
    truncated reference year (202.) cannot steal an exact year's anchor (2028).
    These are the resync points. The first cut of this matched greedily with a
    lookahead window and advanced the cursor on a CORRUPTION too, so one
    mis-paired entity slid every later one: on this fixture it reported
    `140 basis points` as dropped AND hallucinated at once, and three
    "corruptions" ($1.7M -> $12M, 29% -> 33%, $12M -> $91M) that were just the
    slip walking forward. Anchoring on certain matches first makes an error
    local to the gap it happens in.
    """
    n, m = len(ref), len(hyp)
    def match_weight(r: NumberEntity, h: NumberEntity) -> int:
        if r.unit == "year-prefix" or h.unit == "year-prefix":
            return 1 if is_canonical_match(r, h) else 0
        return 2 if is_canonical_match(r, h) else 0

    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            w = match_weight(ref[i], hyp[j])
            if w > 0:
                table[i][j] = table[i + 1][j + 1] + w
            table[i][j] = max(table[i][j], table[i + 1][j], table[i][j + 1])
    out: list[tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        w = match_weight(ref[i], hyp[j])
        if w > 0 and table[i][j] == table[i + 1][j + 1] + w:
            out.append((i, j))
            i += 1
            j += 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


_COMPLETE_FRACTION = 0.98
_TAIL_WORDS = 20
_TAIL_MIN_HITS = 6
_WORD_RE = re.compile(r"[A-Za-z0-9$%.,]+")


def _render_frontier_char(script_text: str, hypothesis_text: str,
                          stems: frozenset[str]) -> float:
    """Char offset in the PREPARED script that the render's tail reaches.

    Only consulted for a replay already proven short by the clock. Anchored on
    the render's last words rather than on its matched numbers — anchoring on
    the matches is self-referential (lose a number, move the frontier past it,
    stop counting it) and was the mechanism behind the gate-evasion defect.
    Falls back to "excuse nothing" when the tail cannot be located, which is the
    safe direction: an unlocatable tail should over-report drops, not hide them.
    """
    prepared = _prepare(script_text, stems)
    script_words = [(m.group(0).lower(), m.end()) for m in _WORD_RE.finditer(prepared)]
    tail = [w.lower() for w in _WORD_RE.findall(hypothesis_text)][-_TAIL_WORDS:]
    if not tail or len(script_words) < len(tail):
        return float("inf")
    wanted = set(tail)
    best_hits, best_end = 0, None
    for start in range(len(script_words) - len(tail) + 1):
        window = script_words[start:start + len(tail)]
        hits = sum(1 for w, _ in window if w in wanted)
        if hits > best_hits:
            best_hits, best_end = hits, window[-1][1]
    if best_hits < _TAIL_MIN_HITS or best_end is None:
        return float("inf")
    return float(best_end)


# EXPLAIN mode. Off by default: the detail lists are capped so a pin JSON stays
# a few hundred KB, and every classification below rides on those capped lists.
# `--explain` lifts the cap and attaches the surrounding text, which is what
# makes a reported error readable without a second, differently-prepared matcher
# (the trap the 2026-08-31 hand-read of the inventions fell into).
EXPLAIN = False
_CTX_PAD = 70
_NEAR_PAD = 220


def _cap(rows: list, n: int) -> list:
    return rows if EXPLAIN else rows[:n]


def _ctx(prepared: str, start: int, end: int, pad: int = _CTX_PAD) -> str:
    """The prepared text around one entity, whitespace-collapsed."""
    return " ".join(prepared[max(0, start - pad):end + pad].split())


def _near_ref(prep_ref: str, prep_hyp: str, start: int) -> str:
    """The reference text at the PROPORTIONAL position of a hypothesis offset.

    Not a match — a place to look. An invented number whose tokens appear right
    here is an alignment artifact of the LCS walk; one whose neighbourhood in
    the reference says something else is a real invention. Proportional because
    the two texts are the same speech at different lengths and no per-token
    alignment exists at this layer.
    """
    if not prep_hyp:
        return ""
    p = int(start / len(prep_hyp) * len(prep_ref))
    return " ".join(prep_ref[max(0, p - _NEAR_PAD):p + _NEAR_PAD].split())


# ---------------------------------------------------------------------------
# SPELLINGS — the same quantity written two ways, reported and NOT gated
# ---------------------------------------------------------------------------
# A number error is a WRONG QUANTITY on the screen. Two things that were being
# counted as errors are not that (2026-09-01 audit of all 217 findings on the
# pinned Earnings21 run, `--explain`):
#
#   1. SAME-SITE SPELLINGS. One quantity, present on both sides at the same
#      place, that the matcher cannot pair because the two sides spell its UNIT
#      differently — `150` vs `150 basis points`, `15` vs `15%`, `three` vs
#      `Q3`, `30% to 50%` vs `30 to 50%` — or because the LCS walk pinned an
#      identical value to a different occurrence (`$5 million` vs `$5 million`).
#      Category compatibility is what blocks the anchor (`_INTERCHANGEABLE`
#      does not admit CARDINAL<->PERCENTAGE / BASIS_POINTS / QUARTER), and the
#      gap-walk corruption rule needs the same category too, so the site is
#      charged TWICE: one drop and one invention for one number that is right.
#      Six of the eleven on the pin are the REFERENCE dropping the unit
#      (Rev.com wrote "represented 15 of our LTM revenues", "down 150 versus
#      points", "paid into three"), two are the render mishearing the unit WORD
#      ("400 business points"), and three are pure alignment slips.
#   2. ENTITY-CODE SPELLINGS. A digit inside an alphanumeric NAME the other
#      side writes glued or hyphenated: the render's `FY 21` / `Form ten K` /
#      `CD 16 A` / `Section 27 A` / `five G` against the reference's `FY21` /
#      `10-K` / `CD16A` / `27A` / `5G`. The `_ALNUM_*` masks already excuse
#      this shape when BOTH sides write it the same way; the residue is
#      entirely the asymmetry.
#
# Neither is hidden: both are counted, exampled and printed. What a unit-word
# error costs is charged by `score_corpus_wer.py` (full vocabulary), which is
# the instrument that owns a wrong WORD; this one owns a wrong QUANTITY.
_SPELLING_WINDOW = 70
_SPELLING_MIN_SHARED = 8
# ...AND the two occurrences must sit at the same PLACE in their documents. A
# ±70-char window is 20-odd words and in a short text those windows overlap
# heavily wherever the two texts are the same speech, so shared words alone let
# a number dropped in one paragraph cancel one invented in another. On the
# eleven candidate pairs on the pinned Earnings21 run the ten real ones sit at
# 0.0004-0.0078 of the document and the eleventh sits at 0.754 — the speaker
# said "roughly 200 ... unit order cancellations" twice, once in the remarks and
# once in the Q&A, and the two occurrences shared nine neighbourhood words. So
# 0.05 is ~6x headroom over every true pair and still refuses that one.
_SPELLING_MAX_POS_DRIFT = 0.05


def _neighbourhood(prepared: str, start: int, end: int) -> set[str]:
    lo, hi = max(0, start - _SPELLING_WINDOW), end + _SPELLING_WINDOW
    return {w.strip(".,").lower()
            for w in _WORD_RE.findall(prepared[lo:hi]) if w.strip(".,")}


def _same_site_spellings(ref_entities: list[NumberEntity],
                         hyp_entities: list[NumberEntity],
                         matched_ref: dict[int, int], matched_hyp: set[int],
                         prep_ref: str, prep_hyp: str
                         ) -> tuple[dict[int, int], list[dict]]:
    """Pair a leftover ref and hyp of IDENTICAL value sharing their text.

    Value equality is exact — a spelling never changes the quantity, so any
    tolerance here would start absorbing real corruptions. The neighbourhood
    test is what keeps it local: without it, a number dropped in one paragraph
    and invented in another would cancel out, which is precisely the
    self-referential excusing this scorer's frontier logic was fixed to avoid.
    """
    pairs: dict[int, int] = {}
    taken: set[int] = set()
    free_hyp = [j for j in range(len(hyp_entities)) if j not in matched_hyp]
    rows: list[dict] = []
    for i, ref in enumerate(ref_entities):
        if i in matched_ref:
            continue
        rn = None
        for j in free_hyp:
            if j in taken:
                continue
            hyp = hyp_entities[j]
            if abs(ref.canonical_value - hyp.canonical_value) > 1e-9:
                continue
            drift = abs(ref.start_char / max(1, len(prep_ref))
                        - hyp.start_char / max(1, len(prep_hyp)))
            if drift > _SPELLING_MAX_POS_DRIFT:
                continue
            if rn is None:
                rn = _neighbourhood(prep_ref, ref.start_char, ref.end_char)
            shared = rn & _neighbourhood(prep_hyp, hyp.start_char, hyp.end_char)
            if len(shared) < _SPELLING_MIN_SHARED:
                continue
            taken.add(j)
            pairs[i] = j
            rows.append({
                "kind": "sameSite",
                "ref_raw": ref.raw_text, "ref_category": ref.category,
                "hyp_raw": hyp.raw_text, "hyp_category": hyp.category,
                "value": ref.canonical_value, "sharedWords": len(shared),
                "refContext": _ctx(prep_ref, ref.start_char, ref.end_char),
                "hypContext": _ctx(prep_hyp, hyp.start_char, hyp.end_char),
            })
            break
    return pairs, rows


_CODE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-‑/.']*")
# A WHOLE short letter run touching the entity, at most one space away. The
# boundary assertions are load-bearing: without them an 8-letter word donates
# its last six letters and invents a code that neither side ever wrote.
_LEFT_ALPHA_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]{1,6})\s?$")
_RIGHT_ALPHA_RE = re.compile(r"^\s?([A-Za-z]{1,6})(?![A-Za-z])")


# The entity-code excuse must find its token NEAR the entity, not anywhere in
# a 40-minute call: a `10k` spoken at minute 3 must not excuse an unmatched
# `10` at minute 38. "Near" is measured from an ANCHOR in the other text: the
# nearest MATCHED entity pair carries this entity's char offset across (scorer
# v2). A relative position (fraction of the text) is the fallback when nothing
# matched, and it is wrong whenever the render dropped a span: a 4-minute
# dropout shifts every later relative position by ~4 kchar, past the window
# (review 2026-09-01, finding 3). Window ±5% of the other text, floor 600
# chars (~100 words); the old 1,500 floor was the whole of a short script.
_CODE_LOCALITY_FRACTION = 0.05
_CODE_LOCALITY_MIN_CHARS = 600


class CodeTokens:
    """Tokens of a text reduced to lowercase alphanumerics, with every
    occurrence's relative position, so a lookup can be LOCAL.

    TOKEN-wise, never a substring scan of the whole text: `10q` occurs inside
    `... at 10 quarters ...` once the spaces are gone, and a substring test
    would excuse any digit that happens to sit before the right letter.
    """

    def __init__(self, text: str) -> None:
        self.length = max(1, len(text))
        self.positions: dict[str, list[int]] = {}
        for m in _CODE_TOKEN_RE.finditer(text):
            t = "".join(ch for ch in m.group(0) if ch.isalnum()).lower()
            if t:
                self.positions.setdefault(t, []).append(m.start())

    def __contains__(self, tok: str) -> bool:
        return tok in self.positions

    def near(self, tok: str, centre: float) -> bool:
        """Does `tok` occur within the locality window of `centre`, a char
        offset in THIS text (the anchored estimate of where the entity would
        sit here)?"""
        occ = self.positions.get(tok)
        if not occ:
            return False
        window = max(_CODE_LOCALITY_MIN_CHARS, _CODE_LOCALITY_FRACTION * self.length)
        return any(abs(p - centre) <= window for p in occ)


def _anchored_centre(ent: NumberEntity, own: list[NumberEntity],
                     other: list[NumberEntity], pair_map: dict[int, int],
                     own_len: int, other_len: int) -> float:
    """Where `ent` would sit in the other text: the nearest matched entity on
    this side, plus this entity's char offset from it. Relative position when
    nothing on this side matched."""
    best = None
    for i, j in pair_map.items():
        d = abs(own[i].start_char - ent.start_char)
        if best is None or d < best[0]:
            best = (d, i, j)
    if best is None:
        return ent.start_char / max(1, own_len) * other_len
    _, i, j = best
    return other[j].start_char + (ent.start_char - own[i].start_char)


def _code_tokens(text: str) -> CodeTokens:
    return CodeTokens(text)


def _entity_code_spelling(ent: NumberEntity, prepared: str,
                          other_tokens: CodeTokens, centre: float) -> str | None:
    """The glued form of this entity plus a neighbouring letter run, when that
    form is a TOKEN of the other side NEAR the same relative position. `Form
    ten K` -> `10k`, present in a reference that writes `Form 10-K`. Returns
    the matched token or None.

    Integers only, and only up to four digits: a code is a name, and
    `$115 million` must never be reachable from here. LOCAL (scorer version
    1): an occurrence anywhere in the other text excused a bare `10` forty
    minutes from the only `10-K`.
    """
    v = ent.canonical_value
    if v != int(v) or not (0 <= v <= 9999):
        return None
    digits = str(int(v))
    lm = _LEFT_ALPHA_RE.search(prepared[max(0, ent.start_char - 10):ent.start_char])
    rm = _RIGHT_ALPHA_RE.match(prepared[ent.end_char:ent.end_char + 10])
    lt = lm.group(1).lower() if lm else ""
    rt = rm.group(1).lower() if rm else ""
    for cand in (lt + digits + rt, lt + digits, digits + rt):
        if cand != digits and other_tokens.near(cand, centre):
            return cand
    return None


def score_number_fidelity(script_text: str, hypothesis_text: str,
                          ticks: list[dict] | None = None,
                          audio_duration: float | None = None,
                          complete: bool = False) -> dict:
    """Numeric fidelity of `hypothesis_text` (the RENDER) against the script.

    `audio_duration` (seconds) is what makes the result GATEABLE. Without it
    there is no way to tell a replay that stopped early from a render that lost
    its tail, and the first cut of this function resolved that ambiguity in the
    worst possible direction: it derived the "how far did the render get"
    frontier from its own matches, so losing render content moved the frontier
    back and EXCUSED exactly the numbers that went missing. Halving the render
    took `droppedFromRender` from 1 to 0, and an empty render scored 0 on every
    gated counter — a change that killed the live transcript passed clean.
    """
    stems = collect_entity_stems(script_text, hypothesis_text)
    _NONNUMERIC_FILTERED.clear()
    # Prepared ONCE and passed down, so the char offsets on every entity index
    # into a string this function still holds. Without that the detail rows can
    # name a raw token and nothing else, and every classification of a reported
    # error ("is this a real error or a spelling?") has to be redone by hand
    # outside the scorer against a differently-prepared text — which is how the
    # 2026-08-31 read of the 112 inventions ended up using a matcher that was
    # not this one. `extract_number_entities` prepares internally when handed
    # raw text, so this is the same string it was already building.
    prep_ref = _prepare(script_text, stems)
    prep_hyp = _prepare(hypothesis_text, stems)
    ref_entities = extract_number_entities(prep_ref, prepared=True, reference=True)
    hyp_entities = extract_number_entities(prep_hyp, prepared=True)
    nonnumeric_filtered = sum(_NONNUMERIC_FILTERED)

    anchors = _lcs_anchors(ref_entities, hyp_entities)
    matched_ref: dict[int, int] = dict(anchors)
    matched_hyp: set[int] = {j for _, j in anchors}
    corruptions: list[dict] = []

    # Walk the GAPS between anchors. A ref and a hyp alone together in the same
    # gap, of compatible kind, is one number rendered wrong — a CORRUPTION.
    # Anything else in the gap is a plain drop or a plain invention: guessing a
    # pairing across a 5-vs-1 gap manufactures findings.
    bounds = [(-1, -1)] + anchors + [(len(ref_entities), len(hyp_entities))]
    for (ra, ha), (rb, hb) in zip(bounds, bounds[1:]):
        gap_ref = list(range(ra + 1, rb))
        gap_hyp = list(range(ha + 1, hb))
        for r_i, h_j in zip(gap_ref, gap_hyp):
            ref, hyp = ref_entities[r_i], hyp_entities[h_j]
            if ref.category != hyp.category and not (ref.unit and ref.unit == hyp.unit):
                continue
            corruptions.append({
                "expected_raw": ref.raw_text, "expected_value": ref.canonical_value,
                "actual_raw": hyp.raw_text, "actual_value": hyp.canonical_value,
                "category": ref.category,
                "refContext": _ctx(prep_ref, ref.start_char, ref.end_char),
                "hypContext": _ctx(prep_hyp, hyp.start_char, hyp.end_char),
            })
            matched_ref[r_i] = h_j
            matched_hyp.add(h_j)

    # SPELLINGS. Run AFTER the corruption walk so a real wrong quantity in a
    # gap is still claimed as a corruption first; these only ever consume
    # entities both passes left unmatched.
    spelling_pairs, spelling_rows = _same_site_spellings(
        ref_entities, hyp_entities, matched_ref, matched_hyp, prep_ref, prep_hyp)
    spelling_ref: set[int] = set(spelling_pairs)
    spelling_hyp: set[int] = set(spelling_pairs.values())
    # The other side's vocabulary is read from the RAW text, not the prepared
    # one: `_SEC_FORM_RE` and the `_ALNUM_*` masks replace exactly the glued
    # entity names this test wants to find, so asking the prepared reference
    # whether it writes `10-K` gets "no, it writes ␣".
    ref_tokens, hyp_tokens = _code_tokens(script_text), _code_tokens(hypothesis_text)
    hyp_to_ref = {j: i for i, j in matched_ref.items()}
    for i, ref in enumerate(ref_entities):
        if i in matched_ref or i in spelling_ref:
            continue
        centre = _anchored_centre(ref, ref_entities, hyp_entities, matched_ref,
                                  len(prep_ref), len(prep_hyp))
        tok = _entity_code_spelling(ref, prep_ref, hyp_tokens, centre)
        if tok:
            spelling_ref.add(i)
            spelling_rows.append({
                "kind": "entityCode", "side": "reference", "token": tok,
                "ref_raw": ref.raw_text, "ref_category": ref.category,
                "value": ref.canonical_value,
                "refContext": _ctx(prep_ref, ref.start_char, ref.end_char)})
    for j, hyp in enumerate(hyp_entities):
        if j in matched_hyp or j in spelling_hyp:
            continue
        centre = _anchored_centre(hyp, hyp_entities, ref_entities, hyp_to_ref,
                                  len(prep_hyp), len(prep_ref))
        tok = _entity_code_spelling(hyp, prep_hyp, ref_tokens, centre)
        if tok:
            spelling_hyp.add(j)
            spelling_rows.append({
                "kind": "entityCode", "side": "render", "token": tok,
                "hyp_raw": hyp.raw_text, "hyp_category": hyp.category,
                "value": hyp.canonical_value,
                "hypContext": _ctx(prep_hyp, hyp.start_char, hyp.end_char)})

    # Did the replay actually play the whole file? This is the ONLY honest way
    # to separate "the audio stopped" from "the render lost its tail", and it
    # comes from the clock, never from the matches. When the replay IS complete
    # the frontier is infinite: every unmatched number is a DROP and the gate
    # can fire. When it is not, the run is marked ungateable rather than quietly
    # excusing the tail — an incomplete replay is not a measurement.
    last_pos = max((t.get("audioPos") or 0.0 for t in (ticks or [])), default=None)
    if complete:
        # A BATCH decode of a whole file (the corpus arm) has no clock to
        # consult and no tail to lose: the caller vouches for completeness.
        coverage, replay_complete = 1.0, True
    elif audio_duration and last_pos is not None:
        coverage = min(1.0, last_pos / audio_duration)
        replay_complete = coverage >= _COMPLETE_FRACTION
    else:
        coverage = None
        replay_complete = None

    frontier = float("inf")
    if replay_complete is False:
        frontier = _render_frontier_char(script_text, hypothesis_text, stems)

    dropped, not_reached, approx_unmatched = [], [], []
    truncated_unmatched = []
    for i, ref in enumerate(ref_entities):
        if i in matched_ref or i in spelling_ref:
            continue
        row = {"raw": ref.raw_text, "value": ref.canonical_value,
               "category": ref.category,
               "refContext": _ctx(prep_ref, ref.start_char, ref.end_char),
               "nearHyp": _near_ref(prep_hyp, prep_ref, ref.start_char)}
        if ref.start_char >= frontier:
            not_reached.append(row)
        elif ref.category == "APPROX":
            # "mid-30s" / "high 20s to low $30 million" have no single value to
            # compare, so they are REPORTED and never gated — a ratchet on them
            # would fire on any legitimate rewording.
            approx_unmatched.append(row)
        elif ref.unit == "year-prefix":
            # A truncated reference year nothing in the render matched: the
            # reference is defective here, so this is reported, not gated.
            truncated_unmatched.append(row)
        else:
            dropped.append(row)

    hallucinations = [
        {"raw": h.raw_text, "value": h.canonical_value, "category": h.category,
         "hypContext": _ctx(prep_hyp, h.start_char, h.end_char),
         "nearRef": _near_ref(prep_ref, prep_hyp, h.start_char),
         # A fabricated SCALED quantity ("300 million") is a different event
         # from a stray "19": it is the shape that lands in a summary.
         # A fabricated 5000% or 50,000 bps is the same event at a lower
         # numeric threshold (audit 2026-08-24: they always read "low").
         "severity": "high" if (
             (abs(h.canonical_value) >= 1000
              and h.category in ("CURRENCY", "CARDINAL", "QUANTITY"))
             or (abs(h.canonical_value) >= 100
                 and h.category in ("PERCENTAGE", "BASIS_POINTS"))) else "low"}
        for i, h in enumerate(hyp_entities)
        if i not in matched_hyp and i not in spelling_hyp
        # An APPROX in the RENDER with no counterpart is the mirror of
        # `approxUnmatched` on the reference side, which is reported and never
        # gated because there is no single value to compare. It was being
        # charged as a hallucination on this side only (one on the pin,
        # `mid-30s` on 4346818): the same asymmetry as the idiom filter.
        and h.category != "APPROX"
    ]
    approx_invented = [
        {"raw": h.raw_text, "value": h.canonical_value, "category": h.category,
         "hypContext": _ctx(prep_hyp, h.start_char, h.end_char)}
        for i, h in enumerate(hyp_entities)
        if i not in matched_hyp and i not in spelling_hyp and h.category == "APPROX"
    ]

    final_splices, transient_splices = scan_tick_splices(
        ticks or [], hypothesis_text, stems)

    # SCRIPT-ATTESTED SPLICES, the same discount INV-3/INV-6 already take. The
    # splice rules are TRUTH-FREE by design — they must fire on a render with no
    # script — so nothing stopped them charging the render for a shape the
    # SPEAKER produced. Measured on the pin: 4346818's `ORPHAN_SCALE` is
    # Rev.com's own "from the cost synergy perspective, million dollars, uh, you
    # know," — a faithful decode of a disfluency, counted as a defect for as
    # long as this cell has existed. Attested = the SAME rule fires on the
    # reference at the same place (`_SPELLING_MAX_POS_DRIFT`), which is the
    # shape question, not a verbatim text compare: Rev's fillers and punctuation
    # never match the render's word for word.
    ref_splices = find_splice_defects(prep_ref, stems, prepared=True)
    attested: list[dict] = []
    kept_splices: list[dict] = []
    for d in final_splices:
        pos = (d["charPos"] / len(prep_hyp)) if prep_hyp else 0.0
        hit = next(
            (rs for rs in ref_splices
             if rs["kind"] == d["kind"]
             and abs(rs["charPos"] / max(1, len(prep_ref)) - pos)
             <= _SPELLING_MAX_POS_DRIFT), None)
        if hit:
            attested.append({**d, "refMatch": hit["match"], "refContext": hit["context"]})
        else:
            kept_splices.append(d)
    final_splices = kept_splices

    scored = (len(ref_entities) - len(not_reached) - len(approx_unmatched)
              - len(truncated_unmatched) - len(spelling_ref))
    exact = len(matched_ref) - len(corruptions)

    # PER-NUMBER OUTCOMES, in reference order, so two arms scored against the
    # same reference can be joined number-by-number (the corpus arm's
    # decoder-vs-ITN attribution), and PER-CATEGORY counts so a regression can
    # be pointed at money / percentages / years rather than "numbers".
    corrupt_ref = {i for i, j in matched_ref.items()
                   if any(c["expected_raw"] == ref_entities[i].raw_text
                          and c["actual_raw"] == hyp_entities[j].raw_text
                          for c in corruptions)}
    outcomes: list[dict] = []
    by_cat: dict[str, dict[str, int]] = {}
    def bump(cat: str, key: str) -> None:
        by_cat.setdefault(cat, {"scored": 0, "exact": 0, "corrupted": 0,
                                "dropped": 0, "invented": 0})[key] += 1
    not_reached_set = {(r["raw"], r["value"]) for r in not_reached}
    approx_set = {(r["raw"], r["value"]) for r in approx_unmatched}
    for i, ref in enumerate(ref_entities):
        if i in corrupt_ref:
            o = "corrupt"
        elif i in matched_ref:
            o = "exact"
        elif i in spelling_ref:
            o = "spelling"
        elif (ref.raw_text, ref.canonical_value) in not_reached_set:
            o = "notReached"
        elif (ref.raw_text, ref.canonical_value) in approx_set:
            o = "approx"
        else:
            o = "dropped"
        outcomes.append({"raw": ref.raw_text, "value": ref.canonical_value,
                         "category": ref.category, "outcome": o,
                         "actual": hyp_entities[matched_ref[i]].raw_text
                         if i in matched_ref else None})
        if o in ("exact", "corrupt", "dropped"):
            bump(ref.category, "scored")
            bump(ref.category, {"exact": "exact", "corrupt": "corrupted",
                                "dropped": "dropped"}[o])
    for h in hallucinations:
        bump(h["category"], "invented")

    # VACUOUS-RENDER GUARD. `scored == 0` means nothing was compared, which the
    # counters otherwise report as a spotless result. `--all` already refuses a
    # run over zero pairs for the same reason; the per-pair path needs the same
    # floor. Gated at tolerance 0 so it can never be absorbed as jitter.
    render_words, script_words_n = len(hypothesis_text.split()), len(script_text.split())
    vacuous = scored == 0 or (script_words_n > 50
                              and render_words < script_words_n * 0.05)
    reasons = []
    if replay_complete is None:
        reasons.append("audio duration unknown — cannot tell a short replay "
                       "from a lost render tail")
    elif not replay_complete:
        reasons.append(f"replay covered {coverage:.0%} of the audio — "
                       f"an incomplete replay is not a measurement")
    gateable = not reasons

    result = {
        "scorerVersion": SCORER_VERSION,
        "gateable": gateable,
        "notGateableReasons": reasons,
        "vacuousRender": int(vacuous),
        "replayCoverage": round(coverage, 4) if coverage is not None else None,
        "audioDurationSec": audio_duration,
        "lastTickAudioPos": last_pos,
        "renderWords": len(hypothesis_text.split()),
        "scriptWords": len(script_text.split()),
        "totalScriptNumbers": len(ref_entities),
        "nonNumericSenseFiltered": nonnumeric_filtered,
        "scoredScriptNumbers": scored,
        "notReachedByRender": len(not_reached),
        "notReachedDetails": _cap(not_reached, 10),
        "totalHypNumbers": len(hyp_entities),
        "exactMatches": exact,
        "numberAccuracyPct": round(exact / scored * 100.0, 1) if scored else None,
        "corruptions": len(corruptions),
        "corruptionDetails": _cap(corruptions, 15),
        "droppedFromRender": len(dropped),
        "droppedDetails": _cap(dropped, 15),
        "approxUnmatched": len(approx_unmatched),
        "approxUnmatchedDetails": _cap(approx_unmatched, 10),
        "truncatedYearUnmatched": len(truncated_unmatched),
        "truncatedYearUnmatchedDetails": _cap(truncated_unmatched, 10),
        # REPORTED, NOT GATED — same quantity, two spellings. See the SPELLINGS
        # block above for the admitting predicates and why neither half is an
        # error in the counter this file owns.
        "spellingEquivalents": len(spelling_rows),
        "spellingSameSite": sum(1 for r in spelling_rows if r["kind"] == "sameSite"),
        "spellingEntityCode": sum(1 for r in spelling_rows if r["kind"] == "entityCode"),
        "spellingDetails": _cap(spelling_rows, 15),
        "approxInvented": len(approx_invented),
        "approxInventedDetails": _cap(approx_invented, 10),
        "hallucinatedNumbers": len(hallucinations),
        "hallucinatedHighSeverity": sum(1 for h in hallucinations
                                        if h["severity"] == "high"),
        "hallucinationDetails": _cap(hallucinations, 15),
        "spliceDefects": len(final_splices),
        # Reported, not gated: the reference carries the same shape here.
        "spliceScriptAttested": len(attested),
        "spliceScriptAttestedDetails": _cap(attested, 10),
        "spliceDefectDetails": _cap(final_splices, 15),
        "spliceDefectsTransient": len(transient_splices),
        "spliceTransientDetails": _cap(transient_splices, 15),
        "byCategory": by_cat,
        "refOutcomes": outcomes,
        "hypInvented": [h["raw"] for h in hallucinations],
    }
    return result


# ---------------------------------------------------------------------------
# Substrate selection
# ---------------------------------------------------------------------------

_ITN_SHAPE_RE = re.compile(r"[\$€£]\s?\d|\d\s?%|\d+\s+basis\s+points", re.I)


def looks_pre_itn(text: str) -> bool:
    """True when the text carries spoken-form quantities and essentially no
    written-form ones — the signature of a dump taken before
    `InverseTextNormalizer.normalize`."""
    spoken = len(re.findall(rf"\b(?:{_NW})\s+(?:{_SC})\b", text, re.I))
    return spoken >= 3 and len(_ITN_SHAPE_RE.findall(text)) <= spoken // 4


def render_text_from_ticks(ticks: list[dict]) -> str:
    return " ".join(r.get("text", "") for r in ticks[-1].get("rows", [])) if ticks else ""


def load_ticks(path: Path) -> list[dict]:
    ticks = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ticks.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return ticks


def audio_duration_seconds(out_dir: Path, pair_dir: Path | None) -> float | None:
    """Seconds of audio the replay was fed, from the diarization dump's last
    segment end or, failing that, the pair's own `system.wav` header. Needed
    because replay completeness is what makes a run gateable at all — see
    `score_number_fidelity`."""
    segs_path = out_dir / "post-diarization-segments.json"
    if segs_path.exists():
        try:
            raw = json.loads(segs_path.read_text())
            segs = raw["segments"] if isinstance(raw, dict) else raw
            ends = [float(s.get("endTime", s.get("end", 0)) or 0) for s in segs]
            if ends and max(ends) > 0:
                return max(ends)
        except (ValueError, KeyError, TypeError):
            pass
    if pair_dir:
        dur = wav_duration_seconds(pair_dir / "system.wav")
        if dur:
            return dur
    return None


def wav_duration_seconds(path: Path) -> float | None:
    """Seconds of audio in a RIFF/WAVE file, by parsing the header directly.

    NOT `wave` from the stdlib: it raises `Error: unknown format: 3` on IEEE
    float PCM, and six of the seven golden pairs are float32. Catching that
    exception and returning None is worse than crashing — the caller reads
    "duration unknown", every pair becomes ungateable, and the gate reports a
    clean run over nothing.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    import struct
    pos, byte_rate, total = 12, None, None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        body = pos + 8
        if cid == b"fmt " and size >= 16:
            byte_rate = struct.unpack_from("<I", data, body + 8)[0]
        elif cid == b"data":
            # A streamed file can carry a bogus size; clamp to what is there.
            total = min(size, len(data) - body)
            break
        pos = body + size + (size & 1)
    if not byte_rate or total is None:
        return None
    return total / float(byte_rate)


def resolve_hypothesis(out_dir: Path, mode: str) -> tuple[str, list[dict], str]:
    """(hypothesis text, ticks, substrate label). Prints a banner when the
    caller has asked for — or fallen back to — the pre-ITN dump.

    Ticks are returned ONLY when they are the substrate. `score_number_fidelity`
    scans the tick series for transient splice defects, so handing it ticks
    alongside a segments hypothesis made one report describe two substrates:
    the value metrics scored the segment dump while the splice list quoted
    `Q 300` and `20 2018`, strings that appear nowhere in the scored text.
    """
    ticks_path = out_dir / "live-ticks.jsonl"
    segs_path = out_dir / "post-diarization-segments.json"
    ticks = load_ticks(ticks_path) if ticks_path.exists() else []

    seg_text = ""
    if segs_path.exists():
        raw = json.loads(segs_path.read_text())
        segs = raw["segments"] if isinstance(raw, dict) else raw
        seg_text = " ".join(s.get("text", "") for s in segs)

    if mode == "segments" or (mode == "auto" and not ticks):
        chosen, label, ticks = seg_text, "post-diarization-segments.json", []
    else:
        chosen, label = render_text_from_ticks(ticks), "live-ticks.jsonl (last tick)"

    if chosen and looks_pre_itn(chosen):
        print("⚠️  PRE-ITN SUBSTRATE — this text carries spoken-form quantities "
              "(\"one hundred fifteen million dollars\") and almost no written "
              "forms.\n    `post-diarization-segments.json` is dumped BEFORE "
              "InverseTextNormalizer.normalize, so scoring it against a "
              "digit-form\n    script measures a stage production already ran. "
              "Use --hypothesis ticks. This result is TRIAGE, not a gate.")
    return chosen, ticks, label


def print_report(name: str, result: dict, label: str) -> None:
    print(f"=== INV-NUM number fidelity — {name} ===")
    print(f"substrate       : {label}")
    if not result["gateable"]:
        for r in result["notGateableReasons"]:
            print(f"⛔ NOT GATEABLE  : {r}")
        print("                  numbers below are TRIAGE — do not pin them.")
    cov = result["replayCoverage"]
    print(f"replay coverage : "
          + (f"{cov:.1%} of {result['audioDurationSec'] or 0:.0f}s audio"
             if cov is not None else "unknown")
          + f"   render {result['renderWords']}w vs script {result['scriptWords']}w")
    if result["vacuousRender"]:
        print("❌ VACUOUS RENDER: nothing was compared. Every counter below reads "
              "0 because the\n                  render is empty or holds no "
              "script number — that is a FAILURE, not a pass.")
    acc = result["numberAccuracyPct"]
    frontier_note = (f", {result['notReachedByRender']} beyond the render frontier"
                     if result["notReachedByRender"] else "")
    print(f"non-numeric sense filtered: {result.get('nonNumericSenseFiltered', '?')} "
          "(both sides; 'oh'/'first'/'second'/'9-11' families, see _is_nonnumeric_sense)")
    if result.get("spellingEquivalents") or result.get("approxInvented"):
        print(f"spelling equivalents: {result.get('spellingEquivalents', 0)} "
              f"(same-site {result.get('spellingSameSite', 0)}, entity-code "
              f"{result.get('spellingEntityCode', 0)}) + "
              f"{result.get('approxInvented', 0)} approximate range(s) in the "
              f"render — REPORTED, NOT GATED")
        for sp in result.get("spellingDetails", [])[:6]:
            if sp["kind"] == "sameSite":
                print(f"  ≈ {sp['ref_raw']!r} [{sp['ref_category']}] vs "
                      f"{sp['hyp_raw']!r} [{sp['hyp_category']}]")
            else:
                print(f"  ≈ {sp['kind']} {sp['side']}: "
                      f"{sp.get('ref_raw') or sp.get('hyp_raw')!r} -> {sp['token']!r}")
    print(f"script numbers  : {result['totalScriptNumbers']} "
          f"({result['scoredScriptNumbers']} scored{frontier_note})")
    print(f"exact matched   : {result['exactMatches']}"
          + (f" ({acc}%)" if acc is not None else " (n/a)"))
    print(f"corrupted       : {result['corruptions']}")
    for c in result["corruptionDetails"]:
        print(f"  ⚠️  {c['expected_raw']} ({c['expected_value']:g}) "
              f"→ {c['actual_raw']} ({c['actual_value']:g})")
    print(f"dropped         : {result['droppedFromRender']}"
          + (f"  (+{result['approxUnmatched']} approximate range(s), not gated)"
             if result["approxUnmatched"] else "")
          + (f"  (+{result['truncatedYearUnmatched']} truncated reference year(s), not gated)"
             if result.get("truncatedYearUnmatched") else ""))
    for m in result["droppedDetails"][:8]:
        print(f"  ❌ {m['raw']} ({m['category']})")
    print(f"hallucinated    : {result['hallucinatedNumbers']} "
          f"({result['hallucinatedHighSeverity']} high-severity)")
    for h in result["hallucinationDetails"][:8]:
        print(f"  ➕ {h['raw']} ({h['category']}, {h['severity']})")
    print(f"splice defects  : {result['spliceDefects']} in the final render, "
          f"{result['spliceDefectsTransient']} shown then repaired"
          + (f", {result['spliceScriptAttested']} script-attested (not gated)"
             if result.get("spliceScriptAttested") else ""))
    for d in result.get("spliceScriptAttestedDetails", [])[:4]:
        print(f"  ≈ {d['kind']} script-attested: \u201c{d['match']}\u201d "
              f"vs reference \u201c{d['refMatch']}\u201d")
    for d in result["spliceDefectDetails"][:8]:
        print(f"  🔧 {d['kind']}: \u201c{d['match']}\u201d  …{d['context']}…")
    for d in result["spliceTransientDetails"][:6]:
        print(f"  ↩️  {d['kind']} @{d.get('audioPos')}s: \u201c{d['match']}\u201d")


# --------------------------------------------------------------- self-check
# Every DROP case below is a verbatim span from the last tick of a committed
# golden pair (measured 2026-08-24), not an invented example. Every KEEP case
# is a sense the filter must not swallow. Run: --self-check (no data needed).

_SELFCHECK_DROP = [
    ("Yeah, this this is Oh, that's so sad.", "oh"),
    ("Good. Good. Oh, quick thing while I'm thinking", "oh"),
    ("with me saying, Oh, Jeremy, Jeremy, don't get excited", "oh"),
    ("Velocity. Oh got it, I see it Oh god.", "oh"),
    ("decision is cover pro, good. oh last thing, the printers", "oh"),
    ("trying to shrink Oh, that changes things.", "oh"),
    ("about two months ago. At first it was a disaster.", "first"),
    ("If we boil the ocean on the format first, attach rate craters", "first"),
    ("don't worry, I'll make a second pan that's just plain", "second"),
    ("First of all, thanks for coming.", "first"),
    ("Second of all, the budget.", "second"),
    ("First off, let me say this.", "first"),
    ("First and foremost, safety.", "first"),
    ("wait a second, that's wrong", "second"),
    ("give me a second", "second"),
    ("I'd like a second opinion", "second"),
]

# (text, a token that MUST still be extracted; None = at least one entity)
_SELFCHECK_KEEP = [
    # digit-string `oh` is a real digit and survives inside its phrase
    ("call four oh three five five five", "four oh three five five five"),
    ("extension five five five oh one", "five five five oh one"),
    ("the second question, of course, was", "second"),
    ("she finished third in the race", "third"),
    ("the first item on the agenda", "first"),
    ("our second largest market", "second"),
    ("the first quarter of 2020", None),
    ("revenue was $115 million", None),
    ("up 21 percent year over year", None),
    ("140 basis points", None),
    ("in twenty twenty we grew", None),
]


def _self_check() -> int:
    bad = 0
    print("=== score_number_fidelity self-check: non-numeric-sense filter ===")
    print("\nmust DROP (verbatim spans from the golden pairs):")
    for txt, tok in _SELFCHECK_DROP:
        got = [e.raw_text.strip().lower() for e in extract_number_entities(txt)]
        ok = tok not in got
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {txt[:50]:<52s} -> {got}")
    print("\nmust KEEP:")
    for txt, tok in _SELFCHECK_KEEP:
        got = [e.raw_text.strip().lower() for e in extract_number_entities(txt)]
        ok = len(got) > 0 if tok is None else tok in got
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {txt[:50]:<52s} -> {got}")

    # NON-VACUITY: the filter must actually be reachable. If it never fires,
    # every DROP row above would pass for the wrong reason.
    fired = sum(1 for txt, _ in _SELFCHECK_DROP
                if len(extract_number_entities(txt)) <
                   len([m for m in NUMBER_ENTITY_RE.finditer(_prepare(txt))]))
    if fired == 0:
        print("\n\u274c NON-VACUOUS CHECK FAILED: the filter never fired")
        bad += 1
    else:
        print(f"\nfilter fired on {fired}/{len(_SELFCHECK_DROP)} drop cases")

    # SPELLINGS, BOTH DIRECTIONS. Every "must be a spelling" case is a verbatim
    # pair from the 2026-08-29 pinned Earnings21 run (`--explain`, 2026-09-01);
    # every "must stay an error" case is the nearest thing to it that a reader
    # would call a wrong number. A one-directional table proves nothing here:
    # the whole risk of this class is that it eats real errors.
    print("\nspelling equivalents (reported, not gated):")
    _no_error = lambda r: (r["corruptions"] == 0 and r["droppedFromRender"] == 0
                           and r["hallucinatedNumbers"] == 0)
    _spelling_cases = [
        # 4346818: the REFERENCE lost the unit ("down 150 versus points").
        ("unit missing on the reference side",
         "Non-GAAP adjusted EBITDA margin was 17%, which was down 150 versus "
         "points from the prior year. Other cost mitigation efforts helped limit.",
         "Non-gap adjusted EBITA margin was 17%, which was down 150 basis "
         "points from the prior year. Other cost mitigation efforts helped limit.",
         lambda r: _no_error(r) and r["spellingSameSite"] == 1),
        # 4359971: Rev.com wrote "represented 15 of our LTM revenues".
        ("percent sign missing on the reference side",
         "Let's turn now to aerospace. Aerospace represented 15 of our LTM "
         "revenues. The near-term outlook for aerospace remains uncertain.",
         "Let's turn now to aerospace. Aerospace represented 15% of our LTM "
         "revenues. The near term outlook for aerospace remains uncertain.",
         lambda r: _no_error(r) and r["spellingSameSite"] == 1),
        # 4346818: the RENDER misheard the unit WORD. The quantity is right;
        # the wrong word is `score_corpus_wer.py`'s to charge, not this one.
        ("unit word misheard by the render",
         "down from last year level of 30.8% but sequentially better by over "
         "400 basis points. As we peep to the second quarter and rest of the year.",
         "down from last year's level of 30.8%, but sequentially better by over "
         "400 business points. As we pivot to the second quarter and rest of the year.",
         lambda r: _no_error(r) and r["spellingSameSite"] == 1),
        # 4320211: `FY21` vs `FY 21` — an entity name, not a quantity.
        ("entity code split by the render",
         "we certainly believe we're gonna be better than that as we roll into "
         "FY21. I appreciate all the color. Thank you.",
         "we certainly believe we're going to be better than that as we roll into "
         "FY 21 I appreciate all the color. Thank you.",
         lambda r: _no_error(r) and r["spellingEntityCode"] == 1),
        # 4384964 / 4387332: the SEC form mask hides `10-K` from the reference
        # vocabulary, so the render's spelled-out `Ten K` had nothing to match.
        ("SEC form spelled out by the render",
         "night and in our most recent 10-K. Speaking today will be Phil Lembo.",
         "night and in our most recent Ten K. Speaking today will be Phil Lembo.",
         lambda r: _no_error(r) and r["spellingEntityCode"] == 1),
        # 4341191: the reference-side idiom filter, now applied to both sides.
        ("idiom in digit form",
         "my experiences as CEO managing through nine eleven and the global "
         "financial crisis. There are three steps in this model.",
         "my experiences as CEO managing through 9-11 and the global "
         "financial crisis. There are three steps in this model.",
         _no_error),
        # 4346818: an APPROX range in the RENDER with no counterpart is the
        # mirror of `approxUnmatched`, which has never been gated.
        ("approximate range invented by the render",
         "Traffic revenues were down sharply, with Europe down 15% and "
         "Americas down 7%, all excluding effects.",
         "Traffic revenues were down in the mid-30s, with Europe down 15% and "
         "Americans down 7%, all excluding effects.",
         lambda r: _no_error(r) and r["approxInvented"] == 1),
    ]
    _spelling_cases += [
        # 4346818: Rev.com's own text carries the orphan scale word, so the
        # speaker said it. The rule is truth-free by design and had no way to
        # know that until the corpus arm started handing it the reference.
        ("orphan scale attested by the reference",
         "on the second quarter. Uh, from my, from the cost synergy "
         "perspective, million dollars, uh, you know, probably 80 to $90 million.",
         "on the second quarter. Uh from a from the the cost synergy "
         "perspective, million dollars, uh I mean uh out of the 80 to $90 million.",
         lambda r: r["spliceDefects"] == 0 and r["spliceScriptAttested"] == 1),
    ]
    _still_error = [
        # 4320211: the reference says it once, the render says it twice.
        ("orphan scale the reference does not carry",
         "the first nine months of the year, we spent approximately $104 "
         "million on acquisitions, including one to four store acquisitions.",
         "the first nine months of the year, we spent approximately $104 "
         "million. million on acquisitions, including one to four store acquisitions.",
         lambda r: r["spliceDefects"] == 1 and r["spliceScriptAttested"] == 0),
        # 4341191: the wrong figure at the same site. Values differ, so the
        # same-site rule cannot reach it however similar the neighbourhood.
        ("wrong figure in an identical sentence",
         "And that's really to cover $13 billion of GE and GE Capital long-term "
         "debt maturities now through 21.",
         "And that's really to cover 18 billion of DE and G capital long-term "
         "debt maturities now through 21.",
         lambda r: r["corruptions"] + r["hallucinatedNumbers"] >= 1
                   and r["spellingEquivalents"] == 0),
        # The same value, category-incompatible (so the LCS cannot anchor it)
        # and in a different paragraph: without the neighbourhood test this is
        # exactly the shape that would cancel a real drop against a real
        # invention — the self-referential excusing the frontier logic was
        # rewritten to avoid.
        ("same value in an unrelated place does not cancel",
         "Margins in aerospace represented 15% of our LTM revenues. Turning "
         "now to the balance sheet and our capital structure.",
         "Margins in aerospace represented a fraction of our LTM revenues. "
         "Turning now to the balance sheet and our capital structure. "
         "Separately we added 15 new distribution partners in Latin America.",
         lambda r: r["droppedFromRender"] == 1 and r["hallucinatedNumbers"] == 1
                   and r["spellingEquivalents"] == 0),
        ("a code shape the other side never writes stays invented",
         "Our team grew again over the period.",
         "Our team grew to 20 K over the period.",
         lambda r: r["hallucinatedNumbers"] == 1 and r["spellingEquivalents"] == 0),
        ("a scaled quantity is never a code",
         "We shipped units to customers in the quarter.",
         "We shipped 115 million units to customers in the quarter.",
         lambda r: r["hallucinatedNumbers"] == 1 and r["spellingEquivalents"] == 0),
    ]
    for label, ref_t, hyp_t, want in _spelling_cases + _still_error:
        res = score_number_fidelity(ref_t, hyp_t, [], complete=True)
        ok = want(res)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<44s} -> "
              f"corrupt={res['corruptions']} drop={res['droppedFromRender']} "
              f"inv={res['hallucinatedNumbers']} spelling={res['spellingEquivalents']}"
              f" (site {res['spellingSameSite']}/code {res['spellingEntityCode']})"
              f" approxInv={res['approxInvented']}")

    # A QUARTER's YEAR must be scored as its own quantity. This block is the
    # regression guard for the 2026-08-24 blind spot: the year used to ride in
    # the QUARTER's `unit` and was compared only when BOTH sides carried one, so
    # a render that DROPPED it scored a PERFECT match. That certified a seam arm
    # at 100.0% while "Q3 2020" was rendered "Q three." — the exact failure this
    # instrument exists to catch.
    print("\nQUARTER year is its own entity:")
    _script = "The impact of this sold in Q3 2020 was a net income benefit."
    _year_cases = [
        ("year dropped", "The impact of this sold in Q three. was a net income benefit.",
         lambda r: r["droppedFromRender"] == 1),
        ("year re-split (still correct)",
         "The impact of this sold in Q three. 2020 was a net income benefit.",
         lambda r: r["droppedFromRender"] == 0 and r["corruptions"] == 0),
        ("wrong year is ONE corruption, not two",
         "The impact of this sold in Q3 2019 was a net income benefit.",
         lambda r: r["corruptions"] == 1),
        ("inline correct", _script, lambda r: r["numberAccuracyPct"] == 100.0),
    ]
    for label, text, want in _year_cases:
        res = score_number_fidelity(_script, text, [])
        ok = want(res)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<40s} -> "
              f"drop={res['droppedFromRender']} corrupt={res['corruptions']} "
              f"acc={res['numberAccuracyPct']}")

    print("\n=== reference shapes (2026-08-27 corpus residuals) ===")
    _shape_cases = [
        ("bare `two quarters` is a count of two", "over the last two quarters revenue grew",
         "over the last 2 quarters revenue grew",
         lambda r: r["corruptions"] == 0 and r["droppedFromRender"] == 0),
        ("`three quarters of a percent` is still 0.75%", "rates fell three quarters of a percent",
         "rates fell 0.75%", lambda r: r["corruptions"] == 0 and r["droppedFromRender"] == 0),
        ("Rev `0.72 cents` is 72 cents", "Starting at continuing EPS of 0.72 cents.",
         "Starting at continuing EPS of 72 cents.",
         lambda r: r["corruptions"] == 0 and r["droppedFromRender"] == 0),
        ("a verbatim stutter `one one` is not a 2", "I'm just one other point worth mentioning.",
         "I'm just one one other point worth mentioning.",
         lambda r: r["corruptions"] == 0 and r["droppedFromRender"] == 0),
    ]
    for label, script, hyp, want in _shape_cases:
        res = score_number_fidelity(script, hyp, [])
        ok = want(res)
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<40s} -> "
              f"drop={res['droppedFromRender']} corrupt={res['corruptions']}")

    print("\n=== matcher: the unit is part of the quantity (audit 2026-08-24) ===")
    _unit_cases = [
        ("$77 million vs €77 million is NOT a match",
         NumberEntity("$77 million", "CURRENCY", 77e6, "USD"),
         NumberEntity("€77 million", "CURRENCY", 77e6, "EUR"), False),
        ("87 days vs 87 shares is NOT a match",
         NumberEntity("87 days", "QUANTITY", 87.0, "days"),
         NumberEntity("87 shares", "QUANTITY", 87.0, "shares"), False),
        ("21% vs 21 basis points is NOT a match (100x)",
         NumberEntity("21%", "PERCENTAGE", 21.0, "%"),
         NumberEntity("21 basis points", "BASIS_POINTS", 21.0, "bps"), False),
        ("21% vs 2100 basis points IS a match",
         NumberEntity("21%", "PERCENTAGE", 21.0, "%"),
         NumberEntity("2100 basis points", "BASIS_POINTS", 2100.0, "bps"), True),
        ("January 1st vs January 1 is one day",
         NumberEntity("1st", "ORDINAL", 1.0, "ordinal"),
         NumberEntity("1", "CARDINAL", 1.0, ""), True),
        ("32nd vs 32 is not a day",
         NumberEntity("32nd", "ORDINAL", 32.0, "ordinal"),
         NumberEntity("32", "CARDINAL", 32.0, ""), False),
        ("$11 million vs bare 11 million still matches (CARDINAL has no unit)",
         NumberEntity("$11 million", "CURRENCY", 11e6, "USD"),
         NumberEntity("11 million", "CARDINAL", 11e6, ""), True),
    ]
    for label, a, b, want in _unit_cases:
        got = is_canonical_match(a, b)
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<62s} -> {got}")

    print("\n=== splice rules: a spoken quarter before a year is not a splice ===")
    _splice_cases = [
        ("Q three 2020 is correct", "sold in Q three 2020, was a net", 0),
        ("q three 2020 (lowercase)", "sold in q three 2020 was", 0),
        ("twenty 2018 IS a splice", "since late twenty 2018 will continue", 1),
        ("three 2020 without Q IS a splice", "sold in three 2020 was", 1),
    ]
    for label, text, want in _splice_cases:
        hits = [d for d in find_splice_defects(text) if d["kind"] == "WORD_DIGIT_SPLICE"]
        ok = len(hits) == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<40s} -> {len(hits)} {[h['match'] for h in hits]}")

    print("\n=== reference shapes: currency word, compound split, forms, idioms, 1Q ===")
    _ref_cases = [
        ("$20.8 million Euros is EUR", "of $20.8 million Euros in", [("CURRENCY", 20.8e6, "EUR")]),
        ("€20.8 million stays EUR", "of €20.8 million in", [("CURRENCY", 20.8e6, "EUR")]),
        ("2 billion then 5 million people are two counts", "2 billion. 5 million people", [("CARDINAL", 2e9, ""), ("CARDINAL", 5e6, "")]),
        ("render-side $1 billion $275 million stays split (an ITN miss)", "of $1 billion $275 million to", [("CURRENCY", 1e9, "USD"), ("CURRENCY", 275e6, "USD")]),
        ("Form 10-K is not a ten", "our Form 10-K and 8-K filings", []),
        ("8Ks is not an eight", "filed at 8Ks and", []),
        ("nine eleven is an event", "managing through nine eleven and", []),
        ("twenty four seven is an idiom", "working twenty four seven", []),
        ("1Q is a quarter", "in 1Q and 2Q of", [("QUARTER", 1.0, ""), ("QUARTER", 2.0, "")]),
        ("one Q is a quarter", "in one Q and two Q", [("QUARTER", 1.0, ""), ("QUARTER", 2.0, "")]),
        ("Act of 199. is a truncated year", "Reform Act of 199. We", [("YEAR", 199.0, "year-prefix")]),
        ("June 30th is an ordinal day", "ended June 30th, 2020 reflect", [("ORDINAL", 30.0, "ordinal"), ("YEAR", 2020.0, "year")]),
        ("Phase III is phase 3", "from the Phase III GUARD trial", [("CARDINAL", 3.0, "")]),
        ("phase three is phase 3", "from the phase three guard trial", [("CARDINAL", 3.0, "")]),
        ("five and five eighths percent is 5.625%", "with five and five eighths percent notes", [("PERCENTAGE", 5.625, "%")]),
        ("5 5/8% is 5.625%", "with 5 5/8% notes", [("PERCENTAGE", 5.625, "%")]),
        ("three quarters of a percent is 0.75%", "up three quarters of a percent to", [("PERCENTAGE", 0.75, "%")]),
        ("Title IX matches title nine", "under Title IX rules", [("CARDINAL", 9.0, "")]),
        ("two and a half is not a fraction here (DECIMAL family owns it)", "two and a half million", [("CARDINAL", 2.5e6, "")]),

    ]
    for label, text, want in _ref_cases:
        got = [(e.category, e.canonical_value, e.unit) for e in extract_number_entities(text)]
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<48s} -> {got}")
    _ref_only = [
        ("REFERENCE $1 billion $275 million is one amount", "of $1 billion $275 million to", [("CURRENCY", 1.275e9, "USD")]),
        ("REFERENCE 1 billion $290 million likewise", "to 1 billion $290 million,", [("CURRENCY", 1.29e9, "USD")]),
    ]
    for label, text, want in _ref_only:
        got = [(e.category, e.canonical_value, e.unit) for e in extract_number_entities(text, reference=True)]
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<48s} -> {got}")

    print("\n=== splice rules: a decimal is not a duplicate, a date is not a splice ===")
    _shape_cases = [
        ("9.9% is one decimal, not `9` twice", "from 9.9% to 9.6%", "DUPLICATED_NUMBER", 0),
        ("$2.2 billion likewise", "free cash flow of $2.2 billion", "DUPLICATED_NUMBER", 0),
        ("2028 2028. IS a duplicate", "notes due 2028 2028. While", "DUPLICATED_NUMBER", 1),
        ("18 18.1% IS a duplicate", "increased 18 18.1% to", "DUPLICATED_NUMBER", 1),
        ("13 13,555 IS a duplicate", "was 13 13,555 thousand", "DUPLICATED_NUMBER", 1),
        ("September 30, 2020 is a date", "ended September 30, 2020 was", "ADJACENT_DIGIT_RUNS", 0),
        ("in 2021, 1.9 billion is a clause boundary", "no maturities in 2021, 1.9 billion of", "ADJACENT_DIGIT_RUNS", 0),
        ("13 1,300 hundred is an orphan scale, not adjacent runs", "approximately 13 1,300 hundred locations", "ADJACENT_DIGIT_RUNS", 0),
        ("13 1,300 locations IS adjacent runs", "approximately 13 1,300 locations", "ADJACENT_DIGIT_RUNS", 1),
        ("1000 1,289 IS adjacent runs", "had 1000 1,289 200. company", "ADJACENT_DIGIT_RUNS", 1),
        ("2 25 cents IS adjacent runs", "range of $2 25 cents to", "ADJACENT_DIGIT_RUNS", 1),
    ]
    for label, text, kind, want in _shape_cases:
        hits = [d for d in find_splice_defects(text) if d["kind"] == kind]
        ok = len(hits) == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<48s} -> {len(hits)} {[h['match'] for h in hits]}")

    # VALUE READING. Two gaps found 2026-08-28 scoring the row-ITN branch
    # against a main control: "two fifty" summed to 52 (implied hundreds), and
    # "-\u20ac33 million" lost its sign because the minus lookahead accepted only
    # "$". Both charged the render a corruption it did not commit.
    print("\nspoken value and signed currency:")
    _value_cases = [
        ("two fifty", 250.0), ("twelve fifty", 1250.0), ("fifty two", 52.0),
        ("three twenty five", 325.0), ("one twenty five million", 125e6),
        ("two hundred fifty", 250.0), ("nineteen ninety five", 1995.0),
    ]
    for phrase, want in _value_cases:
        got = parse_spoken_number_value(phrase)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {phrase:<48s} -> {got}")
    _signed_cases = [
        ("free cash flow was -\u20ac33 million in the quarter", -33e6),
        ("free cash flow was -$33 million in the quarter", -33e6),
        ("free cash flow was negative \u20ac33 million in the quarter", -33e6),
    ]
    for text, want in _signed_cases:
        vals = [e.canonical_value for e in extract_number_entities(text)]
        ok = want in vals
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {text:<48s} -> {vals}")

    print(f"\n{'\u2705 self-check passed' if not bad else f'\u274c {bad} failure(s)'}")
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# Corpus arm — the FINAL transcript, by value, against earnings21
# ---------------------------------------------------------------------------
#
# The live gate above scores what was on SCREEN on 7 golden pairs (146
# numbers, 58 of them from one earnings call). This arm scores what gets
# SAVED — the `_after_orphan.json` rows of a corpus run, the same text the
# meeting persists — on the 11 earnings21 calls (hundreds of numbers, Rev.com
# digit-form references). Two dumps of the same run, one before and one after
# the row-level ITN pass (`mimicscribe --itn-rows`), attribute every miss:
# wrong in both = the decoder/seam produced it; right before and wrong after
# = the normalizer broke it; wrong before and right after = a spoken form the
# value parser could not read that ITN wrote correctly.

# Bumped whenever a change to this file can move a gated count on an UNCHANGED
# transcript (a new excuse class, a matcher change, a category rule). A pin
# scored by one version and a change scored by another are two scorers, not
# two arms, and `corpus_compare` refuses the pair unless told otherwise. Pins
# written before the stamp existed carry no version and are treated as "0".
#   1  2026-09-01: spellingSameSite / spellingEntityCode / spliceScriptAttested
#      excuses (invented 112 -> 67), locality window on the entity-code excuse.
#   2  2026-09-01: the locality window is ANCHORED on the nearest matched
#      entity pair (relative position only as fallback), floor 1,500 -> 600.
SCORER_VERSION = 2

_CORPUS_GATED = ("corruptions", "droppedFromRender", "hallucinatedNumbers",
                 "spliceDefects", "hallucinatedHighSeverity")
# Counted and printed, never ratcheted: a spelling is not a wrong quantity, and
# a ratchet on one would fire on any legitimate rewording of a unit.
_CORPUS_REPORTED = ("spellingEquivalents", "spellingSameSite",
                    "spellingEntityCode", "approxInvented",
                    "spliceScriptAttested")


def nlp_reference_text(path: Path) -> str:
    """Rev.com `.nlp` -> running text with its punctuation column attached.

    A hyphen-terminated token binds to the NEXT token with no space: Rev
    writes the product code `ADX-2191` as the token `ADX-` then `2191`, and a
    space-join produced `ADX- 2191`, which neither entity mask
    matches — so the reference scored a code that the render side
    (`ADX 2191`, masked by the all-caps rule) never could. Six "dropped"
    numbers in `4366522` were that one asymmetry (2026-08-27)."""
    words: list[str] = []
    glue_next = False
    with open(path) as fh:
        fh.readline()  # token|speaker|ts|endTs|punctuation|case|tags|wer_tags
        for line in fh:
            cols = line.rstrip("\n").split("|")
            if len(cols) < 5 or not cols[0]:
                continue
            piece = cols[0] + (cols[4] or "")
            if glue_next and words:
                words[-1] += piece
            else:
                words.append(piece)
            # The hyphen rides the token itself (`ADX-`); a STANDALONE dash is
            # prose punctuation and must not swallow the next word (review 2).
            # Only a CODE-SHAPED stem glues (review 3, 2026-08-27): Rev also
            # writes a self-correction as a hyphen token (`to-` `40`, `mid-`
            # `2021`, `d-` `$100` — 749 of the 765 trailing hyphens in the 11
            # references are stutters or abandoned words), and gluing those
            # handed `to-40` / `mid-2021` to the hyphen mask, which hid the
            # reference number and charged the render with inventing it.
            glue_next = piece.endswith("-") and _code_shaped_stem(piece)
    return " ".join(words)


def _code_shaped_stem(piece: str) -> bool:
    """`ADX-`, `Q3-`, `B737-`: ≥ 2 alphanumerics, all-caps letters or a digit
    among them. `to-`, `mid-`, `d-`, `nove-` are prose and never glue."""
    core = piece.rstrip("-—–")
    core = "".join(ch for ch in core if ch.isalnum())
    if len(core) < 2 or not any(ch.isalpha() for ch in core):
        return False
    return any(ch.isdigit() for ch in core) or all(
        ch.isupper() for ch in core if ch.isalpha())


def corpus_rows_text(path: Path) -> str:
    raw = json.loads(path.read_text())
    segs = raw["segments"] if isinstance(raw, dict) else raw
    segs = sorted(segs, key=lambda s: s.get("startTime", 0.0))
    return " ".join(s.get("text", "") for s in segs)


def attribute(base: dict, post: dict) -> dict:
    """Join two arms number-by-number on the shared reference."""
    bo, po = base["refOutcomes"], post["refOutcomes"]
    assert len(bo) == len(po), "same reference must yield the same entity list"
    out = {"decoderOrSeam": 0, "itnBroke": 0, "itnFixed": 0,
           "itnBrokeDetails": [], "decoderDetails": []}
    for b, p in zip(bo, po):
        if p["outcome"] in ("notReached", "approx", "spelling"):
            continue
        b_ok, p_ok = b["outcome"] == "exact", p["outcome"] == "exact"
        if b_ok and not p_ok:
            out["itnBroke"] += 1
            out["itnBrokeDetails"].append(
                f"{p['raw']} -> before: {b['actual']!r} after: {p['actual']!r} ({p['outcome']})")
        elif not b_ok and p_ok:
            out["itnFixed"] += 1
        elif not b_ok and not p_ok:
            out["decoderOrSeam"] += 1
            out["decoderDetails"].append(f"{p['raw']} ({p['outcome']}, actual {p['actual']!r})")
    p_inv = list(post["hypInvented"])
    common = 0
    for x in base["hypInvented"]:
        if x in p_inv:
            p_inv.remove(x)
            common += 1
    out["decoderInvented"] = common
    out["itnInvented"] = len(p_inv)
    out["itnInventedDetails"] = p_inv[:10]
    out["decoderDetails"] = out["decoderDetails"][:10]
    out["itnBrokeDetails"] = out["itnBrokeDetails"][:15]
    return out


def score_corpus(per_file: Path, nlp_dir: Path, base_per_file: Path | None) -> dict:
    files: dict[str, dict] = {}
    for nlp in sorted(nlp_dir.glob("*.nlp")):
        fid = nlp.stem
        dump = per_file / f"{fid}_after_orphan.json"
        if not dump.exists():
            print(f"⚠️  {fid}: no {dump.name} under {per_file} — skipped")
            continue
        ref = nlp_reference_text(nlp)
        r = score_number_fidelity(ref, corpus_rows_text(dump), None, None, complete=True)
        r["substrate"] = str(dump)
        if base_per_file is not None:
            bdump = base_per_file / f"{fid}_after_orphan.json"
            if bdump.exists():
                b = score_number_fidelity(ref, corpus_rows_text(bdump), None, None,
                                          complete=True)
                r["attribution"] = attribute(b, r)
        files[fid] = r
        print_report(fid, r, dump.name)
        if "attribution" in r:
            a = r["attribution"]
            print(f"   attribution  decoder/seam {a['decoderOrSeam']}  "
                  f"itnBroke {a['itnBroke']}  itnFixed {a['itnFixed']}  "
                  f"itnInvented {a['itnInvented']}  decoderInvented {a['decoderInvented']}")
            for d in a["itnBrokeDetails"][:6]:
                print(f"      ITN broke: {d}")
        print()
    if not files:
        raise SystemExit("❌ scored nothing — a corpus report over zero files is vacuous")
    totals: dict[str, int] = {}
    by_cat: dict[str, dict[str, int]] = {}
    attr: dict[str, int] = {}
    for r in files.values():
        for k in ("scoredScriptNumbers", "exactMatches") + _CORPUS_GATED + _CORPUS_REPORTED:
            totals[k] = totals.get(k, 0) + int(r.get(k) or 0)
        for cat, d in r["byCategory"].items():
            for k, v in d.items():
                by_cat.setdefault(cat, {})[k] = by_cat.setdefault(cat, {}).get(k, 0) + v
        for k, v in r.get("attribution", {}).items():
            if isinstance(v, int):
                attr[k] = attr.get(k, 0) + v
    return {"scorerVersion": SCORER_VERSION,
            "files": files, "totals": totals, "byCategory": by_cat,
            "attribution": attr or None,
            "perFile": str(per_file), "basePerFile": str(base_per_file) if base_per_file else None}


def print_explain(files: dict[str, dict]) -> None:
    """Every reported error, one block each, with the text on both sides.

    Written for a HUMAN classification pass — the two axes the 2026-09-01 audit
    used are value-vs-spelling (format-equivalent / reference-artifact /
    genuine) and stage (decoder / seam / ITN / reference / not-inferable). Only
    the second axis needs anything this file does not hold, which is why it has
    a "not-inferable-from-text" value at all.
    """
    print("\n" + "=" * 78)
    print("EXPLAIN — every corrupted / dropped / invented number, with context")
    print("=" * 78)
    for fid, r in sorted(files.items()):
        print(f"\n### {fid}")
        for c in r["corruptionDetails"]:
            print(f"  CORRUPT [{c['category']}] {c['expected_raw']!r} -> {c['actual_raw']!r}")
            print(f"     ref: …{c.get('refContext', '')}…")
            print(f"     hyp: …{c.get('hypContext', '')}…")
        for d in r["droppedDetails"]:
            print(f"  DROPPED [{d['category']}] {d['raw']!r} ({d['value']})")
            print(f"     ref: …{d.get('refContext', '')}…")
            print(f"     hyp@pos: …{d.get('nearHyp', '')}…")
        for h in r["hallucinationDetails"]:
            print(f"  INVENTED [{h['category']}/{h['severity']}] {h['raw']!r} ({h['value']})")
            print(f"     hyp: …{h.get('hypContext', '')}…")
            print(f"     ref@pos: …{h.get('nearRef', '')}…")
        for s in r["spliceDefectDetails"]:
            print(f"  SPLICE  [{s['kind']}] {s['match']!r}")
            print(f"     ctx: …{s.get('context', '')}…")


def corpus_compare(pin_path: Path, chg_path: Path,
                   allow_cross_version: bool = False) -> int:
    pin, chg = json.loads(pin_path.read_text()), json.loads(chg_path.read_text())
    pv, cv = int(pin.get("scorerVersion", 0)), int(chg.get("scorerVersion", 0))
    if pv != cv:
        msg = (f"pin scored by scorer version {pv}, change by {cv}: two scorer "
               f"versions, not two arms. Re-pin with the current scorer "
               f"(`--corpus <control per-file> --json-out <new pin>`) or pass "
               f"--allow-cross-version to compare anyway and say so in the record.")
        if not allow_cross_version:
            print("❌ REFUSED: " + msg)
            return 2
        print("⚠️  CROSS-VERSION COMPARE: " + msg)
    failed = 0
    rows = []
    for fid, p in pin["files"].items():
        c = chg["files"].get(fid)
        if c is None:
            print(f"❌ {fid}: in the pin but not in the change — a missing file is not a pass")
            failed += 1
            continue
        if c["scoredScriptNumbers"] != p["scoredScriptNumbers"]:
            print(f"⚠️  {fid}: scored {p['scoredScriptNumbers']} -> {c['scoredScriptNumbers']} "
                  f"(reference or substrate changed; the per-key compare below is still run)")
        for k in _CORPUS_GATED:
            pv, cv = int(p.get(k) or 0), int(c.get(k) or 0)
            if cv > pv:
                failed += 1
                rows.append(f"❌ {fid:9} {k:24} {pv:4} -> {cv:4}")
            elif cv < pv:
                rows.append(f"✅ {fid:9} {k:24} {pv:4} -> {cv:4}")
    print("\n".join(rows) or "(no per-file movement)")
    pt, ct = pin["totals"], chg["totals"]
    print("\nTOTALS  " + "  ".join(f"{k} {pt.get(k, 0)}->{ct.get(k, 0)}"
                                    for k in ("exactMatches",) + _CORPUS_GATED))
    print("❌ REGRESSED" if failed else "✅ GOOD — no gated count rose on any file")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Score live number fidelity, ITN and splice defects (INV-NUM)")
    ap.add_argument("out_dir", type=Path, nargs="?", help="replay output directory")
    ap.add_argument("--script", type=Path,
                    help="path to the performed script.txt (single-dir runs only)")
    ap.add_argument("--all", type=Path, metavar="REPLAY_ROOT",
                    help="TRIAGE sweep of every REPLAY_ROOT/<pair>/ with a "
                         "live-ticks.jsonl. The GATE is `score_live_invariants.py "
                         "--all` + `--compare`, which is what reads the INV-NUM "
                         "ratchet; this sweep only prints and dumps per-pair detail")
    ap.add_argument("--pairs-root", type=Path,
                    default=Path(__file__).resolve().parent.parent
                    / "Tests" / "Fixtures" / "golden_pairs",
                    help="where <pair>/script.txt and <pair>/system.wav live "
                         "(default: repo golden pairs)")
    ap.add_argument("--hypothesis", choices=("ticks", "segments", "auto"),
                    default="ticks",
                    help="which rendering to score; 'ticks' (default) is what the "
                         "user read, 'segments' is the PRE-ITN dump (triage only)")
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--corpus", type=Path, metavar="PER_FILE_DIR",
                    help="FINAL-transcript arm: score every earnings21 "
                         "<fid>_after_orphan.json under PER_FILE_DIR by value "
                         "against benchmark/data/earnings21/nlp_references")
    ap.add_argument("--corpus-base", type=Path, metavar="PRE_ITN_PER_FILE_DIR",
                    help="the same run's PRE-ITN dumps, to attribute each miss "
                         "to the decoder/seam or to the normalizer")
    ap.add_argument("--nlp-dir", type=Path,
                    default=(Path(os.environ["MIMICSCRIBE_CORPUS_DATA"]) / "earnings21" / "nlp_references")
                    if os.environ.get("MIMICSCRIBE_CORPUS_DATA")
                    else Path(__file__).resolve().parent.parent
                    / "benchmark" / "data" / "earnings21" / "nlp_references")
    ap.add_argument("--corpus-compare", type=Path, nargs=2, metavar=("PIN", "CHG"),
                    help="ratchet a --corpus --json-out result against a pin: "
                         "no gated count may rise on any file")
    ap.add_argument("--allow-cross-version", action="store_true",
                    help="let --corpus-compare run across two scorer versions "
                         "(printed as a warning; the honest fix is a re-pin)")
    ap.add_argument("--explain", action="store_true",
                    help="print EVERY corrupted / dropped / invented number with "
                         "its own context and the reference text at the same "
                         "proportional position (uncapped detail lists). Reading "
                         "class, not a gate.")
    ap.add_argument("--self-check", action="store_true",
                    help="verify the non-numeric-sense filter against verbatim "
                         "golden-pair spans; needs no data and no API key")
    args = ap.parse_args()

    global EXPLAIN
    EXPLAIN = bool(args.explain)

    if args.self_check:
        return _self_check()
    if args.corpus_compare:
        return corpus_compare(*args.corpus_compare,
                              allow_cross_version=args.allow_cross_version)
    if args.corpus:
        blob = score_corpus(args.corpus, args.nlp_dir, args.corpus_base)
        if EXPLAIN:
            print_explain(blob["files"])
        t, bc = blob["totals"], blob["byCategory"]
        print(f"CORPUS TOTALS  scored {t['scoredScriptNumbers']}  exact {t['exactMatches']}  "
              + "  ".join(f"{k} {t[k]}" for k in _CORPUS_GATED))
        print("CORPUS REPORTED (not gated)  "
              + "  ".join(f"{k} {t.get(k, 0)}" for k in _CORPUS_REPORTED))
        for cat, d in sorted(bc.items(), key=lambda kv: -kv[1].get("scored", 0)):
            print(f"   {cat:13} " + "  ".join(f"{k} {v}" for k, v in d.items()))
        if blob["attribution"]:
            print("ATTRIBUTION  " + "  ".join(f"{k} {v}" for k, v in blob["attribution"].items()))
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(blob, indent=2))
            print(f"\n📊 wrote {args.json_out}")
        return 0

    if not args.out_dir and not args.all:
        print("❌ need an out_dir or --all")
        return 2
    if args.all and args.script:
        # One --script across N pairs scores every pair against one ground
        # truth and reports identical, meaningless numbers for all of them.
        print("❌ --script is a single-pair flag; with --all each pair takes "
              "<pairs-root>/<pair>/script.txt")
        return 2

    def score_one(out_dir: Path, script_path: Path, pair_dir: Path | None) -> dict | None:
        if not script_path.exists():
            print(f"⚠️  {out_dir.name}: no script at {script_path} — skipped")
            return None
        refusal = script_refusal(script_path)
        if refusal:
            print(f"⚠️  {out_dir.name}: {refusal} — skipped (INV-NUM needs a "
                  f"performed script, same bar as INV-4/5)")
            return None
        hyp, ticks, label = resolve_hypothesis(out_dir, args.hypothesis)
        if not hyp:
            print(f"⚠️  {out_dir.name}: no {args.hypothesis} rendering found — skipped")
            return None
        result = score_number_fidelity(
            script_body_text(script_path), hyp, ticks,
            audio_duration=audio_duration_seconds(out_dir, pair_dir))
        result["dir"] = str(out_dir)
        result["substrate"] = label
        print_report(out_dir.name, result, label)
        return result

    if args.all:
        dirs = sorted(d for d in args.all.iterdir()
                      if d.is_dir() and (d / "live-ticks.jsonl").exists())
        if not dirs:
            print(f"❌ no <pair>/live-ticks.jsonl under {args.all}")
            return 2
        pairs: dict[str, dict] = {}
        for d in dirs:
            pair_dir = args.pairs_root / d.name
            r = score_one(d, pair_dir / "script.txt", pair_dir)
            if r:
                pairs[d.name] = r
            print()
        if not pairs:
            print("❌ scored nothing — a report over zero pairs is a vacuous PASS")
            return 2
        blob: dict = {"scorerVersion": SCORER_VERSION, "pairs": pairs}
        failed = [n for n, r in pairs.items() if r["vacuousRender"]]
    else:
        pair_dir = args.pairs_root / args.out_dir.name
        script_path = args.script or (pair_dir / "script.txt")
        blob = score_one(args.out_dir, script_path,
                         pair_dir if pair_dir.exists() else None) or {}
        if not blob:
            return 2
        failed = [args.out_dir.name] if blob["vacuousRender"] else []

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(blob, indent=2))
        print(f"\n📊 wrote {args.json_out}")
    if failed:
        print(f"\n❌ VACUOUS RENDER on: {' '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
