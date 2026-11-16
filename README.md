# Ultimate Hitster

Community-maintained Anki collections for music recognition and release-year recall, organized around Hitster editions worldwide.

**Status: Original France validation build available. No stable release yet.**

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
mobile clients remain unvalidated. The next experiment is a
[ten-song Original France comparison](prototype/COMPARISON.md): native packaged
previews versus minimal HTML5 remote players, with optional album information
on the answer. See [the Hitify investigation](docs/HITIFY_CATALOGUE.md) for
source structure, recording selection and year limitations.

See [the roadmap](docs/ROADMAP.md) and [data model](docs/DATA_MODEL.md). The initial catalogue target remains a French Original edition sample, followed by Belgian and Dutch editions.

## Downloads

Future builds will be published under [Releases](https://github.com/OpenDecksLibrary/ultimate-hitster/releases).

Current APKGs are validation artifacts, not a published stable release. Online
and offline update the same production deck; prototypes remain separate.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Use issues to propose editions, report data errors or discuss playback compatibility.

Independent fan project; not affiliated with Hitster, Jumbo, Anki or any streaming service.
