# Playback experiment: native packaged audio first

Status: **provisional experiment**, 2026-11-16. This is not a production
architecture decision or a statement of mobile compatibility.

## Comparison

| Approach | Blind question side | Offline / media | Dependencies and limitations | Evidence so far |
| --- | --- | --- | --- | --- |
| Anki `[sound:filename]` | Only a native replay control; no answer fields needed | Works with packaged local clips; increases package size | Client playback must be checked; the clip itself may contain spoken clues | Supplied NL templates; prototype imported and rendered by Anki's engine |
| Cropped Spotify iframe | Metadata visually clipped, but still in the iframe | Network and provider playback required; no packaged audio | Fixed pixel offsets; provider layout, login and encrypted-media support affect behavior | Supplied Quiz Bowl template inspected; live playback untested |
| HTML `<audio>` | Neutral controls possible | Local or remote media | Custom player behavior and client webview support need testing; remote URLs can expire | Considered only; not an Anki implementation in this prototype |

Use the native implementation for the first importable experiment because it
needs no JavaScript, login, iframe or runtime network requests. Do not build a
Spotify SDK integration or a reusable media abstraction before client testing.
Keep online playback as an open experiment if distributing local media proves
impractical at catalogue scale.

Spotify documents context-dependent playback, including preview-only playback
when encrypted media is unavailable. It does not give this project control of
a universal 30-second excerpt. Its current recommended compact embed is 152
pixels high; the reference deck's 80-pixel player is a legacy layout.

## Prototype behavior

- One note and one recognition card. Recall artist, title and game-card year
  together; optional difficulty modes are deferred.
- The front includes only the Audio field, with no branding or instructions. The back
  reveals Artist, Title and GameYear. No answer is hidden in CSS on the front.
- Album is planned as optional answer-side information in the future model;
  the current six-field schema stays unchanged for standard prototype updates.
- Audio contains the entire `[sound:filename]` reference, allowing Anki's media
  checker to find it. Filenames contain a prefix and SHA-256, not answer text.
- `FrontSide` retains the question on the back without automatically replaying
  the clip. Playback/autoplay preferences remain under the user's Anki settings.
- The default fixture uses three original synthesized tones, not a Hitster song.
  This validates the plumbing, not music recognition or catalogue accuracy.
- A supplied local clip is copied into the package once. No media download,
  trimming, transcoding or full-track mode is implemented. Prepare excerpts
  before building; MP3 is a candidate for later size testing.

Normal review does not show metadata on the front. This is a self-study interface,
not a way to conceal answers from someone inspecting note fields or media tags.

## Identity and updates

Prototype IDs are reserved separately from future production IDs. The note GUID
is derived from a fixed namespace plus immutable `study_id`. Editing title,
artist, year or clip bytes does not change the GUID. The first field stores
StudyID; model ID, field order, template order and deck ID stay fixed.

`track_id` identifies the recording; `study_id` identifies the fact being studied.
A correction keeps its study identity. Two genuine edition-year variants must
have distinct study identities, allocated independently of the literal year.
Overlapping edition memberships should eventually point to the same study
identity when the facts agree. The prototype does not yet implement those joins.

Import tests use a newer package with Anki's default update-if-newer behavior,
record an actual scheduler answer, and check note/card IDs, scheduling columns
and the full review log after importing a correction and repeating that import.
This does not establish compatibility across different schemas, clients or
overlapping regional/global packages. Do not delete cards before updating.

The build is repeatable from the fixture, and identities/audio bytes are stable.
APKG bytes are **not** guaranteed reproducible: timestamps and generated database
row IDs can differ. A production build needs an explicit version/timestamp policy.

## Validation and release gate

See [the test record](PROTOTYPE_TESTING.md). No GitHub release is published by this
prototype or its CI workflow. Before the first public collection release:

- Verify a small real edition sample and the meaning of each printed year.
- Test play, replay, reveal and media sync on Desktop, AnkiDroid and AnkiMobile.
- Repeat update tests in those clients, including overlapping edition packages.
- Agree stable production schema and IDs before importing a larger catalogue.

## Primary documentation

Consulted 2026-11-16:

- [Anki field replacements](https://docs.ankiweb.net/templates/fields.html)
  (complete sound references and `FrontSide` behavior).
- [Anki media](https://docs.ankiweb.net/media.html) (media checks and filenames).
- [Anki packaged deck updates](https://docs.ankiweb.net/importing/packaged-decks.html)
  (update conditions and schema caveats).
- [Spotify embed troubleshooting](https://developer.spotify.com/documentation/embeds/tutorials/troubleshooting).
- [Spotify embed sizes](https://developer.spotify.com/documentation/embeds/tutorials/creating-an-embed).
