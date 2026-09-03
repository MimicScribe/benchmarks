# ASR Model Bake-off — September 2026

Measured 2026-09-01. This is a dated report, not a leaderboard: the arms are the
models that existed when it was run, the numbers are stamped with the runtime
and revision that produced them, and nothing here is re-run when a new model
ships.

The question is narrow. MimicScribe transcribes meetings on-device with NVIDIA
Parakeet TDT 0.6B v3 through CoreML. Would a different acoustic model cut the
error classes a reader actually judges a transcript on — wrong figures, words
that were never said, dropped turns — by more than tuning the pipeline around
Parakeet can? Four models — Parakeet v3, Parakeet v2, Cohere Transcribe and
Granite Speech — were decoded over one corpus, through their own runtimes and
through ours, and graded two ways: word error rate, and a blind rubric judge
that reads the transcripts against the human reference.

The answer is that no model dominates, that the model the product ships is the
balanced arm, and that none of the alternatives is a replacement.

## How to read the numbers on this page

**These error rates are comparisons, not scores.** The AMI reference is the
time-ordered union of every speaker's channel, so where two people talk at once
it interleaves words that no single-stream decoder can emit in order, and each
one counts as an error however good the recognizer is. That bias is large, and
it is the same for every arm decoded from the same audio against the same
reference. So the *differences* between the arms below are meaningful and the
*levels* are not. None of these figures is comparable to a word error rate
published anywhere else, including the ones the model cards carry.

**The like-for-like comparator for an external model is the Parakeet v3
FluidAudio batch arm, not the shipping pipeline.** The product's number
(15.46%) is the pipeline as it runs on a file import: it includes recovery
layers that run around the model — repair at the join between two decoding
windows, and a second look where the decoder emitted nothing over voiced audio.
(In a live meeting the second of those is off by default as of 2026-09-02; the
first runs on both paths.) The vendor batch path with the same model and no
such layers reads 16.37%. The difference, 0.92 points, belongs to the pipeline
and not to Parakeet, so charging it against Cohere or Granite would overstate
their gap by that much. Both rows are published in every table, and each
comparison in the prose names which row it is drawn against.

**Verbatim error rate measures verbatim-ness first.** Cohere is a
non-verbatim transcriber scored against a verbatim reference, which charges it
for every filled pause it declines to write down. A re-score on two
looser bases is published below for that reason, and it halves some of the
gaps.

**Realtime factors are not published.** The arms ran under different amounts of
contention for the same hardware, so the per-file spread is a measurement of
what else was running. An interleaved re-measure on an idle machine is owed
before any latency claim, and none is made here.

## Corpora

27 files, 178,703 reference words, 18.8 hours of audio. Every arm decoded all
27 except where noted.

- **[AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)** (CC BY 4.0),
  16 meetings, 81,198 reference tokens. The stream is the AMI headset mixdown
  (`Mix-Headset`): all speakers' close-talk headset microphones summed to one
  channel, so overlapped speech is fully present but there is no room
  reverberation. It is not a distant tabletop array, and a figure measured on it
  is not comparable to one measured on the array streams. Which stream the local
  files hold was established byte for byte, and the method is in
  [CORPUS.md](CORPUS.md).
