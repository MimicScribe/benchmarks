# Live Transcription Benchmark

Evaluates the live transcription engine in [MimicScribe](https://mimicscribe.app).

MimicScribe transcribes speech in real time from a series of overlapping listening windows. Where two windows overlap, the engine has two independent readings of the same few seconds of audio, and occasionally they disagree about exactly what was said. Every one of those disagreements is a **stitch point**: the engine must commit one transcript, and the failure mode that matters is a word someone actually said silently disappearing there.

This benchmark measures three things:

1. **Stitch integrity** — at every stitch point, did the committed transcript keep the meaningful words from whichever reading captured them? Counted exhaustively, including every case where a word did not survive.
2. **Content-word recall** — how much of a human reference transcript shows up in the committed live transcript at all.
3. **Sentence punctuation** — whether sentence-ending marks land where a human transcriptionist put them, measured on a second corpus with human-punctuated references.

Corpora: 8 meetings from the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/) (CC BY 4.0) for stitch integrity and recall; 11 earnings calls from [Earnings-21](https://github.com/revdotcom/speech-datasets) (Rev.com human-punctuated references) for punctuation.

Results: [results/RESULTS.md](results/RESULTS.md)
