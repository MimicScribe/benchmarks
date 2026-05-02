# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote Community-1 (on-device diarization) + acoustic boundary snap + Gemini 3 Flash (LLM speaker attribution)

Run date: 2026-05-02

## What's new in this update

**94.8% → 95.1% SAA** (+0.3 pp aggregate). One production change since the 2026-04-30 publication: a new chunk-level correction step runs after the diarizer's clustering and before the LLM attribution, reassigning chunks the clustering step placed in the wrong cluster.

Per-corpus deltas: SCOTUS +1.0 pp, VoxConverse +0.4 pp, Podcast +0.1 pp, AMI ≈ 0, Earnings-21 −0.1 pp (within run-to-run LLM noise). Gains concentrate on long meetings where one speaker's cluster had grown large enough to absorb content from acoustically similar speakers — cases the boundary-snap step can't reach because there's no boundary nearby to refine.

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | + LLM SAA | Speedup |
|--------|------:|----------------:|----------------:|----------:|--------:|
| Earnings-21 | 11 | 98.1% | 96.5% | **96.8%** | 2.6x |
| VoxConverse | 20 | 95.9% | 92.5% | **95.5%** | 3.8x |
| SCOTUS | 5 | 99.2% | 95.0% | **97.0%** | 3.1x |
| AMI | 16 | 97.0% | 93.6% | **94.6%** | 3.3x |
| Podcast | 6 | — | 90.7% | **91.6%** | — |
| **Aggregate** | **58** | — | **94.0%** | **95.1%** | — |

Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment. The acoustic snap does not change cluster counts — it only refines where existing speaker-change boundaries sit in time.

## What the LLM Step Does

The raw diarizer outputs anonymous speaker IDs with unformatted ASR text. The LLM identifies speakers by name from transcript content, fixes ASR errors, and cleans up formatting:

**Before (raw diarization, post-snap):**
```
[  10.9-149.0] Speaker 2:  ? Mr. Chief Justice, and may it please the court, the Fifth Circuit's
                            decision in this case is the f...
[ 154.6-158.9] Speaker 3:  w. Are there any limits on what Congress can do
[ 388.1-388.6] Speaker 1:  reading it,
[ 388.6-389.0] Speaker 2:  you're
[ 389.0-459.0] Speaker 1:  you have a very aggressive view of Congress's authority...
```

**After (LLM attribution):**
```
[  10.9-149.0] Elizabeth Prelogar:  Mr. Chief Justice, and may it please the court, the Fifth
                                    Circuit's decision in this case is the fir...
[ 154.6-158.9] Justice Thomas:     Are there any limits on what Congress can do?
[ 388.1-459.0] Speaker 1:          General, one of the things that struck me as I was reading
                                    it, you have a very aggressive view of Co...
```

## Acoustic boundary snap

Diarizer-emitted speaker-change boundaries are coarse — a turn change can land a few seconds off in either direction, leaking the wrong speaker's words into the wrong segment. The snap step refines each boundary using the audio itself.

For each speaker-change boundary, candidate positions are evaluated around the original location: short clips on either side of each candidate are embedded and the boundary is moved to the position where the audio best separates the two speakers. The move is gated on a confidence margin against the original, capped at a small displacement, and skipped when the diarizer placed clear silence between turns. All thresholds were tuned on a held-out subset of the corpora.

Cost: ~4-6 s per 30-min meeting on Apple Silicon ANE (FBANK + Embedding calls batched per boundary).

## Chunk-cluster migration

The diarizer's clustering step occasionally puts the wrong chunks of audio in the wrong cluster. Two patterns we see repeatedly:

- **Mega-cluster contamination on long meetings**: one speaker's cluster grows large and starts absorbing chunks from acoustically similar speakers. On the SCOTUS files, the Solicitor General's cluster had absorbed ~50% of one Justice's content.
- **Bidirectional smearing on similar-voice conversations**: each cluster ends up ~80% pure with the other speaker's chunks crossed in.

The acoustic boundary snap can't fix this — there's no boundary nearby to move. The chunk-cluster migration step re-evaluates the per-chunk embeddings the diarizer already computed:

1. Build a robust centroid per cluster via iterative outlier rejection (drop chunks whose cosine to the running mean falls below mean − 2σ, recompute, repeat until stable). This produces a centroid that represents the cluster's true acoustic identity rather than the contaminated mean.
2. Score every chunk against every cluster centroid; compute `margin = max(other) − own_score`.
3. Find runs of ≥ 4 contiguous chunks that share the same source cluster, vote for the same alternate cluster, and individually cross a 0.50 margin. Migrate every chunk in such a run to its alternate cluster.
4. Rebuild segments by **splitting** original segments at intra-segment cluster transitions. Adjacent original segments are never merged.

Runs of < 4 chunks don't migrate, which suppresses singleton noise and prevents the kind of segment-split chains that confuse the downstream LLM's name-mapping step. The conservative gate is what makes the recipe regression-free across this corpus (validated by sweep over thresholds 0.45–0.60 and run lengths 3–4; baseline-rerun stochasticity floor at ±0.06 pp aggregate).

