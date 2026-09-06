# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR on CoreML, transcribing in real time from overlapping listening windows.

Run date: 2026-09-02. Corpus: 16 AMI meetings, 8.5 hours, headset mixdown (every speaker's close-talk microphone summed to one channel). Punctuation and casing are measured on 11 Earnings-21 calls, because AMI's references are not punctuated to reference quality. Live display and latency come from 4 recorded capture sessions, a smaller basis, marked as such.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **3.4%** |
| Deletion rate on speech spoken over another speaker | 41.0% |
| Runs of 10+ consecutive words lost, whole corpus | **4** in 8.5 hours, all four at the edge of crosstalk |
| Longest single run of lost words | 14, at a crosstalk edge |
| Sentence-ending punctuation, precision / recall | 86.7% / 83.6% |
| Sentence ends preserved at speaker handoffs | 94.3% |
| Sentence starts rendered capitalized | 84.8% |
| Text shown as final that later changed | 0.33% |
| Time from you stopping speaking to the text being final | 6.9 to 9.9 s |
| Same audio twice, same transcript | byte-identical |

The first two rows are the pair to read together, and they are explained below.

## Word accuracy

Measured against the human reference over the whole transcript, full vocabulary, no filler stop-list. Reference: 81,198 tokens across the 16 meetings, after both sides go through the same number-and-acronym normalizer the saved transcript itself goes through (the note below the table says why).

| | previous build | current | change |
|---|---:|---:|---:|
| Reference words deleted | 11,944 | 11,944 | 0 |
| Words inserted that the reference lacks | 3,379 | 3,379 | 0 |
| Words substituted | 4,072 | 4,060 | −12 |
| Composite error rate | 23.89% | 23.87% | −0.02 points |

Flat. Not a word more deleted and not a word more inserted across 8.5 hours; twelve fewer substitutions is the whole difference this release makes to meeting recognition, and the table says so. Those twelve are a guard shipped in this release: the code that stitches two decoding windows together used to let a word be written with a fragment of itself attached ("Turningning"), and it now refuses that stitch. It removes a wrong word rather than adding a right one, which is why it shows up as substitutions and nowhere else. Both halves of the table are still published because the deletion count alone is worth nothing: a decoder that invents words to fill gaps improves it while making the transcript worse, and the only thing that distinguishes the two is watching insertions at the same time. On the earnings calls the same build moves a little further: deletions 1,619 → 1,617, insertions 1,882 → 1,876, error rate 8.44% → 8.41%.

**What changed in how words are counted.** The saved transcript writes numbers, money, percentages and spelled acronyms the way a reader expects ("2020", "$115 million", "5%", "DNLG"), while the human reference spells them out ("twenty twenty", "D_N_L_G_"). Until the release before this one, the reference was compared as written, so every correctly transcribed number or acronym scored as one or more errors — a bias that grew the moment the transcript started normalizing its own rows, and read as a loss of 327 words on the pair it was first caught on. Both sides now go through the transcript's own normalizer before counting, which is why the reference is 81,198 tokens rather than 81,826. The old counting is kept as an option and reproduces the older pages' numbers to the digit; the scorers print which basis they used and the regression gate refuses to compare across the two.

**And the previous-build column is re-scored, not quoted.** It is the previous release's own decode, put through today's scorer beside this build's decode, so both columns are one scorer and one basis. That matters most on the earnings calls: this page's previous column reads 1,619 deletions, which is exactly what the last page published as its *current* number, while that page's own previous column read 1,636. Nothing was re-decoded in between. The normalizer runs from the binary present at scoring time, so re-scoring an unchanged directory can move the earnings-call column as the number and acronym rules change, and it moves AMI far less because AMI has far fewer of those sites. Quoting a stored number instead of re-scoring the arm would have hidden that shift inside a build comparison.

**We do not publish an absolute word error rate from this instrument.** The AMI reference is the time-ordered union of every speaker's channel, so where two people talk at once it interleaves words no single-stream decoder can emit in order, and each scores as an error however good the recognizer is. That bias is large and constant across builds, which is why the change is meaningful while the level is not.

### How hard the assignment is

| | previous | current |
|---|---:|---:|
| Reference words spoken over another speaker | 30.1% | 30.1% |
| Deletion rate within overlapped speech | 41.0% | 41.0% |
| Deletion rate on clean speech | 3.4% | 3.4% |

Nearly a third of the words in this corpus are spoken over somebody else, and inside that population deletion runs at 41.0% against 3.4% on clean speech. That gap is close to a statement about physics: one mixed channel, two simultaneous talkers. It is also why individual meetings spread so widely — the argumentative EN sessions lose far more than the ES sessions, which is the crosstalk rate showing through rather than a difference in transcription quality.

The clean-speech figure is the recognition-quality signal, and the one to read for what the recognizer does when given a fair chance.

## How badly do losses clump

A hundred scattered single words is a transcript you can read. One 24-word run is a missing paragraph or exchange. Clean speech only:

| Consecutive words lost | previous | current |
|---|---:|---:|
| 1 word | 1,749 | 1,747 |
| 2 to 4 words | 471 | 470 |
| 5 to 9 words | 30 | 30 |
| **10 or more words** | **4** | **4** |
| Longest single run | 14 | 14 |

Flat: four runs of 10+ words on both builds, the longest 14 words on both, and the two shorter buckets move by two words and one run.

**Where the four are.** The same four sites on both builds, at the same lengths: EN2006b and ES2008c at 14 words, EN2002a at 13, ES2016a at 10. Each begins or ends within a second of a word two people spoke at once, against 41% for single-word losses. Long losses concentrate at crosstalk rather than spreading through ordinary speech. Overlapped speech itself is scored separately and excluded from this table.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | previous | current | |
|---|---:|---:|---|
| Sentence-ending precision | 86.6% | 86.7% | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 83.6% | 83.6% | of the sentence ends a human wrote, the share found |
| Boundary recall | 94.3% | 94.3% | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 84.8% | 84.8% | of real sentence starts, the share capitalized |
| Capitalization precision | 89.3% | 89.3% | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

Fractions of a point, in the good direction, and the table is rounded so most of the movement does not survive the rounding. Underneath it: two more sentence ends placed where a human placed one, three fewer placed where none belonged. Nothing was traded for it — the counts that would have paid for it are identical on both builds: 750 sentence ends missed, 39 speaker handoffs left without a sentence end, 847 wrong capitals, 1,087 sentence starts left lowercase. The hard floors are the recall rows, and they are equalled rather than beaten. Boundary recall moved by one ten-thousandth with the miss count unchanged, which is the denominator moving by one handoff and not a boundary recovered; the floor of 94.3% set by the last release still stands.

Terminal punctuation is not cosmetic here. Sentence boundaries become the windows used for speaker embedding, so a punctuation change is also a speaker-identification change, which is why recall carries a hard floor rather than being traded for precision.

## Live display stability

"Text shown as final stays final." The display commits in two tiers and the promise attaches only to the committed tier.

| | |
|---|---:|
| Committed text that later changed | **0.33%** |
| Provisional tail text that later changed | 5.76% |
| Words the renderer dropped entirely | **0** |
| Revisions inside the trailing 60 s, per corpus | 393 (71% single-word) |

The roughly 17x gap between the tiers is the entire case for showing them differently. The committed number was 0.39% before a faster commit policy, rose to 0.65% deliberately when that policy roughly halved the time to a final transcript, and was 0.33% at the last recording — with the time to a final transcript having given part of that speed back (next section). Both halves of that trade are published, in both directions.

Basis: 4 recorded capture sessions, not the 16-meeting corpus. **These two sections are carried forward from the previous release, not re-measured for this one.** They replay recorded sessions rather than scoring a corpus, so refreshing them means re-recording, and nothing in this release changed the display path enough to spend that. They keep the commit and the date of the recording that produced them, which is why the provenance table below stamps them `ecce55f3` / 2026-08-29 while every re-measured axis moved on. A restamped date on an unrepeated measurement is exactly the kind of number this page exists not to publish.

## Latency to trust

How long after you stop speaking until the words stop moving.

| Capture | Pauses measured | Median pause to commit |
|---|---:|---:|
| ES2004a | 50 | 9.9 s |
| IS1009b | 33 | 7.6 s |
| IS1009c | 56 | 8.8 s |
| TS3003a | 81 | 6.9 s |

**6.9 to 9.9 s**, against **4.5 to 7.6 s** at the recording before it and **10.3 to 11.0 s** under the earlier commit policy. This is the number on this page that moved the wrong way at the last release: each session waits 1.4 to 3.2 s longer for its text to stop moving than it did on the previous recording, while committed text changes half as often. Which change is responsible has not been isolated, and this release did not re-record the sessions, so the figure stands where it was last measured. It is the open item on this page.

## The live view against the script

Everything above scores the final transcript. These rows score what is on
screen while you speak: seven two-channel recorded sessions (mic plus system
audio, 32.9 minutes) replayed through the full live pipeline, the rendered
transcript sampled once per second. The duplication rows need no reference —
a span shown twice back to back is a defect whatever was said. The rest are
checked against the session's script as performed.

| | |
|---|---:|
| Doubled phrases (4+ words) visible in the live view | **2 episodes** in 32.9 min |
| Short duplicated spans, punctuation-identical ("on Friday. on Friday.") | **4 episodes** |
| Words shown fused with a fragment of themselves ("Turningning") | **0 episodes** |
| Words shown that were never spoken | 664 |
| Spoken words that never appeared on screen | 162 |
| Already-shown words rewritten under the reader (flicker, case counts) | 642 of 4,940 shown, **13.0 per 100** |
| Punctuation changed on words that stayed | 364, **7.4 per 100** |
| A short repeat ("short short") that reached the saved transcript | 19 |
| The other speaker's words appearing on this channel's row | 10 episodes, 0 saved (tracked, not gated) |
| A bare fragment of a word ("ight") on screen | 12 episodes, 7 saved |

Replayed 2026-09-05 on build `93d9a7d3`. The flicker rows count what the
reader saw BETWEEN RENDERS, so a display that refreshes faster shows more
intermediate states and scores higher, and the gate refuses to compare two
builds at different cadences. This build refreshes on the same 1.5 s floor
as the last two and reads 13.0 and 7.4 per 100 against 13.1 and 7.9 on
the previous build (and 20.1 and 12.2 two builds ago). What changed on
this build: the live view now keeps the first spelling it showed for a
word the normalizer would otherwise re-render with a hyphen in a different
place ("cost cutting" / "cost-cutting", "mid July" / "mid-July") until the
word is final — a hyphen never changes what was said, so that class of
rewrite (68 of the 649 on the last build) is mostly gone (46), and the
punctuation row fell with it. Sentence casing gained the row-end cases a
review found missing ("The year was 2016." now ends a sentence for the
row after it). Two other changes were built, measured on these sessions,
and NOT shipped: moving backchannel paragraph breaks earlier (measured
gain 0.8 s median, not the 7 s first estimated) and keeping speaker badges
across a re-timed row (it removed the "You" badge from every mic row and
produced a badge that later changed name).
The "other speaker's words" row is tracked only: every one of its 10
episodes on this build is two people saying the same two words within a
second of each other, which row-level timing cannot tell from bleed. The
bare-fragment row lost the one episode that named it ("ight", on screen
for four minutes of one session) and gained a real word the dictionary
lacks ("nah").

The last two rows are scored on the five sessions with a verbatim script
(24.2 minutes, 3,337 script words) and count every distinct rendering that
ever appeared, including provisional text later corrected — and a misheard
word charges both rows at once, so they are dominated by ordinary
misrecognitions. They are regression bars, not quality claims: what they
exist to catch is a build that makes the live view invent or withhold more
than this one does.

Transcription reads overlapping windows of audio, and where two windows are
stitched a word can be rendered with a piece of itself attached. **This is the
one class this release set out to close.** A guard now refuses the stitch that
produced them, and the count is zero on all seven sessions, in the live view
and in the final transcript alike; the same guard is what removes the twelve
substitutions in the word-accuracy table above. Zero was also the count on the
last run, so the seven sessions do not prove the fix on their own — the
substitution count on 8.5 hours of meetings is what carries that. The check
needs the system word list to run at all, and reports nothing rather than
guessing when it is absent — several hundred ordinary English words have the
same shape as a fusion, so counting them without a dictionary would produce
noise.

The doubled-phrase row did not move and the short-duplicate row reads four;
neither carries a change. Replaying the same recording twice moves counts
like these by more than two. They are the values the next release is
measured against, not a result.

**New this release: text that vanishes and comes back.** A separate counter
watches for the live view getting *shorter* — a chunk of words disappearing
from the screen and returning a moment later, which no other row here can see
(the loss rows score the settled text, and a word withdrawn and restored never
leaves the union of everything ever shown). **3 on this build's published
replay, 4 on its twin; 2 pinned** — this counter is the noisiest row on the
page and the range is the honest reading of it. The published replay has
three episodes in two of the seven sessions, the worst removing 5 words and
the longest absence 32 s. Two replays of one binary is a small sample, and
the spread across them is as large as the whole count, so read the row as
"a handful per half hour of replay" and not as a value. The pin is the
number a regression has to get past, not a measurement of the build. Part
of this class is the renderer and was fixed two releases ago; the rest is
upstream of the display and is open.

### Numbers on screen

Spoken quantities are checked by value rather than spelling, so "$115 million"
and "one hundred and fifteen million dollars" count as the same number.

| | |
|---|---:|
| Spoken quantities that reached the screen intact | 136 of 144 |
| Rendered as a different quantity | 1 |
| Dropped | 7 |
| Numbers shown that nobody said | 2 |
| Numbers damaged where two decoding windows were stitched | 0 in the final view |

One of the five scripted sessions is a numbers-heavy earnings call and carries
58 of the 144; the other four are conversational and carry 17 to 24 each. This
is a thin basis for a number-accuracy claim and is published as a regression
bar, not as a quality figure.

These five rows are also scored by a newer version of the number scorer than
the ones beside them on the last page, which is why the count of quantities
scored moves from 146 to 144: it stopped charging a name that contains a digit
("Form 10-K" written "Form ten K") as a wrong number. Two columns scored by two
different scorers are not a build comparison, so nothing is claimed from the
dropped and invented rows falling; they are re-pinned and the next release is
measured against them.

### Numbers in the saved transcript

The live view is one pass over the audio; the transcript you keep is the one
that matters. The same by-value check is run on the saved transcript of the
11 Earnings-21 calls against Rev.com's human references — 2,857 spoken
quantities, the densest public substrate for numbers we have.

| | previous build | current |
|---|---:|---:|
| Spoken quantities that reached the saved transcript intact | 2,769 | **2,777 of 2,857 (97.2%)** |
| Rendered as a different quantity | 39 | 39 |
| Dropped | 49 | 41 |
| Numbers in the transcript that nobody said | 70 | 66 |

By kind of number, on this build:

| | scored | intact | different | dropped | nobody said |
|---|---:|---:|---:|---:|---:|
| Plain counts and amounts | 1,027 | 979 | 23 | 25 | 45 |
| Money | 363 | 351 | 9 | 3 | 3 |
| Percentages | 406 | 401 | 5 | 0 | 2 |
| Years | 310 | 306 | 1 | 3 | 0 |
| Fiscal quarters | 442 | 439 | 1 | 2 | 2 |
| Ordinals | 235 | 225 | 1 | 9 | 13 |

Eight quantities recovered, eight fewer dropped, four fewer invented, and not
one more figure rendered as the wrong quantity: this is where the release's
number work shows up, and it is the largest movement on the page. Where two
decoding windows are stitched, the same figure read
as digits on one side and as words on the other used to be kept twice or cut in
half; that class is now five across the corpus, against six on the previous
build. Where a human reference truncates a year ("first quarter of 201."), a
transcript showing the full year is counted as correct; the two such years this
transcript did not match are reported and not scored.

Both columns are scored by the same scorer, on the previous release's own
decode and this one's. That scorer is newer than the one the last page used,
and the change is large enough to say out loud: on the *same* previous decode,
the older scorer read 2,867 quantities scored, 59 dropped and 112 invented
where today's reads 2,857, 49 and 70. It stopped charging four things as wrong
numbers that a reader would not call wrong — a digit inside a name the two
sides write differently ("Form ten K" against "10-K"), a unit only one side
spells out ("15" against "15%"), "9-11" and "24/7", and a stitch-point shape the
speaker actually produced. None of the 39 wrong figures was excused. Read the
drop from 112 to 66 as two steps: 42 of it the scorer and 4 of it the build.
The columns above are the build alone.

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
| Words added per meeting-hour | 84.1 | 84.1 |
| of which the reference supports | 63.3 | 66.1 |
| **of which wrong** | **20.9** | 18.1 |
| Precision | **75.2%** | 78.5% |

27 files, 18.83 hours. The repair pass added
1,619 words and 1,584 of them reached the saved
transcript; the table is over those, because they are the ones anybody
read.

**Added and later removed: 35.** 35 of the added words were taken
out again by a later pass before anything was saved, so no reader ever
met them. They are not wrong words on a page; they are the repair pass
producing text something else had to clean up, which is a different
thing and is counted as its own line rather than folded into the rate
above. Folded in they would add 1.86 to the wrong-words row.

The left column is the headline. Both definitions ask whether an added
word belongs; they differ in what counts as belonging. The right column
asks only whether the same word was spoken within a second, so a repair
word standing where a different word was said reads as correct there.
279 of the added words are exactly that, and a reader
sees every one of them as a wrong word. The left column resolves each
added word through the same alignment the error counts above use, which
is why it is the one pinned.

By repair class, on the headline definition:

| | added | supported | wrong | precision |
|---|---:|---:|---:|---:|
| The stitch between two decoding windows | 301 | 232 | 69 | 77.1% |
| Silence the decoder left over voiced audio | 1,283 | 959 | 324 | 74.7% |

This is published as a regression bar and not as a quality claim. The
measured admission rules that would raise the precision were all
refuted on held-out files, so the number is what the shipping
configuration does, stated rather than improved.

*Basis: 27 files, 18.83 hours, measured at `5b3e5c23` on a ledgered run. This is a different arm from the word-accuracy and punctuation rows above, which is stated here rather than left to provenance; see the provenance table.*

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
| All-wrong runs per meeting-hour | **5.63** | 5.20 |
| Words in them, per meeting-hour | **8.98** | 7.97 |
| Of 3 words or more, per meeting-hour | **0.85** | 0.74 |

106 all-wrong runs of 424 runs on the headline
definition, carrying 169 words, 16 of the runs three
words or longer, over 18.83 hours. The three-word row is the one that
matters to a reader: a one-word all-wrong run is an ordinary
misrecognition, and a three-word one is a sentence fragment nobody said.

Counted by whole repair DECISION rather than by run, the same rows read
22 all-wrong decisions of 104
(21 on the surface definition). That count is
smaller because one decision that gets a word right anywhere rescues
every fragment of itself, including a fragment several seconds away with
nothing right in it. The per-run count is what is pinned, for that
reason; the per-decision count is given so the two are not confused.

These counts are over all 1,619 added words. The section above is over
the 1,584 of them that reached the saved transcript, because its question
is what a reader met; this one's unit is a repair decision's own
fragment, so it counts the phrase the pass produced whether or not a
later pass took it out again.

7 of the 106 all-wrong runs are made entirely of words a later
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

*Basis: 27 files, 18.83 hours, measured at `5b3e5c23` on a ledgered run. This is a different arm from the word-accuracy and punctuation rows above, which is stated here rather than left to provenance; see the provenance table.*

## Invented phrases over silence

The section above scores what the recovery layer adds. It cannot see text the
decoder itself writes over a stretch of room tone. This row scores that
directly: runs of three or more words with no reference word at their time,
over a span more than 25 dB quieter than the meeting's own speech. The energy
test is what separates a fabricated phrase from a passage the annotators never
transcribed; on these meetings the latter are nine runs in ten and are not
counted.

| | previous release | this release |
|---|---:|---:|
| Invented phrases over silence, per meeting-hour | 2.00 | **2.23** |
| Words in them, per meeting-hour | 14.3 | **15.4** |
| Of them in the last 15 seconds of a file | 2 | **2** |

19 runs over 8.5 hours, one every 27 minutes. A decoder reads something
into silence at some rate; this row is that rate for the primary decode,
published beside the recovery layer's so the two are not confused. Before
this release a window rule on the main branch had raised it to 2.47; the
fix brought it back to 2.23. The two runs in the last 15 seconds of a file
come from the final decode of a recording and are pinned on their own.

*Basis: 16 AMI meetings, 8.51 hours, one decode per arm at `7476b3bd0` and at
the previous release, on its own token-frame arm.*

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
| under 10x | 24 | tracked |
| 10x to under 1,000x | 11 | tracked |
| 1,000x or more | 4 | tracked, see below |

39 corruptions in total, neither more nor fewer than that row.
The ratio is folded, so an amount rendered a thousand times too
large and one rendered a thousand times too small count the same.

**The bottom row is tracked, not a bar, and here is why.** It is a split
of a comparison against reference entities, not a count of wrong figures
a reader would meet, and most of what is in it is the comparison rather
than the transcript. Every member, named:

| the reference says | the transcript says | what it is |
|---|---|---|
| `$40 billion` | `$40 million` | a real disagreement about the scale word at the site |
| `three` | `three three and a half million` | scorer artifact: a disfluency paired as one entity |
| `$7.5 million` | `$7.5` | scorer reading: `millionars` does not parse as a scale word |
| `14` | `14 million` | the reference names no scale at the site |

One of them is a real disagreement about a scale word. The others are the
scorer pairing a disfluency as one entity, a scale word it cannot parse,
and a reference that does not name the scale at the site at all. Counting
those as regressions would gate future releases against the reference's
coverage and the scorer's tokenizer, so the row is published and not
enforced.

**What is enforced instead** is the narrower question the row was
reaching for: a figure where the transcript and the reference both name
a scale and name a different one. That is one site on this corpus, it is
the same one on both measured builds, and it is pinned at 1
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
| Word accuracy (16 AMI meetings) | 16 | 9 | 1 | 6 |
| The earnings-call counterexample (11 Earnings-21 calls) | 11 | 9 | 0 | 2 |
| Both corpora together (27 files) | 27 | 18 | 1 | 8 |

Scored on each file's own error rate, on the same normalized basis as
the word-accuracy table. `unchanged` is exact equality: on a
deterministic substrate a file that does not move did not move at all.

The one file that moved the wrong way is `EN2006b` (the one worse file; first read as the merge guard's second-order site, later shown to be three correct reference words recovered by the batch voiced-hole repair, so the +3 insertions are a scorer reading of an interleaved AMI reference, not the guard's cost), by 0.03 points.

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

Same audio in, byte-identical transcript out, verified rather than asserted. This build decoded all 27 files twice and the two runs agree byte for byte on every one of them. That closes the one form of the check this page had never done: the standing evidence was two independently compiled binaries, built from different trees, producing byte-identical output across the 16 meetings — identical not only in text but in per-token frame indices — which is stronger against compiler and layout effects and says nothing about running the same binary twice. Both now hold.

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
| Word accuracy, loss clumping, crosstalk split | `5b3e5c23` | 2026-09-02 | 16 AMI meetings |
| Sentence punctuation and casing | `5b3e5c23` | 2026-09-02 | 11 Earnings-21 calls |
| Determinism | `5b3e5c23`, decoded twice | 2026-09-02 | 27 files (16 AMI + 11 Earnings-21) |
| Live display stability | `ecce55f3` | 2026-08-29 | 4 capture sessions, **carried** |
| Latency to trust | `ecce55f3` | 2026-08-29 | 4 capture sessions, **carried** |
| Live view against the script | `93d9a7d3` | 2026-09-05 | 7 capture sessions (script rows: 5), debug build |
| Numbers in the saved transcript | `5b3e5c23` | 2026-09-02 | 11 Earnings-21 calls (2,857 quantities) |
| Words the recovery layer adds | `5b3e5c23` | 2026-09-02 | 27 files, 18.83 hours, ledgered run |
| Hallucinated rows | `5b3e5c23` | 2026-09-02 | the same ledgered run |
| Invented phrases over silence | `7476b3bd0` (previous release `5c847cf5`) | 2026-09-06 | 16 AMI meetings, 8.51 hours, its own token-frame arm |
| Wrong figures by magnitude | `5c847cf5` | 2026-08-29 | the previous release's 39 corruptions, split by ratio |
| Saved-transcript duplicates | `5c847cf5` | 2026-08-29 | 27 files, 18.83 hours |
| Per-file sign counts | `5b3e5c23` | 2026-09-02 | this page's own pair of arms, 27 files |
| *Corpus arm tree state* | `1469c502`, **`git_dirty: true`** | 2026-09-02 | byte-identical to the clean run `swift_pipeline_cand_5b3e5c23` (`854fdfdd`), all 108 per-file dumps — see below |

**Two rows are a release behind the rest.** The magnitude split and the
duplicate-span rate are decompositions of numbers this page publishes, and they
are still computed from the previous release's arms: the split reads that
release's stored per-figure detail. The duplicate rate reproduces identically on
both builds, so its age costs nothing; the split is a release stale and is
marked here rather than quietly restated against numbers it was not computed
from. The next full run re-takes both beside everything else.

**The sign counts were one of those rows until 2026-09-02, and were wrong
because of it.** They decomposed the *previous* release's change column (rc.26
to rc.27) while sitting under this page's deltas, and read 11 better / 7 worse /
9 unchanged. Re-derived on the two arms this page actually compares, they read
18 / 1 / 8. The old triple was a correct measurement of a pair the page does not
publish, which is exactly the failure mode this table exists to catch.

