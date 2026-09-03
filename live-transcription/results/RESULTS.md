# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR on CoreML, transcribing in real time from overlapping listening windows.

Run date: 2026-08-29. Corpus: 16 AMI meetings, 8.5 hours, headset mixdown (every speaker's close-talk microphone summed to one channel). Punctuation and casing are measured on 11 Earnings-21 calls, because AMI's references are not punctuated to reference quality. Live display and latency come from 4 recorded capture sessions, a smaller basis, marked as such.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **3.4%** |
| Deletion rate on speech spoken over another speaker | 41.0% |
| Runs of 10+ consecutive words lost, whole corpus | **4** in 8.5 hours, all four at the edge of crosstalk |
| Longest single run of lost words | 14, at a crosstalk edge |
| Sentence-ending punctuation, precision / recall | 86.6% / 83.6% |
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
| Reference words deleted | 11,957 | 11,944 | −13 |
| Words inserted that the reference lacks | 3,375 | 3,379 | +4 |
| Words substituted | 4,066 | 4,072 | +6 |
| Composite error rate | 23.89% | 23.89% | 0.00 points |

Flat. Thirteen fewer deletions, four more insertions, six more substitutions across 8.5 hours: this release changed nothing about recognition on far-field meetings, and the table says so. Both halves are still published because the deletion count alone is worth nothing: a decoder that invents words to fill gaps improves it while making the transcript worse, and the only thing that distinguishes the two is watching insertions at the same time. On the earnings calls the same build moves a little: deletions 1,636 → 1,619, insertions 1,924 → 1,882, error rate 8.50% → 8.44%.

**What changed in how words are counted.** The saved transcript writes numbers, money, percentages and spelled acronyms the way a reader expects ("2020", "$115 million", "5%", "DNLG"), while the human reference spells them out ("twenty twenty", "D_N_L_G_"). Until this page, the reference was compared as written, so every correctly transcribed number or acronym scored as one or more errors — a bias that grew the moment the transcript started normalizing its own rows, and read as a loss of 327 words on this same pair. Both sides now go through the transcript's own normalizer before counting, which is why the reference is 81,198 tokens rather than 81,826 and why the previous-build column reads 11,957 deletions where the previous page read 12,214. The old counting is kept as an option and reproduces that page's numbers to the digit; the scorers print which basis they used and the regression gate refuses to compare across the two.

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
| 1 word | 1,734 | 1,749 |
| 2 to 4 words | 474 | 471 |
| 5 to 9 words | 30 | 30 |
| **10 or more words** | **4** | **4** |
| Longest single run | 14 | 14 |

Flat: four runs of 10+ words on both builds, the longest 14 words on both, every bucket within a few dozen.

**Where the four are.** The same four sites on both builds (EN2002a, EN2006b, ES2008c, ES2016a), each beginning or ending within a second of a word two people spoke at once, against 41% for single-word losses; one of them grew from 10 to 14 words. The previous page counted a fifth, a speaker spelling "n l s s d" letter by letter — ten tokens in the reference as written and two under the normalizer now applied to both sides. Long losses concentrate at crosstalk rather than spreading through ordinary speech. Overlapped speech itself is scored separately and excluded from this table.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | previous | current | |
|---|---:|---:|---|
| Sentence-ending precision | 86.1% | 86.6% | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 83.0% | 83.6% | of the sentence ends a human wrote, the share found |
| Boundary recall | 94.4% | 94.3% | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 84.8% | 84.8% | of real sentence starts, the share capitalized |
| Capitalization precision | 89.1% | 89.3% | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

Four rows moved up a little: 105 more sentence ends placed where a human placed one, 9 fewer placed where none belonged, 26 fewer sentence starts left lowercase. Boundary recall moved down by one: 39 speaker handoffs without a sentence end, against 38 before. That row carries a hard floor, and the floor moved — by one boundary out of roughly 13,900 — so it is published as a decline rather than rounded away, and the next release is measured against 94.3%, not 94.4%.

Terminal punctuation is not cosmetic here. Sentence boundaries become the windows used for speaker embedding, so a punctuation change is also a speaker-identification change, which is why recall carries a hard floor rather than being traded for precision.

## Live display stability

"Text shown as final stays final." The display commits in two tiers and the promise attaches only to the committed tier.

| | |
|---|---:|
| Committed text that later changed | **0.33%** |
| Provisional tail text that later changed | 5.76% |
| Words the renderer dropped entirely | **0** |
| Revisions inside the trailing 60 s, per corpus | 393 (71% single-word) |

The roughly 17x gap between the tiers is the entire case for showing them differently. The committed number was 0.39% two releases ago, rose to 0.65% deliberately when a faster commit policy roughly halved the time to a final transcript, and is 0.33% on this build — with the time to a final transcript having given part of that speed back (next section). Both halves of that trade are published, in both directions.

Basis: 4 recorded capture sessions, not the 16-meeting corpus. Both of these sections were re-recorded on this build; they replay recorded sessions, so refreshing them means re-recording rather than re-scoring. See provenance.

## Latency to trust

How long after you stop speaking until the words stop moving.

| Capture | Pauses measured | Median pause to commit |
|---|---:|---:|
| ES2004a | 50 | 9.9 s |
| IS1009b | 33 | 7.6 s |
| IS1009c | 56 | 8.8 s |
| TS3003a | 81 | 6.9 s |

**6.9 to 9.9 s**, against **4.5 to 7.6 s** on the build measured three weeks earlier and **10.3 to 11.0 s** under the earlier commit policy. This is the number on this page that moved the wrong way in this release: each session waits 1.4 to 3.2 s longer for its text to stop moving than it did on the previous measurement, while committed text changes half as often. Which of the changes in between is responsible has not been isolated; it is published as measured and is the open item on this page.

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
| Short duplicated spans, punctuation-identical ("on Friday. on Friday.") | **3 episodes** |
| Words shown fused with a fragment of themselves ("Turningning") | **0 episodes** |
| Words shown that were never spoken | 718 |
| Spoken words that never appeared on screen | 166 |

The last two rows are scored on the five sessions with a verbatim script
(24.2 minutes, 3,337 script words) and count every distinct rendering that
ever appeared, including provisional text later corrected — and a misheard
word charges both rows at once, so they are dominated by ordinary
misrecognitions. They are regression bars, not quality claims: what they
exist to catch is a build that makes the live view invent or withhold more
than this one does.

Transcription reads overlapping windows of audio, and where two windows are
stitched a word can be rendered with a piece of itself attached. None
appeared in this run; the previous run's two were corrected within the second
they appeared. The check needs the
system word list to run at all, and reports nothing rather than guessing when
it is absent — several hundred ordinary English words have the same shape as a
fusion, so counting them without a dictionary would produce noise.

### Numbers on screen

Spoken quantities are checked by value rather than spelling, so "$115 million"
and "one hundred and fifteen million dollars" count as the same number.

| | |
|---|---:|
| Spoken quantities that reached the screen intact | 137 of 146 |
| Rendered as a different quantity | 1 |
| Dropped | 8 |
| Numbers shown that nobody said | 4 |
| Numbers damaged where two decoding windows were stitched | 0 in the final view (1 shown briefly, then repaired) |

One of the five scripted sessions is a numbers-heavy earnings call and carries
58 of the 146; the other four are conversational and carry 18 to 24 each. This
is a thin basis for a number-accuracy claim and is published as a regression
bar, not as a quality figure.

### Numbers in the saved transcript

The live view is one pass over the audio; the transcript you keep is the one
that matters. The same by-value check is run on the saved transcript of the
11 Earnings-21 calls against Rev.com's human references — 2,867 spoken
quantities, the densest public substrate for numbers we have.

| | |
|---|---:|
| Spoken quantities that reached the saved transcript intact | 2,769 of 2,867 (96.6%) |
| Rendered as a different quantity | 39 |
| Dropped | 59 |
| Numbers in the transcript that nobody said | 112 |

By kind of number:

| | scored | intact | different | dropped | nobody said |
|---|---:|---:|---:|---:|---:|
| Plain counts and amounts | 1,032 | 976 | 23 | 33 | 86 |
| Money | 364 | 348 | 9 | 7 | 3 |
| Percentages | 408 | 401 | 5 | 2 | 4 |
| Years | 310 | 305 | 1 | 4 | 0 |
| Fiscal quarters | 442 | 439 | 1 | 2 | 3 |
| Ordinals | 235 | 224 | 1 | 10 | 13 |

Forty-two years in four of the human references are truncated ("first
quarter of 201."); a transcript that shows the full year there is counted as
correct, and the one such year the transcript missed is reported but not
scored. The previous release read 2,768 of 2,867 intact under the same rules, with 43
rendered as a different quantity, 56 dropped and 112 invented. Four fewer wrong
quantities and four fewer stitch-point defects (11 → 7) are the number work of the
last week landing on a full decode; the three more dropped were each traced — a
pairing artifact in the scorer on "two fifty" beside "$250 million", one bare
"hundred" left behind by a new limit on import segment length, one stutter kept
verbatim — and none is a change in how numbers are handled. Where two decoding
windows are stitched, the same figure read as digits on one side and as words on
the other used to be kept twice or cut in half; that is the stitch-point class,
now seven across the corpus. This table is what a
change to number handling is gated on, by kind of number, and it is published
as a regression bar; the substrate is prepared remarks read from a page, so it
says nothing about numbers spoken over another speaker.

## Determinism

Same audio in, byte-identical transcript out, verified rather than asserted. Two independently compiled binaries, built from different trees, produced byte-identical output across all 16 meetings — identical not only in text but in per-token frame indices.

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
| Word accuracy, loss clumping, crosstalk split | `5c847cf5` | 2026-08-29 | 16 AMI meetings |
| Sentence punctuation and casing | `5c847cf5` | 2026-08-29 | 11 Earnings-21 calls |
| Determinism | `95ab236d` vs its parent | 2026-08-13 | 16 AMI meetings |
| Live display stability | `ecce55f3` | 2026-08-29 | 4 capture sessions |
| Latency to trust | `ecce55f3` | 2026-08-29 | 4 capture sessions |
| Live view against the script | `5c847cf5` | 2026-08-29 | 7 capture sessions (script rows: 5) |
| Numbers in the saved transcript | `5c847cf5` | 2026-08-29 | 11 Earnings-21 calls (2,867 quantities) |

The previous-build column is the arm the previous version of this page was pinned on, decoded on 2026-08-25 at `31d125a4` (v1.0.0-rc.26) and re-scored with today's scorers. Under the old counting basis those scorers reproduce that page's published figures to the digit — for its own previous column, 13,515 / 2,969 / 3,964 and 24.99% — which is what makes the arm a valid comparator; both columns above are then scored on the same new basis, so the differences reported are the build and not the counting.

Every row now carries a commit. Until this refresh the display-stability and latency rows carried none: those campaigns pinned dates and capture stamps but not a commit, and the page reported them as unrecorded rather than backfilled with a plausible guess, because a guessed commit is indistinguishable from a verified one once written down. The two rows were re-recorded for this refresh at `ecce55f3`, the merge of the re-pin bundle onto `5c847cf5` (no change to the transcription path between them).

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
| Punctuation-identical duplicated spans | regression bar | 3 |
| Words shown fused with a fragment of themselves | regression bar | 0 |
| Words shown never spoken | regression bar | 718 |
| Spoken words never shown | regression bar | 166 |
| Spoken quantities rendered as a different quantity | regression bar | 1 |
| Spoken quantities dropped | regression bar | 8 |
| Numbers shown that nobody said | regression bar | 4 |
| Saved-transcript quantities rendered as a different quantity | must not rise, per call | 39 |
| Saved-transcript quantities dropped | must not rise, per call | 59 |
| Saved-transcript numbers nobody said | must not rise, per call | 112 |
| Determinism | must hold | byte-identical |

The live-view bars are enforced per session with a measured tolerance for
replay timing jitter (the same recording replayed twice moves the word
counts by a few dozen), plus a tighter cap on the total across sessions —
uncorrelated jitter and a systematic regression separate cleanly there.

The live-view rows were re-measured on the same seven sessions (one replay
of each) at the release build: duplicated spans 5 to 3 (4 to 3 once spans the
script itself repeats are discounted, as the gate does), fusions 2 to 0, the
two script rows 740 to 718 and 164 to 166, every number row unchanged, and
one more speaker handoff without a sentence end (10 to 11 across the seven).
Each of those movements is inside the replay jitter named above, so no
change in either direction is claimed from them; they are the values the
next release is measured against.

Three rules govern how these may be read, and each exists because ignoring it produced a wrong published number here at least once:

1. **A number is only valid for the configuration that ships, on the corpus it claims.** Two numbers on an earlier version of this page were not: one set was five weeks stale, the other came from a policy reachable only by disabling the shipping one. Both read exactly like current numbers. A third case was caught before it reached this page — a punctuation figure computed over 2 of the 11 calls — which is why the gate now checks how many files produced a number before comparing it to anything.
2. **Deletion-only measures never appear alone.** A mechanism that recovers words by inventing them improves every deletion count here, so insertions are published beside deletions or neither is published.
3. **An unchanged result must be proven to have run.** A cached decode once reported an entire change as having no effect with every gate green. Both arms above reported a fully cold decode, and an arm that reports no cache misses is discarded rather than believed.

Every number on this page is produced by a committed script that a later release can re-run. An earlier version carried a family of figures whose analysis code was never committed and whose input was not archived, which meant they could never be checked for drift; they were removed rather than restated.

## Reproducing

The scorers are the same ones that gate changes internally, unmodified — there is no public-only scoring path.

```bash
# one decode per arm, 16 AMI meetings + 11 Earnings-21 calls
swift build -c release
.build/release/mimicscribe --benchmark-pipeline-corpus --corpora ami,earnings21 --files <list>

# word accuracy, crosstalk split, loss clumping — both call the built binary's
# --itn-text mode to put reference and rows on one basis, and print which basis
# they used; --raw is the pre-2026-08-29 counting and does not match the pins
scripts/score_corpus_wer.py --arms <A> <B> --labels base curr --stratify
scripts/asr_bench.py       --arms <A> <B> --labels base curr

# punctuation and casing
scripts/punctuation_accuracy.py --compare <A> <B>

# the live view against the script (replays the recorded sessions live)
scripts/score_live_invariants.py --all <replay-root> --json-out chg.json
scripts/score_live_invariants.py --compare <pinned baseline> chg.json

# numbers in the saved transcript, by value, 11 Earnings-21 calls
scripts/score_number_fidelity.py --corpus <A>/per-file --json-out chg.json
scripts/score_number_fidelity.py --corpus-compare <pinned baseline> chg.json
```

Pin the output directory of each arm explicitly. The scorers default to the newest directory on disk, which silently picks up whatever else has been run since.
