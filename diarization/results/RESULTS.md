# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR + Pyannote Community-1 diarization + on-device post-clustering refinement + Gemini 3.1 Flash Lite for naming.

Run date: 2026-06-11

## What's new in this update

**Aggregate SAA 97.4% → 97.9%, aggregate confusion 2.6% → 2.1%** on the public corpus. Two new post-clustering stages carry most of the gain since the 2026-05-15 publication; the rest comes from refinement of existing stages.

The first targets a failure where a meeting grows a phantom extra speaker: short interjections — "yeah," "right," "okay" — from several real participants can collect into a cluster of their own. A new stage recognizes that profile and re-routes each interjection to the speaker it belongs to. Largest gain on AMI (+0.5 pp), where back-and-forth meeting chatter makes this failure most common.

The second targets the opposite failure: a quieter participant who never gets a cluster at all, because their voice partially resembles several louder ones — common for analysts dialing into earnings calls over telephone-quality lines, whose questions then ride along inside an executive's answer. A new recovery stage notices a sustained stretch of speech that doesn't fit any existing speaker well and gives it a speaker of its own. Largest gain on Earnings-21 (+0.8 pp), where several previously-missing analysts are now attributed.

Both stages follow the pipeline's standing bias: when uncertain, prefer an extra speaker over a merged one — merging two speakers in the UI is one click, splitting them apart is per-segment work.

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | Speedup |
|--------|------:|----------------:|----------------:|--------:|
| Earnings-21 | 11 | 98.1% | **97.7%** | 3.7x |
| VoxConverse | 20 | 95.9% | **96.4%** | 4.1x |
| SCOTUS | 5 | 99.2% | **98.9%** | 5.4x |
| AMI | 16 | 97.0% | **97.6%** | 3.7x |
| **Aggregate** | **52** | — | **97.9%** | — |

Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters.

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

**Confusion is the meaningful component, and it dropped on every corpus.** Aggregate: 2.6% → **2.1%** (−0.5 pp). Earnings-21: 3.1% → 2.3%. AMI: 2.9% → 2.4%. VoxConverse: 3.8% → 3.6%. SCOTUS: 1.3% → 1.1%.

The pipeline collapses consecutive same-speaker word runs into a single segment, even when the speaker paused mid-thought — a 4-second pause shouldn't fragment one person's quote into two transcript lines; the LLM step inserts paragraph breaks when topical structure calls for them. From pyannote's perspective, every merged-over silence between two parts of the same speaker's turn costs false-alarm frames. An ASR that drops mumbled or overlapped speech can score lower on these aggregate components than one that captures it, because missed speech can't be confused.

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 16.3% | 2.3% | 13.5% | 0.5% |
| VoxConverse | 18.8% | 3.6% | 9.5% | 5.7% |
| SCOTUS | 3.6% | 1.1% | 0.0% | 2.5% |
| AMI | 31.1% | 2.4% | 12.4% | 16.2% |
| **Aggregate** | **17.2%** | **2.1%** | **8.8%** | **6.3%** |

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

## Methodology

- **Collar**: 0.25s | **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False`
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML
- **ASR**: Parakeet TDT 0.6B via FluidAudio CoreML
- **LLM**: Gemini 3.1 Flash Lite (temp 0.1, thinking minimal)

## Reproducibility

The deterministic pipeline runs end-to-end in Swift; Python only does the LLM step and scoring. This run was produced at `parakeet-transcriber` commit `33b7394e` with default parameters.

```
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus
benchmark/.venv313/bin/python3 scripts/run_corpus_eval.py
```

The first command runs the deterministic pipeline on the 52-file corpus and writes per-file post-clustering segments plus per-stage timings. The second runs the LLM attribution and scores against the ground-truth RTTMs. Both halves persist progress per file. Audio source paths and ground-truth RTTMs come from the public corpora linked above.
