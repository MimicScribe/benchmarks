# Meeting Assistant Benchmark Results

MimicScribe runs audio capture, transcription, diarization, speaker embeddings, and the on-device action-item trigger locally on your Mac. Text-based AI — live notes, action-item extraction, speaker naming, briefings, and saved summaries — runs on **Gemini 3.1 Flash Lite** by default, or on a sanctioned OpenAI-compatible endpoint or local model you choose.

This page consolidates **live** and **post-meeting** prompt quality across five sections (trigger & cadence, action items, speaker naming, saved AMI notes, and summaries/briefings). Every table below is generated from pinned run outputs and dated to the run that produced it.

## Summary

<!-- BEGIN GENERATED: summary -->
| Pillar | Headline Metric | Scope | Dated |
| --- | --- | --- | --- |
| On-device action-item trigger | **66.5%** caught ≤5 s (**4.68 ms** p50 ANE) | 39.3 h real meetings (421 items) | 2026-11-23 |
| Turn-edge live cadence | **95.7%** pauses / **86.8%** switches ≤10 s | 46 AMI test meetings (23.5 h) | 2026-11-23 |
| Action-item ownership (6 languages) | Live **90.4%** acc (23.3% unowned FP); Saved **90.9%** acc (15.6% unowned FP) | 48 sealed meetings (212 items, 157 decoys) | 2026-11-25 |
| Real meetings & MimicScribe ASR | **98.2%** real follow-ups, **78.7%** owner acc (0.0% hallucinated) | 40 real meetings (20.6 h: ICSI, NOTSOFAR-1 ASR, DiPCo ASR) | 2026-11-25 |
| Saved action items (AMI) | **92.2%** real follow-ups (**1.2%** hallucinated) | 71 AMI meetings (human transcripts) | 2026-10-12 |
| Saved summary coverage (AMI) | **91.1%** captured (**64.5%** in full) | 71 AMI meetings (human transcripts) | 2026-10-12 |
| Live items kept in saved list | **93%** (429/460) | 138 AMI meetings (human transcripts) | 2026-09-28 |
<!-- END GENERATED: summary -->

## Live Action-Item Trigger and Cadence

### On-device action-item trigger

A compact quantized multilingual transformer scores finished utterances on the Apple Neural Engine to detect commitments as they are spoken without waiting for the slower periodic refresh.

<!-- BEGIN GENERATED: action_trigger -->
| Metric | Value | Scope |
| --- | ---: | --- |
| Commitments caught within 5 s (overall) | **66.5%** | 39.3 h real meetings (421 items) |
| ICSI sealed real meetings (≤5 s) | **67.7%** | 15 meetings |
| AMI test real meetings (≤5 s) | **62.5%** | 46 meetings |
| Next-sentence echo share | **14.3%** | Real meetings |
| On-device ANE latency (p50 / p95) | **4.68 ms / 5.07 ms** | Release build, Apple Silicon |
<!-- END GENERATED: action_trigger -->

### Turn-edge refresh cadence and time-to-item

Live notes wait for natural sentence completions and turn edges rather than refreshing mid-sentence.

<!-- BEGIN GENERATED: cadence -->
| Corpus | Pauses ≤10 s | Switches ≤10 s | Refreshes / hr | Mid-sentence cuts | Action p50 / p90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMI test (46 mtgs, 23.5 h) | **95.7%** | **86.8%** | 210.8 | 3.4% | 7.7 s / 19.9 s |
| ICSI sealed (15 mtgs, 16.0 h) | **98.5%** | **90.9%** | 245.2 | 9.3% | — |
<!-- END GENERATED: cadence -->

## Action Items

Live action-item extraction, persistence across refreshes, and deduplication are tested across synthetic multi-turn scenarios (see scenario table below), real-meeting retention, and a sealed multilingual ownership holdout.

**Known weakness:** on ambiguous present-intent phrasing ("I'm working on X now"), the model occasionally closes an item early when the surrounding discussion pivots; because the list is persistent and re-evaluated on each refresh, these recover on the next pass rather than vanishing.

### Live items kept

<!-- BEGIN GENERATED: live_items_kept -->
Across 138 AMI meetings (reference transcripts, dated 2026-09-28), **93%** (429/460) of open live action items carried into the saved list, with 17/138 meetings losing at least one item.
<!-- END GENERATED: live_items_kept -->

### Action-item ownership and live tracking

Evaluated on a sealed holdout of 48 multilingual synthetic meetings across 6 languages (8 each in German, English, Spanish, French, Italian, and Portuguese; 212 planted commitments and 157 adversarial decoys including unanswered asks, group needs, refusals, relayed outsiders, and mid-call speaker-label evolution from bare remote labels to named speakers).

