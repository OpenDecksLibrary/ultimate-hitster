# Manual multi-edition validation

No result is assumed from an automated import or MP3 decode. All results below
are pending until a tester records the actual application/version, operating
system, package checksum, date, observations and pass/fail.

| Client | Online playback | Offline playback | Upgrade/overlap | Current result |
| --- | --- | --- | --- | --- |
| Anki Desktop | Pending | Pending | Pending | Not tested for v0.3 |
| AnkiDroid | Pending | Pending | Pending | Not tested |
| AnkiMobile | Pending | Pending | Pending | Not tested |

The earlier user-reported native and remote prototype successes apply only to
those prototypes. They do not validate these full selections or mobile clients.

## Preparation

1. Back up the collection and use a disposable test profile/collection.
2. Download candidate workflow artifacts and verify SHA256SUMS before importing.
3. Import the published v0.2.0-beta.1 Original France online APKG.
4. Review several cards with different answers; record their card IDs, due dates,
   intervals, review counts and history. Move one card into a personally named deck.
5. Keep the existing deck and notes. For equal/older-timestamp mode packages, use
   Update existing notes: Always. Leave deck placement/scheduling overrides off.

## Import sequence

1. Import the candidate Original France online package: exactly 308 original
   study facts, same note/card IDs, same scheduling and review history.
2. Import Original Refresh France, then Guilty Pleasures France. Shared studies
   update; new studies are added. The expected union count is in validation.json.
3. Import France, then the complete imported catalogue. Verify no duplicate
   study IDs and compare the expected counts in each build report.
4. Import offline variants, then return to online. Verify scheduling, the personal
   deck placement and review history again. Reimport an individual edition after
   the union; other editions must not be deleted or duplicated.
5. Browse a shared song: all known edition/country/language tags are present.
   Create filtered decks by edition tag and verify the shared card is the same card.
6. Find a conflicting-year case listed in catalogue.json if any. Confirm distinct
   year answers and study IDs with the same recording; this duplication is deliberate.

## Playback and answer visibility

- At the front, only the audio player is visible: no artist, title, year, album,
  edition heading or instructions. Test both day and night themes.
- Start/pause/replay the online MP3 with a working connection. Reveal the answer:
  artist, title, catalogue year and optional album appear. Check audio behavior
  when revealing, moving to the next card and replaying.
- Disconnect completely. Online playback may fail; metadata must remain hidden.
  Offline playback must work after media import/sync has completed.
- Test at least one known shared recording, a distinct musical version and an
  uncertain/missing reference from the report. A missing player must not silently
  play a replacement recording; the answer remains visible after revealing it.
- Listen to source/reference disagreements and compare with the physical card or
  edition's QR target where available. Record evidence before accepting a review.
- On mobile, complete media synchronization before testing offline. Repeat the
  import/upgrade sequence on a backed-up collection or sync the Desktop result,
  recording which path was used; synced playback alone does not validate APKG import.

## Record results

Copy the following for each client:

~~~text
Client/version:
OS/device:
Date:
Artifact workflow run and source commit:
SHA256SUMS verified:
Import path (direct APKG or synced collection):
Initial / added / final card counts:
Card IDs and scheduling comparison:
Review history comparison:
User deck placement:
Online playback:
Offline playback (airplane mode):
Front hides metadata:
Answer shows expected fields:
Uncertain reference listening checks:
Failures, screenshots/logs and reproduction:
Tester:
Result: pending / pass / fail
~~~

Do not replace pending results with pass until these checks have real results.
Candidate publication needs PR review/merge and recorded validation; creating this
procedure does not authorize publishing v0.3.0-beta.1.
