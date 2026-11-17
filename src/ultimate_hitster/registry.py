"""Discover available editions without importing their songs."""
from html.parser import HTMLParser
import hashlib
import re
from urllib.parse import urljoin, urlsplit

INDEX_URL = "https://hitify.app/en/hitster-editions"
# Market languages, not the language sung on every recording. Unknown stays und.
MARKETS = {
    "United States": ("US", ["en"]), "United Kingdom": ("GB", ["en"]),
    "Australia": ("AU", ["en"]), "Canada": ("CA", ["en", "fr"]),
    "New Zealand": ("NZ", ["en"]), "International": ("INT", ["und"]),
    "Argentina": ("AR", ["es"]), "Baltics": ("BALTICS", ["et", "lv", "lt"]),
    "Belgium": ("BE", ["fr", "nl"]), "Benelux": ("BENELUX", ["nl"]),
    "Brazil": ("BR", ["pt"]), "Chile": ("CL", ["es"]), "Croatia": ("HR", ["hr"]),
    "Czechia and Slovakia": ("CZ-SK", ["cs", "sk"]), "France": ("FR", ["fr"]),
    "Germany": ("DE", ["de"]), "Greece": ("GR", ["el"]),
    "Hong Kong": ("HK", ["zh"]), "Hungary": ("HU", ["hu"]),
    "Iceland": ("IS", ["is"]), "Israel": ("IL", ["he"]), "Italy": ("IT", ["it"]),
    "Japan": ("JP", ["ja"]), "Lebanon": ("LB", ["ar", "en"]),
    "Mexico": ("MX", ["es"]), "Netherlands": ("NL", ["nl"]),
    "Nordics": ("NORDICS", ["da", "fi", "no", "sv"]),
    "Peru": ("PE", ["es"]), "Philippines": ("PH", ["en"]),
    "Poland": ("PL", ["pl"]), "Portugal": ("PT", ["pt"]), "Romania": ("RO", ["ro"]),
    "South Korea": ("KR", ["ko"]), "Spain": ("ES", ["es"]),
    "Sweden": ("SE", ["sv"]), "Switzerland": ("CH", ["de", "fr", "it"]),
    "Taiwan": ("TW", ["zh"]),
}


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = None
        self.region = None
        self.anchor = None
        self.entries = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3":
            self.heading = []
        if tag == "a" and "ed-tile" in attrs.get("class", "").split():
            self.anchor = [attrs.get("href", ""), [], self.region]

    def handle_data(self, value):
        if self.heading is not None:
            self.heading.append(value)
        if self.anchor is not None:
            self.anchor[1].append(value)

    def handle_endtag(self, tag):
        if tag == "h3" and self.heading is not None:
            self.region = " ".join("".join(self.heading).split())
            self.heading = None
        if tag == "a" and self.anchor is not None:
            self.entries.append(self.anchor)
            self.anchor = None


def discover(source, imported=()):
    parser = IndexParser()
    parser.feed(source)
    imported = set(imported)
    result, seen = [], set()
    digest = hashlib.sha256(source.encode()).hexdigest()
    for href, fragments, market in parser.entries:
        url = urljoin(INDEX_URL, href)
        if urlsplit(url).netloc != "hitify.app" or not urlsplit(url).path.startswith("/en/hitster-editions/"):
            raise ValueError("Unexpected edition source")
        slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        if slug in seen:
            continue
        seen.add(slug)
        text = " ".join(" ".join(fragments).split())
        match = re.fullmatch(r"(Hitster .+?) (\d+) cards(?: (Expansion))?", text)
        if not match or not market:
            raise ValueError("Hitify index structure changed: " + text)
        name, count, expansion = match.groups()
        family = re.sub(r"\s*\([^)]*\)", "", name.removeprefix("Hitster "))
        family = re.sub(r"\s+Refresh$", "", family)
        revision = ("refresh" if "Refresh" in name else
                    "second-edition" if "2nd Edition" in name else
                    "amazon" if "Amazon Edition" in name else
                    "kickstarter" if "Kickstarter" in name else "unspecified")
        region, languages = MARKETS.get(market, (slugify(market).upper(), ["und"]))
        edition_id = "hitster-" + slug
        result.append({"edition_id": edition_id, "slug": slug, "name": name,
                       "market": market, "region": region, "languages": languages,
                       "language_basis": "market inference; song languages are not inferred",
                       "family": slugify(family), "revision": revision,
                       "format": "expansion" if expansion else "standalone",
                       "card_count": int(count), "status": "imported" if edition_id in imported else "available",
                       "sources": [{"url": url, "index_url": INDEX_URL, "index_sha256": digest}]})
    if not result:
        raise ValueError("No edition tiles found; do not replace the registry with an empty response")
    return {"schema_version": 1, "editions": sorted(result, key=lambda e: (e["market"], e["family"], e["slug"]))}


def select_editions(catalogue, config):
    known = {e["edition_id"]: e for e in catalogue["editions"]}
    selectors = [key for key in ("edition_ids", "countries", "families", "all") if config.get(key)]
    if len(selectors) != 1:
        raise ValueError("Use exactly one of edition_ids, countries, families or all")
    key = selectors[0]
    if key == "edition_ids":
        result = set(config[key])
        if result - known.keys():
            raise ValueError("Selection includes an edition that has not been imported")
    elif key == "all":
        if config[key] is not True:
            raise ValueError("all must be true")
        result = set(known)
    else:
        field = "region" if key == "countries" else "family"
        requested = set(config[key])
        available = {e.get(field) for e in known.values()}
        if requested - available:
            raise ValueError("Selection includes an unknown country or family")
        result = {eid for eid, e in known.items() if e.get(field) in requested}
    if not result:
        raise ValueError("Selection contains no imported editions")
    return sorted(result)
