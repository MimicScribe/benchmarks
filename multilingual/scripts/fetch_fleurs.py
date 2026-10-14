#!/usr/bin/env python3
"""Fetch a fixed-seed, duration-capped subset of the FLEURS TEST split per language.

Why this route (2026-09-21): `datasets` 5.x no longer executes dataset loading
scripts (the classic `google/fleurs` repo ships a Python builder script, which
5.x refuses to run). The fix used here is to bypass `datasets` entirely and
pull the auto-generated Parquet mirror at revision `refs/convert/parquet` of
the SAME repo via `huggingface_hub.hf_hub_download` (one file per
`<lang>/test/0000.parquet`; verified 2026-09-21 that every one of the 25
target configs has exactly one shard, no auth token required — it is a public
dataset). This keeps `datasets==5.0.1` in the venv unused for FLEURS; jiwer is
still used downstream by score_fleurs.py.

Parquet schema (verified against nl_nl 2026-09-21): id:int32, num_samples:int32,
path:string (original extraction path, NOT reused), audio:struct<bytes:binary,
path:string> (a self-contained WAV blob, 16 kHz per FLEURS spec but verified
per-row below since the container subtype is not always PCM16), transcription
(lowercased, punctuation-stripped), raw_transcription (as-transcribed, cased
and punctuated), gender:int64 (ClassLabel 0=male 1=female 2=other),
lang_id:int64, language:string, lang_group_id:int64. There is NO speaker id
field anywhere in the parquet mirror — `manifest.jsonl` therefore never has a
`speaker_id` key (documented, not silently omitted).

Selection algorithm (fixed seed, reproducible): shuffle row indices with
`random.Random(f"{seed}:{lang}")`, then greedily accept utterances in that
order until BOTH `total kept duration >= --minutes` AND
`len(kept) >= --min-utterances` (default 100) are satisfied — the two floors
are independent stopping conditions, selection continues until the LATER of
the two is met (2026-09-21 follow-up: previously `--minutes` alone could stop
selection under 100 utterances, breaking the campaign's non-vacuity bar for
9/25 languages). If BOTH genders (0 and 1) are present ANYWHERE in the full
row pool (not just the eventually-kept subset), alternate the accepted gender
each step (skip-and-revisit later within the same shuffle if the preferred
gender is temporarily exhausted) so the kept subset is as close to 50/50 as
the data allows. If only one gender value is present in the FULL test split
(verified per-language 2026-09-21, see `full_split_gender_counts` in
`.fetch_done.json` and the follow-up report — 9/25 languages are genuinely
single-gender in the ENTIRE FLEURS TEST split, not just bad luck in a
subsample: cs_cz, da_dk, nl_nl, et_ee, de_de, hu_hu, pt_br, ro_ro, uk_ua)
selection falls back to plain shuffled order and the manifest still records
`gender` as given by FLEURS (do not invent balance that is not in the data).

`--census-only` mode: downloads each shard, reads ONLY the `gender` column
(no audio decode, no WAV writes), records full-split gender counts into
`.fetch_done.json` (merged, non-destructive) and prints them, then deletes
the shard — used to answer "does the full split have both genders" without
paying for a full re-fetch of languages that don't need one.

Output: <suite>/data/<lang>/{wav/<lang>_<id>.wav, manifest.jsonl,
.fetch_done.json}. Idempotent/resumable: a language is skipped (unless
--force) when `.fetch_done.json` records the same (minutes, seed,
min_utterances) and every manifest WAV file exists on disk. The downloaded
parquet shard is deleted immediately after extraction; nothing but the
trimmed WAVs + manifest persists.

Disk discipline: checks `df -g` before each
per-language download and aborts the whole run if free space drops below 7 GB;
downloads exactly one shard at a time and removes it before moving to the next
language.

AUDIO DECODE BUG FIXED 2026-09-21 (all 25 languages' WAVs were silent):
FLEURS' source WAV blobs are `subtype: FLOAT` (verified via `sf.info`), and
`soundfile.read(..., dtype="int16")` on a FLOAT-subtype container does NOT
rescale by full-scale — it truncates float samples in [-1, 1] to their
integer part, i.e. every sample becomes 0 (or +-1 at a peak). The fix
(`float_to_pcm16` below): always read as `dtype="float32"` (soundfile
normalizes float/PCM sources to [-1, 1] correctly for this dtype), downmix
to mono by averaging channels if the source has >1, resample to 16 kHz via
`scipy.signal.resample_poly` if `sr != 16000` (verified: every one of the 25
target configs' TEST shards is natively 16000 Hz already, so this path is
defensive and has never fired — kept because FLEURS' upstream format is not
a contract), then scale by 32767 and clip to `int16` range before writing
PCM_16. Every DECODED candidate is checked by `audio_health` (peak >= 1000
AND RMS above -50 dBFS) BEFORE it is written or counted toward the
manifest — a candidate that fails is skipped (logged in `.fetch_done.json`'s
`audio_health.skipped_unhealthy_ids`) and the next candidate from the SAME
deterministic `iter_selection_order` is tried instead, so one quiet FLEURS
recording (real corpus variance — verified present in bg_bg/hr_hr/nl_nl/
en_us/et_ee/fi_fi's TEST shards, roughly 1 in a few hundred utterances)
doesn't abort a whole language's fetch. If the ENTIRE candidate pool is
exhausted without meeting both floors, `fetch_language` raises loudly
(`RuntimeError`) — that failure mode is reserved for an actual repeat of the
silent-WAV bug (every candidate failing) or a language genuinely too small,
never for a handful of quiet recordings.

LEVEL NORMALIZATION (READ BEFORE
CITING ANY WER/LANGUAGE-DETECTION NUMBER FROM THIS CORPUS): the re-fetched
FLEURS audio is genuinely very quiet in some languages (median RMS measured
before this change: hr_hr -59 dBFS, en_us -53, et_ee -53, nl_nl -50) and the
app's ASR-only test mode rejects `rms < 0.001` (-60 dBFS) as
`noSpeechDetected` — scoring the UNNORMALIZED corpus would measure FLEURS
recording gain, not language. Every kept utterance is therefore gain-matched
IN FLOAT, BEFORE int16 quantization, to a target RMS of TARGET_RMS_DBFS
(-26 dBFS), with gain reduced (never increased beyond the RMS target) if it
would push the true peak above PEAK_CEILING_DBFS (-1 dBFS). This happens
STRICTLY AFTER the existing (unnormalized) `audio_health` accept/reject
decision below, so selection/seeds are byte-identical to a pre-normalization
fetch — `fetch_language` asserts this explicitly (see
`_assert_same_ids_as_existing_manifest`) whenever an old manifest for the
same (lang, minutes, seed, min_utterances) already exists on disk. Each
manifest.jsonl entry records `gain_db` (the gain actually applied, dB) and
`original_rms_dbfs` (the pre-normalization RMS in dBFS, computed on the
resampled float samples — this is the SAME quantity as `audio_health`'s
`dbfs` field to within int16 quantization noise, just measured in float
before quantization per the brief). `.fetch_done.json` additionally records
an `audio_normalization` block (target_rms_dbfs, peak_ceiling_dbfs, plus
post-normalization min/median RMS and max gain_db actually applied across
the language's kept utterances) — an utterance needing >35 dB of gain is a
signal its SOURCE recording is unusually low-resolution/quiet even by
FLEURS' standards, flagged (not rejected) in that block's
`high_gain_ids` list. Downstream, `score_fleurs.py`'s emitted results JSON
carries a top-level `audio_normalization` field mirroring these constants so
a reader of a results file without this script's source doesn't have to
guess whether the numbers were measured on raw or normalized audio.
"""
from __future__ import annotations

