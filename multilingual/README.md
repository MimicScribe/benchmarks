# Multilingual transcription

Word error rate for all 25 languages MimicScribe transcribes, on FLEURS read speech, measured through the app. Compares the speech model in the current release with the next one.

- Results: [RESULTS.md](RESULTS.md)
- Transcripts: [`results/`](results/)
- Reproduce: `python3 scripts/fetch_fleurs.py --minutes 10 --min-utterances 60 --seed 1337`, then `python3 scripts/score.py --no-digit-refs` (needs `jiwer`, `numpy`, `scipy`, `soundfile`, `pyarrow`, `huggingface_hub`).
