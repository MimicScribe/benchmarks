# Context Retrieval Benchmark Results

Pipeline: Gemini 3.1 Flash Lite (semantic chunking with search phrases) + potion-retrieval-32M (on-device embedding, 256-dim) + hybrid cosine similarity + IDF keyword boost

Run date: 2026-04-08

## Retrieval Accuracy

**91% of queries retrieved the correct reference material in the top 3 results** across 14 scenarios covering 8 document types. Retrieval latency is <1ms (on-device, zero network calls at query time).

| Metric | Score |
|--------|------:|
| Recall@3 | **91%** |
| MRR (mean reciprocal rank) | **87%** |
| Dirty vs clean gap | 2pp |
| Query latency | <1ms |

## By Document Type

| Document type | R@3 | MRR | Notes |
|---------------|----:|----:|-------|
| CRM with UI artifacts | 50% | 50% | HTML tags, buttons, pagination in source |
| Scraped webpage | 100% | 88% | Full HTML with nav, cookie banners, scripts |
| Messy meeting notes | 100% | 100% | Emoji, TODO markers, Slack threads, @mentions |
| PDF-extracted text | 100% | 100% | Broken line wraps, repeated page headers |
| Tracked changes | 100% | 88% | [DELETED], [INSERTED], [COMMENT] markup |
| Clean product docs | 100% | 100% | Structured markdown baseline |
| SEC 10-K filing | 100% | 100% | Dense cross-references, regulatory language |
| Wikipedia technical | 75% | 62% | Many subtopics with similar vocabulary |

CRM is the weakest scenario — generic chunk headers like "Deal Pipeline" don't match semantic queries like "What is the deal size?" Wikipedia is second weakest due to high vocabulary overlap across chunks. Both improve significantly with keyword boost enabled (+25pp on transcript scenarios).

## End-to-End Output Quality

Tested with Claude Sonnet as LLM judge on a realistic sales call scenario (CRM reference doc + live transcript).

| Assertion | Result | Weight |
|-----------|--------|--------|
| Reference attribution — facts stated accurately | PASS | Critical |
| No hallucination — no fabricated facts | PASS | Critical |
| Relevant context surfaced — key info in output | PASS | Major |

## How It Works

1. **Chunking** (ingest time, ~5s): Gemini splits the raw document into semantic chunks and generates 1-4 search phrases per chunk. Search phrases are written as natural questions a user might ask.

2. **Embedding** (ingest time, <10ms): Each search phrase is embedded on-device using potion-retrieval-32M (256-dim static model, sub-millisecond per embedding).

3. **Retrieval** (query time, <1ms): Query is embedded with the same model. Hybrid scoring combines cosine similarity with IDF-weighted keyword boost. Relevance gate prevents injecting unrelated content.

4. **Injection**: Retrieved chunks are formatted as reference context in the LLM prompt. The summarization prompt uses reference context only to enrich facts discussed in the transcript — not to introduce new topics.

## Benchmark vs Production

These results use clean benchmark queries ("What is the deal size?"). In production, queries come from meeting prep text, source titles, or transcript keyword extraction — which are noisier. The keyword boost compensates for this: on transcript-driven scenarios with keyword boost enabled, R@3 reaches 100%.

Reference documents in production may also contain more noise than the benchmark scenarios (which already include HTML, PDF artifacts, UI elements, and tracked changes markup). The Gemini chunking step handles this well — dirty vs clean gap is only 2pp.

## Noisy Document Handling

The pipeline processes real-world documents without manual cleanup:

- **HTML pages**: Gemini strips tags, navigation, cookie banners, scripts — preserves product info
- **CRM records**: UI buttons ([Edit] [Delete]), breadcrumbs, pagination removed
- **PDF extraction**: Broken hyphenation, repeated page headers, inline page numbers cleaned
- **Meeting notes**: Emoji, TODO markers, Slack thread quotes preserved as content
- **Tracked changes**: [DELETED]/[INSERTED]/[COMMENT] markup parsed, current state extracted
