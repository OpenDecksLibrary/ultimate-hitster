"""Build one disposable playback card; this is not the catalogue generator."""

import argparse
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import struct
import tempfile
import wave

import genanki

ROOT = Path(__file__).resolve().parents[1]
# Reserved for this experiment only. Do not silently reuse these in production.
MODEL_ID = 1735068211
DECK_ID = 1735068212
FIELDS = ["StudyID", "TrackID", "Artist", "Title", "GameYear", "Audio"]
SAMPLE = Path(__file__).with_name("sample.json")


def validate_fixture(fixture):
    required = {"study_id", "track_id", "artist", "title", "game_year"}
    if not isinstance(fixture, dict) or set(fixture) != required:
        raise ValueError("Fixture must contain exactly: " + ", ".join(sorted(required)))
    for key in ("study_id", "track_id"):
        if not isinstance(fixture[key], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", fixture[key]):
            raise ValueError(f"{key} must be an opaque lowercase ID (letters, digits, hyphens)")
    for key in ("artist", "title"):
        if not isinstance(fixture[key], str) or not fixture[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
        if any(ord(char) < 32 for char in fixture[key]):
            raise ValueError(f"{key} must not contain control characters")
    if type(fixture["game_year"]) is not int or not 1800 <= fixture["game_year"] <= 2100:
        raise ValueError("game_year must be an integer between 1800 and 2100")


def demo_audio():
    """Three original tones, three seconds of mono PCM, no third-party media."""
    rate = 22050
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        frames = bytearray()
        for frequency in (440, 554.365, 659.255):
            for index in range(rate):
                time = index / rate
                envelope = min(1.0, time / 0.02, (1 - time) / 0.08)
                value = int(7000 * envelope * math.sin(2 * math.pi * frequency * time))
                frames.extend(struct.pack("<h", value))
        output.writeframes(frames)
    return buffer.getvalue()


def note_guid(study_id):
    return genanki.guid_for("opendeckslibrary:ultimate-hitster:prototype:v1", study_id)


def make_model():
    return genanki.Model(
        MODEL_ID,
        "Ultimate Hitster · Native Audio Prototype v1",
        fields=[{"name": name} for name in FIELDS],
        templates=[{
            "name": "Recognition",
            "qfmt": (ROOT / "templates/front.html").read_text(encoding="utf-8"),
            "afmt": (ROOT / "templates/back.html").read_text(encoding="utf-8"),
            "bqfmt": "{{Artist}} — {{Title}}",
            "bafmt": "{{GameYear}}",
        }],
        css=(ROOT / "templates/card.css").read_text(encoding="utf-8"),
        sort_field_index=0,
    )


def build(output, fixture=None, audio=None, timestamp=None):
    fixture = json.loads(SAMPLE.read_text(encoding="utf-8")) if fixture is None else fixture
    validate_fixture(fixture)
    if audio is None:
        payload, suffix = demo_audio(), ".wav"
    else:
        audio = Path(audio)
        suffix = audio.suffix.lower()
        if suffix not in {".mp3", ".wav", ".m4a", ".ogg"}:
            raise ValueError("Use an MP3, WAV, M4A or OGG clip; verify playback on each client")
        payload = audio.read_bytes()
        if not payload:
            raise ValueError("Audio clip is empty")
    # Full content digest: deduplicated bytes, no artist/title in the media filename.
    filename = "uh_" + hashlib.sha256(payload).hexdigest() + suffix
    values = [fixture["study_id"], fixture["track_id"], html.escape(fixture["artist"]),
              html.escape(fixture["title"]), str(fixture["game_year"]), f"[sound:{filename}]"]
    note = genanki.Note(model=make_model(), fields=values,
                        guid=note_guid(fixture["study_id"]), tags=["prototype::native-audio"])
    deck = genanki.Deck(DECK_ID, "Ultimate Hitster::Playback Prototype")
    deck.add_note(note)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        media = Path(temporary) / filename
        media.write_bytes(payload)
        package = genanki.Package(deck)
        package.media_files = [str(media)]
        package.write_to_file(str(output), timestamp=timestamp)
    return {"output": str(output), "guid": note.guid, "media": filename}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/playback-prototype.apkg")
    parser.add_argument("--fixture", type=Path, default=SAMPLE)
    parser.add_argument("--audio", type=Path, help="Local clip; no download or trimming is performed")
    args = parser.parse_args()
    try:
        result = build(args.output, json.loads(args.fixture.read_text(encoding="utf-8")), args.audio)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
