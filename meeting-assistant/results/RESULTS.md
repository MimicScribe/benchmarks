# Meeting Assistant Benchmark Results

Pipeline: Gemini 3.1 Flash Lite (briefing, action items, live summary points) + Claude Sonnet (judge)

Run date: 2026-07-14 (discovery, forward-looking, execution, action-items subsets — 92 scenarios, 3 runs each) | earlier sections keep their dated numbers inline

> **Re-measurement — 2026-07-14.** The four largest subsets were re-run after two production changes: the entire pipeline moved from Gemini 3 Flash (a retired preview model) to Gemini 3.1 Flash Lite, and the long-meeting running summary was replaced by the assistant's live summary points (see "The running summary" below). Two honest headlines: average briefing latency roughly **halved** (~1.5s → ~0.85s), and composite scores are **5–7 points lower** than the Flash-3-era numbers — the cost of running on a smaller, faster, cheaper model. The suites also grew between runs (26 vs 22 discovery scenarios; the action-items suite expanded from 13 to 35 scenarios, adding harder list-persistence cases), so the deltas are not a pure model A/B. Sections not re-run keep their dated numbers.

## Summary

| Metric | Value |
|--------|-------|
| Discovery composite (26 scenarios × 3 runs, 2026-07-14) | **90%** (was 96% on Gemini 3 Flash, 22 scenarios) |
| Execution composite (28 scenarios × 3 runs, 2026-07-14) | **91%** (was 97% on Gemini 3 Flash) |
| Action-items composite (35 scenarios × 3 runs, 2026-07-14) | **90%** (suite expanded from 13 scenarios) |
| Forward-looking composite (3 scenarios × 3 runs, 2026-07-14) | 87% |
| Hallucination tag composite (2026-04-12, 5 runs) | 97% |
| Long-meetings tag composite (2026-04-12, 5 runs) | 96% |
| Avg latency — discovery / execution | **894ms / 844ms** (was 1,513ms / 1,520ms on Gemini 3 Flash) |
| p95 latency — discovery / execution | 1,131ms / 1,086ms |
| p99 latency — discovery / execution | 1,617ms / 1,498ms |
| Stability (cross-run consistency) | 78–85% avg by subset |

The model migration trade, in plain terms: MimicScribe's prompts are tuned to run on a flash-class model — that's what makes the latency, the cost, and the bring-your-own-endpoint story work. When the Gemini 3 Flash preview was retired, the pipeline consolidated on Gemini 3.1 Flash Lite rather than moving up to a larger model. Briefings now land in under a second on average, and the composite scores above are what that trade measures out to. We publish the lower numbers rather than leaving the retired model's numbers up.

## Prompt validation — what we tried and what stuck

This measurement cycle A/B-tested three candidate prompt additions. Principle: every instruction must justify its place — if it doesn't measurably improve quality, it's dropped to save tokens and latency.

| Candidate | Result | Decision |
|-----------|--------|----------|
| End-of-meeting summary "capture every substantive decision, commitment, number, named entity, deadline, unresolved question" (comprehensiveness) | template-summaries exact match 100% → 85% (-14.8pp), section recall 100% → 83.7%, usefulness 4.66 → 4.17, routing 0.849 → 0.759. summary-sections exact match 79.5% → 74.4%, routing 0.564 → 0.436. | **Dropped.** The instruction caused over-packing and misrouting. |
| End-of-meeting summary "separate sections with blank lines so RAG splits cleanly" (section formatting) | Measurement on 53 pre-change outputs: 100% already had blank-line separators without being told. Post-change: still 100%. | **Dropped.** Model already did it naturally. Instruction was dead weight. |
| Briefing `<PREVIOUS_BRIEFING>` softened from "preserve bullets verbatim, append new" to "emit summary if prior had one, focus on recent, replace superseded bullets" | Composite tied (-0.1pp both subsets). Latency p99 improved 730ms (discovery) / 268ms (execution). Shorter instruction → fewer tokens → faster. | **Kept.** No quality cost, latency win. |

