"""Offline regression checks for the ten-song playback comparison."""

import copy
import html
import io
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
sys.path[:0] = [str(ROOT / "prototype"), str(ROOT / "tools")]
import build_comparison as comparison
from build import build as build_original, demo_audio, MODEL_ID
from extract_hitify_rows import extract_rows
from refresh_sample_previews import refresh


def visible_text(fragment):
    return re.sub(r"<[^>]*>", "", re.sub(r"<style>.*?</style>", "", fragment, flags=re.S)).strip()


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.sample = json.loads(comparison.SAMPLE.read_text(encoding="utf-8"))
        self.timestamp = int(time.time())

    def collection(self):
        collection = Collection(str(self.directory / "collection.anki2"))
        self.addCleanup(collection.close)
        return collection

    def import_package(self, collection, path):
        return collection.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(path), options=ImportAnkiPackageOptions(with_scheduling=False)))

    def build(self, mode="remote", sample=None, timestamp=None, clips=None, name=None):
        return comparison.build(self.sample if sample is None else sample, mode,
                                self.directory / (name or f"{mode}.apkg"), clips,
                                self.timestamp if timestamp is None else timestamp)

    def test_remote_has_ten_blind_players_and_no_embedded_media(self):
        path = self.build()
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(json.loads(archive.read("media")), {})
        collection = self.collection()
        self.import_package(collection, path)
        self.assertEqual(collection.note_count(), 10)
        self.assertEqual(collection.card_count(), 10)
        for card_id in collection.find_cards(""):
            card = collection.get_card(card_id)
            question = card.question()
            self.assertEqual(visible_text(question), "")
            self.assertEqual(question.count("<audio "), 1)
            self.assertIn('preload="none"', question)
            self.assertNotIn("autoplay", question)
            self.assertNotIn("<script", question)
            self.assertEqual(card.question_av_tags(), [])
            for field in ("Artist", "Title", "Year", "Album"):
                self.assertIn(card.note()[field], card.answer())

    def test_comparison_packages_coexist_with_original_and_deduplicate_media(self):
        # Synthetic clip tests packaging only; real M4A decoding is checked separately.
        sample = copy.deepcopy(self.sample)
        audio = self.directory / "neutral.wav"
        audio.write_bytes(demo_audio())
        for track in sample["tracks"]:
            track.pop("preview_sha256", None)
        clips = {track["sample_id"]: audio for track in sample["tracks"]}
        native = self.build("native", sample=sample, clips=clips)
        with zipfile.ZipFile(native) as archive:
            self.assertEqual(len(json.loads(archive.read("media"))), 1)
        collection = self.collection()
        original = self.directory / "original.apkg"
        build_original(original, timestamp=self.timestamp)
        self.import_package(collection, original)
        self.import_package(collection, native)
        self.import_package(collection, self.build())
        self.assertEqual(collection.card_count(), 21)
        self.assertEqual(len(collection.models.get(MODEL_ID)["flds"]), 6)
        report = collection.media.check()
        self.assertEqual(list(report.missing), [])
        self.assertEqual(list(report.unused), [])

    def test_remote_correction_and_url_refresh_preserve_review_history(self):
        collection = self.collection()
        self.import_package(collection, self.build())
        card = collection.get_card(collection.find_cards("")[0])
        card.start_timer()
        collection.sched.answerCard(card, 3)
        before = collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id")
        history = collection.db.all("select * from revlog")
        revised = copy.deepcopy(self.sample)
        for track in revised["tracks"]:
            track["title"] += " (corrected)"
            track["preview_url"] = "https://audio-ssl.itunes.apple.com/updated.m4a"
        path = self.build(sample=revised, timestamp=self.timestamp + 10, name="updated.apkg")
        self.assertEqual(len(self.import_package(collection, path).log.updated), 10)
        self.assertEqual(collection.card_count(), 10)
        self.assertEqual(collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left from cards order by id"), before)
        self.assertEqual(collection.db.all("select * from revlog"), history)
        self.assertIn("corrected", collection.get_card(card.id).answer())
        self.import_package(collection, path)
        self.assertEqual(collection.card_count(), 10)

    def test_optional_album_is_escaped_and_omitted_when_empty(self):
        sample = copy.deepcopy(self.sample)
        sample["tracks"][0]["album"] = "<script>bad()</script>"
        sample["tracks"][1]["album"] = ""
        collection = self.collection()
        self.import_package(collection, self.build(sample=sample))
        answers = {collection.get_card(i).note()["SampleID"]: collection.get_card(i).answer()
                   for i in collection.find_cards("")}
        self.assertNotIn("<script>", answers[sample["tracks"][0]["sample_id"]])
        self.assertIn("&lt;script&gt;", answers[sample["tracks"][0]["sample_id"]])
        self.assertNotIn('class="album"', answers[sample["tracks"][1]["sample_id"]])

    def test_invalid_urls_duplicates_and_sample_sizes_are_rejected(self):
        for bad in ("http://audio-ssl.itunes.apple.com/a.m4a", "https://example.com/a.m4a",
                    "https://audio-ssl.itunes.apple.com/a.m4a?token=secret", "javascript:alert(1)"):
            with self.subTest(url=bad), self.assertRaises(ValueError):
                comparison.validate_preview_url(bad)
        for key, value in (("sample_id", "bad id"), ("year", True), ("album", "bad\x1fvalue")):
            invalid = copy.deepcopy(self.sample)
            invalid["tracks"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                comparison.validate_sample(invalid)
        for invalid in ({"tracks": self.sample["tracks"][:9]},
                        {"tracks": [self.sample["tracks"][0]] * 10}):
            with self.assertRaises(ValueError):
                comparison.validate_sample(invalid)

    def test_refresh_uses_pinned_ids_and_does_not_rewrite_answers(self):
        results = [{"kind": "song", "trackId": track["apple_track_id"],
                    "artistName": track["provider_artist"], "trackName": track["provider_title"],
                    "previewUrl": "https://audio-ssl.itunes.apple.com/refreshed.m4a"}
                   for track in self.sample["tracks"]]
        with patch("refresh_sample_previews.urlopen", return_value=io.BytesIO(json.dumps({"results": results}).encode())) as request:
            updated = refresh(self.sample)
        self.assertIn("/lookup?", request.call_args.args[0])
        self.assertNotIn("/search?", request.call_args.args[0])
        for before, after in zip(self.sample["tracks"], updated["tracks"]):
            for field in ("sample_id", "artist", "title", "year", "album", "apple_track_id"):
                self.assertEqual(before[field], after[field])
            self.assertNotIn("preview_sha256", after)

    def test_hitify_table_extraction_is_bounded_and_decodes_entities(self):
        sample = copy.deepcopy(self.sample)
        sample["tracks"][0]["artist"] = "A & B"
        source = "<table><tr><th>No.</th><th>Artist</th><th>Title</th><th>Year</th></tr>"
        for track in sample["tracks"]:
            source += "<tr>" + "".join(f"<td>{html.escape(str(track[k]))}</td>" for k in ("card_number", "artist", "title", "year")) + "</tr>"
        source += "<tr><td>11</td><td>A &amp; B</td><td>Excluded</td><td>2000</td></tr></table>"
        self.assertEqual(extract_rows(source), [{k: track[k] for k in ("card_number", "artist", "title", "year")} for track in sample["tracks"]])
        with self.assertRaises(ValueError):
            extract_rows("<table></table>")


if __name__ == "__main__":
    unittest.main()
