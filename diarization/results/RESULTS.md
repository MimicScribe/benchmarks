# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR + Pyannote Community-1 diarization + on-device post-clustering refinement + Gemini 3.1 Flash Lite for naming.

Run date: 2026-08-29

## What's new in this update

**Aggregate SAA 98.1% → 98.3%** on the same 57 files (98.2% → 98.3% on the 52-file basis). Confusion — the component of the error that measures attribution — fell from 1.9% to 1.7% of reference time, and fell on every corpus: AMI 2.1% to 1.9%, DiPCo 2.6% to 2.4%, Earnings-21 2.1% to 2.0%, SCOTUS 0.8% to 0.6%, VoxConverse 3.1% to 3.0%.

Missed speech moved the other way, slightly: 6.6% to 6.8% of reference time (AMI 13.8% to 14.1%, DiPCo 24.1% to 24.5%, VoxConverse 4.0% to 4.2%, SCOTUS 0.7% to 0.9%, Earnings-21 unchanged at 0.1%). Both movements come from one change in the ASR layer: a word's timing can no longer extend past the audio that produced it. Segments end where speech ends, which trims a sliver of coverage at the tail of utterances and puts turn boundaries a little closer to where the speaker actually changed. Reported as measured, in both directions.

Substantial turns improved: 41 of the 2,987 reference turns of ten seconds or longer land under the wrong speaker, against 44 in the previous run, and 43 of the 57 files still have none. Short turns held or edged up: under two seconds and clear of other speech 60.4% to 61.0%, two to ten seconds 86.8% to 86.9%, spoken over someone 11.8% to 12.1%. Phantom speakers fell from 10 to 9 across the same 7 files, and the visible speaker list is exactly right in 43 of 57 files (was 42).

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA | MimicScribe SAA | Speedup |
|--------|------:|----------------:|----------------:|--------:|
| Earnings-21 | 11 | 98.1% | **98.0%** | 3.7x |
| VoxConverse | 20 | 95.9% | **97.0%** | 4.1x |
| SCOTUS | 5 | 99.2% | **99.4%** | 5.4x |
| AMI | 16 | 97.0% | **98.1%** | 3.7x |
| DiPCo | 5 | — | **97.6%** | — |
| **Aggregate** | **57** | — | **98.3%** | — |

On the 52-file basis used before DiPCo was added, the aggregate is **98.3%**. Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters; the reference has not yet been run on DiPCo.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment.

## Turn-level accuracy

SAA weights speech by time, so long turns dominate it. The questions a reader actually has are sharper: **is a substantial contribution ever credited to the wrong person**, and what happens on quick exchanges? Turn-level scoring on the same run answers both (definitions under Methodology).

**Substantial turns.** Of the 2,987 turns of ten seconds or longer across the corpus, 41 (**1.4%**) end up under the wrong speaker's label. 43 of the 57 files have none. At five seconds or longer it is 3.2%. The misattributed turns concentrate in the hardest rooms: the two crowded, overlap-heavy meeting series (AMI's EN2002 four-way discussions and DiPCo's dinner parties) account for more than half of the 41.

**Quick exchanges.** Attribution falls off with turn length:

| Reference turn | Turns | Attributed to the correct speaker |
|----------------|------:|----------------------------------:|
| Over 10s | 2,983 | 98.6% |
| 2–10s | 6,601 | 86.9% |
| Under 2s, clear of other speech | 3,387 | 61.0% |
| Under 2s, spoken over someone | 4,646 | 12.1% |

The remainder of each row splits between wrong-speaker and not-transcribed; short turns are both the hardest to attribute and the most likely to be dropped by the ASR. The last row is mostly a representation limit rather than an attribution error: the transcript is a single stream, so a backchannel spoken over someone else is usually absorbed into the dominant speaker's line or not transcribed at all. This is the granularity frontier: the numbers this benchmark should be judged on improving.

## Phantom-speaker accounting

SAA measures how much speech time lands on the wrong speaker — it barely moves when the pipeline invents a small extra speaker. So this benchmark also counts **phantom speakers** directly: clusters in the output whose speech belongs to a participant already represented by another cluster. On this run, 50 of the 57 files have no phantom speaker. Of the seven that do, five have one and two have two.

| Corpus | Files | Files with a phantom speaker |
|--------|------:|-----------------------------:|
| Earnings-21 | 11 | 1 |
| VoxConverse | 20 | 5 |
| SCOTUS | 5 | 0 |
| AMI | 16 | 1 |
| DiPCo | 5 | 0 |
| **Total** | **57** | **7** |

Counting visible speakers directly (the hidden Unknown bucket excluded): the speaker list is exactly right in 43 of 57 files, shows one extra speaker in 5, and is missing one speaker in 9. The missing-speaker files are the under-segmentation the over-segmentation preference cannot reach — typically a quiet participant absorbed into an acoustically similar neighbor.

## What the LLM step does

The deterministic pipeline outputs anonymous speaker IDs (`Speaker 2`) with raw ASR text. A short LLM pass then names clusters and cleans up the text: "Speaker 2" becomes "Justice Thomas" when the transcript itself identifies that speaker (a self-introduction, being addressed by name or office, an explicit attribution); clusters without identification keep their ID rather than getting a guess. The LLM does not decide the speaker structure — which clusters exist is settled deterministically before it runs, and two clusters can never share a name. The published SAA is the deterministic pipeline's score: the harness re-scores the transcript after the LLM pass and checks that the attribution number is unchanged.

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

