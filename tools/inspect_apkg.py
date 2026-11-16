"""Inspect legacy Anki packages without importing them or executing templates."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile


def inspect_package(path):
    path = Path(path)
    with zipfile.ZipFile(path) as package:
        # Prefer the real collection over the compatibility warning in anki2.
        if "collection.anki21b" in package.namelist():
            raise ValueError("Modern compressed collections need Anki's importer; do not inspect the fallback DB")
        member = "collection.anki21" if "collection.anki21" in package.namelist() else "collection.anki2"
        if package.getinfo(member).file_size > 100_000_000:
            raise ValueError("Collection exceeds the inspection size limit")
        media = json.loads(package.read("media"))
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "collection.db"
            database.write_bytes(package.read(member))
            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            try:
                models = json.loads(connection.execute("select models from col").fetchone()[0])
                notes = connection.execute("select mid, flds from notes").fetchall()
                sounds = sorted({name for _, fields in notes for name in re.findall(r"\[sound:([^\]]+)\]", fields)})
                spotify = []
                for model_id, fields in notes:
                    names = [field["name"] for field in models[str(model_id)]["flds"]]
                    if "SpotifyID" in names:
                        spotify.append(fields.split("\x1f")[names.index("SpotifyID")])
                result = {
                    "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "collection": member, "notes": len(notes),
                    "cards": connection.execute("select count(*) from cards").fetchone()[0],
                    "media_entries": len(media),
                    "missing_media_members": sorted(key for key in media if key not in package.namelist()),
                    "unique_sound_references": len(sounds),
                    "missing_sound_files": sorted(set(sounds) - set(media.values())),
                    "spotify_ids": len([value for value in spotify if re.fullmatch(r"[A-Za-z0-9]{22}", value)]),
                    "models": list(models.values()),
                }
            finally:
                connection.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps([inspect_package(path) for path in args.packages], indent=2, ensure_ascii=False))
    except (ValueError, OSError, zipfile.BadZipFile, sqlite3.Error) as error:
        parser.exit(2, f"Error: {error}\n")
