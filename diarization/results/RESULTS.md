# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet Ultra (spoken-form fine-tune) / Parakeet TDT v3 ASR + Pyannote Community-1 diarization with NVIDIA Nemotron 3 Diarization + on-device post-clustering refinement + Gemini 3.1 Flash Lite for naming.

Run date: 2026-11-27 (live speaker labels update; post-stop SAA/DER last measured 2026-09-29)

## What's new in the 2026-11-27 update (live speaker separation & labeling)

**Live speaker attribution on cold-start meetings rose from 94.7% to 96.5% SAA (+1.8 pp)** on the four unprofiled meetings shared with the 2026-10-06 measurement (`EN2002a`, `MTG_32003`, `MTG_32005`, `MTG_32008`), with speech carrying a speaker label up from `73.1%` to `75.5%` and last-screen accuracy up from `95.0%` to `96.9%`. Across an expanded **10-meeting cold-start suite** (6 AMI meetings + 4 far-field NOTSOFAR-1 meetings, 1.7 hours, no saved voice profiles), MimicScribe scores **97.3% live SAA during the call** (**98.4%** on AMI, **95.0%** on far-field NOTSOFAR-1), matches the **exact speaker count in 9 of 10 meetings** (0 missing speakers, 1 meeting with one extra speaker), and reaches **80.9% right labels within 10 seconds** of a line ending (**85.2%** on AMI).

We also add two live measurements that were missing on 2026-10-06: **label accuracy and stability over time** (`+5 s` to `+30 s`, provisional flips, and confirmed-label accuracy) and **quiet `1×` real-time turn-separation latency** on public recordings so Neural Engine and queue time are measured directly rather than hidden behind an audio clock.

## What's new in the 2026-09-29 update (post-stop diarization)

**With NVIDIA Nemotron 3 Diarization: 57-file aggregate SAA 98.4% → 98.9%, NOTSOFAR-1 91.7% → 98.8%.** The shipping build runs Nemotron 3 alongside MimicScribe's own diarizer and lets it correct lines and speakers MimicScribe was unsure about, while MimicScribe keeps its speakers and names. Per corpus: AMI 99.1%, DiPCo 99.0%, VoxConverse 99.0%, Earnings-21 98.2%, SCOTUS 99.4%. All four diarization gates passed on the 57 files (phantom rows 9 → 9, no merge regressions; the hidden "Unknown" bucket shrank from 771 to 116 segments). The speaker list is exactly right in 45 of 57 files, up from 42 without Nemotron (one or more extra speakers in 6, one or more missing in 6); the three gained files are VoxConverse. On NOTSOFAR-1 it is exactly right in 73 of 80 meetings.

**Current main, no Nemotron: aggregate SAA 98.3% → 98.4%** on the same 57 files. Per corpus: AMI 98.1% to 98.2%, DiPCo 97.6% to 97.9%, VoxConverse 97.0% to 97.1%, Earnings-21 and SCOTUS unchanged at 98.0% and 99.4%. DER fell on four of five corpora (false alarm fell on every one): AMI 26.1% to 24.9%, DiPCo 29.5% to 28.9%, Earnings-21 15.6% to 14.4%, VoxConverse 14.8% to 14.5%, SCOTUS unchanged at 1.5%.

