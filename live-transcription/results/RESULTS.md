# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet Ultra (a post-training of Parakeet TDT 0.6B v3) on CoreML, transcribing in real time from overlapping listening windows.

Run date: 2026-09-27. Corpus: 16 AMI meetings, 8.5 hours, headset mixdown (every speaker's close-talk microphone summed to one channel). Punctuation and casing are measured on 11 Earnings-21 calls, because AMI's references are not punctuated to reference quality. Live display and latency come from 4 recorded capture sessions, a smaller basis, marked as such.

**What changed this time is the speech model.** The app now runs [Parakeet Ultra](https://huggingface.co/moondream/parakeet-ultra) in place of Parakeet v3, inside the same pipeline. Every "previous" column below is Parakeet v3 run through the same build, so the difference is the model and nothing else. Ultra drops fewer words and loses no long stretches. It also writes fewer "um"s and "uh"s, turns "gonna" into "going to", and writes fewer, more precise sentence ends. This page scores the transcript verbatim, so each of those shows up here as a cost, and all of them are published.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **3.2%** |
| Deletion rate on speech spoken over another speaker | 39.0% |
| Runs of 10+ consecutive words lost, whole corpus | **0** in 8.5 hours |
| Longest single run of lost words | 8 |
| Sentence-ending punctuation, precision / recall | 88.5% / 80.7% |
| Sentence ends preserved at speaker handoffs | 95.0% |
| Sentence starts rendered capitalized | 82.5% |
| Text shown as final that later changed | 0.31% |
| Time from you stopping speaking to the text being final | 4.9 to 8.5 s |
| Same audio twice, same transcript | byte-identical |

The first two rows are the pair to read together, and they are explained below.

## Word accuracy

Measured against the human reference over the whole transcript, full vocabulary, no filler stop-list. Reference: 81,202 tokens across the 16 meetings, after both sides go through the same number-and-acronym normalizer, with numbers converted to digits on both sides (the product now writes every number as words, and the reference writes digits).

| | Parakeet v3 | Parakeet Ultra | change |
|---|---:|---:|---:|
| Reference words deleted | 11,716 | 11,340 | −376 |
| Words inserted that the reference lacks | 3,403 | 3,418 | +15 |
| Words substituted | 4,103 | 4,157 | +54 |
| Composite error rate | 23.67% | 23.29% | −0.38 points |

Ultra deletes 376 fewer reference words across 8.5 hours of meetings for 15 more insertions and 54 more substitutions. The insertions need reading rather than counting. Most of this corpus's insertions are transcription convention (the reference writes "wanna", the transcript "want to") or speech the annotators never transcribed. The residue worth acting on rises from 1,226 to 1,354, and what it holds is small function words the reference lacks ("I [am] also", "we [are] able"): Ultra writes disfluent speech in grammatical form.

**On the earnings calls the verbatim count goes the other way:** deletions 1,516 → 2,364, insertions 1,955 → 1,807, error rate 8.44% → 9.15%. The Rev.com references transcribe every "uh" and "um", and Ultra leaves most of them out. Scored with filled pauses and casual forms folded on both sides and numbers left out, the model comparison on all 27 files reads 14.14% for v3 and 13.63% for Ultra, better on 22 of the 27 files ([the ASR bake-off](../../asr-bakeoff/RESULTS.md#parakeet-ultra--the-model-the-product-ships-now) has that table for every model tested).

**We do not publish an absolute word error rate from this instrument.** The AMI reference is the time-ordered union of every speaker's channel, so where two people talk at once it interleaves words no single-stream decoder can emit in order, and each scores as an error however good the recognizer is. That bias is large and constant across builds, which is why the change is meaningful while the level is not.

### How hard the assignment is

| | Parakeet v3 | Parakeet Ultra |
|---|---:|---:|
| Reference words spoken over another speaker | 30.1% | 30.1% |
| Deletion rate within overlapped speech | 40.5% | 39.0% |
| Deletion rate on clean speech | 3.2% | 3.2% |

Nearly a third of the words in this corpus are spoken over somebody else, and inside that population deletion runs at 39.0% against 3.2% on clean speech. That gap is close to a statement about physics: one mixed channel, two simultaneous talkers. Ultra's gain on deletions comes mostly from overlapped speech.

## How badly do losses clump

A hundred scattered single words is a transcript you can read. One 14-word run is a missing exchange. Clean speech only:

| Consecutive words lost | Parakeet v3 | Parakeet Ultra |
|---|---:|---:|
| 1 word | 1,734 | 1,790 |
| 2 to 4 words | 459 | 455 |
| 5 to 9 words | 28 | 13 |
| **10 or more words** | **4** | **0** |
| Longest single run | 14 | 8 |

The long runs are gone: no run of 10 or more words in 8.5 hours, against four on v3, and the 5-to-9 bucket halves. The single-word bucket grows by 56; Ultra leaves out more filled pauses, and those are lost one word at a time. On v3 the long runs were stretches like "when you use a remote do you press the buttons with your thumb usually", all at the edge of crosstalk.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | Parakeet v3 | Parakeet Ultra | |
|---|---:|---:|---|
| Sentence-ending precision | 86.8% | **88.5%** | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 82.9% | 80.7% | of the sentence ends a human wrote, the share found |
| Boundary recall | 94.4% | **95.0%** | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 84.8% | 82.5% | of real sentence starts, the share capitalized |
| Capitalization precision | 89.3% | 88.6% | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

This is the trade the model makes, and it is the one that costs something. Ultra writes fewer sentence ends: 854 missed against 760 on v3. The ones it writes are more often right, with 95 fewer placed where none belonged. At speaker handoffs, the boundary that stops two speakers running together, it keeps more (34 missed against 38). On the AMI meetings it goes the other way: 86% of sentence ends at a speaker change against 90% for v3. The measurement is on [the bake-off page](../../asr-bakeoff/RESULTS.md#parakeet-ultra--the-model-the-product-ships-now).

Two of these rows were hard floors: sentence-ending recall (83.6%) and capitalization precision (89.3%). Both fall with the model, and both are re-set to Ultra's values here, stated rather than hidden. They are floors again from this release: the next change must not lose more. Terminal punctuation is not cosmetic. Sentence boundaries become the windows used for speaker embedding, so a punctuation change is also a speaker-identification change.

## Live display stability

"Text shown as final stays final." The display commits in two tiers and the promise attaches only to the committed tier.

| | Parakeet v3 | Parakeet Ultra |
|---|---:|---:|
| Committed text that later changed | 0.25% | **0.31%** |
| Provisional tail text that later changed | 5.47% | 4.95% |
| Words the renderer dropped entirely | 0 | **0** |
| Revisions inside the trailing 60 s, per corpus | 349 (69% single-word) | 423 (69% single-word) |

The committed tier holds its promise on both models, at about a third of a percent, which is roughly 16x steadier than the provisional tail. Ultra's committed text changes a little more often than v3's on the same build: 609 of 196,069 committed words against 505 of 199,579, and 423 small revisions against 349. Its provisional tail changes less. The last page read 0.33% on the build before this one.

Basis: 4 recorded capture sessions, not the 16-meeting corpus. All four were **re-recorded for this page**, on both models, with the build under test. They are no longer carried forward.

## Latency to trust

How long after you stop speaking until the words stop moving.

| Capture | Pauses measured | Parakeet v3 | Parakeet Ultra |
|---|---:|---:|---:|
| ES2004a | 46 | 8.5 s | 8.4 s |
| IS1009b | 30 | 6.1 s | 6.7 s |
| IS1009c | 64 | 6.4 s | 8.5 s |
| TS3003a | 86 | 4.8 s | 4.9 s |

**4.9 to 8.5 s** median pause-to-commit on Ultra, against 4.8 to 8.5 s on v3 through the same build and 6.9 to 9.9 s on the last page's build. Most of the gain over the last page is work on the live path, not the model. Between the two models it is level on three sessions, and IS1009c waits about two seconds longer on Ultra. Pause counts are Ultra's, and they differ slightly between models because the model decides where the pauses fall.

## The live view against the script

Everything above scores the final transcript. These rows score what is on
screen while you speak: seven two-channel recorded sessions (mic plus system
audio, 32.9 minutes) replayed through the full live pipeline, the rendered
transcript sampled once per second. The duplication rows need no reference —
a span shown twice back to back is a defect whatever was said. The rest are
checked against the session's script as performed.

| | |
|---|---:|
| Doubled phrases (4+ words) visible in the live view | **4 episodes** in 32.9 min |
| Short duplicated spans, punctuation-identical ("on Friday. on Friday.") | **6 episodes** |
| Words shown fused with a fragment of themselves ("Turningning") | **0 episodes** |
| Words shown that were never spoken | 636 |
| Spoken words that never appeared on screen | 160 |
| Already-shown words rewritten under the reader (flicker, case counts) | 361 of 5,037 shown, **7.2 per 100** |
| Punctuation changed on words that stayed | 186, **3.7 per 100** |
| A short repeat ("short short") that reached the saved transcript | 19 |
| The other speaker's words appearing on this channel's row | 3 episodes, 0 saved (tracked, not gated) |
| A bare fragment of a word ("ight") on screen | 2 episodes, 1 saved |

Replayed 2026-09-27 on a debug build of `964e6af11`, the same 1.5 s refresh floor as the last page. The last page read 13.0 and 7.4 per 100 for flicker and punctuation changes. On v3 at the build before this one they read 7.8 and 3.9, so most of that fall is three weeks of work on the live path, and Ultra takes it the rest of the way to 7.2 and 3.7. Bare word fragments are the model's own gain: 10 on v3 at that build, 2 on Ultra.

**The duplication rows rose, and every new episode is real speech.** Doubled phrases went from 2 to 4 and punctuation-identical duplicates from 4 to 6. Read from the saved rows, the new ones are:
- a speaker stuttering ("this is, this is", which v3 wrote as "this this is"),
- a speaker restarting a figure mid-sentence, shown for about a second and never saved,
- and "That'd be great." said three times, which v3 saved identically.

This gate's ratchet on the duplicated-span total failed by one against the previous pin and was re-pinned to this run with that trace. It reproduced on two separate full replays, so it is not jitter.

The last two rows are scored on the five sessions with a verbatim script
(24.2 minutes, 3,346 script words) and count every distinct rendering that
ever appeared, including provisional text later corrected. A misheard word
charges both rows at once, so they are dominated by ordinary
misrecognitions. They are regression bars, not quality claims: what they
exist to catch is a build that makes the live view invent or withhold more
than this one does.

**Text that vanishes and comes back.** A separate counter watches for the live view getting *shorter*: a chunk of words disappearing from the screen and returning a moment later. **2 episodes on this replay**, the worst removing 3 words and the longest absence 7 s, against 3 on the last page's build. The range across replays of one binary is as large as the whole count, so read it as "a handful per half hour of replay", not as a value.

### Numbers on screen

Spoken quantities are checked by value rather than spelling, so "$115 million"
and "one hundred and fifteen million dollars" count as the same number.

| | |
|---|---:|
| Spoken quantities that reached the screen intact | 136 of 145 |
| Rendered as a different quantity | 2 |
| Dropped | 7 |
| Numbers shown that nobody said | 1 |
| Numbers damaged where two decoding windows were stitched | 0 in the final view |

One of the five scripted sessions is a numbers-heavy earnings call and carries
59 of the quantities; the other four are conversational and carry 17 to 24 each. This
is a thin basis for a number-accuracy claim and is published as a regression
bar, not as a quality figure. Against the last page: the same 136 intact, one
more rendered as a different quantity, one fewer invented.

### Numbers in the saved transcript

The live view is one pass over the audio; the transcript you keep is the one
that matters. The same by-value check is run on the saved transcript of the
11 Earnings-21 calls against Rev.com's human references — about 2,850 spoken
quantities, the densest public substrate for numbers we have.

| | Parakeet v3 | Parakeet Ultra |
|---|---:|---:|
| Spoken quantities that reached the saved transcript intact | 2,725 of 2,858 | **2,730 of 2,854 (95.7%)** |
| Rendered as a different quantity | 58 | **51** |
| Dropped | 75 | **73** |
| Numbers in the transcript that nobody said | 105 | **99** |

By kind of number, on Ultra:

| | scored | intact | different | dropped | nobody said |
|---|---:|---:|---:|---:|---:|
| Plain counts and amounts | 1,022 | 954 | 32 | 36 | 61 |
| Money | 363 | 344 | 13 | 6 | 4 |
| Percentages | 404 | 395 | 5 | 4 | 5 |
| Years | 309 | 302 | 1 | 6 | 3 |
| Fiscal quarters | 441 | 438 | 0 | 3 | 2 |
| Ordinals | 235 | 219 | 0 | 16 | 18 |

Every total moves the right way with the model, though per call it churns in both directions, which is what a model swap looks like. Both columns are the same build and the same scorer, on the transcript as saved. That scorer is newer than the one the last page used, and the transcript now writes every quantity as words ("two thousand twenty", "fifteen percent") where the last page's build wrote digits. So the last page's 2,777 of 2,857 and these columns are not a comparison: they are two scorers reading two spellings.

On the ASR bake-off's basis, where every model's text is re-normalized to digits before scoring, the same two arms read 2,769 intact for v3 and 2,755 for Ultra. Part of that gap is the re-normalization joining neighbouring numbers the speaker said separately; that page publishes both readings.

This table is what a change to number handling is gated on, by kind of number,
and it is published as a regression bar; the substrate is prepared remarks read
from a page, so it says nothing about numbers spoken over another speaker.

<!-- BEGIN GENERATED: reader-visible residual (scripts/generate_public_results.py --live-transcription) -->

## Words the recovery layer adds

Where the decoder emitted nothing over voiced audio, or where two
decoding windows are stitched, a repair pass puts words back. That
pass is the only mechanism on this page that can ADD text, so it is
the only one that can put a sentence on screen nobody said. Deletion
counts are blind to it by construction and so is the clumping table.

| | resolved against the alignment | said within a second |
|---|---:|---:|
| Words added per meeting-hour | 30.5 | 30.5 |
| of which the reference supports | 18.0 | 18.3 |
| **of which wrong** | **12.5** | 12.3 |
| Precision | **59.0%** | 59.8% |

27 files, 18.83 hours. The repair pass added
603 words and 575 of them reached the saved
transcript; the table is over those, because they are the ones anybody
read.

**Added and later removed: 28.** 28 of the added words were taken
out again by a later pass before anything was saved, so no reader ever
met them. They are not wrong words on a page; they are the repair pass
producing text something else had to clean up, which is a different
thing and is counted as its own line rather than folded into the rate
above. Folded in they would add 1.49 to the wrong-words row.

The left column is the headline. Both definitions ask whether an added
word belongs; they differ in what counts as belonging. The right column
asks only whether the same word was spoken within a second, so a repair
word standing where a different word was said reads as correct there.
163 of the added words are exactly that, and a reader
sees every one of them as a wrong word. The left column resolves each
added word through the same alignment the error counts above use, which
is why it is the one pinned.

By repair class, on the headline definition:

| | added | supported | wrong | precision |
|---|---:|---:|---:|---:|
| The stitch between two decoding windows | 91 | 40 | 51 | 44.0% |
| Silence the decoder left over voiced audio | 484 | 299 | 185 | 61.8% |

This is published as a regression bar and not as a quality claim. The
measured admission rules that would raise the precision were all
refuted on held-out files, so the number is what the shipping
configuration does, stated rather than improved.

*Basis: 27 files, 18.83 hours, measured at `964e6af11` on a ledgered run. This is a different arm from the word-accuracy and punctuation rows above, which is stated here rather than left to provenance; see the provenance table.*

## Hallucinated rows

The subset of the above that reads as invented text rather than as a
misheard word: a stretch of added words with nothing right in it. One
wrong word inside a stretch that recovered four is an over-reach; a
stretch with nothing right in it is a phrase on screen that was never
spoken.

The unit is a RUN: the added words of one repair decision, cut wherever
two of them are more than 1.5 s apart. One repair decision can splice
words back in several places, so a run is a fragment of a decision and
not the decision itself, and the run is what a reader meets on the page.
Both counts are given below.

| | resolved against the alignment | said within a second |
|---|---:|---:|
| All-wrong runs per meeting-hour | **5.68** | 6.48 |
| Words in them, per meeting-hour | **8.76** | 9.93 |
| Of 3 words or more, per meeting-hour | **0.69** | 0.80 |

107 all-wrong runs of 330 runs on the headline
definition, carrying 165 words, 13 of the runs three
words or longer, over 18.83 hours. The three-word row is the one that
matters to a reader: a one-word all-wrong run is an ordinary
misrecognition, and a three-word one is a sentence fragment nobody said.

Counted by whole repair DECISION rather than by run, the same rows read
24 all-wrong decisions of 66
(23 on the surface definition). That count is
smaller because one decision that gets a word right anywhere rescues
every fragment of itself, including a fragment several seconds away with
nothing right in it. The per-run count is what is pinned, for that
reason; the per-decision count is given so the two are not confused.

These counts are over all 603 added words. The section above is over
the 575 of them that reached the saved transcript, because its question
is what a reader met; this one's unit is a repair decision's own
fragment, so it counts the phrase the pass produced whether or not a
later pass took it out again.

11 of the 107 all-wrong runs are made entirely of words a later
pass removed before the transcript was saved, so nobody read those.
They stay in this count: the unit here is the repair decision's own
fragment and the pass produced the phrase either way. The
reader-visible split is made in the section above, and the number is
stated here so the difference between the two sections is visible
rather than inferred.

This class is open. Every admission rule measured against it (word
confidence, name shape, digit shape, run length, corroboration by a
second read of the same audio) either failed to separate it from real
recovered speech or cost more true words than it removed wrong ones. It
is published because it is the residual a reader can see, not because it
is solved.

*Basis: 27 files, 18.83 hours, measured at `964e6af11` on a ledgered run. This is a different arm from the word-accuracy and punctuation rows above, which is stated here rather than left to provenance; see the provenance table.*

## Saved-transcript duplicates

"It repeats itself" is the question users ask about a transcript, so
it is measured rather than argued about. A duplicate here is a span of
two or more words ending one row and opening the next.

| | |
|---|---:|
| Repeated spans per meeting-hour | **2.34** |
| Share that sit on a speaker change | **100.0%** |
| Removed by the shipped de-duplication rule | 0 |

44 spans in 18.83 hours across 27 files;
44 of them fall where the two rows belong to
different speakers.

The speaker-change share is the finding, not the count. These are
overwhelmingly two people saying the same short thing in turn: "Thank
you." answered with "Thank you.", "Go ahead." answered with "Go ahead,
Carolina." That is what a transcript is supposed to show, and a rule that
collapsed them would delete a real exchange. That is why this row is
tracked and not ratcheted, and why the shipped de-duplication rule, which
works inside a row, is left unable to reach across one.

## Wrong figures by magnitude

A wrong number is not one thing. `$17 million` for `$17.5 million`
misstates a figure; `$40 billion` read as `$40 million` misstates it
by a factor of a thousand, and only one of those changes what the
sentence means. This is the same population as the "rendered as a
different quantity" row of the saved-transcript table above, split by
how far the rendered value is from the spoken one:

| Wrong by a factor of | | |
|---|---:|---|
| under 10x | 25 | tracked |
| 10x to under 1,000x | 20 | tracked |
| 1,000x or more | 6 | tracked, see below |

51 corruptions in total, neither more nor fewer than that row.
The ratio is folded, so an amount rendered a thousand times too
large and one rendered a thousand times too small count the same.

**The bottom row is tracked, not a bar, and here is why.** It is a split
of a comparison against reference entities, not a count of wrong figures
a reader would meet, and most of what is in it is the comparison rather
than the transcript. Every member, named:

| the reference says | the transcript says | what it is |
|---|---|---|
| `100` | `hundred billion` | the speaker corrected themselves ("100 billion… $100 million") and the scorer paired the correction as one entity |
| `153` | `hundred and fifty three one hundred fifty four point three million` | a restart ("153- 154.3 million") paired as one entity |
| `14` | `fourteen million a quarter` | the reference names no scale at the site |
| `200` | `two hundred thousand thousand` | a real misreading: "200 to 250,000" written "two hundred thousand thousand" |
| `$1 billion $295 million` | `one million two hundred ninety five thousand dollars` | a real disagreement about the scale: the figure is written a thousand times too small |
| `$40 billion` | `forty million dollars` | a real disagreement about the scale word at the site (the same site as on v3) |

Three of them are real errors in the transcript: two scale words wrong
and one range misread. The others are the scorer pairing a
self-correction or a restart as one entity, and a reference that does
not name the scale at the site at all. Counting those as regressions
would gate future releases against the reference's coverage and the
scorer's tokenizer, so the row is published and not enforced.

**What is enforced instead** is the narrower question the row was
reaching for: a figure where the transcript and the reference both name
a scale and name a different one. That is two sites on this corpus: the
"$40 billion" site both models share, and "$1 billion $295 million",
which this model writes a thousand times too small, and it is pinned at
2
with no tolerance. It excludes every case above where the disagreement
is one side having no scale word at all, which is where the readings
live.

## Per-file sign counts

Every delta on this page is a corpus total, and a total can hide a
split: a few files improving a lot while the rest drift the other way
nets out the same as everything moving a little. The substrate is
deterministic run to run, so the noise on these totals is which files
are in the corpus, not measurement jitter, which makes the sign counts
the honest denominator for every change column above.

| Delta on this page | files | better | worse | unchanged |
|---|---:|---:|---:|---:|
| Word accuracy (16 AMI meetings) | 16 | 6 | 8 | 2 |
| The earnings-call counterexample (11 Earnings-21 calls) | 11 | 1 | 10 | 0 |
| Both corpora together (27 files) | 27 | 7 | 18 | 2 |

Scored on each file's own error rate, on the same normalized basis as
the word-accuracy table. `unchanged` is exact equality: on a
deterministic substrate a file that does not move did not move at all.

The one file that moved the wrong way is `(18 of 27)` (on the full-vocabulary verbatim basis, where Ultra's missing filled pauses count as deletions; 10 of the 11 earnings calls, whose references transcribe every 'uh').

## Added decodes

**None this release.** No decoding site was added to the product path,
so no second pass of the audio is paid for on your machine that was not
paid for on the last build. Every recovery number above comes from an
admission decision over words a decode already produced.

This line is a pinned field rather than a sentence somebody remembered
to update: a new decode has to be declared in the pin before it can
ship, and it is declared with what it costs: where it runs, what
triggers it, seconds of audio re-decoded per meeting-hour, and the
words it recovered per hour.

<!-- END GENERATED: reader-visible residual -->

## Determinism

Same audio in, byte-identical transcript out, verified rather than asserted. With the new model, this build decoded all 27 files twice from cold, with no cache of any kind. The two runs agree byte for byte on every stage the pipeline writes: 216 of 216 per-file dumps, including the 27 saved transcripts the scorers read.

Sampling-based systems cannot claim this, and it is load-bearing for everything above: a comparison between two configurations means nothing unless each is reproducible alone.

## Corpora and caveats

- **[AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)** (CC BY 4.0), 16 meetings, 8.5 hours, the Mix-Headset mixdown: every speaker's close-talk microphone summed to one channel, so overlapped speech is fully present and there is no room reverberation. Scored against the union of all speaker channels *including* overlapped speech, the hardest fair reading.
- **[Earnings-21](https://github.com/revdotcom/speech-datasets)**, 11 earnings calls with Rev.com human references including punctuation and casing.

Benchmark numbers come from fixed public corpora, not from your meetings. Real meetings vary, and accents, cross-talk, background noise and call-audio quality all change what the recognizer hears in the first place.

This is not the far-field condition. A single distant microphone in the same room would score worse, and results on the two are not comparable; an earlier version of this page described the corpus as far-field, which was wrong (corrected 2026-09-03 after hash-matching the audio against the AMI mirror).

The word-accuracy figures above are AMI only. Earnings-21 appears on this page for punctuation and casing, and the two corpora are not aggregated.

## Provenance

| Axis | Commit | Measured | Basis |
|---|---|---|---|
| Word accuracy, loss clumping, crosstalk split | `964e6af11` | 2026-09-27 | 16 AMI meetings |
| Sentence punctuation and casing | `964e6af11` | 2026-09-27 | 11 Earnings-21 calls |
| Determinism | `964e6af11`, decoded twice | 2026-09-27 | 27 files (16 AMI + 11 Earnings-21) |
| Live display stability | `964e6af11` | 2026-09-27 | 4 capture sessions, re-recorded on both models |
| Latency to trust | `964e6af11` | 2026-09-27 | the same 4 capture sessions |
| Live view against the script | `964e6af11`, debug build | 2026-09-27 | 7 capture sessions (script rows: 5) |
| Numbers in the saved transcript | `964e6af11` | 2026-09-27 | 11 Earnings-21 calls (2,854 quantities) |
| Words the recovery layer adds | `964e6af11` | 2026-09-27 | 27 files, 18.83 hours, ledgered run |
| Hallucinated rows | `964e6af11` | 2026-09-27 | the same ledgered run |
| Invented phrases over silence | `964e6af11` | 2026-09-27 | 16 AMI meetings, 8.51 hours, its own token-frame arm |
| Wrong figures by magnitude | `964e6af11` | 2026-09-27 | this page's 51 corruptions, split by ratio |
| Saved-transcript duplicates | `964e6af11` | 2026-09-27 | 27 files, 18.83 hours |
| Per-file sign counts | `964e6af11` | 2026-09-27 | this page's own pair of arms, 27 files |

**One build, two models.** Every row above is the same build, from a clean tree.
The Parakeet Ultra column is a cold decode (`swift_pipeline_2026-09-27T213110Z`,
no transcription cache of any kind). The Parakeet v3 column replays v3's own
recorded window decodes through the same pipeline code. A replay is not a
decode, so it was checked: the Ultra replay of the same kind matches the cold
Ultra decode's word counts to the digit.

**The scoring basis is stated because it moved.** The product now writes every
number as words, so the word-accuracy scorers convert numbers to digits on both
sides before comparing (`MIMICSCRIBE_ITN_NUMBERS=1`). Without that switch they
score numbers as spoken, which is a different basis, and the gate refuses to
compare the two. The number rows score the transcript as saved.

**The live-view row is a debug build.** Replaying a recorded session through
the live path needs one, and it is stamped with the commit that actually ran.

Model: Parakeet Ultra (`moondream/parakeet-ultra`, CoreML conversion
`FluidInference/parakeet-ultra-coreml` at `95eaa59a`), Apple Silicon. The
previous column is `parakeet-tdt-0.6b-v3` with the rebuilt int8 encoder.

## Pins

The values the next release is measured against. A pin is not a target; it is the number a regression has to get past unnoticed, and publishing it is what stops that happening quietly.

| Pinned value | Class | Pin |
|---|---|---:|
| Renderer dropped words | must not worsen | 0 |
| Runs of 10+ consecutive words lost | must not rise | 0 |
| Longest single run of lost words | must not rise | 8 |
| Reference words deleted | regression bar | 11,340 |
| Words inserted, actionable | regression bar | 1,354 |
| Clean-speech deletion rate | regression bar | 3.2% |
| Committed text later changed | ceiling 1.0% | 0.31% |
| Sentence-ending recall | must not worsen | 80.7% |
| Boundary recall at speaker handoffs | must not worsen | 95.0% |
| Sentence-start capitalization | regression bar | 82.5% |
| Capitalization precision | must not worsen | 88.6% |
| Doubled phrases visible live | regression bar | 4 |
| Punctuation-identical duplicated spans | regression bar | 6 |
| Words shown fused with a fragment of themselves | regression bar | 0 |
| Words shown never spoken | regression bar | 636 |
| Spoken words never shown | regression bar | 160 |
| Already-shown words rewritten (flicker), per 100 shown | regression bar, same refresh cadence | 7.2 |
| Punctuation changed on unchanged words, per 100 shown | regression bar, same refresh cadence | 3.7 |
| Short repeats reaching the saved transcript | regression bar (7-session sum of rises) | 19 |
| Other channel's words on this channel's row | tracked (row timing cannot separate bleed from coincidence) | 3 |
| Bare word fragments on screen | regression bar | 2 |
| Spoken quantities rendered as a different quantity | regression bar | 2 |
| Spoken quantities dropped | regression bar | 7 |
| Numbers shown that nobody said | regression bar | 1 |
| Saved-transcript quantities rendered as a different quantity | must not rise, per call | 51 |
| Saved-transcript quantities dropped | must not rise, per call | 73 |
| Saved-transcript numbers nobody said | must not rise, per call | 99 |
| Figures where the scale word disagrees | must not rise, tolerance 0 | 2 |
| Wrong words the recovery layer adds, per hour | regression bar | 12.5 |
| Added words removed again before saving, per hour | tracked | 1.49 |
| Hallucinated runs per hour | regression bar | 5.68 |
| Words in them, per hour | regression bar | 8.76 |
| Of 3 words or more, per hour | regression bar | 0.69 |
| Invented phrases over silence, per hour | regression bar | 2.59 |
| Words in them, per hour | regression bar | 16.7 |
| Of them in the last 15 seconds of a file | must not rise | 2 |
| Duplicate spans per hour | tracked | 2.34 |
| Decodes added to the product path | declared before it ships | none |
| Determinism | must hold | byte-identical |

**Pins that moved the wrong way with the model, re-set deliberately:**
- sentence-ending recall (83.6% → 80.7%) and capitalization precision (89.3% → 88.6%), both hard floors;
- sentence-start capitalization (84.8% → 82.5%);
- actionable insertions (1,226 → 1,354);
- duplicated spans on screen (4 → 6);
- invented phrases over silence (2.23 → 2.59 per hour, 22 runs against 19 in 8.5 hours).

The last one needs a sentence of its own. v3 through the same build reproduces the old pin exactly, so the rise is the model. The added runs are the same passages v3 also transcribes, mostly quiet off-microphone talk that the reference never covered and that Ultra writes more of. Each of these is a model trade published beside the gains above, not a relaxed bar: from this release they are floors and ceilings again.

The live-view bars are enforced per session with a measured tolerance for
replay timing jitter (the same recording replayed twice moves the word
counts by a few dozen), plus a tighter cap on the total across sessions —
uncorrelated jitter and a systematic regression separate cleanly there.

Three rules govern how these may be read, and each exists because ignoring it produced a wrong published number here at least once:

1. **A number is only valid for the configuration that ships, on the corpus it claims.** Two numbers on an earlier version of this page were not: one set was five weeks stale, the other came from a policy reachable only by disabling the shipping one. Both read exactly like current numbers. A third case was caught before it reached this page — a punctuation figure computed over 2 of the 11 calls — which is why the gate now checks how many files produced a number before comparing it to anything.
2. **Deletion-only measures never appear alone.** A mechanism that recovers words by inventing them improves every deletion count here, so insertions are published beside deletions or neither is published.
3. **An unchanged result must be proven to have run.** A cached decode once reported an entire change as having no effect with every gate green. The Ultra arm above is a fully cold decode, and an arm that reports no cache misses is discarded rather than believed.

Every number on this page is produced by a committed script that a later release can re-run. An earlier version carried a family of figures whose analysis code was never committed and whose input was not archived, which meant they could never be checked for drift; they were removed rather than restated.

## Reproducing

The scorers are the same ones that gate changes internally, unmodified — there is no public-only scoring path.

```bash
# every axis below in one command, each compared against its committed pin.
# This is what produced the numbers on this page.
scripts/live_transcription_benchmark.sh <out-root> --baseline <previous arm> --determinism
# the scorers convert numbers on both sides; the runner sets this for them:
#   MIMICSCRIBE_ITN_NUMBERS=1 python3 scripts/score_corpus_wer.py ...

# or one step at a time. First, one decode per arm, 16 AMI meetings + 11
# Earnings-21 calls
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus --corpora ami,earnings21 --files <list>

# or with the RELEASED app and no source at all. MIMICSCRIBE_DATA_DIR (alias:
# --data-dir <path>) points the whole data directory at a throwaway one, so the
# run touches no database, keychain item, voice profile, preference or update
# check of an existing install. Model weights are the one thing it still shares.
MIMICSCRIBE_DATA_DIR=./sandbox /Applications/MimicScribe.app/Contents/MacOS/mimicscribe \
  --benchmark-pipeline-corpus --corpora ami,earnings21 --files <list>

# word accuracy, crosstalk split, loss clumping — both call the built binary's
# --itn-text mode to put reference and rows on one basis, and print which basis
# they used; --raw is the pre-2026-08-29 counting and does not match the pins
python3 scripts/score_corpus_wer.py --arms <A> <B> --labels base curr --stratify
python3 scripts/asr_bench.py       --arms <A> <B> --labels base curr

# punctuation and casing
python3 scripts/punctuation_accuracy.py --compare <A> <B>

# the live view against the script (replays the recorded sessions live, on a
# debug build; --repeat 2 replays each session twice to measure replay jitter)
scripts/live_invariants_gate.sh <out-root> --repeat 2
# or by hand:
python3 scripts/score_live_invariants.py --all <replay-root> --json-out chg.json
python3 scripts/score_live_invariants.py --compare <pinned baseline> chg.json

# numbers in the saved transcript, by value, 11 Earnings-21 calls
python3 scripts/score_number_fidelity.py --corpus <A>/per-file --json-out chg.json
python3 scripts/score_number_fidelity.py --corpus-compare <pinned baseline> chg.json

# words the recovery layer adds, and the hallucinated rows among them.
# Needs a run decoded with the per-decision record on (MIMICSCRIBE_SEAM_LEDGER=<dir>)
python3 scripts/seam_ledger_verdicts.py align   --run <A> --cache-dir <cache>
python3 scripts/seam_ledger_verdicts.py repairs --ledger <dir> --run <A> --cache-dir <cache> \
    --split all --json-out repairs.json

# invented phrases over silence: its own token-frame arm (16 AMI meetings, ~10 min),
# then the scorer, which also checks the pin (exit 1 = a regression, 2 = not comparable)
scripts/timestamp_merge_ami16_arm.sh <arm>
python3 scripts/invented_phrase_runs.py --arm <arm> --gate benchmark/results/live-transcription-public/pins.json

# duplicate spans across a row boundary, and how many the shipped rule removes
python3 scripts/bakeoff/seam_repeat_false_fire.py --cross-row <A> \
    --bin .build/release/mimicscribe --json-out crossrow.json

# every pin above, checked in one pass; exit 1 = a regression, 2 = not comparable
python3 scripts/gate_live_transcription_pins.py \
    --word-accuracy wer.log --word-accuracy-json wer.json \
    --punctuation punct.log --clumping clump.log \
    --repairs repairs.json --cross-row crossrow.json --number-fidelity chg.json
```

Pin the output directory of each arm explicitly. The scorers default to the newest directory on disk, which silently picks up whatever else has been run since.