<!-- BEGIN GENERATED: owner_holdout -->
| Mode | Owner Acc (95% CI) | Owner Prec | Unowned FP | Wrong Speaker | Item Prec | Spec Recall | LLM p50 / p95 | Median Tokens (in / out) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Live (single-pass) | **94.5%** (90.7–97.6%) | 96.5% | 8.6% | 1.4% | 98.4% | 67.0% | 1562 / 2095 ms | 3,423 / 386 |
| Live (multi-refresh label evolution) | **90.4%** (87.0–93.8%) | 92.3% | 23.3% | 1.8% | 99.5% | 75.5% | 1380 / 1723 ms | 2,824 / 262 |
| Post-meeting saved | **90.9%** (86.7–94.8%) | 93.2% | 15.6% | 3.7% | 100.0% | 69.3% | 4841 / 6296 ms | 5,732 / 1,749 |

**By language (8 meetings each):**

| Language | Meetings | Saved Owner Acc | Saved Unowned FP | Live Multi-Refresh Owner Acc | Live Unowned FP |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 8 | **85.4%** | 10.0% | **91.7%** | 0.0% |
| German | 8 | **94.7%** | 14.3% | **92.5%** | 22.2% |
| Spanish | 8 | **87.5%** | 0.0% | **93.3%** | 14.3% |
| French | 8 | **90.6%** | 28.6% | **88.9%** | 37.5% |
| Italian | 8 | **86.2%** | 50.0% | **90.6%** | 14.3% |
| Portuguese | 8 | **100.0%** | 0.0% | **85.7%** | 50.0% |

**Transcript jump-link coverage:** 100.0% (197/197) of saved action items carry valid in-range line citations.

**Live-to-saved owner consistency:** 81.8% (108/132 matched items kept the same owner from live panel to saved summary; 83.3% verified correct on both sides).

*Sealed holdout: 48 meetings, 6 languages, model `gemini-3.1-flash-lite`, commit `23e50cb0e`, dated 2026-11-25.*
<!-- END GENERATED: owner_holdout -->

### Timezone Resolution

Timezone resolution is tested across multi-timezone scheduling scenarios where deadlines are resolved from location cues attached to the item's owner without guessing when no location is named. See the scenario table below for the pinned score.

## Speaker Naming and Attribution Safety

Post-meeting speaker naming binds diarized voices to spoken names only on direct evidence (self-identification, addressed-and-present replies, or unambiguous attribution), leaving unidentifiable voices unnamed rather than guessing.

<!-- BEGIN GENERATED: speaker_naming -->
| Check | Result | Dated | Notes |
| --- | ---: | --- | --- |
| Post-meeting speaker naming (6 languages, 48 sealed meetings) | **83.2%** precision (84/101 named) | 2026-11-25 | 41.8% of all voice clusters named; unnamed voices safely left as speaker labels. |
| System-channel ASR-grafted name resistance | **0/4 clean** | 2026-08-23 | System-channel ASR-grafted names remain an open failure mode under the post-meeting prompt (0/4 clean); tracked as a regression ratchet. |
<!-- END GENERATED: speaker_naming -->

## Saved Notes on Real Meetings (AMI)

Evaluated on meetings from the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/) using AMI's human reference transcripts and human-written summaries, decisions, problems, and action-item lists. Transcription and speaker errors are outside these numbers.

### Action items

<!-- BEGIN GENERATED: ami_action_items -->
| Metric | Value | Counts | Dated |
| --- | ---: | ---: | --- |
| Saved action items that are real follow-ups | **92.2%** | 224/243 | 2026-10-12 |
| Hallucinated or distorted items | **1.2%** | 3/243 | 2026-10-12 |
| In transcript but not follow-up work | **6.6%** | — | 2026-10-12 |
| Human-noted action-item recall | **75.3%** | 131/174 | 2026-10-12 |
<!-- END GENERATED: ami_action_items -->

### Summary coverage

<!-- BEGIN GENERATED: ami_summary_coverage -->
| Metric | Value | 95% CI | Dated |
| --- | ---: | ---: | --- |
| Human summary points captured (at least in part) | **91.1%** | 88.7–93.5% | 2026-10-12 |
| Human summary points captured in full | **64.5%** | 60.4–68.9% | 2026-10-12 |

**Known weakness — tentative ideas written as settled:** 5.8% of summary bullets (47/813) state something the transcript does not fully support.
<!-- END GENERATED: ami_summary_coverage -->

### Panel open or closed

When the live notes panel is closed during an online meeting, a low-frequency background pass runs every three minutes (compared with about every half minute in the 2026-10-12 AMI replay), so saved notes still start from live points.

<!-- BEGIN GENERATED: ami_panel_open_closed -->
| Metric | Panel open | Panel closed |
| --- | ---: | ---: |
| Points captured in full | 64.5% | 62.4% |
| Points captured at least in part | 91.1% | 88.3% |
| Human-listed action items carried | 75.3% | 66.1% |
| Saved action items that are real follow-ups | 92.2% | 94.7% |
| Summary bullets not supported | 5.8% | 6.9% |

The differences stay within the meeting-level confidence intervals.
<!-- END GENERATED: ami_panel_open_closed -->

### Limits

- One run on 71 AMI meetings (69 role-played product-design meetings, all English, four participants).
- Input is AMI's human reference transcript; real recordings add transcription and speaker errors on top of these numbers.
- One Claude Haiku judge model, spot-checked by reading rather than scored against human judgments.
- Owners are not scored on the AMI corpus because the transcripts use numbered speaker labels while the human notes use roles; ownership is measured separately in the multilingual holdout above and on real meetings below.

