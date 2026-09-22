# Meeting Search Benchmark Results

Pipeline: Gemini 3.1 Flash Lite (conversational search phrase generation) + paraphrase-multilingual-MiniLM-L12-v2 (on-device transformer embedding, 384-dim, 50+ languages) + cosine similarity search with max-aggregation per meeting

Run date: 2026-09-21 | 26 meetings | 138 queries | ~27 vectors per meeting

## Overall

**94% of queries found the correct meeting in the top 3 results**, and 97% in the top 5. Search runs entirely on-device with zero network calls at query time.

| Metric | Score |
|--------|------:|
| Recall@3 | **94.2%** |
| Recall@5 | **97.1%** |
| MRR (mean reciprocal rank) | **84.1%** |

## What changed: search is now multilingual

Search now uses a multilingual embedding model, so meetings held in other languages can be found by meaning, not only English ones. The previous model was English-only (all-MiniLM-L6-v2).

That trade costs some English accuracy, and this benchmark is English-only, so it measures the cost and not the gain. Both models below were scored in the same run on the same Gemini-generated phrases, so the difference is the embedding model alone:

| Embedding model | R@3 | R@5 | MRR | Buried R@3 | Disambiguation R@3 |
|-----------------|----:|----:|----:|-----------:|-------------------:|
| **Multilingual MiniLM-L12 (shipped)** | **94.2%** | **97.1%** | **84.1%** | **93.8%** | **95.8%** |
| English-only MiniLM-L6 (previous) | 97.1% | 98.6% | 87.4% | 98.5% | 91.7% |

The multilingual model is about 3 points lower on English queries overall. The loss concentrates on details buried in long meetings; it does slightly better at telling apart meetings that cover the same topic.

The previous published run (2026-04-10: English-only model, Gemini 3 Flash phrases, since retired) measured 97.8% R@3 and 100% R@5.

## Search Strategy

Each meeting is embedded as many small pieces rather than a few descriptions: its title, full summary, each summary paragraph, 8-15 conversational search phrases, and each action item.

An earlier strategy that embedded only 3-5 formal descriptions per meeting (~6 vectors) measured 76.8% R@3 on the English-only model (2026-04-10). Conversational phrasing matches how people actually search, and paragraph-level embeddings keep topic context that single descriptions lose.

## Buried Sub-Topics in Long Meetings

The hardest test: finding specific details buried deep inside 90+ minute meetings with 6-10 distinct topics. 65 queries target details like specific numbers, person names, technical decisions, and niche sub-topics within marathon meetings.

**93.8% R@3, 98.5% R@5.** The English-only model found 98.5% in the top 3 on the same phrases.

Types of buried details in the test set:

| Detail type | Example query pattern |
|-------------|----------------------|
| Specific dollar amounts | Revenue figures, deal sizes, budget line items |
| Person names in context | Named individuals and their specific contributions |
| Technical decisions | Architecture choices, tool selections, migration plans |
| Compliance/legal | Audit findings, regulatory requirements, SLA terms |
| Competitive intelligence | Competitor evaluations, win/loss details |
| HR/personnel | Hiring decisions, promotion candidates, on-call concerns |
| Infrastructure specifics | Connection pool sizes, token counts, disk utilization |

## Disambiguation

24 queries test whether the search picks the right meeting when the same topic is discussed across multiple meetings. For example, APAC expansion appears in the quarterly business review, the board meeting, and the sales kickoff, each with different details.

**23 of 24 (95.8%) rank the right meeting in the top 3, and all 24 in the top 5.** The system distinguishes between meetings using the specific context in each query: "board approved APAC budget" finds the board meeting, while "APAC territory assignment for new AEs" finds the sales kickoff.

## ASR Pipeline Artifacts

One meeting includes realistic noise from the speech-to-text pipeline: diarization errors (wrong speaker attribution), garbled jargon ("Rabbit MQ" for "RabbitMQ", "Terraforming" for "Terraform", "Elastic Search" for "Elasticsearch"), imprecise numbers, and thin sections from overlapping speech.

