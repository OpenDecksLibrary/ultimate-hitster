"""Bounded recheck of the twelve original exceptions and Anki suspension import."""
import inspect
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from ultimate_hitster.catalogue import load, write_json
from ultimate_hitster.spotify import resolve_recordings, now
from ultimate_hitster.build import build_package
from test_production import make
from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest
import genanki.card

def run():
    catalogue=load(ROOT/"data")
    tracks=[t for t in catalogue["recordings"] if t["audio"]["status"]!="verified"]
    ids=[p for t in tracks for p in t["providers"]["spotify"]]
    meta=resolve_recordings(ids,ROOT/"build/recheck-cache",refresh=True,workers=2)
    result={"checked_at":now(),"records":[{"recording_id":t["recording_id"],"catalogue_artist":t["artist"],
        "catalogue_title":t["title"],"previous_reason":t["audio"].get("reason"),
        "fresh":meta[t["providers"]["spotify"][0]]} for t in tracks]}
    write_json(ROOT/"data/reports/v0.3-exception-recheck.json",result)
    print("RECHECK",json.dumps(result,ensure_ascii=False))
    print("GENANKI CARD",inspect.getsource(genanki.card.Card))
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        original=root/"original.apkg"
        build_package(make(),{"edition_ids":["test-fr"],"deck_id":1735079101,"deck_name":"Suspension probe"},
                      "online",original,root,timestamp=2000000000)
        patched=root/"suspended.apkg"
        with zipfile.ZipFile(original) as source:
            db=root/"collection.anki2"
            db.write_bytes(source.read("collection.anki2"))
            con=sqlite3.connect(db)
            con.execute("update cards set queue=-1")
            con.commit()
            con.close()
            with zipfile.ZipFile(patched,"w",compression=zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    target.writestr(name,db.read_bytes() if name=="collection.anki2" else source.read(name))
        for scheduling in (False,True):
            col=Collection(str(root/f"test-{scheduling}.anki2"))
            try:
                col.import_anki_package(ImportAnkiPackageRequest(package_path=str(patched),options=ImportAnkiPackageOptions(with_scheduling=scheduling)))
                print("SUSPEND NEW",scheduling,col.db.all("select queue,type from cards"))
            finally: col.close()

if __name__=="__main__":run()
