# Playback prototype test record

Date: 2026-11-16. Environment: Linux, Python 3.12.14, genanki 0.13.1,
Anki Python engine 26.9.4. Test collections are temporary and isolated from
personal Anki profiles.

## Automated results

Original prototype regression checks — **6 tests passed**. The current combined
suite has 13 tests; see [the comparison record](../prototype/COMPARISON.md).
Run all checks with `python -m unittest discover -s tests -v`.

1. Package has one note, one card, exactly one correctly mapped media file,
   reserved IDs and no included review history.
2. Anki imports it, resolves the sound to an audio tag, renders no answer
   metadata on the question, renders metadata on the answer, and reports no
   missing or unused media. The answer does not request automatic replay.
3. After a real scheduler answer, a newer package changes title/year while
   retaining note/card IDs, scheduling state and the complete review log.
   Importing it again creates no duplicate card or note.
4. Metadata and audio changes preserve the note GUID; audio byte changes alter
   the content-based filename.
5. HTML-like title/artist text is escaped, not executed.
6. Invalid IDs, empty text, control characters, non-integer years and missing or
   empty audio inputs fail validation.

The generated WAV was separately decoded successfully with FFmpeg; FFprobe
reported exactly 3.000000 seconds. This confirms decodable bytes, not audible
output through Anki's native player.

The minimal-front revision was also imported over the previous six-field
prototype after recording a review. Rendered question content contained only
the replay control; the existing card, scheduling state and review history
were preserved. The note schema was kept unchanged. Album remains planned
for the future schema, rather than introducing an incompatible field addition.

CI runs these import/update tests and a sample build. It publishes no release
or generated media. Build-time dependencies are pinned separately from the
optional Anki test dependency.

## User-reported manual result

On 2026-11-16, the user confirmed that the native prototype was imported and
worked in Anki. This is a positive manual playback result. The client version,
operating system, offline behavior, sync, night mode and update workflow were
not separately recorded; do not mark those checks as passed. Neither mobile
client was validated by this report. PR #1 was merged before the second
experiment started.

## Compatibility matrix

| Surface | Import / update | Playback / replay / layout | Status |
| --- | --- | --- | --- |
| Anki engine 26.9.4, Linux | Passed | Audio tag resolution and rendered HTML passed | Automated backend evidence only |
| User's Anki client, version not recorded | Import and playback reported working | Positive user report; detailed replay/layout checks not recorded | Native one-card prototype only |
| Agent-side Anki Desktop GUI | Pending | Pending | No usable local graphical display; attempted headless Chromium layout check was blocked by socket restrictions |
| AnkiDroid | Pending | Pending | Device test required |
| AnkiMobile | Pending | Pending | Device test required |
| Spotify embed inside Anki | Not implemented | Pending | Reference template inspected only |

Do not infer GUI or mobile playback support from engine tests. No browser
screenshot or successful live Spotify playback is claimed.

## Manual test steps

1. Use a disposable profile and import `build/playback-prototype.apkg`.
2. Open **Ultimate Hitster → Playback Prototype**. Check the replay control and
   three-tone clip with the network disabled. Check narrow layout and night mode.
3. Confirm the front has no artist/title/year value. Show the answer; confirm
   all three values appear and replay still works. Grade the card once.
4. Copy `prototype/sample.json` into ignored `local/`, correct its title/year
   while retaining `study_id`, and build a newer package. If both builds happen
   in the same second, wait for the next second before rebuilding.
5. Reimport with update-if-newer and no imported learning progress. Confirm a
   single note/card remains, the correction appears, and Card Info still shows
   the previous review. Verify Tools → Check Media has no missing files.
6. Repeat after media sync on AnkiDroid and AnkiMobile. Record client versions,
   OS versions, autoplay settings and actual pass/fail results in this document.

For a real clip, pass `--audio` and a matching fixture as described in
[the prototype guide](../prototype/README.md). Keep that fixture and clip in
ignored local paths. Replacing clip bytes can leave the old file unused in an
existing collection; inspect Anki's media report before cleanup.
