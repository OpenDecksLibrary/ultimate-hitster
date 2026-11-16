"""Retrieve public release assets without authentication and compare their bytes."""

import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from prepare_release import ROOT, ASSETS, release_plan, verify_checksums


def main():
    tag = release_plan()["tag"]
    destination = ROOT / "build/public-download"
    destination.mkdir(parents=True, exist_ok=True)
    for name in [*ASSETS, "SHA256SUMS"]:
        url = f"https://github.com/OpenDecksLibrary/ultimate-hitster/releases/download/{tag}/{name}"
        for attempt in range(4):
            try:
                with urlopen(Request(url, headers={"User-Agent": "UltimateHitster-release-check"}), timeout=60) as response:
                    with (destination / name).open("wb") as output:
                        while block := response.read(1024 * 1024):
                            output.write(block)
                break
            except HTTPError as error:
                if error.code not in (404, 429, 500, 502, 503) or attempt == 3:
                    raise
                time.sleep(min(int(error.headers.get("Retry-After", "5")), 30))
        print(f"Downloaded {name}", flush=True)
    verify_checksums(destination, ROOT / "dist")
    print("Public downloads match every locally generated SHA-256 checksum")


if __name__ == "__main__":
    main()
