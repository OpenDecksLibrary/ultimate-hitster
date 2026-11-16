"""Public reference adapters fail closed on ambiguity and metadata conflicts."""
import unittest
from ultimate_hitster.sources import public_references
from ultimate_hitster.catalogue import import_edition
from test_production import fixture, empty


class SourceTests(unittest.TestCase):
    def source(self):
        rows, _, _, _ = fixture(count=1)
        songs = {"1": {"title": "Song", "artistName": "Artist", "releaseDate": "2009",
                       "providers": {"spotify": {"FR": "https://open.spotify.com/track/" + "A" * 22}}}}
        return rows, {"songs": songs}

    def test_exact_card_reference_and_provenance_not_provider_year(self):
        rows, source = self.source()
        refs, issues = public_references(source, rows, "https://source.example/edition.json", "FR")
        self.assertEqual(issues, [])
        self.assertEqual(refs["1"]["spotify_track_id"], "A" * 22)
        self.assertEqual(refs["1"]["source_release_date"], "2009")
        self.assertEqual(rows[0]["year"], 1980)

    def test_missing_or_territory_ambiguous_reference_is_unresolved(self):
        rows, source = self.source()
        source["songs"]["1"]["providers"]["spotify"]["BE"] = "https://open.spotify.com/track/" + "B" * 22
        refs, issues = public_references(source, rows, "https://source.example/edition.json")
        self.assertIsNone(refs["1"]["spotify_track_id"])
        self.assertEqual(issues[0]["reason"], "missing_or_ambiguous_reference")
        refs, issues = public_references(source, rows, "https://source.example/edition.json", "FR")
        self.assertEqual(refs["1"]["spotify_track_id"], "A" * 22)

    def test_source_version_disagreement_is_not_silently_normalized(self):
        rows, source = self.source()
        source["songs"]["1"]["title"] = "Song - Live"
        refs, issues = public_references(source, rows, "https://source.example/edition.json", "FR")
        self.assertEqual(refs["1"]["spotify_track_id"], "A" * 22)
        self.assertEqual(issues[0]["reason"], "source_metadata_mismatch")

    def test_card_gaps_extra_cards_and_non_spotify_hosts_are_rejected(self):
        rows, source = self.source()
        for change in ("missing", "extra", "url"):
            _, bad = self.source()
            if change == "missing":
                bad["songs"].clear()
            elif change == "extra":
                bad["songs"]["2"] = bad["songs"]["1"]
            else:
                bad["songs"]["1"]["providers"]["spotify"]["FR"] = "https://example.com/track/" + "A" * 22
            with self.assertRaises(ValueError):
                public_references(bad, rows, "https://source.example/edition.json")

    def test_url_refresh_keeps_source_conflicts_and_provenance(self):
        rows, refs, edition, meta = fixture(count=1)
        refs["1"].update(source_checks={"title": False, "artist": True},
                         source_markets=["FR"], source_url="https://source.example/edition.json#card-1")
        c = import_edition(empty(), rows, refs, edition, meta)
        self.assertEqual(c["memberships"][0]["reference"]["status"], "source_conflict")
        self.assertEqual(c["recordings"][0]["audio"]["status"], "unavailable")
        meta["A" * 22]["preview_url"] = "https://p.scdn.co/mp3-preview/" + "9" * 40
        updated = import_edition(c, rows, refs, edition, meta)
        self.assertEqual(updated["memberships"][0]["reference"]["status"], "source_conflict")
        self.assertEqual(updated["memberships"][0]["study_id"], c["memberships"][0]["study_id"])
        self.assertEqual(updated["memberships"][0]["reference"]["source_checks"], refs["1"]["source_checks"])
        refs["1"].update(source_checks={"title": True, "artist": True}, playlist_conflict=True)
        self.assertEqual(import_edition(empty(), rows, refs, edition, meta)["memberships"][0]["reference"]["status"], "source_conflict")

    def test_shared_player_does_not_change_with_selected_edition_label_conflict(self):
        from ultimate_hitster.build import selected_notes
        from test_production import make
        catalogue = make(count=1)
        rows, refs, edition, meta = fixture(count=1)
        rows[0]["title"] = "Song (uncertain catalogue label)"
        catalogue = import_edition(catalogue, rows, refs, dict(edition, edition_id="second-edition"), meta)
        self.assertEqual(catalogue["memberships"][-1]["reference"]["status"], "metadata_mismatch")
        first = selected_notes(catalogue, ["test-fr"])
        second = selected_notes(catalogue, ["second-edition"])
        self.assertEqual(set(first), set(second))
        self.assertTrue(next(iter(first.values()))["verified_reference"])
        self.assertTrue(next(iter(second.values()))["verified_reference"])

    def test_secondary_edition_reimport_preserves_canonical_recording_label(self):
        rows, refs, edition, meta = fixture(count=1)
        catalogue = import_edition(empty(), rows, refs, edition, meta)
        secondary = dict(edition, edition_id="second-edition")
        catalogue = import_edition(catalogue, rows, refs, secondary, meta)
        rows[0]["title"] = "Song (secondary spelling)"
        catalogue = import_edition(catalogue, rows, refs, secondary, meta)
        self.assertEqual(catalogue["recordings"][0]["title"], "Song")
        self.assertEqual(catalogue["memberships"][-1]["catalogue_title"], "Song (secondary spelling)")


if __name__ == "__main__":
    unittest.main()
