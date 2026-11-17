"""Build checked prerelease assets for explicit imported-catalogue selections."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from ultimate_hitster.catalogue import load, validate
from ultimate_hitster.build import allocate_timestamp, build_package, verify_audio, selected_notes
from ultimate_hitster.registry import select_editions
from ultimate_hitster.selections import statistics
from ultimate_hitster.__main__ import report


def release_plan(path=ROOT / "release.json"):
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if not re.fullmatch(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+", plan.get("tag", "")) or plan.get("prerelease") is not True:
        raise ValueError("Only explicit alpha/beta/rc prereleases are supported")
    notes = ROOT / plan["notes"]
    if notes.parent != ROOT / "docs/releases" or notes.stem != plan["tag"] or not notes.is_file():
        raise ValueError("Release notes must exist at docs/releases/<tag>.md")
    if plan.get("missing_policy", "error") not in ("include", "error"):
        raise ValueError("Unknown missing-audio policy")
    if "packages" not in plan:  # Preserve the already published v0.2 plan.
        plan["packages"] = [{"stem": "ultimate-hitster-original-france", "config": "configs/original-france.json"}]
    seen = set()
    if not plan["packages"]:
        raise ValueError("No package selections")
    for package in plan["packages"]:
        stem = package["stem"]
        config = ROOT / package["config"]
        if not re.fullmatch(r"[a-z0-9-]+", stem) or stem in seen:
            raise ValueError("Invalid or duplicate package stem")
        if config.parent != ROOT / "configs" or config.suffix != ".json" or not config.is_file():
            raise ValueError("Package configs must exist inside configs/")
        seen.add(stem)
    return plan


def asset_names(plan):
    return [f"{p['stem']}-{mode}.apkg" for p in plan["packages"] for mode in ("online", "offline")] + ["validation.json"] + plan.get("extra_reports", [])


ASSETS = asset_names(release_plan())


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_checksums(directory, assets=None):
    directory = Path(directory)
    (directory / "SHA256SUMS").write_text(
        "".join(f"{digest(directory / name)}  {name}\n" for name in (assets or ASSETS)), encoding="utf-8")


def verify_checksums(directory, expected=None, assets=None):
    directory = Path(directory)
    content = (directory / "SHA256SUMS").read_text(encoding="utf-8")
    if expected is not None and content != (Path(expected) / "SHA256SUMS").read_text(encoding="utf-8"):
        raise ValueError("Downloaded checksum file differs from the built checksum file")
    lines = content.splitlines()
    names = assets or ASSETS
    if len(lines) != len(names):
        raise ValueError("Unexpected checksum manifest length")
    for line, name in zip(lines, names):
        if line != f"{digest(directory / name)}  {name}":
            raise ValueError(f"Checksum mismatch: {name}")


def verify_anki(online, offline, expected_count):
    from anki.collection import Collection
    from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest

    with tempfile.TemporaryDirectory() as temporary:
        collection = Collection(str(Path(temporary) / "collection.anki2"))
        try:
            def importing(path):
                return collection.import_anki_package(ImportAnkiPackageRequest(
                    package_path=str(Path(path).resolve()), options=ImportAnkiPackageOptions(with_scheduling=True)))
            if len(importing(online).log.new) != expected_count or collection.card_count() != expected_count:
                raise ValueError("Incomplete online Anki import")
            unavailable = collection.find_cards("tag:audio::missing Playback:*unavailable*")
            if any(collection.get_card(cid).queue != -1 for cid in unavailable):
                raise ValueError("Unavailable new cards were not imported suspended")
            card = collection.get_card(collection.find_cards("-is:suspended")[0])
            card.start_timer()
            collection.sched.answerCard(card, 3)
            query = "select id,nid,did,type,queue,due,ivl,factor,reps,lapses,left,odue,odid,flags,data from cards order by id"
            scheduling = collection.db.all(query)
            history = collection.db.all("select * from revlog")
            if len(importing(offline).log.updated) != expected_count or collection.card_count() != expected_count:
                raise ValueError("Offline alternative did not update every existing note")
            if scheduling != collection.db.all(query) or history != collection.db.all("select * from revlog"):
                raise ValueError("Mode switch changed identities, scheduling or review history")
            media = collection.media.check()
            if media.missing or media.unused:
                raise ValueError("Offline import has missing or unused media")
        finally:
            collection.close()
    return {"online_new": expected_count, "offline_updated": expected_count,
            "scheduling_preserved": True, "review_history_preserved": True,
            "missing_media": 0, "unused_media": 0, "unavailable_suspended": len(unavailable),
            "import_learning_progress_required_for_suspension": True}


def prepare(directory, live, plan_path=ROOT / "release.json"):
    plan = release_plan(plan_path)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    catalogue = load(ROOT / "data")
    validate(catalogue)
    # Check only recordings used by this plan. No new editions are imported.
    selections = []
    selected_members = set()
    for package in plan["packages"]:
        config = json.loads((ROOT / package["config"]).read_text())
        ids = select_editions(catalogue, config)
        selected_members.update(ids)
        selections.append((package, config, ids))
    working = copy.deepcopy(catalogue)
    working["editions"] = [e for e in catalogue["editions"] if e["edition_id"] in selected_members]
    working["memberships"] = [m for m in catalogue["memberships"] if m["edition_id"] in selected_members]
    recordings = {m["recording_id"] for m in working["memberships"]}
    working["recordings"] = [t for t in catalogue["recordings"] if t["recording_id"] in recordings]
    verify_audio(working, ROOT / "build/media", refresh=live,
                 progress=lambda done, total: print(f"Release audio {done}/{total}", flush=True))
    audio = {t["recording_id"]: t["audio"] for t in working["recordings"]}
    for track in catalogue["recordings"]:
        if track["recording_id"] in audio:
            track["audio"] = audio[track["recording_id"]]
    validation = report(working)
    if plan.get("missing_policy", "error") == "error" and validation["issues"]:
        raise ValueError("Release blocked by unavailable/unverified references or audio")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    packages = []
    imports = []
    for package, config, ids in selections:
        expected = len(selected_notes(catalogue, ids))
        for mode in ("online", "offline"):
            timestamp = allocate_timestamp(ROOT / "build/anki-build-epoch.txt")
            result = build_package(catalogue, config, mode, directory / f"{package['stem']}-{mode}.apkg",
                                   ROOT / "build/media", missing_policy=plan.get("missing_policy", "error"), timestamp=timestamp)
            result["build_timestamp"] = timestamp
            if result["notes"] != expected:
                raise ValueError("Incomplete selection package")
            packages.append(result)
        imports.append({"stem": package["stem"], **verify_anki(directory / f"{package['stem']}-online.apkg",
                                                              directory / f"{package['stem']}-offline.apkg", expected)})
    registry_path = ROOT / "data/registry.json"
    validation.update(tag=plan["tag"], source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                      live_audio_check=live, packages=packages, anki_import=imports,
                      statistics=statistics(working, json.loads(registry_path.read_text()) if registry_path.exists() else None),
                      manual_full_edition_playback_validated=False, mobile_clients_validated=False)
    (directory / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if "exceptions.json" in plan.get("extra_reports", []):
        recheck = json.loads((ROOT / "data/reports/v0.3-exception-recheck.json").read_text())
        remaining = []
        all_notes = selected_notes(catalogue, sorted(selected_members))
        for study_id, item in sorted(all_notes.items()):
            track = item["track"]
            if not item["verified_reference"] or track["audio"]["status"] != "verified":
                remaining.append({"study_id": study_id, "recording_id": track["recording_id"],
                                  "artist": track["artist"], "title": track["title"], "album": track.get("album"),
                                  "year": item["year"], "audio": track["audio"], "memberships": item["memberships"]})
        exceptions = {"source_commit": validation["source_commit"], "original_recheck": recheck,
                      "resolved_credit_reviews": json.loads((ROOT / "data/sources/guilty-pleasures-france.reviews.json").read_text()),
                      "remaining": remaining, "remaining_count": len(remaining),
                      "anki_search": "tag:audio::missing Playback:*unavailable*",
                      "new_cards_suspended": True, "requires_import_learning_progress": True,
                      "existing_cards": "Anki preserves existing scheduling; suspend current unavailable cards after an upgrade.",
                      "manual_validation": {"Anki Desktop v0.3 GUI": "pending", "AnkiDroid": "pending", "AnkiMobile": "pending",
                                            "physical QR/master comparison": "pending"}}
        (directory / "exceptions.json").write_text(json.dumps(exceptions, ensure_ascii=False, indent=2) + "\n")
    if "successive-imports.json" in plan.get("extra_reports", []):
        from tools.validate_multi_imports import validate as validate_imports
        validation["successive_imports"] = validate_imports(directory, catalogue=catalogue)
        (directory / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
    assets = asset_names(plan)
    write_checksums(directory, assets)
    verify_checksums(directory, assets=assets)
    print(json.dumps({"tag": plan["tag"], "packages": packages, "anki_import": imports}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--plan", type=Path, default=ROOT / "release.json")
    parser.add_argument("--directory", type=Path, default=ROOT / "dist")
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.directory, args.live, args.plan)
    else:
        verify_checksums(args.directory, args.expected, asset_names(release_plan(args.plan)))
        print("All release asset SHA-256 checksums match")
