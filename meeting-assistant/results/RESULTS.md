# Meeting Assistant Benchmark Results

Pipeline: Gemini 3 Flash (briefing) + Gemini 3.1 Flash Lite (action items) + Claude Sonnet (judge)

Run date: 2026-04-08 | 81 scenarios | 3 runs each

## Summary

| Category | Score | Scenarios |
|----------|-------|-----------|
| Hallucination resistance | 96% | 6 |
| Discovery quality | 98% | 19 |
| Goal & commitment tracking | 97% | 19 |
| Interpersonal awareness | 96% | 12 |
| Action items extraction | 98% | 9 |
| Question detection | 89% | 7 |

Average response time is under 1.7 seconds. Stability (cross-run consistency) averages 89%.

## Discovery: helping you ask better questions

The assistant doesn't just track what's been said — it helps you understand the other party's situation before jumping to solutions. Here's what that looks like in practice, using actual outputs from our test suite.

### Spotting workarounds

When someone mentions a manual process or homegrown tool, the assistant recognizes it as a signal that something is missing and suggests exploring it.

> Customer mentions exporting dashboard data to spreadsheets every Monday:
>
> - Ask what an ideal cross-product dashboard looks like.
> - Quantify the impact of **Marcus's** manual spreadsheet work.

> Prospect reveals their engineer spends 15 hours/week maintaining an internal sync tool that breaks every release:
>
> - Ask what happens if replacement isn't live in **two months**.
> - Explore **ML pipeline** impact if Yusuf's time is freed.

### Quantifying impact

Instead of accepting "it's broken" at face value, the assistant suggests questions that surface the business cost — something most people don't think to ask mid-conversation.

> Prospect says "our reports are always wrong":
>
> - Ask what's driving the **two-day** reconciliation delay.
> - Ask how much time **Finance** and **Ops** waste monthly.

### Ideal-state questions

When someone has described their problem in detail, the assistant suggests asking what the perfect solution would look like — opening up the conversation beyond incremental fixes.

> Customer describes 45-minute daily data reconciliation between two systems:
>
> - Ask what an **ideal automated solution** would look like.

> Beta tester says "the export is clunky":
>
> - Ask what an **ideal sharing workflow** looks like.

### Surfacing what hasn't been discussed

When key requirements like budget, decision-makers, or timeline haven't come up, the assistant raises them naturally.

> 20 minutes of technical discussion, budget and authority never mentioned:
>
> - Ask who else needs to approve the **Q4** budget.

### Interview depth

In interview settings, the assistant catches when candidates give surface-level answers and suggests specific follow-ups.

> Candidate proposes Redis with consistent hashing but doesn't address failure modes:
>
> - Ask how they would handle **hot keys** specifically.
> - Ask about **cache stampede** prevention for expired keys.

## Goal tracking: nothing falls through the cracks

When you set a specific objective for a meeting, the assistant tracks whether it's been substantively discussed — not just mentioned in passing. If time is running short and a key topic hasn't been covered, it moves to the top of the list.

The assistant distinguishes between topics that have been briefly named versus genuinely explored with specifics, numbers, or commitments.

## Works with minimal setup

You don't need to write detailed meeting prep for the assistant to be useful. In our tests, a single behavioral line like "Help me understand their situation before suggesting solutions" was enough to produce discovery-oriented suggestions — even with no names, companies, or background context provided.

Adding a name and company improves output polish. Adding deal context (budget status, prior conversations) enables more targeted suggestions. But the floor is high even with minimal input.

## Methodology

- **81 scenarios**, 3 runs each (243 total API calls)
- **Deterministic assertions**: string matching, bullet counts, template structure, annotation leakage detection
- **LLM judge**: Claude Sonnet evaluates semantic quality (hallucination, grounding, forward-looking, discovery depth)
- **Composite scoring**: Critical assertions weighted 3x, Major 2x, Minor 1x
- **Stability**: measured by bullet count variance and keyword Jaccard similarity across runs

See the [benchmark README](../README.md) for full assertion type documentation.
