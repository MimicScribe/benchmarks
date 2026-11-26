# MimicScribe Speech Recognition & Live Transcription Benchmark Results

Pipeline: MimicScribe's spoken-form fine-tune of Parakeet Ultra (a post-training of Parakeet TDT 0.6B v3) on CoreML, with the four fine-tuned top Conformer encoder layers exported in native FP16, transcribing in real time from overlapping listening windows on Apple Silicon.

This page is the unified speech-recognition hub. Every section below reflects the shipped FP16 top-4 spoken-form model (`9e462b9f`), with all live streaming pipeline axes, long-form number-seam stress tests, live display captures, quiet-machine footprint measurements, and determinism re-measured on the `270d9cc4b` release build (**2026-11-26**). Multilingual results across all 25 languages live in [multilingual/RESULTS.md](../../multilingual/RESULTS.md); the historical cross-model comparison lives in [asr-bakeoff/RESULTS.md](../../asr-bakeoff/RESULTS.md).

## Speech model evaluation (FP16 top-4, `9e462b9f`)

Every row below compares unmodified stock Parakeet Ultra (`95eaa59a`) against MimicScribe's retrained spoken-form FP16 top-4 model (`9e462b9f`) through the same release build on the same Apple Silicon Mac, with no transcription caches.

| Evaluation | Stock Parakeet Ultra | Spoken-form FP16 top-4 | Change |
|---|---:|---:|---:|
| **Unseen multi-speaker meetings** (46 held-out AMI meetings, ~282k words, raw WER) | 22.70% | **22.11%** | **−0.59 pp** (−1,653 net errors) |
| **Unseen earnings calls — numbers right** (10 held-out Earnings-22 calls, 2,425 figures) | 2,169 (89.4%) | **2,225 (91.8%)** | **+56 figures** (−2.31 pp value error) |
| **Unseen earnings calls — currencies** (171 sites: kept / mangled / front-only / stray) | 141 / 0 / 26 / 0 | **145 / 0 / 0 / 0** | +4 kept, **0** front-only/mangled/stray |
| **Unseen earnings calls — periods after numbers lost** (332 sentence-end sites) | 70 | **74** | +4 (close to stock) |
| **22 real earnings calls — numbers right** (5,606 figures, Earnings-21 + Earnings-22) | 5,349 (95.4%) | **5,404 (96.4%)** | **+55 figures** (95% CI +32 to +78) |
| **Paired 27-file content WER** (16 AMI + 11 Earnings-21, 161,660 content words) | 13.67% *(AMI-16: 20.71%, E21-11: 7.61%)* | **13.68%** *(AMI-16: 20.63%, E21-11: 7.69%)* | +0.01 pp *(AMI-16 −0.08 pp)* |
| **Multilingual WER across 25 languages** ([FLEURS](../../multilingual/RESULTS.md), 6,039 clips, 4,912 number-neutral) | 10.06% | **10.04%** | **−0.03 pp** (95% CI −0.08 to +0.03) |
| **Non-English spoken numbers** (24 languages, 1,786 figures) | 1,604 (89.81%) | **1,604 (89.81%)** | **0.00 pp** (0 English leaks in 6,399 clips) |
| **Processing speed** (46 unseen AMI meetings, 28.5 h audio, M1 Max ANE) | 52.9× realtime | **63.9× realtime** | faster on Neural Engine |

**What improved in the retrained FP16 top-4 model (`9e462b9f`):**
- **Repeats and live-tail stability:** One-frame rapid repeats across 22 real calls sit at stock levels (**0.45** vs. **0.43** per 1,000 words), and filler timing stays anchored near stock rather than collapsing to single-frame spikes.
- **Periods after numbers:** Preserves sentence-ending periods immediately after numbers close to stock on both synthetic tests and unseen earnings calls (`74` vs. `70` lost out of 332 unseen sentence-end sites).
- **Fast speech and background noise:** At `1.4×` playback speed on long-form number stress audio, **639 of 661** figures stay intact (vs. 606 on stock in the same `270d9cc4b` build); under steady background noise on Apple Neural Engine FP16, token timing stays stable (**0%** timing collapse across all tested contexts).
- **Honest caveats:** Held-out AMI and Earnings-22 file identifiers are kept sealed so they cannot become tuning targets (only aggregate totals are published). The unseen Earnings-22 set contains 0 GBP sites, so British pound coverage comes from the 22-call development set and synthetic checks rather than the sealed holdout. Non-English multilingual testing on FLEURS covers single-sentence read speech only, not multi-speaker meetings.

## Long-form number-seam and fast-speech stress (Break-It)

Real earnings calls test spoken numbers, but most figures sit inside a single decoding window. Break-It is our synthetic multi-minute stress suite: dense spoken figures, currencies, percentages, dates, and identifiers placed across overlapping listening-window boundaries, including a `1.4×` fast-speech pass. Both columns below were decoded on the same `270d9cc4b` release binary on Apple Silicon with no transcription cache.

