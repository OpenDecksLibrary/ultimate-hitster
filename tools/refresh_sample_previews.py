"""Refresh URLs for manually selected Apple recording IDs, never search/rematch."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from build_comparison import SAMPLE, validate_preview_url, validate_sample


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=SAMPLE)
    parser.add_argument("--output", type=Path, default=ROOT / "build/refreshed-sample.json")
    args = parser.parse_args()
    try:
        updated = refresh(json.loads(args.sample.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")