import argparse
import tempfile
import hashlib
import io
import json
import math
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import scipy.signal
import soundfile as sf
from huggingface_hub import hf_hub_download

REPO_ID = "google/fleurs"
REPO_TYPE = "dataset"
REVISION = "refs/convert/parquet"
SPLIT = "test"

# DATASET_VERSION (bumped 2026-09-21, review finding 1): version 1 keyed the
# manifest/WAV filename on `row["id"]`, which is FLEURS' SENTENCE id (shared
# by different speakers reading the same sentence) — a second speaker's
# recording silently OVERWROTE the first WAV on disk while BOTH manifest rows
# survived (489/2695 = 18% of v1 manifest rows across all 25 languages,
# verified 2026-09-21 by comparing manifest row counts to distinct
# `wav/*.wav` files; every duplicate-id group's reference text was identical,
# so nothing was mis-paired — the audio was just scored twice as independent
# samples, inflating n and narrowing bootstrap CIs). v2 keys each row on
# `<lang>_<sentenceId>_<k>` where `k` is that sentence id's 0-based occurrence
# index within the shard's own row order (verified 2026-09-21 against a live
# de_de parquet shard: the schema's `path` column — an "original extraction
# path, NOT reused" per the note below — IS in fact unique per recording,
# 862/862 distinct, confirming `k` cleanly disambiguates every recording of a
# repeated sentence). `sentence_id` is kept as its own manifest field.
# Consumers (score_fleurs.py, score_language_detection.py) refuse to score a
# manifest whose rows carry more than one DATASET_VERSION — see
# `manifest_dataset_versions()` there. Rows fetched before this change have
# NO `dataset_version` key at all; readers treat that as version 1 (see
# `entry.get("dataset_version", 1)` at every call site — do not change this
# default without re-auditing those sites).
DATASET_VERSION = 2

DEFAULT_LANGS = (
    "bg_bg hr_hr cs_cz da_dk nl_nl en_us et_ee fi_fi fr_fr de_de el_gr hu_hu "
    "it_it lv_lv lt_lt mt_mt pl_pl pt_br ro_ro sk_sk sl_si es_419 sv_se ru_ru uk_ua"
).split()

