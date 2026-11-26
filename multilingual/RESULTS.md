# Multilingual transcription — FLEURS, 25 languages

MimicScribe transcribes 25 languages on-device with one shared speech model. This page measures all 25 languages on read speech through the app itself, comparing MimicScribe's spoken-form fine-tune with stock Parakeet Ultra on the exact same app build.

**Scope, stated first:** this tests read speech (one sentence per clip, single speakers, studio-quality recordings) — 240 to 260 clips per language (6,039 total), plus an extended 800-clip set in German, English, Spanish, and French. It does not measure multi-speaker meetings, room reverberation, crosstalk, or switching languages mid-sentence. English meetings and earnings calls are measured separately in the [live transcription](../live-transcription/results/RESULTS.md) and [ASR bake-off](../asr-bakeoff/RESULTS.md) benchmarks.

## Corpus

[FLEURS](https://huggingface.co/datasets/google/fleurs) (Google, CC BY 4.0), **test split**:
- **Primary 25-language set:** 6,039 utterances (240–260 per language; 4,912 number-neutral utterances, plus 1,786 spoken figures across the 24 non-English languages).
- **Extended 4-language set:** 800 additional test-split utterances (200 each in German, English, Spanish, and French; 644 number-neutral utterances, plus 198 non-English figures).

MimicScribe's fine-tune never saw the FLEURS test split.

## Method

- Each clip is transcribed on-device by the MimicScribe app on Apple Silicon. Both models run inside the same release build on the same Mac; only the model weights change.
  - **Stock Ultra:** unmodified Parakeet Ultra ([FluidInference/parakeet-ultra-coreml](https://huggingface.co/FluidInference/parakeet-ultra-coreml), `95eaa59a`).
  - **Spoken-form fine-tune (FP16 top-4):** MimicScribe's fine-tune ([MimicScribe/parakeet-ultra-spoken-coreml](https://huggingface.co/MimicScribe/parakeet-ultra-spoken-coreml), `9e462b9f`), trained to write English numbers, currencies, and dates in spoken form while keeping all other languages at stock behavior, with the four fine-tuned top Conformer encoder layers exported in native FP16.
- **Number-neutral WER (main basis):** lowercase, punctuation stripped on both sides, restricted to utterances whose reference contains no digits (4,912 of 6,039). FLEURS references write numbers as digits ("70 km"), so an English spoken-form output would otherwise score as an error.
- **Non-English spoken numbers (right column):** every spoken number in the 24 non-English languages is checked by numeric value (whether rendered as digits or words), catching corrupted values or dropped numbers that number-neutral WER hides.
- **Change:** fine-tune minus stock Ultra, in percentage points, with a 95% paired cluster-bootstrap confidence interval. An interval spanning 0 means no measurable change.

## Results — 25 languages (2026-11-25)

| Language | Number-neutral clips | Stock Ultra | Fine-tune (FP16 top-4) | Change (95% CI) | Numbers right (stock → fine-tune) |
|---|---:|---:|---:|---|---:|
| Italian | 196 | 2.32% | 2.34% | +0.02 pp (−0.04, +0.10) | 79/81 → 79/81 |
| Spanish (Latin America) | 197 | 2.80% | 2.88% | +0.08 pp (+0.02, +0.16) | 68/74 → 68/74 |
| Portuguese (Brazil) | 201 | 3.18% | 3.20% | +0.02 pp (−0.12, +0.18) | 61/61 → 61/61 |
| German | 195 | 3.76% | 3.76% | +0.00 pp (−0.13, +0.11) | 69/79 → 67/79 |
| French | 196 | 4.33% | 4.27% | −0.06 pp (−0.22, +0.09) | 69/74 → 69/74 |
| English | 193 | 4.42% | 4.12% | −0.30 pp (−0.58, −0.07) | — *(scored in English calls)* |
| Russian | 198 | 5.53% | 5.42% | −0.11 pp (−0.27, +0.05) | 67/68 → 67/68 |
| Slovak | 205 | 5.70% | 5.81% | +0.10 pp (−0.08, +0.32) | 48/51 → 48/51 |
| Ukrainian | 198 | 5.98% | 5.98% | +0.00 pp (−0.18, +0.18) | 70/75 → 70/75 |
| Polish | 214 | 6.36% | 6.49% | +0.13 pp (−0.17, +0.42) | 66/74 → 67/74 |
| Dutch | 203 | 6.73% | 6.63% | −0.10 pp (−0.28, +0.07) | 70/75 → 70/75 |
| Romanian | 196 | 9.78% | 9.62% | −0.16 pp (−0.40, +0.09) | 69/72 → 69/72 |
| Bulgarian | 194 | 10.05% | 10.10% | +0.05 pp (−0.24, +0.33) | 65/77 → 65/77 |
| Finnish | 193 | 10.80% | 10.63% | −0.17 pp (−0.44, +0.07) | 67/79 → 68/79 |
| Czech | 195 | 11.61% | 11.58% | −0.03 pp (−0.26, +0.20) | 73/77 → 74/77 |
| Swedish | 196 | 11.90% | 12.05% | +0.15 pp (−0.10, +0.44) | 61/71 → 63/71 |
| Hungarian | 193 | 12.29% | 12.29% | +0.00 pp (−0.30, +0.33) | 68/76 → 69/76 |
| Croatian | 192 | 12.91% | 12.82% | −0.09 pp (−0.36, +0.15) | 77/81 → 77/81 |
| Estonian | 196 | 14.40% | 14.46% | +0.06 pp (−0.34, +0.46) | 70/77 → 71/77 |
| Latvian | 195 | 15.63% | 15.51% | −0.12 pp (−0.53, +0.29) | 59/70 → 58/70 |
| Danish | 197 | 15.70% | 15.58% | −0.12 pp (−0.48, +0.24) | 58/72 → 58/72 |
| Lithuanian | 190 | 16.31% | 16.72% | +0.41 pp (−0.03, +0.83) | 81/89 → 80/89 |
| Maltese | 194 | 17.76% | 18.02% | +0.27 pp (−0.11, +0.65) | 48/73 → 44/73 |
| Greek | 189 | 20.08% | 19.45% | −0.64 pp (−1.09, −0.17) | 70/78 → 70/78 |
| Slovenian | 196 | 21.26% | 21.20% | −0.05 pp (−0.44, +0.29) | 71/82 → 72/82 |
| **Mean of 25 languages** | **4,912** | **10.06%** | **10.04%** | **−0.03 pp (−0.08, +0.03)** | **1,604/1,786 (89.81%) → 1,604/1,786 (89.81%)** |

### Extended 4-language check (800 clips)

| Language | Number-neutral clips | Stock Ultra | Fine-tune (FP16 top-4) | Change (95% CI) |
|---|---:|---:|---:|---|
| Spanish (Latin America) | 162 | 2.50% | 2.57% | +0.07 pp (+0.00, +0.17) |
| German | 165 | 3.57% | 3.51% | −0.06 pp (−0.18, +0.00) |
| English | 159 | 4.42% | 4.14% | −0.28 pp (−0.50, −0.10) |
| French | 158 | 4.94% | 4.94% | +0.00 pp (−0.18, +0.19) |
| **Pooled (4 languages)** | **644** | — | — | **−0.07 pp (−0.15, +0.01)** |

## Summary and caveats

- **Overall parity:** Mean number-neutral WER across all 25 languages is **10.04% vs. 10.06%** on stock Ultra (−0.03 pp, 95% CI −0.08 to +0.03). Greek (−0.64 pp) and English (−0.30 pp) improve measurably; Spanish (+0.08 pp, CI +0.02 to +0.16), Lithuanian (+0.41 pp, CI −0.03 to +0.83), and Maltese (+0.27 pp, CI −0.11 to +0.65) lean slightly worse.
- **Non-English spoken numbers:** Across all 24 non-English languages in the primary set, numeric accuracy ties stock Ultra exactly at **1,604 / 1,786 (89.81%, +0.00 pp, CI −0.53 to +0.54)**. Maltese drops 4 numbers (48/73 → 44/73) and German drops 2 (69/79 → 67/79), balanced by small gains in Swedish, Polish, Finnish, Czech, Hungarian, Estonian, and Slovenian. On the smaller extended set, non-English numbers move from 184/198 (92.9%) to 182/198 (91.9%, −2 figures).
- **Zero English leakage:** Across all 6,399 non-English utterances (primary + extended), **0** non-English clips leaked English spoken-form number words.
- **Accuracy differs widely by language:** From 2.3% (Italian) to 21.2% (Slovenian). Stock Ultra has the same spread, so it comes from the base Parakeet Ultra model rather than MimicScribe's fine-tune.
- **Prior 2026-10-14 Bulgarian number bug retired:** The post-decode digit verbalizer responsible for the earlier Bulgarian "10 000" error was removed; Bulgarian numbers now match stock Ultra at 65/77.

## Provenance

- **Date:** 2026-11-25
- **Stock Ultra:** `FluidInference/parakeet-ultra-coreml` (`95eaa59a`)
- **Spoken-form fine-tune:** `MimicScribe/parakeet-ultra-spoken-coreml` (`9e462b9f`, FP16 top-4 encoder layers)
- **Hardware:** Apple Silicon (M1 Max, CoreML Neural Engine)
