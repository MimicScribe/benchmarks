# Multilingual transcription

Word error rate and non-English number accuracy for all 25 languages MimicScribe transcribes, measured through the app on FLEURS read speech. Compares MimicScribe's spoken-form FP16 top-4 fine-tune (`9e462b9f`) with stock Parakeet Ultra (`95eaa59a`).

- Results: [RESULTS.md](RESULTS.md)
- Corpus: 6,039 test-split utterances across all 25 languages (4,912 number-neutral utterances; 1,786 non-English numbers across 24 languages) plus an extended 800-clip set in German, English, Spanish, and French.
- Reproduce: `scripts/fetch_fleurs.py` + `scripts/score.py --no-digit-refs` (requires `jiwer`, `numpy`, `scipy`, `soundfile`, `pyarrow`, `huggingface_hub`).
