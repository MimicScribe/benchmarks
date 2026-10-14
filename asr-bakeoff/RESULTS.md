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

A fifth arm, Parakeet Unified 0.6B, a model built for live transcription, was
decoded over the same 27 files on 2026-09-25 and has its own section. Nothing
already on this page was re-decoded for it.

A sixth arm, Parakeet Ultra, a post-training of Parakeet v3, was added on
2026-09-27 and replaced v3 in the product. Its section re-scores every arm on a
content basis (filled pauses and casual forms folded, numbers scored
separately), because Ultra writes fewer filled pauses than the verbatim
reference expects. The earlier tables are unchanged.

A seventh arm, NVIDIA Nemotron Speech Streaming 0.6B, a streaming model, was
decoded over the same 27 files on 2026-09-28 and has its own section. What it
measures is FluidInference's CoreML conversion of that model through FluidAudio,
at a chunk size NVIDIA documents; which NVIDIA checkpoint the conversion carries
is not established, and NVIDIA's own runtime was not run. Nothing
already on this page was re-decoded for it, and its section carries a fresh
blind-judge run, because the earlier judges cannot be mixed with a new one.

Two streaming models, Voxtral Realtime 4B and Moonshine Streaming Medium, were
probed on a single file after publication and are reported separately below.
Neither was part of the measured comparison and their section says so.

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
before any latency claim, and none is made here. The Nemotron section reports
its own throughput under stated conditions and compares it with nothing.

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
12,552 more reference words while substituting 2,014 fewer and inserting 1,782 fewer,
and it is worse on 26 of the 27 files (median +5.0 points). Part of that is
that it is a non-verbatim transcriber scored against a verbatim reference —
9,134 filled-pause deletions against 4,372 — and part of it is not: it also
drops ordinary words, "the" 610 more times, "you" 588, "know" 399. Those word
counts are from the vendor-default run; the patched run's are within five of
each.

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

## Parakeet Unified 0.6B