All 14 queries that target this meeting find it in the top 3 (12 of 14 rank it first), including queries that use the correct terminology against the garbled summary.

## By Query Type

| Query type | Count | R@1 | R@3 |
|-----------|------:|----:|----:|
| Topic (direct match) | 11 | 90.9% | **90.9%** |
| Buried (sub-topic in long meeting) | 65 | 83.1% | **93.8%** |
| Disambiguation (right meeting among similar) | 24 | 58.3% | **95.8%** |
| Action item (specific task or owner) | 8 | 50.0% | **100%** |
| Decision (outcome queries) | 6 | 83.3% | **83.3%** |
| Person (participant or company) | 6 | 83.3% | **100%** |
| Conversational (casual phrasing) | 10 | 70.0% | **100%** |
| Vague (ambiguous, multiple valid matches) | 8 | 37.5% | **87.5%** |

## Known Failures

8 of 138 queries fail to rank the correct meeting in the top 3. 4 of those find it in the top 5.

**Details buried in long, multi-topic meetings (4).** Specific facts mentioned once inside a long meeting, such as a frontend performance detail in a 150-minute business review, rank below meetings with more general overlap. This is where the multilingual model loses most against the English-only one.

**A broad topic query (1).** "quarterly revenue review" ranks the finance budget review first. A short query with common business terms matches several meetings about money, and the specific meeting is not the closest.

**A topic shared across meetings (1).** A query about a customer choosing between vendors ranks the right meeting 5th, behind other meetings that discuss the same competitor.

**Vague and decision queries (2).** "team performance review" has two valid answers and matches a retrospective instead. A query about an API versioning decision ranks a product planning meeting that discusses the same API above the architecture review where the decision was made.

## How It Works

1. **Search phrase generation** (summarization time): Gemini 3.1 Flash Lite generates 8-15 conversational search phrases per meeting alongside the summary. Phrases are written in speech-style phrasing with lowercase proper nouns, covering buried sub-topics and specific details, not just the main theme.

2. **Embedding** (summarization time): Title, full summary, each summary paragraph, each search phrase, and each action item are embedded individually on-device using paraphrase-multilingual-MiniLM-L12-v2 (384-dim transformer). ~27 vectors per meeting.

3. **Search** (query time): The query is embedded on-device. Cosine similarity is computed against all meeting vectors within a 6-month window using Accelerate/vDSP batch dot products. Results are aggregated per meeting by max similarity: a meeting's score is its single best-matching vector.

4. **Hybrid ranking**: Vector similarity (50% weight) is combined with full-text search rank (30%), recency (10%), and meeting length (10%) to produce final results. The benchmark tests vector similarity in isolation.

## Benchmark vs Production

**Search phrases are Gemini-generated, not hand-crafted.** The production results use Gemini 3.1 Flash Lite phrases, the model that ships. The benchmark generates phrases from the meeting summary in a separate call; the app generates them from the transcript in the same call that writes the summary, using the same phrase rules.

**Meeting summaries are synthetic but realistic.** The corpus includes synthetic summaries at production-realistic lengths (780-1,127 words for marathon meetings). One meeting includes ASR pipeline artifacts (diarization errors, garbled jargon, imprecise numbers) matching real pipeline output.

**Paragraph splitting matches production code.** The benchmark splits summaries on double newlines with a 30-character minimum, matching `MeetingEmbeddingManager.generateAndStoreEmbeddings()`.

**Embedding model and search floor match production.** The benchmark uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, the same model weights as the on-device Swift implementation, with the same minimum-similarity floor the app applies for that model.

**The corpus is English-only.** It measures what the multilingual model costs on English meetings. It does not measure how well search works in other languages.

**Search phrase generation is non-deterministic.** Gemini produces slightly different phrases on each run. This run used one set of freshly generated phrases for both models; results may vary by 1-2% on another fresh run.
