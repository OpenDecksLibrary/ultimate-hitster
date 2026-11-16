"""Release gates: prerelease-only plans and integrity of distributed bytes."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_release import ASSETS, release_plan, verify_checksums, write_checksums


class ReleaseTests(unittest.TestCase):
    def test_manifest_requires_prerelease_and_matching_notes(self):
        self.assertTrue(release_plan()["prerelease"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.json"
            for tag, prerelease, notes in (("v0.2.0", True, "docs/releases/v0.2.0-beta.1.md"),
                                            ("v0.2.0-beta.1", False, "docs/releases/v0.2.0-beta.1.md"),
                                            ("v0.2.0-beta.1", True, "../untrusted.md")):
                path.write_text(json.dumps({"tag": tag, "prerelease": prerelease, "notes": notes}))
                with self.assertRaises(ValueError):
                    release_plan(path)

    def test_checksums_detect_tampered_or_missing_assets_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            built, downloaded = root / "built", root / "downloaded"
            built.mkdir()
            downloaded.mkdir()
            for directory in (built, downloaded):
                for name in ASSETS:
                    (directory / name).write_bytes(name.encode())
                write_checksums(directory)
            verify_checksums(downloaded, built)
            (downloaded / ASSETS[0]).write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_checksums(downloaded, built)
            write_checksums(downloaded)
            with self.assertRaises(ValueError):
                verify_checksums(downloaded, built)
            (downloaded / ASSETS[1]).unlink()
            with self.assertRaises(FileNotFoundError):
                verify_checksums(downloaded)


if __name__ == "__main__":
    unittest.main()
