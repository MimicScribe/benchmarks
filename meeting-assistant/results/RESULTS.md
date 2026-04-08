# Meeting Assistant Benchmark Results

Pipeline: Gemini 3 Flash (briefing) + Gemini 3.1 Flash Lite (action items) + Claude Sonnet (judge)

Run date: 2026-04-08 | 59 scenarios | 3 runs each

## Summary

| Metric | Value |
|--------|-------|
| Scenarios | 59 |
| Assertions passed | 222 / 248 (89%) |
| **Composite score** | **94.0%** |
| Avg latency | 1671ms |
| p50 / p95 / p99 latency | 1642ms / 2253ms / 3248ms |
| Stability (cross-run consistency) | 88% avg |
| Action items extracted | 161 (127 with due dates) |

## Hallucination (Targeted)

**6 scenarios** | **25/27 assertions** | **96% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Hallucination: prepared context bleeding into summary (enterprise deal) | 100% | 6/6 | 1707ms | 97% |
| :white_check_mark: Hallucination: number/date mutation in dense financial discussion | 100% | 4/4 | 1608ms | 88% |
| :white_check_mark: Hallucination: speaker name fabrication (anonymous remote participants) | 100% | 5/5 | 1695ms | 86% |
| :white_check_mark: Hallucination: similar numbers across topics (confusion risk) | 100% | 4/4 | 1426ms | 92% |
| :white_check_mark: Hallucination: partial transcript with sparse context (early meeting) | 100% | 4/4 | 1504ms | 92% |
| :large_orange_diamond: Hallucination: context mentions competitor but transcript doesn't | 78% | 2/4 | 1882ms | 86% |

**Failures:**

- [67%] [critical] Hallucination: context mentions competitor but transcript doesn't -- No hallucination (LLM judge)
- [67%] [critical] Hallucination: context mentions competitor but transcript doesn't -- No fabricated names (LLM judge)

## Goal Tracking & Forward-Looking

**9 scenarios** | **42/44 assertions** | **96% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Goal: budget never discussed (30-min call) | 100% | 4/4 | 1656ms | 93% |
| :white_check_mark: Goal: both budget and timeline covered | 100% | 5/5 | 1857ms | 88% |
| :white_check_mark: Goal: timeline discussed, budget missing (mid-call) | 100% | 4/4 | 1633ms | 97% |
| :large_orange_diamond: Forward-looking: don't parrot recent exchange | 78% | 4/5 | 1508ms | 83% |
| :white_check_mark: Forward-looking: suggest what hasn't been covered | 100% | 4/4 | 1557ms | 89% |
| :white_check_mark: Wrap-up: unaddressed budget goal with closing signals (should be first bullet) | 100% | 5/5 | 1546ms | 91% |
| :white_check_mark: Wrap-up: two goals unaddressed, meeting ending abruptly | 100% | 5/5 | 1318ms | 83% |
| :large_orange_diamond: Wrap-up: all goals met, no false resurfacing | 90% | 3/4 | 1472ms | 92% |
| :white_check_mark: Long meeting: compacted summary + recent window, quality stable | 100% | 8/8 | 1868ms | 90% |

**Failures:**

- [0%] [major] Forward-looking: don't parrot recent exchange -- No parroting 'native connectors' in talking points
- [67%] [major] Wrap-up: all goals met, no false resurfacing -- No pricing reminder (already confirmed)

## Interpersonal Awareness

**12 scenarios** | **44/48 assertions** | **96% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Interpersonal: overlap during disagreement (annotated) | 100% | 5/5 | 2020ms | 88% |
| :white_check_mark: Interpersonal: overlap during disagreement (baseline, no annotations) | 100% | 3/3 | 1845ms | 98% |
| :white_check_mark: Interpersonal: fast speech during pricing pushback (annotated) | 100% | 4/4 | 1803ms | 95% |
| :white_check_mark: Interpersonal: combined overlap + fast during heated exchange (annotated) | 95% | 3/4 | 2245ms | 73% |
| :white_check_mark: Interpersonal: neutral conversation, no annotations | 100% | 3/3 | 1580ms | 88% |
| :white_check_mark: Interpersonal: overlap during enthusiastic agreement | 100% | 4/4 | 1342ms | 92% |
| :white_check_mark: Edge: passive agreement with tension acoustic signals | 100% | 4/4 | 1780ms | 87% |
| :white_check_mark: Edge: fast technical explanation — no tension (false positive risk) | 95% | 3/4 | 2640ms | 91% |
| :white_check_mark: Edge: excited fast speech on good news — no negative signal | 100% | 5/5 | 1923ms | 91% |
| :large_orange_diamond: Edge: brief overlap at natural turn boundaries | 71% | 3/4 | 1547ms | 89% |
| :white_check_mark: Edge: pervasive overlaps in collaborative working session | 100% | 4/4 | 1750ms | 88% |
| :large_orange_diamond: Edge: text-only disagreement without acoustic signals (regression test) | 90% | 3/4 | 1802ms | 78% |

