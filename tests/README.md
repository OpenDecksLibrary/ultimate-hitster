# Tests

Run `python -m unittest discover -s tests -v` after installing the editable
project and `prototype/requirements-test.txt`. Tests use disposable Anki collections and
cover APKG contents, media references, question/answer rendering, stable GUIDs,
validation and actual scheduler history across metadata updates.

See [the test record](../docs/PROTOTYPE_TESTING.md) for evidence and pending
client checks. Production tests cover catalogue integrity, exact-reference
deduplication, memberships, year conflicts, missing data and online/offline
updates. Release tests reject stable/mismatched plans and corrupted downloads.

The [release workflow](../docs/RELEASING.md) additionally checks live MP3s and
imports both complete 308-card packages before publishing. Unit tests do not
require live network access or claim manual GUI/mobile validation.
