# Ultimate Hitster

Community-maintained Anki collections for music recognition and release-year recall, organized around Hitster editions worldwide.

**Status: [v0.2.0-beta.1 prerelease](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/tag/v0.2.0-beta.1). Original France: 308 cards. No stable release yet.**

## Goals

- Support individual editions, country collections and a deduplicated global collection.
- Learn artist, title and game-card year from a musical cue.
- Preserve stable note identities across updates.
- Keep edition-specific years and track versions distinct where necessary.
- Generate downloadable `.apkg` packages from validated, versioned source data.

## Getting started

The full [Original France edition](docs/ORIGINAL_FRANCE_VALIDATION.md) contains
308 cards with checked MP3 previews and albums. The
[production workflow](docs/PRODUCTION_WORKFLOW.md) imports the complete catalogue
and builds online/offline alternatives with shared, stable production identities.
See [schema v1](docs/DATA_MODEL.md) and the seven explicit version-label reviews
before validating the full deck. Other editions have not been imported.

Start with the [one-card native audio prototype](prototype/README.md). It generates an importable APKG with a three-second synthetic clip and tests stable updates through Anki's engine. This is a playback experiment, not a populated Hitster edition.

The [reference deck inspection](docs/REFERENCE_DECKS.md), [provisional playback decision](docs/PLAYBACK_DECISION.md) and [test record](docs/PROTOTYPE_TESTING.md) distinguish verified behavior from pending Desktop and mobile playback checks.

The original native prototype has a positive user-reported Anki playback test;
mobile clients remain unvalidated. The earlier comparison is a
[ten-song Original France comparison](prototype/COMPARISON.md): native packaged
previews versus minimal HTML5 remote players, with optional album information
on the answer. See [the Hitify investigation](docs/HITIFY_CATALOGUE.md) for
source structure, recording selection and year limitations.

See [the roadmap](docs/ROADMAP.md) and [data model](docs/DATA_MODEL.md). Only Original France has been imported; future editions require separate validation.

## Downloads

The first beta is available under [v0.2.0-beta.1](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/tag/v0.2.0-beta.1).

| Package | Download | Playback |
| --- | --- | --- |
| Online (about 234 KB) | [Online APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.2.0-beta.1/ultimate-hitster-original-france-online.apkg) | Internet required |
| Offline (about 105 MB) | [Offline APKG](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.2.0-beta.1/ultimate-hitster-original-france-offline.apkg) | Included MP3 previews |

Verify downloads with [SHA256SUMS](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.2.0-beta.1/SHA256SUMS).
Read the [release notes](docs/releases/v0.2.0-beta.1.md) for known limitations and
[validation.json](https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/v0.2.0-beta.1/validation.json)
for build results. Full-edition manual playback and mobile validation remain open.

**Online and offline update the same production cards.** Import into your existing
collection without deleting its deck/notes. For an older/equal-timestamp mode file,
choose **Update existing notes: Always** and use files from the same release.
Production identities match the full-edition PR #3 packages; prototype progress
remains separate. See the [update instructions](docs/releases/v0.2.0-beta.1.md#update-without-losing-progress).

Maintainers: [automated prerelease workflow](docs/RELEASING.md). APKGs and media
are release assets and are not stored in Git.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Use issues to propose editions, report data errors or discuss playback compatibility.

Independent fan project; not affiliated with Hitster, Jumbo, Anki or any streaming service.
