# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote Community-1 (on-device diarization) + acoustic boundary snap + Gemini 3 Flash (LLM speaker attribution)

Run date: 2026-04-28 (LLM prompt `v4-seal`, acoustic boundary snap enabled)

## What's new in this update

**93.7% → 94.7% SAA** (+1.0 pp aggregate), with DER down across all corpora. Two production changes since the 2026-04-27 publication:

- **v4-seal LLM prompt** (replaces `seal-prod-merge-meta-v6`) — structural attribution: one output entry per input segment, segment boundaries preserved verbatim.
- **Acoustic boundary snap** — new post-pass between diarizer and LLM, refines speaker-change boundaries via fresh embedding pass on candidate positions ±2 s.

| Corpus | v6 (prior) | **v4-seal + snap (now)** | Δ |
|---|---:|---:|---:|
| AMI | 93.2% | **94.5%** | +1.3 |
| Earnings-21 | 97.0% | 96.8% | −0.2 |
| Podcast | 89.4% | **91.3%** | +1.9 |
| SCOTUS | 94.7% | **95.7%** | +1.0 |
| VoxConverse | 93.0% | **94.8%** | +1.8 |
| **Aggregate** | **93.7%** | **94.7%** | **+1.0** |

Snap contributes ~half the SAA gain (+0.6 pp on top of v4-seal alone) and most of the DER reduction.

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | + LLM SAA | Speedup |
|--------|------:|----------------:|----------------:|----------:|--------:|
| Earnings-21 | 11 | 98.1% | 96.5% | **96.8%** | 2.6x |
| VoxConverse | 20 | 95.9% | 92.5% | **94.8%** | 3.8x |
| SCOTUS | 5 | 99.2% | 95.0% | **95.7%** | 3.1x |
| AMI | 16 | 97.0% | 93.6% | **94.5%** | 3.3x |
| Podcast | 6 | — | 90.7% | **91.3%** | — |
| **Aggregate** | **58** | — | **94.0%** | **94.7%** | — |

Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment. The acoustic snap does not change cluster counts — it only refines where existing speaker-change boundaries sit in time.

## Reading SAA and DER together

SAA isolates **confusion** — was the right speaker tagged on speech the system actually transcribed? DER mixes confusion with **missed speech** (omitted by the system) and **false alarm** (speech the system attributed but ground-truth marks as silence). On meeting-style audio, those two components are dominated by UX choices rather than diarization quality:

- Sentence-level segmentation deliberately leaves gaps between turns; pyannote.metrics counts them as false alarm when an LLM merges adjacent same-speaker segments.
- An ASR that drops mumbled or overlapped speech can score *lower* DER than a system that captures it, because missed speech can't be confused.

Look at the **DER + Confusion** breakdown below to compare attribution quality across runs.

## Acoustic boundary snap — how it works

For each speaker-change boundary, evaluate candidate positions ±2 s and move the boundary to where the audio best separates the two speakers.

- **Score**: at each candidate `t`, embed `[t−3s, t]` and `[t, t+3s]` and pick the position that maximizes `(before↔prev + after↔next) − (before↔next + after↔prev)` against the cluster centroids.
- **Confidence gate**: must beat the original position's score by ≥ 0.20.
- **Move cap**: ≤ 2 s of displacement.
- **Skip rule**: gap > 1 s between adjacent segments → don't snap (diarizer correctly identified silence).

Cost: ~2-3 s per 30-min meeting on Apple Silicon ANE.

## Benchmark vs Production

These results are a **worst-case scenario** using single-channel mixed audio with no prior context. In production:

- **Dual-channel audio** eliminates local/remote speaker confusion
- **Voice profiles** enable verified speaker recognition
- **Meeting context** helps the LLM identify participants by name and role

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

## Latency

| Corpus | File | Audio | Pyannote | MimicScribe | Speedup |
|--------|------|------:|---------:|------------:|--------:|
| VoxConverse | duvox | 16 min | 47.7s | 12.7s | 3.8x |
| SCOTUS | 22-842 | 74 min | 312.7s | 99.3s | 3.1x |
| Earnings-21 | 4320211 | 55 min | 208.7s | 79.7s | 2.6x |
| AMI | ES2004a | 40 min | 53.4s | 16.0s | 3.3x |

Diarization-only, Apple M1 Max. Pyannote uses MPS (GPU); MimicScribe uses ANE. Acoustic snap adds ~2-3 s per 30-minute meeting on top of these numbers.

## DER Breakdown

**Confusion** is the meaningful component for attribution quality. False alarm and missed speech are dominated by the UX and segmentation choices described above.

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 18.1% | 3.2% | 12.1% | 2.8% |
| VoxConverse | 16.7% | 5.2% | 5.9% | 5.5% |
| SCOTUS | 6.6% | 4.3% | 0.0% | 2.3% |
| AMI | 27.3% | 5.5% | 6.3% | 15.5% |
| Podcast | 10.5% | 8.7% | 1.2% | 0.7% |
| **Aggregate** | **15.9%** | **5.3%** | **5.2%** | **5.4%** |

For comparison — confusion-only on the prior LLM prompt (`seal-prod-merge-meta-v6`): Earnings-21 3.0%, VoxConverse 7.0%, SCOTUS 5.3%, AMI 6.8%, Podcast 10.6%. The combined v4-seal + snap update reduces confusion on 4 of 5 corpora; Earnings-21 ticks up 0.2 pp.

The SCOTUS DER drop (26.9% → 6.6%) is dominated by false-alarm reduction: v4-seal preserves segment boundaries verbatim instead of merging adjacent same-speaker segments, which v6 was doing on the long-monologue SCOTUS audio in a way that left attributed-speech intervals overlapping ground-truth silence.

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
- **LLM**: Gemini 3 Flash, prompt `v4-seal` (temp 0.1, thinking minimal)

## Reproducibility

The 58-file corpus is pinned in the parakeet-transcriber repo for byte-exact reruns:

```
parakeet-transcriber@7db23d9b:benchmark/results/corpus_eval/
├── raw_segments/                       # 58 pre-LLM diarizer outputs (cluster IDs + cluster-centroid embeddings)
├── seal-prod/                          # baseline LLM attribution (RTTM)
├── seal-prod-merge-meta-v6/            # prior published prompt (RTTM)
├── v4seal/                             # v4-seal LLM attribution alone (RTTM)
└── v4seal-with-snap/                   # current production: v4-seal + acoustic boundary snap (RTTM)
```

Audio source paths and ground-truth RTTMs come from the public corpora linked above. Re-running the LLM step on the pinned `raw_segments/` reproduces the v4-seal columns without re-running diarization. Re-running the acoustic snap requires the audio files (loaded fresh per file at 16 kHz mono).
