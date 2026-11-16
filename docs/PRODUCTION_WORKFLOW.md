# Original France production workflow

Use Python 3.12 from this repository checkout:

~~~sh
python -m venv .venv
# Activate the environment for your platform, then:
python -m pip install -e .
python -m pip install -r prototype/requirements-test.txt
~~~

FFmpeg and FFprobe are required for live audio verification, not for generating
the online package from already checked data. No SDK, API account, Anki add-on
or running Anki instance is required. Editable installation keeps templates and
config alongside the code; this is not distributed as a standalone wheel.

## Import all cards and exact references

~~~sh
python -m ultimate_hitster refresh-references --albums
python -m ultimate_hitster import-hitify --html data/sources/original-france.hitify.html
python -m ultimate_hitster check-audio
python -m ultimate_hitster validate
~~~

The importer has no ten-card cap. It validates all expected card numbers,
duplicate rows, table structure and exact reference-map coverage. Without
--html it retrieves the edition URL. --expected-count is explicit; France
defaults to 308. The pure importer also accepts other edition definitions,
but this branch imports no other edition.

Direct Hitify HTTP access returned 403 in this environment. The committed
HTML is explicitly a normalized table snapshot reconstructed from public page
retrieval, not a claimed raw HTTP response. It preserves all 308 source values
and makes the import repeatable. See the source notes under data/sources.

The card-number reference map is pinned, not inferred by song search. Its first
100 IDs exactly match the public Hitify-linked playlist prefix. That embed
exposes only 100 rows. Exact per-track embed pages verify the pinned references
and expose MP3 previews; exact track pages provide albums. Private endpoints
and session/auth tokens are not used or stored.

## Generate online or offline

~~~sh
python -m ultimate_hitster build --mode online --output build/ultimate-hitster-original-france-online.apkg --missing-policy error
python -m ultimate_hitster build --mode offline --output build/ultimate-hitster-original-france-offline.apkg --missing-policy error
~~~

configs/original-france.json selects edition IDs, a stable deck ID and name.
Later selections can contain several editions; shared study IDs produce only
one note. The current canonical dataset contains Original France only.

Online uses direct MP3 URLs and requires internet. Offline packages the same
checked MP3 bytes for playback after import/media sync. The front contains
only the player; the back shows catalogue year, title, artist and optional
album. Generated packages/media stay under ignored build/, outside git.

Production modes share IDs: import a newer alternative to switch player while
retaining the same card/history. Do not delete the deck to switch/update.
Prototype history remains separate; no automatic prototype-history migration
is claimed. Tests record actual Anki scheduler answers before switching modes
and importing metadata corrections.

To switch to an older/equal-timestamp alternative file, select Anki's
"Update existing notes: Always" for that import. Default update-if-newer
correctly retains a newer installed version. Tests confirm that forcing the
older mode updates notes while preserving scheduling and review history.
Use files from the same catalogue revision: Always also applies that file's
artist/title/year/album values.

## Missing and uncertain data

The error policy refuses unverified/unavailable audio. For an explicitly
documented validation build, --missing-policy include keeps the catalogue fact
with a disabled neutral player, tags it audio::missing and lists its reason in
the report. It never silently omits a card or substitutes another song/format.

Seven abbreviated labels have explicit pinned-version reviews in
data/sources/original-france.reviews.json and tags reference::reviewed.
Compare those cards with the physical edition before claiming that validation.
A changed provider ID/title invalidates the review.

## Verify and renew URLs

~~~sh
python -m ultimate_hitster refresh-references --refresh --albums
python -m ultimate_hitster import-hitify --html data/sources/original-france.hitify.html
python -m ultimate_hitster check-audio --refresh
python -m ultimate_hitster build --mode online --output build/ultimate-hitster-original-france-online.apkg --missing-policy error
~~~

Only pinned recording IDs are re-read. A different resolved ID is rejected.
Changed URLs clear prior verification. Audio is downloaded, hashed, inspected
with FFprobe and decoded with FFmpeg. Metadata gaps, expired/unavailable audio,
HTTP errors and unexpected page formats are reported without guessed fallback.

A successful check establishes availability at check time, not permanent URLs.
Normally check-audio reuses verified content-addressed cache entries;
--refresh forces live retrieval. Interrupted runs resume from ignored
per-recording metadata/album/media checkpoints.

## Tests and manual validation

~~~sh
python -m unittest discover -s tests -v
~~~

Tests cover full-table import, exact references, missing data, review
invalidation, duplicates, conflicting years, content dedup, offline corruption,
stable timestamps and actual Anki progress across mode/metadata updates.
CI validates canonical data and builds the complete online package without
live network calls. Synthetic unit packaging fixtures are not live decoder
tests; actual clip verification is reported separately.

Import a production package into a disposable profile, verify 308 cards,
player/answer behavior, albums and the seven reviewed references. Check replay,
reveal during playback, card transitions, offline mode, sync and updates;
record exact client/OS versions. Earlier prototype playback was confirmed by
the user. The complete edition and mobile clients still need manual testing.
See ORIGINAL_FRANCE_VALIDATION.md for measured results and open checks.
