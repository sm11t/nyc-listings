"""
Parse all listings/*.md frontmatter into web/data/listings.json.

No external dependencies — handcoded YAML subset (we control the schema).
Run from repo root:  python scripts/build_data.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_DIR = ROOT / "listings"
OUT_FILE = ROOT / "web" / "data" / "listings.json"

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_scalar(v: str):
    v = v.strip()
    if v == "" or v.lower() == "null":
        return None
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    # quoted string
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    # int
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    # float
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def parse_frontmatter(text: str) -> dict:
    """Tiny YAML parser sufficient for our schema: scalars + simple list-of-scalars."""
    data: dict = {}
    current_key: str | None = None
    current_list: list | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip():
            current_key = None
            current_list = None
            continue

        # list item belonging to current key
        if raw_line.startswith("  - ") and current_list is not None:
            current_list.append(parse_scalar(raw_line[4:]))
            continue

        m = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$", raw_line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)

        if value == "":
            # opens a list (or nested mapping — we only support lists)
            data[key] = []
            current_key = key
            current_list = data[key]
        else:
            data[key] = parse_scalar(value)
            current_key = None
            current_list = None

    return data


def parse_rooms_from_body(body: str) -> list[dict]:
    """Extract per-room rows from a markdown table inside the body, if present.

    Looks for tables whose header includes 'Room' and 'Price/mo'. Returns a
    list of {room, price, phone, hours, avail, notes} dicts. Empty if none.
    """
    rooms: list[dict] = []
    lines = body.splitlines()
    in_table = False
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not in_table:
            lower = [c.lower() for c in cells]
            if "room" in lower and any("price" in c for c in lower):
                in_table = True
                header = lower
                continue
            else:
                continue
        # separator row
        if all(re.fullmatch(r":?-+:?", c or "") for c in cells if c):
            continue
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        rooms.append(
            {
                "room": row.get("room"),
                "price": row.get("price/mo") or row.get("price"),
                "phone": row.get("phone"),
                "hours": row.get("hours"),
                "avail": row.get("avail"),
                "notes": row.get("notes"),
            }
        )
    return rooms


def slug_from_path(p: Path) -> str:
    return p.stem


def build():
    listings = []
    for md in sorted(LISTINGS_DIR.glob("2026-*.md")):
        text = md.read_text(encoding="utf-8")
        m = FRONT_RE.match(text)
        if not m:
            print(f"skip (no frontmatter): {md.name}")
            continue
        front = parse_frontmatter(m.group(1))
        body = m.group(2).strip()

        rooms = parse_rooms_from_body(body)

        front["id"] = slug_from_path(md)
        front["source_file"] = f"listings/{md.name}"
        front["body_md"] = body
        if rooms:
            front["rooms"] = rooms

        # normalize price into a single sortable number for filtering
        if "price_per_bedroom" in front and front["price_per_bedroom"] is not None:
            front["price_sort"] = front["price_per_bedroom"]
        elif "price_per_bedroom_low" in front and front["price_per_bedroom_low"] is not None:
            front["price_sort"] = front["price_per_bedroom_low"]
        else:
            front["price_sort"] = None

        listings.append(front)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(
            {"generated_from": "listings/*.md", "count": len(listings), "listings": listings},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT_FILE.relative_to(ROOT)}  ({len(listings)} listings)")


if __name__ == "__main__":
    build()
