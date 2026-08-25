# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR on CoreML, transcribing in real time from overlapping listening windows.

Run date: 2026-08-25. Corpus: 16 AMI far-field meetings, 8.5 hours, single distant microphone. Punctuation and casing are measured on 11 Earnings-21 calls, because AMI's references are not punctuated to reference quality. Live display and latency come from 4 recorded capture sessions, a smaller basis, marked as such.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **3.7%** |
| Deletion rate on speech spoken over another speaker | 41.2% |
| Runs of 10+ consecutive words lost, whole corpus | **5** in 8.5 hours, 4 of them at the edge of crosstalk |
| Longest single run of lost words | 14, at a crosstalk edge |
| Sentence-ending punctuation, precision / recall | 86.1% / 83.0% |
| Sentence ends preserved at speaker handoffs | 94.4% |
| Sentence starts rendered capitalized | 84.8% |
| Text shown as final that later changed | 0.65% |
| Time from you stopping speaking to the text being final | 4.5 to 7.6 s |
| Same audio twice, same transcript | byte-identical |

The first two rows are the pair to read together, and they are explained below.

## Word accuracy

Measured against the human reference over the whole transcript, full vocabulary, no filler stop-list. Reference: 81,826 words across the 16 meetings.

| | previous build | current | change |
|---|---:|---:|---:|
| Reference words deleted | 13,515 | 12,214 | **−1,301** |
| Words inserted that the reference lacks | 2,969 | 3,352 | +383 |
| Words substituted | 3,964 | 4,170 | +206 |
| Composite error rate | 24.99% | 24.12% | **−0.87 points** |

1,301 more reference words recovered, at a cost of 383 more insertions and 206 more substitutions — 712 fewer errors on balance. Both halves are published because the deletion count alone is worth nothing: a decoder that invents words to fill gaps improves it while making the transcript worse, and the only thing that distinguishes the two is watching insertions at the same time.

This release is a deliberate trade in that direction, and the insertion row is the price. A rebuilt quantization of the recognizer's encoder recovers speech the previous one dropped, and emits more words in doing so. The effect is spread across 14 of the 16 meetings rather than concentrated in a few, it tracks recovery closely, and each inserted word comes with 3.4 recovered ones. The inserted tokens are ordinary short function words, not invented names or phrases. Earnings calls move the other way on the same build: insertions fall from 4,065 to 3,874 while deletions fall from 2,063 to 1,568.

**We do not publish an absolute word error rate from this instrument.** The AMI reference is the time-ordered union of every speaker's channel, so where two people talk at once it interleaves words no single-stream decoder can emit in order, and each scores as an error however good the recognizer is. That bias is large and constant across builds, which is why the change is meaningful while the level is not.

### How hard the assignment is

| | previous | current |
|---|---:|---:|
| Reference words spoken over another speaker | 30.0% | 30.0% |
| Deletion rate within overlapped speech | 43.6% | **41.2%** |
| Deletion rate on clean speech | 4.9% | **3.7%** |

Nearly a third of the words in this corpus are spoken over somebody else, and inside that population deletion runs at 41.2% against 3.7% on clean speech. That gap is close to a statement about physics: one mixed channel, two simultaneous talkers. It is also why individual meetings spread so widely — the argumentative EN sessions lose far more than the ES sessions, which is the crosstalk rate showing through rather than a difference in transcription quality.

The clean-speech figure is the recognition-quality signal, and the one to read for what the recognizer does when given a fair chance.

## How badly do losses clump

A hundred scattered single words is a transcript you can read. One 24-word run is a missing paragraph or exchange. Clean speech only:

| Consecutive words lost | previous | current |
|---|---:|---:|
| 1 word | 1,816 | **1,739** |
| 2 to 4 words | 614 | **543** |
| 5 to 9 words | 52 | **32** |
| **10 or more words** | **14** | **5** |
| Longest single run | 24 | **14** |

Runs of 10+ words lost dropped from 14 to 5 across the entire 8.5-hour corpus, and the longest single run fell from 24 words to 14. Every bucket improved.

