# Context Retrieval Benchmark

Evaluates the reference document retrieval pipeline: how accurately MimicScribe surfaces the right information from user-provided reference documents during meetings.

## What It Tests

Users can attach reference documents (CRM records, product docs, competitor briefs, financial reports) before or during a meeting. The pipeline chunks documents, embeds search phrases on-device, and retrieves relevant chunks in real time based on meeting content.

The benchmark tests retrieval accuracy across 14 scenarios covering 8 document types — including noisy real-world inputs like scraped web pages, PDF-extracted text, and CRM records with UI artifacts.

## Metrics

- **Recall@3**: Does the correct reference material appear in the top 3 retrieved results?
- **MRR** (Mean Reciprocal Rank): How high is the correct result ranked on average?
- **End-to-end quality**: Does the AI assistant correctly use the retrieved reference material? (Evaluated by Claude Sonnet as LLM judge)

## Results

See [results/RESULTS.md](results/RESULTS.md) for the latest benchmark results.
