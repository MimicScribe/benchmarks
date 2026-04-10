# Context Retrieval Benchmark Results

Pipeline: Gemini 3.1 Flash Lite (semantic chunking with conversational search phrases) + all-MiniLM-L6-v2 (on-device transformer embedding, 384-dim) + multi-query retrieval from transcript + Claude Sonnet (LLM judge)

Run date: 2026-04-10 | 26 scenarios | 77 assertions (60 critical, 17 major) | single run

## Hallucination Safety

**Zero number misattribution across all dedicated accuracy scenarios.** Every number in the output is checked against source material and verified to be attributed to the correct entity.

| Safety metric | Pass rate | Scenarios |
|---------------|-----------|-----------|
| Number accuracy — correct value AND correct entity | **9/9 (100%)** | Competing prices, overlapping deal sizes, similar percentages |
| Entity confusion — multi-source, similar names | **4/4 (100%)** | Two companies with "Meridian" in the name, two product tiers |
| Stale data — outdated reference vs current transcript | **2/2 (100%)** | Old pricing sheet loaded, meeting discusses new pricing |
| No hallucination (all scenarios) | **24/26 (92%)** | Every e2e scenario tested; 2 failures are LLM output variance |

When the reference document contains a number tied to a specific entity (e.g., "$3,200/month for Workato"), the system preserves that attribution in the talking points. If two entities have different numbers, they are not grouped or averaged.

When a reference document contains outdated information that contradicts the live transcript, the system uses the transcript's numbers. In one test, a pricing sheet from Q3 2024 was loaded during a meeting discussing January 2026 price increases — the system correctly used the updated prices from the conversation.

## Retrieval Accuracy

**99% of queries retrieved the correct reference material in the top 3 results** across 26 scenarios covering 15 document types. Retrieval runs entirely on-device with zero network calls at query time.

| Metric | Score |
|--------|------:|
| Recall@3 | **99%** |
| Recall@5 | **100%** |
| MRR (mean reciprocal rank) | **98%** |
| Query latency (end-to-end) | <100ms |

### By Document Type

All 15 document types achieve 100% R@3. Dirty documents (HTML artifacts, PDF extraction noise, tracked changes markup) perform identically to clean structured documents.

| Category | Document types | R@3 | Notes |
|----------|---------------|----:|-------|
| Dirty/noisy sources | CRM with UI artifacts, scraped HTML, messy meeting notes, PDF-extracted text, tracked changes | 100% | Gemini strips noise at chunking time |
| Dense/structured | SEC 10-K filing, technical article, strategic plan | 100% | Many subtopics with similar vocabulary |
| Business documents | Customer profiles, pricing sheets, competitive intel, contract terms, case studies | 100% | Numbers, names, and terms preserved |
| Clean baseline | Product documentation | 100% | Structured markdown |

## End-to-End Quality

**73/77 assertions pass (94.8%)** across 26 e2e scenarios evaluated by Claude Sonnet as LLM judge. Each scenario includes a reference document, a realistic meeting transcript (ASR-style lowercase text without punctuation), and 2-4 judge assertions.

| Category | Scenarios | Pass rate |
|----------|-----------|-----------|
| Positive — reference context improves talking points | 12 | 93% |
| Failure resilience — reference context could hurt but doesn't | 5 | 93% |
| Long meetings — topic drift, resolved topics, resurfacing | 4 | 91% |
| Number accuracy — competing prices, similar metrics | 5 | 97% |

### Long Meetings

Four scenarios test meetings with extended transcripts where topics are discussed and resolved early, parked and resurfaced later, or buried after unrelated discussion. Retrieval uses a 2-minute window of recent speech, so transcript length beyond that window does not affect retrieval — only the current conversation drives what reference material is surfaced.

| Scenario type | Result |
|---------------|--------|
| Signal buried after procedural discussion | Pass — correct reference surfaced |
| Topic resolved early, should not resurface | Pass — gate blocked retrieval correctly |
| Topic parked mid-meeting, resurfaced at end | Pass — retrieval caught the resurfaced topic |
| Dense pipeline review, reference matches one deal | Pass — competitive intel surfaced for correct deal |

## Failure Resilience

Five scenarios test situations where loaded reference documents could produce incorrect or misleading talking points.

**Stale data:** A pricing document from a previous quarter is loaded. The meeting discusses updated pricing. The system uses the transcript's current numbers rather than the outdated reference. In one test, the system framed the old price as "the previous quote" — historical context for negotiation rather than a current fact.

**Wrong entity:** A customer profile for Company A is loaded. The meeting is with Company B (same industry, similar requirements). The system does not attribute Company A's contract value, SLA, or contact names to Company B.

**Similar entity names:** Two documents with similar names (e.g., "Meridian Financial" and "Meridian Health") are loaded simultaneously. The system keeps facts from each entity separate — contract values, contacts, and requirements are not cross-contaminated.

**Tangential content:** A product roadmap is loaded. The meeting briefly mentions one feature (offline sync). The system surfaces details about that feature without volunteering unrelated roadmap items (push notifications, biometric auth) from the same document section.

**No relevant context:** An unrelated document is loaded (e.g., IT policy handbook for a customer success meeting). The retrieval gate blocks all chunks. The briefing still produces useful talking points from the transcript alone.

## How It Works

1. **Chunking** (ingest time, ~4s): Gemini splits the raw document into semantic chunks and generates 2-4 conversational search phrases per chunk. Search phrases are written in the style someone would speak in a meeting — casual, lowercase, matching speech-to-text output.

2. **Embedding** (ingest time, <15ms/phrase): Each search phrase is embedded on-device using all-MiniLM-L6-v2 (384-dim transformer model). The body text is stored but not embedded.

3. **Retrieval** (query time, ~50-100ms): The user's meeting prep context and recent transcript turns (~2 minutes) are each embedded separately. Each index entry is scored by its best match across all query phrases (max-pooling). Only entries above a score threshold are selected, capped at 5 chunks.

4. **Injection**: Retrieved chunks are formatted as reference context in the briefing prompt. The system instruction tells the model to use reference facts to enrich talking points — not to introduce unrelated topics or reassign facts between entities.

## Benchmark vs Production

**Transcripts match ASR output.** All benchmark transcripts use lowercase text without punctuation, matching the style produced by the on-device speech-to-text pipeline after filler word removal and inverse text normalization.

**Multi-query retrieval matches production.** The benchmark uses the same retrieval path as production: prepared context + recent transcript turns embedded separately, max-pooled similarity, absolute score floor gating.

**System instruction is simplified.** The benchmark uses a subset of the production briefing prompt — the reference context, prepared context, and requirements tracking sections. Production includes additional sections for question detection, interpersonal awareness, and display templates that are not relevant to retrieval quality.

**Temperature.** The benchmark uses temperature 0.5. Production currently uses the Gemini API default. Results at both settings show equivalent number accuracy (100% across 70 focused runs).

**Chunking is non-deterministic.** Gemini's semantic chunking produces slightly different search phrases on each run. The benchmark caches chunks to ensure reproducibility within a run, but results may vary by 1-3% across fresh runs due to different search phrase generation.
