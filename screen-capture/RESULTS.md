# Screen Capture Benchmark Results

With Capture Presentations on, MimicScribe saves a picture of the shared window when a new slide, document or page appears. Faces in a picture are blurred before it is written to disk. This page measures two things: how often a saved picture repeats a screen already captured, and how many faces the blur covers.

Run date: 2026-10-16 | 7 public Zoom recordings, about 7 hours | parakeet-transcriber `ab77ab0f1`

## Overall

| Metric | Result |
|--------|------:|
| Pictures that are not a repeat of a screen already captured | **83%** (262 of 314) |
| Faces blurred | **98.2%** (279 of 284) |

## Repeats

Each recording was played through the app's capture detector frame by frame, as a live shared window would be. Every distinct screen in the recordings was labelled by hand (337 screens). A picture counts as a repeat when an earlier picture already shows the same screen. A document edited over several minutes can get updated pictures as the edit goes on; those count as new.

| | Pictures |
|---|---:|
| Saved | 314 |
| Repeats | 52 |
| Taken while no screen was shared | 3 |

Most repeats come from one kind of screen: a web editor whose text reflows as messages are opened, so the same page looks different each time. Slide decks come through slide by slide.

The detector skips screens that are only on show briefly, so it does not catch every screen. It caught 72% of the labelled screens (243 of 337): all of them in two slide-heavy talks, and 60–64% in the two recordings with long live web demos, where pages change every few seconds.

## Face blur

169 full-resolution frames were taken from the same recordings, one every 40 seconds, weighted toward webcam galleries. Each frame went through the app's own face search and blur. An independent face detector (OpenCV YuNet, score ≥ 0.7) then marked every face it could find, and a face counts as covered when at least half of it falls inside a blurred area.

| Face size | Covered |
|---|---:|
| Under 32 px | 5 of 7 |
| 32–64 px | 65 of 68 |
| 64–128 px | 149 of 149 |
| Over 128 px | 60 of 60 |
| **All** | **279 of 284 (98.2%)** |

The 5 faces left are small round avatars on a slide, painted or cartoon faces, and a half-cropped webcam face. If the face search fails on a picture, the picture is not saved. YuNet cannot judge faces in profile, so those are not scored.

## Corpus

Seven Zoom meeting recordings from Wikimedia Commons (CC BY / CC BY-SA): OpenRefine and SDC community meetup (Feb 22 2022), GMT20210812-090035 Recording, LDH Mentees Working Session (27th July), Challenges of Small Wikis (29th August), August 2024 Future Audiences office hours, Defense Against the Dark Arts – Disinformation on Wikipedia, and Translatewiki 101.

## Caveats

- The detector was tuned on these same seven recordings. A separate set of ten recordings (Teams, Google Meet, spreadsheets, code) is held back for testing and has not been scored yet.
- All recordings are Zoom's own composited recordings, not a live window, so window resizing and switching are not covered.
- Screen labels were drafted with model help and reviewed by one person, and faces were judged by one model. A small shift in where a screen starts can move a picture between "new" and "repeat".
