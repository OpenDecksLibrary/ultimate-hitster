"""Exercise APKG packaging and real Anki imports in disposable collections."""

import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
import zipfile

from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from build import DECK_ID, MODEL_ID, build, demo_audio, note_guid, validate_fixture


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.fixture = json.loads((ROOT / "prototype/sample.json").read_text())
        self.timestamp = int(time.time())

    def package(self, name="test.apkg", fixture=None, audio=None, timestamp=None):
        path = self.directory / name
        build(path, fixture or self.fixture, audio, self.timestamp if timestamp is None else timestamp)
        return path

    def collection(self):
        collection = Collection(str(self.directory / "collection.anki2"))
        self.addCleanup(collection.close)
        return collection

    def import_package(self, collection, path):
        return collection.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(path), options=ImportAnkiPackageOptions(with_scheduling=False)))

    def test_package_contains_exactly_one_note_card_and_audio_file(self):
        path = self.package()
        with zipfile.ZipFile(path) as package:
            media = json.loads(package.read("media"))
            self.assertEqual(len(media), 1)
            name = next(iter(media.values()))
            self.assertEqual(name, "uh_" + hashlib.sha256(demo_audio()).hexdigest() + ".wav")
            self.assertEqual(package.read(next(iter(media))), demo_audio())
            database = self.directory / "inspect.db"
            database.write_bytes(package.read("collection.anki2"))
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute("select count(*) from notes").fetchone()[0], 1)
            self.assertEqual(connection.execute("select count(*) from cards").fetchone()[0], 1)
            self.assertEqual(connection.execute("select mid from notes").fetchone()[0], MODEL_ID)
            self.assertEqual(connection.execute("select did from cards").fetchone()[0], DECK_ID)
            self.assertEqual(connection.execute("select count(*) from revlog").fetchone()[0], 0)

    def test_anki_import_renders_hidden_question_and_visible_answer(self):
        collection = self.collection()
        self.import_package(collection, self.package())
        card = collection.get_card(collection.find_cards("")[0])
        question, answer = card.question(), card.answer()
        for field in ("artist", "title", "game_year"):
            self.assertNotIn(str(self.fixture[field]), question)
            self.assertIn(str(self.fixture[field]), answer)
        for forbidden in ("iframe", "<script", "https://", "<audio"):
            self.assertNotIn(forbidden, question.lower())
        tags = card.question_av_tags()
        self.assertEqual(len(tags), 1)
        self.assertTrue((Path(collection.media.dir()) / tags[0].filename).is_file())
        # FrontSide keeps a replay control but does not autoplay again on answer.
        self.assertEqual(len(card.answer_av_tags()), 0)
        report = collection.media.check()
        self.assertEqual(list(report.missing), [])
        self.assertEqual(list(report.unused), [])

    def test_reimport_updates_metadata_and_preserves_actual_review(self):
        collection = self.collection()
        first = self.package("v1.apkg")
        self.import_package(collection, first)
        card_id = collection.find_cards("")[0]
        card = collection.get_card(card_id)
        note_id = card.nid
        card.start_timer()
        collection.sched.answerCard(card, 3)
        scheduling = collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left,odue,odid from cards")
        history = collection.db.all("select * from revlog")
        self.assertEqual(len(history), 1)
        updated = dict(self.fixture, title="Corrected demonstration title", game_year=2025)
        second = self.package("v2.apkg", updated, timestamp=self.timestamp + 10)
        result = self.import_package(collection, second)
        self.assertEqual(len(result.log.updated), 1)
        self.assertEqual(collection.find_cards(""), [card_id])
        self.assertEqual(collection.find_notes(""), [note_id])
        self.assertEqual(collection.get_note(note_id)["Title"], updated["title"])
        self.assertEqual(collection.get_note(note_id)["GameYear"], "2025")
        self.assertEqual(collection.db.all("select id,nid,type,queue,due,ivl,factor,reps,lapses,left,odue,odid from cards"), scheduling)
        self.assertEqual(collection.db.all("select * from revlog"), history)
        self.import_package(collection, second)
        self.assertEqual(collection.note_count(), 1)
        self.assertEqual(collection.card_count(), 1)

    def test_guid_is_independent_of_metadata_and_audio(self):
        original = build(self.directory / "first.apkg", self.fixture)
        custom = self.directory / "Artist - Revealing title.wav"
        custom.write_bytes(demo_audio() + b"different bytes")
        revised = build(self.directory / "second.apkg", dict(self.fixture, artist="Someone else"), custom)
        self.assertEqual(original["guid"], revised["guid"])
        self.assertNotEqual(original["media"], revised["media"])
        self.assertNotIn("Artist", revised["media"])
        self.assertNotEqual(note_guid("different-study"), original["guid"])

    def test_field_html_is_escaped(self):
        collection = self.collection()
        fixture = dict(self.fixture, title='<script>alert("answer")</script>', artist="A & B")
        self.import_package(collection, self.package(fixture=fixture))
        card = collection.get_card(collection.find_cards("")[0])
        self.assertNotIn("<script>", card.answer())
        self.assertIn("&lt;script&gt;", card.answer())
        self.assertIn("A &amp; B", card.answer())

    def test_invalid_fixture_or_missing_media_fails_before_packaging(self):
        for changes in ({"study_id": "../../escape"}, {"title": ""}, {"game_year": True},
                        {"game_year": "2026"}, {"artist": "bad\x1fvalue"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_fixture(dict(self.fixture, **changes))
        with self.assertRaises(FileNotFoundError):
            self.package(audio=self.directory / "missing.mp3")
        empty = self.directory / "empty.mp3"
        empty.touch()
        with self.assertRaises(ValueError):
            self.package(audio=empty)


if __name__ == "__main__":
    unittest.main()
