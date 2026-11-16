"""Production packages share identities across online/offline modes."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import subprocess
import time

import genanki

from .catalogue import validate, write_json
from .spotify import check_clip, now
from .registry import select_editions

MODEL_ID = 1735079001
FIELDS = ["StudyID", "RecordingID", "Artist", "Title", "Year", "Album", "Playback"]
ROOT = Path(__file__).resolve().parents[2]


def note_guid(study_id):
    return genanki.guid_for("OpenDecksLibrary:UltimateHitster:production:v1", study_id)


def allocate_timestamp(path):
    """Make consecutive CLI mode changes newer even within the same second."""
    path = Path(path)
    previous = int(path.read_text()) if path.exists() else 0
    timestamp = max(int(time.time()), previous + 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(timestamp), encoding="utf-8")
    return timestamp


def verify_audio(catalogue, directory, workers=3, refresh=False, progress=None):
    directory = Path(directory)
    index_dir = directory / "checks"
    index_dir.mkdir(parents=True, exist_ok=True)
    tracks = [track for track in catalogue["recordings"] if track["audio"].get("url")]

    def verify(track):
        audio = track["audio"]
        index = index_dir / (hashlib.sha256(audio["url"].encode()).hexdigest() + ".json")
        if index.exists() and not refresh:
            old = json.loads(index.read_text(encoding="utf-8"))
            path = directory / f"uh_{old.get('sha256', '')}.mp3"
            if old.get("status") == "verified" and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == old["sha256"]:
                audio.update(old)
                return
        try:
            digest, path = check_clip(audio["url"], directory)
            probe = json.loads(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name", "-of", "json", str(path)],
                timeout=30))
            duration = float(probe["format"]["duration"])
            if not probe["streams"] or any(stream["codec_name"] != "mp3" for stream in probe["streams"]) or not 0 < duration <= 120:
                raise ValueError("Preview is not a supported short MP3 clip")
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                           check=True, capture_output=True, timeout=30)
            evidence = {"status": "verified", "sha256": digest, "duration_seconds": duration,
                        "decoded": True, "checked_at": now()}
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            evidence = {"status": "check_failed", "decoded": False, "checked_at": now(),
                        "reason": f"{type(error).__name__}: {error}"}
        audio.update(evidence)
        write_json(index, evidence)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, _ in enumerate(pool.map(verify, tracks), 1):
            if progress and (index % 25 == 0 or index == len(tracks)):
                progress(index, len(tracks))
    validate(catalogue)
    return catalogue


def selected_notes(catalogue, edition_ids):
    validate(catalogue)
    recordings = {track["recording_id"]: track for track in catalogue["recordings"]}
    known = {edition["edition_id"] for edition in catalogue["editions"]}
    if not edition_ids or set(edition_ids) - known:
        raise ValueError("Choose known edition IDs")
    notes = {}
    for member in catalogue["memberships"]:
        if member["edition_id"] not in edition_ids:
            continue
        track = recordings[member["recording_id"]]
        item = notes.setdefault(member["study_id"], {"track": track, "year": member["catalogue_year"],
                                                    "memberships": [], "verified_reference": False})
        item["memberships"].append(member)
        item["verified_reference"] |= member["reference"]["status"] in ("verified", "reviewed")
    # A shared study keeps the same player in every selection. Verification
    # from another imported membership is valid only for this exact study/ID.
    for member in catalogue["memberships"]:
        if member["study_id"] in notes:
            notes[member["study_id"]]["verified_reference"] |= member["reference"]["status"] in ("verified", "reviewed")
    return notes


def build_package(catalogue, config, mode, output, media_dir, missing_policy="include", timestamp=None):
    if mode not in ("online", "offline") or missing_policy not in ("include", "error"):
        raise ValueError("Unknown build mode or missing-audio policy")
    edition_ids = select_editions(catalogue, config)
    notes = selected_notes(catalogue, edition_ids)
    editions = {e["edition_id"]: e for e in catalogue["editions"]}
    model = genanki.Model(MODEL_ID, "Ultimate Hitster · Production v1",
                          fields=[{"name": name} for name in FIELDS],
                          templates=[{"name": "Recognition", "qfmt": "{{Playback}}",
                                      "afmt": (ROOT / "templates/production/back.html").read_text(encoding="utf-8"),
                                      "bqfmt": "{{Artist}} — {{Title}}", "bafmt": "{{Year}}"}],
                          css=(ROOT / "templates/production/card.css").read_text(encoding="utf-8"))
    deck = genanki.Deck(config["deck_id"], config["deck_name"])
    media, missing, playable = {}, [], 0
    for study_id, item in sorted(notes.items()):
        track = item["track"]
        audio = track["audio"]
        available = item["verified_reference"] and audio["status"] == "verified"
        playable += int(available)
        if available and mode == "online":
            playback = '<audio controls preload="none" aria-label="Play audio" src="' + html.escape(audio["url"], quote=True) + '"></audio>'
        elif available:
            name = f"uh_{audio['sha256']}.mp3"
            path = Path(media_dir) / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != audio["sha256"]:
                raise ValueError(f"Missing or modified offline media for {track['recording_id']}")
            playback = f"[sound:{name}]"
            media[name] = str(path)
        else:
            missing.extend({"edition_id": member["edition_id"], "card_number": member["card_number"],
                            "title": track["title"], "reason": (member["reference"]["status"]
                                if member["reference"]["status"] not in ("verified", "reviewed")
                                else audio.get("reason", audio["status"]))}
                           for member in item["memberships"])
            if missing_policy == "error":
                raise ValueError("Unverified or unavailable audio; use include only for a documented validation build")
            playback = '<audio controls preload="none" aria-label="Audio unavailable"></audio>'
        tag_members = [m for m in catalogue["memberships"] if m["study_id"] == study_id]
        tags = ["edition::" + member["edition_id"] for member in tag_members]
        for member in tag_members:
            edition = editions[member["edition_id"]]
            tags.append("country::" + edition.get("region", "unknown"))
            for language in edition.get("languages", [edition.get("language", "und")]):
                tags.append("language::" + language)
            tags.append("family::" + edition.get("family", "unknown"))
        tags.append("decade::" + str(item["year"] // 10 * 10) + "s")
        tags.extend("card::" + member["edition_id"] + "::" + member["card_number"] for member in tag_members)
        if any(member["reference"]["status"] == "reviewed" for member in item["memberships"]):
            tags.append("reference::reviewed")
        if any(m["reference"]["status"] not in ("verified", "reviewed") for m in tag_members):
            tags.append("reference::uncertain")
        if not available:
            tags.append("audio::missing")
        values = [study_id, track["recording_id"], html.escape(track["artist"]), html.escape(track["title"]),
                  str(item["year"]), html.escape((track.get("album") or {}).get("name", "")), playback]
        deck.add_note(genanki.Note(model=model, fields=values, guid=note_guid(study_id), tags=sorted(set(tags))))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    package = genanki.Package(deck)
    package.media_files = list(media.values())
    package.write_to_file(str(output), timestamp=timestamp)
    return {"mode": mode, "notes": len(notes), "playable": playable,
            "media_files": len(media), "missing_cards": missing, "bytes": output.stat().st_size,
            "output": output.name, "deck_id": config["deck_id"], "model_id": MODEL_ID,
            "edition_ids": edition_ids}
