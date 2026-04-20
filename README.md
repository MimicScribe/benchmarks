# MimicScribe Benchmarks

Evaluation suites for the [MimicScribe](https://mimicscribe.app) meeting transcription pipeline.

| Benchmark | What it measures | Results |
|-----------|-----------------|---------|
| [Diarization](diarization/) | Speaker attribution accuracy on public corpora (AMI, Earnings-21, VoxConverse, SCOTUS) | [Results](diarization/results/RESULTS.md) |
| [Meeting Assistant](meeting-assistant/) | Real-time briefing quality — talking points, action items, question detection, interpersonal awareness, long-meeting compaction | [Results](meeting-assistant/results/RESULTS.md) |
| [Context Retrieval](context-retrieval/) | Reference document retrieval + end-to-end hallucination safety across 15 document types — CRM, HTML, PDF, contracts, competitive intel, strategic plans | [Results](context-retrieval/results/RESULTS.md) |
| [Meeting Search](meeting-search/) | Semantic search across months of meetings — buried sub-topics, disambiguation, ASR noise tolerance, conversational vs formal phrasing | [Results](meeting-search/results/RESULTS.md) |
| [Transform](transform/) | Selection-based text transformation quality — number/date/URL preservation, anti-injection from Reference Documents, voice matching, collision resilience | [Results](transform/results/RESULTS.md) |
