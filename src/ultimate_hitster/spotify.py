"""Read exact public Spotify recording references; never search or substitute."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_PAGE = 2_000_000
MAX_AUDIO = 10_000_000


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(url, limit=MAX_PAGE):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "UltimateHitster/0.3 (+https://github.com/OpenDecksLibrary/ultimate-hitster)"}), timeout=25) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Response exceeds the size limit")
            return data
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            retry = error.headers.get("Retry-After", "")
            time.sleep(min(int(retry), 60) if retry.isdigit() else 2 ** (attempt + 1))
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9]{22}", value) is not None


def valid_preview(url):
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.netloc == "p.scdn.co"
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r"/mp3-preview/[0-9a-f]{40}", parsed.path) is not None)


def entity_from_html(page):
    if isinstance(page, bytes):
        page = page.decode("utf-8")
    match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("Public embed structure changed")
    return json.loads(match.group(1))["props"]["pageProps"]["state"]["data"]["entity"]


def parse_recording(page, expected_id):
    entity = entity_from_html(page)
    resolved_id = entity.get("id") or entity.get("uri", "").rsplit(":", 1)[-1]
    if entity.get("type") != "track" or resolved_id != expected_id:
        raise ValueError("Provider resolved a different recording; substitution rejected")
    artists = [artist["name"] for artist in entity.get("artists", [])]
    if not entity.get("title") or not artists:
        raise ValueError("Provider title or artist is absent")
    preview = (entity.get("audioPreview") or {}).get("url")
    if preview and not valid_preview(preview):
        raise ValueError("Provider returned an unapproved or non-MP3 preview URL")
    return {"spotify_id": expected_id, "title": entity["title"], "artists": artists,
            "duration_ms": entity.get("duration"),
            "release_date": (entity.get("releaseDate") or {}).get("isoString"),
            "album": entity.get("albumName") or None,
            "preview_url": preview, "status": "available" if preview else "missing_preview",
            "checked_at": now(), "source_url": f"https://open.spotify.com/embed/track/{expected_id}"}


def resolve_recordings(ids, directory, refresh=False, workers=3, progress=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    def resolve(track_id):
        if not valid_id(track_id):
            raise ValueError("Invalid Spotify reference")
        path = directory / f"{track_id}.json"
        if path.exists() and not refresh:
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            result = parse_recording(fetch(f"https://open.spotify.com/embed/track/{track_id}"), track_id)
        except (OSError, ValueError, KeyError) as error:
            result = {"spotify_id": track_id, "status": "fetch_failed", "checked_at": now(),
                      "error": f"{type(error).__name__}: {error}"}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return result

    output = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, result in enumerate(pool.map(resolve, sorted(set(ids))), 1):
            output[result["spotify_id"]] = result
            if progress and (index % 25 == 0 or index == len(set(ids))):
                progress(index, len(set(ids)))
    return output


def check_clip(url, directory):
    """Fetch one exact URL, validate MP3 signatures and cache by content hash."""
    if not valid_preview(url):
        raise ValueError("Unapproved preview URL")
    data = fetch(url, MAX_AUDIO)
    if len(data) < 1024 or not (data.startswith(b"ID3") or (data[0] == 255 and data[1] & 224 == 224)):
        raise ValueError("Preview response is not an MP3 file")
    digest = hashlib.sha256(data).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"uh_{digest}.mp3"
    if not path.exists():
        path.write_bytes(data)
    return digest, path


class AlbumPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.album_url = self.track_url = None
        self.links = []
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property", attrs.get("name"))
            if key == "music:album":
                self.album_url = attrs.get("content")
            elif key == "og:url":
                self.track_url = attrs.get("content")
        elif tag == "a":
            self.link = [attrs.get("href", ""), []]

    def handle_data(self, text):
        if self.link is not None and text.strip():
            self.link[1].append(text.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.link is not None:
            self.links.append(self.link)
            self.link = None


def parse_album(page, expected_id):
    parser = AlbumPage()
    parser.feed(page.decode("utf-8") if isinstance(page, bytes) else page)
    if not parser.track_url or urlsplit(parser.track_url).path.rsplit("/", 1)[-1] != expected_id:
        raise ValueError("Album page does not identify the exact pinned track")
    album_id = (parser.album_url or "").rsplit("/", 1)[-1]
    if not valid_id(album_id):
        return None
    names = {parts[0] for href, parts in parser.links
             if urlsplit(href).path == f"/album/{album_id}" and parts}
    if len(names) != 1:
        return None
    return {"name": names.pop(), "spotify_id": album_id,
            "source_url": f"https://open.spotify.com/track/{expected_id}"}


def resolve_albums(ids, directory, workers=2, progress=None, refresh=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    def resolve(track_id):
        path = directory / f"{track_id}.json"
        if path.exists() and not refresh:
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            album = parse_album(fetch(f"https://open.spotify.com/track/{track_id}"), track_id)
            result = {"spotify_id": track_id, "album": album, "checked_at": now()}
        except (OSError, ValueError, KeyError) as error:
            result = {"spotify_id": track_id, "album": None, "error": f"{type(error).__name__}: {error}", "checked_at": now()}
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    output = {}
    unique = sorted(set(ids))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, result in enumerate(pool.map(resolve, unique), 1):
            output[result["spotify_id"]] = result
            if progress and (index % 25 == 0 or index == len(unique)):
                progress(index, len(unique))
    return output
