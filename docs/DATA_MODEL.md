# Production catalogue schema v1

Schema v1 is the production contract for the Original France validation build.
File layouts, namespaces, field order and IDs are frozen for this version.
Future incompatible changes require a migration. Prototypes remain separate.

| File | Entity | Purpose |
| --- | --- | --- |
| data/tracks.json | Recording | Immutable recording_id, canonical artist/title, optional album, provider aliases, metadata and audio evidence |
| data/editions.json | Edition | Immutable edition_id, region/language, card count, source provenance and year semantics |
| data/editions/EDITION.json | Membership | Immutable membership_id, card number, recording, catalogue year, study identity and exact-reference evidence |

Every file has schema_version 1. The root arrays are recordings, editions and
memberships respectively. Source snapshots and explicit label reviews under
data/sources are audit inputs, not another editable song catalogue.

## Recording identity and deduplication

Recording IDs are initially allocated with UUIDv5 in namespace
a352d6e0-24ad-41c1-bb02-a31a5ed2b72c, anchored to the first exact Spotify ID.
Once stored, they are immutable registry identities. Add reviewed provider
aliases to an existing recording; do not recompute its ID from a later alias.

Exact Spotify IDs deduplicate imports. A provider alias cannot belong to two
recordings. Matching names never automatically merge recordings, covers, live
versions, edits or remasters. ISRC/fuzzy equivalence requires verified evidence
and an explicit alias/merge decision. A changed recording reference for an
existing card fails import instead of silently replacing its identity/history.

Canonical names come from the first catalogue, not automatic provider text.
France preserves Hitify's artist, title and year values. Raw rows remain in the
normalized source snapshot. Case, punctuation, diacritics and artist order can
be compared without changing display values; version labels are not stripped.
Explicit shortened-label reviews bind exact card/provider IDs and both titles
and fail if those values change.

## Memberships and study facts

Catalogue years are separate from provider release dates. France's year_kind
is catalogue_release_year; printed physical-card years are not independently
verified. A remaster/reissue date never overwrites the catalogue year.

study_id identifies the recognition fact, independently of mutable text, URL,
mode or literal year. New memberships with the same exact recording and agreeing
year reuse a study ID. A genuinely conflicting edition year gets a distinct
study ID anchored to its first membership. Correcting an existing membership's
year retains its ID. Conflicting facts sharing a study ID fail validation and
require a reviewed split/correction; shared facts are not silently changed.

Reference states are verified (provider ID/metadata agree), reviewed (explicit
version-label decision), metadata_mismatch and fetch_failed. Neither verified
nor reviewed claims a physical-card scan. Review reasons are stored and tagged.

## Checked audio and albums

Audio states are unchecked, verified, unavailable and check_failed. Verified
audio includes an approved unsigned HTTPS MP3 URL, SHA-256, measured duration,
successful decode evidence and a UTC check time. A URL alone is not verification.
Every selected clip is fetched and decoded during check-audio. No different
song, recording, provider or format is silently substituted.

Album metadata is optional and read from the exact track page's matching album
link. Missing or ambiguous album metadata stays unknown.

## Frozen production Anki contract

- Model ID: 1735079001; distinct from all prototype IDs.
- France deck ID: 1735079101; explicitly assigned in the config.
- Fields, in order: StudyID, RecordingID, Artist, Title, Year, Album, Playback.
- One Recognition template: front is Playback only; back reveals year, title,
  artist and conditional album, retaining the player.
- GUID namespace: OpenDecksLibrary:UltimateHitster:production:v1 plus StudyID.
  Mode, edition selection, URL, title, artist, album and year are excluded.
- Online and offline are alternative representations of the same production
  notes/deck. They update each other rather than making two study copies.
  Prototypes keep their own separate identities.

Playback contains either neutral HTML5 MP3 controls or a native Anki sound
reference. Mode changes require no schema changes. Content-addressed filenames
use uh_FULL-SHA256.mp3 and identical bytes are packaged once. Edition/card tags
retain membership information; a shared note/card belongs to one Anki deck.

CLI builds reserve monotonically increasing timestamps in ignored
build/anki-build-epoch.txt, preventing same-second mode builds from tying
Anki's update-if-newer check. Library callers supply a newer explicit timestamp.
APKG bytes are not guaranteed reproducible; IDs, source data and audio hashes
are the stable contract.
