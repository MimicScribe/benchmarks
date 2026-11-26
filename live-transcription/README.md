# Live Transcription & Speech Recognition Benchmark

Evaluates the on-device speech recognition model and live streaming transcription pipeline in [MimicScribe](https://mimicscribe.app).

MimicScribe transcribes speech locally on Apple Silicon from overlapping listening windows. Where two windows overlap, the engine has two readings of the same few seconds of audio and must commit one transcript without dropping spoken words, splitting numbers, or rewriting text the reader already trusted.

No single number describes a speech recognizer and streaming pipeline, so this benchmark separates **speech model quality** from **live streaming behavior** across five pillars:

1. **Core word accuracy and speed (Model).** Unseen multi-speaker meetings (46 held-out AMI meetings, ~282k words), paired 27-file content WER (AMI-16 + Earnings-21), and Apple Silicon realtime factor.
2. **Multilingual accuracy and non-English safety (Model).** All 25 supported languages on FLEURS read speech (6,039 + 800 clips), non-English spoken numbers, and English-leakage checks — detailed in [multilingual/RESULTS.md](../multilingual/RESULTS.md).
3. **Spoken-form numbers, currencies, punctuation, and stability (Model).** Unseen held-out earnings calls (10 calls, 2,425 figures), 22 real earnings calls, Rev.com sentence punctuation/casing, fast speech (`1.4×`), rapid-repeat rate, and steady-noise timing stability.
4. **Live streaming continuity, stability, and latency (Pipeline).** Clean vs. overlapped deletion rates, loss clumping, recovery precision, silence hallucinations, live view vs. script, committed-text stability paired with pause-to-commit latency, and byte-identical determinism.
5. **Competitive and historical model bake-off.** Cross-model comparison on the same hash-verified 27-file corpus — archived in [asr-bakeoff/RESULTS.md](../asr-bakeoff/RESULTS.md).

Live stability and latency trade against each other and are always published together: committing sooner makes text settle faster and makes it slightly more likely to be revised. Deletion-only counts never appear without insertion counts beside them.

Results: [results/RESULTS.md](results/RESULTS.md)
