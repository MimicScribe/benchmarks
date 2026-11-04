# MimicScribe Speaker Identity Benchmark Results

How reliably does the app recognize a *returning* speaker — someone with a saved
voice profile — in a new meeting? This is a different question from diarization
(who spoke when, within one meeting), and it is scored separately.

Run date: 2026-11-04 for the headline, second-corpus, real-timeline and device-switch rows. They were measured on the development build that becomes the next release. Other rows keep the dates listed under Reproducibility.

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
built by the exact production code path (never a more permissive shortcut),
full-meeting recognition:

| Metric | Value |
|---|---|
| Correct identification, 30 seconds of clear speech per recording | **96.3%** (750 of 779 trials) |
| Correct identification, each recording's full history | **98.5%** (767 of 779 trials) |
| Wrong identification | **0** of 779 (95% upper bound 0.5%) |
| Below-bar suggestion tier precision | 90% (95% CI 79–96%) |
| Speech required to create a profile | **30 seconds** of clear speech in any number of turns, with one stretch of at least 7.5 seconds, from the next release; the current release asks for 20 seconds across a few turns (a hard floor: below it, the app refuses to enroll) |
| First suggestion for an already-enrolled speaker | within the first **~5 seconds** of heard speech (reaches 36.6% of returning speakers at 91.0% precision) |

This page used to report 92.0% for the 30-second row. Most of the change is in
how the test counts speech, not in the app. The test used to count 30 seconds
before removing unreliable speech, which left about 15 to 30 seconds of usable
speech. It now counts 30 seconds of reliable speech, the way the app does.
Undoing that correction alone gives 92.6%. Matching the app's two voiceprints per
established profile adds about 0.3 points. Undoing both gives 92.7%, so the last
0.7 points back to 92.0% come from other changes since August that we did not
trace.

The last two rows are the timing context the accuracy rows need: they say how
long it takes to get *into* the system. From the next release, creating a profile
requires 30 seconds of qualifying speech, in one turn or several, with at least one stretch of 7.5
seconds; below that the app refuses to enroll rather than build a profile from
too little evidence. Earlier versions counted turns as well as seconds, which
refused one clean long turn while admitting several short ones.
The 96.3% is measured with 30 seconds per recording, pooled across a speaker's
other meetings, so it is not the score of a profile saved from one meeting; the
real-timeline section below is. At full-meeting length this test measured zero
wrong identifications; shorter speech and the same-room tests below found some.
Recognizing a returning speaker starts
much sooner than that: within the first ~5 seconds they are heard in a new
meeting, the one-click suggestion tier already reaches about a third of
returning speakers at ~91% precision, while automatic naming deliberately
waits for more evidence before committing a name on its own.

The refusals that make up the remaining ~4% are dominated by short speech:
recognition-time speech, not enrollment speech, is the binding constraint.
Coverage roughly doubles between the first ~20 seconds a speaker is heard and
the full meeting. Forced early snapshots are also where the rare wrong
identification lives — under 1% when a decision is forced at 10–20 seconds
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
On the same test ICSI measures 90.9% with 30 seconds per recording (359 of 395
trials) and 92.4% with full history (365 of 395), with zero wrong
identifications. The gap to AMI is all refusals. ICSI also enables a larger
same-room test (410 trials of people probing their room-mates' profiles, with
their own profile in the library): one wrong match appeared (0.2%). ICSI runs as
a standing validation corpus alongside AMI.

## The real timeline

The tests above pool several recordings per profile and use speech cut by human
reference labels. This test follows normal use. A profile is saved from the
first meeting where a person clears the floor, later meetings are scored in
order, and each correct match teaches the profile. About one person in five
never saves a profile and serves as a stranger. Each row covers 30 meeting orders
and scores a person's main voice in each meeting, by voice alone.

| Corpus and pipeline | Named correctly | Wrong name | Strangers given a name |
|---|---|---|---|
| AMI, 46 meetings, current pipeline | **98.0%** (2,630 trials) | 0 | 0 of 2,415 |
| AMI, 168 meetings, earlier pipeline | 97.0% (11,072 trials) | 31 (0.3%) | 47 of 8,401 (0.6%) |
| ICSI, 64 meetings, earlier pipeline | 94.2% (8,166 trials) | 0 | 0 of 3,608 |

These counts repeat the same people across meeting orders, so they are not
independent trials. The first row covers 44 returning people and 172 separate
stranger appearances, so its zero is compatible with a true stranger rate of up
to about 2%. In that row every main voice with 30 seconds or more of speech was
named correctly; the misses are shorter. Its 46 meetings leave out most of the
voice pairs behind the errors in the second row, so they do not show that those
pairs are solved.

## Switching devices

A profile enrolled on one microphone and heard on a very different one is the
hardest realistic case for a returning speaker. Measured with AMI's two capture
chains standing in for a device switch (headset for enrollment, distant room
array for recognition): with full-meeting evidence the switch costs little —
94% recognized versus 97% on the matched device — but with only 20 seconds of
heard speech, recognition drops to 25% versus 64%, all of it refusals rather
than wrong names. Once a single meeting on the new device is confirmed into
the profile, 20-second recognition recovers to 40%
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
  someone else's saved profile has to be *more* confident than one that stands
  alone. In a same-room test on earlier vectors, a plain best-match rule gave 5
  of 1,401 trials a wrong name at full-meeting length. This rule removed all
  five when the other person also had a saved profile, and none when they were
  a stranger with no profile. All five come from two pairs of voices. This page
  used to report only the first case, and called it stranger trials.
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
- **The alternatives were measured, not assumed.** Intuitive alternatives that
  measured no better — or actively worse — than the simpler approach are not in
  the app.