## Hallucination (Targeted)

**6 scenarios** | **27/28 critical assertions pass on 5-run average** | **97% avg composite**

_(Last measured 2026-04-12 — numbers unchanged pending full-suite re-run.)_

| Scenario | Score | Latency | Stability |
|----------|-------|---------|-----------|
| :white_check_mark: Prepared context bleeding into summary | 91% | 1757ms | 85% |
| :white_check_mark: Number/date mutation in dense financial discussion | 100% | 1598ms | 88% |
| :white_check_mark: Speaker name fabrication (anonymous participants) | 100% | 1655ms | 86% |
| :white_check_mark: Similar numbers across topics (confusion risk) | 100% | 1443ms | 92% |
| :white_check_mark: Partial transcript with sparse context | 100% | 1488ms | 92% |
| :white_check_mark: Competitor in context but not in transcript | **100%** | 1849ms | 88% |

The "competitor in context" scenario — previously at 78% — is now at 100% after the briefing system instruction was strengthened with a dedicated rule: commitments from any source (summary or recent transcript) are locked, and talking points must not generate "confirm/remind/verify/check" prompts about them.

### Concrete examples — what the system gets right

**Competitor context scenario** — prepared context includes *"Competitor intel: They evaluated Otter.ai last quarter and rejected it for privacy reasons"*. The transcript is a technical discussion about on-device processing and data residency that never names Otter.ai.

Output (5/5 runs, after the fix):
> *- Ask if on-device processing resolves their previous privacy concerns.*
> *- Ask how the CFO views the current technical progress.*
> *- Confirm the timeline for the CISO security review.*

The model picks up the privacy thread from prepared context as a topic to pursue without surfacing the specific competitor name unprompted. It focuses on actionable follow-ups that align with what was discussed.

**Dense financial scenario** — prepared context includes a board-meeting summary with CAC ($28K blended, $42K enterprise), LTV ($380K enterprise, $95K mid-market), NRR (112%), gross margin (78%), runway (22 months at $18M cash). All 14 financial metrics appear in output across 5 runs without mutation — no `$28K` → `$30K`, no `$380K` → `$400K`, no runway conversion.

### Known weakness — rapport notes leaking as technical pitches

One pattern that fails 1/5 runs on the dedicated test scenario: rapport-building notes in prepared context occasionally surface as technical talking points.

**Prepared context:**
> *"Internal note: Laura was previously at Snowflake — use this to build rapport."*

**Transcript:** Technical discussion about hybrid deployment, encryption, data residency — no mention of Snowflake.

**Failing output (1/5 runs):**
> *- Mention your Snowflake integration to see if it fits her roadmap.*

The named entity (`Snowflake`) is from prepared context as intended, but the framing turns a rapport cue into a technical pitch — conflating Laura's prior employer with the user's product integration. 20% failure rate on this specific scenario type; general "context bleeding" without named rapport notes is at 100%.

## Discovery Quality

**26 scenarios** | **139/164 assertions** | **90% avg composite** | **894ms avg latency** _(re-measured 2026-07-14 on Gemini 3.1 Flash Lite)_

Tests whether the assistant helps users understand the other party's situation — root causes, ideal outcomes, impact quantification, and unexplored requirements — rather than jumping to solutions or surface-level suggestions.

_The per-scenario-type tables below are from the 2026-04-18 Gemini 3 Flash run and are kept for detail until the next full breakdown._

