# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT v3 ASR + Pyannote Community-1 diarization with NVIDIA Nemotron 3 Diarization + on-device post-clustering refinement + Gemini 3.1 Flash Lite for naming.

Run date: 2026-09-29 (previous run: 2026-08-29)

## What's new in the 2026-09-29 update

**With NVIDIA Nemotron 3 Diarization: 57-file aggregate SAA 98.4% → 98.9%, NOTSOFAR-1 91.7% → 98.8%.** The shipping build runs Nemotron 3 alongside MimicScribe's own diarizer and lets it correct lines and speakers MimicScribe was unsure about, while MimicScribe keeps its speakers and names. Per corpus: AMI 99.1%, DiPCo 99.0%, VoxConverse 99.0%, Earnings-21 98.2%, SCOTUS 99.4%. All four diarization gates passed on the 57 files (phantom rows 9 → 9, no merge regressions; the hidden "Unknown" bucket shrank from 771 to 116 segments). The speaker list is exactly right in 45 of 57 files, up from 42 without Nemotron (one or more extra speakers in 6, one or more missing in 6); the three gained files are VoxConverse. On NOTSOFAR-1 it is exactly right in 73 of 80 meetings.

**Current main, no Nemotron: aggregate SAA 98.3% → 98.4%** on the same 57 files. Per corpus: AMI 98.1% to 98.2%, DiPCo 97.6% to 97.9%, VoxConverse 97.0% to 97.1%, Earnings-21 and SCOTUS unchanged at 98.0% and 99.4%. DER fell on four of five corpora (false alarm fell on every one): AMI 26.1% to 24.9%, DiPCo 29.5% to 28.9%, Earnings-21 15.6% to 14.4%, VoxConverse 14.8% to 14.5%, SCOTUS unchanged at 1.5%.

