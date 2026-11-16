"""Extract at most ten card rows from a locally saved Hitify edition HTML page."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path


class EditionRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cells, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.cells = []
        elif tag == "td" and self.cells is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.cells.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.cells is not None:
            if len(self.rows) < 10 and len(self.cells) == 4 and self.cells[0].isdigit() and self.cells[3].isdigit():
                self.rows.append(dict(zip(("card_number", "artist", "title", "year"), self.cells)))
            self.cells = None


def extract_rows(source):
    parser = EditionRows()
    parser.feed(source)
    rows = parser.rows[:10]
    if len(rows) != 10 or [row["card_number"] for row in rows] != [str(n) for n in range(1, 11)]:
        raise ValueError("Expected the first ten numbered card rows; check the source structure")
    for row in rows:
        row["year"] = int(row["year"])
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract_rows(args.html.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