**The live-view row is a debug build.** Replaying a recorded session through
the live path needs one, and it is stamped with the commit that actually ran:
`73bfd2f8`, which differs from the shipped `5b3e5c23` by a scorer and some
documentation and by no application code at all.

**The corpus arm's manifest reads `git_dirty: true`, and here is what that does
and does not mean.** The run that produced every word-accuracy, clumping,
punctuation and number figure on this page
(`swift_pipeline_2026-09-02T125210Z`, stamped `1469c502`) was decoded from a
tree with an uncommitted change: the 08-29 live-invariants pin file, edited
while the decode was running. A dirty tree is normally enough to disqualify an
arm, because nobody can say afterwards what was in it. Here it can be settled by
comparison rather than by assertion. A second run of the same corpus,
`swift_pipeline_cand_5b3e5c23`, was decoded three hours earlier from a CLEAN
tree (`854fdfdd`, `git_dirty: false`), and its dumps are byte-identical to the
page arm's — all 108 per-file dumps, the 27 the scorers read included:

```bash
for f in benchmark/output/swift_pipeline_2026-09-02T125210Z/per-file/*; do
  cmp -s "$f" "benchmark/output/swift_pipeline_cand_5b3e5c23/per-file/$(basename "$f")" \
    || echo "DIFF $f"
done   # 108 files compared, no output
```

