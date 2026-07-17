# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR + Pyannote Community-1 diarization + on-device post-clustering refinement + Gemini 3.1 Flash Lite for naming.

Run date: 2026-07-17

## What's new in this update

**Aggregate SAA 97.9% → 98.2% on the same 52 files as the previous publication, and the corpus grows to 57 files with the addition of DiPCo** (dinner-party conversations). On the expanded 57-file corpus the aggregate is 98.1%. Confusion dropped on every corpus.

Most of the gain comes from work on phantom extra speakers — clusters the diarizer creates that don't correspond to any real participant. Two failure shapes were addressed since the last publication.

The first is the *turn-opening* phantom. The first words of a speaking turn sound measurably different from the same speaker's steady voice — the effect is strongest through Bluetooth headsets, whose audio processing ramps in over the first moments of speech. Those opening slivers can collect into a phantom speaker of their own, so a meeting shows an extra participant who only ever says the first few words of someone else's turns. A new stage recognizes a cluster made almost entirely of turn openings and routes each opener to the speaker who actually continued the turn. Related handling covers switching input devices mid-meeting (connecting or disconnecting a headset): the brief settling period after a switch no longer feeds speaker identity.

The second is a refinement of the existing interjection-cluster dissolution: a grab-bag cluster of one-word acknowledgments from several participants is now recognized even when a single longer aside sits among them and previously disguised the cluster as a real speaker.

Alongside these, a brief fragment that can't be confidently placed with any speaker now parks in a hidden "Unknown" bucket instead of being forced into the nearest cluster — a wrong attribution is harder to notice and undo than a missing one. This follows the pipeline's standing bias: when uncertain, prefer a recoverable error over an invisible one.

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | Speedup |
|--------|------:|----------------:|----------------:|--------:|
| Earnings-21 | 11 | 98.1% | **98.0%** | 3.7x |
| VoxConverse | 20 | 95.9% | **97.2%** | 4.1x |
| SCOTUS | 5 | 99.2% | **99.0%** | 5.4x |
| AMI | 16 | 97.0% | **97.8%** | 3.7x |
| DiPCo | 5 | — | **97.4%** | — |
| **Aggregate** | **57** | — | **98.1%** | — |

On the previous publication's 52-file basis (DiPCo excluded), the aggregate is **98.2%** — up from 97.9%. Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters; the reference has not yet been run on DiPCo.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment.

## What the LLM step does

The deterministic pipeline outputs anonymous speaker IDs (e.g. `Speaker 2`) with raw ASR text. The LLM pass renames each cluster from transcript context, fixes ASR errors, and cleans up formatting:

**Before (deterministic pipeline output):**
```
[  10.9-149.0] Speaker 2:  ? Mr. Chief Justice, and may it please the court, the Fifth Circuit's
                            decision in this case is the f...
[ 154.6-158.9] Speaker 3:  w. Are there any limits on what Congress can do
[ 388.1-389.0] Speaker 2:  you're
[ 389.0-459.0] Speaker 1:  you have a very aggressive view of Congress's authority...
```

**After (LLM naming + cleanup):**
```
[  10.9-149.0] Elizabeth Prelogar:  Mr. Chief Justice, and may it please the court, the Fifth
                                    Circuit's decision in this case is the fir...
[ 154.6-158.9] Justice Thomas:     Are there any limits on what Congress can do?
[ 388.1-459.0] Speaker 1:          General, one of the things that struck me as I was reading
                                    it, you have a very aggressive view of Co...
```

A cluster is renamed only when the transcript directly identifies that speaker — by self-introduction, by another speaker addressing them, or by a role mentioned in the transcript. Clusters without identification keep their cluster ID. The model is instructed to default to the cluster ID rather than guess from setting or topic.

The LLM is also not allowed to give two cluster IDs the same name. A deterministic post-process verifies this: if the model attempts to collapse two acoustic clusters under one identity, the larger cluster keeps the name and the other is reset to its cluster ID. The published SAA is the deterministic-pipeline score; the LLM names speakers but does not produce the score reported in this table.

## Post-clustering refinement

The deterministic pipeline does not stop at the diarizer's output. Several on-device stages run between clustering and the LLM step, addressing common failure modes: turn-change boundaries that land a few seconds off, chunks the clustering placed in the wrong cluster on long meetings or with similar-voice speakers, sentence-boundary integration that recovers speakers whose entire contribution sits between acoustic-chunk boundaries, dissolution of phantom clusters that collect short interjections from several participants, and recovery of quiet speakers absorbed into an acoustically similar neighbor. These stages run on the Neural Engine and on cached embeddings — total cost is well under 10 s per 30-minute meeting.

