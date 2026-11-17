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
from .registry import INDEX_URL, discover
from .selections import statistics

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
    importing.add_argument("--edition", default="hitster-original-france", help="Edition ID in data/registry.json")
    importing.add_argument("--references", type=Path, required=True, help="Exact card-reference CSV or JSON map; no title search")
    importing.add_argument("--expected-count", type=int, help="Optional additional assertion against the registry")
    importing.add_argument("--provider-cache", type=Path, default=ROOT / "build/provider-cache")
    importing.add_argument("--album-cache", type=Path, default=ROOT / "build/album-cache")
    importing.add_argument("--reviews", type=Path)
    resolving = commands.add_parser("refresh-references")
    resolving.add_argument("--references", type=Path, required=True)
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
    registry = commands.add_parser("discover-editions")
    registry.add_argument("--html", type=Path)
    commands.add_parser("statistics")
    args = parser.parse_args()
    try:
        catalogue = load(args.data)
        if args.command == "import-hitify":
            registry_path = args.data / "registry.json"
            entries = json.loads(registry_path.read_text())["editions"] if registry_path.exists() else catalogue["editions"]
            entry = next((e for e in entries if e["edition_id"] == args.edition), None)
            if entry is None:
                raise ValueError("Unknown edition; run discover-editions first")
            url = entry["sources"][0]["url"]
            source = args.html.read_text(encoding="utf-8") if args.html else fetch(url).decode("utf-8")
            count = entry["card_count"]
            if args.expected_count is not None and args.expected_count != count:
                raise ValueError("Expected card count disagrees with registry")
            rows = parse_hitify(source, count)
            references = (json.loads(args.references.read_text()) if args.references.suffix == ".json"
                          else read_references(args.references))
            edition = {**entry, "year_kind": "catalogue_release_year", "printed_years_verified": False,
                       "language": entry.get("language", (entry.get("languages") or ["und"])[0]),
                       "sources": [{"url": url, "retrieved_on": now()[:10],
                                    "snapshot": args.html.name if args.html else None,
                                    "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()},
                                   {"snapshot": args.references.name, "sha256": source_digest(args.references)}]}
            catalogue = import_edition(catalogue, rows, references, edition,
                                       cache(args.provider_cache), cache(args.album_cache),
                                       json.loads(args.reviews.read_text()) if args.reviews else {})
            save(args.data, catalogue)
        elif args.command == "refresh-references":
            references = (json.loads(args.references.read_text()) if args.references.suffix == ".json"
                          else read_references(args.references))
            ids = [r["spotify_track_id"] for r in references.values() if r.get("spotify_track_id")]
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
        elif args.command == "discover-editions":
            source = args.html.read_text() if args.html else fetch(INDEX_URL).decode("utf-8")
            registry = discover(source, [e["edition_id"] for e in catalogue["editions"]])
            write_json(args.data / "registry.json", registry)
            print(f"Discovered {len(registry['editions'])} editions")
            return
        elif args.command == "statistics":
            path = args.data / "registry.json"
            registry = json.loads(path.read_text()) if path.exists() else None
            result = statistics(catalogue, registry)
            write_json(args.data / "reports/catalogue.json", result)
            print(json.dumps(result, indent=2))
            return
        elif args.command == "validate":
            validate(catalogue)
        result = report(catalogue)
        write_json(args.data / "reports/import-validation.json", result)
        print(json.dumps({key: value for key, value in result.items() if key != "issues"}, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
