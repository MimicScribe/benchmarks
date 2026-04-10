# Context Retrieval Benchmark

Evaluates the reference document retrieval pipeline: how accurately MimicScribe surfaces the right information from user-provided reference documents during meetings, and how safely it handles edge cases like stale data, wrong-entity documents, and tangential content.

## What It Tests

Users can attach reference documents (CRM records, product docs, competitor briefs, financial reports, contracts) before or during a meeting. The pipeline chunks documents, embeds search phrases on-device, and retrieves relevant chunks in real time based on the live conversation.

The benchmark tests 26 scenarios across 15 document types with 77 assertions evaluated by Claude Sonnet as LLM judge. Scenarios include:

- **Positive cases**: sales calls, technical reviews, board meetings, investor updates, partner negotiations, interviews
- **Failure resilience**: stale data, wrong-entity documents, similar entity names, tangential content, no relevant context
- **Long meetings**: topic drift, resolved topics that shouldn't resurface, topics that come back after being parked
- **Number accuracy**: competing prices, overlapping deal sizes, similar percentages across different metrics
- **Multi-source**: multiple documents loaded simultaneously, only one relevant to the current discussion

All transcripts use realistic ASR-style text (lowercase, no punctuation) matching on-device speech-to-text output.

## Metrics

- **Recall@3 / Recall@5**: Does the correct reference material appear in the top results?
- **MRR** (Mean Reciprocal Rank): How high is the correct result ranked?
- **Number accuracy**: Are specific numbers (prices, dates, percentages) attributed to the correct entity?
- **Entity confusion**: Does the system keep facts from similar-named entities separate?
- **No hallucination**: Does the output avoid introducing fabricated facts?
- **End-to-end quality**: Does the AI assistant correctly use retrieved reference material without surfacing irrelevant content?

All e2e assertions are evaluated by Claude Sonnet as an LLM judge.

## Results

See [results/RESULTS.md](results/RESULTS.md) for the latest benchmark results.
