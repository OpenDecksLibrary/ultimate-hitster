"""Schema v1: recordings, editions, memberships and immutable study identities."""

import copy
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from uuid import UUID, uuid5

from .spotify import valid_id, valid_preview, now

NAMESPACE = UUID("a352d6e0-24ad-41c1-bb02-a31a5ed2b72c")
SOURCE_URL = "https://hitify.app/en/hitster-editions/original-france"
REFERENCE_URL = "https://github.com/oleuml/musicminds-hitster-playlists/blob/main/hitster-aaaa0004-fr.csv"


def stable_id(kind, anchor):
    return kind + "_" + uuid5(NAMESPACE, kind + ":" + anchor).hex


def normalized(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text).casefold()
                   if char.isalnum() and not unicodedata.combining(char))


def artists_match(display, artists):
    remaining = normalized(display)
    for artist in sorted((normalized(name) for name in artists), key=len, reverse=True):
        if not artist or artist not in remaining:
            return False
        remaining = remaining.replace(artist, "", 1)
    return bool(artists) and not remaining


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, text):
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_hitify(source, expected_count=None):
    """Parse the actual table, with no ten-card cap and no title rematching."""
    parser = TableParser()
    parser.feed(source)
    tables = [table for table in parser.tables if table and
              [normalized(value) for value in table[0]] == ["no", "artist", "title", "year"]]
    if len(tables) != 1:
        raise ValueError("Expected exactly one Hitify No./Artist/Title/Year table")
    rows, seen = [], set()
    for cells in tables[0][1:]:
        if len(cells) != 4 or not cells[0].isdigit() or not cells[3].isdigit():
            raise ValueError("Malformed catalogue row")
        number, artist, title, year = cells
        if number in seen or not artist or not title or not 1800 <= int(year) <= 2100:
            raise ValueError("Duplicate card number, missing metadata or invalid year")
        seen.add(number)
        rows.append({"card_number": number, "artist": artist, "title": title, "year": int(year)})
    if expected_count is not None and (len(rows) != expected_count or
            seen != {str(number) for number in range(1, expected_count + 1)}):
        raise ValueError(f"Expected all {expected_count} catalogue cards, without gaps")
    return rows


def read_references(path):
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8", newline="")))
    result = {}
    for row in rows:
        number, spotify_id = row["card_nr"], row["spotify_track_id"]
        if number in result or not valid_id(spotify_id):
            raise ValueError("Duplicate card number or missing/invalid exact Spotify reference")
        result[number] = row
    return result


