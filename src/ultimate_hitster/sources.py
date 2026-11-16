"""Adapters for explicit, public, per-card recording reference snapshots."""
import re
from urllib.parse import urlsplit

from .catalogue import normalized, artists_match
from .spotify import valid_id, entity_from_html


def public_references(data, rows, source_url, market=None):
    """Accept only an exact card lookup and a single, unambiguous Spotify ID.

    Alternate providers are retained by the upstream source, never substituted
    for the pinned Spotify recording here. Conflicts remain explicit issues.
    """
    songs = data.get("songs")
    if not isinstance(songs, dict):
        raise ValueError("Reference source has no per-card songs map")
    wanted = {row["card_number"] for row in rows}
    if set(songs) != wanted:
        raise ValueError("Reference source card numbers differ from the Hitify catalogue")
    refs, issues = {}, []
    for row in rows:
        number = row["card_number"]
        song = songs[number]
        urls = song.get("providers", {}).get("spotify", {})
        selected = {market: urls[market]} if market in urls else urls
        ids = set()
        for url in selected.values():
            parsed = urlsplit(url)
            match = re.fullmatch(r"/track/([A-Za-z0-9]{22})", parsed.path)
            if parsed.scheme != "https" or parsed.netloc != "open.spotify.com" or not match:
                raise ValueError("Invalid source Spotify track URL")
            ids.add(match.group(1))
        matches = {
            "title": normalized(row["title"]) == normalized(song.get("title", "")),
            "artist": artists_match(row["artist"], song.get("artistName", "").split(";")),
        }
        provider = next(iter(ids)) if len(ids) == 1 else None
        refs[number] = {"spotify_track_id": provider, "source_url": source_url + "#card-" + number,
                        "source_markets": sorted(selected), "source_title": song.get("title"),
                        "source_artist": song.get("artistName"), "source_release_date": song.get("releaseDate"),
                        "source_checks": matches}
        if provider is None or not all(matches.values()):
            issues.append({"card_number": number, "reason": "missing_or_ambiguous_reference" if provider is None else "source_metadata_mismatch",
                           "source_checks": matches})
    return refs, issues


def playlist_ids(page):
    entity = entity_from_html(page)
    if entity.get("type") != "playlist":
        raise ValueError("Expected a public playlist embed")
    result = []
    for track in entity.get("trackList", []):
        provider = track.get("uri", "").removeprefix("spotify:track:")
        if not valid_id(provider):
            raise ValueError("Missing exact recording in playlist embed")
        result.append(provider)
    if not result:
        raise ValueError("Public playlist exposes no exact track references")
    return result