| Scenario Type | Count | Score | Avg Latency |
|---------------|-------|-------|-------------|
| Sales discovery (first calls, BANT gaps, workarounds, magic-wand) | 5 | 98% | 1744ms |
| Customer success (QBR expansion, workarounds, disengaged renewal) | 3 | 94% | 1523ms |
| Product / user research (vague feedback, unused features, manual processes) | 3 | 100% | 1535ms |
| Interviews (technical depth, behavioral probing, collaboration dodge) | 5 | 92% | 1785ms |
| Context density tiers (directive-only through rich context) | 3 | 99% | 1646ms |
| Discovery-to-execution transitions (BANT complete, partial gaps) | 2 | 96% | 1797ms |
| Edge: very early call, minimal transcript | 1 | 94% | 1305ms |

**Remaining weak spots:**

- [major] Interview depth — one technical-probe scenario at 78%. LLM judge is stricter on what counts as "probing deeper" than the underlying keyword assertions.
- [major] Compelling-event probing — one scenario at 91%. Model asked about ideal outcomes instead of what's driving the evaluation. Keyword assertion too narrow for valid alternative phrasings.
- [major] Disengaged-renewal detection — 83% on the customer-success renewal scenario when tension is text-only without acoustic signals.

### Interview Depth

**3 scenarios** | **19/20 assertions** | **98% avg composite**

Tests whether the assistant suggests follow-up questions that probe deeper into candidate responses — clarifying vague claims, testing technical depth, or digging into behavioral specifics.

| Scenario | Score | Key Behavior |
|----------|-------|-------------|
| :white_check_mark: System design — textbook answer, misses trade-offs | 100% | Probes exactly-once gap, data residency contradiction, suggests poison pill and backpressure |
| :white_check_mark: Behavioral — deflects on conflict, vague impact | 93% | Targets vague metrics ("ask for specific cycle time post-PIP") |
| :white_check_mark: Strong depth, dodges collaboration | 100% | Probes bypass-vs-delegation pattern, fires interpersonal on defensiveness |

### Context Density Tiers

Tests whether the minimal one-line template directive produces useful results without any additional context.

| Context Level | Composite | Notes |
|--------------|-----------|-------|
| Directive only (no name, no company) | 100% | Discovery-oriented talking points with zero user input |
| Directive + minimal context | 96% | Mostly solid; occasional minor gaps |
| Directive + rich context (role, status, gaps) | 100% | Budget/authority gaps surfaced from context |
| Execution directive only | 100% | Correctly shifted to commitment tracking mode |

### Notable Outputs

Actual model outputs from discovery scenarios (unedited):

**Workaround detection** — customer mentions exporting to spreadsheets:
> - Ask what an ideal cross-product dashboard looks like.
> - Quantify the impact of **Marcus's** manual spreadsheet work.

**Workaround detection** — prospect's engineer maintains a fragile internal tool:
> - Ask what happens if replacement isn't live in **two months**.
> - Explore **ML pipeline** impact if Yusuf's time is freed.

**Interview depth** — candidate gives high-level caching answer without failure modes:
> - Ask how to handle **poison pill** tasks that crash consumers.
> - Ask about **backpressure** mechanisms when downstream services are slow.
> - Ask for a deep dive into **exactly-once** failure modes.

**Interview depth** — candidate dodges collaboration, does everything solo:
> - Ask how they handle **technical disagreements** during RFC reviews.
> - Ask how they **mentor** others to handle cross-team work.
> - Ask for an example of **delegating** a critical path task.

## Execution Quality (Goal & Commitment Tracking)

**28 scenarios** | **151/185 assertions** | **91% avg composite** | **844ms avg latency** _(re-measured 2026-07-14 on Gemini 3.1 Flash Lite)_

Tests whether the assistant tracks stated goals, surfaces unaddressed items at wrap-up, and drives toward commitments in late-stage meetings.

_The per-scenario-type tables below are from the 2026-04-18 Gemini 3 Flash run and are kept for detail until the next full breakdown._

