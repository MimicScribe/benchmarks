# Meeting Assistant Benchmark

Evaluates the real-time meeting assistant briefing system in [MimicScribe](https://mimicscribe.app). The assistant generates talking points, action items, question detection, and interpersonal awareness suggestions during live meetings.

81 scenarios are run 3 times each against the production prompt. Each run is scored by a combination of deterministic assertions and LLM-as-judge (Claude Sonnet) semantic evaluation.

## Models

| Call | Model | Thinking | Purpose |
|------|-------|----------|---------|
| Briefing | Gemini 3 Flash | minimal | Talking points, summary, question detection, interpersonal |
| Action items | Gemini 3.1 Flash Lite | minimal | Structured JSON extraction |
| Judge | Claude Sonnet | — | LLM-as-judge for semantic assertions |

## What's Tested

### Hallucination Resistance (6 scenarios)

Targeted tests for specific hallucination failure modes: prepared context bleeding into output, number/date mutation in dense financial transcripts, speaker name fabrication for anonymous participants, cross-topic number confusion, sparse-context gap filling, and competitor references from context that aren't in the conversation.

### Discovery Quality (19 scenarios)

Tests the assistant's ability to help users understand the other party's situation before jumping to solutions. Covers:

- **Workaround detection**: When someone mentions a manual process or homegrown tool, the assistant suggests exploring what it costs and what's missing
- **Root cause probing**: When a prospect describes symptoms ("our reports are wrong"), the assistant suggests digging into why rather than accepting the symptom
- **Ideal-state questions**: After pain has been described in detail, the assistant suggests asking what the perfect solution would look like
- **BANT gap surfacing**: When budget, authority, timeline, or the compelling event haven't been discussed, the assistant raises them naturally
- **Context density tiers**: Tests that a single behavioral directive ("Help me understand their situation before suggesting solutions") produces good results even with zero additional context

Scenarios span sales discovery calls, customer success QBRs, user research sessions, and interviews.

### Goal & Commitment Tracking (19 scenarios)

Verifies the assistant surfaces unaddressed meeting goals as talking points. Tests partial coverage (timeline discussed but budget missing), full coverage (no false reminders), end-of-meeting resurfacing, and the transition from discovery to execution when requirements are gathered.

### Interpersonal Awareness (12 scenarios)

Tests detection of tension, defensiveness, and disengagement from transcript text and acoustic signals (overlap, speech rate, response latency). Equally important: verifies the assistant does NOT flag positive dynamics — enthusiasm, collaborative overlaps, fast technical discussion, and natural turn-taking are not interpersonal risks.

### Action Items (13 scenarios)

Tests extraction of explicit commitments with owner and due date. Verifies brainstorming and casual suggestions do not produce action items. Incremental scenarios test that previous action items are preserved, deadlines updated, and cancelled items removed across successive triggers.

### Question Detection (7 scenarios)

Only questions from remote speakers are surfaced. Questions asked by the user are excluded. A question is considered answered if any subsequent speaker addresses it.

### Complex & Long Meeting Scenarios (12 scenarios)

Long domain-specific transcripts with jargon across enterprise sales, sprint planning, board meetings, and QBRs. Long meeting scenarios (90+ minutes) use compacted summaries of earlier discussion plus a recent transcript window.

### Template Compliance (2 scenarios)

Verifies output follows the expected structural ordering.

## Scoring

**Composite score**: Weighted average across all assertions per scenario.

| Weight | Multiplier | Used for |
|--------|-----------|----------|
| Critical | 3x | Hallucination, action item stability |
| Major | 2x | Discovery quality, goal tracking, forward-looking, interpersonal accuracy |
| Minor | 1x | Template compliance, latency |

**Stability**: Structural consistency across 3 runs — bullet count variance and keyword overlap (Jaccard similarity).

## Assertion Types

### Deterministic

Exact checks that don't require judgment: string presence/absence, bullet counts, template structure ordering, annotation leakage detection, backward-looking phrase detection.

### LLM Judge (Claude Sonnet)

Semantic evaluation where interpretation is required:

| Rubric | What it evaluates |
|--------|-------------------|
| Hallucination | No fabricated names, numbers, dates, or claims beyond all provided context |
| Discovery Deepening | At least one suggestion helps the user dig deeper into the other party's situation |
| No Premature Solution | Suggestions focus on understanding, not pitching features before needs are clear |
| Requirements Surfaced | Unexplored BANT requirements are mentioned when gaps exist |
| No Summarization | Talking points propose forward actions, not recaps of what was said |
| Action Items Grounded | Every item traces to an explicit verbal commitment |
| Action Items Stable | Previous items preserved unless transcript supersedes; no duplicates |
| Question Detection | Only unanswered remote questions surfaced; user's own questions excluded |

## Results

See [results/RESULTS.md](results/RESULTS.md).
