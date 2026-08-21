# MimicScribe Speaker Identity Benchmark Results

How reliably does the app recognize a *returning* speaker — someone with a saved
voice profile — in a new meeting? This is a different question from diarization
(who spoke when, within one meeting), and it is scored separately.

Run date: 2026-08-01 (voiceprint-evidence and cluster-consistency rows added 2026-08-20)

## What is measured

Standard speaker-recognition benchmarks score *verification*: one voice sample,
one claimed identity, yes or no. That shape misses the failure that actually
matters in a meeting app. MimicScribe answers an *identification* question: a
speaker appears in a meeting, and the app must decide which of the user's saved
profiles — if any — this voice belongs to, against the whole profile library at
once.

Each trial has one of three outcomes:

- **Correct**: the speaker is matched to their own profile.
- **Wrong**: the speaker is matched to someone else's profile. This is the
  expensive error — it writes a false name into a durable transcript and folds
  the wrong voice into a saved profile, making the *next* error more likely.
- **Refused**: the app declines to pick. This costs one manual rename.

The two error families are never averaged into a single score, because they are
not the same price. The design goal is that when the app is unsure, it refuses
rather than guesses.

## Headline numbers

AMI meeting corpus (CC BY 4.0), recurring speakers across sessions, profiles
built by the exact production code path (never a more permissive shortcut), 30
seconds of enrollment speech, full-meeting recognition:

| Metric | Value |
|---|---|
| Correct identification | **92.0%** (779 genuine trials) |
| Wrong identification | **0** (95% upper bound 0.5%) |
| Below-bar suggestion tier precision | 90% (95% CI 79–96%) |
| Speech required to create a profile | **20 seconds** across a few turns (a hard floor: below it, the app refuses to enroll) |
| First suggestion for an already-enrolled speaker | within the first **~5 seconds** of heard speech (reaches 36.5% of returning speakers at 91.9% precision) |

The last two rows are the timing context the accuracy rows need: they say how
long it takes to get *into* the system. Creating a profile requires 20 seconds
of qualifying speech spread across a few separate turns (a single continuous
monologue needs more); below that the app refuses to enroll rather than build
a profile from too little evidence. The floor was originally 30 seconds and
was lowered only after a dedicated recalibration: 2,808 profiles that the old
floor refused were admitted on this corpus with zero wrong identifications and
zero impostor false-accepts, and the floors that did not pass that bar were
left unchanged. Every budget that clears the floor measured zero wrong
identifications. Recognizing a returning speaker starts
much sooner than that: within the first ~5 seconds they are heard in a new
meeting, the one-click suggestion tier already reaches about a third of
returning speakers at ~92% precision, while automatic naming deliberately
waits for more evidence before committing a name on its own.

The refusals that make up the remaining ~8% are dominated by short speech:
recognition-time speech, not enrollment speech, is the binding constraint.
Coverage roughly doubles between the first ~20 seconds a speaker is heard and
the full meeting. Forced early snapshots are also where the rare wrong
identification lives — under 0.6% when a decision is forced at 10–20 seconds
of heard speech — which is why the app accumulates evidence rather than
committing on first hearing; at full-meeting evidence, wrong identifications
measured zero. Below the automatic-match bar, the app shows a one-click "Is
this X?" suggestion instead of deciding on its own; those suggestions are
right 90% of the time.

## A second corpus

