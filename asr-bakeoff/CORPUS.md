# The bake-off corpus: 27 public files, reproducible by hash

Every number on the ASR bake-off page is measured on the same 27 recordings:
16 AMI meetings (8.51 h) and 11 Earnings-21 earnings calls (10.32 h), 18.8 h in
all. The file list is not ours to choose after the fact — it is pinned in
`benchmark/results/live-transcription-public/pins.json` under `corpus.ami_16`
and `corpus.earnings21_11`.

**We redistribute no audio.** Both corpora are published by their owners, and
this report points at those publishers. What we ship instead is
[`corpus_manifest.json`](corpus_manifest.json): a SHA-256 for every audio file
and every reference file, so you can rebuild the corpus yourself and prove your
copy is byte-identical to the one the numbers were measured on.

```bash
# Rebuild it (about 2.2 GB of audio, from AMI + Hugging Face + GitHub)
python3 scripts/bakeoff/fetch_corpus.py --dest ./data

# Or check a tree you already have
python3 scripts/bakeoff/fetch_corpus.py --verify-only ./data
```

Standard library only — no build, no virtualenv, no API key. The fetch is
resumable: a file whose hash already matches is skipped without a request.
`--verify-only` prints match / mismatch / missing per file and exits non-zero if
anything is wrong. `--corpus ami|earnings21|all` narrows it.

## Which AMI audio this is

**The `Mix-Headset` stream** — the four close-talking headset channels summed
into one 16 kHz mono track. It is *near-field*, not a distant tabletop array
microphone.

That is worth stating plainly, because the AMI site offers several streams for
the same meeting at identical length and identical file size, and
`benchmark/data/ami/audio/EN2002a.wav` gives no hint of which one it holds.
Duration and channel count cannot separate them: `Mix-Headset`, `Array1-01` and
`Array2-01` for EN2002a are each 1 ch / 16 kHz / 16-bit / 2142.71 s /
68,566,744 bytes.

**How it was confirmed.** An HTTP Range read of 8,192 bytes at offset 5,000,000
from each of the three published streams, hashed and compared against the same
slice of the local file:

| stream on the AMI mirror | SHA-256 of bytes 5000000–5008191 | local file with that slice |
|---|---|---|
| `EN2002a.Mix-Headset.wav` | `015e1676cf191779…` | `ami/audio/EN2002a.wav` ✔ |
| `EN2002a.Array1-01.wav` | `ee6385ee438b0e8e…` | `ami/audio/EN2002a.Array1.wav` |
| `EN2002a.Array2-01.wav` | `c78f9c396d4e8b35…` | `ami/audio/EN2002a.Array2.wav` |

The bake-off's pipeline run names its files by the bare meeting id
(`EN2002a`, not `EN2002a.Array1`), which is the `Mix-Headset` copy. The full
audio file was then downloaded from
`…/amicorpus/IS1009a/audio/IS1009a.Mix-Headset.wav` and hashed whole: identical
to the local `ami/audio/IS1009a.wav`.

Note for anyone comparing against a published AMI figure: near-field headset
mix is the *easier* channel than a distant array, and this corpus is a 16-meeting
subset of the 57-file canonical set the diarization page uses. The two pages are
not measured on the same basis and their file counts should not be compared.

## Reference files, and who may redistribute them

| Reference | What reads it | Source | License | May we redistribute? |
|---|---|---|---|---|
| `ami/annotations/words/<meeting>.<A–D>.words.xml` (4 per meeting, 64 total) | `scripts/score_corpus_wer.py` — the AMI WER reference | inside `ami_public_manual_1.6.2.zip` on the AMI site | **CC BY 4.0** | Yes, with attribution |
| `ami/rttm/<meeting>.rttm`, `ami/uem/<meeting>.uem` | diarization scorers | `BUTSpeechFIT/AMI-diarization-setup` (derived from the AMI manual transcription) | **CC BY 4.0** | Yes, with attribution |
| `earnings21/nlp_references/<id>.nlp` | `score_corpus_wer.py`, `score_number_fidelity.py`, `punctuation_accuracy.py` — the Earnings-21 WER, number and punctuation reference | `revdotcom/speech-datasets` | **CC BY-SA 4.0** | Yes, with attribution — but ShareAlike |
| `earnings21/rttm/<id>.rttm` | diarization scorers | `revdotcom/speech-datasets` | **CC BY-SA 4.0** | Yes, with attribution — but ShareAlike |