Added 2026-09-25. NVIDIA's `parakeet-unified-en-0.6b` is English only and is
trained to run either as a stream or over a whole file with one set of
weights. It was run the way a live caller would run it: through FluidAudio's
streaming manager at its 1,120 ms latency setting (the setting with the best
streaming error rate in that runtime's own benchmark), int8 encoder on the
Neural Engine, fed 160 ms of audio at a time.

27 files, pooled:

| arm | hypothesis words | error rate | sub | del | ins |
|---|---:|---:|---:|---:|---:|
| Parakeet v3 int8-v2, FluidAudio batch (the comparator) | 168,105 | 16.37% | 8,518 | 15,671 | 5,073 |
| Parakeet v3 int8-v2, MimicScribe pipeline | 170,401 | 15.46% | 8,797 | 13,563 | 5,261 |
| **Parakeet Unified 0.6B, streaming** | 156,463 | **19.15%** | 6,369 | 25,052 | 2,809 |

Per corpus, AMI 25.69% (2,238 / 16,713 / 1,911) against the comparator's
25.57%, and Earnings-21 13.71% (4,131 / 8,339 / 898) against 8.71%.

**The whole gap is deletion, and it sits in the earnings calls.** Against the
comparator it deletes 9,381 more reference words while substituting 2,149
fewer and inserting 2,264 fewer. On the meetings it is level with the
comparator; on the earnings calls it is 5 points behind. Like Cohere, it writes
a tidier transcript than was spoken: filled pauses, repeated words and false
starts are left out, and in back-and-forth conversation long stretches go
unpunctuated.

**Streaming is not what costs it.** The same model has an offline path that
reads each stretch of audio with full context in both directions. Run that way
on two files, it lands within 0.6 points of the stream:

| file | streaming | offline | Parakeet v3, MimicScribe pipeline |
|---|---:|---:|---:|
| IS1009a (AMI) | 26.50% | 25.95% | 21.81% |
| 4320211 (Earnings-21) | 10.08% | 10.13% | 7.46% |

This is a control on two files, not a second arm. Four files of the streaming
arm were decoded twice and came out byte-identical both times.

**Numbers:** 2,685 of 2,840 scored quantities intact, 51 wrong, 104 dropped, 84
never said, 6 doubled or spliced. These were scored with the published scorer
on a later build of the normalizer than the Numbers table below, so they are
not in that table. Re-scoring the v3 batch comparator on the same build reads
2,745 intact against its published 2,749, which bounds how much the build
moves a row.

On the one meeting every model decoded, it marks the fewest sentence ends of
any arm (see the next section): 20% of the sentence ends at a speaker change,
and almost none it should not.

**Verdict: not a replacement.** It deletes more than the model the product
ships, in both of its own modes on the files tried, and its punctuation is too
sparse to split speakers on.

## Parakeet Ultra — the model the product ships now

Added 2026-09-27. [Parakeet Ultra](https://huggingface.co/moondream/parakeet-ultra)
is moondream's post-training of Parakeet TDT 0.6B v3 (CC BY 4.0): the same
architecture, tokenizer and 25 languages with different weights. It runs
through FluidInference's CoreML conversion, int8 encoder on the Neural Engine,
inside the same pipeline as the v3 pipeline rows on this page, and from this
date it is the model the product ships.

Ultra writes fewer filled pauses than v3 and expands casual forms ("gonna"
becomes "going to"). A verbatim reference charges both as errors, so on this
page's verbatim basis the two pipelines are level: 15.58% for Ultra against
15.36% for v3 on the same build (15.46% for the rc.27 pipeline arm above). All
of Ultra's extra deletions on that basis are filled pauses: it leaves out 728
more "uh"s than v3.

**Every arm, on a content basis.** The table below re-scores every 27-file arm
on this page with three changes, each applied to the reference and the
hypothesis alike: filled pauses removed, casual forms folded to their
expansion, and number words and digits left out. The last one is there because
some arms write "2020" and others "twenty twenty", and the comparison should not
turn on spelling. Numbers are scored by value in the next table instead.

27 files, pooled, content basis, numbers excluded:

| arm | error rate | sub | del | ins | AMI | Earnings-21 |
|---|---:|---:|---:|---:|---:|---:|
| **Parakeet Ultra, MimicScribe pipeline** | **13.63%** | 7,423 | **10,262** | 4,901 | **20.68%** | **7.65%** |
| Parakeet v3 int8-v2, MimicScribe pipeline, same build | 14.14% | 7,440 | 11,148 | 4,849 | 21.72% | 7.72% |
| Parakeet v3 int8-v2, MimicScribe pipeline (rc.27, the arm above) | 14.27% | 7,400 | 11,463 | 4,798 | 21.93% | 7.79% |
| Parakeet v3 int8-v2, FluidAudio batch (the comparator) | 15.09% | 7,187 | 13,259 | 4,564 | 23.49% | 7.98% |
| Parakeet v3 stock int8, FluidAudio batch | 15.54% | 7,191 | 14,260 | 4,303 | 24.48% | 7.97% |
| Parakeet v3, NeMo | 15.44% | 7,083 | 15,258 | 3,253 | 22.33% | 9.61% |
| Parakeet v2, FluidAudio batch | 16.48% | 6,768 | 17,201 | 3,343 | 24.26% | 9.89% |
| Parakeet v2, NeMo | 16.62% | 6,322 | 18,668 | **2,558** | 23.90% | 10.46% |
| Parakeet Unified 0.6B, streaming | 16.77% | **5,426** | 19,698 | 2,670 | 23.85% | 10.77% |
| Cohere Transcribe (loop-patched) | 17.28% | 5,708 | 19,641 | 3,300 | 25.92% | 9.98% |

Ultra is better than v3 through the same pipeline on 22 of the 27 files, worse
on 4 and level on 1, and the gain is deletions: 886 fewer reference words
dropped, with substitutions and insertions level. The gaps narrow for the arms
that leave filled pauses out: Cohere goes from 4.9 points behind the pipeline
to 3.0 behind v3's pipeline, and v2 from 3.1 to 1.4 behind v3's batch
comparator. NeMo v3 moves ahead of the stock-encoder batch arm, and v2 ahead of
Parakeet Unified.

**Numbers, re-scored on one build.** Every arm's rows were put through the same
normalizer build and scored by a later version of the number scorer than the
Numbers table below, so this table and that one do not mix. The v3 pipeline arm
reproduces its published 2,769 intact figures exactly on the new build and scorer.

| arm | scored | intact | wrong quantity | dropped | never said | doubled or spliced form |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, pipeline | 2,857 | 2,755 (96.4%) | 41 | 61 | 87 | 5 |
| Parakeet v3 int8-v2, pipeline, same build | 2,861 | **2,769 (96.8%)** | 42 | **50** | 91 | 11 |
| Parakeet v3 int8-v2, pipeline (rc.27) | 2,860 | 2,769 (96.8%) | 37 | 54 | 71 | 6 |
| Parakeet v3 int8-v2, batch | 2,859 | 2,747 (96.1%) | 44 | 68 | 84 | 10 |
| Parakeet v3 stock int8, batch | 2,857 | 2,746 (96.1%) | 43 | 68 | 79 | 9 |
| Parakeet v2, batch | 2,847 | 2,732 (96.0%) | 43 | 72 | 66 | 0 |
| Parakeet v2, NeMo | 2,839 | 2,712 (95.5%) | 33 | 94 | 60 | 1 |
| Parakeet v3, NeMo | 2,850 | 2,685 (94.2%) | **29** | 136 | 58 | 0 |
| Cohere Transcribe | 2,851 | 2,725 (95.6%) | 37 | 89 | **57** | 4 |
| Parakeet Unified 0.6B | 2,843 | 2,687 (94.5%) | 49 | 107 | 88 | 6 |

Ultra keeps 14 fewer figures intact than v3 through the same pipeline and drops
11 more. Part of that is the scoring path, not the transcript: the product now
writes every quantity as words, and re-normalizing Ultra's words to digits for
scoring joins some neighbours that were spoken apart ("another one eighty, uh,
140 million dollars" scores as one figure). Scored on the rows as the product
saves them, without that step, Ultra keeps 2,730 of 2,854 intact against v3's
2,725 of 2,858. The table above is the one comparable to every other arm, and on
it Ultra is 0.4 points behind v3.

**The one meeting every model decoded** (IS1009a), on the same scorers as the
streaming-probe section below:

| | Parakeet Ultra, pipeline | Parakeet v3, pipeline (rc.27) |
|---|---:|---:|
| real words skipped on clean speech, fillers stripped | **1.7%** (22 of 1,273) | 2.5% (32 of 1,273) |
| error rate, fillers stripped | **17.2%** | 17.7% |
| sentence ends at a speaker change | **92%** | 89% |

That meeting flatters Ultra on punctuation. Across all 16 AMI meetings its
sentence ends are more precise and fewer: precision 77.0% against 74.7%, recall
82.8% against 88.1%, and sentence ends at a speaker change 86.0% against 90.0%
for v3 on the same build. The product splits speakers partly on sentence ends,
so this is the cost that matters most, and it is published here for that
reason.

**What else differs.** Ultra writes some characters v3's vocabulary never had
(quotes, parentheses, dashes, "&") as an unknown token; the product restores
"&" and paired brackets or quotes and drops the rest. Outside this corpus, on
FLEURS read speech in ten European languages, its error rate is lower than v3's
in every one of the ten (6.56% against 7.66% mean).

**Verdict: the replacement.** Fewer words dropped than any arm on this page,
the same substitution and insertion counts as v3, and a small loss on number
fidelity and on sentence ends at speaker changes, both measured above.

## MimicScribe's spoken-form fine-tune — the next release

Added 2026-10-14. The next MimicScribe release replaces stock Parakeet Ultra with
[a fine-tune of it](https://huggingface.co/MimicScribe/parakeet-ultra-spoken-coreml)
(revision `5edfc817`, CC BY 4.0) that writes English numbers the way they were
said: "twenty nineteen" stays "twenty nineteen", "two thousand nineteen" stays
"two thousand nineteen". Only the decoder and joint network were trained; the
encoder and tokenizer are Ultra's.

Three arms on the 27 files (18.8 hours), so the model's effect is separated from
the app's: the published Ultra arm above (the current release), stock Ultra
decoded by the next release's app build, and the fine-tune decoded by that same
build. All three are scored by the same scorer build, which reproduces the
published Ultra row exactly.

Content basis, numbers excluded (as in the table above):

| arm | error rate | sub | del | ins | AMI | Earnings-21 |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, current release | 13.63% | 7,423 | 10,262 | 4,901 | 20.68% | 7.65% |
| Parakeet Ultra, next release's app | 13.61% | 7,424 | 10,232 | 4,906 | 20.66% | 7.64% |
| **Spoken-form fine-tune, next release's app** | **13.59%** | 7,520 | **10,067** | 4,933 | **20.57%** | 7.68% |

Word accuracy is level. The fine-tune drops 165 fewer reference words than
Ultra in the same build and adds 27 more, and it drops 29% fewer than
stock Parakeet v3 through FluidAudio's batch runner (14,260), against 28% for
Ultra.

**Numbers, scored on the transcript as saved.** The fine-tune writes numbers as
words, and the product saves them that way. Scoring the saved rows directly
avoids the step that re-joins spoken neighbours into one figure (see the Ultra
section above), so this table uses a later scorer and does not mix with the
earlier number tables.

| arm | scored | intact | wrong quantity | dropped | never said | doubled or spliced form |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, current release | 2,880 | 2,790 (96.9%) | 38 | 52 | 81 | 0 |
| Parakeet Ultra, next release's app | 2,880 | 2,797 (97.1%) | 35 | 48 | 74 | 0 |
| **Spoken-form fine-tune, next release's app** | 2,882 | **2,812 (97.6%)** | **29** | **41** | **72** | 0 |

**The one meeting every model decoded** (IS1009a): real words skipped on clean
speech with fillers stripped, 1.7% (22 of 1,276) for Ultra in both builds and
**1.5% (19 of 1,276)** for the fine-tune.

**Punctuation**, Earnings-21 rows: sentence-end recall 0.807 → 0.812 and
sentence-start recall 0.825 → 0.827, while boundary recall at a speaker's last
word moved 0.950 → 0.949 and capitalisation precision is level (0.886 → 0.885).

**What it costs.** It sometimes writes "GAAP" as "gap". It keeps the other 24
languages as they were: on FLEURS read speech it is level with Ultra across all
25 languages ([multilingual results](../multilingual/RESULTS.md)).

## Nemotron Speech Streaming 0.6B

Added 2026-09-28, revised the same day. NVIDIA's `nemotron-speech-streaming-en-0.6b`
is an English-only, cache-aware streaming FastConformer-RNNT model (NVIDIA Open
Model License). This section measures **FluidInference's CoreML conversion of it
through FluidAudio's `StreamingNemotronAsrManager`**, not NVIDIA's own runtime,
which was not run. FluidAudio is upstream v0.17.4, not the v0.15.6-based fork the
other Swift arms pin; int8 encoder; audio fed 160 ms at a time; M1 Max, 32 GB,
macOS 27.0.

**Tier.** The headline arm runs at the **1,120 ms** chunk, one of the chunk sizes
NVIDIA documents for the model (80, 160, 560 and 1,120 ms; the card's AMI figure,
11.73%, is at 1.12 s on a different AMI basis, so it is not compared with anything
here). The library's default is a 2,240 ms tier, which NVIDIA does not document;
it is FluidAudio's throughput tier and is reported as a secondary row.

**Which checkpoint is not established.** NVIDIA's `main` branch is the checkpoint
released 2026-03-13; the January 2026 checkpoint is on the branch
`nemotron-speech-streaming-jan2026`. The FluidInference repository was created on
2026-01-12 and its 2,240, 1,120 and 560 ms tiers were re-converted on 2026-06-05
from a checkpoint it does not name; the conversion script pins no revision. Both
NVIDIA cards say the model outputs punctuation and capitalization, and the
tokenizer in the conversion has the comma, period and question-mark tokens. We
did not convert either checkpoint ourselves. Every result below is for this
conversion, and it may not represent either NVIDIA checkpoint.

All 27 files were decoded at both tiers. Both corpora are English, so no file was
set aside as not applicable to an English-only model. Nothing already on this page
was re-decoded. The comparator rows were re-scored today on the same normalizer
build as the Nemotron rows and reproduce their published figures to within 12
hypothesis words (the vendor batch arm reads 16.38% against a published 16.37%; the
Unified, Ultra, same-build v3 and number-table rows reproduce exactly).

Two comparators, by the rule at the top of the page: the like-for-like row for an
external model is the Parakeet v3 FluidAudio batch arm, and the streaming
comparator is Parakeet Unified, which ran through the same kind of streaming
manager. The two pipeline rows are the product and are shown for reference.

27 files, pooled, verbatim basis:

| arm | hypothesis words | error rate | sub | del | ins | AMI | Earnings-21 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, MimicScribe pipeline | 170,227 | 15.58% | 8,905 | 13,704 | 5,225 | 23.29% | 9.15% |
| Parakeet v3 int8-v2, MimicScribe pipeline, same build | 170,832 | 15.36% | 8,863 | 13,232 | 5,358 | 23.67% | 8.44% |
| Parakeet v3 int8-v2, FluidAudio batch (the comparator) | 168,117 | 16.38% | 8,522 | 15,666 | 5,077 | 25.57% | 8.72% |
| **Nemotron Speech Streaming 0.6B, 1,120 ms** | 161,818 | **17.28%** | 7,894 | 19,940 | 3,052 | 24.44% | 11.32% |
| Nemotron Speech Streaming 0.6B, 2,240 ms (FluidAudio's off-spec speed tier) | 161,846 | 17.29% | 7,839 | 19,958 | 3,098 | 24.52% | 11.26% |
| Parakeet Unified 0.6B, streaming | 156,463 | 19.15% | 6,369 | 25,052 | 2,809 | 25.69% | 13.71% |

The two tiers are within 0.01 points of each other pooled and within 0.1 on either
corpus, so the tier does not explain any result below; the rest of this section
quotes the 1,120 ms arm.

**Against the batch comparator it is 0.91 points worse, and the gap is
deletion.** It deletes 4,274 more reference words while substituting 628 fewer and
inserting 2,025 fewer. The gap is specific to the corpus. On AMI it is 1.14 points
better than the comparator (24.44% against 25.57%, better on 13 of 16 meetings).
On Earnings-21 it is 2.6 points worse (11.32% against 8.72%), worse on all 11
calls, with 5,315 deletions against 1,839. That earnings-only gap is 3,476
deletions: 57% are filled pauses and backchannels ("uh" +1,431, "um" +456) and the
rest are mostly function words ("the" +102, "I" +93, "you" +92, "and" +79, "know"
+68). No stretch of audio went untranscribed on the two calls we checked, the
longest and the one with the most deletions against the comparator (no gap of more
than 5 seconds between rows on either); the deletions are single words spread
through the calls.

**Against Parakeet Unified it is 1.87 points better**, better on 23 of the 27
files. Both are streaming models of the same size. Nemotron deletes 5,112 fewer
reference words and substitutes 1,525 more; it is 1.25 points ahead on AMI and
2.39 on Earnings-21. It is 1.71 points behind the Ultra pipeline the product ships
(worse on 22 of 27 files) and 1.92 behind the same-build v3 pipeline.

**Content basis.** The same re-score as the Ultra section (filled pauses removed,
casual forms folded, number words and digits left out, each on both sides):

| arm | error rate | sub | del | ins | AMI | Earnings-21 |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, MimicScribe pipeline | 13.63% | 7,423 | 10,262 | 4,901 | 20.68% | 7.65% |
| Parakeet v3 int8-v2, MimicScribe pipeline, same build | 14.14% | 7,440 | 11,148 | 4,849 | 21.72% | 7.72% |
| Parakeet v3 int8-v2, FluidAudio batch (the comparator) | 15.09% | 7,187 | 13,259 | 4,564 | 23.49% | 7.98% |
| **Nemotron Speech Streaming 0.6B, 1,120 ms** | **15.09%** | 6,711 | 15,477 | 2,825 | 22.43% | 8.88% |
| Nemotron Speech Streaming 0.6B, 2,240 ms | 15.11% | 6,667 | 15,508 | 2,878 | 22.56% | 8.82% |
| Parakeet Unified 0.6B, streaming | 16.77% | 5,426 | 19,698 | 2,670 | 23.85% | 10.77% |

On this basis the pooled rate ties the comparator (25,013 errors against 25,010),
but that is two offsetting corpus results, not agreement. It is 1.06 points better
on AMI and 0.90 worse on Earnings-21, and it still deletes 2,218 more reference
words overall. The pooled gap to Unified is 1.68 points.

On clean speech on AMI (no other speaker talking) it deletes at the comparator's
rate, 5.0% against 5.0%; on overlapped speech it deletes 48.1% against 45.1%
(Unified: 6.3% and 53.8%).

**Numbers**, on the same build and scorer as the number table under "Parakeet
Ultra", Earnings-21 quantities checked by value:

| arm | scored | intact | wrong quantity | dropped | never said | doubled or spliced form |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet Ultra, pipeline | 2,857 | 2,755 (96.4%) | 41 | 61 | 87 | 5 |
| Parakeet v3 int8-v2, pipeline, same build | 2,861 | 2,769 (96.8%) | 42 | 50 | 91 | 11 |
| Parakeet v3 int8-v2, batch (the comparator) | 2,859 | 2,747 (96.1%) | 44 | 68 | 84 | 10 |
| **Nemotron Speech Streaming 0.6B, 1,120 ms** | 2,858 | **2,751 (96.3%)** | 40 | 67 | 132 | 20 |
| Nemotron Speech Streaming 0.6B, 2,240 ms | 2,857 | 2,748 (96.2%) | 41 | 68 | 130 | 20 |
| Parakeet Unified 0.6B | 2,843 | 2,687 (94.5%) | 49 | 107 | 88 | 6 |

It keeps as many quantities intact as the comparator (2,751 against 2,747) and has
the highest never-said and doubled-or-spliced counts in the number tables on this
page, all of which run under one normalizer. That normalizer was built for
Parakeet's output style, and the model's raw text is different: it spells years
out ("twenty twenty" 207 times in the earnings calls, never as digits) and writes
few commas. Scored on the rows as decoded, without the
normalizer, the 1,120 ms arm reads 2,692 intact of 2,851 (94.4%), 60 wrong, 99
dropped, 168 never said and no splices. So the normalizer turns 59 more
quantities intact, cuts the dropped by 32 and the never-said by 36, and creates
the 20 splices. Eleven of those 20 are a day followed by a year ("30 2020"), which read
like dates whose comma the transcript never wrote. The never-said count is mostly
cardinals (73) and ordinals (23, of which 16 are "first"); Parakeet's batch arm
has 55, 14 and 10 in the same classes. We did not separate how much of the rest is
the model and how much is the normalizer meeting text it was not tuned on.

**Punctuation is domain-specific and sparse.** Words ending in a period, question
mark or exclamation mark, per 1,000 words, in the rows as decoded
(`scripts/bakeoff/punct_recount.py`):

| arm | AMI | Earnings-21 |
|---|---:|---:|
| Nemotron, 1,120 ms | 0.4 (30 of 68,535 words) | 13.8 (1,320 of 95,846) |
| Parakeet v3, FluidAudio batch | 99.0 | 48.1 |
| Parakeet Unified | 9.5 | 51.9 |

On AMI it writes almost no sentence ends. On Earnings-21 it writes some, under a
third as many as the comparator. On one meeting, IS1009a, the terminal-punctuation
scorer from the probes section finds none of the 133 reference sentence ends its
words line up with marked (recall 0.000). That is one file. We did not establish
whether the sparse marks come from the checkpoint, the conversion or the decoder;
NVIDIA's cards say the model writes punctuation and this transcript mostly does
not on meeting speech. Speaker attribution needs sentence ends, which is why
Unified's sparse marks disqualified it above.

Side checks, each one line. Tier: the 2,240 ms arm above is the whole comparison.
One meeting (IS1009a): deletion on clean speech 4.3% for Nemotron at 1,120 ms
against 5.0% for the batch comparator, 3.1% against 4.5% with fillers and
backchannels removed, error rate 18.2% against 21.8%. Speed: 30.0 times real time
in aggregate at 1,120 ms (2,262 s for 18.83 h) and 32.9 at 2,240 ms (2,062 s), per
file 20.6 to 33.3 and 17.3 to 42.5, on a machine with other jobs running, so no
comparison with another arm is made.

**The blind judge.** The two earlier judges were `gemini-3.1-flash-lite` and
`anthropic/claude-haiku-4.5`, and their grades cannot be mixed with a third
judge's. So four arms were graded again by one judge, `gemini-3.8-flash-medium`
through the `agy` CLI, over the same 80 windows as run 4 (all 92 window and pass
ids match), with balanced letters, the same excerpt cap and the same anchor check.
The arms are the Ultra pipeline, the vendor batch comparator, Parakeet Unified and
Nemotron at 1,120 ms; the 2,240 ms arm was not judged. The CLI sets no temperature
or thinking budget, so this run's levels are not comparable with run 4's, and the
run 4 tables are unchanged. The anchor check dropped 15 windows in which at
least one arm's excerpt was not the same stretch of the meeting (Unified in 9, Nemotron in 7, batch in 5, Ultra in 3),
leaving 65 windows and 73 calls, against run 4's 68 and 78.
One call returned an empty turn at the CLI's own limit and was asked again; none failed in the end.

Single judge, 65 windows. Lower is better except readability; wrong figures
are event counts and no ordering is claimed from them:

| arm | wrong figures (events) | wrong names / terms | dropped | added | readability |
|---|---:|---:|---:|---:|---:|
| Parakeet Ultra, pipeline | 8 | 0.42 | **0.55** | 0.08 | **4.28** |
| Parakeet v3, FluidAudio batch | 7 | 0.55 | 0.66 | 0.11 | 4.22 |
| **Nemotron Speech Streaming 0.6B, 1,120 ms** | 3 | 0.55 | 0.85 | **0.05** | 3.10 |
| Parakeet Unified 0.6B | 10 | **0.37** | 0.83 | 0.06 | 3.88 |

Nemotron adds the least content and has the fewest wrong-figure events, ties the
comparator on wrong names, and drops the most (0.85 against the comparator's 0.66,
Unified's 0.83). The wrong-figure events are all on the earnings calls (3 for
Nemotron, 7 for the comparator, 6 for Ultra, 10 for Unified; on AMI there are 2 in
all, both Ultra's), and that column is a handful of events, not a ranking. On its
own 12 repeated windows the judge matched itself on every cell for wrong figures,
names and added content, on 91% for dropped content and 84% for readability
(chance-corrected: figures 1.00, names 1.00, dropped 0.68, added 1.00, readability
0.76). By prompt position the added-content means are 0.05, 0.07, 0.05 and 0.10 for
A to D. There is no second-vendor judge for this run, so a reader cannot separate a
property of the transcripts from a property of this judge.

**Caveats.**

- **English only.** It cannot serve the 25-language product; this corpus is
  English.
- **The FluidAudio conversion, not NVIDIA's runtime.** FluidAudio's documentation
  says WER parity with NVIDIA's own tuning is a tracked follow-up; its own figure
  for the 2,240 ms tier is 2.46% on LibriSpeech test-clean. A result through
  NVIDIA's runtime, or for the March checkpoint if the conversion carries the
  January one (or the reverse), may read differently.
- **The deletion check is two files**, and the number-normalizer attribution above
  is not separated further.
- **Readability measures output format here.** The judge's notes mention missing
  punctuation on 48 of its 92 Nemotron cells, so that column says what the
  transcript looks like and is not used in the verdict.

**Verdict, scoped: not a replacement.** For the FluidAudio CoreML port at 1,120 ms,
under this page's normalizer and scorer stack, it deletes more than the model the
product ships and than the vendor batch arm on the verbatim basis (worse on
Earnings-21, better on AMI, level on the pooled content basis), writes almost no
sentence ends on AMI, and has the highest never-said and spliced quantity counts
in the number tables. It is a better streaming recognizer than Parakeet Unified on
this corpus. That is a statement about this conversion and this scoring; NVIDIA's
own runtime was not run.

## Two streaming models — probes, not arms

Neither model below is one of the arms above. Each was run on one file after
publication, and nothing here is comparable to the pooled figures. So that the
probes can be read against every model, the two tables below also carry each
arm's own decode of the same file, added 2026-09-25; those rows are one file
too.

**Voxtral Realtime 4B.** Mistral's `Voxtral-Mini-4B-Realtime-2602` (Apache
2.0) is natively streaming: a causal encoder and a 3.4B decoder emitting one
token per 80 ms frame. It was published 2026-02-04, seven months before this
report was measured, so "dated and closed" does not cover its omission. Run
4-bit at a 480 ms delay on 2026-09-06, with an fp16 control on 2026-09-07.

**Moonshine Streaming Medium.** Moonshine's `moonshine-streaming-medium` (245M,
English only, MIT) streams with a sliding-window encoder. It sat close to
Parakeet v3 on an earlier version of the Open ASR Leaderboard, ahead on AMI
(10.68 against 11.39 in that version) and behind on the average. The current
version no longer lists it. Run 2026-09-21 through the vendor's own
`moonshine-voice` runtime (0.1.5), CPU only, fed in 200 ms chunks. That runtime
ships a quantized build, while the leaderboard scored the published weights; we
did not run a full-precision control, so part of any gap to the leaderboard may
be the quantization.

**The file.** IS1009a (AMI, 839 s). No second corpus, no judge, no
number-fidelity pass. Every column below was scored in one run of each scorer
on one binary, with `MIMICSCRIBE_ITN_NUMBERS=1` (see Reproducing). The rows added
on 2026-09-25 were scored in a later run on a later binary; that run re-scored
the first four rows as well and reproduced every cell.

Terminal punctuation against AMI's own `punc="true"` annotations, over 1:1
aligned words. The scorer is `scripts/bakeoff/ami_punctuation_accuracy.py`; it
is newer than the four scorers above and has had less review:

| arm | coverage | precision | recall | F1 | recall at a speaker change | extra marks |
|---|---:|---:|---:|---:|---:|---:|
| Parakeet v3, FluidAudio batch | 0.765 | **0.783** | 0.834 | 0.808 | 0.853 | 35 |
| Parakeet v3, MimicScribe pipeline | 0.792 | 0.760 | 0.875 | **0.814** | 0.888 | 42 |
| Voxtral Realtime 4-bit | 0.714 | 0.702 | **0.943** | 0.805 | **0.944** | 56 |
| Moonshine Streaming Medium | 0.736 | 0.600 | 0.684 | 0.639 | 0.719 | 62 |
| Cohere Transcribe | 0.721 | 0.704 | 0.856 | 0.773 | 0.889 | 50 |
| Parakeet v3, NVIDIA NeMo | 0.766 | 0.758 | 0.844 | 0.799 | 0.876 | 38 |
| Parakeet v2, FluidAudio batch | 0.749 | 0.778 | 0.829 | 0.803 | 0.888 | 33 |
| Parakeet Unified 0.6B, streaming | 0.739 | **0.947** | 0.137 | 0.240 | 0.198 | 1 |

**Voxtral punctuates better than either Parakeet arm.** 94.4% of reference
sentence ends at a speaker change get a mark, against 85.3% and 88.8%, and it
pays in precision. Its coverage is the lowest, so part of that recall may be a
selection effect we did not separate. **Moonshine punctuates worst of the
first four rows**, on every column but coverage. Its output comes in lines, and a line
break might be read as a sentence end the text does not mark. It does not
explain the gap: 17 of the 25 sentence ends it misses at a speaker change fall
inside a line, and counting every line break as a mark only lifts it to 0.809,
still below both Parakeet arms.

**Parakeet Unified marks the fewest sentence ends of any row**: 20% of those at
a speaker change, against 72% for Moonshine and 85–94% for everything else. The
marks it does make are almost all right, which is why its precision is the
highest here and its recall the lowest.

Deletions, split by whether another speaker was talking at the same instant.
The overlapped column is structural for any single-stream decoder; the clean
column is recognition quality:

| arm | deletion, overlapped | deletion, clean speech | clean, fillers and backchannels removed | WER, fillers and backchannels removed |
|---|---:|---:|---:|---:|
| Parakeet v3, FluidAudio batch | 47.2% | 5.0% | 4.5% | 21.8% |
| Parakeet v3, MimicScribe pipeline | 39.2% | **2.7%** | **2.5%** | **17.7%** |
| Voxtral Realtime 4-bit | 50.1% | 11.4% | 7.1% | 19.8% |
| Voxtral Realtime fp16 | 49.2% | 11.2% | 6.8% | 19.5% |
| Moonshine Streaming Medium | 48.2% | 7.0% | 5.2% | 23.1% |
| Cohere Transcribe | 48.7% | 11.1% | 6.1% | 20.8% |
| Parakeet v3, NVIDIA NeMo | 45.4% | 3.9% | 3.2% | 18.4% |
| Parakeet v2, FluidAudio batch | 47.7% | 6.5% | 3.7% | 18.8% |
| Parakeet Unified 0.6B, streaming | 53.3% | 6.7% | 3.9% | 20.2% |

The two right-hand columns remove the scorer's filler and backchannel list
("yeah", "mm", "uh", "okay" and similar) from both the reference and the
transcript before aligning, with `scripts/bakeoff/backchannel_stripped_deletion.py`.
They exist because the raw clean-speech column mixes a transcription
convention with real loss: fillers and backchannels are 42% of Voxtral's
clean-speech deletions, 30% of Moonshine's and 22–27% of the two Parakeet v3
arms' in the first rows (Cohere 48%, Parakeet v2 48%, Parakeet Unified 45%,
NeMo 33%). With
them removed, Voxtral's content loss is 2.8 times the pipeline's rather than
4.2 times, and its word error rate lands between the two Parakeet arms.
Moonshine's content loss is close to the batch path's, 66 words against 57 of
1,273, and twice the pipeline's.

Against a 1,981-word reference the pipeline writes down 1,786 words, the batch
path 1,719, NeMo 1,709, Moonshine 1,686, Parakeet v2 1,666, Parakeet Unified
1,627, Cohere 1,595 and Voxtral 1,549. fp16 against 4-bit moved
Voxtral by 8 words, so the shortfall is the model, not the compression.

No delay sweep was run for Voxtral. The model's card puts 480 ms within 1-2% of
its own batch mode, with 2,400 ms at parity, so the setting's whole range is
smaller than the gap it would need to close. Its published AMI figure, 15.05%,
sits above Parakeet v3's 11.31% on the same leaderboard. Moonshine at a 500 ms
chunk size on a 4.3-minute slice of the same file lost 6.3% of clean speech,
against 7.1% at 200 ms, so chunk size is not what holds it back.

**How Moonshine runs.** It does not run on the Neural Engine. The runtime can
hand ONNX Runtime a Core ML provider, but on this build the first decode fails
every time: the streaming decoder starts from an empty cache, and the Core ML
provider rejects a zero-length input. On CPU, one stream ran at 1.41 times
real time, kept 2.25 cores busy and peaked at 2.6 GB. A meeting is two streams,
microphone and system audio. Its line timestamps are usable. Its word
timestamps are not: 7.9% end before they start and 55% repeat the previous
word's start. The model card warns it can hallucinate and repeat phrases on
short or noisy segments; this file produced no repetition loops. It is English
only.

**Neither is a replacement, for different reasons.** Cohere and Granite say
less and lose on the words. Voxtral marks up sentences better than what ships
and recognizes less of them, and the punctuation exists to serve speaker
attribution, which needs the words to be there first. Moonshine loses on
sentence ends, which are the one thing speaker attribution cannot do without,
loses on words to the pipeline, and would add a CPU-bound engine alongside the
Neural Engine one for English only.

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
   The failures are not spread evenly: Parakeet v2 is one of the unanchored arms
   in 10 of the 12 windows, Cohere in 7, the FluidAudio v3 batch arm in 5 and the
   pipeline in 2. The drop is still right — those excerpts are text from another
   part of the meeting — but it means v2's judge figures come only from windows
   where it could be anchored. With all 80 windows kept, v2's dropped-content mean
   rises from 0.55 to 0.93 under the first judge and from 1.41 to 4.03 under the
   second, where it falls to last.

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

**Set `MIMICSCRIBE_ITN_NUMBERS=1` for every command below.** From v1.0.0-rc.29
the app keeps spoken numbers as words in the saved transcript, and that includes
`--itn-text`, the normalizer both scorers call. Without the variable, numbers are
never put on one basis, and the WER and number tables come out wrong without
any error: pooled WER for the FluidAudio v3 int8-v2 batch arm reads about 18%
instead of 16.37%. The WER scorer caches normalized text by binary, not by
environment, so delete `./cache/itn_text` if you ran it once without the variable. The pipeline arm
was measured on v1.0.0-rc.27 (app `5c847cf5`); a later release decodes
differently, so a re-decode with the current app is a new measurement, not a
reproduction of that row. The raw-row arms' number figures also move with the
normalizer version, as the Numbers section says.

```bash
export MIMICSCRIBE_ITN_NUMBERS=1
```

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

```bash
# 3b. Parakeet Unified, streaming at the 1,120 ms setting. The models directory
#     holds FluidInference/parakeet-unified-en-0.6b-coreml; the runner never
#     downloads, so a missing encoder fails loudly. --offline runs the model's
#     own offline path instead, which is how the two-file control was made.
swift run --package-path scripts/parakeet_version_probe unified_probe \
  --arm unified-1120 --tier 1120 --models-dir <model directory> \
  --out benchmark/output/bakeoff-unified-1120 \
  --audio <file.wav> [--audio <file.wav> ...]
```

The runner stops if the words it writes out differ from the model's own
transcript, retries a file whose decode a CoreML timeout interrupted, and keeps
files an earlier interrupted run already finished.

The probe package pins the same FluidAudio fork revision the app pins
(`MimicScribe/FluidAudio` @ `3c2cd9c2…`, the sha in the Provenance table), by
URL, so `swift run` resolves it on any machine with network access.

```bash
# 3c. Nemotron Speech Streaming, 1,120 ms tier (headline; repeat with
#     nemotron_coreml_2240ms and --arm nemotron-2240 for the secondary row).
#     --models-dir is the tier directory itself
#     (FluidInference/nemotron-speech-streaming-en-0.6b-coreml at revision
#     e673531c, folder nemotron_coreml_1120ms); the runner never
#     downloads. The package pins upstream FluidAudio v0.17.4, so it is built
#     apart from step 3's package. Same stop-on-mismatch, retry and resume
#     behavior as step 3b.
swift build -c release --package-path scripts/nemotron_probe
scripts/nemotron_probe/.build/release/nemotron_probe \
  --arm nemotron-1120 --out benchmark/output/bakeoff-nemotron-1120 \
  --models-dir <model directory>/nemotron_coreml_1120ms \
  --audio <file.wav> [--audio <file.wav> ...]
```

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

# 6c. The Parakeet Ultra section. Content basis for any number of arms, on the
#     files they share (filled pauses and casual forms folded on both sides;
#     the last column also drops number words and digits on both sides):
python3 scripts/score_content_wer.py "ultra=<dir>" "v3=<dir>" "cohere=<dir>" ...
#     Its number table: every arm's rows through step 6b on ONE build, then
#     the current number scorer (the Numbers table above used an earlier one;
#     this directory's git history has it).

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
  --run-a judge_gemini/grades.jsonl --run-b judge_haiku/grades.jsonl --max-anchor-wer 1.0 \
  --out judge_agreement.json
```

```bash
# 6d. The Nemotron section. Every arm through step 6b on one build, then the
#     number scorer, the content basis and the judge on those copies.
for arm in <nemotron dir> <unified dir> <batch dir> <ultra pipeline dir>; do
  python3 scripts/bakeoff/itn_normalize_arm.py $arm <normalized>/$(basename $arm)
done
python3 scripts/score_corpus_wer.py --arms <ultra> <pipeline> <batch> <unified> <nemotron> \
  --labels ultra_pipe v3_pipe v3_batch unified nemotron --per-file --stratify
python3 scripts/score_content_wer.py "ultra=<dir>" "batch=<dir>" "unified=<dir>" "nemotron=<dir>"
python3 scripts/score_number_fidelity.py --corpus <normalized>/nemotron/per-file --json-out numbers_nemotron.json
# The judge: one judge, four arms, through the agy CLI (a Gemini subscription,
# no API key). Same seed and windows as run 4. Each call runs in a scratch
# directory and is killed after 15 minutes; concurrency up to 10 is allowed
# for this provider only. A row whose call failed is kept as a parse failure
# and is re-asked by deleting it from grades.jsonl and re-running with --resume.
python3 scripts/bakeoff/judge_transcripts.py \
  --arms ultra=<norm>/ultra batch=<norm>/batch unified=<norm>/unified nemotron=<norm>/nemotron \
  --provider agy --model gemini-3.8-flash-medium --concurrency 6 \
  --balanced-positions --max-excerpt-ratio 1.5 --out judge_agy
# Anchor check, per-window means, event counts, self-agreement and position
# effect for ONE run (judge_agreement.py needs two):
python3 scripts/bakeoff/judge_single_summary.py judge_agy/grades.jsonl --max-anchor-wer 1.0
python3 scripts/bakeoff/punct_recount.py nemotron=<dir> batch=<dir> unified=<dir>
```

```bash
# 6b. Normalize a raw arm's rows once, line for line, through the same pass the
#     saved transcript goes through, so the number scorer and the judge read
#     every arm on one basis. The WER scorer does this itself at scoring time.
#     Row text out, one line per row, then back into the same JSON shape.
MIMICSCRIBE_DATA_DIR=./sandbox /Applications/MimicScribe.app/Contents/MacOS/mimicscribe \
  --itn-text --in <rows.txt> --out <rows.itn.txt>
```

```bash
# 8. The two streaming probes, IS1009a only. The probe runners are internal;
#    these are the scorers, run over one directory per arm, each holding
#    per-file/IS1009a_after_orphan.json.
python3 scripts/score_corpus_wer.py --arms <batch> <pipeline> <voxtral> <moonshine> \
  --labels batch pipeline voxtral moonshine --stratify
python3 scripts/bakeoff/ami_punctuation_accuracy.py \
  <batch> <pipeline> <voxtral> <moonshine> --files IS1009a
python3 scripts/bakeoff/backchannel_stripped_deletion.py --file IS1009a \
  --arms batch=<dir> pipeline=<dir> voxtral=<dir> moonshine=<dir>
```

Pin the output directory of each arm explicitly. The scorers default to the
newest directory on disk, which silently picks up whatever else has been run
since.

## Provenance

Every arm decoded and scored on 2026-09-01, on the same 27 files, by the same
two scorers on the same basis. The number-fidelity table was re-scored on
2026-09-03, on one binary; that section says so and carries the caveat. The
Parakeet Unified arm was decoded and scored on 2026-09-25 by the scorers in
this directory, on a later build of the normalizer; its section says what that
moves. The Nemotron arm was decoded and scored on 2026-09-28 the same way, with
the comparator rows re-scored on the same build (its section says by how much
they moved) and a fresh judge run.

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
| Voxtral Realtime 4B (probe, 1 file, 2026-09-06) | `mlx-community/Voxtral-Mini-4B-Realtime-2602-4bit` | 4-bit, 480 ms delay | 2026-02-04 | MLX on Apple Silicon GPU |
| Parakeet Ultra, MimicScribe pipeline (arm, 27 files, 2026-09-27) | `moondream/parakeet-ultra` via `FluidInference/parakeet-ultra-coreml` | CoreML `95eaa59a`, int8 encoder; app `964e6af11` | 2026-09-22 | CoreML on Apple Silicon, same pipeline as the v3 rows |
| Parakeet Unified 0.6B (arm, 27 files, 2026-09-25) | `nvidia/parakeet-unified-en-0.6b` via `FluidInference/parakeet-unified-en-0.6b-coreml`, int8 | streaming encoder `70_7_7` weights `f145c8da…`, offline encoder `f984b815…`; FluidAudio same | 2026-04-07 | CoreML on Apple Silicon, `StreamingUnifiedAsrManager`, 1,120 ms |
| Nemotron Speech Streaming 0.6B (arm, 27 files, 2026-09-28) | `nvidia/nemotron-speech-streaming-en-0.6b` via `FluidInference/nemotron-speech-streaming-en-0.6b-coreml`, int8 encoder; the checkpoint behind the conversion is not stated (NVIDIA `main` is 2026-03-13, branch `nemotron-speech-streaming-jan2026` is the January one) | headline: 1,120 ms tier, encoder weights `409df110…`; secondary: 2,240 ms tier, `0c67d14d…`; CoreML repository revision `e673531c…`; FluidAudio upstream `21493f8dac5a97e65742e6ff26f42f164c2fda0f` (v0.17.4) | 2025-12-17 | CoreML on Apple Silicon, library-default compute units, `StreamingNemotronAsrManager`, M1 Max |
| Moonshine Streaming Medium (probe, 1 file, 2026-09-21) | `moonshine-ai/moonshine-streaming-medium`, vendor build `quantized_26_08_21` | vendor download, not the Hugging Face weights; `moonshine-voice` 0.1.5, 200 ms chunks | 2026-01-06 | ONNX Runtime 1.23.2, CPU |

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
`benchmark/output/bakeoff-nemo-{v2,v3}`, the Parakeet Unified arm at
`benchmark/output/bakeoff-unified-1120`, the Nemotron arm at
`benchmark/output/bakeoff-nemotron-1120` (headline) and `bakeoff-nemotron-2240`
(its judge run at `benchmark/output/bakeoff-judge-agy-gemini-3.8-flash-medium`). The MimicScribe pipeline arm is
`benchmark/output/swift_pipeline_2026-08-30T021253Z`, decoded by app commit
`5c847cf5`, which shipped as v1.0.0-rc.27. The Parakeet Ultra arm is
`benchmark/output/swift_pipeline_2026-09-27T213110Z`, a cold decode by app
commit `964e6af11`; its same-build v3 row replays v3's recorded window decodes
through that build's pipeline.

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