**Where the remaining five are.** Four of the five begin or end within a second of a
word two people spoke at once, against 41% for single-word losses. Long losses
concentrate at crosstalk rather than spreading through ordinary speech. Overlapped
speech itself is scored separately and excluded from this table.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | previous | current | |
|---|---:|---:|---|
| Sentence-ending precision | 86.2% | 86.1% | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 83.0% | 83.0% | of the sentence ends a human wrote, the share found |
| Boundary recall | 94.3% | 94.4% | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 84.4% | **84.8%** | of real sentence starts, the share capitalized |
| Capitalization precision | 89.7% | 89.1% | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

Punctuation is flat this release. The one row that moved is capitalization precision, and it moved because the row above it did: the build capitalizes 158 more words, 95 of them correctly, which buys sentence-start capitalization and costs a little precision. That is the counter-check doing its job rather than a rule quietly trading one for the other.

Terminal punctuation is not cosmetic here. Sentence boundaries become the windows used for speaker embedding, so a punctuation change is also a speaker-identification change, which is why recall carries a hard floor rather than being traded for precision.

## Live display stability

"Text shown as final stays final." The display commits in two tiers and the promise attaches only to the committed tier.

| | |
|---|---:|
| Committed text that later changed | **0.65%** |
| Provisional tail text that later changed | 7.33% |
| Words the renderer dropped entirely | **0** |
| Revisions inside the trailing 60 s, per corpus | 745 (68% single-word) |

The roughly 11x gap between the tiers is the entire case for showing them differently. The committed number was 0.39% in an earlier release and rose to 0.65% deliberately: a faster commit policy roughly halved the time to a final transcript and cost some stability. Both halves of that trade are published rather than only the half that improved.

Basis: 4 recorded capture sessions, not the 16-meeting corpus. **These two sections are the one place on this page where the numbers predate the current build** — they are replayed from recorded sessions, so refreshing them means re-recording rather than re-scoring. See provenance.

## Latency to trust

How long after you stop speaking until the words stop moving.

| Capture | Pauses measured | Median pause to commit |
|---|---:|---:|
| ES2004a | 52 | 7.6 s |
| IS1009b | 36 | 4.5 s |
| IS1009c | 58 | 5.6 s |
| TS3003a | 85 | 5.5 s |

**4.5 to 7.6 s**, against **10.3 to 11.0 s** under the earlier commit policy. This is what the stability trade above was paid for.

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
| Short duplicated spans, punctuation-identical ("on Friday. on Friday.") | **6 episodes** |
| Words shown fused with a fragment of themselves ("Turningning") | **2 episodes**, 0 reaching the final text |
| Words shown that were never spoken | 732 |
| Spoken words that never appeared on screen | 162 |

The last two rows are scored on the five sessions with a verbatim script
(24.2 minutes, 3,337 script words) and count every distinct rendering that
ever appeared, including provisional text later corrected — and a misheard
word charges both rows at once, so they are dominated by ordinary
misrecognitions. They are regression bars, not quality claims: what they
exist to catch is a build that makes the live view invent or withhold more
than this one does.

The fusion row is new in this run. Transcription reads overlapping windows of
audio, and where two windows are stitched a word can be rendered with a piece
of itself attached. Both episodes here were corrected before the text settled;
the median one was on screen for about three seconds. The check needs the
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

One of the five scripted sessions is a numbers-heavy earnings call and carries
58 of the 146; the other four are conversational and carry 18 to 24 each. This
is a thin basis for a number-accuracy claim and is published as a regression
bar, not as a quality figure.

## Determinism

Same audio in, byte-identical transcript out, verified rather than asserted. Two independently compiled binaries, built from different trees, produced byte-identical output across all 16 meetings — identical not only in text but in per-token frame indices.

Sampling-based systems cannot claim this, and it is load-bearing for everything above: a comparison between two configurations means nothing unless each is reproducible alone.

## Corpora and caveats

