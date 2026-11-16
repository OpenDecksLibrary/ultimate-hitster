"""Multi-edition invariants and actual successive Anki imports, without network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import test_production as production
from test_production import fixture, make, empty, ROOT
from ultimate_hitster.catalogue import import_edition, load
from ultimate_hitster.build import build_package, selected_notes, MODEL_ID, FIELDS
from ultimate_hitster.registry import discover, select_editions
from ultimate_hitster.selections import statistics


class MultiEditionTests(unittest.TestCase):
    setUp = production.ProductionTests.setUp
    collection = production.ProductionTests.collection
    import_package = production.ProductionTests.import_package
    available = production.ProductionTests.available

    def multi(self):
        first = make()
        first["editions"][0].update(region="FR", language="fr", family="original")
        rows, refs, edition, meta = fixture()
        rows[1]["title"] = "Another"
        refs["2"]["spotify_track_id"] = "C" * 22
        meta["C" * 22] = dict(meta["B" * 22], spotify_id="C" * 22, title="Another")
        edition = dict(edition, edition_id="test-be", region="BE", language="fr", family="summer-party")
        return import_edition(first, rows, refs, edition, meta)

    def test_all_selection_types_and_unknowns(self):
        c = self.multi()
        for config, expected in [
            ({"edition_ids": ["test-fr"]}, ["test-fr"]),
            ({"countries": ["BE"]}, ["test-be"]),
            ({"families": ["original"]}, ["test-fr"]),
            ({"edition_ids": ["test-be", "test-fr"]}, ["test-be", "test-fr"]),
            ({"all": True}, ["test-be", "test-fr"]),
        ]:
            self.assertEqual(select_editions(c, config), expected)
        for config in ({}, {"countries": ["ZZ"]}, {"families": ["missing"]},
                       {"edition_ids": ["missing"]}, {"all": True, "countries": ["FR"]}):
            with self.assertRaises(ValueError):
                select_editions(c, config)

    def test_successive_editions_global_and_modes_preserve_scheduling_and_user_deck(self):
        c = self.available(self.multi())
        collection = self.collection()
        sequence = [
            ({"edition_ids": ["test-fr"]}, "online", 2),
            ({"edition_ids": ["test-be"]}, "online", 3),
            ({"countries": ["FR"]}, "offline", 3),
            ({"families": ["original"]}, "online", 3),
            ({"all": True}, "offline", 3),
            ({"all": True}, "online", 3),
            ({"edition_ids": ["test-fr"]}, "offline", 3),
        ]
        previous = {}
        history = []
        columns = "id,nid,did,ord,type,queue,due,ivl,factor,reps,lapses,left,odue,odid,flags,data"
        for index, (selection, mode, total) in enumerate(sequence):
            config = dict(selection, deck_id=1735079200, deck_name="Ultimate Hitster")
            path = self.path / f"step-{index}.apkg"
            result = build_package(c, config, mode, path, self.path, timestamp=self.timestamp + index * 10)
            with zipfile.ZipFile(path) as package:
                media = json.loads(package.read("media"))
                self.assertEqual(len(media.values()), len(set(media.values())))
                self.assertEqual(len(media), 1 if mode == "offline" else 0)
            self.import_package(collection, path)
            self.assertEqual(collection.card_count(), total)
            current = {row[0]: row for row in collection.db.all(f"select {columns} from cards")}
            for card_id, state in previous.items():
                self.assertEqual(state, current[card_id])
            self.assertEqual(history, collection.db.all("select * from revlog"))
            if index == 0:
                card = collection.get_card(collection.find_cards("")[0])
                card.start_timer()
                collection.sched.answerCard(card, 3)
                # Users can organize existing cards; later APKGs must respect this.
                deck_id = collection.decks.id("My music")
                collection.set_deck([card.id], deck_id)
            previous = {row[0]: row for row in collection.db.all(f"select {columns} from cards")}
            history = collection.db.all("select * from revlog")
        self.assertEqual(len(history), 1)
        self.assertEqual(result["notes"], 2)
        self.assertFalse(collection.media.check().missing)

    def test_tags_include_all_known_memberships_even_in_individual_package(self):
        c = self.available(self.multi())
        path = self.path / "tags.apkg"
        build_package(c, dict(self.config, edition_ids=["test-fr"]), "online", path, self.path)
        collection = self.collection()
        self.import_package(collection, path)
        shared = next(m["study_id"] for m in c["memberships"] if m["edition_id"] == "test-fr" and m["card_number"] == "1")
        note = collection.get_note(collection.find_notes("StudyID:" + shared)[0])
        self.assertTrue({"country::FR", "country::BE", "language::fr", "edition::test-fr",
                         "edition::test-be", "decade::1980s"} <= set(note.tags))
        card = collection.get_card(collection.find_cards("StudyID:" + shared)[0])
        self.assertNotIn("Artist", card.question())
        self.assertNotIn("Song", card.question())
        self.assertNotIn("1980", card.question())
        self.assertIn("Song", card.answer())

    def test_unresolved_references_keep_rows_without_guessing_or_substitution(self):
        rows, refs, edition, meta = fixture()
        refs.pop("2")
        c = import_edition(empty(), rows, refs, edition, meta)
        unresolved = c["memberships"][1]
        self.assertEqual(unresolved["reference"]["status"], "unresolved")
        self.assertIsNone(unresolved["reference"]["spotify_id"])
        result = build_package(c, self.config, "online", self.path / "missing.apkg", self.path)
        self.assertEqual(result["notes"], 2)
        self.assertEqual(len(result["missing_cards"]), 2)
        with self.assertRaises(ValueError):
            build_package(c, self.config, "online", self.path / "strict.apkg", self.path, "error")

    def test_uncertain_new_membership_does_not_disable_verified_shared_recording(self):
        c = self.available(make(count=1))
        old_audio = copy.deepcopy(c["recordings"][0]["audio"])
        rows, refs, edition, meta = fixture(count=1)
        rows[0]["title"] = "Song (uncertain version)"
        c = import_edition(c, rows, refs, dict(edition, edition_id="test-be"), meta)
        self.assertEqual(c["recordings"][0]["audio"], old_audio)
        self.assertEqual(c["memberships"][-1]["reference"]["status"], "metadata_mismatch")
        result = build_package(c, self.config, "online", self.path / "original.apkg", self.path)
        self.assertEqual(result["playable"], 1)

    def test_recordings_with_different_years_share_media_but_not_study(self):
        c = make(count=1)
        rows, refs, edition, meta = fixture(count=1, year=1981)
        c = self.available(import_edition(c, rows, refs, dict(edition, edition_id="test-be"), meta))
        result = build_package(c, dict(self.config, all=True, edition_ids=[]), "offline", self.path / "years.apkg", self.path)
        self.assertEqual((result["notes"], result["media_files"]), (2, 1))
        stats = statistics(c)
        self.assertEqual(len(stats["conflicting_years"]), 1)
        self.assertEqual(stats["unique_recordings"], 1)

    def test_published_v1_identities_and_note_type_stay_fixed(self):
        baseline = json.loads((ROOT / "tests/fixtures/v0.2.0-identities.json").read_text())
        current = load(ROOT / "data")
        current = {m["card_number"]: m for m in current["memberships"] if m["edition_id"] == "hitster-original-france"}
        self.assertEqual(len(current), 308)
        for member in baseline["memberships"]:
            self.assertEqual(member, {key: current[member["card_number"]][key] for key in member})
        self.assertEqual(MODEL_ID, baseline["model_id"])
        self.assertEqual(FIELDS, ["StudyID", "RecordingID", "Artist", "Title", "Year", "Album", "Playback"])

    def test_registry_keeps_markets_revisions_and_counts_without_importing(self):
        source = '<h3>France</h3><a class="ed-tile" href="/en/hitster-editions/original-refresh-france"><span>Hitster Original Refresh</span><span>308 cards</span></a>'
        entry = discover(source)["editions"][0]
        self.assertEqual((entry["region"], entry["family"], entry["revision"], entry["card_count"]),
                         ("FR", "original", "refresh", 308))
        self.assertEqual(entry["status"], "available")
        self.assertEqual(discover(source, [entry["edition_id"]])["editions"][0]["status"], "imported")
        with self.assertRaises(ValueError):
            discover("<html>unavailable</html>")


if __name__ == "__main__":
    unittest.main()