### Real meetings and real ASR (ICSI, NOTSOFAR-1, DiPCo)

To measure action-item precision, ownership, citation grounding, and false-positive control beyond role-played human transcripts, we also evaluate post-meeting notes on real non-role-played academic meetings (ICSI) and end-to-end MimicScribe ASR + diarization outputs on workplace meetings (NOTSOFAR-1) and overlapping casual dinner-party chat (DiPCo).

<!-- BEGIN GENERATED: real_meetings_asr -->
| Corpus | Transcript | Meetings (Hours) | Real Follow-ups | Hallucinated | Owner Acc | Unowned FP | Citations Valid | LLM p50 / p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ICSI (real academic meetings) | Human reference | 15 (15.9 h) | **98.3%** (59/60) | 0.0% | **84.8%** | 5.3% | 100.0% | 6233 / 8133 ms |
| NOTSOFAR-1 (workplace meetings) | MimicScribe ASR + diarization | 20 (2.0 h) | **98.0%** (49/50) | 0.0% | **71.4%** | 23.1% | 100.0% | 4021 / 4697 ms |
| DiPCo (casual dinner chat, negative control) | MimicScribe ASR + diarization | 5 (2.6 h) | **0 FP** (0 extracted) | 0.0% | **—** | — | — | 4673 / 5784 ms |

*Casual-conversation negative control (DiPCo): 0.0 extracted items/meeting (0.0 items/hr across 2.6 h of overlapping dinner chat; 0 non-follow-up false positives).* 

*Real-meeting evaluation: 40 meetings (20.6 h), model `gemini-3.1-flash-lite`, commit `9485570b8`, dated 2026-11-25.*
<!-- END GENERATED: real_meetings_asr -->

## Summaries, Corrections, and Live Briefings

### Adaptive summary structure and faithfulness

Summary structure adapts to the recording rather than forcing fixed business headings onto lectures, interviews, or panels. Action items stay in their dedicated list rather than being restated in prose.

### Summary preservation after user corrections

When a user edits a transcript or renames a speaker, revised summaries keep the existing section headings and order unless restructuring is explicitly requested, while retagging action-item owners in lockstep with the speaker roster.

### Live Briefings and In-Meeting Q&A

<!-- BEGIN GENERATED: live_scenarios -->
| Category | Score | Scenarios | Dated |
| --- | ---: | ---: | --- |
| Hallucination resistance | **97%** | 6 | 2026-04-12 |
| Discovery quality | **90%** | 26 | 2026-07-14 |
| Commitment & requirements tracking | **91%** | 28 | 2026-07-14 |
| Interpersonal awareness | **94%** | 12 | 2026-04-12 |
| Action items extraction | **90%** | 35 | 2026-07-14 |
| Timezone resolution | **100%** | 7 | 2026-04-22 |
| Question detection | **89%** | 7 | 2026-04-12 |
| Long-meeting quality (90+ min) | **96%** | 7 | 2026-04-12 |

*Action-items & attribution scenarios are scheduled for re-run on the updated prompts.*
<!-- END GENERATED: live_scenarios -->

#### Hallucination (Targeted)

Targeted hallucination-resistance scenarios verifying that the live assistant refuses to invent figures, names, or commitments absent from the transcript.

#### Discovery Quality

Discovery scenarios measuring whether live questions uncover concrete workflow gaps and impact rather than restating what was already said.

#### Execution Quality (Goal & Commitment Tracking)

Goal and commitment tracking scenarios measuring whether unaddressed objectives stay surfaced across turns.

#### Interpersonal Awareness

Interpersonal dynamics scenarios balancing tension detection against false-positive suppression on enthusiastic or fast-paced collaboration.

#### Question Detection

Question-detection scenarios testing whether unanswered remote questions surface while rhetorical or already-answered questions stay quiet.

#### Long Meetings (90+ min)

Long-meeting continuity scenarios testing compaction and state retention across 90+ minute transcripts.

#### Template Compliance

Structural compliance with user-editable display templates.

## Methodology and Reproducibility

- **Models:** Text-AI benchmarks use Gemini 3.1 Flash Lite (minimal thinking for live notes, live briefings, and post-meeting summaries; low thinking for live Q&A). On-device trigger latency is measured in release builds on Apple Silicon ANE.
- **Judging:** Deterministic checks verify schema structure, grounding, citation ranges, speaker-label mapping, and live backfill bounds. Semantic scoring uses blind LLM judges (Claude Haiku for AMI saved notes, the multilingual ownership holdout, and the real-meeting ASR suite, spot-checked by reading; Claude Sonnet for the scenario suite; Gemini 3.1 Flash Lite for live-items-kept retention).
- **No stale mixing:** Every table row is dated to the run that produced it; any pillar whose underlying prompt or pipeline changed since its last run is explicitly marked **regenerating** or dated to its prior run until re-measured on the shipping build.