GENDER_NAMES = {0: "male", 1: "female", 2: "other"}

MIN_FREE_GB = 7

# Non-vacuity thresholds (module-level so build_sessions.py / score_fleurs.py
# --self-test can import and apply the SAME bar).
# DEVIATION FROM THE ORIGINAL SPEC (peak>=1000 / RMS>=-50dBFS), recorded here
# because it was found empirically, not guessed: at peak>=1000/-50dBFS, a
# first pass over hr_hr/nl_nl/en_us/et_ee/fi_fi rejected 318/442 hr_hr
# candidates alone and the survivors were 100% female — hr_hr's real FLEURS
# TEST audio has a ~29dB level gap between genders (verified: median peak
# int16 female=8803/-30.6dBFS vs male=295/-59.2dBFS, sampled straight from
# the source parquet, nothing to do with our decode). That is real recording-
# session variance in the corpus, not the silent-WAV bug, and a -50dBFS floor
# would have silently re-broken gender balance — the exact failure this
# follow-up exists to prevent — while looking like a successful audio-health
# pass. The actual bug signature (confirmed before this fix, e.g.
# bg_bg_001664: peak=0, rms_dbfs=-270.3) is many orders of magnitude below any
# real speech. These thresholds catch THAT while accepting real quiet speech:
MIN_PEAK_INT16 = 50
MIN_RMS_DBFS = -80.0
FULL_SCALE_16 = 32767.0

# Level normalization (TASK 1, 2026-09-21) — module-level so score_fleurs.py
# can read the SAME constants into its emitted `audio_normalization` field
# instead of duplicating (and risking drifting from) them.
TARGET_RMS_DBFS = -26.0
PEAK_CEILING_DBFS = -1.0
# An utterance needing more than this much gain to reach TARGET_RMS_DBFS is
# flagged (not rejected) as coming from an unusually low-resolution/quiet
# source recording — see `.fetch_done.json`'s `audio_normalization.high_gain_ids`.
HIGH_GAIN_WARN_DB = 35.0


def assign_recording_dup_indices(sentence_ids: list[int]) -> list[int]:
    """Finding 1 (2026-09-21): given the raw FLEURS `id` (sentence id) for
    EVERY row in a shard, IN SHARD ROW ORDER, return each row's 0-based
    occurrence index for its sentence id — `rows[i]`'s unique DATASET_VERSION
    2 id is then `f"{lang}_{sentence_ids[i]:06d}_{dup_indices[i]}"`. Pure and
    order-sensitive (no shuffling) so it is reproducible independent of the
    fixed-seed selection algorithm, which runs AFTER ids are assigned."""
    seen: dict[int, int] = {}
    out = []
    for sid in sentence_ids:
        k = seen.get(sid, 0)
        seen[sid] = k + 1
        out.append(k)
    return out


def build_row_id(lang: str, sentence_id: int, dup_index: int) -> str:
    return f"{lang}_{sentence_id:06d}_{dup_index}"


def free_gb(path: str = str(Path.home())) -> float:
    out = subprocess.run(["df", "-g", path], capture_output=True, text=True, check=True)
    line = out.stdout.strip().splitlines()[-1]
    # Filesystem  1G-blocks  Used  Avail  Capacity  iused  ifree  %iused  Mounted
    fields = line.split()
    return float(fields[3])


