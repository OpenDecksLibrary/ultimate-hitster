# Original France validation record

Date: 2026-11-16. Python 3.12.14, genanki 0.13.1, Anki engine 26.9.4.

| Check | Result |
| --- | --- |
| Hitify cards / production notes | 308 / 308 |
| Unique pinned recordings | 308 |
| Metadata comparisons / explicit label reviews | 301 / 7 |
| Exact-track album names | 308 |
| MP3 fetch, signature, FFprobe and full decode | 308 passed |
| Missing or failed excerpts | 0 |
| Measured excerpt durations | 14.968163–29.753469 seconds |
| Automated tests | 27 passed |
| Complete online import | 308 new notes/cards |
| Online → offline update | 308 updated; same card IDs, scheduling and complete review log |
| Offline media check | 0 missing / 0 unused |
| Older online import with Update Always | 308 updates; scheduling and history retained |

Both production packages contain 308 cards. Online embeds no media; offline
contains 308 distinct MP3 files. It uses the exact bytes checked for online,
with full content hashes. No source/reference ID was silently replaced.

## Explicit version-label reviews

The IDs come from the pinned card-reference CSV, not a fuzzy search. The
following catalogue labels omit or format provider version details differently.
Those exact source IDs are kept, with an explicit review entry and the tag
reference::reviewed. This is an auditable validation choice, not proof of a
physical-card/audio comparison.

| Card | Catalogue title | Exact provider title |
| --- | --- | --- |
| 58 | Happy | Happy - From "Despicable Me 2" |
| 80 | Under Pressure | Under Pressure - Remastered 2011 |
| 110 | La Bamba | La Bamba - Single Version |
| 170 | Get Lucky (feat. Pharrell Williams and Nile Rodgers) | Get Lucky (Radio Edit) [feat. Pharrell Williams and Nile Rodgers] |
| 198 | Lean On (feat. MØ & DJ Snake) | Lean On |
| 263 | The Ketchup Song (Aserejé) | The Ketchup Song (Aserejé) - Spanglish Version |
| 292 | Shallow | Shallow - Radio Edit |

110 provider release dates differ from the catalogue year. Provider dates
can describe reissues/remasters; all Hitify catalogue years are retained.
The machine-readable list is in data/reports/original-france.json.

## Provenance and verification limits

The Hitify input is a normalized public-table snapshot; direct HTTP access
returned 403 here. The importer handles a saved original page or live page
when reachable, with no ten-card cap. The 308-row reference CSV is a separate
community source. Its first 100 IDs match the public Hitify playlist prefix.
All 308 exact track metadata pages were checked; the remaining 208 mapping
positions were not independently observed in the truncated playlist embed.
Historical QR URLs tested for cards 1 and 308 redirect to the app download
page. No physical-card scan or independently confirmed printed years are claimed.

The earlier native and corrected HTML5 MP3 prototypes were reported working
by the user. The complete 308-card packages are ready for manual validation,
not claimed tested in the GUI or on mobile. Decode/import tests do not prove
audible playback, sync, layout, client codec behavior or permanent URL availability.
Listen to the seven reviewed version labels and record client/OS versions.

## Artifacts

| Package | Bytes | SHA-256 |
| --- | ---: | --- |
| ultimate-hitster-original-france-online.apkg | 233690 | 565d16a990b5ec7dd4b35240a4ebb3fd03f7b71d9da81bb89148d8f19b7ce210 |
| ultimate-hitster-original-france-offline.apkg | 104922645 | fa3555c0880e39668ef073433271d358753d0495eac386455e1d6ceb8dfa72c4 |

Production modes are alternative representations of the same notes/deck.
They preserve history when switching/updating; choose Update Always if the
target file has an older timestamp. Existing prototypes are unchanged and
their progress is separate. No other edition or stable release is published.
