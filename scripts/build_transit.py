"""
Slim and clip transit GeoJSON files to Brooklyn + Manhattan.

Reads raw downloads from web/data/transit/{subway-lines, subway-stations,
bus-routes}.geojson and writes web/data/transit/{subway-lines,
subway-stations, bus-routes}.min.geojson with:

* features clipped/filtered to a Brooklyn + Manhattan bbox
* one bus shape per (route, direction) — drops duplicate trip variants
* coordinate precision rounded to 5 decimal places (~1m)
* only the properties the frontend actually needs

The min files are what the page loads at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSIT_DIR = ROOT / "web" / "data" / "transit"

# Brooklyn + Manhattan bbox, generous so we keep lines that exit the area.
BBOX_S, BBOX_W = 40.55, -74.05
BBOX_N, BBOX_E = 40.92, -73.85


def in_bbox(lng: float, lat: float) -> bool:
    return BBOX_S <= lat <= BBOX_N and BBOX_W <= lng <= BBOX_E


def round_coords(geom, precision: int = 5):
    """Recursively round all numeric leaves in a geometry's coordinates."""
    coords = geom.get("coordinates")
    geom["coordinates"] = _round(coords, precision)
    return geom


def _round(x, p):
    if isinstance(x, (list, tuple)):
        if x and isinstance(x[0], (int, float)):
            return [round(v, p) for v in x]
        return [_round(v, p) for v in x]
    return x


def _perp_sq(p, a, b):
    """Squared perpendicular distance from p to segment a-b (lon/lat plane)."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        ddx, ddy = px - ax, py - ay
        return ddx * ddx + ddy * ddy
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    ddx, ddy = px - cx, py - cy
    return ddx * ddx + ddy * ddy


def douglas_peucker(points, tol_deg):
    """Iterative DP simplification. tol_deg is in degrees (~0.00005 ≈ 5m)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    tol_sq = tol_deg * tol_deg
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        max_d, max_k = -1.0, -1
        a, b = points[i], points[j]
        for k in range(i + 1, j):
            d = _perp_sq(points[k], a, b)
            if d > max_d:
                max_d, max_k = d, k
        if max_d > tol_sq:
            keep[max_k] = True
            stack.append((i, max_k))
            stack.append((max_k, j))
    return [p for k, p in zip(keep, points) if k]


def simplify_geom(geom, tol_deg):
    """Simplify (Multi)LineString in place; ignores other geometry types."""
    t = geom.get("type")
    if t == "LineString":
        geom["coordinates"] = douglas_peucker(geom["coordinates"], tol_deg)
    elif t == "MultiLineString":
        geom["coordinates"] = [douglas_peucker(part, tol_deg) for part in geom["coordinates"]]
    return geom


def line_in_bbox(geom) -> bool:
    """True if any vertex of a (Multi)LineString is inside the bbox."""
    coords = geom.get("coordinates", [])
    t = geom.get("type")
    parts = [coords] if t == "LineString" else coords
    for part in parts:
        for pt in part:
            if in_bbox(pt[0], pt[1]):
                return True
    return False


def write(name: str, fc: dict):
    out = TRANSIT_DIR / name
    out.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"  -> {name}  ({len(fc['features'])} features, {size_kb:,.1f} KB)")


# ---------- subway lines ----------
def build_subway_lines():
    src = json.loads((TRANSIT_DIR / "subway-lines.geojson").read_text(encoding="utf-8"))
    out = []
    for f in src["features"]:
        g = f.get("geometry") or {}
        if not g or not line_in_bbox(g):
            continue
        simplify_geom(g, tol_deg=0.00008)  # ~9m
        round_coords(g, 5)
        p = f.get("properties", {})
        out.append({
            "type": "Feature",
            "geometry": g,
            "properties": {
                "service": p.get("service"),
                "service_name": p.get("service_name"),
            },
        })
    write("subway-lines.min.geojson", {"type": "FeatureCollection", "features": out})


# ---------- subway stations ----------
def build_subway_stations():
    src = json.loads((TRANSIT_DIR / "subway-stations.geojson").read_text(encoding="utf-8"))
    out = []
    for f in src["features"]:
        p = f.get("properties", {})
        if p.get("borough") not in ("Bk", "M"):
            continue
        g = f.get("geometry")
        if not g:
            continue
        round_coords(g, 5)
        out.append({
            "type": "Feature",
            "geometry": g,
            "properties": {
                "stop_name": p.get("stop_name"),
                "daytime_routes": p.get("daytime_routes"),
                "line": p.get("line"),
                "borough": p.get("borough"),
                "complex_id": p.get("complex_id"),
                "structure": p.get("structure"),
                "ada": p.get("ada"),
            },
        })
    write("subway-stations.min.geojson", {"type": "FeatureCollection", "features": out})


# ---------- bus routes ----------
def build_bus_routes():
    src = json.loads((TRANSIT_DIR / "bus-routes.geojson").read_text(encoding="utf-8"))
    seen: dict[tuple, dict] = {}
    for f in src["features"]:
        p = f.get("properties", {})
        rsn = (p.get("route_short_name") or "").upper()
        if not rsn:
            continue
        # Brooklyn + Manhattan + cross-borough express buses serving them
        prefixes = ("B", "M", "BM", "X", "Q", "S", "SBS")
        # exclude Bx (Bronx) — short_name starts with 'BX'
        if rsn.startswith("BX"):
            continue
        if not any(rsn.startswith(pfx) for pfx in prefixes):
            continue

        g = f.get("geometry") or {}
        if not g or not line_in_bbox(g):
            continue

        # One shape per route (the two directions differ only on one-way streets).
        if rsn in seen:
            continue

        simplify_geom(g, tol_deg=0.00025)  # ~28m — buses are seen at lower zoom
        round_coords(g, 4)
        seen[rsn] = {
            "type": "Feature",
            "geometry": g,
            "properties": {
                "route_short_name": rsn,
                "route_long_name": p.get("route_long_name"),
                "route_color": p.get("route_color"),
            },
        }
    out = list(seen.values())
    out.sort(key=lambda f: f["properties"]["route_short_name"])
    write("bus-routes.min.geojson", {"type": "FeatureCollection", "features": out})


def main():
    print("clipping/slimming transit data -> Brooklyn + Manhattan")
    build_subway_lines()
    build_subway_stations()
    build_bus_routes()


if __name__ == "__main__":
    main()
