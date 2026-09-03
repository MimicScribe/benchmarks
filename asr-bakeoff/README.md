# ASR Model Bake-off

Four acoustic models decoded over one 27-file public corpus, through their own runtimes and through ours, and graded two ways: word error rate, and a blind rubric judge reading each transcript against the human reference. The report is [RESULTS.md](RESULTS.md); the corpus, its licences and its per-file hashes are [CORPUS.md](CORPUS.md).

Dated and closed. Measured 2026-09-01 and published as a snapshot of what existed then, not as a leaderboard — nothing here is re-run when a new model ships, and no release is gated on it.

The operator's map — every published number with its internal owner, the arm directory that produced it, and the command that re-derives it — is `benchmark/results/asr-bakeoff/pins.json`.

Layout: `RESULTS.md` (the report), `CORPUS.md` + `corpus_manifest.json` (what to
fetch and the hash of every file), `scripts/` (the corpus fetcher, the two
scorers, the judge and its agreement scorer, and the external-arm runners).
Commands in the report's Reproducing section run from this directory with
`MIMICSCRIBE_CORPUS_DATA=./data` and `MIMICSCRIBE_BIN=/Applications/MimicScribe.app/Contents/MacOS/mimicscribe`.
