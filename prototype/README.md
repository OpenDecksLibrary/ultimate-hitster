# Native audio card prototype

An importable **one-card technical experiment**, with an original three-second
tone fixture. It is not a French edition, a catalogue import or a release.

Run from the repository root with Python 3.12:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r prototype/requirements.txt
python prototype/build.py
```

Import `build/playback-prototype.apkg` into a disposable Anki profile. The
question shows only a native audio replay control, with no headings or instructions. The
answer shows artist, title and year. No add-on or account is required by the
template. Audio playback in each client is still subject to manual validation.

For an existing local clip, create `local/clip.json` using the same keys as
`prototype/sample.json`, with the matching artist, title and game-card year:

```sh
python prototype/build.py --fixture local/clip.json --audio local/clip.mp3 --output build/local-clip.apkg
```

Keep `study_id` and `track_id` unchanged when correcting metadata. Pass an
already prepared excerpt: the builder copies the whole input without trimming
or transcoding. It accepts MP3, WAV, M4A and OGG filenames, but does not validate
their codecs; confirm successful decoding and client playback separately.
The default generated WAV needs no FFmpeg or external media.

Run the actual Anki import/update regression tests:

```sh
python -m pip install -r prototype/requirements-test.txt
python -m unittest discover -s tests -v
```

The build dependency is genanki; Anki is needed only for regression tests.
The tests use temporary collections, not a running Anki instance or AnkiConnect.
No catalogue data, regional packages or releases are generated.

See [reference findings](../docs/REFERENCE_DECKS.md),
[playback rationale](../docs/PLAYBACK_DECISION.md) and
[tested versus pending checks](../docs/PROTOTYPE_TESTING.md).
