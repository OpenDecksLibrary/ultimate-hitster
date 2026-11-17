# Roadmap

## 0.1 — Proof of concept

- [ ] Confirm the target edition and a small verified track sample.
- [x] Inspect supplied NL and Quiz Bowl APKG templates and media maps.
- [x] Build a one-card native audio APKG with original synthetic test audio.
- [x] Test imports, answer visibility and review-preserving corrections in Anki's engine.
- [x] Record the positive user-reported native Anki import/playback test.
- [x] Inspect the Original France catalogue and select a ten-card playback sample.
- [x] Build separate native and HTML5 remote comparison APKGs with optional albums.
- [ ] Test native local audio and an online playback prototype on Anki Desktop.
- [ ] Test AnkiDroid and AnkiMobile compatibility.
- [ ] Define stable model, deck and note identifiers.
- [ ] Generate and import a test package; verify a second import preserves review history.

The automated engine update test passes; GUI and device update checks remain
open. See [the test record](PROTOTYPE_TESTING.md). Prototype IDs are separate
from the stable production identities defined in schema v1.

## 0.2 — First edition

- [x] Import all 308 Original France catalogue rows and exact source references.
- [x] Verify MP3 previews and retrieve albums; document explicit label reviews.
- [x] Define schema-v1 production IDs and deduplicate exact recordings/study facts.
- [x] Build full online/offline validation packages; test real mode-switch imports.
- [ ] Manually validate the complete edition and reviewed version labels.
- [x] Collect the French Original catalogue; retain its years and document their verification limits.
- [x] Implement repeatable validation and package generation.
- [x] Automate beta publication with tests, full Anki imports, checksums and download checks.
- [ ] Complete manual edition/client validation before a stable release.

## 0.3 — Multi-edition support

- [x] Discover and classify all Hitify-listed editions without importing the world.
- [x] Generalize import and selection configuration; retain schema v1 and published IDs.
- [x] Add complete Original Refresh France and Guilty Pleasures France source imports.
- [x] Deduplicate exact recording/year studies; preserve distinct versions and year conflicts.
- [x] Build individual, country, family, custom and imported-global selections.
- [x] Add hierarchical tags and document one-card/one-deck behavior.
- [x] Test overlapping imports, scheduling/history, user decks, modes and beta compatibility.
- [x] Prepare candidate artifacts and a disabled v0.3.0-beta.1 publication plan.
- [ ] Complete Desktop, AnkiDroid and AnkiMobile manual checks with recorded results.
- [ ] Review and merge the v0.3 PR, then explicitly authorize candidate publication.
- [ ] Add further countries/editions in separately reviewed imports.

See [multi-edition rules](MULTI_EDITION.md), [statistics](../data/reports/catalogue.json)
and [manual validation](MANUAL_VALIDATION.md). Radio Contact Belgium remains
available in the registry; its complete per-card reference source was not
available in the complementary source used for this import.

## 1.0 — Stable community release

- [ ] Automate builds and validation in CI.
- [ ] Document compatibility, data provenance and upgrade procedures.
- [ ] Open community data corrections and edition contributions.

Milestones are targets, not release commitments.