| Scenario Type | Count | Score | Avg Latency |
|---------------|-------|-------|-------------|
| Goal tracking (budget/timeline coverage, partial completion) | 3 | 100% | 1650ms |
| Wrap-up resurfacing (unaddressed goals at meeting end) | 5 | 100% | 1346ms |
| Complex domain-specific (sales, sprint, QBR, board, partner, attribution) | 6 | 93% | 2060ms |
| Execution-specific (closing, board decisions, standup) | 3 | 100% | 1447ms |
| Standup & blocker ownership (unowned, stalled, minimal) | 3 | 93% | 1697ms |
| Presentation coverage tracking | 4 | 98% | 1426ms |
| Discovery-to-execution transitions | 2 | 94% | 1669ms |
| Long meetings with compacted summary | 1 | 94% | 1570ms |
| Context tier (execution directive only) | 1 | 100% | 1274ms |

**Remaining weak spots:**

- [major] Complex scenarios with dense multi-threaded content — one API-integration partnership scenario at 82% (diagnostic-tool next-step surfaced in 3/5 runs).
- [major] Complex attribution dispute — 88%; Friday deadline occasionally not surfaced.
- [major] Minimal-standup scenario — 82%; model generates filler talking points when nothing needs flagging.
- [major] Presentation "all points covered" — 95%; model occasionally produces transitional bullets instead of minimal output.

### Standup & Blocker Ownership

**3 scenarios** | **~93% avg composite**

Tests detection of unowned blockers and stalled handoffs in standup meetings.

| Scenario | Score | Key Behavior |
|----------|-------|-------------|
| :white_check_mark: Multiple blockers — some owned, some not | 96% | Catches unowned blockers; bullet count mostly within limit |
| :white_check_mark: Stalled handoffs with false-positive non-blockers | 100% | Flags auth keys and PR review; correctly ignores non-blocker noise |
| :large_orange_diamond: Everything on track — minimal expected | 82% | Generates filler talking points when nothing needs flagging |

### Customer Workaround Detection

**3 scenarios** | **100% avg composite**

Tests detection of workarounds and unexpressed needs in customer calls.

| Scenario | Score | Key Behavior |
|----------|-------|-------------|
| :white_check_mark: Spreadsheet workaround normalized as "just how we do it" | 100% | "Ask what Mateo's ideal automated workflow looks like" — connects ETL bottleneck to stalled ML model and European expansion |
| :white_check_mark: Frustrated customer masking pain behind "it's fine" | 100% | Surfaces parallel routing need, Janelle's spreadsheet, compliance risk. Fires interpersonal on "stopped asking" frustration |
| :white_check_mark: Happy customer with buried dependency risk | 100% | Catches Raj single-point-of-failure, suggests exploring native connectors |

### Presentation Coverage Tracking

**4 scenarios** | **98% avg composite**

Tests whether the assistant tracks prepared key points and surfaces uncovered ones.

| Scenario | Score | Key Behavior |
|----------|-------|-------------|
| :white_check_mark: Mid-talk — 2 of 4 points covered | 100% | Surfaces briefing latency and SSO (uncovered); does NOT re-surface ASR or diarization (covered) |
| :white_check_mark: Audience Q&A mid-presentation | 100% | Fires question detection, surfaces SOC 2 and encryption keys (uncovered) |
| :large_orange_diamond: All points covered — minimal expected | 95% | Produces mostly transitional bullets; occasional filler |
| :white_check_mark: Dense financial metrics | 98% | Numbers perfectly preserved; surfaces runway and hiring (uncovered) |

### Wrap-up

**5 scenarios** | **100% avg composite**

| Scenario | Score | Key Behavior |
|----------|-------|-------------|
| :white_check_mark: Unaddressed budget (closing signals) | 100% | Budget surfaced as first bullet |
| :white_check_mark: Two goals unaddressed, meeting ending | 100% | CTO meeting and sign-off both surfaced |
| :white_check_mark: All goals met — no false resurfacing | 100% | No pricing reminder (confirmed); clean minimal output |
| :white_check_mark: Conditional agreement (pending CISO) | 100% | Security review blocker surfaced |
| :white_check_mark: Vague verbal yes without specifics | 100% | Finance approval and timeline gaps surfaced |

