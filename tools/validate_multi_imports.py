"""Exercise complete candidate selections after the actual published beta APKG."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest
from ultimate_hitster.build import build_package, allocate_timestamp, selected_notes
from ultimate_hitster.catalogue import load
from ultimate_hitster.registry import select_editions

COLUMNS = "id,nid,did,ord,type,queue,due,ivl,factor,reps,lapses,left,odue,odid,flags,data"


def validate(directory):
    directory = Path(directory)
    catalogue = load(ROOT / "data")
    baseline = json.loads((ROOT / "tests/fixtures/v0.2.0-online-asset.json").read_text())
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        with urlopen(Request(baseline["url"], headers={"User-Agent": "UltimateHitster-validation"}), timeout=60) as response:
            data = response.read(2_000_000)
        if hashlib.sha256(data).hexdigest() != baseline["sha256"]:
            raise ValueError("Published v0.2.0-beta.1 package checksum mismatch")
        package = root / "beta.apkg"
        package.write_bytes(data)
        collection = Collection(str(root / "collection.anki2"))
        result = []
        try:
            def importing(path):
                return collection.import_anki_package(ImportAnkiPackageRequest(
                    package_path=str(Path(path).resolve()), options=ImportAnkiPackageOptions(with_scheduling=False)))
            importing(package)
            if collection.card_count() != 308:
                raise ValueError("Published beta import is incomplete")
            baseline_ids = set(collection.find_cards(""))
            for card_id in sorted(baseline_ids)[:5]:
                card = collection.get_card(card_id)
                card.start_timer()
                collection.sched.answerCard(card, 3)
            personal = collection.decks.id("My existing music")
            collection.set_deck([min(baseline_ids)], personal)
            seen = set()
            for name, mode in [
                ("original-france", "online"), ("original-refresh-france", "online"),
                ("guilty-pleasures-france", "online"), ("france", "online"),
                ("original-family", "online"), ("custom-example", "online"),
                ("imported-catalogue", "offline"), ("imported-catalogue", "online"),
                ("original-france", "offline"),
            ]:
                config = json.loads((ROOT / "configs" / f"{name}.json").read_text())
                ids = select_editions(catalogue, config)
                selected = selected_notes(catalogue, ids)
                seen.update(selected)
                path = root / f"{name}-{mode}.apkg"
                build_package(catalogue, config, mode, path, ROOT / "build/media",
                              timestamp=allocate_timestamp(ROOT / "build/anki-build-epoch.txt"))
                before = {row[0]: row for row in collection.db.all(f"select {COLUMNS} from cards")}
                history = collection.db.all("select * from revlog")
                imported = importing(path)
                after = {row[0]: row for row in collection.db.all(f"select {COLUMNS} from cards")}
                if any(after.get(card_id) != row for card_id, row in before.items()):
                    raise ValueError("Import changed existing card scheduling/deck/identity")
                if history != collection.db.all("select * from revlog"):
                    raise ValueError("Import changed actual review history")
                if collection.card_count() != len(seen) or not baseline_ids <= set(after):
                    raise ValueError("Study facts were duplicated, removed or recreated")
                result.append({"selection": name, "mode": mode, "selected_studies": len(selected),
                               "collection_cards": collection.card_count(), "new": len(imported.log.new),
                               "updated": len(imported.log.updated), "history_preserved": True,
                               "scheduling_preserved": True, "user_deck_preserved": True})
            if collection.media.check().missing:
                raise ValueError("Imported offline media is missing")
            guids = collection.db.list("select guid from notes")
            if len(guids) != len(set(guids)):
                raise ValueError("Duplicate Anki note GUIDs")
        finally:
            collection.close()
    output = {"baseline_package_sha256": baseline["sha256"], "baseline_cards": 308,
              "actual_review_rows": 5, "sequence": result, "manual_device_results": "pending"}
    (directory / "successive-imports.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "dist")
    validate(parser.parse_args().directory)
