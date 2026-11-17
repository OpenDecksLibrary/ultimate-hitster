"""Actual Anki suspension/import-option behavior and bounded credit review checks."""
import copy
import json
import unittest
from pathlib import Path
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest
import test_production as production
from test_production import fixture, empty
from ultimate_hitster.catalogue import import_edition
from ultimate_hitster.build import build_package

SEARCH = "tag:audio::missing Playback:*unavailable*"


class SuspensionTests(unittest.TestCase):
    setUp = production.ProductionTests.setUp
    collection = production.ProductionTests.collection
    available = production.ProductionTests.available

    def importing(self, collection, path, scheduling=True):
        return collection.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(path), options=ImportAnkiPackageOptions(with_scheduling=scheduling)))

    def mixed(self):
        catalogue = self.available(production.make())
        catalogue["recordings"][1]["audio"] = {"format": "mp3", "provider": "spotify",
                                               "url": None, "status": "unavailable", "reason": "provider_no_preview"}
        return catalogue

    def test_new_missing_cards_suspended_and_mode_switch_preserves_existing_schedules(self):
        catalogue = self.mixed()
        online, offline = self.path / "online.apkg", self.path / "offline.apkg"
        result = build_package(catalogue, self.config, "online", online, self.path, timestamp=self.timestamp)
        self.assertEqual(result["suspended_cards"], 1)
        col = self.collection()
        self.importing(col, online)
        missing = col.find_cards(SEARCH)
        self.assertEqual(len(missing), 1)
        self.assertEqual(col.get_card(missing[0]).queue, -1)
        active = col.find_cards("-is:suspended")
        self.assertEqual(len(active), 1)
        card = col.get_card(active[0])
        card.start_timer()
        col.sched.answerCard(card, 3)
        query = "select id,nid,type,queue,due,ivl,factor,reps,lapses,left,data from cards order by id"
        before, history = col.db.all(query), col.db.all("select * from revlog")
        build_package(catalogue, self.config, "offline", offline, self.path, timestamp=self.timestamp + 10)
        self.importing(col, offline)
        self.assertEqual(before, col.db.all(query))
        self.assertEqual(history, col.db.all("select * from revlog"))

    def test_import_without_learning_progress_requires_the_documented_manual_filter(self):
        catalogue = self.mixed()
        path = self.path / "package.apkg"
        build_package(catalogue, self.config, "online", path, self.path)
        col = self.collection()
        self.importing(col, path, scheduling=False)
        missing = col.find_cards(SEARCH)
        self.assertEqual(len(missing), 1)
        self.assertEqual(col.get_card(missing[0]).queue, 0)
        col.sched.suspend_cards(missing)
        self.assertEqual(col.get_card(missing[0]).queue, -1)

    def test_recovered_audio_does_not_unsuspend_existing_cards_or_match_current_missing_filter(self):
        catalogue = self.mixed()
        path = self.path / "package.apkg"
        build_package(catalogue, self.config, "online", path, self.path, timestamp=self.timestamp)
        col = self.collection()
        self.importing(col, path)
        missing = col.find_cards(SEARCH)
        self.assertEqual(len(missing), 1)
        catalogue["recordings"][1]["audio"] = copy.deepcopy(catalogue["recordings"][0]["audio"])
        build_package(catalogue, self.config, "online", path, self.path, timestamp=self.timestamp + 10)
        self.importing(col, path)
        self.assertEqual(col.find_cards(SEARCH), [])
        self.assertEqual(col.get_card(missing[0]).queue, -1)

    def test_explicit_credit_review_is_bound_to_id_title_artist_and_source_checks(self):
        rows, refs, edition, meta = fixture(count=1)
        rows[0]["artist"] = "Stage Name"
        refs["1"]["source_checks"] = {"title": True, "artist": False}
        review = {"1": {"spotify_id": "A" * 22, "catalogue_title": "Song", "provider_title": "Song",
                        "catalogue_artist": "Stage Name", "provider_artists": ["Artist"],
                        "source_checks": {"title": True, "artist": False}, "review_kind": "credit_only",
                        "reason": "Explicit stage-name credit review"}}
        c = import_edition(empty(), rows, refs, edition, meta, reviews=review)
        self.assertEqual(c["memberships"][0]["reference"]["status"], "reviewed")
        self.assertEqual(c["memberships"][0]["study_id"],
                         import_edition(c, rows, refs, edition, meta, reviews=review)["memberships"][0]["study_id"])
        for kind in ("id", "title", "artist", "source"):
            changed_meta, changed_refs = copy.deepcopy(meta), copy.deepcopy(refs)
            if kind == "id":
                changed_refs["1"]["spotify_track_id"] = "B" * 22
            elif kind == "title":
                changed_meta["A" * 22]["title"] = "Song - Live"
            elif kind == "artist":
                changed_meta["A" * 22]["artists"] = ["Different Artist"]
            else:
                changed_refs["1"]["source_checks"] = {"title": True, "artist": True}
            with self.assertRaises(ValueError):
                import_edition(empty(), rows, changed_refs, edition, changed_meta, reviews=review)


if __name__ == "__main__":
    unittest.main()
