# Hitify catalogue investigation

Observed on 2026-11-16. This investigation stores only a ten-card sample;
`data/tracks.json` and `data/editions.json` remain unpopulated.

## Public structure

- [`/en/hitster-editions`](https://hitify.app/en/hitster-editions) lists editions
  by region, with names, counts and edition-page links.
- Family pages such as
  [`/en/hitster-editions/original`](https://hitify.app/en/hitster-editions/original)
  distinguish regional boxes. Original and Original Refresh are separate families.
- The [Original France detail page](https://hitify.app/en/hitster-editions/original-france)
  identifies the region, standalone status and 308-card count. An HTML table has
  four columns: card number, artist, title, release year. The first ten rows
  were inspected in both the public page and browser DOM.
- That page links a Spotify playlist, ID `2lAku81lIpo9szImYSFv9h`, explicitly
  described as being in card order. It embeds that playlist in an iframe.
- The edition table has plain text cells, with no per-track provider IDs,
  audio URLs or album names in the inspected rows. A separate
  [`/en/cards`](https://hitify.app/en/cards) search opens song dialogs with
  links to Spotify, Apple Music, Deezer and other providers. Duplicate names
  and alternate recordings exist there; do not blindly take the first match.

The detail table can be parsed without a JavaScript catalogue API. Saving the
edition page as HTML and running the following command extracts only cards
1–10 and fails if the expected four-column structure/order changes:

```sh
python tools/extract_hitify_rows.py local/original-france.html
```

The parser is tested against a small table fixture. The actual ten rows were
read from Hitify, but a complete saved HTML extraction was not run: direct
HTTP retrieval of the Hitify page returned 403 in this environment, while its
public browser page worked. No authenticated, private or undocumented Hitify
API was used. Pagination/search forms in `/cards` are a separate surface from
the edition table and must not be treated as edition membership evidence.

## Sample and recording references

`prototype/france-original.sample.json` holds cards 1–10 in source order, plus
the edition URL, access date, playlist URL and explicitly selected Apple track
IDs. Artist/title/year values come from Hitify. Apple supplies album/collection,
preview URL, full-recording duration and a separate provider release date.
The source values are not silently rewritten using provider dates.

Selections were manually checked against the artist/title and playlist
duration. For example, the 659-second Disco Inferno recording was selected
instead of the search result's re-recording or single edit. ISRCs/master
identity and the physical box's printed years have **not** been verified.
The displayed year is therefore the Hitify catalogue year, not a claim of
independent game-card validation. Album is the provider's collection for the
selected preview; it may be a compilation rather than the original album.

The [Apple Search API documentation](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/UnderstandingSearchResults.html)
describes `previewUrl`, `collectionName` and track fields. Exact provider IDs
are pinned after selection. The refresh tool uses ID lookup, never a new
title search or automatic recording substitution.

## Preview lifetime

The inspected Deezer track response provided a signed preview URL expiring
about 15 minutes after retrieval. A snapshot of that URL would quickly fail
in an APKG. No token-stripping or URL guessing was attempted.

The selected Apple preview URLs are HTTPS URLs without expiry query strings.
All ten were fetched and decoded as approximately 30-second AAC/M4A clips.
Their URLs are still external references: absence of an expiry parameter is
not a promise of permanent availability. The sample pins content hashes and
measured durations for the downloaded comparison clips.

If a URL becomes unavailable, refresh only the pinned recording IDs:

```sh
python tools/refresh_sample_previews.py
python prototype/build_comparison.py --sample build/refreshed-sample.json --mode both --download
```

A changed preview URL clears its old byte hash/duration in the refreshed
copy, so new bytes must be decoded and inspected before establishing a new
pin. The tool does not change answers, album text, provider ID or study ID.
This is an experiment utility, not a full catalogue importer or resolver.