## Interpersonal Awareness

**12 scenarios** | **42/48 assertions** | **94% avg composite**

_(Last measured 2026-04-12 — numbers unchanged pending full-suite re-run.)_

| Scenario Type | Count | Score | Avg Latency | Stability |
|---------------|-------|-------|-------------|-----------|
| Tension detection with acoustic signals | 3 | 98% | 2023ms | 85% |
| Tension detection from text only | 1 | 90% | 1802ms | 78% |
| False positive suppression (enthusiasm, collaboration, technical speed) | 5 | 97% | 1662ms | 90% |
| Acoustic signal edge cases (disengagement, natural overlap) | 3 | 90% | 1826ms | 89% |

**Failures:**

- [0%] [major] Natural turn-boundary overlaps — model incorrectly flagged brief collaborative overlaps as interpersonal risk
- [67%] [major] Text-only disagreement — tension detected in 2/3 runs without acoustic signals (acceptable but inconsistent)

## Question Detection

**7 scenarios** | **17/19 assertions** | **89% avg composite**

_(Last measured 2026-04-12 — numbers unchanged pending full-suite re-run.)_

| Scenario Type | Count | Score | Avg Latency |
|---------------|-------|-------|-------------|
| Unanswered remote question | 1 | 100% | 1417ms |
| Answered by user or other remote | 3 | 100% | 1348ms |
| User's own questions (must not surface) | 2 | 100% | 1434ms |
| Rhetorical question | 1 | 100% | 1719ms |
| Deflection without answering | 1 | 25% | 1468ms |

**Failures:**

- [0%] [critical] Deflection scenario — remote speaker says "can we circle back on that?" which is a non-answer, but the LLM judge ruled it answered in 3/3 runs

## Action Items

**35 scenarios** | **81/95 assertions** | **90% avg composite** | **814ms avg latency** _(re-measured 2026-07-14 on Gemini 3.1 Flash Lite)_

The action-items suite nearly tripled since the last published run (13 → 35 scenarios). Beyond extraction — explicit commitments, due-date resolution, rejecting brainstorming and casual check-ins that contain no commitments — it now covers **list persistence across refreshes**: items on screen stay on screen unless explicitly closed, a reworded commitment updates the existing item in place instead of duplicating it, and completing one task must never close an unrelated one. It also covers media exclusion in both directions (no action items extracted from a video or podcast playing during the meeting, and real commitments still extracted while media plays).

Across the run: 236 action items extracted over 105 runs, 195 with resolved due dates.

**Known weakness:** on ambiguous present-intent phrasing ("I'm working on X now"), the model occasionally closes an item early when the surrounding discussion pivots. Because the list is persistent and re-evaluated each refresh, these recover on the next pass rather than vanishing.

## Timezone Resolution

**7 scenarios** | **18/18 assertions** | **100% avg composite**

_(Measured 2026-04-22 after the `dueTimezone` feature landed.)_

Action items carry a `dueTimezone` field (IANA identifier or null). It's resolved from location cues attached to the item's owner — either in USER_CONTEXT prep notes ("Marty is East Coast") or in the transcript itself ("our London office", "by 2 PM Eastern"). When no cue is present for the owner, the field stays null rather than being guessed.

| Scenario Type | Count | Score | Avg Latency | Stability |
|---------------|-------|-------|-------------|-----------|
| USER_CONTEXT cue → resolved zone | 1 | 100% | 1371ms | 82% |
| Transcript cue → resolved zone | 1 | 100% | 1471ms | 78% |
| No location cue → null (no spurious guess) | 1 | 100% | 1298ms | 82% |
| Mixed: owner-scoped zones, user null + remote resolved | 1 | 100% | 1274ms | 79% |
| Attribution: cue about non-committer must not spill over | 1 | 100% | 1437ms | 80% |
| Multi-zone: three speakers, three zones, each independent | 1 | 100% | 1315ms | 87% |
| Explicit zone in commitment speech (no inference needed) | 1 | 100% | 1246ms | 77% |

