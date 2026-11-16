"""Build checked prerelease assets; never import or modify canonical editions."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ultimate_hitster.catalogue import load, validate
from ultimate_hitster.build import allocate_timestamp, build_package, verify_audio
from ultimate_hitster.__main__ import report

PACKAGE_STEM = "ultimate-hitster-original-france"
ASSETS = [f"{PACKAGE_STEM}-{mode}.apkg" for mode in ("online", "offline")] + ["validation.json"]


def release_plan(path=ROOT / "release.json"):
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if not re.fullmatch(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+", plan.get("tag", "")) or plan.get("prerelease") is not True:
        raise ValueError("Only explicit alpha/beta/rc prereleases are supported")
    notes = ROOT / plan["notes"]
    if notes.parent != ROOT / "docs/releases" or notes.stem != plan["tag"] or not notes.is_file():
        raise ValueError("Release notes must exist at docs/releases/<tag>.md")
    return plan


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_checksums(directory):
    directory = Path(directory)
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest(directory / name)}  {name}\n" for name in ASSETS), encoding="utf-8")


def verify_checksums(directory, expected=None):
    directory = Path(directory)
    content = (directory / "SHA256SUMS").read_text(encoding="utf-8")
    if expected is not None and content != (Path(expected) / "SHA256SUMS").read_text(encoding="utf-8"):
        raise ValueError("Downloaded checksum file differs from the built checksum file")
    lines = content.splitlines()
    if len(lines) != len(ASSETS):
        raise ValueError("Unexpected checksum manifest length")
    for line, name in zip(lines, ASSETS):
        if line != f"{digest(directory / name)}  {name}":
            raise ValueError(f"Checksum mismatch: {name}")


def verify_anki(online, offline, expected_count):
    # Disposable collection only; no user profile or scheduling is imported.
    from anki.collection import Collection
    from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest

    with tempfile.TemporaryDirectory() as temporary:
        collection = Collection(str(Path(temporary) / "collection.anki2"))
        try:
            def importing(path):
                return collection.import_anki_package(ImportAnkiPackageRequest(
                    package_path=str(Path(path).resolve()), options=ImportAnkiPackageOptions(with_scheduling=False)))

            if len(importing(online).log.new) != expected_count or collection.card_count() != expected_count:
                raise ValueError("Incomplete online Anki import")
            card = collection.get_card(collection.find_cards("")[0])
            card.start_timer()
            collection.sched.answerCard(card, 3)
            scheduling = collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id")
            history = collection.db.all("select * from revlog")
            if len(importing(offline).log.updated) != expected_count or collection.card_count() != expected_count:
                raise ValueError("Offline alternative did not update every existing note")
            if scheduling != collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id") or history != collection.db.all("select * from revlog"):
                raise ValueError("Mode switch changed card identities, scheduling or review history")
            media = collection.media.check()
            if media.missing or media.unused:
                raise ValueError("Offline import has missing or unused media")
        finally:
            collection.close()
    return {"online_new": expected_count, "offline_updated": expected_count,
            "scheduling_preserved": True, "review_history_preserved": True,
            "missing_media": 0, "unused_media": 0}


def prepare(directory, live):
    plan = release_plan()
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    catalogue = load(ROOT / "data")
    validate(catalogue)
    if {edition["edition_id"] for edition in catalogue["editions"]} != {"hitster-original-france"} or len(catalogue["memberships"]) != 308:
        raise ValueError("This release must contain exactly the 308 Original France cards")
    verify_audio(catalogue, ROOT / "build/media", refresh=live,
                 progress=lambda done, total: print(f"Release audio {done}/{total}", flush=True))
    validation = report(catalogue)
    if validation["issues"] or validation["audio_status"] != {"verified": 308}:
        raise ValueError("Release blocked by unavailable/unverified references or audio")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "configs/original-france.json").read_text())
    packages = []
    for mode in ("online", "offline"):
        timestamp = allocate_timestamp(ROOT / "build/anki-build-epoch.txt")
        result = build_package(catalogue, config, mode, directory / f"{PACKAGE_STEM}-{mode}.apkg",
                               ROOT / "build/media", missing_policy="error", timestamp=timestamp)
        result["build_timestamp"] = timestamp
        if result["notes"] != 308 or result["playable"] != 308:
            raise ValueError("Incomplete release package")
        packages.append(result)
    validation["anki_import"] = verify_anki(directory / ASSETS[0], directory / ASSETS[1], 308)
    validation["tag"] = plan["tag"]
    validation["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    validation["live_audio_check"] = live
    validation["packages"] = packages
    validation["manual_full_edition_playback_validated"] = False
    validation["mobile_clients_validated"] = False
    (directory / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_checksums(directory)
    verify_checksums(directory)
    print(json.dumps({"tag": plan["tag"], "packages": packages, "anki_import": validation["anki_import"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--directory", type=Path, default=ROOT / "dist")
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--live", action="store_true", help="Force fresh MP3 retrieval instead of checked local media")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.directory, args.live)
    else:
        verify_checksums(args.directory, args.expected)
        print("All release asset SHA-256 checksums match")