**What this report actually ships: none of them.** The AMI annotations are
permissively licensed and could be shipped, and the Earnings-21 references are
redistributable too — but ShareAlike would attach a copyleft obligation to the
copy we published, and a reader who has to fetch 2.2 GB of audio from the
publishers anyway gains nothing from us mirroring 11 MB of text. So
`fetch_corpus.py` fetches every reference file, hash-verified, alongside the
audio. One command, one source of truth, no license question to answer.

Audio is a separate matter and not a choice: AMI's CC BY 4.0 would permit
redistribution, and Earnings-21's `LICENSE.md` covers "the transcripts and
associated text files" without granting anything for the media. We redistribute
neither, and the manifest is how you check that what you fetched is what we
measured.

## Where the files land

The layout is the one the scorers already expect, so a fetched tree can be
pointed at directly:

```
<dest>/ami/audio/<meeting>.wav                          Mix-Headset, 16 kHz mono
<dest>/ami/annotations/words/<meeting>.<X>.words.xml     manual word annotations
<dest>/ami/rttm/<meeting>.rttm
<dest>/ami/uem/<meeting>.uem
<dest>/earnings21/audio/<id>.wav
<dest>/earnings21/nlp_references/<id>.nlp
<dest>/earnings21/rttm/<id>.rttm
```

AMI's manual word annotations have no per-file URL — they ship inside one
21.8 MB zip, pinned in the manifest by its own SHA-256. The script downloads it
only when a word file is actually missing or wrong, extracts the 64 members this
corpus needs, and leaves the archive in place; it is an intermediate and can be
deleted afterwards.

RTTM and UEM come from split directories (`test/` for EN2002a, EN2002b, ES2004c,
IS1009a, IS1009b; `train/` for the other eleven), and a wrong split returns 404
rather than the wrong file — so the split each meeting is fetched from is itself
checkable, and every entry was confirmed by a live fetch whose bytes hash-matched.

## The 27 files

**AMI** (8.51 h, 14.0–50.9 min per meeting): EN2002a, EN2002b, EN2006b,
ES2002a, ES2004c, ES2008c, ES2013b, ES2016a, IS1000a, IS1003b, IS1006c,
IS1009a, IS1009b, TS3005a, TS3009c, TS3012b.

**Earnings-21** (10.32 h, 21.8–95.7 min per call): 4320211, 4341191, 4346818,
4359971, 4365024, 4366522, 4366893, 4367535, 4383161, 4384964, 4387332.

## How the manifest is kept honest

It is generated by hashing a real, already-measured tree, never typed:

```bash
python3 scripts/bakeoff/fetch_corpus.py --emit-manifest <benchmark/data dir>
```

A hand-kept hash list drifts silently — the file it names stays downloadable
while the number stops describing it, and nothing fails. Regenerating from the
tree is the only version of this that can go stale loudly.

## Citation

- AMI Meeting Corpus — Carletta, J. et al. (2005). *The AMI Meeting Corpus: A
  Pre-announcement.* Licensed [CC BY 4.0](https://groups.inf.ed.ac.uk/ami/corpus/license.shtml).
- Earnings-21 — Del Rio, M. et al. (2021). *Earnings-21: A Practical Benchmark
  for ASR in the Wild.* Interspeech 2021.
  [revdotcom/speech-datasets](https://github.com/revdotcom/speech-datasets),
  transcripts CC BY-SA 4.0.
- AMI diarization RTTM/UEM —
  [BUTSpeechFIT/AMI-diarization-setup](https://github.com/BUTSpeechFIT/AMI-diarization-setup).