This phase carries most of the difference between the Pyannote C1 SAA column and the MimicScribe SAA column.

## Latency

| Corpus | File | Audio | Pyannote | MimicScribe | Speedup |
|--------|------|------:|---------:|------------:|--------:|
| VoxConverse | duvox | 16 min | 47.7s | 11.5s | 4.1x |
| SCOTUS | 22-842 | 74 min | 312.7s | 57.6s | 5.4x |
| Earnings-21 | 4320211 | 55 min | 208.7s | 56.6s | 3.7x |
| AMI | ES2004a | 17 min | 53.4s | 14.5s | 3.7x |

Diarization-only, Apple M1 Max. Pyannote uses MPS (GPU); MimicScribe uses ANE.

## DER Breakdown

The DER number on this benchmark mixes three components, only one of which measures attribution quality:

- **Confusion** — was the right speaker tagged on speech the system actually transcribed?
- **Missed speech** — speech the system didn't emit at all. Driven by ASR coverage, not diarization.
- **False alarm** — hyp-tagged speech that ref marks as silence. Driven by UX choices about how segments are drawn.

**Confusion is the meaningful component, and it dropped on every corpus.** Aggregate: 2.1% → **1.9%** (1.8% on the previous publication's 52-file basis). Earnings-21: 2.3% → 2.0%. AMI: 2.4% → 2.2%. VoxConverse: 3.6% → 2.8%. SCOTUS: 1.1% → 1.0%. The aggregate missed-speech component rises with this update because the newly added DiPCo — overlapping dinner-table conversation — carries 25.9% missed speech; that is ASR coverage on hard audio, not attribution error.

The pipeline collapses consecutive same-speaker word runs into a single segment, even when the speaker paused mid-thought — a 4-second pause shouldn't fragment one person's quote into two transcript lines; the LLM step inserts paragraph breaks when topical structure calls for them. From pyannote's perspective, every merged-over silence between two parts of the same speaker's turn costs false-alarm frames. An ASR that drops mumbled or overlapped speech can score lower on these aggregate components than one that captures it, because missed speech can't be confused.

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 16.2% | 2.0% | 13.5% | 0.7% |
| VoxConverse | 15.8% | 2.8% | 7.5% | 5.5% |
| SCOTUS | 3.4% | 1.0% | 0.0% | 2.4% |
| AMI | 28.2% | 2.2% | 9.7% | 16.3% |
| DiPCo | 31.0% | 2.6% | 2.4% | 25.9% |
| **Aggregate** | **17.4%** | **1.9%** | **7.4%** | **8.2%** |

## Benchmark vs Production

These results are a **worst-case scenario** using single-channel mixed audio with no prior context. In production:

- **Dual-channel audio** eliminates local/remote speaker confusion.
- **Voice profiles** enable verified speaker recognition.
- **Meeting context** helps the LLM identify participants by name and role.

## Corpora

| Corpus | Source | Files | Duration | Speakers |
|--------|--------|------:|---------:|---------:|
| [Earnings-21](https://huggingface.co/datasets/Revai/earnings21) | Public earnings calls | 11 | ~10 hrs | 5–15 |
| [VoxConverse](https://github.com/joonson/voxconverse) | YouTube debates/interviews | 20 | ~2 hrs | 2–6 |
| [SCOTUS](https://www.oyez.org) | Supreme Court oral arguments | 5 | ~7.5 hrs | 10–12 |
| [AMI](https://groups.inf.ed.ac.uk/ami/corpus/) | Meeting recordings (IHM-mix) | 16 | ~9 hrs | 4 |
| [DiPCo](https://arxiv.org/abs/1909.13447) | Dinner-party conversations | 5 | ~2.5 hrs | 4 |

## Methodology

- **Collar**: 0.25s | **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False`
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML
- **ASR**: Parakeet TDT 0.6B via FluidAudio CoreML
- **LLM**: Gemini 3.1 Flash Lite (temp 0.1, thinking minimal)

## Reproducibility

The deterministic pipeline runs end-to-end in Swift; Python only does scoring (and, separately, the LLM step — which does not produce the published score). This run was produced at `parakeet-transcriber` commit `d4a99c61` with default parameters.

```
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus
PYTHONPATH=benchmark/src benchmark/.venv313/bin/python3 -m mimicscribe_bench.runner
```

The first command runs the deterministic pipeline on the 57-file corpus and writes per-file post-clustering segments plus per-stage timings. The second scores them against the ground-truth RTTMs (pyannote.metrics, optimal mapping, 0.25s collar). Both halves persist progress per file. Audio source paths and ground-truth RTTMs come from the public corpora linked above.