So the uncommitted edit did not reach the transcript, and it could not have: it
was a JSON pin read by a scorer, not by the decoder. The dirty flag is reported
rather than quietly dropped because a reader checking the manifest would
otherwise find it and have no way to tell which kind of dirty it was.

The previous-build column is the previous release's own decode — 2026-08-30, `dfe0677e`, the tree of v1.0.0-rc.27 — re-scored beside this one. On both corpora it reproduces the last page's published *current* column to the digit (AMI 11,944 deleted / 3,379 inserted / 4,072 substituted at 23.89%; Earnings-21 1,619 and 1,882 at 8.44%), which is what makes the arm a valid comparator: one scorer, one basis, and the differences reported are the build.

Every row carries a commit. The display-stability and latency rows carried none until the previous refresh: those campaigns pinned dates and capture stamps but not a commit, and the page reported them as unrecorded rather than backfilled with a plausible guess, because a guessed commit is indistinguishable from a verified one once written down. They keep `ecce55f3` here because that is the build their recording ran on, and this release did not re-record them.

Model: `parakeet-tdt-0.6b-v3`, CoreML, Apple Silicon.

## Pins

The values the next release is measured against. A pin is not a target; it is the number a regression has to get past unnoticed, and publishing it is what stops that happening quietly.

| Pinned value | Class | Pin |
|---|---|---:|
| Renderer dropped words | must not worsen | 0 |
| Runs of 10+ consecutive words lost | must not rise | 4 |
| Longest single run of lost words | must not rise | 14 |
| Reference words deleted | regression bar | 11,944 |
| Words inserted | regression bar | 3,379 |
| Clean-speech deletion rate | regression bar | 3.4% |
| Committed text later changed | ceiling 1.0% | 0.33% |
| Sentence-ending recall | must not worsen | 83.6% |
| Boundary recall at speaker handoffs | must not worsen | 94.3% |
| Sentence-start capitalization | regression bar | 84.8% |
| Doubled phrases visible live | regression bar | 2 |
| Punctuation-identical duplicated spans | regression bar | 4 |
| Words shown fused with a fragment of themselves | regression bar | 0 |
| Words shown never spoken | regression bar | 664 |
| Spoken words never shown | regression bar | 162 |
| Live text withdrawn and restored | regression bar | 6 episodes |
| Already-shown words rewritten (flicker), per 100 shown | regression bar, same refresh cadence | 13.0 |
| Punctuation changed on unchanged words, per 100 shown | regression bar, same refresh cadence | 7.4 |
| Short repeats reaching the saved transcript | regression bar (7-session sum of rises) | 19 |
| Other channel's words on this channel's row | tracked (row timing cannot separate bleed from coincidence) | 10 |
| Bare word fragments on screen | regression bar | 12 |
| Spoken quantities rendered as a different quantity | regression bar | 1 |
| Spoken quantities dropped | regression bar | 7 |
| Numbers shown that nobody said | regression bar | 2 |
| Saved-transcript quantities rendered as a different quantity | must not rise, per call | 39 |
| Saved-transcript quantities dropped | must not rise, per call | 41 |
| Saved-transcript numbers nobody said | must not rise, per call | 66 |
| Figures where the scale word disagrees | must not rise, tolerance 0 | 1 |
| Wrong words the recovery layer adds, per hour | regression bar | 20.9 |
| Added words removed again before saving, per hour | tracked | 1.86 |
| Hallucinated runs per hour | regression bar | 5.63 |
| Words in them, per hour | regression bar | 8.98 |
| Of 3 words or more, per hour | regression bar | 0.85 |
| Invented phrases over silence, per hour | regression bar | 2.23 |
| Words in them, per hour | regression bar | 15.4 |
| Of them in the last 15 seconds of a file | must not rise | 2 |
| Duplicate spans per hour | tracked | 2.34 |
| Decodes added to the product path | declared before it ships | none |
| Determinism | must hold | byte-identical |