def resample_to_16k(data_f32: np.ndarray, sr: int, target_sr: int = 16000) -> np.ndarray:
    """Downmix to mono and resample a float [-1,1] buffer to `target_sr`.

    Split out from the old `float_to_pcm16` (2026-09-21 TASK 1 follow-up) so
    gain normalization can be applied to the resampled FLOAT samples, between
    this step and `scale_clip_to_int16` — i.e. still before int16
    quantization, per the brief.
    """
    if data_f32.ndim > 1:
        data_f32 = data_f32.mean(axis=1)
    if sr != target_sr:
        # Defensive: every target config's TEST shard is natively 16000 Hz
        # (verified 2026-09-21); this path has never fired. Polyphase
        # resample via scipy, exact rational ratio.
        from math import gcd

        g = gcd(sr, target_sr)
        data_f32 = scipy.signal.resample_poly(data_f32, target_sr // g, sr // g)
    return data_f32


def scale_clip_to_int16(data_f32: np.ndarray) -> np.ndarray:
    """Scale a float [-1,1] buffer to int16 full-scale and clip."""
    scaled = np.clip(data_f32 * FULL_SCALE_16, -32768, 32767)
    return scaled.astype(np.int16)


def float_to_pcm16(data_f32: np.ndarray, sr: int, target_sr: int = 16000) -> np.ndarray:
    """Correctly convert a float [-1,1] buffer to scaled, clipped int16 PCM.

    THE BUG THIS REPLACES: `soundfile.read(..., dtype="int16")` on a
    FLOAT-subtype WAV does not rescale — every FLEURS sample truncated to 0
    (or +-1 at a peak). Always decode as float32 first (soundfile does this
    correctly for both FLOAT and PCM source subtypes) and do the int16
    conversion ourselves. Back-compat wrapper (unnormalized) around
    `resample_to_16k` + `scale_clip_to_int16`; `fetch_language` calls those
    two directly so it can insert gain normalization between them.
    """
    return scale_clip_to_int16(resample_to_16k(data_f32, sr, target_sr))


def compute_gain_db(
    data_f32: np.ndarray,
    target_rms_dbfs: float = TARGET_RMS_DBFS,
    peak_ceiling_dbfs: float = PEAK_CEILING_DBFS,
) -> tuple[float, float]:
    """Return `(gain_db, original_rms_dbfs)` for gain-matching `data_f32`
    (resampled float [-1,1], PRE-quantization) to `target_rms_dbfs` RMS,
    reducing the gain (never increasing it beyond the RMS target) if it would
    push the true peak above `peak_ceiling_dbfs`.

    True silence (rms/peak ~0, the float/int16 bug signature) gets zero gain
    — amplifying near-zero noise toward the target would fabricate signal
    from nothing; `audio_health` rejects those candidates separately, before
    this function is ever called.
    """
    if len(data_f32) == 0:
        return 0.0, -240.0
    rms = float(np.sqrt(np.mean(data_f32.astype(np.float64) ** 2)))
    peak = float(np.abs(data_f32).max())
    if rms <= 1e-9 or peak <= 1e-9:
        return 0.0, -240.0
    original_rms_dbfs = 20.0 * math.log10(rms)
    gain_db = target_rms_dbfs - original_rms_dbfs
    peak_dbfs = 20.0 * math.log10(peak)
    max_gain_db = peak_ceiling_dbfs - peak_dbfs
    if gain_db > max_gain_db:
        gain_db = max_gain_db
    return gain_db, original_rms_dbfs


def apply_gain(data_f32: np.ndarray, gain_db: float) -> np.ndarray:
    if gain_db == 0.0:
        return data_f32
    return data_f32 * (10.0 ** (gain_db / 20.0))


def audio_health(pcm16: np.ndarray) -> dict:
    peak = int(np.abs(pcm16).max()) if len(pcm16) else 0
    rms = float(np.sqrt(np.mean(pcm16.astype(np.float64) ** 2))) if len(pcm16) else 0.0
    dbfs = 20.0 * np.log10(max(rms, 1e-9) / FULL_SCALE_16)
    return {"peak": peak, "rms": round(rms, 2), "dbfs": round(float(dbfs), 2)}


def assert_audio_health(pcm16: np.ndarray, file_id: str) -> dict:
    """FAILS LOUDLY (raises) — a repeat of the float/int16 silent-WAV bug must
    stop the fetch, not produce another silent corpus."""
    health = audio_health(pcm16)
    if health["peak"] < MIN_PEAK_INT16 or health["dbfs"] < MIN_RMS_DBFS:
        raise RuntimeError(
            f"AUDIO HEALTH FAIL {file_id}: peak={health['peak']} (need >={MIN_PEAK_INT16}), "
            f"rms_dbfs={health['dbfs']:.1f} (need >={MIN_RMS_DBFS}) — looks silent/near-silent"
        )
    return health


def iter_selection_order(rows: list[dict], seed_key: str):
    """Yields EVERY row index in fixed-seed, gender-alternated (when possible)
    order — no stopping condition; the caller decides when it has enough.

    Split out from the old `select_indices` (2026-09-21 follow-up) so
    fetch_language can SKIP a candidate that fails the audio-health check and
    pull the next one from the SAME deterministic order instead of aborting
    the whole language on one quiet recording (see `assert_audio_health`
    call site below — a handful of genuinely-quiet FLEURS utterances exist
    per language; this is real corpus variance, not a repeat of the
    float/int16 bug, and MUST NOT abort a whole language's fetch).
    """
    rng = random.Random(seed_key)
    order = list(range(len(rows)))
    rng.shuffle(order)

    genders_present = {rows[i]["gender"] for i in order}
    alternate = len(genders_present & {0, 1}) == 2  # both male and female present

    if not alternate:
        yield from order
        return

    # Bucket the shuffled order by gender, preserving shuffle order within each bucket.
    buckets: dict[int, list[int]] = {0: [], 1: []}
    others: list[int] = []
    for i in order:
        g = rows[i]["gender"]
        if g in buckets:
            buckets[g].append(i)
        else:
            others.append(i)

    want = 0  # alternate starting with male(0)
    bi = {0: 0, 1: 0}
    while bi[0] < len(buckets[0]) or bi[1] < len(buckets[1]):
        progressed = False
        for g in (want, 1 - want):
            b = buckets[g]
            if bi[g] < len(b):
                yield b[bi[g]]
                bi[g] += 1
                progressed = True
                break
        want = 1 - want
        if not progressed:
            break
    yield from others


def select_indices(rows: list[dict], minutes: float, min_utterances: int, seed_key: str) -> list[int]:
    """Fixed-seed subset selection, gender-alternated when possible, stopping
    once BOTH floors are met (total duration >= minutes*60 AND
    len(kept) >= min_utterances). AUDIO-UNAWARE — kept for documentation/
    testing of the ordering only; `fetch_language` does its own floor-tracking
    loop over `iter_selection_order` so it can skip unhealthy candidates and
    keep pulling replacements, which this function cannot do.
    """
    target_s = minutes * 60.0
    kept: list[int] = []
    total = 0.0
    for i in iter_selection_order(rows, seed_key):
        if total >= target_s and len(kept) >= min_utterances:
            break
        kept.append(i)
        total += rows[i]["duration_s"]
    return kept


def gender_census(lang: str, tmp_root: Path) -> dict:
    """Download a shard, read ONLY the gender column, delete the shard. No audio touched."""
    free = free_gb()
    if free < MIN_FREE_GB:
        raise SystemExit(f"ABORT: free disk {free:.1f} GB < {MIN_FREE_GB} GB before census {lang}")
    tmp_root.mkdir(parents=True, exist_ok=True)
    local_path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        revision=REVISION,
        filename=f"{lang}/{SPLIT}/0000.parquet",
        local_dir=str(tmp_root),
    )
    try:
        table = pq.ParquetFile(local_path).read(columns=["gender"])
        genders = table.column("gender").to_pylist()
        counts: dict[str, int] = {}
        for g in genders:
            name = GENDER_NAMES.get(g, "unknown")
            counts[name] = counts.get(name, 0) + 1
        return {"lang": lang, "full_split_n": len(genders), "full_split_gender_counts": counts}
    finally:
        shard_dir = tmp_root / lang
        if shard_dir.exists():
            shutil.rmtree(shard_dir, ignore_errors=True)