**A new corpus: NOTSOFAR-1 evaluation set**, 80 far-field meetings of 3 to 7 speakers (CC BY 4.0, [arXiv 2501.17304](https://arxiv.org/abs/2501.17304)). MimicScribe was not tuned on it. On this room MimicScribe scores **91.7% SAA**, well below the other corpora, because single-channel far-field audio makes it merge speakers.

The turn-level, phantom-speaker, latency and DER-breakdown sections below are from the 2026-08-29 run.

## Previous update: 2026-08-29

### What changed on 2026-08-29

**Aggregate SAA 98.1% → 98.3%** on the same 57 files (98.2% → 98.3% on the 52-file basis). Confusion — the component of the error that measures attribution — fell from 1.9% to 1.7% of reference time, and fell on every corpus: AMI 2.1% to 1.9%, DiPCo 2.6% to 2.4%, Earnings-21 2.1% to 2.0%, SCOTUS 0.8% to 0.6%, VoxConverse 3.1% to 3.0%.

Missed speech moved the other way, slightly: 6.6% to 6.8% of reference time (AMI 13.8% to 14.1%, DiPCo 24.1% to 24.5%, VoxConverse 4.0% to 4.2%, SCOTUS 0.7% to 0.9%, Earnings-21 unchanged at 0.1%). Both movements come from one change in the ASR layer: a word's timing can no longer extend past the audio that produced it. Segments end where speech ends, which trims a sliver of coverage at the tail of utterances and puts turn boundaries a little closer to where the speaker actually changed. Reported as measured, in both directions.

Substantial turns improved: 41 of the 2,987 reference turns of ten seconds or longer land under the wrong speaker, against 44 in the previous run, and 43 of the 57 files still have none. Short turns held or edged up: under two seconds and clear of other speech 60.4% to 61.0%, two to ten seconds 86.8% to 86.9%, spoken over someone 11.8% to 12.1%. Phantom speakers fell from 10 to 9 across the same 7 files, and the visible speaker list is exactly right in 43 of 57 files (was 42).

## Speaker Attribution Accuracy (SAA)

**SAA = 1 − confusion rate.** Percentage of speech time attributed to the correct speaker.

| Corpus | Files | Pyannote C1 SAA (2026-08-29 run, reference not re-run) | MimicScribe SAA, 2026-08-29 | MimicScribe SAA, 2026-09-29 | With Nemotron 3 Diarization | Speedup |
|--------|------:|----------------:|----------------:|----------------:|----------------:|--------:|
| Earnings-21 | 11 | 98.1% | 98.0% | 98.0% | **98.2%** | 3.7x |
| VoxConverse | 20 | 95.9% | 97.0% | 97.1% | **99.0%** | 4.1x |
| SCOTUS | 5 | 99.2% | 99.4% | 99.4% | **99.4%** | 5.4x |
| AMI | 16 | 97.0% | 98.1% | 98.2% | **99.1%** | 3.7x |
| DiPCo | 5 | — | 97.6% | 97.9% | **99.0%** | — |
| **Aggregate** | **57** | — | **98.3%** | **98.4%** | **98.9%** | — |
| NOTSOFAR-1 eval (not tuned on) | 80 | not run | — | 91.7% | **98.8%** | — |

The "With Nemotron 3 Diarization" column is the shipping build (CPU inference). The 2026-09-29 column is the same main without Nemotron.

On the 52-file basis used before DiPCo was added, the aggregate is **98.3%** (2026-08-29 run; the 2026-09-29 52-file figure is not recomputed here). Speedup is diarization-only on Apple M1 Max (ANE vs MPS GPU). **Pyannote C1** is the reference [community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) pipeline run in Python with default parameters; the reference has not yet been run on DiPCo or NOTSOFAR-1. Speedup is from the 2026-08-29 run.

Over-segmentation is preferred over under-segmentation. Merging two speakers in the UI is a single correction; splitting one speaker requires manual per-segment reassignment.

## Live speaker labels (during the call)

_Measured 2026-10-06 on build `2ed6b4964`._

The table above scores the finished transcript. This section scores what you see while the meeting is still going: the speaker label on each line of the live transcript, as it stood on screen at that moment.

**During the call, speaker attribution accuracy was 97.3%**, on the same measure as the SAA table above, against the same human reference timelines. Counted only over the speech that already carried a speaker label, **96.6% of it was under the right speaker.**

| Files | Voice profiles | Hours | SAA during the call | Of labeled speech, right speaker | SAA, last screen before stop | Speech under a label, during the call |
|-------|----------------|------:|------:|------:|------:|------:|
| AMI ES2004c/d, IS1009c/d, TS3003c/d | saved from earlier meetings in the series | 2.02 | 98.3% | 98.1% | 98.4% | 87.8% |
| AMI EN2002a, NOTSOFAR-1 MTG_32003/05/08 | none | 0.70 | 94.7% | 92.8% | 95.0% | 73.1% |
| **All 10** | | **2.72** | **97.3%** | **96.6%** | **97.4%** | **83.6%** |

How it is measured:

- Each recording is replayed through the live pipeline at twice real speed, played in as the call's remote audio, as if every participant were on the other end of a video call. AMI files run their first 20 minutes; the three NOTSOFAR-1 meetings are about 7 minutes each.
- **Voice profiles.** Six AMI files ran with saved profiles of their participants, enrolled from earlier meetings in the same series (never from the meeting being scored), the way a returning team would use the app. The other four had none. The table reports the two groups separately; with no profiles, attribution is about 3.6 points lower.
- **During the call.** The screen is scored at every 30 seconds of meeting time, each time against only the speech heard so far. Errors and speech are summed over those snapshots, so a snapshot counts in proportion to the speech it covers. Each file counts in proportion to its own speech in every column.
- **What SAA leaves out.** As in the finished-transcript SAA, speech without a speaker label is not counted as wrong. During the call that is 16.4% of reference speech: 4.8% sits on lines still showing the neutral "Remote" label, and the rest is speech not on screen yet or not transcribed. The "of labeled speech" column divides by labeled speech only. Counting the "Remote" lines as wrong, attribution reads 92.5% during the call and 95.9% at the last screen. Lines can stay "Remote" for some time before they are identified; by the last screen 1.5% of speech is still unlabeled.
- **Label changes are not penalized.** The best match between on-screen labels and real speakers is worked out at each snapshot, so a line that moves from one label to another between snapshots is scored on where it sits at that moment. This measures how well speech is grouped by speaker at each point in the call, not how stable the labels are.
- **The last column is the live screen.** "Last screen before stop" is the live transcript at the end of the replayed excerpt, not the finished transcript scored above, and the AMI excerpts are the first 20 minutes, not whole meetings.

What this does not cover:

- Ten files is a small basis next to the 57 above, and it is one run. Two earlier runs of the same files, on the two builds before this one, read 97.1% and 95.3% during the call.
- NOTSOFAR-1's far-field rooms are the weak spot: 90–94% per file during the call, against 96.7–99.6% on AMI.
- The local microphone channel is not scored here. These recordings have one channel, so everything plays as remote audio.
- Whether the name shown on a line is the right person is a separate measurement and not part of these numbers.

| File | Corpus | Voice profiles | SAA during the call | Of labeled speech | SAA, last screen |
|------|--------|---|---------:|---------:|---------:|
| ES2004c | AMI | yes | 98.9% | 98.7% | 99.2% |
| ES2004d | AMI | yes | 97.8% | 97.3% | 98.4% |
| IS1009c | AMI | yes | 98.9% | 98.7% | 98.7% |
| IS1009d | AMI | yes | 97.8% | 97.5% | 97.7% |
| TS3003c | AMI | yes | 99.6% | 99.6% | 99.3% |
| TS3003d | AMI | yes | 97.0% | 96.6% | 96.7% |
| EN2002a | AMI | no | 96.7% | 95.5% | 96.1% |
| MTG_32003 | NOTSOFAR-1 | no | 93.5% | 90.0% | 94.9% |
| MTG_32005 | NOTSOFAR-1 | no | 90.2% | 88.1% | 91.1% |
| MTG_32008 | NOTSOFAR-1 | no | 94.0% | 91.0% | 95.6% |

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
| [NOTSOFAR-1](https://arxiv.org/abs/2501.17304) (eval set, CC BY 4.0; not tuned on) | Far-field single-channel meetings | 80 | ~8.3 hrs | 3–7 |

## Methodology

- **Collar**: 0.25s — a quarter-second on each side of every reference boundary is excluded from scoring (standard practice; boundary placement inside the collar is not measured)
- **Scoring**: [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/) DiarizationErrorRate, `skip_overlap=False` — overlapping speech is scored, not excluded
- **Turn-level metrics**: a turn is consecutive same-speaker reference speech merged across gaps ≤ 1.0s (turns of 2s or more are scored; the 2026-08-29 text said 0.5s, but `over_split_diagnostic.py` uses 1.0s); a turn counts as correctly attributed when the majority of the transcribed time in its span carries that speaker's (optimally mapped) label; "spoken over someone" means more than half the turn coincides with another speaker's reference speech
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML, with NVIDIA Nemotron 3 Diarization (FluidAudio CoreML, CPU)
- **ASR**: Parakeet TDT 0.6B v3 via FluidAudio CoreML. Every run behind these numbers used v3; the app now ships Parakeet Ultra, which has not been scored here.
- **LLM**: Gemini 3.1 Flash Lite (temp 0.1, thinking minimal)

## Reproducibility

The deterministic pipeline runs end-to-end in Swift; Python only does scoring (and, separately, the LLM step — which does not produce the published score). The 2026-08-29 run was produced at `parakeet-transcriber` commit `5c847cf5` with default parameters. The 2026-09-29 runs were produced at commit `db5059662` (without Nemotron) and `9677ee3be` (with Nemotron 3, the shipping configuration).

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
| 2026-08-29 | 57 | 98.3% | Word timings no longer overrun the audio that produced them: confusion 1.9% → 1.7% with missed speech 6.6% → 6.8%; substantial-turn misattribution 44 → 41 of 2,987; phantom rows 10 → 9 |
| 2026-09-29 | 57 | **98.4%** | Current main: DER fell on four of five corpora (AMI 26.1% → 24.9%); NOTSOFAR-1 (80 meetings) added at 91.7%, not tuned on. With NVIDIA Nemotron 3 Diarization: **98.9%**, NOTSOFAR-1 98.8% |

Aggregates are comparable only within the same file basis: 58 → 52 removed the Podcast corpus (May 2026); 52 → 57 added DiPCo (July 2026). On the shared 52-file basis, the 2026-07-17 and 2026-08-25 runs both score 98.2% and the 2026-08-29 run scores 98.3%.
