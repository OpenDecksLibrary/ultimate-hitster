"""Import only explicitly selected editions; discovery never imports songs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ultimate_hitster.catalogue import load, save, write_json, parse_hitify, import_edition
from ultimate_hitster.registry import INDEX_URL, discover
from ultimate_hitster.spotify import fetch, resolve_recordings, resolve_albums, now
from ultimate_hitster.sources import public_references, playlist_ids
from ultimate_hitster.selections import statistics
from ultimate_hitster.build import verify_audio


def snapshot(url, path, refresh):
    path = Path(path)
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    content = fetch(url).decode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(plan, root, refresh=False, audio=False):
    root = Path(root)
    catalogue = load(root)
    index = snapshot(INDEX_URL, root / "sources/hitify-index.html", refresh)
    registry = discover(index, [e["edition_id"] for e in catalogue["editions"]])
    entries = {e["edition_id"]: e for e in registry["editions"]}
    reference_index_url = plan["reference_index"]
    reference_index = json.loads(snapshot(reference_index_url, root / "sources/reference-index.json", refresh))
    progress = lambda done, total: print(f"References {done}/{total}", flush=True)
    # Retain published catalogue rows and identities. Add classification only.
    for existing in catalogue["editions"]:
        entry = entries.get(existing["edition_id"], {})
        for key in ("family", "revision", "languages"):
            if key in entry and key not in existing:
                existing[key] = entry[key]
    for selection in plan["editions"]:
        edition_id = selection["edition_id"]
        entry = entries[edition_id]
        slug = entry["slug"]
        url = entry["sources"][0]["url"]
        page = snapshot(url, root / "sources" / f"{slug}.hitify.html", refresh)
        rows = parse_hitify(page, entry["card_count"])
        candidates = [r for r in reference_index
                      if r["id"] == selection.get("reference_id") or
                      (selection.get("reference_name_contains") and selection["reference_name_contains"].casefold() in r["name"].casefold())]
        if len(candidates) != 1:
            raise ValueError(f"Select one explicit reference source for {edition_id}; candidates: {[r['id'] for r in candidates]}")
        reference_id = candidates[0]["id"]
        reference_url = urljoin(reference_index_url, reference_id + ".json")
        raw = snapshot(reference_url, ROOT / "build/sources" / f"{reference_id}.json", refresh)
        refs, source_issues = public_references(json.loads(raw), rows, reference_url, selection.get("reference_market"))
        write_json(root / "sources" / f"{slug}.references.json", refs)
        # Compare independent references to every ID actually exposed publicly.
        playlist_match = re.search(r"https://open.spotify.com/(?:embed/)?playlist/([A-Za-z0-9]{22})", page)
        playlist_checks = {"status": "unavailable"}
        if playlist_match:
            playlist_url = "https://open.spotify.com/embed/playlist/" + playlist_match.group(1)
            try:
                exposed = playlist_ids(snapshot(playlist_url, ROOT / "build/sources" / f"{slug}.playlist.html", refresh))
                mismatches = [str(i) for i, provider in enumerate(exposed, 1)
                              if i > len(rows) or refs[str(i)]["spotify_track_id"] != provider]
                playlist_checks = {"source_url": playlist_url, "exposed": len(exposed), "mismatches": mismatches,
                                   "status": "matched" if not mismatches else "conflict"}
            except (OSError, ValueError, KeyError) as error:
                playlist_checks = {"source_url": playlist_url, "status": "fetch_failed", "error": str(error)}
        for number in playlist_checks.get("mismatches", []):
            if number in refs:
                refs[number]["playlist_conflict"] = True
        write_json(root / "sources" / f"{slug}.references.json", refs)
        ids = [ref["spotify_track_id"] for ref in refs.values() if ref["spotify_track_id"]]
        metadata = resolve_recordings(ids, ROOT / "build/provider-cache", refresh=refresh, progress=progress)
        albums = resolve_albums(ids, ROOT / "build/album-cache", progress=progress, refresh=refresh)
        edition = {**entry, "languages": selection.get("languages", entry["languages"]),
                   "year_kind": "catalogue_release_year", "printed_years_verified": False,
                   "sources": [{"url": url, "snapshot": f"{slug}.hitify.html", "sha256": digest(page), "retrieved_on": now()[:10]},
                               {"url": reference_url, "snapshot": f"{slug}.references.json", "upstream_sha256": digest(raw),
                                "retrieved_on": now()[:10], "matcher": candidates[0].get("matcher")}],
                   "reference_playlist_check": playlist_checks, "reference_source_issues": source_issues}
        review_path = root / "sources" / f"{slug}.reviews.json"
        reviews = json.loads(review_path.read_text()) if review_path.exists() else {}
        catalogue = import_edition(catalogue, rows, refs, edition, metadata, albums, reviews)
        # A positional/source conflict is never declared verified solely by a
        # matching title. Keep the original ID, metadata and explicit issue.
        uncertain = {issue["card_number"] for issue in source_issues}
        uncertain.update(playlist_checks.get("mismatches", []))
        for member in catalogue["memberships"]:
            if member["edition_id"] == edition_id:
                member["reference"]["source_checks"] = refs[member["card_number"]]["source_checks"]
                member["reference"]["source_markets"] = refs[member["card_number"]]["source_markets"]
                if member["card_number"] in uncertain and member["reference"]["status"] not in ("unresolved", "reviewed"):
                    member["reference"]["status"] = "source_conflict"
        save(root, catalogue)
        print("IMPORTED", edition_id, len(rows), "SOURCE ISSUES", len(source_issues), "PLAYLIST", playlist_checks, flush=True)
    if audio:
        verify_audio(catalogue, ROOT / "build/media", refresh=refresh,
                     progress=lambda done, total: print(f"Audio {done}/{total}", flush=True))
        save(root, catalogue)
    imported = {e["edition_id"] for e in catalogue["editions"]}
    for entry in registry["editions"]:
        entry["status"] = "imported" if entry["edition_id"] in imported else "available"
    registry["retrieved_on"] = now()[:10]
    write_json(root / "registry.json", registry)
    stats = statistics(catalogue, registry)
    write_json(root / "reports/catalogue.json", stats)
    print(json.dumps({key: value for key, value in stats.items() if key not in ("issues", "conflicting_years")}, indent=2))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "configs/import-v0.3.json")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--check-audio", action="store_true")
    args = parser.parse_args()
    run(json.loads(args.plan.read_text()), args.data, args.refresh, args.check_audio)
