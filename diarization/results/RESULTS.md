# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote Community-1 (on-device diarization) + acoustic boundary snap + Gemini 3 Flash (LLM speaker attribution)

Run date: 2026-04-30

## What's new in this update

**94.7% → 94.8% SAA** (+0.1 pp aggregate), with DER down on every corpus. One production change since the 2026-04-28 publication: the acoustic boundary snap now searches a wider window around each speaker-change boundary and runs its embedding calls as batched ANE invocations.

Per-corpus gains range from +0.1 to +0.3 pp; worst-case file regression is −0.1 pp. Gains concentrate on SCOTUS and VoxConverse where speaker-change boundaries have a wider distribution of placement errors.

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | + LLM SAA | Speedup |
|--------|------:|----------------:|----------------:|----------:|--------:|
| Earnings-21 | 11 | 98.1% | 96.5% | **96.9%** | 2.6x |
| VoxConverse | 20 | 95.9% | 92.5% | **95.1%** | 3.8x |
| SCOTUS | 5 | 99.2% | 95.0% | **96.0%** | 3.1x |
| AMI | 16 | 97.0% | 93.6% | **94.6%** | 3.3x |
| Podcast | 6 | — | 90.7% | **91.5%** | — |
| **Aggregate** | **58** | — | **94.0%** | **94.8%** | — |

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
| Earnings-21 | 18.0% | 3.1% | 12.1% | 2.8% |
| VoxConverse | 16.4% | 4.9% | 5.9% | 5.5% |
| SCOTUS | 6.3% | 4.0% | 0.0% | 2.3% |
| AMI | 27.3% | 5.4% | 6.3% | 15.5% |
| Podcast | 10.4% | 8.5% | 1.2% | 0.7% |
| **Aggregate** | **15.8%** | **5.2%** | **5.2%** | **5.4%** |

The wider snap reduces confusion on every corpus. False-alarm and missed components are unchanged from the prior publication — they're dominated by ASR/segmentation behavior this update doesn't touch.

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
parakeet-transcriber@2a380f19:
├── benchmark/results/corpus_eval/raw_segments/    # 58 pre-LLM diarizer outputs
├── benchmark/output/snap_wide_c_full/             # snapped raw_segments (current)
├── benchmark/output/v4seal_wide_c_full/rttm/      # current: LLM-attributed (RTTM)
└── benchmark/results/diarization/v4seal_wide_c_full_2026-04-30.json  # scored result
```

Audio source paths and ground-truth RTTMs come from the public corpora linked above. Re-running the LLM step on the pinned `raw_segments/` reproduces the LLM column without re-running diarization. Re-running the acoustic snap requires the audio files (loaded fresh per file at 16 kHz mono).
