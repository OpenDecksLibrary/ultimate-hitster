# Tests

Run `python -m unittest discover -s tests -v` after installing
`prototype/requirements-test.txt`. Tests use disposable Anki collections and
cover APKG contents, media references, question/answer rendering, stable GUIDs,
validation and actual scheduler history across metadata updates.

See [the test record](../docs/PROTOTYPE_TESTING.md) for evidence and pending
client checks. Catalogue integrity, recording deduplication, memberships and
overlapping regional/global imports need tests when they are implemented.