The live-view bars are enforced per session with a measured tolerance for
replay timing jitter (the same recording replayed twice moves the word
counts by a few dozen), plus a tighter cap on the total across sessions —
uncorrelated jitter and a systematic regression separate cleanly there.

The live-view rows were re-measured on the same seven sessions at this build,
this time with each session replayed twice so the jitter above could be
measured rather than assumed: duplicated spans 3 to 5, fusions 0 to 0, the two
script rows 718 to 720 and 166 to 163, speaker handoffs without a sentence end
unchanged at 11 across the seven, and the number rows re-scored by the newer
scorer described above. Every one of those movements is inside the replay
jitter, so no change in either direction is claimed from them; they are the
values the next release is measured against. The withdraw-and-restore counter
is pinned here for the first time.

Three rules govern how these may be read, and each exists because ignoring it produced a wrong published number here at least once:

1. **A number is only valid for the configuration that ships, on the corpus it claims.** Two numbers on an earlier version of this page were not: one set was five weeks stale, the other came from a policy reachable only by disabling the shipping one. Both read exactly like current numbers. A third case was caught before it reached this page — a punctuation figure computed over 2 of the 11 calls — which is why the gate now checks how many files produced a number before comparing it to anything.
2. **Deletion-only measures never appear alone.** A mechanism that recovers words by inventing them improves every deletion count here, so insertions are published beside deletions or neither is published.
3. **An unchanged result must be proven to have run.** A cached decode once reported an entire change as having no effect with every gate green. Both arms above reported a fully cold decode, and an arm that reports no cache misses is discarded rather than believed.

Every number on this page is produced by a committed script that a later release can re-run. An earlier version carried a family of figures whose analysis code was never committed and whose input was not archived, which meant they could never be checked for drift; they were removed rather than restated.

## Reproducing

The scorers are the same ones that gate changes internally, unmodified — there is no public-only scoring path.

```bash
# every axis below in one command, each compared against its committed pin.
# This is what produced the numbers on this page.
scripts/live_transcription_benchmark.sh <out-root> --baseline <previous arm> --determinism

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