| Stress suite | Figures | Stock Parakeet Ultra | Spoken-form FP16 top-4 | Corrupted | Invented | False repeats |
|---|---:|---:|---:|---:|---:|---:|
| **Multilingual seams (Break-It v1)** — 24 meetings (EN/DE/ES/FR) | 2,448 | 1,806 (73.8%) | **1,860 (76.0%, +54)** | 338 → **285** | 197 → **184** | 14 → **3** |
| **Held-out voices (Break-It v3)** — 7 meetings (EN/DE/ES) | 931 | 856 (91.9%) | **881 (94.6%, +25)** | 72 → **48** | 25 → **22** | 8 → **0** |
| **Held-out English edge cases (Break-It v4)** — 12 meetings (EN) | 642 | 634 (98.8%) | **641 (99.8%, +7)** | 8 → **1** | 8 → **1** | 1 → **0** |
| **Fast speech at `1.4×` playback** — 5 EN meetings | 661 | 606 (91.7%) | **639 (96.7%, +33)** | 51 → **22** | 17 → **8** | 4 → **0** |

Per-language breakdown on the multilingual stress suites (figures intact, stock → spoken-form):
- **Break-It v1:** English `899 → 946 / 1,122` (`80.1% → 84.3%`, +47), German `433 → 434 / 510`, Spanish `362 → 363 / 510`, French `112 → 117 / 306`.
- **Break-It v3 (held-out voices):** English `611 → 640 / 661` (`92.4% → 96.8%`, +29), German `127 → 127 / 138`, Spanish `118 → 114 / 132` (−4).
- **Fast speech (`1.4×`):** Dropped figures fall from `4` on stock to **`0`** on the spoken-form model, and false repeats fall from `4` to **`0`**.

**Caveats:** Break-It uses synthetic text-to-speech audio, not human speakers. Break-It v1 includes voices that overlap the synthetic training voices, whereas v3 and v4 use held-out voices. On v3 Spanish, the spoken-form model gets 4 fewer figures right than stock (`114` vs. `118` of `132`: 1 dropped and 17 corrupted vs. 0 dropped and 14 corrupted on stock), so non-English number accuracy is tracked alongside FLEURS (`1,604 / 1,786`, exact stock parity) rather than claimed as a win on synthetic stress alone.

---

## Live streaming pipeline benchmarks (2026-11-26 — `270d9cc4b`)