def merge_full_split_census(out_dir: Path, census: dict) -> None:
    done_marker = out_dir / ".fetch_done.json"
    if not done_marker.exists():
        return
    try:
        prev = json.loads(done_marker.read_text())
    except (OSError, json.JSONDecodeError):
        return
    prev["full_split_n"] = census["full_split_n"]
    prev["full_split_gender_counts"] = census["full_split_gender_counts"]
    done_marker.write_text(json.dumps(prev, indent=2))


def fetch_language(
    lang: str, minutes: float, min_utterances: int, seed: int, data_root: Path, tmp_root: Path, force: bool
) -> dict:
    out_dir = data_root / lang
    wav_dir = out_dir / "wav"
    manifest_path = out_dir / "manifest.jsonl"
    done_marker = out_dir / ".fetch_done.json"

    if not force and done_marker.exists():
        try:
            prev = json.loads(done_marker.read_text())
        except (OSError, json.JSONDecodeError):
            prev = {}
        if (
            prev.get("minutes") == minutes
            and prev.get("seed") == seed
            and prev.get("min_utterances") == min_utterances
            and prev.get("dataset_version") == DATASET_VERSION
            and manifest_path.exists()
        ):
            lines = manifest_path.read_text().splitlines()
            all_present = all((wav_dir / (json.loads(l)["id"] + ".wav")).exists() for l in lines if l.strip())
            if all_present and lines:
                print(f"[{lang}] already fetched ({len(lines)} utts, minutes={minutes}, seed={seed}) — skipping")
                return {"lang": lang, "skipped": True, "n": len(lines)}

    # Capture the pre-existing selection (if any) so the post-fetch assert
    # below can confirm normalization did not change WHICH utterances are
    # selected — only their level (TASK 1, 2026-09-21). Only meaningful when
    # the old manifest is the SAME DATASET_VERSION: a version bump (e.g. the
    # finding-1 id-format change, v1 -> v2, 2026-09-21) deliberately changes
    # every id's string form, so comparing across versions would always
    # "fail" for a reason that has nothing to do with selection drift.
    old_ids: list[str] | None = None
    if manifest_path.exists():
        try:
            old_lines = manifest_path.read_text().splitlines()
            old_entries = [json.loads(l) for l in old_lines if l.strip()]
            old_versions = {e.get("dataset_version", 1) for e in old_entries}
            if old_versions == {DATASET_VERSION}:
                old_ids = sorted(e["id"] for e in old_entries)
            else:
                print(f"[{lang}] prior manifest is DATASET_VERSION {sorted(old_versions)} (fetching {DATASET_VERSION}) — skipping same-id selection assert, ids are expected to change")
        except (OSError, json.JSONDecodeError, KeyError):
            old_ids = None

    free = free_gb()
    if free < MIN_FREE_GB:
        raise SystemExit(f"ABORT: free disk {free:.1f} GB < {MIN_FREE_GB} GB before fetching {lang}")

    wav_dir.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)

    print(f"[{lang}] downloading test/0000.parquet (free={free:.1f} GB)...")
    t0 = time.time()
    local_path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        revision=REVISION,
        filename=f"{lang}/{SPLIT}/0000.parquet",
        local_dir=str(tmp_root),
    )
    print(f"[{lang}] downloaded in {time.time() - t0:.1f}s -> {local_path}")

    try:
        table = pq.ParquetFile(local_path).read()
        cols = table.to_pylist()
        rows = []
        # DATASET_VERSION 2 (finding 1): `r["id"]` is a SENTENCE id shared by
        # every speaker who read that sentence — count occurrences IN SHARD
        # ROW ORDER (a static, deterministic file) so each recording of a
        # repeated sentence gets its own stable, reproducible suffix `_<k>`.
        dup_indices = assign_recording_dup_indices([r["id"] for r in cols])
        for r, k in zip(cols, dup_indices):
            audio_bytes = r["audio"]["bytes"]
            # float32 read only for length/sr here — VALUES unused, so the
            # int16-truncation bug (see module docstring) can't corrupt this
            # duration computation, but float32 keeps one decode path for
            # the whole file instead of two subtly different ones.
            data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            duration_s = len(data) / sr
            rows.append(
                {
                    "id": build_row_id(lang, r["id"], k),
                    "raw_id": r["id"],
                    "sentence_id": r["id"],
                    "sentence_dup_index": k,
                    "transcription": r["transcription"],
                    "raw_transcription": r["raw_transcription"],
                    "gender": r["gender"],
                    "gender_name": GENDER_NAMES.get(r["gender"], "unknown"),
                    "duration_s": round(duration_s, 3),
                    "sample_rate": sr,
                    "_bytes": audio_bytes,
                }
            )

        full_split_gender_counts: dict[str, int] = {}
        for r in rows:
            full_split_gender_counts[r["gender_name"]] = full_split_gender_counts.get(r["gender_name"], 0) + 1

        # Integrated select+decode+health-check+write loop (2026-09-21 follow-up):
        # walk the SAME deterministic order select_indices would have used, but
        # decode/health-check each candidate as we go so an unhealthy one (a
        # handful of genuinely-quiet FLEURS recordings exist per language — real
        # corpus variance, not the float/int16 bug) is SKIPPED and replaced by
        # the next candidate instead of aborting the whole language.
        target_s = minutes * 60.0
        manifest_lines = []
        total_s = 0.0
        gender_counts: dict[str, int] = {}
        audio_healths: list[dict] = []
        normalized_healths: list[dict] = []
        gain_records: list[dict] = []
        skipped_unhealthy: list[dict] = []
        kept_content_hashes: list[str] = []
        for i in iter_selection_order(rows, seed_key=f"{seed}:{lang}"):
            if total_s >= target_s and len(manifest_lines) >= min_utterances:
                break
            row = rows[i]
            data_f32, sr = sf.read(io.BytesIO(row["_bytes"]), dtype="float32")
            resampled = resample_to_16k(data_f32, sr, target_sr=16000)
            # Health-check gate runs on the UNNORMALIZED signal — this is the
            # SAME accept/reject decision as before TASK 1, so selection/seeds
            # stay identical (asserted below) regardless of the normalization
            # applied afterward.
            raw_pcm = scale_clip_to_int16(resampled)
            health = audio_health(raw_pcm)
            if health["peak"] < MIN_PEAK_INT16 or health["dbfs"] < MIN_RMS_DBFS:
                skipped_unhealthy.append({"id": row["id"], **health})
                continue
            gain_db, original_rms_dbfs = compute_gain_db(resampled)
            normalized = apply_gain(resampled, gain_db)
            pcm = scale_clip_to_int16(normalized)
            wav_path = wav_dir / f"{row['id']}.wav"
            sf.write(str(wav_path), pcm, 16000, subtype="PCM_16")
            audio_healths.append(health)
            normalized_healths.append(audio_health(pcm))
            gain_records.append({"id": row["id"], "gain_db": round(gain_db, 2)})
            entry = {
                "id": row["id"],
                "sentence_id": row["sentence_id"],
                "path": str(wav_path.relative_to(data_root.parent.parent)),
                "transcription": row["transcription"],
                "raw_transcription": row["raw_transcription"],
                "gender": row["gender_name"],
                "duration_s": row["duration_s"],
                "gain_db": round(gain_db, 2),
                "original_rms_dbfs": round(original_rms_dbfs, 2),
                "dataset_version": DATASET_VERSION,
            }
            manifest_lines.append(entry)
            kept_content_hashes.append(hashlib.sha256(row["_bytes"]).hexdigest())
            total_s += row["duration_s"]
            gender_counts[row["gender_name"]] = gender_counts.get(row["gender_name"], 0) + 1

        if skipped_unhealthy:
            print(
                f"[{lang}] skipped {len(skipped_unhealthy)} unhealthy candidate(s), replaced from pool: "
                f"{[s['id'] for s in skipped_unhealthy]}"
            )
        if not (total_s >= target_s and len(manifest_lines) >= min_utterances):
            raise RuntimeError(
                f"{lang}: exhausted the FULL candidate pool ({len(rows)} rows) with only "
                f"{len(manifest_lines)} healthy utterances / {total_s / 60:.1f} min "
                f"(skipped {len(skipped_unhealthy)} unhealthy) — cannot meet floors "
                f"minutes={minutes} min_utterances={min_utterances}"
            )

        manifest_lines.sort(key=lambda e: e["id"])  # stable, readable manifest order

        # Non-vacuity assert (TASK 1): normalization must change LEVEL only,
        # never WHICH utterances got selected. Fails loudly rather than
        # silently shipping a different subset under an unchanged seed.
        new_ids = [e["id"] for e in manifest_lines]
        if old_ids is not None:
            if new_ids != old_ids:
                added = sorted(set(new_ids) - set(old_ids))
                removed = sorted(set(old_ids) - set(new_ids))
                raise RuntimeError(
                    f"{lang}: utterance SELECTION changed vs the existing manifest.jsonl "
                    f"(gain normalization must not change which utterances are selected) — "
                    f"added={added[:5]}{'...' if len(added) > 5 else ''} "
                    f"removed={removed[:5]}{'...' if len(removed) > 5 else ''}"
                )
            print(f"[{lang}] selection assert OK: {len(new_ids)} utterance ids unchanged vs prior manifest")

        # FINDING 1 non-vacuity asserts (2026-09-21 review, DATASET_VERSION 2):
        # a repeat of the sentence-id-collision bug must fail LOUDLY here,
        # never silently ship a manifest with rows sharing a wav file again.
        if len(new_ids) != len(set(new_ids)):
            dupes = sorted({i for i in new_ids if new_ids.count(i) > 1})
            raise RuntimeError(f"{lang}: manifest ids NOT unique after DATASET_VERSION={DATASET_VERSION} fix — {dupes[:5]}")
        if len(kept_content_hashes) != len(set(kept_content_hashes)):
            from collections import Counter

            dup_hashes = [h for h, c in Counter(kept_content_hashes).items() if c > 1]
            raise RuntimeError(
                f"{lang}: {len(dup_hashes)} audio content hash collision(s) among kept recordings "
                f"— two 'different' rows decoded to byte-identical audio, investigate before shipping"
            )
        print(f"[{lang}] uniqueness assert OK: {len(new_ids)} manifest ids and {len(kept_content_hashes)} audio content hashes all distinct")

        with manifest_path.open("w") as f:
            for entry in manifest_lines:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        peaks = sorted(h["peak"] for h in audio_healths)
        dbfs_vals = sorted(h["dbfs"] for h in audio_healths)
        n = len(peaks)
        audio_summary = {
            "n_checked": n,
            "min_peak": peaks[0] if n else None,
            "median_peak": peaks[n // 2] if n else None,
            "median_rms_dbfs": dbfs_vals[n // 2] if n else None,
            "n_failed": 0,  # 0 in the FINAL kept set by construction — unhealthy ones were skipped, not counted
            "n_skipped_unhealthy": len(skipped_unhealthy),
            "skipped_unhealthy_ids": [s["id"] for s in skipped_unhealthy],
        }

        gains = sorted(g["gain_db"] for g in gain_records)
        ng = len(gains)
        norm_dbfs_vals = sorted(h["dbfs"] for h in normalized_healths)
        nn = len(norm_dbfs_vals)
        high_gain_ids = sorted(g["id"] for g in gain_records if g["gain_db"] > HIGH_GAIN_WARN_DB)
        audio_normalization = {
            "target_rms_dbfs": TARGET_RMS_DBFS,
            "peak_ceiling_dbfs": PEAK_CEILING_DBFS,
            "min_gain_db": gains[0] if ng else None,
            "median_gain_db": gains[ng // 2] if ng else None,
            "max_gain_db": gains[-1] if ng else None,
            "high_gain_warn_db": HIGH_GAIN_WARN_DB,
            "high_gain_ids": high_gain_ids,
            "post_norm_min_rms_dbfs": norm_dbfs_vals[0] if nn else None,
            "post_norm_median_rms_dbfs": norm_dbfs_vals[nn // 2] if nn else None,
            "post_norm_max_rms_dbfs": norm_dbfs_vals[-1] if nn else None,
        }
        if high_gain_ids:
            print(
                f"[{lang}] {len(high_gain_ids)} utterance(s) needed >{HIGH_GAIN_WARN_DB} dB gain "
                f"(low-resolution/quiet source): {high_gain_ids}"
            )

        done_marker.write_text(
            json.dumps(
                {
                    "dataset_version": DATASET_VERSION,
                    "minutes": minutes,
                    "min_utterances": min_utterances,
                    "seed": seed,
                    "n_utterances": len(manifest_lines),
                    "total_duration_s": round(total_s, 1),
                    "gender_counts": gender_counts,
                    "full_split_n": len(rows),
                    "full_split_gender_counts": full_split_gender_counts,
                    "audio_health": audio_summary,
                    "audio_normalization": audio_normalization,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "source": f"{REPO_ID}@{REVISION}:{lang}/{SPLIT}/0000.parquet",
                },
                indent=2,
            )
        )
        print(
            f"[{lang}] kept {len(manifest_lines)} utts, {total_s / 60:.1f} min, "
            f"genders={gender_counts}, min_peak={audio_summary['min_peak']}, "
            f"median_peak={audio_summary['median_peak']}, median_rms_dbfs={audio_summary['median_rms_dbfs']}, "
            f"post_norm_median_rms_dbfs={audio_normalization['post_norm_median_rms_dbfs']}, "
            f"max_gain_db={audio_normalization['max_gain_db']}"
        )
        return {
            "lang": lang,
            "n": len(manifest_lines),
            "minutes": round(total_s / 60, 2),
            "genders": gender_counts,
            "audio_health": audio_summary,
            "audio_normalization": audio_normalization,
        }
    finally:
        # Delete the shard immediately — disk discipline.
        shard_dir = tmp_root / lang
        if shard_dir.exists():
            shutil.rmtree(shard_dir, ignore_errors=True)


def self_test() -> None:
    n_pass = 0
    n_total = 0

    def check(actual, expected, label):
        nonlocal n_pass, n_total
        n_total += 1
        if actual == expected:
            n_pass += 1
            print(f"  PASS {label}: {actual!r}")
        else:
            print(f"  FAIL {label}: expected {expected!r}, got {actual!r}")

    print("=== fetch_fleurs.py self-test ===")

    # 1. No duplicate sentence ids -> every dup_index is 0.
    check(assign_recording_dup_indices([100, 200, 300]), [0, 0, 0], "[1] no duplicates: all dup_index=0")

    # 2. A sentence id repeated 3x (2 different speakers + itself) -> 0,1,2 in
    # shard row order, matching finding 1's de_de example (raw_id 2003 seen
    # 3x at parquet rows 0, 249, 473).
    check(assign_recording_dup_indices([2003, 1, 2003, 2003]), [0, 0, 1, 2], "[2] triple-repeated sentence id: 0,1,2 in row order")

    # 3. Resulting per-recording ids are unique even though sentence_id repeats.
    sentence_ids = [2003, 1, 2003, 2003]
    dup_idx = assign_recording_dup_indices(sentence_ids)
    ids = [build_row_id("de_de", sid, k) for sid, k in zip(sentence_ids, dup_idx)]
    check(ids, ["de_de_002003_0", "de_de_000001_0", "de_de_002003_1", "de_de_002003_2"], "[3] built ids all distinct")
    check(len(ids) == len(set(ids)), True, "[3b] built ids: len(ids)==len(set(ids))")

    # 4. Deterministic / reproducible: same input order -> same output, twice.
    check(
        assign_recording_dup_indices(sentence_ids) == assign_recording_dup_indices(sentence_ids),
        True,
        "[4] deterministic across repeated calls",
    )

    # 5. Regression guard: the OLD (buggy) v1 scheme collided on sentence id
    # alone — confirm that scheme WOULD have collided on this exact fixture
    # (documents the bug this fix replaces; not testing production code).
    old_scheme_ids = [f"de_de_{sid:06d}" for sid in sentence_ids]
    check(len(old_scheme_ids) != len(set(old_scheme_ids)), True, "[5] v1 scheme (no dup suffix) DOES collide on this fixture, confirming the bug")

    print(f"\n{n_pass}/{n_total} assertions passed")
    if n_pass != n_total:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--langs", nargs="+", default=DEFAULT_LANGS)
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--min-utterances", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument(
        "--data-root",
        default=str(Path(__file__).resolve().parents[1] / "data"),
    )
    ap.add_argument(
        "--tmp-root",
        default=str(Path(tempfile.gettempdir()) / "fleurs_tmp"),
    )
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--census-only", action="store_true", help="gender-column-only pass, no WAVs written")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    data_root = Path(args.data_root)
    tmp_root = Path(args.tmp_root)
    data_root.mkdir(parents=True, exist_ok=True)

    results = []
    if args.census_only:
        for lang in args.langs:
            try:
                census = gender_census(lang, tmp_root)
                merge_full_split_census(data_root / lang, census)
                print(f"[{lang}] full_split_n={census['full_split_n']} genders={census['full_split_gender_counts']}")
                results.append(census)
            except SystemExit:
                raise
            except Exception as e:  # noqa: BLE001
                print(f"[{lang}] ERROR: {e}", file=sys.stderr)
                results.append({"lang": lang, "error": str(e)})
        print("\n=== Census Summary ===")
        for r in results:
            print(r)
        return

    for lang in args.langs:
        try:
            res = fetch_language(lang, args.minutes, args.min_utterances, args.seed, data_root, tmp_root, args.force)
            results.append(res)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 - report and continue to next language
            print(f"[{lang}] ERROR: {e}", file=sys.stderr)
            results.append({"lang": lang, "error": str(e)})

    print("\n=== Summary ===")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