Diarization-only, Apple M1 Max. Pyannote uses MPS (GPU); MimicScribe uses ANE. These timings are carried forward from the 2026-07-17 run; the reference pipeline was not re-run for this publication.

## DER Breakdown

The DER number on this benchmark mixes three components, only one of which measures attribution quality:

- **Confusion** — was the right speaker tagged on speech the system actually transcribed?
- **Missed speech** — speech the system didn't emit at all. Driven by ASR coverage, not diarization.
- **False alarm** — hyp-tagged speech that ref marks as silence. Driven by UX choices about how segments are drawn.

**Confusion is the meaningful component, and it fell from 1.9% to 1.7% aggregate** (1.8% to 1.7% on the 52-file basis). Per corpus: Earnings-21 2.1% to 2.0%, AMI 2.1% to 1.9%, VoxConverse 3.1% to 3.0%, SCOTUS 0.8% to 0.6%, DiPCo 2.6% to 2.4%. Aggregate DER is flat at 16.0%: the confusion gain is offset by missed speech rising from 6.6% to 6.8% — ASR coverage, not attribution — with false alarm unchanged at 7.5%.

The pipeline collapses consecutive same-speaker word runs into one segment even across mid-thought pauses — a 4-second pause shouldn't split one person's quote into two transcript lines — and every merged-over pause costs false-alarm frames in this scoring. Note the anti-gaming asymmetry: a system that drops mumbled or overlapped speech shows *less* confusion than one that captures it, because missed speech can't be misattributed.

| Corpus | DER | Confusion | False Alarm | Missed |
|--------|----:|----------:|------------:|-------:|
| Earnings-21 | 15.6% | 2.0% | 13.5% | 0.1% |
| VoxConverse | 14.8% | 3.0% | 7.6% | 4.2% |
| SCOTUS | 1.5% | 0.6% | 0.0% | 0.9% |
| AMI | 26.1% | 1.9% | 10.0% | 14.1% |
| DiPCo | 29.5% | 2.4% | 2.6% | 24.5% |
| **Aggregate** | **16.0%** | **1.7%** | **7.5%** | **6.8%** |

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

- **Collar**: 0.25s — a quarter-second on each side of every reference boundary is excluded from scoring (standard practice; boundary placement inside the collar is not measured)
- **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False` — overlapping speech is scored, not excluded
- **Turn-level metrics**: a turn is consecutive same-speaker reference speech merged across gaps ≤ 0.5s; a turn counts as correctly attributed when the majority of the transcribed time in its span carries that speaker's (optimally mapped) label; "spoken over someone" means more than half the turn coincides with another speaker's reference speech
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML
- **ASR**: Parakeet TDT 0.6B via FluidAudio CoreML
- **LLM**: Gemini 3.1 Flash Lite (temp 0.1, thinking minimal)

## Reproducibility

The deterministic pipeline runs end-to-end in Swift; Python only does scoring (and, separately, the LLM step — which does not produce the published score). This run was produced at `parakeet-transcriber` commit `5c847cf5` with default parameters.

```
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus
PYTHONPATH=benchmark/src benchmark/.venv313/bin/python3 -m mimicscribe_bench.runner
```

The first command runs the deterministic pipeline on the 57-file corpus and writes per-file post-clustering segments plus per-stage timings. The second scores them against the ground-truth RTTMs (pyannote.metrics, optimal mapping, 0.25s collar). Both halves persist progress per file. Audio source paths and ground-truth RTTMs come from the public corpora linked above.

## Publication history

Every published run of this benchmark, oldest to newest. The full text of each version is in this repository's git history.

| Run date | Files | Aggregate SAA | What changed |
|----------|------:|--------------:|--------------|
| 2026-04-28 | 58 | 94.7% | First published run in the current form: context-gated LLM naming, acoustic boundary snap |
| 2026-04-30 | 58 | 94.8% | Wider acoustic boundary snap |
| 2026-05-02 | 58 | 95.1% | Chunk-level correction step — chunks the clustering placed in the wrong cluster are reassigned before the LLM |
| 2026-05-06 | 58 | 95.0% | Orphan-fragment reabsorption; the no-collapse rule on LLM naming became a deterministic check |
| 2026-05-15 | 52 | 97.4% | Sentence-boundary clustering refinement. The 6 Podcast files were removed after their AI-generated reference labels failed an aural spot-check — every remaining file uses human-verified references |
| 2026-06-11 | 52 | 97.9% | Phantom-cluster dissolution; recovery of quiet speakers absorbed into an acoustically similar neighbor |
| 2026-07-17 | 57 | 98.1% | DiPCo (dinner-party) corpus added; turn-opening phantom routing; interjection-cluster dissolution refined; unplaceable fragments park in a hidden "Unknown" bucket |
| 2026-08-25 | 57 | 98.1% | ASR recovery work: missed speech 8.2% → 6.6% with confusion flat at 1.9%; short-turn attribution up in every bucket |
| 2026-08-29 | 57 | **98.3%** | Word timings no longer overrun the audio that produced them: confusion 1.9% → 1.7% with missed speech 6.6% → 6.8%; substantial-turn misattribution 44 → 41 of 2,987; phantom rows 10 → 9 |

Aggregates are comparable only within the same file basis: 58 → 52 removed the Podcast corpus (May 2026); 52 → 57 added DiPCo (July 2026). On the shared 52-file basis, the 2026-07-17 and 2026-08-25 runs both score 98.2% and the 2026-08-29 run scores 98.3%.
