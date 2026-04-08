# Meeting Assistant Benchmark Results

Pipeline: Gemini 3 Flash (briefing) + Gemini 3.1 Flash Lite (action items) + Claude Sonnet (judge)

Run date: 2026-04-08 | 53 scenarios | 3 runs each

## Summary

| Metric | Value |
|--------|-------|
| Scenarios | 53 |
| Assertions passed | 204 / 221 (92%) |
| **Composite score** | **94.4%** |
| Avg latency | 1664ms |
| p50 / p95 / p99 latency | 1647ms / 2342ms / 2587ms |
| Stability (cross-run consistency) | 88% avg |
| Action items extracted | 160 (125 with due dates) |

## Hallucination

**12/12 passed (100%)** across all complex and long meeting scenarios.

Every name, number, date, product, and technical claim in the assistant's output is verified against the transcript, prepared context, meeting summary, and previous action items. Claude Sonnet evaluates each run independently.

Tested on enterprise sales negotiations with multi-product pricing, sprint planning with framework-specific jargon, board meetings with financial metrics, and 90-minute meetings with 8 speakers.

**Pass** (enterprise deal, hybrid deployment discussion):

```
- Confirm **Kafka** consumer group compatibility with webhook events.
- Ask about **dead-letter queue** retry window configuration.

---
- **Webhook** architecture supports arbitrary headers for correlation IDs.
- **Schema versioning** uses semver in the payload envelope.
- Retry logic includes **exponential backoff with jitter** (3 retries, 30s default).
```

Every term (Kafka, dead-letter queue, semver, 30s) appears in the transcript. No fabricated details.

**What a failure looks like** (not from this run -- illustrative):

```
- Ask about their **Datadog** integration requirements.
```

Flagged because "Datadog" was never mentioned in the transcript or context. The model inferred a monitoring tool from context clues but fabricated the specific product name.

## Forward-Looking Talking Points

**41/41 passed (100%)**

Talking points must propose what the user should say, ask, or do next. Recapping what was already discussed is a failure. The judge evaluates each bullet independently -- a single backward-looking bullet ("You mentioned the Q2 timeline") among forward-looking ones fails the assertion.

**Pass** (renewal call, pricing discussed):

```
- Confirm **annual billing** discount for **200 users**.
- Ask about their **timeline** for implementation.
```

Both bullets propose next actions. Neither restates what was said.

**Fail** (complex scenario, 33% pass rate):

```
- **Elliot** decided to cut **Constellation** from the sprint.
```

This restates a decision already made in the transcript rather than suggesting a next step. It should have been omitted or reframed as a follow-up (e.g., "Confirm Constellation cut with stakeholders").

## Goal Tracking

**17/19 passed (89%)** | 13 scenarios

When the user sets a meeting goal (e.g., "discuss budget and timeline"), the assistant must surface unaddressed goals as talking points. If a goal has been substantively discussed, no reminder should appear.

**Pass** (budget never discussed, 30-minute call):

```
- Ask about **budget** -- not yet discussed.
```

Budget was set as a goal but never came up. The assistant surfaces it.

**Fail** (both goals met, 67% pass rate):

```
- Ask about **budget** -- not yet discussed.
```

Budget was actually discussed with specific numbers in the transcript. The model missed the coverage and generated a false reminder.

## Action Items

**9/10 passed (90%)** | 4 non-incremental scenarios

Action items must trace to explicit verbal commitments ("I will", "I'll send"). Brainstorming ("we should", "we could") and casual suggestions must not produce items. Due dates must map to time references in the transcript.

**Pass** (mixed commitments and brainstorming):

```json
[
  {"owner": "you", "task": "Send diagnostic tool credentials and cert matrix", "due": "2026-04-10"},
  {"owner": "Remote", "task": "Run diagnostic tool across three customer environments"}
]
```

Both items correspond to explicit "I'll send" / "we will run" commitments. Brainstorming items ("We might want to do a webinar") correctly excluded.

**Fail** (due date grounding, 67% pass rate):

```json
{"task": "Send SOC 2 report to Sarah", "due": "2026-04-09"}
```

The transcript said "by end of day Thursday" but the resolved date didn't match the actual Thursday. The judge flagged the date as ungrounded.

## Incremental Action Items

**8/8 passed (100%)** | 5 scenarios

When the assistant is triggered multiple times during a meeting, previous action items are passed back in. The model must preserve them unless the transcript explicitly cancels, reassigns, or updates them. No duplicates allowed.

**Pass** (transcript cancels an item):

Previous items included "Coordinate joint webinar with partner marketing team." Transcript: "We're not going to do the joint webinar after all. Marketing decided to go a different direction."

```json
[
  {"owner": "you", "task": "Send integration documentation", "due": "2026-04-08"},
  {"owner": "Remote", "task": "Share test results from three customer environments", "due": "2026-04-13"}
]
```