**Failures:**

- [0%] [major] Edge: brief overlap at natural turn boundaries -- No interpersonal flag for natural turn overlaps
- [67%] [minor] Interpersonal: combined overlap + fast during heated exchange (annotated) -- Latency <= 3000ms
- [67%] [minor] Edge: fast technical explanation — no tension (false positive risk) -- Latency <= 3000ms
- [67%] [major] Edge: text-only disagreement without acoustic signals (regression test) -- Detects pushback from text alone (no acoustic annotations)

## Complex Scenarios

**7 scenarios** | **31/43 assertions** | **85% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Complex: enterprise data observability deal, multi-product with competitor eval | 100% | 6/6 | 2202ms | 90% |
| :large_orange_diamond: Complex: sprint planning with internal tools, feature scoping, and infra migration | 76% | 4/6 | 1895ms | 86% |
| :white_check_mark: Complex: hiring committee debrief with rubric scores and bar-raiser veto | 100% | 5/5 | 2066ms | 81% |
| :large_orange_diamond: Complex: QBR with product issues, trust erosion, and gated expansion | 74% | 4/7 | 1973ms | 76% |
| :large_orange_diamond: Complex: API integration partnership with hybrid deployment constraints | 82% | 4/6 | 1900ms | 86% |
| :large_orange_diamond: Complex: Series B board prep with CFO, bridge round debate, margin tension | 82% | 3/6 | 2049ms | 78% |
| :large_orange_diamond: Complex: attribution dispute, channel budget allocation with competing data | 79% | 5/7 | 1966ms | 87% |

**Failures:**

- [0%] [major] Complex: sprint planning with internal tools, feature scoping, and infra migration -- No summarization as talking points (LLM judge)
- [0%] [major] Complex: attribution dispute, channel budget allocation with competing data -- Surfaces Sam's model by Friday (next step)
- [33%] [major] Complex: QBR with product issues, trust erosion, and gated expansion -- No hallucination (LLM judge)
- [33%] [major] Complex: QBR with product issues, trust erosion, and gated expansion -- No summarization as talking points (LLM judge)
- [33%] [major] Complex: API integration partnership with hybrid deployment constraints -- Surfaces diagnostic tool action (next step)
- [67%] [major] Complex: sprint planning with internal tools, feature scoping, and infra migration -- Surfaces Elliot communication (decided to cut Constellation)
- [67%] [major] Complex: QBR with product issues, trust erosion, and gated expansion -- Surfaces SSO cert action item (Janet)
- [67%] [major] Complex: API integration partnership with hybrid deployment constraints -- No summarization as talking points (LLM judge)
- [67%] [major] Complex: Series B board prep with CFO, bridge round debate, margin tension -- Max 3 talking points
- [67%] [major] Complex: Series B board prep with CFO, bridge round debate, margin tension -- No hallucination of financial details (LLM judge)
- [67%] [major] Complex: Series B board prep with CFO, bridge round debate, margin tension -- No summarization as talking points (LLM judge)
- [67%] [major] Complex: attribution dispute, channel budget allocation with competing data -- No summarization as talking points (LLM judge)

## Question Detection

**7 scenarios** | **18/19 assertions** | **89% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Question: unanswered Remote question at end of transcript | 100% | 3/3 | 1417ms | 89% |
| :white_check_mark: Question: Remote question answered by user — should not surface | 100% | 3/3 | 1291ms | 91% |
| :white_check_mark: Question: Remote question answered by another Remote — should not surface | 100% | 3/3 | 1352ms | 78% |
| :white_check_mark: Question: user asks question, gets answer — must NOT surface | 100% | 2/2 | 1401ms | 89% |
| :white_check_mark: Question: user asks multiple questions, all answered — no question surfaced | 100% | 3/3 | 1467ms | 91% |
| :x: Question: Remote deflects without answering — question should surface | 25% | 1/2 | 1468ms | 90% |
| :white_check_mark: Question: rhetorical Remote question — should not surface | 100% | 3/3 | 1719ms | 85% |

