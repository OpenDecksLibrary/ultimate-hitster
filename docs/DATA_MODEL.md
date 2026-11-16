# Proposed data model

Use versioned JSON source files and immutable identifiers. These conventions are provisional until validated against Anki imports.

## Tracks (`data/tracks.json`)

Each entry has `track_id` (immutable opaque ID), `artist`, `title`, optional `recording_year`, optional `isrc` / `musicbrainz_recording_id`, and optional `providers` with provider-specific track IDs. Distinct recordings, covers and remixes remain separate even when titles match.

## Editions (`data/editions.json`)

Each entry has `edition_id` (immutable ID), `name`, `region`, `language`, optional `revision`, and `sources` (URLs and access dates).

## Edition membership (`data/editions/*.json`)

Each entry has `edition_id`, `track_id`, `card_number` (string), `game_year` (integer) and optional source or correction notes. Keep the year printed by the game separate from the recording's release year. Do not silently resolve conflicts.

## Anki export

Use an explicitly assigned stable model ID and a deterministic note GUID derived from a stable study identity, never from mutable artist or title text. If the same recording has conflicting game years, preserve separate study identities or expose the difference explicitly. Use tags for edition membership; shared notes must not be assumed to belong to several decks at once. Verify overlapping package imports before publishing global and regional builds.

Keep local media separate from source data, and select playback implementations after platform testing. Do not commit media or private imports.