## Merging two recordings of the same voice

When you merge two meetings, an unnamed speaker in one may be the same person
as an unnamed speaker in the other. The app decides that automatically, from
voice alone, and the two costs are not symmetric: two rows a person can
merge in one click, versus two people fused into one identity. Measured on
AMI — 975 pairs of the same speaker across two recordings, 2,646 pairs of
different speakers from the same room and series, 218,823 from different
rooms — with both recordings cut to the same amount of speech:

| Speech per recording | Same speaker unified | Different speakers fused (same room) | Different speakers fused (different rooms) |
|---|---|---|---|
| 20 seconds | 13.8% (135 of 975) | 0 of 2,646 | 0 of 218,823 |
| 40 seconds | 50.3% (490 of 975) | 6 of 2,646 | 0 of 218,823 |
| Full meeting | **93.0%** (907 of 975) | **0 of 2,646** | **0 of 218,823** |

Short recordings split rather than fuse. The six wrong fusions at 40 seconds
all trace to reference clusters whose first 40 seconds contain a second
speaker's voice; at full-meeting evidence the same pairs score far apart.
Below 20 seconds the app does not unify on voice at all.

## A second voiceprint, used only like-for-like

Each speaker turn now also carries a second voiceprint, computed in one pass
from that speaker's own audio after the meeting ends. It is stored next to the
existing voiceprint, not in place of it, and every number above still comes
from the existing one.

The two are never compared with each other. When saved profiles built from the
existing voiceprint were scored against the new one, recognition of the
author's own microphone fell from 91 to 76 of 120 trials. So the second
voiceprint is used only when both the saved profile and the new meeting have
it, and only for a speaker the existing matcher left unnamed. It never changes
a name the existing matcher assigned or a match it refused, and it does not
override a name the meeting's context gave.

The effect is small and starts late. A profile needs second-voiceprint audio
from more than one meeting after the update before this applies. Measured
with the exact decision rule:

| Substrate | Correct identification | Added wrong identifications | Unenrolled speakers named |
|---|---|---|---|
| AMI, 3-meeting profiles (552 trials) | 97.3% → 97.5% | 0 | 0 |
| AMI, 2-meeting profiles (600 trials) | 96.0% → 96.2% | 0 | 0 |
| ICSI, 3-meeting profiles (347 trials) | 95.1% → 95.1% | 0 | 0 |
| ICSI, 2-meeting profiles (362 trials) | 92.3% → 92.3% | 0 | 0 |
| Author's own microphone (10 trials) | 8 → 9 of 10 | 0 | 0 |

These trials use whole-meeting recognition and profiles from two or three
earlier meetings, so their baseline is higher than the 30-second-enrollment
headline above. The zeros are measured zeros with small denominators, not
guarantees.

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
- No test here passes audio through a call. Conferencing codecs and network
  loss are not measured.
- All corpora are English. One person speaking two languages is not measured.

## Methodology

Voice embeddings come from the same on-device pipeline the app ships
(FluidAudio speaker embeddings); profile construction, matching, and refusal
logic run the production decision rules. Genuine trials hold out each
recurring speaker's newest session for recognition and enroll from the rest,
so no recognition audio ever contributes to the profile it is scored against.
False-accept trials probe every profile with speakers who co-occurred in the
same rooms — the hardest impostor population — plus cross-corpus strangers.
Stranger tests remove the stranger's own profile from the library, as in real
use. A test feeds real voice vectors through both the app's own matching and
profile-building code and these scoring scripts and requires the same decisions;
deliberately wrong copies of the rules must fail it.

The results above are measured on reference-segmented speech, except the
real-timeline section, which runs the same decision rules on the app's own
diarizer output. The benchmark also runs as a regression gate for changes to
profile logic.

## Reproducibility

The headline, second-corpus, real-timeline, device-switch and same-room stranger
rows were produced at `parakeet-transcriber` commit `acbf5a45` with
`scripts/profile_identity_benchmark.py --production-gallery` (`--corpora ami`, then
`--corpora icsi`), `scripts/exp_identity_tuning/many_orders.sh`,
`scripts/identity_decision_cells.py deviceswitch`,
`scripts/centroid_pricing_cells.py production` and
`scripts/time_to_eligibility_cell.py`, at default parameters. The
enrollment-floor row was produced at commit `8efacf56` on the same
substrate, also with production default parameters; the enrollment-floor
recalibration (30 → 20 seconds, the current release's rule) was produced at commit `afc0a31f`, and the
one-wrong-in-410 same-room row at commit `126c0a05`. The first device-switch and
shared-profile measurements were produced at commits `6a62b013`, `5fed6281`,
and `468c3f59`, and the shared-profile follow-ups and diarizer-output check
at commits `323421b3` and `d1067e57` — production default parameters
throughout. The voiceprint-evidence rows were produced at commit `dc0bd03d`
(against `c57c3bec` for the before arm) with
`scripts/evidence_retention.py --batch` over the committed golden pairs in
`Tests/Fixtures/golden_pairs`, each replayed with `--replay-raw-pair`; the
cluster-consistency calibration with `scripts/coherence_floor_rttm.py` at
default parameters on the cached AMI embedding substrate. The
merge-across-recordings row was produced at commit `866a9299` with
`scripts/identity_decision_cells.py mergepair` on the same substrate, default
parameters. The second-voiceprint rows were produced at commit `060788641`
with `scripts/exp_identity_tuning/recipe_match_sim.py all 3` and `all 2` on the
AMI and ICSI embedding banks built by `scripts/exp_identity_tuning/bank.py`,
default parameters, and over the committed golden pairs replayed with that build for the
microphone rows.
