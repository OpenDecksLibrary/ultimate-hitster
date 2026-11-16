"""Production invariants and actual Anki imports; no live network in CI."""

import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ultimate_hitster.catalogue import import_edition, parse_hitify, validate, load, save
from ultimate_hitster.build import MODEL_ID, build_package, note_guid, allocate_timestamp
from ultimate_hitster.spotify import parse_recording, parse_album, check_clip


def empty():
    return {"recordings": [], "editions": [], "memberships": []}


def fixture(count=2, shared=False, year=1980):
    ids = ["A" * 22, "A" * 22 if shared else "B" * 22]
    rows = [{"card_number": str(i + 1), "artist": "Artist", "title": "Song", "year": year} for i in range(count)]
    refs = {row["card_number"]: {"spotify_track_id": ids[i]} for i, row in enumerate(rows)}
    meta = {provider: {"spotify_id": provider, "title": "Song", "artists": ["Artist"], "status": "available",
                       "preview_url": "https://p.scdn.co/mp3-preview/" + str(i + 1) * 40}
            for i, provider in enumerate(ids[:count])}
    edition = {"edition_id": "test-fr", "card_count": count}
    return rows, refs, edition, meta


def make(**kwargs):
    return import_edition(empty(), *fixture(**kwargs))


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.config = {"edition_ids": ["test-fr"], "deck_id": 1735079101, "deck_name": "Production test"}
        self.timestamp = int(time.time())

    def collection(self):
        collection = Collection(str(self.path / "collection.anki2"))
        self.addCleanup(collection.close)
        return collection

    def import_package(self, collection, path):
        return collection.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(path), options=ImportAnkiPackageOptions(with_scheduling=False)))

    def available(self, catalogue):
        # Packaging fixture only. Real provider MP3 decoding is checked by check-audio.
        data = b"ID3" + b"\x00" * 4096
        digest = hashlib.sha256(data).hexdigest()
        (self.path / f"uh_{digest}.mp3").write_bytes(data)
        for track in catalogue["recordings"]:
            track["audio"].update(status="verified", sha256=digest, duration_seconds=30, decoded=True)
        return catalogue

    def test_full_source_is_308_rows_without_a_sample_cap(self):
        source = (ROOT / "data/sources/original-france.hitify.html").read_text(encoding="utf-8")
        rows = parse_hitify(source, 308)
        self.assertEqual(len(rows), 308)
        self.assertEqual(rows[-1]["card_number"], "308")
        with self.assertRaises(ValueError):
            parse_hitify(source, 307)
        with self.assertRaises(ValueError):
            parse_hitify(source.replace("<td>308</td>", "<td>1</td>"), 308)

    def test_exact_provider_dedup_and_no_fuzzy_song_merging(self):
        shared = make(shared=True)
        self.assertEqual(len(shared["recordings"]), 1)
        self.assertEqual(len({member["study_id"] for member in shared["memberships"]}), 1)
        distinct = make()
        self.assertEqual(len(distinct["recordings"]), 2)  # Identical names, different pinned recordings.
        rows, refs, edition, metadata = fixture(shared=True)
        edition = dict(edition, edition_id="test-be")
        multi = import_edition(shared, rows, refs, edition, metadata)
        self.assertEqual(len(multi["recordings"]), 1)
        self.assertEqual(len({member["study_id"] for member in multi["memberships"]}), 1)

    def test_conflicting_edition_years_get_distinct_studies(self):
        first = make(count=1)
        rows, refs, edition, meta = fixture(count=1, year=1981)
        second = import_edition(first, rows, refs, dict(edition, edition_id="test-be"), meta)
        self.assertEqual(len(second["recordings"]), 1)
        self.assertEqual(len({member["study_id"] for member in second["memberships"]}), 2)

    def test_reference_changes_and_unreviewed_versions_are_never_silently_substituted(self):
        original = make(count=1)
        rows, refs, edition, meta = fixture(count=1)
        refs["1"]["spotify_track_id"] = "C" * 22
        with self.assertRaises(ValueError):
            import_edition(original, rows, refs, edition, meta)
        rows, refs, edition, meta = fixture(count=1)
        meta["A" * 22]["title"] = "Song - Live"
        unreviewed = import_edition(empty(), rows, refs, edition, meta)
        self.assertEqual(unreviewed["memberships"][0]["reference"]["status"], "metadata_mismatch")
        self.assertEqual(unreviewed["recordings"][0]["audio"]["status"], "unavailable")

    def test_explicit_review_is_bound_to_exact_id_and_version(self):
        rows, refs, edition, meta = fixture(count=1)
        meta["A" * 22]["title"] = "Song - Radio Edit"
        review = {"1": {"spotify_id": "A" * 22, "catalogue_title": "Song", "provider_title": "Song - Radio Edit", "reason": "Pinned source version reviewed"}}
        result = import_edition(empty(), rows, refs, edition, meta, reviews=review)
        self.assertEqual(result["memberships"][0]["reference"]["status"], "reviewed")
        meta["A" * 22]["title"] = "Song - Live"
        with self.assertRaises(ValueError):
            import_edition(empty(), rows, refs, edition, meta, reviews=review)

    def test_missing_audio_keeps_catalogue_cards_and_strict_build_fails(self):
        catalogue = make()
        path = self.path / "missing.apkg"
        result = build_package(catalogue, self.config, "online", path, self.path)
        self.assertEqual((result["notes"], result["playable"], len(result["missing_cards"])), (2, 0, 2))
        collection = self.collection()
        self.import_package(collection, path)
        self.assertEqual(collection.card_count(), 2)
        for card_id in collection.find_cards(""):
            card = collection.get_card(card_id)
            self.assertIn('aria-label="Audio unavailable"', card.question())
            self.assertNotIn("Song", card.question())
            self.assertIn("Song", card.answer())
        with self.assertRaises(ValueError):
            build_package(catalogue, self.config, "online", self.path / "strict.apkg", self.path, "error")

    def test_online_offline_switch_and_corrections_preserve_actual_review_history(self):
        catalogue = self.available(make())
        online, offline = self.path / "online.apkg", self.path / "offline.apkg"
        with patch("ultimate_hitster.spotify.fetch", side_effect=AssertionError("Build must be offline")):
            build_package(catalogue, self.config, "online", online, self.path, timestamp=self.timestamp)
            build_package(catalogue, self.config, "offline", offline, self.path, timestamp=self.timestamp + 10)
        with zipfile.ZipFile(offline) as package:
            self.assertEqual(len(json.loads(package.read("media"))), 1)
        collection = self.collection()
        self.import_package(collection, online)
        card = collection.get_card(collection.find_cards("")[0])
        card.start_timer()
        collection.sched.answerCard(card, 3)
        before = collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id")
        history = collection.db.all("select * from revlog")
        self.assertEqual(len(self.import_package(collection, offline).log.updated), 2)
        catalogue["memberships"][0]["catalogue_year"] = 1982
        catalogue["recordings"][0]["title"] = "Corrected title"
        catalogue["recordings"][0]["album"] = {"name": "<script>album</script>"}
        build_package(catalogue, self.config, "online", online, self.path, timestamp=self.timestamp + 20)
        self.import_package(collection, online)
        self.assertEqual(collection.card_count(), 2)
        self.assertEqual(before, collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id"))
        self.assertEqual(history, collection.db.all("select * from revlog"))
        self.assertNotIn("<script>", collection.get_card(card.id).answer())
        self.assertNotIn(MODEL_ID, [1735068211, 1735068221, 1735068222])

    def test_integrity_checks_reject_modified_offline_audio_and_invalid_schema(self):
        catalogue = self.available(make())
        for path in self.path.glob("*.mp3"):
            path.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            build_package(catalogue, self.config, "offline", self.path / "bad.apkg", self.path)
        for mutation in (lambda c: c["memberships"][0].update(recording_id="missing"),
                         lambda c: c["memberships"][0].update(catalogue_year=True),
                         lambda c: c["recordings"][0]["audio"].update(url="https://example.com/file.mp3")):
            invalid = copy.deepcopy(catalogue)
            mutation(invalid)
            with self.assertRaises(ValueError):
                validate(invalid)

    def test_provider_parser_rejects_relinks_and_preserves_missing_preview(self):
        entity = {"id": "A" * 22, "type": "track", "title": "Song", "artists": [{"name": "Artist"}], "audioPreview": None}
        page = '<script id="__NEXT_DATA__">' + json.dumps({"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}) + '</script>'
        parsed = parse_recording(page, "A" * 22)
        self.assertEqual(parsed["status"], "missing_preview")
        self.assertIsNone(parsed["preview_url"])
        with self.assertRaises(ValueError):
            parse_recording(page, "B" * 22)
        with patch("ultimate_hitster.spotify.fetch", return_value=b"<html>not an MP3</html>"), self.assertRaises(ValueError):
            check_clip("https://p.scdn.co/mp3-preview/" + "1" * 40, self.path)

    def test_album_page_requires_exact_track_and_unambiguous_album(self):
        page = '<meta property="og:url" content="https://open.spotify.com/track/' + "A" * 22 + '"><meta property="music:album" content="https://open.spotify.com/album/' + "B" * 22 + '"><a href="/album/' + "B" * 22 + '"><span>Album &amp; More</span></a>'
        self.assertEqual(parse_album(page, "A" * 22)["name"], "Album & More")
        with self.assertRaises(ValueError):
            parse_album(page, "C" * 22)

    def test_json_roundtrip_and_year_correction_keep_identity(self):
        catalogue = make()
        save(self.path, catalogue)
        original = load(self.path)
        rows, refs, edition, meta = fixture(year=1985)
        updated = import_edition(original, rows, refs, edition, meta)
        self.assertEqual([m["study_id"] for m in original["memberships"]], [m["study_id"] for m in updated["memberships"]])
        self.assertEqual([note_guid(m["study_id"]) for m in original["memberships"]], [note_guid(m["study_id"]) for m in updated["memberships"]])

    def test_back_to_back_modes_receive_newer_import_timestamps(self):
        with patch("ultimate_hitster.build.time.time", return_value=100):
            first = allocate_timestamp(self.path / "clock.txt")
            second = allocate_timestamp(self.path / "clock.txt")
        self.assertEqual((first, second), (100, 101))

    def test_provider_reissue_dates_do_not_replace_catalogue_years(self):
        rows, refs, edition, meta = fixture(count=1, year=1969)
        meta["A" * 22]["release_date"] = "2009-01-01T00:00:00Z"
        catalogue = import_edition(empty(), rows, refs, edition, meta)
        self.assertEqual(catalogue["memberships"][0]["catalogue_year"], 1969)
        self.assertIn("2009", catalogue["recordings"][0]["provider_metadata"]["release_date"])


if __name__ == "__main__":
    unittest.main()
