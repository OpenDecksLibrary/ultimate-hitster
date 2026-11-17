# Ultimate Hitster

Community-maintained Anki collections for music recognition and release-year
recall, organized around Hitster editions worldwide.

**Status: [v0.3.0-beta.1 pre-release](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/tag/v0.3.0-beta.1). Three imported editions, 643 unique study cards; no stable release yet.**

## Downloads

| Selection | Cards / playable | Online | Offline |
| --- | ---: | --- | --- |
| Original France | 308 / 308 | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-france-online.apkg) | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-france-offline.apkg) |
| Original Refresh France | 308 / 308 | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-refresh-france-online.apkg) | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-refresh-france-offline.apkg) |
| Guilty Pleasures France | 308 / 298 | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-guilty-pleasures-france-online.apkg) | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-guilty-pleasures-france-offline.apkg) |
| Original family | 338 / 338 | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-family-online.apkg) | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-original-family-offline.apkg) |
| All imported editions | 643 / 633 | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-imported-catalogue-online.apkg) | [APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/ultimate-hitster-imported-catalogue-offline.apkg) |

Online requires Internet; offline includes the checked MP3 excerpts.
[SHA256SUMS](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/SHA256SUMS),
[validation.json](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/validation.json),
[exceptions.json](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/exceptions.json) and
[successive-imports.json](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.3.0-beta.1/successive-imports.json)
accompany the ten APKGs. See the [English release notes](docs/releases/v0.3.0-beta.1.md).

## Import safely and keep progress

Keep your existing production notes/decks. Published schema-v1 identities are
compatible with [v0.2.0-beta.1](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/tag/v0.2.0-beta.1).
Online/offline alternatives and overlapping editions update the same notes.
For equal/older-timestamp alternatives, use Update existing notes: Always.

**Enable Import learning progress / Include scheduling** to retain suspension
of newly imported unavailable cards. Existing card scheduling, review history
and personal deck placement are preserved in automated Anki-engine tests.
If that option is disabled, or exception cards were already imported from a
candidate, open Browse after import and search:

~~~text
tag:audio::missing Playback:*unavailable*
~~~

Suspend any active results before ordinary study. A recovered player's old tag
can persist; this combined search checks the current Playback field. See
[unavailable audio and import options](docs/MISSING_AUDIO.md) for details and
restored-card handling. No cards are deleted to update.

The twelve original exceptions were rechecked on their unchanged Spotify IDs.
Two credit-only differences are explicitly reviewed; ten recordings remain
without enabled audio (six absent previews and four unresolved musical versions).
They remain in the catalogue and packages, suspended on fresh imports that keep
scheduling. No recording is silently substituted.

## Catalogue and generation

The [registry](data/registry.json) inventories 175 Hitify-listed editions with
market, inferred market languages, family, revision, count, sources and status.
Only Original France, Original Refresh France and Guilty Pleasures France are
imported: 924 card occurrences, 643 recordings/studies and 281 shared repetitions.
See [statistics](data/reports/catalogue.json) and the
[validation snapshot](docs/MULTI_EDITION_VALIDATION.md).

Generate online/offline packages for individual editions, countries, families,
custom selections or the entire imported catalogue. Country France currently
equals all imported editions. Shared exact recording/year facts use one card;
distinct pinned versions and conflicting year facts stay separate. Existing
cards stay in the user's deck. Use hierarchical edition/country/language/family/
decade tags and filtered decks for overlapping collections.

See [multi-edition rules](docs/MULTI_EDITION.md),
[production commands](docs/PRODUCTION_WORKFLOW.md),
[schema v1](docs/DATA_MODEL.md), [release procedure](docs/RELEASING.md),
[roadmap](docs/ROADMAP.md) and [changelog](CHANGELOG.md).
APKGs/media are release assets, not Git files. This publication imports no new
editions and does not import the complete world catalogue.

## Validation and prototypes

Full v0.3 Anki Desktop GUI playback/import updates, AnkiDroid, AnkiMobile and
physical-card/version listening checks are still pending. Follow the
[manual validation procedure](docs/MANUAL_VALIDATION.md); automated MP3 decoding
and Anki-engine tests are not manual device results.

The [native one-card prototype](prototype/README.md) and
[ten-song playback comparison](prototype/COMPARISON.md) remain unchanged, with
separate identities. Earlier user-reported native/remote prototype successes
do not validate full editions or mobile clients. See the
[reference inspection](docs/REFERENCE_DECKS.md), [playback decision](docs/PLAYBACK_DECISION.md),
[Hitify investigation](docs/HITIFY_CATALOGUE.md) and
[prototype test record](docs/PROTOTYPE_TESTING.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Propose editions, data corrections and
playback issues through GitHub.

Independent fan project; not affiliated with Hitster, Jumbo, Anki or streaming services.
