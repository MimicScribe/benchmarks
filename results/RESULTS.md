# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote Community-1 (on-device diarization) + Gemini 3 Flash (LLM speaker attribution)

Run date: 2026-04-07

## Speaker Attribution Accuracy (SAA)

**SAA = 1 - confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | + LLM SAA | Speedup |
|--------|------:|----------------:|----------------:|----------:|--------:|
| Earnings-21 | 11 | 98.1% | 95.3% | **97.3%** | 2.6x |
| VoxConverse | 20 | 95.9% | 92.3% | **94.0%** | 3.8x |
| SCOTUS | 5 | 99.2% | 95.4% | 94.5% | 3.1x |
| AMI | 16 | 97.0% | 93.5% | 91.4% | 3.3x |

Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters.

On SCOTUS and AMI, the post-LLM SAA is slightly lower than pre-LLM. This is a measurement artifact from transcript cleanup -- merging split-word fragments and removing filler shifts segment boundaries, which costs DER frames despite producing a better transcript.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment.

## Benchmark vs Production

These results are a **worst-case scenario** using single-channel mixed audio with no prior context. In production:

- **Dual-channel audio** eliminates local/remote speaker confusion
- **Voice profiles** enable verified speaker recognition
- **Meeting context** helps the LLM identify participants by name and role

## What the LLM Step Does

The raw diarizer outputs anonymous speaker IDs with unformatted ASR text. The LLM identifies speakers by name from transcript content, fixes ASR errors, and cleans up formatting:

**Before (raw diarization):**
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

Diarization-only, Apple M1 Max. Pyannote uses MPS (GPU); MimicScribe uses ANE.

## DER Breakdown

**Confusion** is the meaningful component. False alarm is inflated by sentence-level segmentation (silent gaps within segments are a deliberate UX choice).

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 16.5% | 2.7% | 13.2% | 0.6% |
| VoxConverse | 18.0% | 6.0% | 7.1% | 4.9% |
| SCOTUS | 8.2% | 5.5% | 0.0% | 2.7% |
| AMI | 35.7% | 8.6% | 17.0% | 10.1% |

## Corpora

| Corpus | Source | Files | Duration | Speakers |
|--------|--------|------:|---------:|---------:|
| [Earnings-21](https://huggingface.co/datasets/Revai/earnings21) | Public earnings calls | 11 | ~10 hrs | 5-15 |
| [VoxConverse](https://github.com/joonson/voxconverse) | YouTube debates/interviews | 20 | ~2 hrs | 2-6 |
| [SCOTUS](https://www.oyez.org) | Supreme Court oral arguments | 5 | ~7.5 hrs | 10-12 |
| [AMI](https://groups.inf.ed.ac.uk/ami/corpus/) | Meeting recordings (IHM-mix) | 16 | ~9 hrs | 4 |

## Methodology

- **Collar**: 0.25s | **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False`
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML
- **ASR**: Parakeet TDT 0.6B via FluidAudio CoreML
- **LLM**: Gemini 3 Flash
