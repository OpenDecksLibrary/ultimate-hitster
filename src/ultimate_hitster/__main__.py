"""Explicit import, reference refresh, media verification and package commands."""

import argparse
import hashlib
from collections import Counter
import json
from pathlib import Path
import sys

from .catalogue import SOURCE_URL, REFERENCE_URL, load, save, parse_hitify, read_references, import_edition, source_digest, write_json, validate
from .spotify import fetch, resolve_recordings, resolve_albums, now
from .build import verify_audio, build_package, allocate_timestamp

ROOT = Path(__file__).resolve().parents[2]


def cache(directory):
    return {item["spotify_id"]: item for path in Path(directory).glob("*.json")
            for item in [json.loads(path.read_text(encoding="utf-8"))]}


def report(catalogue):
    tracks = {track["recording_id"]: track for track in catalogue["recordings"]}
    issues, reviewed, dates = [], [], []
    for member in catalogue["memberships"]:
        track = tracks[member["recording_id"]]
        if member["reference"]["status"] == "reviewed":
            reviewed.append({"card_number": member["card_number"], "catalogue_title": track["title"],
                             "provider_title": track["provider_metadata"]["title"],
                             "reason": member["reference"]["review"]})
        release_date = track.get("provider_metadata", {}).get("release_date")
        if release_date and release_date[:4].isdigit() and int(release_date[:4]) != member["catalogue_year"]:
            dates.append({"card_number": member["card_number"], "catalogue_year": member["catalogue_year"],
                          "provider_release_date": release_date})
        if member["reference"]["status"] not in ("verified", "reviewed") or track["audio"]["status"] != "verified":
            issues.append({"card_number": member["card_number"], "artist": track["artist"], "title": track["title"],
                           "reference_status": member["reference"]["status"], "audio": track["audio"],
                           "provider_title": track.get("provider_metadata", {}).get("title"),
                           "provider_artists": track.get("provider_metadata", {}).get("artists")})
    return {"checked_at": now(), "cards": len(catalogue["memberships"]), "recordings": len(tracks),
            "studies": len({member["study_id"] for member in catalogue["memberships"]}),
            "reference_status": dict(Counter(member["reference"]["status"] for member in catalogue["memberships"])),
            "audio_status": dict(Counter(track["audio"]["status"] for track in tracks.values())),
            "albums": sum(bool(track.get("album")) for track in tracks.values()), "issues": issues,
            "explicit_label_reviews": reviewed, "provider_date_differences": dates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    commands = parser.add_subparsers(dest="command", required=True)
    importing = commands.add_parser("import-hitify")
    importing.add_argument("--html", type=Path, help="Saved/normalized source table; omit to fetch the edition URL")
    importing.add_argument("--references", type=Path, default=ROOT / "data/sources/original-france.references.csv")
    importing.add_argument("--expected-count", type=int, default=308)
    importing.add_argument("--provider-cache", type=Path, default=ROOT / "build/provider-cache")
    importing.add_argument("--album-cache", type=Path, default=ROOT / "build/album-cache")
    importing.add_argument("--reviews", type=Path, default=ROOT / "data/sources/original-france.reviews.json")
    resolving = commands.add_parser("refresh-references")
    resolving.add_argument("--references", type=Path, default=ROOT / "data/sources/original-france.references.csv")
    resolving.add_argument("--provider-cache", type=Path, default=ROOT / "build/provider-cache")
    resolving.add_argument("--album-cache", type=Path, default=ROOT / "build/album-cache")
    resolving.add_argument("--refresh", action="store_true")
    resolving.add_argument("--albums", action="store_true")
    resolving.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    checking = commands.add_parser("check-audio")
    checking.add_argument("--media-dir", type=Path, default=ROOT / "build/media")
    checking.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    checking.add_argument("--refresh", action="store_true")
    building = commands.add_parser("build")
    building.add_argument("--config", type=Path, default=ROOT / "configs/original-france.json")
    building.add_argument("--mode", choices=["online", "offline"], required=True)
    building.add_argument("--media-dir", type=Path, default=ROOT / "build/media")
    building.add_argument("--missing-policy", choices=["include", "error"], default="include")
    building.add_argument("--output", type=Path, required=True)
    commands.add_parser("validate")
    commands.add_parser("report")
    args = parser.parse_args()
    try:
        catalogue = load(args.data)
        if args.command == "import-hitify":
            source = args.html.read_text(encoding="utf-8") if args.html else fetch(SOURCE_URL).decode("utf-8")
            rows = parse_hitify(source, args.expected_count)
            edition = {"edition_id": "hitster-original-france", "name": "Hitster Original France", "region": "FR",
                       "language": "fr", "card_count": args.expected_count, "year_kind": "catalogue_release_year",
                       "printed_years_verified": False, "anki_deck_id": 1735079101,
                       "sources": [{"url": SOURCE_URL, "retrieved_on": now()[:10],
                                    "snapshot": args.html.name if args.html else None,
                                    "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()},
                                   {"url": REFERENCE_URL, "sha256": source_digest(args.references)}]}
            catalogue = import_edition(catalogue, rows, read_references(args.references), edition,
                                       cache(args.provider_cache), cache(args.album_cache),
                                       json.loads(args.reviews.read_text(encoding="utf-8")) if args.reviews.exists() else {})
            save(args.data, catalogue)
        elif args.command == "refresh-references":
            ids = [row["spotify_track_id"] for row in read_references(args.references).values()]
            progress = lambda a, b: print(f"References {a}/{b}", file=sys.stderr, flush=True)
            resolve_recordings(ids, args.provider_cache, args.refresh, args.workers, progress)
            if args.albums:
                resolve_albums(ids, args.album_cache, min(args.workers, 2), progress, refresh=args.refresh)
            print("References cached. Re-run import-hitify to apply exact-ID metadata; no automatic substitutions.")
            return
        elif args.command == "check-audio":
            verify_audio(catalogue, args.media_dir, args.workers, args.refresh,
                         lambda a, b: print(f"Audio {a}/{b}", file=sys.stderr, flush=True))
            save(args.data, catalogue)
        elif args.command == "build":
            config = json.loads(args.config.read_text(encoding="utf-8"))
            timestamp = allocate_timestamp(ROOT / "build/anki-build-epoch.txt")
            result = build_package(catalogue, config, args.mode, args.output, args.media_dir, args.missing_policy, timestamp)
            result["build_timestamp"] = timestamp
            write_json(args.output.with_suffix(".report.json"), result)
            print(json.dumps(result, indent=2))
            return
        elif args.command == "validate":
            validate(catalogue)
        result = report(catalogue)
        write_json(args.data / "reports/original-france.json", result)
        print(json.dumps({key: value for key, value in result.items() if key != "issues"}, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
