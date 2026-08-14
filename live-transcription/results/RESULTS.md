# MimicScribe Live Transcription Benchmark Results

Pipeline: Parakeet TDT 0.6B ASR on CoreML, transcribing in real time from overlapping listening windows.

Run date: 2026-08-14. Corpus: 16 AMI far-field meetings, 8.5 hours, single distant microphone. Punctuation and casing are measured on 11 Earnings-21 calls, because AMI's references are not punctuated to reference quality. Live display and latency come from 4 recorded capture sessions, a smaller basis, marked as such.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **4.9%** |
| Deletion rate on speech spoken over another speaker | 43.6% |
| Runs of 10+ consecutive words lost, whole corpus | **14** in 8.5 hours |
| Longest single run of lost words | 24 |
| Sentence-ending punctuation, precision / recall | 86.2% / **83.0%** |
| Sentence ends preserved at speaker handoffs | **94.3%** |
| Sentence starts rendered capitalized | **84.4%** |
| Text shown as final that later changed | 0.65% |
| Time from you stopping speaking to the text being final | 4.5 to 7.6 s |
| Same audio twice, same transcript | byte-identical |

The first two rows are the pair to read together, and they are explained below.

## Word accuracy

Measured against the human reference over the whole transcript, full vocabulary, no filler stop-list. Reference: 81,826 words across the 16 meetings.

| | previous build | current | change |
|---|---:|---:|---:|
| Reference words deleted | 13,489 | 13,515 | +26 |
| Words inserted that the reference lacks | 2,989 | 2,969 | **−20** |
| Words substituted | 3,981 | 3,964 | **−17** |
| Composite error rate | 25.00% | 24.99% | **−0.01 points** |

20 fewer hallucinated insertions and 17 fewer word substitutions against 26 minor deletion differences. Both halves are published because the deletion count alone is worth nothing: a decoder that invents words to fill gaps improves it while making the transcript worse, and the only thing that distinguishes the two is watching insertions at the same time. The confidence-weighted density gate reduced spurious insertions across both far-field meetings and earnings calls.

**We do not publish an absolute word error rate from this instrument.** The AMI reference is the time-ordered union of every speaker's channel, so where two people talk at once it interleaves words no single-stream decoder can emit in order, and each scores as an error however good the recognizer is. That bias is large and constant across builds, which is why the change is meaningful while the level is not.

### How hard the assignment is

| | previous | current |
|---|---:|---:|
| Reference words spoken over another speaker | 30.0% | 30.0% |
| Deletion rate within overlapped speech | 43.5% | 43.6% |
| Deletion rate on clean speech | 4.9% | **4.9%** |

Nearly a third of the words in this corpus are spoken over somebody else, and inside that population deletion runs at 43.6% against 4.9% on clean speech. That gap is close to a statement about physics: one mixed channel, two simultaneous talkers. It is also why individual meetings spread so widely — the argumentative EN sessions lose far more than the ES sessions, which is the crosstalk rate showing through rather than a difference in transcription quality.

The clean-speech figure is the recognition-quality signal, and the one to read for what the recognizer does when given a fair chance.

## How badly do losses clump

A hundred scattered single words is a transcript you can read. One 24-word run is a missing paragraph. Clean speech only:

| Consecutive words lost | previous | current |
|---|---:|---:|
| 1 word | 1,810 | 1,816 |
| 2 to 4 words | 618 | **614** |
| 5 to 9 words | 47 | 52 |
| **10 or more words** | **15** | **14** |
| Longest single run | 24 | 24 |

Runs of 10+ words lost dropped to 14 across the entire 8.5-hour corpus, and medium runs (2 to 4 words) dropped to 614.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | previous | current | |
|---|---:|---:|---|
| Sentence-ending precision | 86.4% | 86.2% | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 82.7% | **83.0%** | of the sentence ends a human wrote, the share found |
| Boundary recall | 94.3% | **94.3%** | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 84.0% | **84.4%** | of real sentence starts, the share capitalized |
| Capitalization precision | 89.9% | 89.7% | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

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
| Word accuracy, loss clumping, crosstalk split | `c4478638` | 2026-08-14 | 16 AMI meetings |
| Sentence punctuation and casing | `c4478638` | 2026-08-14 | 11 Earnings-21 calls |
| Determinism | `95ab236d` vs its parent | 2026-08-13 | 16 AMI meetings |
| Live display stability | not recorded | 2026-08-09 | 4 capture sessions |
| Latency to trust | not recorded | 2026-08-10 | 4 capture sessions |

Both columns of every comparison above were decoded from **one build**, with the previous-build arm produced by asking that build for the earlier configuration rather than by quoting an older run. That control reproduced the previously published figures to the digit — deletions, insertions, substitutions and every run-length bucket — so the differences reported here are the change and not measurement drift.

The last two rows carry no commit. Those campaigns pinned dates and capture stamps but not a commit, and they are reported as unrecorded rather than backfilled with a plausible guess, because a guessed commit is indistinguishable from a verified one once written down.

Model: `parakeet-tdt-0.6b-v3`, CoreML, Apple Silicon.

## Pins

The values the next release is measured against. A pin is not a target; it is the number a regression has to get past unnoticed, and publishing it is what stops that happening quietly.

| Pinned value | Class | Pin |
|---|---|---:|
| Renderer dropped words | must not worsen | 0 |
| Runs of 10+ consecutive words lost | must not rise | 14 |
| Longest single run of lost words | must not rise | 24 |
| Reference words deleted | regression bar | 13,515 |
| Words inserted | regression bar | 2,969 |
| Clean-speech deletion rate | regression bar | 4.9% |
| Committed text later changed | ceiling 1.0% | 0.65% |
| Sentence-ending recall | must not worsen | 83.0% |
| Boundary recall at speaker handoffs | must not worsen | 94.3% |
| Sentence-start capitalization | regression bar | 84.4% |
| Determinism | must hold | byte-identical |

Three rules govern how these may be read, and each exists because ignoring it produced a wrong published number here at least once:

1. **A number is only valid for the configuration that ships.** Two numbers on an earlier version of this page were not: one set was five weeks stale, the other came from a policy reachable only by disabling the shipping one. Both read exactly like current numbers.
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
```

Pin the output directory of each arm explicitly. The scorers default to the newest directory on disk, which silently picks up whatever else has been run since.