- **[Earnings-21](https://github.com/revdotcom/speech-datasets)**, 11 earnings
  calls with Rev.com human references, 97,505 reference tokens. Prepared
  remarks read from a page, and the densest public substrate for spoken
  numbers we have.
- **Held-out recorded sessions** — our own two-channel captures, with a
  performed script as the reference. Used for the Granite arm only, because
  Granite's card names AMI in its training set. We cannot redistribute this
  audio, so those rows are the one part of this report a reader cannot
  reproduce.

Every file is fetched from its publisher and verified by hash;
[CORPUS.md](CORPUS.md) carries the licences, the per-file hashes and what is and
is not redistributable.

The crosstalk share of the AMI corpus, and what it does to deletion rate, is on
the live-transcription page rather than restated here:
**[MimicScribe live transcription benchmark](../live-transcription/results/RESULTS.md)** —
what the shipping pipeline does on these same corpora, axis by axis, with its
own pins.

Both sides of every comparison go through the same number-and-acronym
normalizer the saved transcript itself goes through, so a correctly transcribed
"$115 million" is not charged as an error against a reference that spells it
out. The word-error tables apply that normalizer to both sides at scoring
time; for the number table and the judge, every arm's rows were put through the
same normalizer once, line for line, before scoring, so all three instruments
read the same text.

## Parakeet v3 against Parakeet v2

The prior worth testing was that v2, the English-only model, is the stronger
English recognizer. It is not, on this material, through either runtime.

27 files, one decode path per row, pooled:

| arm | hypothesis words | error rate | sub | del | ins | vs the product |
|---|---:|---:|---:|---:|---:|---:|
| **Parakeet v3 int8-v2, MimicScribe pipeline** | 170,401 | **15.46%** | 8,797 | 13,563 | 5,261 | |
| Parakeet v3 int8-v2, FluidAudio batch | 168,105 | 16.37% | 8,518 | 15,671 | 5,073 | +0.92 |
| Parakeet v3 stock int8, FluidAudio batch | 166,873 | 16.75% | 8,525 | 16,621 | 4,786 | +1.29 |
| Parakeet v3, NVIDIA NeMo | 164,062 | 16.93% | 8,380 | 18,260 | 3,619 | +1.48 |
| Parakeet v2, FluidAudio batch | 159,059 | 19.50% | 8,040 | 23,224 | 3,580 | +4.04 |
| Parakeet v2, NVIDIA NeMo | 155,572 | 20.22% | 7,473 | 25,895 | 2,764 | +4.76 |

Per corpus, AMI (81,198 reference words) and Earnings-21 (97,505):

| arm | AMI | sub / del / ins | Earnings-21 | sub / del / ins |
|---|---:|---|---:|---|
| Parakeet v3 int8-v2, pipeline | 23.89% | 4,072 / 11,944 / 3,379 | 8.44% | 4,725 / 1,619 / 1,882 |
| Parakeet v3 int8-v2, batch | 25.57% | 3,790 / 13,829 / 3,147 | 8.71% | 4,728 / 1,842 / 1,926 |
| Parakeet v3, NeMo | 24.74% | 3,797 / 14,031 / 2,264 | 10.43% | 4,583 / 4,229 / 1,355 |
| Parakeet v2, batch | 27.63% | 3,814 / 16,095 / 2,528 | 12.72% | 4,226 / 7,129 / 1,052 |
| Parakeet v2, NeMo | 28.49% | 3,511 / 17,747 / 1,872 | 13.33% | 3,962 / 8,148 / 892 |

**v2 is worse than v3 by 3.29 points through NVIDIA's own runtime and by 3.12
points through FluidAudio** (differences are taken from the unrounded rates)**, and both runtimes attribute the whole of it to
deletion** (+7,635 and +7,553 reference words dropped). v2 inserts less and
lacks v3's colloquial spellings, and neither pays for the deletion wall. Two
independent runtimes agreeing on the direction and the size is what settles
this; a single runtime could not, and the first pass at it did not.

**FluidAudio is slightly better than NeMo for both versions** — v3 by 0.56
points, v2 by 0.72 — and better on numbers, so the runtime we ship
disadvantages neither version. Our production runtime is not leaving v3 quality
on the table.

**The confound, named.** Neither runtime chunks the two versions the same
way. The NeMo arms use the window length each model's own card recommends for
long audio, so the v2 arm carries more window joins than the v3 arm. FluidAudio
places v3's window starts on silence and v2's at a fixed stride, because its
chunk-context setting resolves differently for the two versions. Both
asymmetries bias against v2. Two measurements bound how much: swapping
FluidAudio's chunk-context setting on either version made that version worse,
so the placement difference does not explain a 3-point gap; and on the
900-second sample below, where joins are few, v2 ties v3 through FluidAudio,
so joins are part of v2's cost on long audio. The direction and size agree
across two runtimes with different chunking; the exact split between the model
and the joins is not established here.

**The pipeline is worth 0.92 points over the vendor batch path on the same
model**, entirely on deletions: 2,108 fewer reference words dropped. That is
the recovery layer measured against the model it wraps.

**The rebuilt encoder is worth 0.38 points over the stock file**, again all
deletions (950 fewer). FluidAudio's stock encoder file uses a 6-bit
representation; the int8 rebuild is what MimicScribe ships.

### The 900-second sample that got there first

Before the full-corpus arms, a 900-second window of three files was decoded
through NeMo to check whether FluidAudio's v3 path was faithful to the vendor's.
**This is a sample and is published as one** — three files, one window each,
and it does not settle anything on its own.

| arm | pooled | sub | del | ins | one AMI file |
|---|---:|---:|---:|---:|---:|
| Parakeet v2, NeMo | 17.07% | 118 | 225 | 57 | 30.17% |
| Parakeet v3, NeMo, plain card recipe | 22.07% | 117 | 350 | 50 | **45.76%** |
| Parakeet v2, FluidAudio | 17.29% | 129 | 206 | 70 | 30.05% |
| Parakeet v3 int8-v2, FluidAudio | 17.29% | 125 | 194 | 86 | 30.05% |

On this window v2 wins through NeMo by 5 points and ties through FluidAudio,
which is the opposite of what the corpus says — which is exactly why the full
corpus was then run through both runtimes. Two things came out of it.

FluidAudio's v3 emits about 9% more words than NeMo's v3 here, and the question
was whether those are recovered speech or invention. Of the 210 extra words on
the AMI file, **175 align to reference words NeMo deleted**, in long
contiguous runs; the true invention count is single digits.

And the 45.76% is the plain recipe, not a property of v3: NeMo's card
recommends a different attention configuration for long audio, and the plain
pass has none. With the recommended configuration the same runtime reads 24.74%
on AMI over the full corpus, 0.83 points better than FluidAudio there while
1.72 points worse on the earnings calls. The plain-recipe figure is kept here
as what it is — a misconfiguration, published so nobody reads a collapse into
the model.

## Cohere Transcribe 03-2026

A 2B open-weights transcriber, run through the model's own long-form chunker
unmodified, with the decoder prompt the vendor's processor sets by default.

| arm | error rate | sub | del | ins |
|---|---:|---:|---:|---:|
| Parakeet v3 int8-v2, FluidAudio batch (the comparator) | 16.37% | 8,518 | 15,671 | 5,073 |
| Parakeet v3 int8-v2, MimicScribe pipeline | 15.46% | 8,797 | 13,563 | 5,261 |
| **Cohere Transcribe**, six looping chunks re-decoded | **20.36%** | 6,783 | 26,115 | 3,479 |
| Cohere Transcribe, vendor default | 21.11% | 6,910 | 26,129 | 4,680 |

**20.36%, restated from 21.11%.** The first run read 21.11%. Six of its 2,102
chunks, all on AMI, collapsed into a repeated token under the vendor's default
greedy decode — one chunk emitted "Yeah." 206 times — and those six chunks
carry most of the arm's insertion outliers. Re-decoding **only those six** with
a repetition constraint, every other chunk copied byte for byte, removes 1,201
insertions and moves AMI from 30.99% to 29.33%. Earnings-21 does not move and
neither does number fidelity. 20.36% is that patched run and is the figure this
report uses; 21.11% is what the unpatched vendor default produces and is
recorded here because it is what a reader running the Quick Start will get.

The loops are a model characteristic under crosstalk, not a runner bug, which
is why the audit's "no runner defect above 0.3 points" and this 0.75-point
restatement are both true. Turning a repetition constraint on globally is not
the fix: the global probe below used a shorter n-gram than the six-chunk patch
(3 against 5), and it cost 2.4 points on clean speech.

**The whole gap is deletion.** Against the shipping pipeline the patched run deletes
12,552 more reference words while substituting 2,013 fewer and inserting 1,782 fewer,
and it is worse on 26 of the 27 files (median +5.1 points). Part of that is
that it is a non-verbatim transcriber scored against a verbatim reference —
9,134 filled-pause deletions against 4,372 — and part of it is not: it also
drops ordinary words, "the" 610 more times, "you" 588, "know" 399.

**Contamination, checked.** The card names no training sets, and 11 of our 16
AMI files sit in AMI's public train split. The train files and the five
held-out files score the same (30.99% against 30.98%), so no memorization
shows on that split; Earnings-21 was not checked. The Parakeet cards name their
training collections and we have not audited them for either corpus, so the
same question is open for the arms this report favours.

**Verdict: not a replacement.** It deletes too much to stand in for the
recognizer, and it produces no timestamps, so it cannot be used as a second
opinion to fill a gap either. The one cell worth remembering is that it invents
the fewest numbers of any arm, with a wrong-quantity count that ties ours.

## Granite Speech 4.1-2b

Granite's card names AMI in its training set and Earnings22, the sibling of
Earnings-21, as well. **Its corpus numbers are therefore not evidence and are
not published.** It is reported only on the held-out recorded sessions, which
are held out for every arm.

Pooled error rate against the performed script, filled pauses stripped from
every arm:

| channel | Granite | sub / del / ins | Parakeet, live pipeline | sub / del / ins |
|---|---:|---|---:|---|
| system audio (2,047 reference words) | **15.3%** | 100 / 60 / 153 | 15.5% | 102 / 35 / 180 |
| cleaned microphone (770) | 29.7% | 51 / 94 / 84 | **26.4%** | 57 / 26 / 120 |

The comparator here is the live pipeline, the only Parakeet arm run on these
sessions; by the rule at the top of the page that flatters Parakeet, so the
verdict below is the conservative reading. Granite ties on the system channel
with a different error shape — it deletes
where Parakeet inserts — and is worse on the microphone channel. Across nine
name-and-term cells it is the only arm that reads a compliance acronym
Parakeet never does (1 of its 3 occurrences, against 0), and it invented two
name-shaped tokens at turn boundaries, against four of the same class from the
live Parakeet arm.

**Its margins here sit inside its own variance.** Moving the position of the
chunk seam changes 25% of the stitched transcript: 274 words appear at one seam
position only and 69 at the other, with no duplication either way. A tie on one
channel is not a result at that spread. A much longer chunk degenerates into a
repeated sentence, so there is no free way to remove the seams.

One real defect in our stitching of Granite's chunks was found and fixed before
any of this was measured: the aligner anchored deep inside a recurring phrase
and dropped 58 of 98 words on one file. Every Granite figure here is post-fix.

**Verdict: no replacement case.** A tie on one channel, worse on the other, and
in-domain on the corpus. It is kept in this report because its deletion-heavy
error shape is the mirror of Parakeet's insertion-heavy one, and because it
reads a domain acronym Parakeet does not.

The same measurement also covered two Apple on-device transcribers, from a
separate campaign. They are not published here, because their method is not part
of this report and a number without its method is not a comparison.

## Why the verbatim rate overstates the gaps

The same arms, re-scored on two looser bases. Earnings-21 / AMI:

| basis | Parakeet v3, pipeline | Parakeet v2 | Cohere |
|---|---:|---:|---:|
| verbatim (the tables above) | 8.44% / 23.89% | 12.72% / 27.63% | 12.88% / 30.99% |
| filled pauses and backchannels stripped from both sides | 7.94% / 19.96% | 10.00% / 22.26% | 10.07% / 25.08% |
| content words only | 8.61% / 20.02% | 9.39% / 21.59% | 9.11% / 23.75% |

On content words the Earnings-21 gap between the product and Cohere is half a
point, and on Earnings-21 Cohere has fewer content-word substitutions (2,787 against 3,181)
and fewer insertions (636 against 958) than Parakeet, with twice the content
deletions (1,831 against 825). Cohere's AMI column is the unpatched run, which
is the arm this re-score was taken on.

A verbatim rate answers "how much of what was said is written down, exactly."
That is the right question for a meeting transcript and the wrong one for
ranking recognizers against each other, which is why the blind judge exists.

## Numbers

Spoken quantities in the Earnings-21 calls, checked by value rather than
spelling, so "$115 million" and "one hundred and fifteen million dollars" are
the same number.

Every row below was scored on 2026-09-03 by one version of the scorer, on the
same decodes, after every arm's rows had been through the same normalizer
(binary `7fc35acc`). That last step matters more than it sounds: the vendor
batch path writes spoken quantities as words ("eighty percent") where the
pipeline, NeMo, Cohere and the reference write digits, and the campaign's own
2026-09-01 scoring compared them as written. That scoring is superseded.

| arm | scored | intact | wrong quantity | dropped | never said | doubled or spliced form |
|---|---:|---:|---:|---:|---:|---:|
| **Parakeet v3 int8-v2, pipeline** | 2,857 | **2,769** | 39 | **49** | 70 | 6 |
| Parakeet v3 int8-v2, batch | 2,856 | 2,749 | 45 | 62 | 83 | 12 |
| Parakeet v3 stock int8, batch | 2,854 | 2,749 | 45 | 60 | 76 | 11 |
| Parakeet v2, batch | 2,844 | 2,730 | 46 | 68 | 62 | 0 |
| Parakeet v2, NeMo | 2,836 | 2,710 | 35 | 91 | 56 | 1 |
| Parakeet v3, NeMo | 2,847 | 2,681 | **30** | 136 | 57 | 0 |
| Cohere Transcribe | 2,848 | 2,723 | 38 | 87 | **54** | 4 |

*Scored* is the count of reference quantities the scorer could pair for that
arm; a quantity the arm rendered as the same value in a different spelling is
excused and leaves the count, which is why it varies by up to 21 between rows.
The intact, wrong-quantity and dropped columns sum to it. *Doubled or spliced
form* is a rule over the rendered text alone — a quantity written twice, or a
scale word left without its number — and it does not know where any arm's
window joins were; an arm decoded in one long window per file (NeMo v3) cannot
score on it.

The pipeline's merge and repair layers are worth 20 intact figures over the
vendor batch path on the same model: 6 fewer wrong quantities, 13 fewer dropped,
13 fewer invented. Between v2 and v3 the figures do not point one way. Through
FluidAudio, v3 keeps 19 more intact than v2 and drops 6 fewer, with the
wrong-quantity counts tied; through NeMo, v2 keeps 29 more intact than v3
because it drops 45 fewer, while v3 has the fewest wrong quantities of any arm.
Cohere ties the pipeline on wrong quantities (38 against 39), invents the fewest
numbers of any arm, and drops 87 where the pipeline drops 49.

## The blind judge

Word error rate cannot tell a misheard filler from a misstated figure, and both
count as one error. So each arm was also read by a rubric judge that grades
what a person would notice.

**Method.** The shared reference is cut into windows of about 150 reference
words, 40 per corpus, stratified across files. Each window is shown to the
judge as the human reference plus every arm's excerpt of the same span, under
blind letters, so the judge never knows which arm it is grading. It counts four
things per window — figures rendered wrong, names or terms rendered wrong,
dropped content that changes the meaning, content added that was never said —
and rates readability from 1 to 5. Filled pauses, colloquial and dialect
spellings and punctuation were declared non-errors, because they are not what
this is asking about. 15% of windows are graded twice. 80 windows and 92 calls
were sampled and graded; 68 windows and 78 calls survive the anchor check
described below, and those are what the tables report.

The run published here is the fourth. An outside review of the third found
three more ways the harness could charge an arm for something that was not its
transcription, and a fourth turned up while they were being fixed. They are
described here, after the two from the earlier runs, because a reader should
know what a leak in this kind of instrument looks like.

1. **The excerpt was the wrong unit.** Each arm's excerpt was every whole row
   that touched the window, and the pipeline's rows are whole speaker turns
   while the batch arms' rows are short fixed chunks. So the pipeline's arm was
   shown with roughly 170 extra words on each side of the window that no other
   arm carried, and the judge dutifully reported them as a massive amount of
   invented content.
2. **The trim picked the wrong occurrence.** The first fix trimmed the excerpt
   back to a phrase boundary, but chose the earliest and latest occurrence of
   that phrase, which on a long row reopened the excerpt it was supposed to
   close.
3. **The trim had no ceiling.** Run 3 reported a median excerpt of 0.97 of the
   reference window for the pipeline and 0.99 for the batch arms, and that
   median was true. It was also the wrong statistic. Behind it, 27 of 368
   graded cells still ran past 1.5x the window, the worst of them a 1,558-word
   Cohere excerpt against a 150-word window. Every surplus word is content the
   reference window does not contain, so the judge counted it as added — and
   the arms carrying the most of those cells were Parakeet v2 (12) and Cohere
   (6), not the pipeline (3). Run 4 caps every excerpt at 1.5x the window,
   centered on the part that matches, and publishes the maximum and the number
   of capped cells beside the median.
4. **Both judges penalize the third position, and the letters were not dealt
   evenly.** Grading by prompt position rather than by arm, run 3's first judge
   counted added content 0.51 / 0.48 / 0.70 / 0.53 across positions A to D, and
   the second judge 0.88 / 0.89 / 1.63 / 0.73. The random shuffle had put Cohere
   in the penalized position 32 times and Parakeet v2 17 times, so part of what
   read as a difference between arms was a difference between letters. Worse,
   the second judge replayed the first judge's shuffle, so the agreement between
   them was not independent of position either. Run 4 deals the letters by a
   fixed rotation — each arm sits in each position exactly 20 of 80 windows —
   and rotates the second judge's deal by one place, so the two judges never see
   the same arm under the same letter.
5. **The repeated windows were counted twice.** The means were taken over the 92
   calls, not the 80 windows, so each of the 12 windows graded twice carried
   1.15 times the weight of the rest. That is enough to move a published
   ordering: on run 3's own grades, Cohere's added content reads 0.424 against
   the pipeline's 0.435 per call, and 0.481 against 0.444 per window. Run 4
   averages a window's two passes before averaging the windows.
6. **Twelve windows were never anchored at all.** The harness locates each arm's
   excerpt by matching text, and on 12 of the 80 windows it matched at least one
   arm to a different stretch of the same meeting. Both judges say so in their
   own notes — "completely unrelated to the reference excerpt" — and the rubric
   tells a judge facing an unrelated excerpt to report a high number of dropped
   words. That instruction has no ceiling on it. The first judge answered 5 and
   10; the second answered 100, twice, on the same arm, and those two cells alone
   carried 200 of that arm's 333 dropped-content points. Run 3 had the same
   broken windows and hid them just as well, answering them with added-content
   counts of 35 and 45 instead. Run 4 identifies them by the arm's own local
   error rate against the window — more errors than the window has words means
   the excerpt is not of that window — and drops all 12 before any mean is taken.
   The tables below are the 68 windows every arm was really anchored into.

**Two other things changed with run 4, and neither is a defect in the judge.**
Every arm's rows now go through the same number-and-acronym normalizer before
they are read, because the two FluidAudio batch arms wrote numbers as words
("eighty percent") while the pipeline, Cohere and the reference wrote digits —
a spelling difference the judge can see and charge. And the Cohere arm is the
loop-patched run described under the audits, where run 3 used the vendor-default
one. Granite is not in these tables at all: it had 3 windows, all from a single
Earnings-21 call that Granite's own model card puts in its training data.

**First judge, `gemini-3.1-flash-lite`, 68 windows** — lower is better except
readability. Wrong figures is published as an event count, not a mean: across
both judges there are 9 to 17 of them per arm in the whole run, and no ordering
is claimed from that column.

| arm | wrong figures (events) | wrong names / terms | dropped | added | readability |
|---|---:|---:|---:|---:|---:|
| Parakeet v3, MimicScribe pipeline | 14 | 0.76 | **0.51** | 0.35 | 4.06 |
| Parakeet v3, FluidAudio batch | 16 | 0.85 | 0.53 | 0.43 | 4.00 |
| Parakeet v2, FluidAudio batch | 17 | 0.90 | 0.55 | 0.25 | 4.21 |
| Cohere Transcribe | 12 | **0.68** | 0.84 | **0.18** | **4.29** |

Per corpus: on AMI the shipping pipeline drops the least (0.65 against Cohere's
1.29) and Cohere adds the least (0.29 against the pipeline's 0.52). On
Earnings-21, where the figures are, the wrong-figure events run 8 for the
pipeline, 9 for Cohere, 11 for v2 and 13 for the v3 batch arm on this judge,
and 6 / 6 / 6 / 9 on the second — a spread too small to order. Cohere has the
fewest wrong names there.

**How much the judge repeats itself.** Both passes of a repeated window now get
the same letters, so this measures whether the judge returns the same grade for
the same prompt rather than whether it is stable under a reshuffle. On 40 arm
pairs over 10 repeated windows it matched itself exactly on every cell for
figures, names and added content, on 95% of dropped-content cells and 98% of
readability. The chance-corrected agreement is 1.00, 1.00, 1.00, 0.89 and 0.96 —
worth stating because most of these counts are zero most of the time, and a
column that is almost always zero agrees with itself by accident. Run 3's
numbers are not comparable: its two passes were graded under different letters,
so its 94 / 96 / 84 / 80 / 80% mixed judge noise with position noise.

The Spearman correlation between the judge's total error count and content-word
error rate on the same window is **0.27** for the first judge and 0.51 for the
second. The judge is measuring something word error rate does not.

### A second judge

The grades above come from one Google model, so a reader cannot separate a
property of the transcripts from a property of that judge. A second, non-Google
judge — `anthropic/claude-haiku-4.5`, through OpenRouter — read the identical
excerpts, verified row by row afterwards: 78 of 78 scored rows carry
byte-identical excerpts for every arm, and 78 of 78 carry a different arm-to-letter
map, which is what keeps the two judges' agreement independent of position. The
run cost $0.35 and returned 0 parse failures.

| arm | wrong figures (events) | wrong names / terms | dropped | added | readability |
|---|---:|---:|---:|---:|---:|
| Parakeet v3, MimicScribe pipeline | 10 | 0.66 | 1.13 | 0.56 | 3.53 |
| Parakeet v3, FluidAudio batch | 13 | 0.75 | **1.08** | 0.60 | 3.54 |
| Parakeet v2, FluidAudio batch | 12 | 0.79 | 1.41 | 0.49 | 3.79 |
| Cohere Transcribe | 9 | **0.60** | 1.46 | **0.27** | **3.88** |

On its own repeated windows the second judge matched itself exactly on every
cell for figures, names and added content, on 85% of dropped content and 92% of
readability, with chance-corrected agreement 1.00, 1.00, 1.00, 0.76 and 0.87.

**The two judges agree on order and not on level.** Per graded cell, 312 of
them:

| criterion | Spearman | exact match | chance-corrected |
|---|---:|---:|---:|
| wrong figures | 0.71 | 91% | 0.67 |
| wrong names / terms | 0.81 | 75% | 0.61 |
| dropped content | 0.47 | 41% | 0.13 |
| added content | 0.57 | 76% | 0.47 |
| readability | 0.52 | 52% | 0.27 |

The two judges put the four arms in the same order on wrong names or terms and
on added content, and on wrong figures as well — though that column is a dozen
events per arm and is not offered as an ordering. They differ on dropped content
and on readability, and in both cases only by swapping the two Parakeet v3 arms,
which sit 0.05 apart on dropped content and 0.02 apart on readability. The
second judge still counts about twice as much dropped content per cell and reads
readability 0.44 lower: the levels are not comparable between the judges, the
ordering is. Dropped content is the column
they agree on least, and it is also the column that tracks how short an excerpt
is — within every arm, a shorter excerpt draws a higher dropped-content count
(Spearman −0.27 to −0.55). Part of that column is re-reading what word error
rate already reads.

**Position, after balancing.** Balanced letters do not remove the judges'
preference for a position, they stop it landing on one arm. On the published
windows the first judge's added-content counts by position A to D are 0.22 /
0.24 / 0.31 / 0.32 and the second judge's are 0.39 / 0.41 / 0.45 / 0.51 —
against run 3's 0.51 / 0.48 / 0.70 / 0.53 and 0.88 / 0.89 / 1.63 / 0.73. Most of
run 3's spread came from the same 12 windows the anchor check now removes.

**Excerpt sizes, as published.** Median excerpt as a fraction of its reference
window, then the maximum, over the 68 windows: Cohere 0.90 / 1.16, Parakeet v2
0.90 / 1.50, the pipeline 0.97 / 1.45, the v3 batch arm 0.98 / 1.47. One cell
hit the cap. Over the full 80 windows as collected, before the anchor check, the
cap fired 3 times on the pipeline, 6 on the v3 batch arm, 12 on v2 and 6 on
Cohere, against uncapped maxima of 4.25, 4.08, 4.13 and 10.38.

**Reading.** No model dominates, and that has survived four runs of removing
harness artifacts. Cohere is the cleanest transcript when it speaks — fewest
wrong names and best readability on both judges, fewest additions on both — and
the one that drops the most, on both judges, worst on the multi-party meeting
audio. The shipping pipeline and the vendor batch path running the same model
are separated by less than the judges are separated from each other: the
pipeline drops less on the first judge, the batch arm drops less on the second,
and the gap is 0.02 in one direction and 0.05 in the other. Two of run 3's
readings do not survive. Parakeet v2 is not last on every criterion but dropped
content — it is last on names in both judges, and second best on added content
and on readability in both, which is what a transcript that says less looks
like to a reader. And the pipeline is no longer separable from the rest on
figures: on Earnings-21 the first judge counts 8 wrong-figure events for it
against Cohere's 9, and the second counts 6 for each of three arms. One event
is not an ordering, and the column is too small to carry one.

## The runners were audited

Three independent audits of the three external runners, against each vendor's
reference implementation, plus measured subsets. **All three runners are
correct, and no defect found moves any arm's number by more than 0.3 points**,
so no arm needed a full-corpus re-run on the audit's account. Two hypotheses
the audit was told to test were rejected by measurement rather than argument;
both are in the next section. One latent defect remains in the Granite runner
and is inert on this corpus, because every file in it is mono.

## What we did not find

Published so nobody spends the machine time again.

| probe | result |
|---|---|
| FluidAudio's `melChunkContext`, swapped either way | worse in both directions |
| FluidAudio dual-decode | +0.57 points, and twice the wall clock |
| `maxTokensPerChunk`, swept over a wide range | byte-identical output |
| Cohere `<\|itn\|>` instead of the default `<\|noitn\|>` | 10.89% to 10.81% on a 3-file subset; number fidelity 445 intact, 6 corrupted, 10 dropped either way; invented 8 against 9 |
| Cohere float16 against float32 | 0.09 points |
| Cohere batch size 4 against 1 | byte-identical output |
| Cohere `no_repeat_ngram_size=3` applied globally | **+2.43 points and +145 deletions** (10.89% to 13.33% on the same subset) |
| A max-token retry as a cheaper loop fix | catches 3 of the 6 looping chunks |
| Granite with a much longer chunk | degenerates into a repeated sentence |
| Re-segmenting the scorer's input | 0.000 points |

The global repetition constraint is the important negative. It breaks every one
of the six looping chunks and recovers their real content, and it costs 2.43
points across clean speech by suppressing legitimate repeated phrases in dense
financial talk. That is why the published Cohere figure comes from re-decoding
six chunks rather than from changing the decode for all 2,102.

The `<|itn|>` probe answers a fairness question and answers it "no": Cohere is
prompted for word-form output by its own processor while the reference is
digit-form, and the concern was that our normalizer, tuned on Parakeet, would
mishandle its word forms. Switching the prompt changes nothing measurable, so
Cohere's dropped numbers are genuine deletions and not a normalization
artifact.

## Reproducing

Every number above comes from a committed script, except where marked. The
scorers are the same ones that gate changes internally, unmodified, and they
ship in this directory under `scripts/`. Run everything from this directory
with `MIMICSCRIBE_CORPUS_DATA=./data` pointing at the tree step 1 builds; the
two scorers and the judge read the references from there, and the scorers find
the app binary through `MIMICSCRIBE_BIN` (the released app's
`Contents/MacOS/mimicscribe`), which they call only for its text normalizer.

```bash
# 1. Corpus. No audio is redistributed; this fetches every file from its
#    publisher and verifies it by hash. Standard library only: no build, no
#    virtualenv, no API key. --corpus ami|earnings21|all narrows it.
python3 scripts/bakeoff/fetch_corpus.py --dest ./data
python3 scripts/bakeoff/fetch_corpus.py --verify-only ./data
```

`--verify-only` prints match, mismatch and missing per file and exits non-zero
if anything is wrong; `--emit-manifest` is how the manifest itself is rebuilt.
See [CORPUS.md](CORPUS.md) for the licences, the per-file hashes and what is not
redistributable.

```bash
# 2. The MimicScribe pipeline arm, with the released app and no source.
#    MIMICSCRIBE_DATA_DIR (alias: --data-dir <path>) points the whole data
#    directory at a throwaway one, so the run touches no database, keychain
#    item, voice profile, preference or update check of an existing install.
#    Model weights are the one thing it still shares — and because the
#    sandbox has no record of which encoder file was verified, pin the
#    encoder explicitly or a fresh sandbox decodes the STOCK file (the 16.75%
#    row), not the rebuilt one this report calls the product.
MIMICSCRIBE_DATA_DIR=./sandbox MIMICSCRIBE_ASR_ENCODER_PRECISION=int8-v2 \
  /Applications/MimicScribe.app/Contents/MacOS/mimicscribe \
  --benchmark-pipeline-corpus --corpora ami,earnings21 --files <the 27 ids> \
  --out-dir benchmark/output/bakeoff-app \
  --no-asr-cache --no-window-cache
```

Name every file with `--files`. A bare `--corpora ami,earnings21` decodes the
whole of both corpora, which is a different experiment and several times the
compute. An arm that reports no cache misses replayed an earlier decode and is
discarded rather than believed.

```bash
# 3. The FluidAudio batch arms: v3 rebuilt encoder, v3 stock encoder, v2.
swift run --package-path scripts/parakeet_version_probe parakeet_version_probe \
  --arm v3-int8v2 --version v3 --precision int8-v2 \
  --models-dir <model directory> --out benchmark/output/bakeoff-v3-int8v2 \
  --audio <file.wav> [--audio <file.wav> ...]
```

The probe package pins the same FluidAudio fork revision the app pins
(`MimicScribe/FluidAudio` @ `3c2cd9c2…`, the sha in the Provenance table), by
URL, so `swift run` resolves it on any machine with network access.

```bash
# 4. Cohere. Vendor defaults; the loop patch re-decodes only the six chunks
#    that ran into a repeated token.
python3 scripts/bakeoff/run_cohere_transcribe.py --out benchmark/output/bakeoff-cohere

# Which chunks looped, and do they break under repetition control? (prints only)
python3 scripts/bakeoff/cohere_repeat_probe.py --run-dir benchmark/output/bakeoff-cohere

# The loop patch: copies the run, re-decodes the six looping chunks with
# no_repeat_ngram_size=5, leaves every other chunk byte-identical.
python3 scripts/bakeoff/cohere_patch_loops.py \
  --run-dir benchmark/output/bakeoff-cohere \
  --out benchmark/output/audit-cohere-loopfix
```

All three take `--audio-root` if the corpus is not under `benchmark/data`,
which is where step 1 puts it.

```bash
# 5. Granite.
python3 scripts/bakeoff/granite_run.py \
  --out benchmark/output/bakeoff-granite --files <file.wav> [<file.wav> ...]
```

```bash
# 5b. NeMo, vendor runtime, CPU. nemo_toolkit[asr]==2.5.0 + torch==2.13.0.
#     v3 runs the card's long-audio recipe (local attention [128,128],
#     1800 s windows); v2 runs the card default (full rel_pos, 300 s windows).
python3 scripts/bakeoff/nemo_run.py --arm v3 --out benchmark/output/bakeoff-nemo-v3
python3 scripts/bakeoff/nemo_run.py --arm v2 --out benchmark/output/bakeoff-nemo-v2
```

`nemo_run.py` was written from the two run manifests
(`benchmark/output/bakeoff-nemo-{v2,v3}/manifest.json`) after the fact and has
NOT been re-executed — the original runner was never committed. The published
NeMo numbers come from that original run, so a re-run is a fresh measurement,
not a verification. The script's docstring names the five details the manifests
do not record: the `transcribe()` arguments, how the window audio was handed to
it, dtype, the scheduling niceness, and whether the v2 arm also set the
subsampling factor. The model revisions are no longer among them — `--revision`
defaults per arm to the snapshot the run resolved, the same two shas the
Provenance table carries.

```bash
# 6. Score. Both scorers put reference and hypothesis on one basis by calling
#    the binary's own --itn-text mode, and print which basis they used.
python3 scripts/score_corpus_wer.py --arms <A> <B> --labels pipeline cohere --per-file
python3 scripts/score_number_fidelity.py --corpus <arm>/per-file --json-out numbers.json

# 7. The blind judge, run 4. Defaults: 40 windows per corpus, 15% of windows
#    graded twice, seed 1234, temperature 0.1, one call at a time. Every arm
#    directory here is the NORMALIZED copy (step 6b), so no arm is identifiable
#    by its number spelling. --balanced-positions rotates arms through the
#    letters so each sits in each position equally; --max-excerpt-ratio caps
#    an arm's excerpt at 1.5x the window.
python3 scripts/bakeoff/judge_transcripts.py \
  --arms pipeline=<dir> batch=<dir> v2=<dir> cohere=<dir> \
  --balanced-positions --max-excerpt-ratio 1.5 \
  --out judge_gemini/judge.json
# The second judge replays the first run's windows and excerpts verbatim with
# the rotation offset by one position, so both stay balanced and no window
# shares a letter map between judges.
python3 scripts/bakeoff/judge_transcripts.py \
  --arms pipeline=<dir> batch=<dir> v2=<dir> cohere=<dir> \
  --provider openrouter --model anthropic/claude-haiku-4.5 \
  --windows-from judge_gemini/grades.jsonl --balanced-positions --position-offset 1 \
  --out judge_haiku/judge.json
# Agreement, position effect, cap counts, and the anchor check that drops a
# window where any arm's excerpt is not the same stretch of the meeting.
python3 scripts/bakeoff/judge_agreement.py \
  --run-a judge_gemini/grades.jsonl --run-b judge_haiku/grades.jsonl --max-anchor-wer 1.0
```

```bash
# 6b. Normalize a raw arm's rows once, line for line, through the same pass the
#     saved transcript goes through, so the number scorer and the judge read
#     every arm on one basis. The WER scorer does this itself at scoring time.
#     Row text out, one line per row, then back into the same JSON shape.
MIMICSCRIBE_DATA_DIR=./sandbox /Applications/MimicScribe.app/Contents/MacOS/mimicscribe \
  --itn-text --in <rows.txt> --out <rows.itn.txt>
```

Pin the output directory of each arm explicitly. The scorers default to the
newest directory on disk, which silently picks up whatever else has been run
since.

## Provenance

Every arm decoded and scored on 2026-09-01, on the same 27 files, by the same
two scorers on the same basis. The number-fidelity table was re-scored on
2026-09-03, on one binary; that section says so and carries the caveat.

**Published** is the date the model's Hugging Face repository was created.

| arm | model | revision | published | runtime |
|---|---|---|---|---|
| MimicScribe pipeline | `parakeet-tdt-0.6b-v3`, rebuilt int8 encoder | encoder `8d2c79e1…`; app `5c847cf5` (v1.0.0-rc.27) | 2025-08-04 | CoreML on Apple Silicon, via FluidAudio |
| FluidAudio batch, v3 rebuilt encoder | `parakeet-tdt-0.6b-v3` | encoder `8d2c79e1…`; FluidAudio `3c2cd9c22f0118eccdcf3bf9ae7bea3ea12fc9a0` | 2025-08-04 | CoreML, batch path, one model set per process |
| FluidAudio batch, v3 stock encoder | `parakeet-tdt-0.6b-v3` | encoder `e2020f32…`; FluidAudio same | 2025-08-04 | same |
| FluidAudio batch, v2 | `parakeet-tdt-0.6b-v2` | FluidAudio same | 2025-04-15 | same |
| NeMo v2 | `nvidia/parakeet-tdt-0.6b-v2` | `ae9ad070` | 2025-04-15 | NVIDIA NeMo 2.5.0, CPU |
| NeMo v3 | `nvidia/parakeet-tdt-0.6b-v3` | `541d1f99` | 2025-08-04 | NVIDIA NeMo 2.5.0, CPU |
| Cohere Transcribe 03-2026 (2B) | `evewashere/cohere-transcribe-03-2026-ungated` | `29b9036c` | 2026-03-24, mirror 2026-07-21 | MPS, float16 |
| Granite Speech 4.1-2b | `ibm-granite/granite-speech-4.1-2b` | `de575db6` | 2026-04-16 | MPS, bfloat16 |

Both CoreML encoder files come from `FluidInference/parakeet-tdt-0.6b-v3-coreml`.
The rebuilt int8 encoder the product ships has `weights/weight.bin` SHA-256
`8d2c79e15a4545e08fe3a21fe741e42b8bf24329db81de8fdfacd92388ea5a66`
(594,211,328 bytes), and the local file matches that repository's stored object
byte for byte. The stock file is
`e2020f323703477a5b21d7c2d282c403e371afb5962e79877e3033e73ba6f421`
(445,187,200 bytes).

The Cohere repository above is an ungated mirror, created 2026-07-21. The
canonical repository is gated for the account this was run from, which is stated
here because the mirror is what the revision identifies; its published date is
the canonical repository's.

Neither NeMo manifest records a model revision. The two shas above are the
snapshots in the Hugging Face cache the arms ran from, which is what the run
resolved.

Arm output directories (not redistributed; each holds one JSON of per-file
transcripts): `benchmark/output/bakeoff-<arm>/per-file/`, the patched Cohere
run at `benchmark/output/audit-cohere-loopfix`, the NeMo arms at
`benchmark/output/bakeoff-nemo-{v2,v3}`. The MimicScribe pipeline arm is
`benchmark/output/swift_pipeline_2026-08-30T021253Z`, decoded by app commit
`5c847cf5`, which shipped as v1.0.0-rc.27.

## What this page is not

It is not a leaderboard. Models ship monthly and this report is dated and
closed; nothing here ratchets, and no future release is gated on it.

It is not a latency comparison, for the reason given at the top.

It is not a speaker-attribution comparison. That has its own published page.

Every number here has an owner in a pin file in the source repository
(`benchmark/results/asr-bakeoff/pins.json`), naming the arm directory and the
command that re-derives it; the arm directories and commands are the ones
listed above. Start there, or start with
[what the shipping pipeline does](../live-transcription/results/RESULTS.md).