Display downstream renders the primary time in the user's local zone and appends the speaker's clock when zones differ — so a deadline spoken at "2 PM Eastern" by a coworker lands on the user's screen as `11:00 AM PDT · 2:00 PM EDT`.

## Long Meetings (90+ min)

**7 scenarios** | **29/32 assertions** | **96% avg composite**

_(Last measured 2026-04-12 — numbers unchanged pending full-suite re-run.)_

| Scenario Type | Count | Score | Avg Latency | Stability |
|---------------|-------|-------|-------------|-----------|
| Multi-speaker all-hands (8 speakers) | 1 | 93% | 1688ms | 86% |
| Enterprise deal negotiation | 1 | 100% | 1706ms | 88% |
| Sprint planning continuation | 2 | 93% | 1608ms | 85% |
| Investor board update | 1 | 100% | 1692ms | 87% |

### Date preservation — "two weeks" stays "two weeks"

A concrete improvement: when the meeting-so-far summary contains commitments like *"Martin can have the CAC dashboard ready in two weeks"*, the briefing model now preserves the relative phrasing rather than converting to an absolute date.

**Earlier behavior:**
> *"Martin to deliver manual CAC dashboard by **April 23**"*

The model computed April 23 from "two weeks" and today's date (with the wrong arithmetic — April 12 + 14 = April 26, not April 23). More fundamentally, the summary is supposed to reflect what was said, not what the model infers.

**Current behavior (all 5 runs on the investor-board scenario):**
> *"Martin to deliver manual CAC dashboard in **two weeks**"*

Calendar resolution is handled separately by the action-items extraction model, which outputs both a resolved ISO `due` date and a verbatim `dueDescription` ("in two weeks") — giving users the calendar-ready date for scheduling alongside the original phrasing they can quote back to the speaker.

**Remaining weakness:** 2 real hallucinations in 35 runs, both in the enterprise-deal scenario where action-item due dates were occasionally still computed as absolute dates (a pre-existing issue in the action-items extraction, not the briefing summary).

### The running summary — live summary points (updated 2026-07-14)

The background compaction step described in earlier versions of this page has been **removed**. Long-meeting briefings are now grounded in the assistant's **live summary points** — the short, self-contained notes the assistant already produces on screen during the meeting. The accumulated points are passed into each briefing call as the meeting-so-far summary, replacing the separate summarization pass entirely (one fewer recurring LLM call per meeting, and the briefing reasons over the same notes the user is reading).

Measured on the same three synthesized 80-minute marathon transcripts and the same judge used for the previous compaction numbers:

| Metric | Compaction (previous) | **Live summary points** |
|--------|:-:|:-:|
| Number coverage (avg across 3 scenarios) | 83% | **92% / 96%** (two runs) |
| Noun coverage (avg) | 72% | **74%** |

Points also handle reversals: when a decision changes mid-meeting, the stale point is retracted from the live view rather than left contradicting the new one — and the retracted point is kept (marked as superseded) so the post-meeting summary still knows the full history.

### Post-meeting summary coverage on long meetings (new — 2026-07-14)

Long-meeting summaries have traditionally had a **dwell-time bias**: topics discussed at length dominate, and something mentioned once and never revisited tends to silently vanish. Measured on a field-derived 77-minute advice call with 19 hand-labeled key points, the baseline summary covered **44%** of them. A structural coverage check added this cycle corrects for the bias — briefly-mentioned substance is caught and included rather than depending on model behavior alone:

| Configuration | Key-point coverage |
|---------------|:-:|
| Before (single-call summary) | 44% |
| With the coverage check | **~72%** (3 runs: 58–84%) |

