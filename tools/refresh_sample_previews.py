"""Refresh pinned recording URLs without searching or rematching recordings."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
import re
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from build_comparison import SAMPLE, validate_preview_url, validate_remote_url, validate_sample


def refresh(sample):
    validate_sample(sample)
    query = urlencode({"id": ",".join(str(t["apple_track_id"]) for t in sample["tracks"]),
                       "entity": "song", "country": "FR"})
    with urlopen("https://itunes.apple.com/lookup?" + query, timeout=30) as response:
        results = json.load(response)["results"]
    by_id = {track["trackId"]: track for track in results if track.get("kind") == "song"}
    result = json.loads(json.dumps(sample))
    for track in result["tracks"]:
        provider = by_id[track["apple_track_id"]]
        if (provider["artistName"] != track["provider_artist"]
                or provider["trackName"] != track["provider_title"]):
            raise ValueError("Provider identity changed; inspect the recording manually")
        validate_preview_url(provider["previewUrl"])
        if provider["previewUrl"] != track["preview_url"]:
            # New bytes must be checked before restoring their integrity pin.
            track.pop("preview_sha256", None)
            track.pop("preview_duration_seconds", None)
        track["preview_url"] = provider["previewUrl"]
        track["preview_checked_on"] = date.today().isoformat()
    return result


def refresh_remote(sample):
    """Read public playlist embed metadata; never store its session/auth fields."""
    validate_sample(sample)
    playlist = sample["edition"]["spotify_playlist_url"].rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9]{22}", playlist):
        raise ValueError("Invalid pinned playlist ID")
    with urlopen(f"https://open.spotify.com/embed/playlist/{playlist}", timeout=30) as response:
        page = response.read(2_000_001).decode("utf-8")
    if len(page) > 2_000_000:
        raise ValueError("Public embed response exceeded the size limit")
    match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Public embed structure changed; inspect it manually")
    rows = json.loads(match.group(1))["props"]["pageProps"]["state"]["data"]["entity"]["trackList"]
    by_id = {row["uri"].rsplit(":", 1)[-1]: row for row in rows}
    result = json.loads(json.dumps(sample))
    for track in result["tracks"]:
        row = by_id[track["spotify_track_id"]]
        if row["title"] != track["title"] or row["subtitle"] != track["artist"]:
            raise ValueError("Pinned playlist recording changed; inspect it manually")
        preview = row["audioPreview"]
        if preview["format"] != "MP3_96":
            raise ValueError("Expected an MP3 preview, not an AAC replacement")
        validate_remote_url(preview["url"])
        if preview["url"] != track.get("remote_preview_url"):
            track.pop("remote_preview_sha256", None)
            track.pop("remote_preview_duration_seconds", None)
        track["remote_preview_url"] = preview["url"]
        track["remote_preview_checked_on"] = date.today().isoformat()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=SAMPLE)
    parser.add_argument("--output", type=Path, default=ROOT / "build/refreshed-sample.json")
    parser.add_argument("--mode", choices=["native", "remote", "both"], default="both")
    args = parser.parse_args()
    try:
        updated = json.loads(args.sample.read_text(encoding="utf-8"))
        if args.mode in ("native", "both"):
            updated = refresh(updated)
        if args.mode in ("remote", "both"):
            updated = refresh_remote(updated)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")