- **[AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)** (CC BY 4.0), 16 meetings, 8.5 hours, far-field single distant microphone, which is the hard condition. Scored against the union of all speaker channels *including* overlapped speech, the hardest fair reading.
- **[Earnings-21](https://github.com/revdotcom/speech-datasets)**, 11 earnings calls with Rev.com human references including punctuation and casing.

Benchmark numbers come from fixed public corpora, not from your meetings. Real meetings vary, and accents, cross-talk, background noise and call-audio quality all change what the recognizer hears in the first place.

Far-field results are not comparable to near-field ones. Blending the two produces a figure that describes neither.

The word-accuracy figures above are AMI only. Earnings-21 appears on this page for punctuation and casing, and the two corpora are not aggregated.

## Provenance

| Axis | Commit | Measured | Basis |
|---|---|---|---|
| Word accuracy, loss clumping, crosstalk split | `31d125a4` | 2026-08-25 | 16 AMI meetings |
| Sentence punctuation and casing | `31d125a4` | 2026-08-25 | 11 Earnings-21 calls |
| Determinism | `95ab236d` vs its parent | 2026-08-13 | 16 AMI meetings |
| Live display stability | not recorded | 2026-08-09 | 4 capture sessions |
| Latency to trust | not recorded | 2026-08-10 | 4 capture sessions |
| Live view against the script | `4a0dfb86` | 2026-08-25 | 7 capture sessions (script rows: 5) |

Both columns of every comparison above were decoded from **one build**, with the previous-build arm produced by asking that build for the earlier configuration rather than by quoting an older run. That control reproduced the previously published figures to the digit — deletions, insertions, substitutions and every run-length bucket — so the differences reported here are the change and not measurement drift.

The last two rows carry no commit. Those campaigns pinned dates and capture stamps but not a commit, and they are reported as unrecorded rather than backfilled with a plausible guess, because a guessed commit is indistinguishable from a verified one once written down.

Model: `parakeet-tdt-0.6b-v3`, CoreML, Apple Silicon.

## Pins

The values the next release is measured against. A pin is not a target; it is the number a regression has to get past unnoticed, and publishing it is what stops that happening quietly.

| Pinned value | Class | Pin |
|---|---|---:|
| Renderer dropped words | must not worsen | 0 |
| Runs of 10+ consecutive words lost | must not rise | 5 |
| Longest single run of lost words | must not rise | 14 |
| Reference words deleted | regression bar | 12,214 |
| Words inserted | regression bar | 3,352 |
| Clean-speech deletion rate | regression bar | 3.7% |
| Committed text later changed | ceiling 1.0% | 0.65% |
| Sentence-ending recall | must not worsen | 83.0% |
| Boundary recall at speaker handoffs | must not worsen | 94.4% |
| Sentence-start capitalization | regression bar | 84.8% |
| Doubled phrases visible live | regression bar | 2 |
| Punctuation-identical duplicated spans | regression bar | 6 |
| Words shown fused with a fragment of themselves | regression bar | 2 |
| Words shown never spoken | regression bar | 732 |
| Spoken words never shown | regression bar | 162 |
| Spoken quantities rendered as a different quantity | regression bar | 1 |
| Spoken quantities dropped | regression bar | 8 |
| Numbers shown that nobody said | regression bar | 4 |
| Determinism | must hold | byte-identical |

The live-view bars are enforced per session with a measured tolerance for
replay timing jitter (the same recording replayed twice moves the word
counts by a few dozen), plus a tighter cap on the total across sessions —
uncorrelated jitter and a systematic regression separate cleanly there.

The live-view and number bars moved onto a seven-session basis this run, up
from six, so they are not comparable to the previous page's figures as a
change. On the six sessions common to both, duplicated spans went from 8 to 4
and the two script rows moved by 11 and 3 words — differences inside the
replay jitter named above, which is why no improvement is claimed from them.

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

# word accuracy, crosstalk split, loss clumping
scripts/score_corpus_wer.py --arms <A> <B> --labels base curr --stratify
scripts/asr_bench.py       --arms <A> <B> --labels base curr

# punctuation and casing
scripts/punctuation_accuracy.py --compare <A> <B>

# the live view against the script (replays the recorded sessions live)
scripts/score_live_invariants.py --all <replay-root> --json-out chg.json
scripts/score_live_invariants.py --compare <pinned baseline> chg.json
```

Pin the output directory of each arm explicitly. The scorers default to the newest directory on disk, which silently picks up whatever else has been run since.