The numbers above are measured on AMI. To check that the operating point is
not tuned to one corpus's acoustics, the same production decision rules run
on an independent second corpus (ICSI meeting corpus), with the same
reference-label audit applied first — it excluded eleven ICSI sessions with
suspect labels, the same defect class the audit caught and excluded in AMI.
Under a one-probe-per-returning-speaker protocol, AMI measures 99.4% correct
(170 trials) and ICSI measures 89.5% (38 trials, a thin sample with wide
bounds) — zero wrong identifications on both, with the entire gap being
additional refusals, never wrong names. ICSI also enables a larger same-room
impostor test than AMI supports (410 trials of people probing their actual
room-mates' profiles): one wrong match appeared (0.2%). That is the number
at higher statistical power, and ICSI now runs as a standing validation
corpus alongside AMI.

## Switching devices

A profile enrolled on one microphone and heard on a very different one is the
hardest realistic case for a returning speaker. Measured with AMI's two capture
chains standing in for a device switch (headset for enrollment, distant room
array for recognition): with full-meeting evidence the switch costs little —
95% recognized versus 97% on the matched device — but with only 20 seconds of
heard speech, recognition drops to 25% versus 63%, all of it refusals rather
than wrong names. Once a single meeting on the new device is confirmed into
the profile, 20-second recognition recovers to 41%
and keeps climbing with more evidence, at no change to the false-accept rate.
The app's enrollment flow adds that meeting automatically once the speaker is
confirmed.

## What keeps profiles accurate

A saved profile is only as good as the voice data that builds it, and a
matching rule is only as safe as its worst case. Several measured safeguards
work together:

- **Enrollment is gated.** Speech only enters a profile after clearing quality
  and quantity floors; low-evidence fragments are excluded rather than
  averaged in.
- **A profile can hold more than one voiceprint.** The same person sounds
  different through AirPods than through a laptop microphone, and different
  again early in their enrollment history. Profiles hold separate voiceprints
  for genuinely distinct conditions — keyed by the actual input device on the
  microphone side — rather than blurring them into one average.
- **Every voiceprint must clear its own evidence-based confidence bar before
  it can claim a match.** A voiceprint that sits acoustically close to
  someone else's profile has to be *more* confident than one that stands
  alone. This is what makes multiple voiceprints safe: in our measurements it
  removed every same-room false accept that a naive best-match rule produced
  (5 of 1,401 stranger trials → 0), at no cost in correct identifications.
- **A profile deliberately shared by two people keeps one voiceprint per
  person.** Merging two people into one profile is the user's decision and
  is never second-guessed. Averaging the two voices together would cost the
  members a quarter of their full-meeting
  recognitions (99% → 73%), while per-person voiceprints keep members
  recognized exactly as reliably as separate profiles would, with no change
  to anyone else's accuracy or to false accepts. Verified on both corpora,
  and the result holds even when one member speaks a tenth as much as the
  other.
- **Every voiceprint is checked against the audio it was built from.**
  Measured on 141 speaker segments from six committed recordings, stored
  voiceprints cover 99.0% of the speech they stand for (up from 91.0%), and
  none claims audio it never heard (0 of 141).
- **Confirming a name cannot fold a second voice into a profile.** A
  confirmed speaker's turns have to agree with one another first. Calibrated
  on 792 ground-truth identities across 200 AMI sessions: 4.8% of genuine
  speakers refused, 16.2% of even two-person blends let through.
- **A profile built from too little evidence gets rebuilt, not defended.**
  When you confirm a speaker and the saved profile still does not recognize
  them, a profile with too thin a history is rebuilt from the recording you
  confirmed. One Undo reverses it. A profile with a real history is left
  alone.
- **Close calls are refused, and visibly.** When two profiles score within an
  ambiguity margin of each other, the app refuses the match and surfaces the
  conflict instead of silently picking one.
- **The alternatives were measured, not assumed.** Every mechanism above
  shipped only after beating its alternatives on this benchmark; intuitive
  alternatives that measured no better — or actively worse — than the simpler
  approach are not in the app.

## Honest caveats

- AMI headset and room-microphone conditions are acoustically closer to each
  other than a user's real device switches (AirPods vs. built-in mic), so the
  multi-voiceprint gains measured here are conservative for the device case
  the feature targets.
- During the label audit we found one AMI session pair whose reference
  speaker labels are rotated relative to the audio; it is excluded from the
  substrate, and the audit method is applied to every corpus before its
  numbers are published.
- The zero in the wrong-identification row is a measured zero with a finite
  denominator, not a guarantee; its 95% upper bound is stated alongside it.
- Enrollment and probe speech are drawn from talkative meeting participants
  (AMI's minimum is ~26 s per session), which is mildly optimistic for a
  genuinely quiet participant.
- The voiceprint-coverage numbers come from six recordings on one machine.
  They say the stored voiceprints are honest about their audio; they do not
  claim a recognition gain.
- The device-switch numbers use AMI's headset-vs-array chains as a stand-in
  for a real device switch; the shape of the result is the claim, the exact
  percentages are corpus-specific.

## Methodology

Voice embeddings come from the same on-device pipeline the app ships
(FluidAudio speaker embeddings); profile construction, matching, and refusal
logic run the production decision rules. Genuine trials hold out each
recurring speaker's newest session for recognition and enroll from the rest,
so no recognition audio ever contributes to the profile it is scored against.
False-accept trials probe every profile with speakers who co-occurred in the
same rooms — the hardest impostor population — plus cross-corpus strangers.

The results above are measured on reference-segmented speech. Re-scoring
the same decision rules on the app's own diarizer output over real
recordings gave the same outcome: the main voice cluster for each speaker
was recognized as the benchmark predicts, and every failure was a refusal,
not a wrong name. The benchmark also runs as a regression gate: a change to
profile logic must reproduce these results exactly before it ships.

## Reproducibility

Produced at `parakeet-transcriber` commit `9df400c9` with production default
parameters on the cached AMI embedding substrate. The enrollment-floor and
suggestion-timing rows were produced at commit `8efacf56` on the same
substrate, also with production default parameters; the enrollment-floor
recalibration (30 → 20 seconds) was produced at commit `afc0a31f`, and the
second-corpus (ICSI) validation at commit `126c0a05`. The device-switch and
shared-profile measurements were produced at commits `6a62b013`, `5fed6281`,
and `468c3f59`, and the shared-profile follow-ups and diarizer-output check
at commits `323421b3` and `d1067e57` — production default parameters
throughout. The voiceprint-evidence rows were produced at commit `dc0bd03d`
(against `c57c3bec` for the before arm) with
`scripts/evidence_retention.py --batch` over the committed golden pairs in
`Tests/Fixtures/golden_pairs`, each replayed with `--replay-raw-pair`; the
cluster-consistency calibration with `scripts/coherence_floor_rttm.py` at
default parameters on the cached AMI embedding substrate.
