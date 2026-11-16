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
