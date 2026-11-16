# Reference deck inspection

Inspected on 2026-11-16 using `tools/inspect_apkg.py`. Findings apply to the
specific supplied exports, not to every version of these decks. Templates were
read as data; their scripts and remote resources were not executed.

| Supplied file | Notes / cards | Packaged media | Playback implementation |
| --- | --- | --- | --- |
| `HITSTER__HITSTER-NL(1).apkg` | 305 / 305 | 0 | `Song` contains native Anki `[sound:…mp3]` references |
| `Quiz_Bowl_Composers(1).apkg` | 434 / 434 | 0 | Spotify track iframe using the `SpotifyID` field |

Both archives contain `collection.anki21` and a compatibility `collection.anki2`.
Inspect the former; inspecting only the latter would describe the fallback
collection instead of the actual deck.

## HITSTER NL

- Note type: `HitsterDecks`; fields: Artist, Title, Year, Song, Version.
- All 305 notes reference distinct MP3 filenames, such as `1.mp3`.
- The media map is empty: **all 305 referenced files are absent from this export**.
  This proves the playback mechanism, but cannot establish whether the source
  collection had working audio before export.
- The front inserts `Song` without displaying artist/title/year. It also loads
  an external image with a version query parameter. The back displays metadata
  and uses JavaScript for decade styling.
- Generic numbered filenames could collide with media from another collection.
  The prototype instead uses a project prefix and a full content digest.

## Quiz Bowl Composers

- Note type: `MusicCardWithSpotify`; fields: Front, Back, Image, Flag, SpotifyID,
  Description, Tags.
- The front displays `Front` and a 300 × 80 iframe inside a 40 × 80 wrapper with
  `overflow: hidden`. The iframe is positioned at top −40, left −255 pixels.
  This exposes a small control area while clipping most provider metadata.
- 425 notes contain a syntactically valid 22-character Spotify ID; nine other
  values require cleanup before reuse. Syntax does not prove track availability.
- The wrapper only changes presentation. It cannot remove content from the
  cross-origin iframe, and provider layout changes can move or expose controls.
- The back uses `FrontSide`, remote composer images and some local image
  references; no images are packaged in this supplied export.
- The front is not a blind music quiz by itself: the `Front` field can already
  name the piece. We reuse neither its data nor its templates.

## Reproduce the inspection

```sh
python tools/inspect_apkg.py /path/to/HITSTER.apkg /path/to/Quiz_Bowl_Composers.apkg
```

The inspector prints counts, missing sound filenames, model definitions and
templates. It reads the database from a temporary file, never imports personal
review history, and rejects modern compressed collections rather than silently
reading their fallback database. No uploaded APKG or extracted catalogue is
committed to this repository.

File SHA-256 values:

```text
HITSTER__HITSTER-NL(1).apkg
335e098898c53f85dccb84db03aea09aa1e260b6ebfe0a3e1425983889e9dfbc

Quiz_Bowl_Composers(1).apkg
3807cd9fbc17b08a613413cca745f6cf61a5bb7b5ba79f460019ab4ebc7e1f08
```
