# Original France source evidence

- original-france.hitify.html is a normalized snapshot of the complete table
  at https://hitify.app/en/hitster-editions/original-france, retrieved
  2026-11-16. All 308 numbers, artists, titles and catalogue years are retained.
  It contains no external scripts/images and is not a raw HTTP capture.
  Direct HTTP access returned 403; public page retrieval supplied the table.
- original-france.references.csv comes from
  https://github.com/oleuml/musicminds-hitster-playlists/blob/main/hitster-aaaa0004-fr.csv.
  It maps numbered cards to Spotify IDs and historical QR URLs, credits the
  original songseeker contributors and is distributed under the included
  REFERENCES_LICENSE.txt. No song-search result replaced a pinned ID.
- The first 100 IDs match the public Hitify-linked playlist, in order:
  https://open.spotify.com/playlist/2lAku81lIpo9szImYSFv9h.
  Its embed exposes 100 rows. The remaining mapping comes from the card CSV,
  checked against exact provider metadata; no full 308-row embed is claimed.
- Historical QR URLs tested for cards 1 and 308 redirect to the general
  Hitster app download page, so do not independently prove the Spotify target.
  No successful physical-card scan is claimed.
- original-france.reviews.json records seven abbreviated catalogue labels
  and their explicit provider-version labels. The exact source IDs are kept
  for validation, with physical-card/audio comparison outstanding.

Hitify catalogue years take priority over CSV/provider dates. Provider dates
may describe a remaster, reissue or compilation; differences are reported
without automatic correction.

Provider/album evidence comes from public Spotify track/embed pages by exact
ID. Canonical files retain only normalized public metadata, MP3 URLs and
checks. HTTP caches and downloaded MP3s stay ignored under build/. The CSV
license does not describe audio ownership.
