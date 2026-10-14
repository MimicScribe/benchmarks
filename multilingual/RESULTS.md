# Multilingual transcription — FLEURS, 25 languages

MimicScribe transcribes 25 languages on-device. This page measures each of them on read speech, through the app itself, and compares MimicScribe's spoken-form fine-tune with stock Parakeet Ultra, the model it replaced.

**Scope, stated first:** this is a small test. It is read speech (one sentence per clip), 44–55 sentences per language on the main basis, single speakers, studio-quality recordings. It does not measure meetings, crosstalk, accents, non-native speakers, or switching languages mid-sentence. English meeting accuracy is measured separately in the [ASR bake-off](../asr-bakeoff/RESULTS.md) and [live transcription](../live-transcription/results/RESULTS.md) benchmarks.

## Corpus

[FLEURS](https://huggingface.co/datasets/google/fleurs) (Google, CC BY 4.0), **test split**, 60–65 utterances per language (1,512 in total), drawn with a fixed seed and balanced by speaker gender where the split allows. MimicScribe's fine-tune never saw the FLEURS test split.

## Method

- Each clip is transcribed by the MimicScribe app (single-utterance path, the one dictation and short imports use). The text scored is what the app shows, including how it writes numbers in each language.
- Both models run in the same app build on the same Mac; only the speech model changes.
  - **Stock Ultra:** Parakeet Ultra ([FluidInference/parakeet-ultra-coreml](https://huggingface.co/FluidInference/parakeet-ultra-coreml)), the model in MimicScribe up to 1.0.0-rc.40.
  - **Fine-tune:** MimicScribe's fine-tune of Parakeet Ultra ([MimicScribe/parakeet-ultra-spoken-coreml](https://huggingface.co/MimicScribe/parakeet-ultra-spoken-coreml)), trained to write English numbers the way they were spoken. Only the decoder and joint network were trained; the encoder is unchanged.
- **Word error rate (WER):** lowercase, punctuation removed on both sides.
- **Main basis, number-neutral:** sentences whose reference contains no digits (1,220 of 1,512). FLEURS references write numbers as digits ("70 km"), so a correct number written as words would count as errors. The right-hand column scores all sentences anyway.
- **Change:** fine-tune minus stock Ultra, in percentage points, with a 95% paired bootstrap interval over sentences (2,000 resamples). An interval that includes 0 means no measurable change.

## Results (2026-10-14)

| Language | Sentences | Stock Ultra | Fine-tune | Change (95% CI) | All sentences, stock → fine-tune |
|---|---:|---:|---:|---|---|
| Italian | 48 | 2.5% | 2.7% | +0.18 pp (-0.18, +0.56) | 3.5% → 3.6% |
| Portuguese (Brazil) | 51 | 3.1% | 3.1% | +0.00 pp (+0.00, +0.00) | 5.5% → 5.5% |
| French | 52 | 4.0% | 3.9% | -0.14 pp (-0.54, +0.21) | 5.9% → 5.8% |
| English | 49 | 4.1% | 4.0% | -0.19 pp (-0.69, +0.19) | 7.1% → 6.8% |
| Spanish (Latin America) | 50 | 4.0% | 4.3% | +0.25 pp (+0.00, +0.82) | 6.0% → 6.2% |
| German | 47 | 4.1% | 4.4% | +0.30 pp (-0.32, +0.94) | 5.8% → 6.4% |
| Polish | 55 | 5.1% | 5.5% | +0.41 pp (-0.20, +1.07) | 5.4% → 6.0% |
| Russian | 51 | 6.3% | 6.3% | +0.00 pp (+0.00, +0.00) | 8.7% → 8.9% |
| Slovak | 52 | 6.9% | 6.8% | -0.10 pp (-0.76, +0.49) | 9.4% → 9.3% |
| Ukrainian | 51 | 6.8% | 6.9% | +0.10 pp (-0.36, +0.68) | 9.7% → 9.6% |
| Dutch | 48 | 7.8% | 7.5% | -0.26 pp (-0.66, +0.09) | 9.2% → 8.9% |
| Finnish | 46 | 8.5% | 8.5% | +0.00 pp (-0.97, +0.89) | 12.7% → 12.8% |
| Romanian | 45 | 9.3% | 9.2% | -0.09 pp (-0.57, +0.39) | 11.8% → 11.7% |
| Hungarian | 45 | 10.1% | 10.0% | -0.12 pp (-0.53, +0.25) | 12.0% → 12.0% |
| Bulgarian | 51 | 9.7% | 10.2% | +0.50 pp (-0.10, +1.14) | 14.9% → 15.5% |
| Swedish | 49 | 11.9% | 12.0% | +0.11 pp (-0.44, +0.69) | 13.9% → 13.8% |
| Croatian | 45 | 12.2% | 12.2% | +0.00 pp (-0.39, +0.36) | 15.5% → 15.7% |
| Czech | 44 | 12.8% | 12.8% | +0.00 pp (-0.35, +0.35) | 14.3% → 14.2% |
| Estonian | 50 | 14.3% | 13.8% | -0.50 pp (-1.20, +0.13) | 17.2% → 17.1% |
| Danish | 48 | 15.5% | 15.4% | -0.10 pp (-0.86, +0.69) | 17.5% → 17.6% |
| Maltese | 46 | 16.9% | 15.8% | -1.13 pp (-2.13, -0.20) | 19.1% → 18.5% |
| Latvian | 52 | 17.5% | 17.2% | -0.24 pp (-0.96, +0.36) | 18.2% → 18.1% |
| Lithuanian | 48 | 19.7% | 20.1% | +0.38 pp (-0.53, +1.37) | 20.5% → 20.8% |
| Slovenian | 48 | 20.9% | 21.1% | +0.20 pp (-0.81, +1.17) | 24.2% → 24.2% |
| Greek | 49 | 22.1% | 22.9% | +0.78 pp (-0.44, +2.11) | 23.4% → 24.1% |
| **Mean of 25** | 1220 | **10.25%** | **10.27%** | +0.01 pp | 12.45% → 12.52% |

**Summary:** the fine-tune is level with stock Ultra on non-English speech. Mean number-neutral WER is 10.25% vs 10.27% across the 25 languages. No language is measurably worse. Maltese is measurably better (−1.1 pp). Greek, Bulgarian and Polish lean slightly worse, inside their intervals.

**Wrong values found:** reading the outputs turned up one number written with the wrong value. A Bulgarian sentence with "10 000" came out from the fine-tune as "десет нула нула нула" ("ten zero zero zero"), where stock Ultra wrote "десет хиляди" ("ten thousand"). That is 1 of 1,512 sentences. It is logged for a fix.

**Accuracy differs by language:** from 2.5% (Italian) to 22.9% (Greek). Stock Ultra shows the same spread, so it comes from the base model, not from MimicScribe's fine-tune.

## Reproduce

- [`scripts/fetch_fleurs.py`](scripts/fetch_fleurs.py) downloads the same sentences (`--minutes 10 --min-utterances 60 --seed 1337`).
- [`results/transcripts_released.jsonl`](results/transcripts_released.jsonl) and [`results/transcripts_next.jsonl`](results/transcripts_next.jsonl) hold every app transcript.
- [`scripts/score.py`](scripts/score.py) scores them against the FLEURS references and prints this table (`--no-digit-refs` for the main basis).