Run date: **2026-11-26**, clean release binary of `270d9cc4b` comparing stock Parakeet Ultra (`95eaa59a`) and the shipped spoken-form FP16 top-4 model (`9e462b9f`), with all transcription and window caches disabled. Corpus: 16 AMI meetings (8.5 hours, headset mixdown — every speaker's close-talk microphone summed to one channel) and 11 Earnings-21 calls (10.3 hours, Rev.com human references with punctuation and casing). Live display stability, latency, and the live view against the script were re-recorded on `270d9cc4b` with the shipped model.

## Headline numbers

| Metric | Value |
|---|---:|
| **Deletion rate on clean (non-overlapped) speech** | **3.0%** *(1.4% on single-meeting IS1009a, fillers stripped)* |
| Deletion rate on speech spoken over another speaker | 38.7% |
| Runs of 10+ consecutive words lost, whole corpus | **0** in 8.5 hours |
| Longest single run of lost words | **8** |
| Sentence-ending punctuation, precision / recall | **89.2%** / 80.6% |
| Sentence ends preserved at speaker handoffs | **96.2%** |
| Sentence starts rendered capitalized | 82.1% *(capitalization precision **89.8%**)* |
| Spoken numbers intact in the saved transcript | **97.7%** *(2,815 of 2,882; 0 window-stitch errors)* |
| Text shown as final that later changed | **0.28%** |
| Time from you stopping speaking to the text being final | **5.2 to 8.9 s** |
| Determinism across cold repeat runs (27 files) | **Byte-identical** (27 of 27) |

The first two rows are the pair to read together, and they are explained below.

## Word accuracy

Measured against the human reference over the whole transcript, full vocabulary, no filler stop-list. Reference: 81,202 tokens across the 16 AMI meetings, after both sides go through the same number-and-acronym normalizer, with numbers converted to digits on both sides (the product writes English numbers as words, and the reference writes digits).

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 | Change |
|---|---:|---:|---:|
| Reference words deleted | 11,338 | **11,139** | **−199** |
| Words inserted that the reference lacks | 3,289 | 3,326 | +37 |
| Actionable insertions (excluding convention/coverage gaps) | 1,304 | **1,304** | **0** |
| Words substituted | 4,145 | **4,102** | **−43** |
| Composite error rate (AMI-16, normalized) | 23.12% | **22.87%** | **−0.25 pp** |

The fine-tune deletes 199 fewer reference words and makes 43 fewer substitutions across 8.5 hours of meetings for 37 more total insertions, with actionable insertions completely flat (`1,304 → 1,304`). All 16 AMI meetings improve (`16 better, 0 worse`).

**On the 11 Earnings-21 calls (97,504 normalized reference tokens):** deletions fall `2,264 → 2,068` (−196), total insertions move `1,661 → 1,718` (+57), actionable insertions fall `768 → 763` (−5), and normalized error rate falls `8.78% → 8.65%` (−0.13 pp).

**Content WER across all 27 files (18.8 hours, 161,660 content words, filled pauses folded and numbers excluded):** stock Parakeet Ultra reads `13.67%` (AMI-16 `20.71%`, Earnings-21 `7.61%`) and the shipped FP16 top-4 fine-tune reads **`13.68%`** (AMI-16 **`20.63%`**, −0.08 pp, 95% CI −0.14 to −0.03; Earnings-21 `7.69%`, +0.08 pp, CI −0.02 to +0.21). Across those 18.8 hours, the shipped pipeline drops **9,567** content words — compared with `9,705` on stock Ultra in the same build and `14,260` on stock Parakeet v3 through FluidAudio's batch runner (**33% fewer words dropped**; see [the ASR bake-off](../../asr-bakeoff/RESULTS.md) for the historical multi-model table). On the single meeting (`IS1009a`) used in the streaming-model bake-off, clean-speech deletion with fillers stripped is **`1.4%`** (`18 of 1,273` words, vs. `1.5%` on stock Ultra in the same build and `7.1%` on the best real-time streaming model tested).

**We do not publish an absolute AMI word error rate as a standalone headline.** The AMI reference is the time-ordered union of every speaker's channel, so where two people talk at once it interleaves words no single-stream decoder can emit in order, and each scores as an error however good the recognizer is. That bias is large and constant across builds, which is why the paired delta is meaningful while the raw AMI level is not.

### How hard the assignment is

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 |
|---|---:|---:|
| Reference words spoken over another speaker | 30.1% | 30.1% |
| Deletion rate within overlapped speech | 39.0% | **38.7%** |
| Deletion rate on clean speech | 3.2% | **3.0%** |

Nearly a third of the words in this corpus are spoken over somebody else, and inside that population deletion runs at 38.7% against 3.0% on clean speech. That gap is close to a statement about physics: one mixed channel, two simultaneous talkers. The fine-tune improves both populations.

## How badly do losses clump

A hundred scattered single words is a transcript you can read. One 14-word run is a missing exchange. Clean speech only (AMI-16):

| Consecutive words lost | Stock Parakeet Ultra | Spoken-form FP16 top-4 |
|---|---:|---:|
| 1 word | 1,820 | **1,793** |
| 2 to 4 words | 465 | **435** |
| 5 to 9 words | 13 | **12** |
| **10 or more words** | **0** | **0** |
| Longest single run | 8 | 8 |
| Total clean-speech words lost | 2,966 | **2,855** (−111) |

Every non-zero bucket shrinks. There is still no run of 10 or more consecutive lost words in 8.5 hours, and the longest run is 8 words.

**This table counts deletions only** and never appears without the insertion count beside it, for the reason given above.

## Sentence punctuation and casing

*11 Earnings-21 calls, token-aligned against Rev.com human references. Scored on the speaker turns a reader actually sees.*

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 | |
|---|---:|---:|---|
| Sentence-ending precision | 88.8% | **89.2%** | of the sentence ends written, the share a human also placed |
| Sentence-ending recall | 81.1% | 80.6% | of the sentence ends a human wrote, the share found |
| Boundary recall | 95.4% | **96.2%** | sentence ends at a speaker handoff, the ones that stop two speakers running together |
| Sentence-start capitalization | 82.3% | 82.1% | of real sentence starts, the share capitalized |
| Capitalization precision | 89.2% | **89.8%** | counter-check: a rule that capitalizes indiscriminately buys the row above and loses this one |

Compared against stock Ultra on the same `270d9cc4b` build, the spoken-form model cuts spurious sentence ends (`465 → 433`), cuts missed speaker-handoff boundaries (`32 → 26`, pushing boundary recall from `95.4%` to **`96.2%`**), and improves capitalization precision (`89.2% → 89.8%`). Missed sentence ends are nearly identical (`861 → 863`, +2 across 11 calls); the reported recall ratio dips by 0.5 points (`81.1% → 80.6%`) primarily because the aligned-token denominator is smaller when spoken-form numbers are written as words rather than matching digit reference tokens one-to-one (`tp 3,695 → 3,578`). Stray punctuation before lowercase words across all 27 files also drops (`65 → 55` stray periods, `4 → 1` stray `?`/`!`). Terminal punctuation is not cosmetic: sentence boundaries set the windows used for speaker embedding, so a punctuation change is also a speaker-identification change.

## Live display stability

"Text shown as final stays final." The display commits in two tiers and the promise attaches only to the committed tier. Re-recorded **2026-11-26** on `270d9cc4b` with the shipped FP16 top-4 model across 4 recorded meeting sessions (`ES2004a`, `IS1009b`, `IS1009c`, `TS3003a`):

| | Previous published (2026-09-27, stock Ultra) | Current (2026-11-26, FP16 top-4) |
|---|---:|---:|
| Committed text that later changed | 0.31% | **0.28%** *(541 of 191,049)* |
| Provisional tail text that later changed | 4.95% | **4.26%** *(3,951 of 92,741)* |
| Words the renderer dropped entirely | 0 | **0** |
| Revisions inside the trailing 60 s, per corpus | 423 *(69% single-word)* | **368** *(78% single-word, 94% ≤2 words)* |

The committed tier holds at **0.28%** (well inside the 1.0% ceiling and ~15× steadier than the provisional tail). Across the four sessions, committed edits range from `0.18%` (`ES2004a`) to `0.38%` (`IS1009c`), and trailing-60s revision events drop from `423` to `368`.

## Latency to trust

How long after you stop speaking until the words stop moving. Measured on the same four 2026-11-26 capture sessions as the stability table above (stability and latency are always published together because committing faster trades against revision rate):

| Capture | Pauses measured | Previous (2026-09-27, stock Ultra) | Current (2026-11-26, FP16 top-4) |
|---|---:|---:|---:|
| ES2004a | 46 | 8.4 s | **7.6 s** |
| IS1009b | 30 | 6.7 s | **5.8 s** |
| IS1009c | 62 | 8.5 s | 8.9 s |
| TS3003a | 88 | 4.9 s | 5.2 s |

Median pause-to-commit runs **5.2 to 8.9 s** (with median time to settle text at `0.0 to 1.6 s`). Pause counts differ slightly between builds because the recognizer places sentence pauses where speech stops.

## The live view against the script

Everything above scores the final transcript or the four single-channel captures. These rows score what is on screen while you speak during two-channel live recordings (microphone plus system audio) replayed at 1× through the full live pipeline, with the rendered transcript sampled once per second. Replayed twice on a debug build of `270d9cc4b` (**2026-11-26**, FP16 top-4 model `9e462b9f`; pass 1 vs. pass 2: 0 regressions).

We report both the **7 original sessions** (32.9 minutes, for continuity with earlier releases) and the **expanded 12-session suite** (44.0 minutes, which adds five extra number-dense, clock-time, and multilingual recordings):

| | 7 original sessions (32.9 min) | All 12 sessions (44.0 min) |
|---|---:|---:|
| Doubled phrases (4+ words) visible in the live view | **2 episodes** | **2 episodes** |
| Short duplicated spans, punctuation-identical ("on Friday. on Friday.") | **6 episodes** | **6 episodes** |
| Words shown fused with a fragment of themselves ("Turningning") | **0 episodes** | **0 episodes** |
| Words shown that were never spoken | 608 | 677 |
| Spoken words that never appeared on screen | 160 | 173 |
| Already-shown words rewritten under the reader (flicker, case counts) | 278 of 5,035 (**5.5 per 100**) | 332 of 5,973 (**5.6 per 100**) |
| Punctuation changed on words that stayed | 206 (**4.1 per 100**) | 249 (**4.2 per 100**) |
| A short repeat ("short short") that reached the saved transcript | 18 | 23 |
| The other speaker's words appearing on this channel's row | 2 episodes, 0 saved *(tracked)* | 2 episodes, 0 saved *(tracked)* |
| A bare fragment of a word ("ight") on screen | 6 episodes, 4 saved | 6 episodes, 4 saved |

Against the previously published 2026-09-27 replay on the same 7 sessions, doubled phrases drop `4 → 2`, live word flicker drops `7.2 → 5.5 per 100` words shown (`361 → 278`), words shown that were never spoken drop `636 → 608`, and short repeats reaching the saved transcript drop `19 → 18`. Bare word fragments rise `2 → 6` (4 saved) and punctuation changes on unchanged words move `3.7 → 4.1 per 100`; both are re-pinned directly here rather than hidden.

The shown/spoken rows are scored on the scripted sessions and count every distinct rendering that ever appeared, including provisional text later corrected. A misheard word charges both rows at once, so they are regression bars rather than absolute quality claims.

**Text that vanishes and comes back.** A separate counter watches for the live view getting *shorter* — words disappearing from the screen and returning a moment later. On this replay: **0 episodes** across the 7 original sessions (down from 2 previously) and **1 episode** across all 12 sessions (worst drop 4 words, 5 s absence). Because replay timing jitter moves small episode counts by a few between passes, read it as "near zero per half hour of replay" rather than an exact constant.

### Numbers on screen

Spoken quantities are checked by numeric value rather than spelling, so "$115 million" and "one hundred fifteen million dollars" count as the same number.

| | 7 original sessions (5 scripted) | All 12 sessions |
|---|---:|---:|
| Spoken quantities that reached the screen intact | **139 of 147 (94.6%)** | **213 of 227 (93.8%)** |
| Rendered as a different quantity | **1** | **1** |
| Dropped | 7 | 13 |
| Numbers shown that nobody said | 1 | 8 |
| Numbers damaged where two decoding windows were stitched | **0** | **0** |

Across all 12 sessions, live-screen numeric fidelity jumps from `194 of 228` (`85.1%`, 6 corrupted, 28 dropped, 22 invented on the prior 2026-11-14 pin) to **`213 of 227` (`93.8%`, 1 corrupted, 13 dropped, 8 invented, 0 splice defects)**. Even with 12 sessions, this remains a small scripted sample published as a live regression bar; the large public number evaluation is below.

### Numbers in the saved transcript

The live view is one pass over the audio; the transcript you keep is the one that matters. The same by-value check (scorer v10) is run on the saved transcript of the 11 Earnings-21 calls against Rev.com's human references — ~2,880 spoken quantities, both arms decoded on `270d9cc4b`:

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 |
|---|---:|---:|
| Spoken quantities that reached the saved transcript intact | 2,787 of 2,878 (96.8%) | **2,815 of 2,882 (97.7%)** |
| Rendered as a different quantity | 34 | **28** |
| Dropped | 57 | **39** |
| Numbers in the transcript that nobody said | 63 | **58** |
| Numbers damaged where two decoding windows were stitched | 10 | **0** |

By kind of number, on the shipped spoken-form FP16 top-4 model:

| | Scored | Intact | Different | Dropped | Nobody said |
|---|---:|---:|---:|---:|---:|
| Plain counts and amounts | 1,017 | 978 | 13 | 26 | 44 |
| Money | 362 | 351 | 8 | 3 | 2 |
| Percentages | 408 | 401 | 6 | 1 | 1 |
| Years | 309 | 305 | 0 | 4 | 0 |
| Fiscal quarters | 442 | 441 | 0 | 1 | 1 |
| Ordinals | 265 | 259 | 1 | 5 | 6 |

*(Smaller categories in the by-kind breakdown: 64 compound quantities [63 intact, 1 dropped, 1 nobody said], 14 basis-point figures [14 intact, 1 nobody said], and 3 clock times [3 intact, 2 nobody said] — accounting for the remaining 4 invented figures to reach 58 total. The by-kind table sums to 2,884 scored / 41 dropped vs. 2,882 / 39 in the headline table because two truncated-year items at clip boundaries are excluded from the headline totals while remaining in the category breakdown.)*

Every defect class drops simultaneously against stock Ultra on the same build: corrupted figures `34 → 28`, dropped figures `57 → 39`, invented figures `63 → 58`, and window-stitch splice defects **`10 → 0`**. This table is gated per call and by category; because the substrate is prepared financial remarks read cleanly, it does not measure numbers spoken over another speaker.

## Words the recovery layer adds

Where the decoder emitted nothing over voiced audio, or where a pause triggers an end-of-turn recovery pass, a repair pass puts words back. That pass can add text, so deletion counts alone are blind to its errors.

| | Resolved against the alignment | Said within a second |
|---|---:|---:|
| Words added per meeting-hour (reached saved transcript) | 157.9 | 157.9 |
| of which the reference supports | 129.3 | 112.7 |
| **of which wrong** | **28.7** | 45.2 |
| Precision | **81.8%** | 71.4% |

27 files, 18.83 hours (`270d9cc4b`, spoken-form FP16 top-4). The logged recovery passes added 3,109 words and 2,974 of them reached the saved transcript; the table is over those 2,974 words because they are the ones a reader sees. Compared against stock Ultra on the same build (`2,999` reached, `29.5` wrong/h, `81.5%` aligned precision), the spoken-form model is slightly cleaner.

**Added and later removed: 135 (`7.17/h`).** These 135 words were removed by a later pass before anything was saved, so no reader saw them. They are reported on their own line rather than folded into the reader-visible error rate above.

By logged repair class, on the headline aligned definition (words reaching the saved transcript):

| | Added | Supported | Wrong | Precision |
|---|---:|---:|---:|---:|
| End-of-turn recovery pass | 2,729 | 2,287 | 442 | **83.8%** |
| Silence the decoder left over voiced audio | 245 | 147 | 98 | 60.0% |

**Scope caveat:** On the current merge pipeline, the recovery ledger instruments end-of-turn and voiced-hole repairs; window-stitch repairs are not yet emitted into this ledger and are therefore excluded from these totals (tracked for the next pipeline milestone). Do not compare these totals directly against earlier 2026-10-14 ledger totals that logged window stitches and voiced holes without the end-of-turn pass.

## Hallucinated rows

The subset of recovery additions that reads as invented text rather than a misheard word: a stretch of added words with nothing right in it. The unit is a **run** — the added words of one repair decision, split wherever two consecutive words are more than 1.5 s apart.

| | Resolved against the alignment | Said within a second |
|---|---:|---:|
| All-wrong runs per meeting-hour | **4.73** | 6.43 |
| Words in them, per meeting-hour | **17.63** | 27.40 |
| Of 3 words or more, per meeting-hour | **1.75** | 2.60 |

89 all-wrong runs of 475 total runs on the headline aligned definition, carrying 332 words, with 33 runs of three words or longer over 18.83 hours (stock Ultra on the same build: `5.15` runs/h, `17.84` words/h, `1.70` runs ≥3w/h). Counted by whole repair decision rather than run, the same rows read 46 all-wrong decisions of 360 (63 on the surface definition). 15 of the 89 all-wrong runs consist entirely of words removed before saving; they stay in this count because the unit is what the repair pass produced.

This class remains open: simple admission rules measured against it cost more true recovered words than wrong ones removed, so it is published and ratcheted rather than claimed solved.

## Invented phrases over silence (primary decode)

The hallucinated-rows section only inspects recovery passes; text emitted by the primary decoder itself over silent room tone never enters the recovery ledger. We measure it separately on AMI-16 (8.51 hours) by checking every unsupported run of 3 or more content words whose audio RMS sits at least 25 dB below the meeting's speech level (separating silence hallucinations from untranscribed human speech).

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 |
|---|---:|---:|
| Over-silence runs per meeting-hour | 2.23 *(19 runs)* | **2.35** *(20 runs)* |
| Words in them, per meeting-hour | 14.3 *(122 words)* | **14.7** *(125 words)* |
| Runs in the final 15 seconds of a file | 2 | **2** |

Both columns run on `270d9cc4b`. Compared against the prior 2026-10-14 spoken-form release (`2.70` runs/h, `16.2` words/h, `2` tail runs), silence hallucinations drop by 3 runs and 13 words over 8.5 hours. The two tail runs sit at the end-of-recording finalize decode on `EN2006b` and are pinned with zero tolerance so the finalize path cannot silently widen.

## Saved-transcript duplicates

"It repeats itself" is a common question about meeting transcripts, so we measure every span of two or more words ending one saved row and opening the next across all 27 files (18.83 hours).

| | Stock Parakeet Ultra | Spoken-form FP16 top-4 |
|---|---:|---:|
| Repeated spans per meeting-hour | 2.97 *(56 spans)* | **3.08** *(58 spans)* |
| Share that sit on a speaker change | 98.2% *(55 of 56)* | **98.3%** *(57 of 58)* |
| Removed by the shipped intra-row de-duplication rule | 0 | **0** |

The speaker-change share is the finding, not the count. Nearly every span (`57 of 58`) is two speakers saying the same short phrase in turn ("Good morning." / "Good morning.", "Thank you." / "Thank you."). Collapsing those would delete real conversation, so this metric is tracked rather than ratcheted and the shipped de-duplication rule operates only inside a row.

## Wrong figures by magnitude

A wrong number is not one thing: `$17 million` for `$17.5 million` is a small error, while `$40 billion` written as `$40 million` is off by a factor of a thousand. This splits the 28 corrupted figures from the saved-transcript table above by ratio (`|rendered / reference|`, folded to `>= 1`):

| Wrong by a factor of | Stock Parakeet Ultra | Spoken-form FP16 top-4 | Status |
|---|---:|---:|---|
| Under 10× | 19 | **18** | tracked |
| 10× to under 1,000× | 10 | **8** | tracked |
| 1,000× or more | 5 | **2** | tracked, named below |

Every member of the `1,000× or more` row on the shipped model:

| The reference says | The transcript says | What it is |
|---|---|---|
| `100` | `hundred billion` | the speaker corrected themselves ("100 billion… $100 million") and the scorer paired the correction against the first token |
| `$40 billion` | `forty million dollars` | a real disagreement about the scale word at the site (same site as on stock Ultra) |

Stock Ultra on the same build has both of these plus three additional `1,000×+` corruptions the spoken-form model gets right (including `$1 billion $295 million` rendered as `$1,295,000` and `200` rendered as `200,000`).

**What is enforced instead** is the narrower bar where both transcript and reference name a scale word (`hundred`/`thousand`/`million`/`billion`/`trillion`) and disagree on the largest scale word: **1 site** (`$40 billion` → `forty million dollars`), pinned at `1` with zero tolerance.

## Per-file sign counts

Corpus totals can hide a split where a few files carry the whole gain while the rest regress. Because the batch pipeline is byte-deterministic, file-to-file sign counts are the honest denominator for the paired stock vs. spoken-form changes above (scored on each file's normalized error rate):

| Delta on this page (Stock → Spoken-form FP16 top-4) | Files | Better | Worse | Unchanged |
|---|---:|---:|---:|---:|
| Word accuracy (16 AMI meetings) | 16 | **16** | **0** | 0 |
| Earnings calls (11 Earnings-21 calls) | 11 | **8** | 3 | 0 |
| **Both corpora together (27 files)** | **27** | **24** | **3** | **0** |

The three files that moved slightly worse are `4366522` (+0.35 pp), `4366893` (+0.05 pp), and `4367535` (+0.60 pp).

## Added decodes

**None this release.** No extra decoding site was added to the product path; every recovery number above comes from existing decode passes.

## Determinism

Same audio in, byte-identical transcript out, verified rather than asserted. On **2026-11-26** (`270d9cc4b`, shipped FP16 top-4 model `9e462b9f`), all 27 files (16 AMI + 11 Earnings-21) were decoded twice from cold with no ASR cache: **27 of 27** saved-transcript JSON files agreed **byte for byte (`0` diffs)**.

## Speed and memory on Apple Silicon

Quiet-machine release measurements on an M1 Max (10-core, 32 GB, macOS 27.0) with the shipped FP16 top-4 model (`9e462b9f`; memory, CPU, and pipeline throughput on `270d9cc4b`, first-launch compile on `005e86e2d` with the same `9e462b9f` weights):

| Measurement | Value | Basis |
|---|---:|---|
| Idle memory (`phys_footprint`) | **239 MB** | 90 s idle against real DB (peak 250 MB) |
| Active meeting memory (`phys_footprint`) | **~600 MB** *(592–603 MB steady)* | Live 2-channel replay (ASR + diarization + echo cancellation; 734 MB warmup peak) |
| Active meeting CPU | **33% median** *(38% mean of 1 core)* | 60 s steady-state live replay (~3–4% of 10-core CPU) |
| First-launch Neural Engine compile | **~27 s** *(26.7 s)* | Empty compile cache, one-time per model revision (`005e86e2d`, 2026-11-25) |
| Batch pipeline throughput | **41.9×–56.5× realtime** *(27 files)* | Cold-ASR pipeline 41.9×; warm-embedding repeat 56.5×; 46-AMI holdout 63.9× |

Full methodology and how to measure your own machine with `footprint` are documented in [Performance & Memory](https://mimicscribe.app/docs/performance).

## Corpora and caveats

- **[AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)** (CC BY 4.0), 16 meetings, 8.5 hours, the Mix-Headset mixdown: every speaker's close-talk microphone summed to one channel, so overlapped speech is fully present and there is no room reverberation. Scored against the union of all speaker channels *including* overlapped speech, the hardest fair reading.
- **[Earnings-21](https://github.com/revdotcom/speech-datasets)**, 11 earnings calls (10.3 hours) with Rev.com human references including punctuation and casing.
- **Break-It synthetic stress sets** (v1, v3, v4, and `1.4×` fast-speech): synthetic TTS multi-minute audio packed with cross-window spoken numbers, currencies, dates, and identifiers.

Benchmark numbers come from fixed corpora, not from your meetings. Real meetings vary, and accents, cross-talk, room reverberation, background noise, and call-audio quality all change what the recognizer hears.

This is not a far-field room-microphone condition. A single distant microphone in a reverberant room scores worse, and results on the two are not comparable; an earlier version of this page described AMI-16 as far-field, which was wrong (corrected 2026-09-03 after hash-matching the audio against the AMI mirror).

AMI-16 and Earnings-21 are reported separately for every axis where they measure different things (overlap and loss clumping on AMI; punctuation, casing, and saved numbers on Earnings-21), and shown both per-corpus and pooled on the 27-file content WER and per-file sign-count tables.

## Provenance

| Axis | Commit / Binary | Measured | Basis |
|---|---|---|---|
| Unseen AMI holdout (raw WER & speed) | `27d658215705` (model `9e462b9f`) | **2026-11-25** | 46 unseen AMI meetings (~282k words, aggregate-only) |
| Unseen Earnings-22 holdout (numbers, currency, stops) | `27d658215705` (model `9e462b9f`) | **2026-11-25** | 10 unseen Earnings-22 calls (2,425 figures, aggregate-only) |
| 22 real earnings calls (numbers, repeats, stability) | `27d658215705` (model `9e462b9f`) | **2026-11-25** | 22 calls (5,606 figures) |
| Multilingual WER & non-English numbers | `5dbccc68543c` (model `9e462b9f`) | **2026-11-25** | 25 languages on FLEURS (6,039 + 800 clips) |
| Break-It long-form seams & `1.4×` fast speech | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | v1 (24), v3 (7), v4 (12), `1.4×` (5 EN) — paired stock vs. spoken |
| Word accuracy, content WER, loss clumping, crosstalk split | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 16 AMI meetings + 11 Earnings-21 calls (cold decode) |
| Sentence punctuation and casing | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 11 Earnings-21 calls (post-merge rows) |
| Numbers in the saved transcript & magnitude split | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 11 Earnings-21 calls (2,882 quantities, scorer v10) |
| Recovery additions & hallucinated rows | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 27 files, 18.83 h, ledgered run (end-of-turn + voiced-hole) |
| Invented phrases over silence | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 16 AMI meetings, 8.51 h |
| Saved-transcript duplicates & per-file sign counts | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 27 files, 18.83 h, paired cold decode |
| Determinism | `270d9cc4b`, decoded twice cold | **2026-11-26** | 27 files (27/27 byte-identical) |
| Live display stability & latency to trust | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | 4 freshly recorded capture sessions |
| Live view against the script & live numbers | `270d9cc4b`, debug build (model `9e462b9f`) | **2026-11-26** | 12 two-channel sessions × 2 passes (7 original shown beside 12) |
| Footprint, CPU & pipeline speed | `270d9cc4b` (model `9e462b9f`) | **2026-11-26** | M1 Max 10-core 32 GB, macOS 27.0, quiet machine |
| First-launch Neural Engine compile | `005e86e2d` (model `9e462b9f`) | **2026-11-25** | M1 Max 10-core 32 GB, macOS 27.0, empty compile cache |

**One build, two models.** Every paired comparison above runs stock Parakeet Ultra (`95eaa59a`) and the spoken-form FP16 top-4 fine-tune (`9e462b9f`) through the exact same release binary with fresh per-arm sandboxes and no transcription cache.

**The scoring basis is stated because it matters.** The product writes English numbers as spoken words, so corpus word-accuracy scorers align numbers on one basis (digit-normalized scoring on both sides for the pipeline word-accuracy and loss-clumping rows; content-word Levenshtein excluding numbers on the 27-file content WER row; raw full-vocabulary WER on the 46-meeting unseen AMI holdout). All number rows score the transcript as saved by numeric value.

Current model: MimicScribe's spoken-form FP16 top-4 fine-tune of Parakeet Ultra (`MimicScribe/parakeet-ultra-spoken-coreml` at `9e462b9f`, top-4 Conformer encoder layers in FP16 plus decoder and joint weights on `FluidInference/parakeet-ultra-coreml` at `95eaa59a`), Apple Silicon. The stock Parakeet Ultra column is `95eaa59a` unmodified.

## Pins

The values the next release is measured against. A pin is not a target; it is the number a regression has to get past unnoticed, and publishing it is what stops that happening quietly.

| Pinned value | Class | Pin |
|---|---|---:|
| Renderer dropped words | must not worsen | 0 |
| Runs of 10+ consecutive words lost | must not rise | 0 |
| Longest single run of lost words | must not rise | 8 |
| Reference words deleted (AMI-16, ITN) | regression bar | 11,139 |
| Words inserted, actionable (AMI-16, ITN) | regression bar | 1,304 |
| Clean-speech deletion rate (AMI-16) | regression bar | 3.0% |
| Committed text later changed | ceiling 1.0% | 0.28% |
| Sentence-ending recall (E21-11 rows) | must not worsen | 80.6% |
| Boundary recall at speaker handoffs | must not worsen | 96.2% |
| Sentence-start capitalization | regression bar | 82.1% |
| Capitalization precision | must not worsen | 89.8% |
| Doubled phrases visible live (7 / 12 sessions) | regression bar | 2 / 2 |
| Punctuation-identical duplicated spans (7 / 12 sessions) | regression bar | 6 / 6 |
| Words shown fused with a fragment of themselves | regression bar | 0 |
| Words shown never spoken (7 / 12 sessions) | regression bar | 608 / 677 |
| Spoken words never shown (7 / 12 sessions) | regression bar | 160 / 173 |
| Already-shown words rewritten (flicker), per 100 shown (7 / 12) | regression bar, same refresh cadence | 5.5 / 5.6 |
| Punctuation changed on unchanged words, per 100 shown (7 / 12) | regression bar, same refresh cadence | 4.1 / 4.2 |
| Short repeats reaching the saved transcript (7 / 12) | regression bar | 18 / 23 |
| Other channel's words on this channel's row | tracked | 2 |
| Bare word fragments on screen | regression bar | 6 |
| Live spoken quantities rendered as a different quantity (7 / 12) | regression bar | 1 / 1 |
| Live spoken quantities dropped (7 / 12) | regression bar | 7 / 13 |
| Live numbers shown that nobody said (7 / 12) | regression bar | 1 / 8 |
| Saved-transcript quantities rendered as a different quantity | must not rise, per call | 28 |
| Saved-transcript quantities dropped | must not rise, per call | 39 |
| Saved-transcript numbers nobody said | must not rise, per call | 58 |
| Saved-transcript window-stitch number splices | must not rise | 0 |
| Figures where the scale word disagrees | must not rise, tolerance 0 | 1 |
| Wrong words the recovery layer adds, per hour (end-of-turn + voiced-hole) | regression bar | 28.7 |
| Added words removed again before saving, per hour | tracked | 7.17 |
| Hallucinated runs per hour (end-of-turn + voiced-hole) | regression bar | 4.73 |
| Words in them, per hour | regression bar | 17.63 |
| Of 3 words or more, per hour | regression bar | 1.75 |
| Invented phrases over silence, per hour | regression bar | 2.35 |
| Words in them, per hour | regression bar | 14.7 |
| Of them in the last 15 seconds of a file | must not rise | 2 |
| Duplicate spans per hour | tracked | 3.08 |
| Decodes added to the product path | declared before it ships | none |
| Determinism | must hold | byte-identical |

The live-view bars are enforced per session with a measured tolerance for replay timing jitter (the same recording replayed twice moves the word counts by a few dozen), plus a tighter cap on the total across sessions — uncorrelated jitter and a systematic regression separate cleanly there.

Three rules govern how these may be read, and each exists because ignoring it produced a wrong published number here at least once:

1. **A number is only valid for the configuration that ships, on the corpus it claims.** Two numbers on an earlier version of this page were not: one set was five weeks stale, the other came from a policy reachable only by disabling the shipping one. Both read exactly like current numbers. A third case was caught before it reached this page — a punctuation figure computed over 2 of the 11 calls — which is why the gate now checks how many files produced a number before comparing it to anything.
2. **Deletion-only measures never appear alone.** A mechanism that recovers words by inventing them improves every deletion count here, so insertions are published beside deletions or neither is published.
3. **An unchanged result must be proven to have run.** A cached decode once reported an entire change as having no effect with every gate green. Both arms above are fully cold decodes, and an arm that reports no cache misses is discarded rather than believed.

Every number on this page is produced by a committed script that a later release can re-run.

## Reproducing

The scorers are the same ones that gate changes internally, unmodified — there is no public-only scoring path.

```bash
# every pipeline axis in one command, each compared against its committed pin.
scripts/live_transcription_benchmark.sh <out-root> --baseline <previous arm> --determinism

# live view against the script (12 two-channel sessions replayed at 1x, --repeat 2 checks jitter)
scripts/live_invariants_gate.sh <out-root> --repeat 2

# numbers in the saved transcript, by value, 11 Earnings-21 calls
python3 scripts/score_number_fidelity.py --corpus <A>/per-file --json-out chg.json
python3 scripts/score_number_fidelity.py --corpus-compare benchmark/results/number-fidelity/final_transcript_baseline_2026-11-26.json chg.json

# invented phrases over silence (16 AMI meetings, ~10 min)
scripts/timestamp_merge_ami16_arm.sh <arm>
python3 scripts/invented_phrase_runs.py --arm <arm> --gate benchmark/results/live-transcription-public/pins.json

# check every published pin on this page and on the website
python3 scripts/public_asr_check.py
```

Pin the output directory of each arm explicitly. The scorers default to the newest directory on disk, which silently picks up whatever else has been run since.
