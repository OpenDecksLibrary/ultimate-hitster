"""Build only the ten-card France playback experiment, without changing v1."""

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

import genanki

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = Path(__file__).with_name("france-original.sample.json")
FIELDS = ["SampleID", "Artist", "Title", "Year", "Album", "Playback"]
IDS = {"native": (1735068221, 1735068231), "remote": (1735068222, 1735068232)}
MAX_CLIP_BYTES = 10 * 1024 * 1024


def validate_preview_url(value):
    if not isinstance(value, str):
        raise ValueError("preview_url must be a string")
    url = urlsplit(value)
    if (url.scheme != "https" or url.hostname != "audio-ssl.itunes.apple.com"
            or url.username or url.password or url.port not in (None, 443)
            or url.query or url.fragment or not url.path.endswith(".m4a")):
        raise ValueError("Expected an unsigned HTTPS Apple audio preview URL")


def validate_remote_url(value):
    if not isinstance(value, str):
        raise ValueError("remote_preview_url must be a string")
    url = urlsplit(value)
    if (url.scheme != "https" or url.hostname != "p.scdn.co" or url.username
            or url.password or url.port not in (None, 443) or url.query or url.fragment
            or not re.fullmatch(r"/mp3-preview/[0-9a-f]{40}", url.path)):
        raise ValueError("Expected an unsigned HTTPS Spotify MP3 preview URL")


def validate_sample(sample):
    tracks = sample.get("tracks", [])
    if len(tracks) != 10:
        raise ValueError("This experiment requires exactly ten tracks")
    identities, cards, providers = set(), set(), set()
    for track in tracks:
        identity = track["sample_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z0-9-]{1,80}", identity):
            raise ValueError("Invalid immutable sample_id")
        if identity in identities or track["card_number"] in cards or track["apple_track_id"] in providers:
            raise ValueError("Duplicate sample ID, card number or provider recording")
        identities.add(identity)
        cards.add(track["card_number"])
        providers.add(track["apple_track_id"])
        if type(track["apple_track_id"]) is not int or track["apple_track_id"] <= 0:
            raise ValueError("apple_track_id must be a positive integer")
        if type(track["year"]) is not int or not 1800 <= track["year"] <= 2100:
            raise ValueError("year must be an integer between 1800 and 2100")
        for key in ("artist", "title", "album"):
            value = track.get(key, "")
            if (not isinstance(value, str) or (key != "album" and not value.strip())
                    or any(ord(char) < 32 for char in value)):
                raise ValueError(f"Invalid {key}")
        validate_preview_url(track["preview_url"])
        if "remote_preview_url" in track:
            validate_remote_url(track["remote_preview_url"])
        digest = track.get("preview_sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid preview_sha256")


def guid(mode, sample_id):
    return genanki.guid_for("opendeckslibrary:ultimate-hitster:comparison:v1", mode, sample_id)


def download_clips(sample, directory):
    """Fetch pinned previews once; build and unit tests can also run offline."""
    validate_sample(sample)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    clips = {}
    for track in sample["tracks"]:
        path = directory / f'apple-{track["apple_track_id"]}.m4a'
        with urlopen(track["preview_url"], timeout=30) as response:
            validate_preview_url(response.url)
            data = response.read(MAX_CLIP_BYTES + 1)
        if not data or len(data) > MAX_CLIP_BYTES:
            raise ValueError("Empty or oversized preview")
        expected = track.get("preview_sha256")
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'Preview bytes changed for {track["sample_id"]}; inspect before rebuilding')
        path.write_bytes(data)
        clips[track["sample_id"]] = path
    return clips


def build(sample, mode, output, clips=None, timestamp=None):
    validate_sample(sample)
    if mode not in IDS:
        raise ValueError("Choose native or remote")
    model_id, deck_id = IDS[mode]
    templates = ROOT / "templates/comparison"
    model = genanki.Model(
        model_id, f"Ultimate Hitster · France comparison · {mode} v1",
        fields=[{"name": name} for name in FIELDS],
        templates=[{"name": "Recognition", "qfmt": "{{Playback}}",
                    "afmt": (templates / "back.html").read_text(encoding="utf-8"),
                    "bqfmt": "{{Artist}} — {{Title}}", "bafmt": "{{Year}}"}],
        css=(templates / "card.css").read_text(encoding="utf-8"),
    )
    deck = genanki.Deck(deck_id, f"Ultimate Hitster::France Original Sample::{mode.title()}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        media = {}
        for track in sample["tracks"]:
            if mode == "remote":
                validate_remote_url(track["remote_preview_url"])
                playback = '<audio controls preload="none" aria-label="Play audio" src="' + html.escape(track["remote_preview_url"], quote=True) + '"></audio>'
            else:
                path = Path((clips or {})[track["sample_id"]])
                data = path.read_bytes()
                if not data or path.suffix.lower() not in {".m4a", ".mp3", ".wav"}:
                    raise ValueError("Native mode needs a non-empty local audio clip")
                digest = hashlib.sha256(data).hexdigest()
                if track.get("preview_sha256") and digest != track["preview_sha256"]:
                    raise ValueError("Local audio does not match the pinned preview bytes")
                name = f"uh_{digest}{path.suffix.lower()}"
                destination = Path(temporary) / name
                if name not in media:
                    destination.write_bytes(data)
                    media[name] = str(destination)
                playback = f"[sound:{name}]"
            values = [track["sample_id"], html.escape(track["artist"]), html.escape(track["title"]),
                      str(track["year"]), html.escape(track.get("album", "").strip()), playback]
            deck.add_note(genanki.Note(model=model, fields=values, guid=guid(mode, track["sample_id"]),
                                      tags=["prototype::france-original", f"playback::{mode}"]))
        package = genanki.Package(deck)
        package.media_files = list(media.values())
        package.write_to_file(str(output), timestamp=timestamp)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=SAMPLE)
    parser.add_argument("--mode", choices=["remote", "native", "both"], default="remote")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--download", action="store_true", help="Download the ten pinned clips for native mode")
    parser.add_argument("--media-dir", type=Path, default=ROOT / "build/previews")
    args = parser.parse_args()
    try:
        sample = json.loads(args.sample.read_text(encoding="utf-8"))
        validate_sample(sample)
        modes = ["remote", "native"] if args.mode == "both" else [args.mode]
        clips = None
        if "native" in modes:
            clips = download_clips(sample, args.media_dir) if args.download else {
                track["sample_id"]: args.media_dir / f'apple-{track["apple_track_id"]}.m4a'
                for track in sample["tracks"]}
        for mode in modes:
            print(build(sample, mode, args.output_dir / f"france-original-10-{mode}.apkg", clips))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