Cost: pure NumPy / vDSP on cached embeddings — no model calls. ~70 ms on a 30-min meeting, ~550 ms on a 90-min meeting (M-series silicon). Well under 1% of pipeline time vs ASR/snap/LLM.

## Latency

| Corpus | File | Audio | Pyannote | MimicScribe | Speedup |
|--------|------|------:|---------:|------------:|--------:|
| VoxConverse | duvox | 16 min | 47.7s | 12.7s | 3.8x |
| SCOTUS | 22-842 | 74 min | 312.7s | 99.3s | 3.1x |
| Earnings-21 | 4320211 | 55 min | 208.7s | 79.7s | 2.6x |
| AMI | ES2004a | 40 min | 53.4s | 16.0s | 3.3x |

Diarization-only, Apple M1 Max. Pyannote uses MPS (GPU); MimicScribe uses ANE. Acoustic snap adds ~4-6 s per 30-minute meeting on top of these numbers.

## DER Breakdown

SAA isolates **confusion** — was the right speaker tagged on speech the system actually transcribed? DER mixes confusion with **missed speech** (omitted by the system) and **false alarm** (speech the system attributed but ground-truth marks as silence). On meeting-style audio, those last two are dominated by UX choices rather than diarization quality:

- Sentence-level segmentation deliberately leaves gaps between turns; pyannote.metrics counts them as false alarm when an LLM merges adjacent same-speaker segments.
- An ASR that drops mumbled or overlapped speech can score *lower* DER than a system that captures it, because missed speech can't be confused.

**Confusion** is the meaningful component for attribution quality.

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 18.1% | 3.2% | 12.1% | 2.8% |
| VoxConverse | 16.0% | 4.5% | 6.0% | 5.5% |
| SCOTUS | 5.4% | 3.0% | 0.0% | 2.3% |
| AMI | 27.2% | 5.4% | 6.3% | 15.5% |
| Podcast | 10.3% | 8.4% | 1.2% | 0.7% |
| **Aggregate** | **15.5%** | **4.9%** | **5.2%** | **5.4%** |

Confusion drops on every corpus that benefits from migration (SCOTUS −1.0 pp, VoxConverse −0.4 pp). False-alarm and missed components are unchanged from the prior publication — they're dominated by ASR/segmentation behavior this update doesn't touch.

## Benchmark vs Production

These results are a **worst-case scenario** using single-channel mixed audio with no prior context. In production:

- **Dual-channel audio** eliminates local/remote speaker confusion
- **Voice profiles** enable verified speaker recognition
- **Meeting context** helps the LLM identify participants by name and role

## Corpora

| Corpus | Source | Files | Duration | Speakers |
|--------|--------|------:|---------:|---------:|
| [Earnings-21](https://huggingface.co/datasets/Revai/earnings21) | Public earnings calls | 11 | ~10 hrs | 5-15 |
| [VoxConverse](https://github.com/joonson/voxconverse) | YouTube debates/interviews | 20 | ~2 hrs | 2-6 |
| [SCOTUS](https://www.oyez.org) | Supreme Court oral arguments | 5 | ~7.5 hrs | 10-12 |
| [AMI](https://groups.inf.ed.ac.uk/ami/corpus/) | Meeting recordings (IHM-mix) | 16 | ~9 hrs | 4 |
| Podcast | Long-form interview podcasts | 6 | ~10 hrs | 2-4 |

## Methodology

- **Collar**: 0.25s | **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False`
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML
- **Acoustic boundary snap**: WeSpeaker ResNet34 (FBank → Embedding pipeline) on Apple Neural Engine
- **ASR**: Parakeet TDT 0.6B via FluidAudio CoreML
- **LLM**: Gemini 3 Flash (temp 0.1, thinking minimal)

## Reproducibility

The 58-file corpus is pinned in the parakeet-transcriber repo for byte-exact reruns:

```
parakeet-transcriber@ff042dba:
├── benchmark/results/corpus_eval/raw_segments/                                                # 58 pre-LLM diarizer outputs
├── benchmark/output/snap_wide_c_full/                                                         # snapped raw_segments
├── benchmark/output/v4seal-wide_c-with-migration_t50r4/rttm/                                  # current: LLM-attributed (RTTM)
└── benchmark/results/diarization/v4seal-wide_c-with-migration_t50r4_corpus_2026-05-02.json    # scored result
```

Audio source paths and ground-truth RTTMs come from the public corpora linked above. The chunk-cluster migration step is reproduced from the cached snap output via:

```
benchmark/.venv/bin/python3 scripts/run_v4seal_migration_corpus_eval.py \
    --snap-source wide_c --threshold 0.50 --min-run 4
```

Re-running the LLM step on the pinned `raw_segments/` reproduces the LLM column without re-running diarization. Re-running the acoustic snap requires the audio files (loaded fresh per file at 16 kHz mono).
