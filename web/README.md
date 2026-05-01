# NYC Listings — Map Visualization

Static single-page app that plots every listing in `../listings/` on a map of
Brooklyn + Manhattan. Click a marker for full details and to add notes.

## Run locally

The page loads `data/listings.json` via `fetch`, so it must be served over
HTTP (not opened with `file://`).

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings\web"
python -m http.server 8765
# then open  http://127.0.0.1:8765/
```

## Regenerate data after adding/editing listings

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings"
python scripts\build_data.py
```

This re-parses every `listings/*.md` frontmatter and writes
`web/data/listings.json`.

## Refresh the transit overlays (rare)

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings"

# 1. Download raw MTA / NY-State open-data exports (~24 MB; gitignored)
curl -L -o web/data/transit/subway-lines.geojson `
  "https://data.ny.gov/api/geospatial/s692-irgq?method=export&format=GeoJSON"
curl -L -o web/data/transit/subway-stations.geojson `
  "https://data.ny.gov/api/geospatial/39hk-dx4f?method=export&format=GeoJSON"
curl -L -o web/data/transit/bus-routes.geojson `
  "https://data.ny.gov/api/geospatial/h2wf-afav?method=export&format=GeoJSON"

# 2. Slim + clip to Brooklyn + Manhattan
python scripts\build_transit.py
```

The slimmed `*.min.geojson` files are what the page actually loads
(~1.4 MB total). The raw downloads are gitignored.

## What's here

| File | Purpose |
|---|---|
| `index.html` | Page shell + filter sidebar + detail panel |
| `styles.css` | Dark editorial design tokens and layout |
| `app.js` | Leaflet map, markers, filters, notes (localStorage) |
| `data/listings.json` | Generated from `../listings/*.md` |
| `../scripts/build_data.py` | Markdown → JSON build script |

## Features

- **Map** — CARTO dark tiles, bounded to Brooklyn + Manhattan (free, no API key).
- **Markers** — color-coded by price tier (≤$1,150 / $1,151–$1,350 / ≥$1,351),
  violet for sublets. A small dot in the corner means a note is saved for that
  listing.
- **Click** — opens the right-hand detail panel with rent, beds/baths, distance
  to NYU, contact, operator, coords, last-updated stamp, amenities, multi-room
  table (Kingston Ave), and the full markdown summary.
- **Notes** — free-text per listing, saved to `localStorage`
  (`nyc-listings:notes:v1`). Auto-saves on blur.
- **Status** — pick one of `interested / contacted / scheduled / visited /
  rejected` per listing, also persisted in `localStorage`.
- **Filters** — search box, price min/max, lease (standard / 11mo / sublet),
  neighborhood. `reset filters` clears all.
- **Quick list** — when no listing is selected, the right panel shows all
  visible listings sorted by distance to NYU; click to fly the map there.

## Transit overlay

- **Subway lines** — every NYCT service that touches Brooklyn or Manhattan,
  colored per the official MTA palette (1/2/3 red, 4/5/6 green, 7 purple,
  A/C/E blue, B/D/F/M orange, N/Q/R/W yellow, G mint, J/Z brown, L gray).
- **Stations** — 322 stations across Brooklyn + Manhattan; hover for name and
  served routes.
- **Bus routes** — 223 distinct routes (B-, M-, BM-, X-, plus crossover Q/S).
  Hidden by default; toggle on in the sidebar.
- **Place labels** — separate toggle, off by default for a cleaner map.

Stacking order from bottom: bus → subway → stations → labels → listing markers.

## Future

- Walking-distance isochrones from each listing to NYU.
- Per-listing nearest-station summary (auto-derive when generating
  `listings.json`).
- Export to a static portfolio site (drop the `web/` folder into any host —
  GitHub Pages / Netlify / Vercel — no build step required).

## Data persistence note

Notes and status live in your browser's `localStorage`. They are not synced or
checked into the repo. If you want them durable, copy the JSON out of
DevTools → Application → Local Storage and stash it somewhere safe.
