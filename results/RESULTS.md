# MimicScribe Diarization Benchmark Results

Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote (on-device diarization) + Gemini 3 Flash (LLM speaker attribution)

Run date: 2026-03-29

Collar: 0.25s (standard)

## Benchmark vs Production

These results represent a **worst-case scenario** for the MimicScribe pipeline. In normal use, the pipeline has several advantages not available in this benchmark:

- **Mic/system audio separation**: MimicScribe captures the user's microphone and system audio (remote participants) as separate streams. This gives the diarization a free speaker separation signal — the primary user is always identified from the mic channel, and remote speakers are a distinct pool. In this benchmark, all speakers come from a single mixed audio file with no channel distinction.
- **Voice profiles**: Users can save voice profiles that provide verified speaker recognition with high confidence. The benchmark has no saved profiles.
- **Meeting context**: Users can provide prep context (e.g., "Meeting with Alice and Bob about Q3") that helps the LLM identify speakers. The benchmark has no context.
- **Segment granularity**: The pipeline outputs sentence-level segments because that's what users read. DER penalizes this heavily — silent gaps within a sentence count as false alarm — but it is a deliberate UX choice, not a diarization failure. This accounts for the majority of the false alarm rate.

## Summary

DER is the sum of three error types. **Confusion** (speaker assignment error) is the most relevant metric for diarization quality — it measures how often speech is attributed to the wrong speaker. **False Alarm** is inflated by the pipeline's sentence-level segments spanning silent gaps (see above). **Missed** is speech that was not detected at all.

| Corpus | Files | DER | Confusion (speaker error) | False Alarm (segment boundaries) | Missed |
|--------|------:|----:|--------------------------:|--------------------------------:|-------:|
| ami | 16 | 37.7% | 9.8% | 10.7% | 17.2% |
| earnings21 | 11 | 17.4% | 3.2% | 13.7% | 0.5% |

## Baseline Comparison

[Pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) is the reference open-source diarization system, run with default parameters.

| Corpus | Pyannote Community-1 | MimicScribe Pipeline |
|--------|--------------------:|--------------------:|
| ami | 13.1% | 37.7% |
| earnings21 | 4.6% | 17.4% |

## Per-File Results

### ami

| File | Pyannote C1 | MimicScribe | Ref Spk | Hyp Spk |
|------|------------:|------------:|--------:|--------:|
| EN2002a | 17.8% | 44.0% | 4 | 5 |
| EN2002b | 17.2% | 51.9% | 4 | 8 |
| EN2002c | 15.4% | 42.5% | 3 | 4 |
| EN2002d | 20.1% | 49.7% | 4 | 5 |
| ES2004a | 14.4% | 40.3% | 4 | 4 |
| ES2004b | 8.7% | 24.8% | 4 | 4 |
| ES2004c | 8.5% | 36.0% | 4 | 5 |
| ES2004d | 14.0% | 49.8% | 4 | 4 |
| IS1009a | 14.6% | 39.4% | 4 | 4 |
| IS1009b | 10.5% | 18.8% | 4 | 5 |
| IS1009c | 6.3% | 17.2% | 4 | 6 |
| IS1009d | 11.1% | 39.1% | 4 | 6 |
| TS3003a | 14.0% | 36.1% | 4 | 3 |
| TS3003b | 8.4% | 24.2% | 4 | 5 |
| TS3003c | 10.3% | 35.4% | 4 | 4 |
| TS3003d | 16.2% | 47.6% | 4 | 4 |

### earnings21

| File | Pyannote C1 | MimicScribe | Ref Spk | Hyp Spk |
|------|------------:|------------:|--------:|--------:|
| 4320211 | 5.0% | 21.7% | 10 | 10 |
| 4341191 | 3.1% | 23.7% | 15 | 9 |
| 4346818 | 2.3% | 16.9% | 15 | 15 |
| 4359971 | 3.1% | 14.6% | 10 | 10 |
| 4365024 | 2.3% | 9.3% | 13 | 12 |
| 4366522 | 2.0% | 12.5% | 5 | 5 |
| 4366893 | 2.2% | 11.2% | 9 | 9 |
| 4367535 | 7.5% | 18.1% | 11 | 10 |
| 4383161 | 1.8% | 10.7% | 11 | 11 |
| 4384964 | 18.1% | 33.7% | 15 | 15 |
| 4387332 | 0.9% | 10.7% | 6 | 6 |
