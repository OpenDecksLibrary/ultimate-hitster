"""Reports over imported editions and exact recording identities."""
from collections import Counter, defaultdict


def statistics(catalogue, registry=None):
    members = catalogue["memberships"]
    recordings = {t["recording_id"]: t for t in catalogue["recordings"]}
    used = {m["recording_id"] for m in members}
    studies = {m["study_id"] for m in members}
    editions = catalogue["editions"]
    years = defaultdict(set)
    occurrences = Counter(m["recording_id"] for m in members)
    for m in members:
        years[m["recording_id"]].add(m["catalogue_year"])
    return {
        "imported_editions": len(editions),
        "available_editions": len(registry["editions"]) if registry else None,
        "catalogue_cards": len(members), "unique_recordings": len(used),
        "unique_studies": len(studies),
        "duplicate_recording_occurrences": len(members) - len(used),
        "deduplicated_study_occurrences": len(members) - len(studies),
        "shared_recordings": sum(n > 1 for n in occurrences.values()),
        "conflicting_years": [{"recording_id": rid, "years": sorted(values)}
                              for rid, values in sorted(years.items()) if len(values) > 1],
        "reference_status": dict(Counter(m["reference"]["status"] for m in members)),
        "audio_status": dict(Counter(recordings[r]["audio"]["status"] for r in used)),
        "editions": [{"edition_id": e["edition_id"], "cards": e["card_count"],
                      "unique_recordings": len({m["recording_id"] for m in members if m["edition_id"] == e["edition_id"]}),
                      "shared_with_other_editions": len({m["recording_id"] for m in members if m["edition_id"] == e["edition_id"]} &
                          {m["recording_id"] for m in members if m["edition_id"] != e["edition_id"]})}
                     for e in sorted(editions, key=lambda e: e["edition_id"])],
        "issues": [{"edition_id": m["edition_id"], "card_number": m["card_number"],
                    "recording_id": m["recording_id"], "reference": m["reference"],
                    "audio_status": recordings[m["recording_id"]]["audio"]["status"]}
                   for m in members if m["reference"]["status"] not in ("verified", "reviewed") or
                   recordings[m["recording_id"]]["audio"]["status"] != "verified"],
    }
