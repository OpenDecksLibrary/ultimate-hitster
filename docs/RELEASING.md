# Publishing a prerelease

Release packages and MP3s are generated under ignored `dist/` and `build/`.
They are uploaded as GitHub Release assets, never committed to Git.

## Maintainer procedure

1. Validate catalogue/reference changes separately. This release process does
   not import editions, search for replacement tracks or rewrite canonical data.
2. Add English notes at `docs/releases/<tag>.md`, update download links and
   changelog, then change `release.json` to a **new** `vX.Y.Z-beta.N` (or alpha/rc)
   tag with `prerelease: true` and the notes path. Commit these together in a PR.
3. Merge to `main`. The `Publish prerelease` workflow triggers only when
   `release.json` changes on `main`, or when manually dispatched on `main`.
   It refuses stable version strings; stable releases require a separate decision.
4. Check the workflow and release assets. The workflow uses the checked-out
   commit as the tag target, not a later moving branch head.

The workflow installs pinned Python dependencies and FFmpeg, runs the complete
automated suite, fetches/probes/fully decodes all 308 MP3 previews and generates
both full APKGs. Any missing reference/audio blocks publication. It uses the
existing pinned URLs; if they expire, refresh and validate references using the
[production workflow](PRODUCTION_WORKFLOW.md) in a separate reviewed change.

Both complete APKGs are imported into a temporary Anki collection. A real review
is recorded before changing modes; card identities, scheduling and review history
must remain unchanged. The offline collection must have no missing/unused media.

The workflow generates `validation.json` and `SHA256SUMS`, creates a draft
prerelease, uploads all four assets, downloads and compares their checksums,
then publishes the complete prerelease. It finally downloads the public assets
without authentication and compares them with the generated checksum manifest.
Only the publishing job receives `contents: write`; no personal token or custom
secret is needed. Concurrent publications are serialized.

Existing tags/releases are never moved or overwritten. If publication fails,
inspect its state before retrying. A failed upload can leave a draft; complete or
remove that unpublished draft deliberately before rerunning. A failed public
download check can leave an already published release: inspect/download its
assets rather than replacing them. Use a new beta version for changed artifacts.

## Local preparation and verification

From an editable checkout with test dependencies and FFmpeg installed:

~~~sh
python tools/prepare_release.py prepare --live
python tools/prepare_release.py verify --directory dist
~~~

Without `--live`, preparation may reuse checked, hash-verified media caches.
The publication workflow always uses `--live`. Canonical data is loaded into
memory and is not saved or modified by release preparation.

After publication, with matching local `dist/` artifacts:

~~~sh
python tools/verify_release_downloads.py
~~~

Users can verify downloaded assets with `sha256sum -c SHA256SUMS` (download all
three listed files), or compare `Get-FileHash -Algorithm SHA256 <file>` on Windows
with its line in `SHA256SUMS`. These hashes verify byte integrity, not musical
identity or manual client compatibility. See the version's notes for known
reference and playback limitations and progress-preserving import instructions.