**A new corpus: NOTSOFAR-1 evaluation set**, 80 far-field meetings of 3 to 7 speakers (CC BY 4.0, [arXiv 2501.17304](https://arxiv.org/abs/2501.17304)). MimicScribe was not tuned on it. On this room MimicScribe scores **91.7% SAA**, well below the other corpora, because single-channel far-field audio makes it merge speakers.

The turn-level, phantom-speaker, latency and DER-breakdown sections below are from the 2026-08-29 run.

## Speaker Attribution Accuracy (SAA — saved transcript after Stop)

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

## Live speaker labels & separation (during the call)

_Measured **2026-11-27** on release build `541309fd0` (shipped Parakeet Ultra spoken-form model + live Pyannote/WeSpeaker/Nemotron stack). The saved-profile row below is carried forward from the 2026-10-06 build (`2ed6b4964`) and dated separately._

The table above scores the finished transcript after Stop. This section scores what appears on screen **while the meeting is still running**: how accurately lines are grouped, how quickly a new speaker separates onto their own row, how fast the right label arrives, and how steady confirmed labels stay. All audio processing runs on-device on Apple Silicon.

### Live speaker attribution accuracy (cold start, no voice profiles)

Ten public meetings replayed as remote call audio with no prior voice profiles (first 10 minutes of 6 AMI meetings + 4 full NOTSOFAR-1 far-field meetings, 1.7 hours total):

| Subset | Voice profiles | Hours | SAA during the call | Of labeled speech, right speaker | SAA, last screen before Stop | Speech under a label, during the call | Exact speaker count |
|---|---|---:|---:|---:|---:|---:|---:|
| **AMI (6 meetings)** (`EN2002a/b`, `EN2006b`, `ES2004c`, `IS1009c`, `TS3005a`) | none | 1.02 | **98.4%** | **97.7%** | **98.5%** | 78.0% | **5 / 6** |
| **NOTSOFAR-1 far-field (4 meetings)** (`MTG_32000/03/05/08`) | none | 0.68 | **95.0%** | **93.1%** | **95.4%** | 75.9% | **4 / 4** |
| **All 10 cold-start meetings (2026-11-27)** | **none** | **1.70** | **97.3%** | **96.2%** | **97.5%** | **77.3%** | **9 / 10** |
| *4-file overlap vs. 2026-10-06 (`EN2002a`, `MTG_32003/05/08`)* | *none* | *0.68* | *94.7% → **96.5%*** | *92.8% → **95.1%*** | *95.0% → **96.9%*** | *73.1% → **75.5%*** | *4 / 4* |
| *Prior profiled-team suite (2026-10-06, `2ed6b4964`, AMI `ES2004c/d`, `IS1009c/d`, `TS3003c/d`)* | *saved from earlier meetings* | *2.02* | *98.3%* | *98.1%* | *98.4%* | *87.8%* | *—* |

Across the 10 cold-start meetings, the live visible speaker count matches the ground-truth count (speakers with ≥ 5 s of speech) in **9 of 10 meetings** — 1 meeting (`EN2002b`) shows one extra speaker and **0 meetings** miss a real speaker.

### Label accuracy over time and label stability

Rather than only scoring end-of-meeting grouping, we check the speaker label shown on screen **`+5 s`, `+10 s`, `+15 s`, and `+30 s`** after each line ends (fair speaker-group mapping against human RTTM timelines), paired with stability checks so showing labels faster cannot be gamed by flickering or guessing prematurely:

| Replay basis | `+5 s` right / unlabeled / wrong | `+10 s` right / unlabeled / wrong | `+15 s` right / unlabeled / wrong | `+30 s` right / unlabeled / wrong | Provisional labels switching speaker | Confirmed labels that later changed | Confirmed-label accuracy | Median time to confirmed label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **AMI (6 meetings, deterministic audio clock)** | **70.0%** / 29.0% / 1.0% | **85.2%** / 12.6% / 2.2% | **90.2%** / 6.7% / 3.1% | **91.3%** / 5.6% / 3.1% | **0.10%** | 4.6% | **95.8%** | 8.8 s |
| **NOTSOFAR-1 (4 far-field meetings, audio clock)** | 46.9% / 48.3% / 4.8% | 74.2% / 22.4% / 3.5% | 84.4% / 11.1% / 4.5% | 87.9% / 8.5% / 3.5% | 2.96% | 10.3% | 92.5% | 8.8 s |
| **All 10 cold-start meetings (audio clock)** | **61.0%** / 36.5% / 2.5% | **80.9%** / 16.4% / 2.7% | **87.9%** / 8.4% / 3.6% | **90.0%** / 6.7% / 3.3% | **1.22%** | 6.8% | **94.5%** | 8.8 s |
| **Real-time `1×` playback (4 public meetings, M1 Max)** | **60.8%** / 37.5% / 1.7% | **83.7%** / 14.2% / 2.1% | **89.4%** / 7.2% / 3.4% | **91.2%** / 4.9% / 3.8% | **0.16%** *(0.00% AMI)* | 8.8% | **94.7%** | 8.8 s |

### Turn-separation speed (how fast a speaker switch splits onto a new row)

A deterministic audio-clock replay pauses for model work at every step, so it measures decisions without Neural Engine or queue delay. To measure what a reader actually experiences, we run **quiet serial `1×` real-time replays** on Apple M1 Max alongside the 10-meeting deterministic suite, using strict separation (a new turn counts as separated only when its primary row shares no overlap with the previous speaker's turn) plus **word-level wrong-row share** (which catches both late splits and splits placed at the wrong sentence):

| Replay basis | Speaker changes scored | Unseparated turns | Median time to split after speaker change | Median time to split after words appear | All-changes censored median | Words on wrong speaker's row (`+5 s` → `+12 s` → Stop) |
|---|---:|---:|---:|---:|---:|---:|
| **Real-time `1×` playback** (4 public meetings: `EN2002a`, `EN2006b`, `ES2004c`, `MTG_32005`, 21 min) | 60 | 11 | **9.4 s** *(p90 18.0 s)* | **6.0 s** *(p90 15.4 s)* | **10.8 s** | **16.8% → 10.4% → 7.7%** |
| **Deterministic audio clock** (10 public meetings, 1.7 h; excludes model queue time) | 344 | 76 | 8.0 s *(p90 13.9 s)* | 5.0 s *(p90 11.0 s)* | 8.8 s | 15.7% → 10.3% → 7.9% |

The `~1.4 s` gap between audio-clock (`8.0 s`) and real `1×` (`9.4 s`) reflects actual on-device model inference and queue latency during live recording.

### Per-file live breakdown (2026-11-27, cold start, no voice profiles)

| File | Corpus | SAA during the call | Of labeled speech | SAA, last screen | Visible / true speakers |
|---|---|---:|---:|---:|---:|
| EN2002a | AMI | 98.4% | 97.9% | 98.9% | 4 / 4 |
| EN2002b | AMI | 98.9% | 98.1% | 98.5% | 5 / 4 |
| EN2006b | AMI | 94.7% | 91.7% | 95.7% | 4 / 4 |
| ES2004c | AMI | 99.3% | 99.2% | 99.2% | 4 / 4 |
| IS1009c | AMI | 99.5% | 99.5% | 99.5% | 2 / 2 |
| TS3005a | AMI | 99.0% | 99.0% | 98.8% | 4 / 4 |
| MTG_32000 | NOTSOFAR-1 | 93.8% | 91.6% | 93.9% | 4 / 4 |
| MTG_32003 | NOTSOFAR-1 | 97.4% | 96.8% | 97.6% | 4 / 4 |
| MTG_32005 | NOTSOFAR-1 | 96.2% | 95.6% | 95.9% | 4 / 4 |
| MTG_32008 | NOTSOFAR-1 | 92.9% | 89.0% | 94.4% | 4 / 4 |

### How live speaker labels are measured — and honest caveats

- **Hardest channel condition (single-channel remote audio):** Every participant in these public recordings plays through the remote/system channel while the microphone channel is silent. In real video calls, your own microphone is captured on its own isolated channel, so local-vs-remote separation is immediate.
- **Cold start vs. returning teams:** All 2026-11-27 rows above run with zero saved voice profiles — every speaker is discovered from scratch during the call. Returning teams with enrolled voice profiles generally reach higher coverage earlier (see the dated 2026-10-06 profiled-team row).
- **Far-field rooms stay harder:** NOTSOFAR-1 single-channel far-field audio trails AMI close-talk audio (`95.0%` vs `98.4%` live SAA; `74.2%` vs `85.2%` right at `+10 s`), and accounts for most provisional speaker switches (`2.96%` vs `0.10%` on AMI).
- **Audio clock vs. `1×` real time:** Deterministic audio-clock replays are repeatable across builds and best for accuracy and regression gating; real-time `1×` replays are slower by real Neural Engine + queue time (~1–1.5 s) and vary slightly across runs. Both are reported beside each other rather than quoting the faster audio-clock figure alone.
- **What SAA leaves out:** As in post-stop SAA, speech without a speaker label yet is not counted as wrong. Counting unlabeled "Remote" lines as wrong reads `93.3%` during the call and `95.5%` at the last screen across the 10 meetings (`90.7%` / `94.2%` on `1×`).

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

**Confusion is the meaningful component, and it dropped on every corpus.** Aggregate: 1.9% → **1.7%** (1.8% to 1.7% on the 52-file basis). Per corpus: Earnings-21 2.1% to 2.0%, AMI 2.1% to 1.9%, VoxConverse 3.1% to 3.0%, SCOTUS 0.8% to 0.6%, DiPCo 2.6% to 2.4%. Aggregate DER is flat at 16.0%: the confusion gain is offset by missed speech rising from 6.6% to 6.8% — ASR coverage, not attribution — with false alarm unchanged at 7.5%.

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
- **Turn-level metrics**: a turn is consecutive same-speaker reference speech merged across gaps ≤ 1.0s (turns of 2s or more are scored); a turn counts as correctly attributed when the majority of the transcribed time in its span carries that speaker's (optimally mapped) label; "spoken over someone" means more than half the turn coincides with another speaker's reference speech
- **Live speaker metrics (2026-11-27)**: deterministic audio-clock replays use `--replay-live-labels` (first 10 min of AMI, full NOTSOFAR-1); real-time replays use `--replay-live-meeting` at `1×` serially on Apple M1 Max. Both run with default parameters and cold start (no voice profiles).
- **Diarization**: Pyannote Community-1 via [FluidAudio](https://github.com/FluidInference/FluidAudio) CoreML, with NVIDIA Nemotron 3 Diarization (FluidAudio CoreML, CPU)
- **ASR**: Post-stop 2026-09-29 runs used Parakeet TDT 0.6B v3; 2026-11-27 live speaker runs use the shipped Parakeet Ultra spoken-form fine-tune via FluidAudio CoreML.
- **LLM**: Gemini 3.1 Flash Lite (temp 0.1, thinking minimal)

## Reproducibility

The deterministic pipeline runs end-to-end in Swift; Python only does scoring (and, separately, the LLM step — which does not produce the published score). Post-stop 2026-09-29 runs were produced at `parakeet-transcriber` commits `db5059662` (without Nemotron) and `9677ee3be` (with Nemotron 3). The 2026-11-27 live speaker measurements were produced at commit `541309fd0` with default parameters.

```bash
# Post-stop deterministic diarization (57-file corpus)
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus
PYTHONPATH=benchmark/src benchmark/.venv313/bin/python3 -m mimicscribe_bench.runner

# Live speaker separation & labeling (single meeting example, default parameters)
.build/release/mimicscribe --replay-live-labels --raw-mic <silent.wav> --system <meeting.wav> --out-dir <out> --max-seconds 600
.build/release/mimicscribe --replay-live-meeting --raw-mic <silent.wav> --system <meeting.wav> --out-dir <out> --max-seconds 300
PYTHONPATH=benchmark/src benchmark/.venv313/bin/python3 benchmark/results/live-first/scripts/live_saa_score.py <arm_dir>
python3 benchmark/results/live-first/scripts/r1025/ab_score.py --until 570 SHIP=<meeting_dirs_csv>
python3 benchmark/results/live-first/scripts/break_latency.py --strict-sep --channel sys <meeting_dirs...>
```

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
| 2026-11-27 | 10 live | **97.3% live** | Live speaker separation & labeling update (`541309fd0`): cold-start 4-file overlap live SAA `94.7% → 96.5%`; 10-meeting cold-start `97.3%` live SAA (`9/10` exact speaker counts, `80.9%` right at `+10 s`); added quiet `1×` real-time turn-separation latency (`9.4 s` median after change, `6.0 s` after words appear) |

Aggregates are comparable only within the same file basis: 58 → 52 removed the Podcast corpus (May 2026); 52 → 57 added DiPCo (July 2026). On the shared 52-file basis, the 2026-07-17 and 2026-08-25 runs both score 98.2% and the 2026-08-29 run scores 98.3%.