Webinar item correctly removed. Other items preserved with original dates.

**Pass** (transcript updates a deadline):

Previous: "Send diagnostic credentials by Friday." Transcript: "I won't be able to get you the credentials by Friday... I should have it sorted by next Wednesday."

```json
{"owner": "you", "task": "Send diagnostic tool credentials and certification test matrix to Flux", "due": "2026-04-15"}
```

Deadline updated from Friday to Wednesday. No duplicate created alongside the old version.

## Question Detection

**15/16 passed (93%)** | 7 scenarios

Only questions from remote speakers are surfaced. Questions asked by the user (You/Mic) are excluded -- those are the user's own questions, not prompts they need to respond to. A question is considered answered if any subsequent speaker addresses it.

**Pass** (unanswered remote question):

Transcript ends with: `[Remote] What about failover? Do you have multi-region redundancy?`

```
❓ Do you have multi-region redundancy for failover?
```

Correctly surfaced -- asked by Remote, not yet answered.

**Pass** (user's own question, answered):

User asked: `[You/Mic] When do we expect a recommendation?`
Remote answered: `End of next week.`

No ❓ line in output. Correctly suppressed -- the user asked it, and it was answered.

**Fail** (remote deflects, 33% pass rate):

Remote says "Can we circle back on that?" -- a deflection, not a real answer. The model sometimes surfaces the user's preceding question instead of recognizing the deflection as the unanswered remote request.

## Interpersonal Awareness

**47/48 passed (98%)** | 12 scenarios

The assistant detects tension, defensiveness, and disengagement from transcript text and acoustic signals (overlap, speech rate, response latency). Equally important: it must NOT flag positive dynamics. Enthusiasm, collaborative overlaps, fast technical discussion, and natural turn-taking are not risks.

Acoustic signals are passed in a separate block (not inlined in the transcript) to prevent raw annotation terms from leaking into the output.

**Pass** (pricing pushback with fast speech):

Transcript shows a prospect speaking 30% faster than baseline while pushing back on a 15% price increase.

```
💬 The prospect is frustrated about the pricing increase; acknowledge their concern before presenting alternatives.
```

Correctly identified tension. No raw annotation data leaked ("fast+30%" does not appear).

**Pass** (enthusiastic agreement with overlaps):

Both speakers talking over each other excitedly about a partnership idea.

No 💬 line in output. Correctly suppressed -- overlapping speech during agreement is not an interpersonal risk.

**Fail** (natural turn overlaps, 0% pass rate):

Brief, polite overlaps at natural turn boundaries (e.g., "Yeah, the team's using it daily now --" / "Good to hear."). The model sometimes flags these as interpersonal dynamics when they're just conversational rhythm. This is the hardest edge case -- distinguishing polite overlap from aggressive interruption without full audio analysis.

## Long Meetings

**21/22 passed (95%)** | 5 scenarios

Simulates 90+ minute meetings using a compacted summary (~300 words), recent transcript window (~400 words), and accumulated previous action items. Tests that the assistant handles context from earlier in the meeting without re-suggesting decided topics or dropping aged-out action items.

Scenarios: 8-speaker company all-hands, enterprise deal negotiation, sprint planning, investor board update.

**Pass** (company all-hands, 8 speakers):

Meeting summary covers revenue update, hiring decisions, product roadmap, and NPS discussion. Recent transcript discusses engineering hiring details.

```
- Reach out to **Korn Ferry** and **Riviera Partners** this week for recruiting.
- Ask **Raj** if the infrastructure role could take a strong mid-level engineer.

---
- **Tyler** will deliver onboarding specialist JD by **Wednesday** (moved up from Friday).
- Engineering hiring requires **distributed systems** specialists, not general full-stack.
```

All names and details traced to transcript or summary. Previous action items preserved. No re-suggestion of already-decided topics.

## Complex Scenarios

**33/43 passed (76%)** | 7 scenarios

Long domain-specific transcripts with enterprise sales jargon, financial metrics, and multi-stakeholder dynamics. This is the weakest category -- the model occasionally exceeds the 3-bullet talking point limit and sometimes frames a recap as a talking point on complex multi-topic transcripts.

## Template Compliance

**13/13 passed (100%)** | 2 scenarios

Output follows the display template: question line before bullets, interpersonal before divider, summary after divider. Bold formatting on names and numbers. No markdown section headers.

## Methodology

- **53 scenarios**, 3 runs each (159 total runs)
- **Deterministic assertions**: string matching, bullet counts, template structure, annotation leakage detection
- **LLM judge**: Claude Sonnet evaluates semantic quality (hallucination, grounding, forward-looking, stability)
- **Composite scoring**: Critical assertions weighted 3x, Major 2x, Minor 1x
- **Stability**: measured by bullet count variance and keyword Jaccard similarity across runs

See the [benchmark README](../README.md) for full methodology and assertion type documentation.