Honest caveats: this is a single long-meeting case — the one that surfaced the problem in the field — not a corpus, and run-to-run variance is real (the range above). Closing the remaining gap is open work.

## Refresh Continuity (New — 2026-04-17)

A production change this month passes the prior briefing's markdown back into the next briefing call as `<PREVIOUS_BRIEFING>`. The model preserves the summary section's bullets verbatim while regenerating talking points and interpersonal observations fresh from the recent transcript.

Tested in an internal multi-turn exploration across 3 long-meeting scenarios (enterprise deal, sprint planning, investor board) with a judge scoring preservation, new-content incorporation, and hallucination against the prior summary:

| Metric | Baseline (no prior state) | With `<PREVIOUS_BRIEFING>` |
|--------|:-:|:-:|
| Summary preservation score (1-5) | 3.0 | **5.0** |
| Dropped bullets per refresh (avg) | 1.7 | **0** |
| Hallucinated facts (avg) | 1.7 | **0** |
| Talking-point freshness (bleed check) | N/A | **No bleed observed** |

The model correctly preserves summary bullets across refreshes while generating fresh talking points from the recent window. This addresses the prior "summary appears one refresh, gone the next" behavior.

## Template Compliance

**2 scenarios** | **12/13 assertions** | **99% avg composite**

_(Last measured 2026-04-12 — numbers unchanged pending full-suite re-run.)_

Output structure (question before bullets, interpersonal before divider, summary after divider), bold formatting, and bullet length limits all pass consistently.

## Known Weakness: Procedural Resurfacing at Meeting End

The most persistent failure mode across iterations: the briefing model occasionally suggests procedural "wrap-up" talking points that re-raise activities which just happened.

**Example** — sprint planning meeting that has visibly closed:

> *[You/Mic] Everyone good?*
> *[Remote] Good here.*
> *[Remote] Let's do it.*

**Failing output:**
> *- Ask if anyone has unresolved concerns before closing.*
> *- Confirm the meeting is adjourned.*
> *- Suggest a final review of the sprint board.*

All three bullets restate things the transcript just accomplished. The model defaults to "meeting-closing activities" as a safe output pattern even when those activities are visibly complete. This remains the dominant failure class in the 2026-07-14 re-measurement as well — most of the dropped assertion points in the discovery and action-items subsets trace to talking points that restate commitments already made instead of proposing a net-new angle.

**Where the model does well on specificity** — same scenario, different run, decisions still open:
> *- Ask how Alex's RFC should structure the caching invalidation strategy.*
> *- Confirm Nadia's written confirmation on promo code stacking tomorrow.*
> *- Ask Ravi about his plan for the Adyen webhook spike.*

Each bullet names specific people and topics from the source while adding a concrete angle rather than restating a commitment. Procedural-resurfacing is the fallback when the model cannot identify a net-new angle.

## Methodology

- The suite has grown to 130+ scenarios across all subsets. The 2026-07-14 re-measurement covered the 92 scenarios in the four largest subsets (discovery, forward-looking, execution, action items) at 3 runs each; smaller subsets keep their dated numbers.
- **Production config**: Gemini 3.1 Flash Lite, temperature 1.0 with minimal thinking for briefing; temperature 0.2 for action items. (Earlier published runs used the since-retired Gemini 3 Flash preview for briefing.)
- **Deterministic assertions**: string matching, bullet counts, template structure, annotation leakage detection
- **LLM judge**: Claude Sonnet evaluates semantic quality (hallucination, grounding, forward-looking, discovery depth, interview depth, blocker ownership, workaround detection, presentation coverage, requirements surfacing)
- **Composite scoring**: Critical assertions weighted 3x, Major 2x, Minor 1x
- **Stability**: measured by bullet count variance and keyword Jaccard similarity across runs

See the [benchmark README](../README.md) for full assertion type documentation.
