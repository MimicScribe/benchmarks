# Live Transcription Benchmark

Evaluates the live transcription engine in [MimicScribe](https://mimicscribe.app).

MimicScribe transcribes speech in real time, committing text as you speak rather than waiting for the recording to end. The question this benchmark asks is what that costs: how much of what people actually said reaches the transcript, how the losses are distributed, and whether text the app has shown you as settled stays settled.

It measures four things:

1. **Word accuracy** — against human reference transcripts, over the full vocabulary with no filler stop-list. Deletions and insertions are always reported together, because a recognizer that invents words to fill gaps improves one while making the transcript worse.
2. **How losses clump** — a hundred scattered single words is a transcript you can read; one 24-word run is a missing paragraph. Both are counted separately.
3. **Sentence punctuation and casing** — whether sentence ends and capitalization land where a human transcriptionist put them, measured on a second corpus with human-punctuated references.
4. **Display stability and latency** — how much text shown as final later changed, and how long after you stop speaking the words stop moving.

Corpora: 16 meetings from the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/) (CC BY 4.0, far-field single distant microphone, 8.5 hours) for word accuracy and loss distribution; 11 earnings calls from [Earnings-21](https://github.com/revdotcom/speech-datasets) (Rev.com human-punctuated references) for punctuation and casing.

Every comparison is decoded by a single build, with the previous configuration requested from that same build rather than quoted from an older run, so a reported change is the change and not drift between builds.

Results: [results/RESULTS.md](results/RESULTS.md)
