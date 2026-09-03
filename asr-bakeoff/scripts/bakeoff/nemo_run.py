#!/usr/bin/env python3
"""nemo_run.py - NVIDIA NeMo Parakeet arms of the ASR bake-off (v2 and v3).

*** UNTESTED AS COMMITTED. ***

This runner was RECONSTRUCTED on 2026-09-03 from the two run manifests that the
published arms left behind — `benchmark/output/bakeoff-nemo-v2/manifest.json`
and `benchmark/output/bakeoff-nemo-v3/manifest.json` — plus the recipe sentence
in `docs/analysis/model-bakeoff-2026-09-01.md`. The original script was never
committed. Nothing here has been re-executed: the numbers in
`benchmark/public/asr-bakeoff/RESULTS.md` come from the ORIGINAL run, not from
this file. Treat a re-run as a fresh measurement, not as a verification, until
someone has run it and compared per-file word counts against the manifests.

WHAT THE MANIFESTS PIN (reproduced here exactly)

    arm  model_id                        chunk_s  recipe
    v2   nvidia/parakeet-tdt-0.6b-v2      300.0   rel_pos (card default, full)
    v3   nvidia/parakeet-tdt-0.6b-v3     1800.0   rel_pos_local_attn [128,128]
                                                  + subsampling_conv_chunking_factor 1

    both: CPU, torch threads 4, NeMo 2.5.0, torch 2.13.0.

The 300 s / 1800 s windows are CONTIGUOUS and NON-OVERLAPPING — derived from
the recorded segment bounds, which tile each file end to end ([0,300], [300,600]
… last window ending at the file's exact duration) and give exactly the
`chunks` count each manifest records (ceil(audio_s / chunk_s)). There is no
seam dedup: each window's decode is one output segment.

WHAT THE MANIFESTS DO NOT PIN — these are RECONSTRUCTION CHOICES, not records:

  1. The `transcribe()` call arguments. The manifests say only
     "NeMo ASRModel.from_pretrained + transcribe (CPU)". `batch_size`,
     `return_hypotheses`, `num_workers` and `timestamps` are unrecorded; this
     file passes `batch_size=1` and requests no timestamps (consistent with the
     output, which carries window bounds and no word times, but not proven).
  2. HOW the chunk audio reached `transcribe()` — a temporary WAV per window
     (what this file does) versus an in-memory array. Unrecorded.
  3. dtype. Unrecorded; CPU float32 (the NeMo default) is assumed.
  4. `nice -n 15`, named in the analysis doc but not in either manifest, is a
     scheduling nicety with no effect on output. Run it under `nice` to match.
  5. Whether the v2 arm ALSO called `change_subsampling_conv_chunking_factor`.
     Its manifest's `recipe` lists only `attention`, so this file does not call
     it for v2 — that is an inference from an absent key.

The model REVISIONS were on that list until 2026-09-03 and are not any more.
Neither manifest records one, but the snapshots the arms ran from are still in
this machine's Hugging Face cache, so `--revision` now DEFAULTS per arm to the
sha the published run resolved — `ARMS[<arm>]["revision"]`, the same two shas
the public Provenance table carries. Pass `--revision ""` to let `main` resolve
at download time instead, which is a different model file the day upstream
pushes one. `--model` without `--revision` pins nothing: the arm's sha does not
identify some other repository.

OUTPUT SHAPE (identical to granite_run.py / run_cohere_transcribe.py, so
`scripts/score_corpus_wer.py` and `scripts/score_number_fidelity.py --corpus`
read it unchanged):

    <out>/per-file/<id>_after_orphan.json  {"segments":[{startTime,endTime,text}]}
    <out>/manifest.json                    provenance + timing + recipe

Text is RAW model output: no inverse text normalization, no filler filtering.
The scorers own both.

PYTHON ENVIRONMENT

    nemo_toolkit[asr] == 2.5.0
    torch == 2.13.0            (CPU build is enough; the arms ran on CPU)
    soundfile, numpy

    python3 -m venv .venv-nemo
    .venv-nemo/bin/pip install "nemo_toolkit[asr]==2.5.0" torch==2.13.0 soundfile

USAGE

    python3 scripts/bakeoff/nemo_run.py --arm v3 \\
        --out benchmark/output/bakeoff-nemo-v3
    python3 scripts/bakeoff/nemo_run.py --arm v2 \\
        --out benchmark/output/bakeoff-nemo-v2

`--audio-root` points at the corpus (default: <repo>/benchmark/data, where
scripts/bakeoff/fetch_corpus.py puts it). `--files` narrows the 27-file set.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import soundfile as sf

SR = 16000

# Repo root, derived from this file's own location (scripts/bakeoff/<this>).
REPO = Path(__file__).resolve().parents[2]
AUDIO_ROOT = REPO / "benchmark" / "data"

EARNINGS21 = [
    "4320211", "4341191", "4346818", "4359971", "4365024", "4366522",
    "4366893", "4367535", "4383161", "4384964", "4387332",
]
AMI = [
    "EN2002a", "EN2002b", "EN2006b", "ES2002a", "ES2004c", "ES2008c",
    "ES2013b", "ES2016a", "IS1000a", "IS1003b", "IS1006c", "IS1009a",
    "IS1009b", "TS3005a", "TS3009c", "TS3012b",
]

# One entry per published arm, copied from that arm's manifest.json.
ARMS = {
    "v2": {
        "model_id": "nvidia/parakeet-tdt-0.6b-v2",
        # The snapshot in this machine's HF cache, i.e. what the published run
        # resolved `main` to. Not recorded by the manifest -- see --revision.
        "revision": "ae9ad07059c7c739ffaf932226a8fe64ae2620b0",
        "chunk_seconds": 300.0,
        "recipe": {"attention": "rel_pos (card default, full)"},
        # card default: no change_attention_model call, no chunking-factor call
        "attention_model": None,
        "att_context_size": None,
        "subsampling_conv_chunking_factor": None,
    },
    "v3": {
        "model_id": "nvidia/parakeet-tdt-0.6b-v3",
        # Same basis as v2's: the cached snapshot the published run resolved.
        "revision": "541d1f99c6b0c3cd0b11a95167540bb8edefd82b",
        "chunk_seconds": 1800.0,
        "recipe": {
            "attention": "rel_pos_local_attn [128,128]",
            "subsampling_conv_chunking_factor": 1,
        },
        "attention_model": "rel_pos_local_attn",
        "att_context_size": [128, 128],
        "subsampling_conv_chunking_factor": 1,
    },
}


def audio_path(file_id: str, audio_root: Path | str | None = None) -> Path:
    root = Path(audio_root) if audio_root is not None else AUDIO_ROOT
    if file_id in EARNINGS21:
        return root / "earnings21/audio" / f"{file_id}.wav"
    return root / "ami/audio" / f"{file_id}.wav"


def plan_chunks(total_s: float, chunk_s: float) -> list[tuple[float, float]]:
    """Contiguous, non-overlapping windows; the last one ends at total_s.

    ceil(total_s / chunk_s) windows, which is the `chunks` count each manifest
    records for every file.
    """
    n = max(1, int(math.ceil(total_s / chunk_s)))
    spans = []
    for i in range(n):
        start = i * chunk_s
        end = min(start + chunk_s, total_s)
        if end <= start:
            break
        spans.append((start, end))
    return spans


def hyp_text(h) -> str:
    """NeMo 2.x transcribe() returns Hypothesis objects; older paths return str."""
    if isinstance(h, str):
        return h
    text = getattr(h, "text", None)
    if text is not None:
        return text
    return str(h)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=sorted(ARMS), required=True,
                    help="which published arm's recipe to reproduce")
    ap.add_argument("--out", required=True, help="run directory to write")
    ap.add_argument("--audio-root", default=str(AUDIO_ROOT),
                    help="corpus root holding ami/audio and earnings21/audio "
                         f"(default: {AUDIO_ROOT})")
    ap.add_argument("--files", nargs="*", default=None,
                    help="file ids; default = the 27-file bake-off set")
    ap.add_argument("--model", default=None,
                    help="override the arm's model id")
    ap.add_argument("--revision", default=None,
                    help="HF revision; defaults to the arm's pinned snapshot, "
                         "which is the one the published run resolved. Pass an "
                         "empty string to let `main` resolve at download time.")
    ap.add_argument("--chunk", type=float, default=None,
                    help="override the arm's window length in seconds")
    ap.add_argument("--threads", type=int, default=4,
                    help="torch CPU threads (manifests record 4)")
    ap.add_argument("--batch-size", type=int, default=1,
                    help="transcribe() batch_size; UNRECORDED for the original run")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()

    arm = ARMS[a.arm]
    model_id = a.model or arm["model_id"]
    chunk_s = a.chunk if a.chunk is not None else arm["chunk_seconds"]
    if a.revision is not None:
        revision = a.revision or None      # "" means: do not pin
    elif a.model:
        revision = None                    # another model: the arm's sha is not its sha
    else:
        revision = arm["revision"]

    import torch  # noqa: E402  (after arg parsing: NeMo import is slow)
    import nemo
    from nemo.collections.asr.models import ASRModel

    torch.set_num_threads(a.threads)

    out = Path(a.out)
    (out / "per-file").mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"

    file_ids = a.files if a.files else EARNINGS21 + AMI

    t_load = time.time()
    kw = {"revision": revision} if revision else {}
    model = ASRModel.from_pretrained(model_name=model_id, map_location="cpu", **kw)
    if arm["attention_model"] is not None:
        # The card's long-audio recipe. Both calls are on the manifest's
        # `recipe` key for v3 and absent for v2.
        model.change_attention_model(arm["attention_model"], arm["att_context_size"])
    if arm["subsampling_conv_chunking_factor"] is not None:
        model.change_subsampling_conv_chunking_factor(
            arm["subsampling_conv_chunking_factor"])
    model.eval()
    load_s = time.time() - t_load
    print(f"[nemo] {model_id} loaded in {load_s:.1f}s "
          f"(threads={a.threads}, chunk={chunk_s:.0f}s)", flush=True)

    manifest = {
        "model_id": model_id,
        "path": "NeMo ASRModel.from_pretrained + transcribe (CPU)",
        "nemo": nemo.__version__,
        "torch": torch.__version__,
        "threads": a.threads,
        "chunk_seconds": chunk_s,
        "recipe": dict(arm["recipe"]),
        "load_seconds": round(load_s, 1),
        "files": {},
        # Not in the original manifests: this runner is a reconstruction.
        "reconstructed_runner": "scripts/bakeoff/nemo_run.py (2026-09-03, UNTESTED)",
    }
    if revision:
        manifest["revision"] = revision

    def flush():
        manifest_path.write_text(json.dumps(manifest, indent=2))

    flush()
    t_run = time.time()

    for fid in file_ids:
        dest = out / "per-file" / f"{fid}_after_orphan.json"
        if a.skip_existing and dest.exists():
            print(f"[nemo] skip {fid}", flush=True)
            continue
        wav_path = audio_path(fid, a.audio_root)
        info = sf.info(str(wav_path))
        assert info.samplerate == SR, f"{wav_path} is {info.samplerate} Hz, expected {SR}"
        total_s = info.frames / info.samplerate
        spans = plan_chunks(total_s, chunk_s)

        t_file = time.time()
        segments = []
        with tempfile.TemporaryDirectory() as td:
            for ci, (s, e) in enumerate(spans):
                data, _ = sf.read(str(wav_path), start=int(s * SR),
                                  frames=int(round((e - s) * SR)),
                                  dtype="float32", always_2d=True)
                mono = data[:, 0]
                # RECONSTRUCTION CHOICE: the window is handed to transcribe()
                # as a temporary WAV. The original run's input form is
                # unrecorded (see the module docstring).
                clip = Path(td) / f"{fid}_{ci:04d}.wav"
                sf.write(str(clip), mono, SR, subtype="PCM_16")
                hyps = model.transcribe([str(clip)], batch_size=a.batch_size)
                if hyps and isinstance(hyps[0], (list, tuple)):
                    hyps = hyps[0]  # older NeMo returns (best, all_hyps)
                text = hyp_text(hyps[0]).strip() if hyps else ""
                segments.append({
                    "startTime": round(s, 3),
                    "endTime": round(e, 3),
                    "text": text,
                })
                print(f"[nemo] {fid} {ci + 1}/{len(spans)} "
                      f"[{s:.0f}-{e:.0f}s] {len(text.split())} words "
                      f"({time.time() - t_file:.0f}s elapsed)", flush=True)

        wall = time.time() - t_file
        dest.write_text(json.dumps({"segments": segments},
                                   ensure_ascii=False, indent=1))
        words = sum(len(sg["text"].split()) for sg in segments)
        manifest["files"][fid] = {
            "audio_s": round(total_s, 1),
            "wall_s": round(wall, 1),
            "chunks": len(spans),
            "words": words,
        }
        flush()
        print(f"[nemo] === {fid}: {total_s:.0f}s audio in {wall:.0f}s "
              f"words={words} (run {(time.time() - t_run) / 60:.0f} min) ===",
              flush=True)

    manifest["total_wall_seconds"] = round(time.time() - t_run, 1)
    flush()
    return 0


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    sys.exit(main())