**Failures:**

- [0%] [critical] Question: Remote deflects without answering — question should surface -- Question detection correct (LLM judge)

## Action Items

**4 scenarios** | **13/14 assertions** | **97% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :large_orange_diamond: Action items: explicit commitments with due dates (sales call) | 89% | 3/4 | 1653ms | 89% |
| :white_check_mark: Action items: brainstorming should NOT produce items | 100% | 3/3 | 1425ms | 83% |
| :white_check_mark: Action items: mixed commitments and vague plans (should extract only commitments) | 100% | 4/4 | 1580ms | 87% |
| :white_check_mark: Action items: no commitments in casual check-in (should return empty) | 100% | 3/3 | 1330ms | 89% |

**Failures:**

- [67%] [critical] Action items: explicit commitments with due dates (sales call) -- Due dates grounded in transcript (LLM judge)

## Incremental Action Items

**5 scenarios** | **10/11 assertions** | **99% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Action items: incremental — previous items preserved with new transcript | 100% | 2/2 | 1415ms | 87% |
| :white_check_mark: Action items: incremental — transcript updates deadline on existing item | 95% | 2/3 | 2051ms | 88% |
| :white_check_mark: Action items: incremental — unrelated new transcript, all previous items preserved | 100% | 2/2 | 1146ms | 80% |
| :white_check_mark: Action items: incremental with compacted summary — aged-out items retained | 100% | 2/2 | 1515ms | 94% |
| :white_check_mark: Action items: incremental — transcript cancels a previous item | 100% | 2/2 | 1526ms | 87% |

**Failures:**

- [67%] [minor] Action items: incremental — transcript updates deadline on existing item -- Latency <= 3000ms

## Long Meetings (90+ min)

**4 scenarios** | **14/16 assertions** | **94% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :large_orange_diamond: Long: company all-hands (8 speakers, 90 min) | 89% | 3/4 | 1702ms | 93% |
| :white_check_mark: Long: enterprise deal negotiation (90 min, 3 speakers) | 100% | 4/4 | 1684ms | 87% |
| :white_check_mark: Long: product sprint planning (90 min, eng team) | 100% | 4/4 | 1632ms | 87% |
| :large_orange_diamond: Long: investor board update with CFO tension (90 min) | 89% | 3/4 | 1744ms | 85% |

**Failures:**

- [67%] [critical] Long: company all-hands (8 speakers, 90 min) -- No hallucination (LLM judge)
- [67%] [critical] Long: investor board update with CFO tension (90 min) -- No hallucination (LLM judge)

## Long Meetings

**1 scenarios** | **5/6 assertions** | **88% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :large_orange_diamond: Long meeting: earlier decisions in summary should not be re-suggested | 88% | 5/6 | 1528ms | 83% |

**Failures:**

- [33%] [major] Long meeting: earlier decisions in summary should not be re-suggested -- Does NOT re-suggest Lighthouse P0 (already decided)

## Template Compliance

**2 scenarios** | **13/13 assertions** | **100% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Template: question detected, full structure expected | 100% | 6/6 | 1861ms | 97% |
| :white_check_mark: Template: no question, no interpersonal — minimal structure | 100% | 7/7 | 1565ms | 89% |

## Other

**2 scenarios** | **7/7 assertions** | **100% avg composite**

| Scenario | Score | Assertions | Latency | Stability |
|----------|-------|------------|---------|-----------|
| :white_check_mark: Edge: very early call, minimal transcript | 100% | 4/4 | 1138ms | 98% |
| :white_check_mark: Edge: no prepared context | 100% | 3/3 | 1421ms | 84% |

## Methodology

- **59 scenarios**, 3 runs each (177 total runs)
- **Deterministic assertions**: string matching, bullet counts, template structure, annotation leakage detection
- **LLM judge**: Claude Sonnet evaluates semantic quality (hallucination, grounding, forward-looking, stability)
- **Composite scoring**: Critical assertions weighted 3x, Major 2x, Minor 1x
- **Stability**: measured by bullet count variance and keyword Jaccard similarity across runs

See the [benchmark README](../README.md) for full methodology and assertion type documentation.
