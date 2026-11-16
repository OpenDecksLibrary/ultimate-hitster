# Publishing a prerelease

APKGs and MP3s are generated under ignored dist/ and build/. They are Actions or
release assets, never committed to Git.

## Candidate preparation (no publication)

release-candidate.json currently describes v0.3.0-beta.1 with publish: false.
It is separate from the active release.json. Prepare and validate it with:

~~~sh
python tools/prepare_release.py prepare --plan release-candidate.json --live
python tools/validate_multi_imports.py
python tools/prepare_release.py verify --plan release-candidate.json --directory dist
~~~

The candidate Actions workflow runs the suite, checks the selected MP3s, builds
the configured online/offline packages, imports each pair into temporary Anki
collections, and tests the actual published v0.2.0-beta.1 package followed by
overlapping complete editions and wider selections. The beta APKG is pinned by
its published SHA-256. Scheduling, review history and personal deck placement are
compared after every import. Reports and SHA256SUMS accompany candidate assets.

Cache reuse still verifies content hashes. --live forces fresh network retrieval
and decoding. Preparation never imports new editions or saves changes to
canonical data. Missing/uncertain references are included only when the plan
explicitly chooses missing_policy: include; every affected card is reported.
Use error for strict publication gates.

Actions artifacts expire (currently seven days); they are validation downloads,
not a release. Record actual manual results using MANUAL_VALIDATION.md before
approving publication. Automated engine success is not a manual playback result.

## Maintainer publication procedure

1. Review/merge the implementation and data PR, inspect measured coverage and
   record manual validation results. Resolve or explicitly document open issues.
2. Review the candidate package configs, missing policy and English notes.
   Each package uses an explicit stem/config; no edition is hardcoded in the
   build or publishing workflow. Avoid multiple assets for identical selections.
3. In a separate approved change, promote the candidate plan to release.json,
   choose a new prerelease tag and set publish: true. Until then publication is
   disabled, even if the workflow is manually dispatched.
4. Merge the approved publication change to main. A release.json push, or a
   manual dispatch on main, invokes the publication gate.
5. The job tests, retrieves and fully decodes selected audio, builds both modes,
   verifies Anki imports, creates a draft prerelease at the checked-out commit,
   uploads all configured APKGs plus validation.json/SHA256SUMS, downloads and
   checks the bytes, then makes the complete prerelease public.
6. Public assets are downloaded without authentication and compared again.

The published v0.2.0-beta.1 plan remains backward compatible; absent publish
authorization now defaults to disabled. The v0.3 candidate is not promoted or
published by this implementation PR. Only the publication job receives contents:
write. No personal token or custom secret is needed.

Tags/releases are never moved or overwritten. Inspect any existing draft or
published release after a failed run before retrying. A public download failure
can leave a published release; do not replace its bytes. Use a new beta tag for
changed assets. Stable version strings are rejected.

For local byte verification, download all files listed in SHA256SUMS and run
sha256sum -c SHA256SUMS, or compare Get-FileHash -Algorithm SHA256 on Windows.
Checksums establish byte integrity, not musical identity or device compatibility.
