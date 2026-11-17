"""Apply two explicitly bound credit reviews and keep all remaining exceptions."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ultimate_hitster.catalogue import load, save, import_edition, parse_hitify, write_json, source_digest
from ultimate_hitster.build import verify_audio
from ultimate_hitster.selections import statistics

def run():
    catalogue=load(ROOT/"data")
    before={(m["edition_id"],m["card_number"]):(m["membership_id"],m["recording_id"],m["study_id"],m["catalogue_year"]) for m in catalogue["memberships"]}
    recheck=json.loads((ROOT/"data/reports/v0.3-exception-recheck.json").read_text())
    fresh={r["fresh"]["spotify_id"]:r["fresh"] for r in recheck["records"]}
    metadata={p:{**t["provider_metadata"],"preview_url":t["audio"].get("url")}
              for t in catalogue["recordings"] for p in t["providers"]["spotify"]}
    metadata.update(fresh)
    edition=next(e for e in catalogue["editions"] if e["edition_id"]=="hitster-guilty-pleasures-france")
    review_path=ROOT/"data/sources/guilty-pleasures-france.reviews.json"
    reviews=json.loads(review_path.read_text())
    rows=parse_hitify((ROOT/"data/sources/guilty-pleasures-france.hitify.html").read_text(),edition["card_count"])
    refs=json.loads((ROOT/"data/sources/guilty-pleasures-france.references.json").read_text())
    edition["credit_reviews"]={"snapshot":review_path.name,"sha256":source_digest(review_path)}
    catalogue=import_edition(catalogue,rows,refs,edition,metadata,reviews=reviews)
    verify_audio(catalogue,ROOT/"build/media",progress=lambda a,b:print(f"Audio {a}/{b}",flush=True))
    after={(m["edition_id"],m["card_number"]):(m["membership_id"],m["recording_id"],m["study_id"],m["catalogue_year"]) for m in catalogue["memberships"]}
    if before!=after:raise ValueError("Exception review changed frozen identities or years")
    save(ROOT/"data",catalogue)
    stats=statistics(catalogue,json.loads((ROOT/"data/registry.json").read_text()))
    write_json(ROOT/"data/reports/catalogue.json",stats)
    print("RESOLVED CREDIT REVIEWS",sorted(reviews))
    print("AUDIO STATUS",stats["audio_status"])

if __name__=="__main__":run()