def load(root):
    root = Path(root)
    def records(name, key):
        path = root / name
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if data == []:  # Empty pre-production scaffold only.
            return []
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported catalogue schema")
        return data[key]
    memberships = []
    for path in sorted((root / "editions").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported membership schema")
        memberships.extend(data["memberships"])
    return {"recordings": records("tracks.json", "recordings"),
            "editions": records("editions.json", "editions"), "memberships": memberships}


def save(root, catalogue):
    validate(catalogue)
    root = Path(root)
    write_json(root / "tracks.json", {"schema_version": 1, "recordings": catalogue["recordings"]})
    write_json(root / "editions.json", {"schema_version": 1, "editions": catalogue["editions"]})
    for edition in catalogue["editions"]:
        write_json(root / "editions" / (edition["edition_id"] + ".json"),
                   {"schema_version": 1, "edition_id": edition["edition_id"],
                    "memberships": [member for member in catalogue["memberships"]
                                    if member["edition_id"] == edition["edition_id"]]})


def import_edition(catalogue, rows, references, edition, metadata, albums=None, reviews=None):
    result = copy.deepcopy(catalogue)
    edition_id = edition["edition_id"]
    if set(references) - {row["card_number"] for row in rows}:
        raise ValueError("The reference map contains unknown catalogue card numbers")
    recordings = {track["recording_id"]: track for track in result["recordings"]}
    by_provider = {provider: track for track in recordings.values()
                   for provider in track["providers"]["spotify"]}
    old_members = {(member["edition_id"], member["card_number"]): member for member in result["memberships"]}
    origins = {}
    edition_order = {e["edition_id"]: i for i, e in enumerate(result["editions"])}
    for member in sorted(result["memberships"], key=lambda m: edition_order[m["edition_id"]]):
        origins.setdefault(member["recording_id"], member["edition_id"])
    studies = {(member["recording_id"], member["catalogue_year"]): member["study_id"] for member in result["memberships"]}
    added_members = []
    for row in rows:
        reference = references.get(row["card_number"], {})
        provider = reference.get("spotify_track_id") or None
        if provider is not None and not valid_id(provider):
            raise ValueError("Invalid pinned Spotify reference")
        member_anchor = stable_id("member", edition_id + ":" + row["card_number"])
        unresolved_id = stable_id("rec", "unresolved:" + member_anchor)
        track = by_provider.get(provider) if provider else recordings.get(unresolved_id)
        if track is None:
            track = {"recording_id": stable_id("rec", "spotify:" + provider) if provider else unresolved_id,
                     "artist": row["artist"], "title": row["title"], "album": None,
                     "providers": {"spotify": [provider] if provider else []},
                     "catalogue_origin": edition_id}
            recordings[track["recording_id"]] = track
            if provider:
                by_provider[provider] = track
        existing = old_members.get((edition_id, row["card_number"]))
        if existing and existing["recording_id"] != track["recording_id"]:
            raise ValueError("A card's recording reference changed; an explicit identity review is required")
        evidence = metadata.get(provider, {"spotify_id": provider, "status": "fetch_failed", "error": "Metadata not fetched"})
        matches = {"title": normalized(row["title"]) == normalized(evidence.get("title", "")),
                   "artist": artists_match(row["artist"], evidence.get("artists", []))}
        verified = all(matches.values()) and evidence.get("spotify_id") == provider
        status = ("unresolved" if provider is None else
                  "verified" if verified else
                  "fetch_failed" if evidence.get("status") == "fetch_failed" else "metadata_mismatch")
        review = (reviews or {}).get(row["card_number"])
        if review:
            if (review["spotify_id"] != provider or review["catalogue_title"] != row["title"]
                    or review["provider_title"] != evidence.get("title") or not matches["artist"]):
                raise ValueError("A recording review no longer matches the exact reference/title/artist")
            verified, status = True, "reviewed"
        if verified or "provider_metadata" not in track:
            track["provider_metadata"] = {key: value for key, value in evidence.items() if key != "preview_url"}
        album = (albums or {}).get(provider, {}).get("album")
        if album:
            track["album"] = album
        old_audio = track.get("audio", {})
        url = evidence.get("preview_url")
        if verified and url:
            track["audio"] = old_audio if old_audio.get("url") == url else {
                "format": "mp3", "provider": "spotify", "url": url, "status": "unchecked"}
        elif not old_audio.get("url") or not old_audio.get("status") == "verified":
            track["audio"] = {"format": "mp3", "provider": "spotify", "url": None,
                              "status": "unavailable", "reason": status if not verified else "provider_no_preview"}
        member_id = stable_id("member", edition_id + ":" + row["card_number"])
        study_id = existing["study_id"] if existing else studies.get((track["recording_id"], row["year"]))
        study_id = study_id or stable_id("study", member_id)
        studies[(track["recording_id"], row["year"])] = study_id
        added_members.append({"membership_id": member_id, "edition_id": edition_id,
                              "card_number": row["card_number"], "recording_id": track["recording_id"],
                              "study_id": study_id, "catalogue_year": row["year"],
                              "catalogue_artist": row["artist"], "catalogue_title": row["title"],
                              "reference": {"spotify_id": provider, "qr_url": reference.get("qr_code_value"),
                                            "status": status, "checks": matches,
                                            **({"source_url": reference["source_url"]} if reference.get("source_url") else {}),
                                            **({"review": review["reason"]} if review else {})}})
    # A corrected spelling in the same edition must not depend on provider text.
    for row, member in zip(rows, added_members):
        track = recordings[member["recording_id"]]
        origin = track.get("catalogue_origin", origins.get(track["recording_id"], edition_id))
        track["catalogue_origin"] = origin
        if (edition_id, row["card_number"]) in old_members and origin == edition_id:
            recordings[member["recording_id"]]["artist"] = row["artist"]
            recordings[member["recording_id"]]["title"] = row["title"]
    result["recordings"] = sorted(recordings.values(), key=lambda track: track["recording_id"])
    result["editions"] = [old for old in result["editions"] if old["edition_id"] != edition_id] + [edition]
    result["memberships"] = [member for member in result["memberships"] if member["edition_id"] != edition_id] + added_members
    validate(result)
    return result


def validate(catalogue):
    editions = {edition["edition_id"]: edition for edition in catalogue["editions"]}
    recordings = {track["recording_id"]: track for track in catalogue["recordings"]}
    if len(editions) != len(catalogue["editions"]) or len(recordings) != len(catalogue["recordings"]):
        raise ValueError("Duplicate edition or recording identity")
    providers, studies, cards, member_ids = {}, {}, set(), set()
    for edition_id in editions:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", edition_id):
            raise ValueError("Invalid immutable edition ID")
    for track in recordings.values():
        if not re.fullmatch(r"rec_[0-9a-f]{32}", track["recording_id"]):
            raise ValueError("Invalid recording ID")
        if not track["artist"].strip() or not track["title"].strip():
            raise ValueError("Recording artist/title is missing")
        for value in (track["artist"], track["title"], (track.get("album") or {}).get("name", "")):
            if any(ord(char) < 32 for char in value):
                raise ValueError("Metadata contains control characters")
        for provider in track["providers"]["spotify"]:
            if not valid_id(provider) or (provider in providers and providers[provider] != track["recording_id"]):
                raise ValueError("Duplicate provider recording or invalid provider ID")
            providers[provider] = track["recording_id"]
        audio = track["audio"]
        if audio.get("url") and not valid_preview(audio["url"]):
            raise ValueError("Invalid production MP3 URL")
        if audio["status"] == "verified" and (not audio.get("url") or not audio.get("decoded")
                or not re.fullmatch(r"[0-9a-f]{64}", audio.get("sha256", ""))
                or not 0 < audio.get("duration_seconds", 0) <= 120):
            raise ValueError("Incomplete verified audio evidence")
    for member in catalogue["memberships"]:
        if (not re.fullmatch(r"member_[0-9a-f]{32}", member["membership_id"])
                or not re.fullmatch(r"study_[0-9a-f]{32}", member["study_id"])):
            raise ValueError("Invalid membership or study ID")
        key = member["edition_id"], member["card_number"]
        if key in cards or member["membership_id"] in member_ids:
            raise ValueError("Duplicate edition card or membership ID")
        cards.add(key)
        member_ids.add(member["membership_id"])
        if member["edition_id"] not in editions or member["recording_id"] not in recordings:
            raise ValueError("Dangling membership reference")
        if type(member["catalogue_year"]) is not int or not 1800 <= member["catalogue_year"] <= 2100:
            raise ValueError("Invalid catalogue year")
        if (member["reference"]["spotify_id"] is None and member["reference"]["status"] != "unresolved") or (
                member["reference"]["spotify_id"] is not None and
                member["reference"]["spotify_id"] not in recordings[member["recording_id"]]["providers"]["spotify"]):
            raise ValueError("Membership recording/provider disagreement")
        fact = member["recording_id"], member["catalogue_year"]
        if member["study_id"] in studies and studies[member["study_id"]] != fact:
            raise ValueError("One study ID refers to conflicting recordings/years; allocate a reviewed variant")
        studies[member["study_id"]] = fact
    for edition_id, edition in editions.items():
        count = sum(member["edition_id"] == edition_id for member in catalogue["memberships"])
        if count != edition["card_count"]:
            raise ValueError(f"Incomplete edition {edition_id}: {count}/{edition['card_count']}")


def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
