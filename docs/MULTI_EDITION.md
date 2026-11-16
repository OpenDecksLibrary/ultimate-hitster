# Universal edition support (v0.3 candidate)

## Scope and provenance

The available-edition registry is discovered from Hitify's English edition index.
Discovery stores market, market languages, family, revision, card count, source
URL, index fingerprint and import status; it does not import any songs.
"Available" means listed by Hitify, not validated against a physical box.
Market languages are explicitly inferred and are not the languages sung on every
recording. A multilingual region retains all candidate market languages; an
unknown market uses und. The index snapshot makes discovery reproducible.
Edition-specific overrides belong in import configuration, not importer code.

The selected import plan adds Original Refresh France and Guilty Pleasures France.
The original 308-card France dataset remains the published baseline. New
catalogue rows come from Hitify; per-card Spotify references come from the public
Hitster for All playlist JSON used by its scanner. Each source is fingerprinted.
No Spotify ID is selected by title search. Independent Spotify playlist positions
are compared where publicly exposed; this is partial evidence, not a claim that
all physical QR codes or musical masters were manually checked.

References with absent/ambiguous IDs, source disagreement, provider mismatch,
unavailable metadata or missing audio remain explicit issues. Unresolved rows are
retained with a deterministic identity and a player with no source; strict builds
fail. A later identity resolution requires an explicit identity review, rather
than silently replacing a published recording.

## Identity, deduplication and years

Schema version 1, production model 1735079001, its seven fields, the note GUID
namespace and every published Original France membership/recording/study ID are
unchanged. A checked-in fixture pins all 308 baseline identities.

A shared exact Spotify ID identifies one recording. Different Spotify IDs are
kept separate, even when artist/title text is identical; live, radio edit,
remaster and re-recording distinctions are not stripped. The schema already
allows reviewed provider aliases on a recording, but title similarity is not
evidence for adding one. Potential remaining aliases require human review.
Offline media are deduplicated by content SHA-256, independently of note count.

One recording plus the same catalogue year reuses one study ID and one Anki card.
Different catalogue years use distinct study IDs and answers while sharing the
recording and MP3. Neither a provider reissue date nor an edition imported later
overwrites another edition's year. Every membership keeps its own catalogue
artist/title as provenance; a shared card displays the recording's canonical
artist/title. Original France's existing rows and years are preserved.

## One card, one deck

Individual, country, family, custom and global selections are subsets of the same
production notes; they are not separate copies of the songs. New universal
packages put new cards into Ultimate Hitster. The Original France package retains
its published deck identity/name for compatibility.

Anki keeps an existing card in the deck where the user has placed it during
subsequent imports. Thus importing Guilty Pleasures after Original France adds only
new study facts; shared cards retain their schedule and their existing deck.
Importing a global collection later expands the collection without making every
existing card move into the new deck. Users may select all production cards in
Browse and use Change Deck to organize them; this preserves their history.

Use tags or filtered decks for overlapping editions. A shared card carries every
known edition's country, language, edition and card-number tags, even in a
single-edition export. Decade tags use the study's catalogue year. Tags are
hierarchical: country::FR, language::fr, edition::hitster-original-france,
family::original, decade::1980s. Language tags describe edition markets.
Anki may retain tags from earlier imports; tags are not a mechanism for deleting
previously imported editions. A smaller package does not remove other cards.

## Commands

Install the existing project and test requirements. No new runtime dependency is
needed.

~~~sh
python -m pip install -e . -r prototype/requirements-test.txt
python -m ultimate_hitster discover-editions
python tools/import_catalogue.py --plan configs/import-v0.3.json --check-audio
python -m ultimate_hitster statistics
python -m ultimate_hitster build --config configs/original-refresh-france.json --mode online --output build/refresh-online.apkg
python -m ultimate_hitster build --config configs/france.json --mode offline --output build/france-offline.apkg
python -m ultimate_hitster build --config configs/original-family.json --mode online --output build/original-family-online.apkg
python -m ultimate_hitster build --config configs/custom-example.json --mode online --output build/custom-online.apkg
python -m ultimate_hitster build --config configs/imported-catalogue.json --mode offline --output build/all-offline.apkg
~~~

Use exactly one config selector: edition_ids (one or more explicit IDs),
countries (market codes), families (registry family IDs), or all: true.
Only imported editions can be selected; the available registry is not an import
instruction. Unknown or mixed selectors fail instead of widening the build.

The low-level import command accepts any registered compatible edition:

~~~sh
python -m ultimate_hitster refresh-references --references data/sources/original-refresh-france.references.json --albums
python -m ultimate_hitster import-hitify --edition hitster-original-refresh-france --references data/sources/original-refresh-france.references.json --html data/sources/original-refresh-france.hitify.html
python -m ultimate_hitster check-audio
~~~

Refreshing references resolves the pinned IDs only. Re-import the saved catalogue
snapshot to apply updated preview URLs; do not fetch new edition years implicitly
during a URL-only renewal. Recheck audio before packaging. import_catalogue.py
uses saved source snapshots/caches unless --refresh is explicitly requested.
Run it on a review branch; it never imports editions outside its plan.

## Validation and delivery

See [the generated statistics](../data/reports/catalogue.json), the available
[edition registry](../data/registry.json), and the [manual procedure](MANUAL_VALIDATION.md).
Automated tests use real Anki collections and check successive overlapping
imports, expansion to country/global selections, mode changes, user deck
placement, scheduling, review history, identities, tags and media reuse.
The validation workflow also imports the actual v0.2.0-beta.1 online APKG before
the new complete packages and verifies its published checksum.

release-candidate.json prepares v0.3.0-beta.1 but has publish: false. It is not the
active release plan. The candidate workflow uploads APKGs, checksums and reports
as Actions artifacts only. No tag or release is created. Candidate artifacts are
temporary and intended for manual validation, not stable distribution.
The existing prototypes and v0.2 release assets remain available.
