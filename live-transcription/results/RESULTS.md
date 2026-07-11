# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR on CoreML, transcribing in real time from overlapping listening windows; a deterministic stitcher commits the final transcript.

Run date: 2026-07-10

## Headline numbers

<!-- MERGE_SEAM_HEADLINE:BEGIN -->
| Metric | Value |
|---|---:|
| Stitch points checked | 736 |
| Stitch points that lost 3+ meaningful words | **0** |
| Stitch points that lost any meaningful word | 161 (149 lost one word, 12 lost two) |
| Content words surviving across all stitch-point disagreements | 86.2% (1,081 of 1,254) |
| Content-word recall vs. human reference transcript | 83.3% |
| Sentence-ending punctuation, precision / recall | 79.7% / 82.2% |
| Sentence ends preserved at speaker handoffs | 92.8% |
<!-- MERGE_SEAM_HEADLINE:END -->

Stitch-point and recall numbers come from 8 meetings of the AMI corpus; punctuation from 11 Earnings-21 calls. Both corpora are described under [Corpora](#corpora).

## What a stitch point is

The live engine decodes audio in overlapping windows, so every stretch of speech near a window boundary is transcribed twice, by two windows that each saw different surrounding context. Usually the two readings agree. When they don't, the stitcher has to commit one transcript — and the failure that matters is a word someone actually said disappearing at that moment, silently.

We count every one of those disagreements. Across the 8 test meetings there were 736. At each one we take every meaningful word either reading contained (skipping fillers like "um" and "okay") and check it against the committed transcript.

## Where words do get lost — every case, counted

Zero stitch points lost three or more meaningful words. 161 of 736 lost at least one: 149 lost exactly one word, 12 lost two. Pooled across all 736 disagreements, the two readings contained 1,254 meaningful words between them and 1,081 survived to the committed transcript (86.2%).

That 86.2% is not a bug count — most of the missing words *cannot* survive, because the two windows heard **different words for the same syllables**. When one window hears "cat" and the other hears "cut", committing both would duplicate the utterance; one reading has to lose. The missing words break down into a few recurring shapes, all visible in the example table below:

- **Rival readings of the same audio** — "cat" vs. "cut", "padded" vs. "parrot". One is committed, the other is counted as lost. Where the engine detects this case it also records the discarded alternative and hands both readings to the LLM cleanup pass instead of deciding silently.
- **Two renderings of the same word** — "'cause" vs. "because", "colour" vs. "color". The word survived; the count is strict enough to flag the spelling that didn't.
- **Half-words at a window edge** — a window boundary cut through a word and one side caught only a fragment ("ree", "arging"). The complete word usually exists in the other reading and is committed; the stranded fragment counts as lost.
- **Genuinely dropped words** — the honest residue. One reading held a word ("range", "fine", "three thirty") that the committed transcript does not contain in any form. Checked against the human reference, most of these turn out to be mishearings that deserved to lose; the real losses are concentrated in simultaneous speech, where the two windows latched onto different speakers and one mixed audio channel can't keep both.

## Example stitches

Real rows from the benchmark, quoted as decoded (readings truncated to the disagreement region). "Lost" lists meaningful words from either reading that are absent from the committed transcript. The last column quotes what AMI's human reference says the speakers said at that moment — so you can judge each stitch yourself.

| Meeting | Time | One window heard | The other heard | Committed | Lost | Human reference |
|---|---|---|---|---|---|---|
| IS1009a | 0:59 | "is" | "we do is" | "we do is" | — | "the first thing we do is introduce ourselves" |
| ES2004c | 6:04 | "Yeah, okay." | "Unless anyone" | "Yeah, okay. Unless anyone" | — | two speakers at once: "Yeah, okay." + "Unless anyone has any questions" |
| EN2002a | 16:29 | "those stuff?" | "their stuff" | "their stuff?" | — | "wanna talk about their stuff?" |
| IS1009a | 4:57 | "cat." | "cut" | "cut." | cat | "traditional kitty cat." |
| ES2004c | 10:27 | "'cause" | "because" | "because" | 'cause | "'cause they use them quite frequently" |
| ES2004c | 5:10 | "ree." | "ird. It's still" | "ird. It's still" | ree | "first is actually third is still important" |
| ES2004c | 18:41 | "padded" | "parrot" | "padded" | parrot | "parrot green to chilli red" |
| IS1009a | 4:04 | "write this" | "range" | "write this" | range | "I can't write with this thing." |
| IS1009a | 12:47 | "have well we have a trying" | "fine" | "have well we have a trying" | fine | "we have well, we have a twen two two two three minutes" |
| ES2004c | 35:59 | "? Yeah for the decisions that we've got" | "ions that we've made" | "? Yeah for the decisions that we've got" | ions, made | "for the decisions that we've made" |
| EN2002a | 31:36 | "…What's w what would you prefer?" | "Or three thirty" | "…What's w what would you prefer?" | three, thirty | two speakers at once: "Three's good though… what would you prefer?" + "Or three thirty." |

The first three rows are the normal case (575 of 736): the readings differ, and the committed transcript keeps everything meaningful — the fuller reading, both halves of a two-speaker moment (6:04), or words from one reading and punctuation from the other (16:29). The lossy rows carry their own verdicts. On rival readings the committed pick goes both ways — right at 4:04 and 5:10, wrong at 4:57, 18:41, and 35:59 — which is exactly why those disagreements are recorded and handed to the LLM cleanup pass rather than decided silently. And the reference reclassifies the "genuine" drops: "range" and "fine" were themselves mishearings that deserved to lose, leaving 31:36 as the table's one real casualty — two people spoke at once, and one mixed audio channel kept one of them.

## Per-meeting results

<!-- MERGE_SEAM_PER_MEETING:BEGIN -->
| Meeting | Stitch points | Lost ≥1 word | Lost 3+ words | Committed words | Content-word recall |
|---|---:|---:|---:|---:|---:|
| IS1009a | 37 | 9 | 0 | 1,713 | 83.9% |
| ES2004c | 115 | 25 | 0 | 6,093 | 88.7% |
| EN2002a | 110 | 34 | 0 | 5,400 | 73.3% |
| TS3003b | 115 | 22 | 0 | 4,573 | 91.7% |
| TS3003d | 121 | 19 | 0 | 4,516 | 85.9% |
| IS1009c | 101 | 17 | 0 | 4,092 | 92.2% |
| ES2004a | 40 | 11 | 0 | 2,177 | 83.8% |
| EN2002b | 97 | 24 | 0 | 4,474 | 73.0% |
<!-- MERGE_SEAM_PER_MEETING:END -->

The two EN2002 meetings score lowest on recall — they are the most argumentative in the set, with the heaviest simultaneous speech. AMI's reference merges each speaker's individual headset microphone into one transcript, so it contains overlapping speech that no single mixed audio channel can fully capture; that caps recall independent of transcription quality.

## Content-word recall vs. a human transcript

Stitch integrity shows the stitching step isn't the thing losing words. A separate, harder question is how much of what was said makes it into the transcript at all — that depends on the recognizer too, not just the stitching. Against AMI's human-corrected references, 83.3% of meaningful reference words (16,511 of 19,831) appear in what MimicScribe committed live, across all 8 meetings.

Both sides are normalized the same way before comparison — case-folded, fillers dropped, punctuation stripped — so formatting differences don't count as misses. A stricter companion measurement is planned: reprocessing the same audio without the real-time constraint, to separate how much of the gap is inherent to transcribing live versus recoverable with more time.

## Sentence punctuation

Sentence-ending marks (`.` `?` `!`) decide where sentences begin and end in the transcript you read and export. Measured against Rev.com's human-punctuated Earnings-21 references (11 calls, token-aligned):

- **Precision 79.7%** — of the sentence ends the engine wrote, four in five match a human transcriptionist's placement.
- **Recall 82.2%** — of the sentence ends the human reference contains, the engine found four in five.
- **Boundary recall 92.8%** — sentence ends at a speaker handoff, the ones that keep two speakers' words from running together, survive at a higher rate than sentence ends overall.

## Corpora

- **[AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)** (CC BY 4.0) — real recorded workplace meetings with professionally corrected transcripts. 8 meetings: IS1009a, IS1009c, ES2004a, ES2004c, EN2002a, EN2002b, TS3003b, TS3003d. Used for stitch integrity and content-word recall.
- **[Earnings-21](https://github.com/revdotcom/speech-datasets)** — 11 real earnings calls with Rev.com human transcripts that include punctuation and casing. Used for sentence-punctuation accuracy, because AMI's references aren't punctuated to reference quality.

Benchmark numbers come from fixed public corpora, not your meetings. Real meetings vary — accents, cross-talk, background noise, and call-audio quality all change what the recognizer hears in the first place. Stitch integrity measures whether the stitching step throws away words the recognizer *did* hear; it says nothing about words the recognizer never heard.

## Method notes

- **Stitch integrity is self-referential.** It compares the pipeline against itself — did the committed transcript keep what either of its own windows heard — so it needs no human reference and stays valid across recognition-model changes.
- **"Meaningful word" is deliberate.** Fillers and function words ("um", "okay", "the") are excluded from the loss count so a dropped "uh" doesn't count the same as a dropped "range". The full stopword-filtered count is what's reported everywhere on this page.
- **Recall is scored against the union of all AMI speaker channels**, including overlapped speech — the hardest fair reading of the reference.
- **Reference quotes in the example table are verbatim** from the AMI word annotations at each stitch point's timestamp, including the reference's own disfluency fragments (the "twen" at 12:47 is what the human transcriber wrote — the speaker cut the word off). No aggregate "pick accuracy vs. reference" number is published: the curated rows let you judge individual stitches, but a headline rate would need its own properly pinned metric.
- The per-row LLM-judge scores used during development are diagnostic and not published as results; judge-model changes would break comparability.

## Reproducing

This run was produced at `parakeet-transcriber` commit `63e09f62` with default parameters:

```bash
# per meeting: decode + record every window-overlap disagreement
scripts/merge_loss_table.py --file <AMI meeting>.wav --cache /tmp/mlt_<meeting>.json
# compose the pinned report (stitch integrity, distribution, recall, punctuation)
scripts/merge_seam_report.py
# punctuation arm (Earnings-21 run directory)
scripts/punctuation_accuracy.py <run_dir>
```

The pinned source of truth is `benchmark/results/asr-merge/merge_seam_baseline.json`, which records the corpus list, a checksum of the AMI annotations, and the regression rule: no change ships if it lowers stitch integrity, introduces a 3+-word drop, or lowers any meeting's committed content words.
