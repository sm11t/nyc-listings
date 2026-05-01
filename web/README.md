# NYC Listings — Map Visualization

Static single-page app that plots every listing in `../listings/` on a map of
Brooklyn + Manhattan. Click a marker for full details, post notes that sync
across everyone viewing the page (Firebase), or fall back to per-browser
localStorage if no Firebase project is configured.

Two surfaces:

- **Brain (here)** — `web/` reads plaintext `data/listings.json`. No gate.
  This is where you edit listings and run dev.
- **Portfolio** — `asmit-space/nyclistings/` ships an encrypted blob
  (`data/listings.enc.json`) and prompts for a password before decrypting.
  The plaintext password lives only in `.env.local` on the brain side and
  never appears in the portfolio repo.

## Run locally

The page loads `data/listings.json` via `fetch`, so it must be served over
HTTP (not opened with `file://`).

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings\web"
python -m http.server 8765
# then open  http://127.0.0.1:8765/
```

## View on your phone (same Wi-Fi)

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings\web"
python -m http.server 8765 --bind 0.0.0.0
# find your laptop's LAN IP (Wi-Fi adapter) — e.g. 192.168.1.42
# then on your phone open  http://192.168.1.42:8765/
```

The phone layout uses a full-screen map with a **Filters** floating button
(top-left) and a **bottom sheet** for listing details. Tap a marker to expand
the sheet; tap the grip handle to collapse it.

## Regenerate data after adding/editing listings

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings"
python scripts\build_data.py
```

## Deploy to portfolio (asmit.space/nyclistings)

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings"
python scripts\deploy_portfolio.py

# then commit + push the portfolio repo
cd "C:\Users\asmit\OneDrive\Documents\GitHub\asmit-space"
git add nyclistings
git commit -m "deploy: nyclistings update"
git push
```

The deploy script:
1. rebuilds `web/data/listings.json` from markdown,
2. reads the password from `.env.local` (gitignored — see `.env.local` at
   the repo root),
3. encrypts `listings.json` with AES-GCM, key from PBKDF2-HMAC-SHA256
   (250k iterations, fresh 16-byte salt + 12-byte IV per build),
4. copies `web/` → `asmit-space/nyclistings/`, replacing the plaintext
   `listings.json` with `listings.enc.json`. Drops raw MTA `.geojson`
   downloads, only keeps the slimmed `.min.geojson` files.

A round-trip decrypt runs at the end of the deploy as a sanity check.

### How the gate works

`gate.js` runs before `app.js`:

1. Tries `data/listings.json` first — if found (brain side / dev), uses it
   directly and skips the gate.
2. Otherwise fetches `data/listings.enc.json`, derives an AES-GCM key from
   the user's password input via PBKDF2 (same parameters embedded in the
   blob), tries to decrypt. If the auth tag verifies, the data unlocks; if
   it doesn't, the user sees "wrong password" and re-prompts.
3. The successfully derived key is cached in `localStorage`, so a returning
   visitor doesn't have to re-enter the password.

The plaintext password is never in any portfolio file. Even with full
source access, the only way to read the listings is to know the password
and let PBKDF2-derived AES-GCM decrypt it.

## Refresh the transit overlays (rare)

```powershell
cd "C:\Users\asmit\OneDrive\Desktop\nyc listings"

curl -L -o web/data/transit/subway-lines.geojson `
  "https://data.ny.gov/api/geospatial/s692-irgq?method=export&format=GeoJSON"
curl -L -o web/data/transit/subway-stations.geojson `
  "https://data.ny.gov/api/geospatial/39hk-dx4f?method=export&format=GeoJSON"
curl -L -o web/data/transit/bus-routes.geojson `
  "https://data.ny.gov/api/geospatial/h2wf-afav?method=export&format=GeoJSON"

python scripts\build_transit.py
```

The slimmed `*.min.geojson` files are what the page actually loads
(~1.4 MB total). The raw downloads are gitignored.

## Firebase — shared notes & status

The page picks one of two backends at load time:

| Backend  | When | Where notes live |
|---|---|---|
| **firebase** | `firebase-config.js` has real values | Firestore — every viewer sees the same thread in real time |
| **local**    | Config is still placeholder values | Per-browser `localStorage` only |

The pill in the top-right corner shows which one is active (`live` vs `local`).

### Set up the Firebase project (one-time)

1. Open https://console.firebase.google.com → **Add project** → give it a name
   (e.g. `nyc-listings`).
2. Inside the project, **Build → Authentication → Get started → Sign-in method**
   → enable **Anonymous**.
3. **Build → Firestore Database → Create database** → start in **production
   mode** → pick a region (e.g. `nam5` for New York).
4. **Project settings (⚙) → General → Your apps → `</>` Web app** → register
   the app (no Hosting needed) → copy the `firebaseConfig` object.
5. Paste those values into `web/firebase-config.js`, replacing every
   `REPLACE_*` placeholder. Save.
6. Reload the page. The pill should read **live**. Open the same URL in
   another browser/phone; notes posted in one show up instantly in the other.

### Firestore security rules

In the Firebase Console: **Firestore → Rules** — paste this and **Publish**.

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Notes thread: stored at /listings/{listingId}/notes/{noteId}.
    // Use a recursive-wildcard match — required for the
    // collectionGroup('notes') query that powers marker note-counts.
    // The structural `/listings/{lid}/notes/{nid}` form would only allow
    // direct subscriptions, not the collection-group query.
    match /{path=**}/notes/{noteId} {
      allow read: if true;

      allow create: if request.auth != null
        && request.resource.data.text is string
        && request.resource.data.text.size() > 0
        && request.resource.data.text.size() < 2000
        && request.resource.data.uid == request.auth.uid
        && request.resource.data.author is string
        && request.resource.data.author.size() < 60;

      // Only the author can edit or delete their own note.
      allow update, delete: if request.auth != null
        && resource.data.uid == request.auth.uid;
    }

    // Status (interested/contacted/scheduled/visited/rejected) is one shared
    // doc per listing at /listings/{listingId}/meta/status. Recursive form
    // here too because we read it via collectionGroup('meta').
    match /{path=**}/meta/{metaDoc} {
      allow read: if true;
      allow write: if request.auth != null
        && (request.resource.data.value == null
            || request.resource.data.value is string
            && request.resource.data.value.size() < 30);
    }
  }
}
```

If you want notes to be your-only / read-only for everyone else, swap the
`create` rule to `if request.auth.uid == 'YOUR_OWN_UID_AFTER_FIRST_SIGNIN'`.

### Data shape

```
listings/
  {listingId}/
    notes/
      {auto-id}/
        text       : string  (1..1999 chars)
        author     : string  (display name, ≤60 chars)
        uid        : string  (Firebase auth UID — author identity)
        createdAt  : Timestamp (serverTimestamp())
    meta/
      status/
        value     : string | null  ('interested'|'contacted'|...)
        uid       : string
        updatedAt : Timestamp
```

`listingId` is the markdown file's stem
(e.g. `2026-04-30-fort-greene-54-cumberland-st`).

### Quotas to be aware of

Firebase free tier (Spark) gives you 50k reads / 20k writes / day, which is
plenty for a portfolio site that streams a thread of notes per click.
Real-time listeners count once on subscribe + once per change.

### Local-only mode

If `firebase-config.js` still has `REPLACE_*` placeholders the app silently
falls back to `localStorage` — useful for local dev or for someone forking the
repo. Notes posted in this mode never leave the browser.

## What's here

| File | Purpose |
|---|---|
| `index.html` | Page shell, FAB, drawer, bottom sheet, detail template |
| `styles.css` | Dark editorial design tokens; mobile drawer + bottom sheet |
| `app.js` | Leaflet map, filters, notes thread, drawer/sheet wiring |
| `firebase-config.js` | Firebase web config (placeholders by default) |
| `firebase.js` | ES-module bridge: Firestore + anonymous auth |
| `data/listings.json` | Generated from `../listings/*.md` |
| `data/transit/*.min.geojson` | Slimmed subway / bus / station GeoJSON |
| `../scripts/build_data.py` | Listings markdown → JSON |
| `../scripts/build_transit.py` | Raw MTA GeoJSON → clipped+slimmed `.min.geojson` |

## Features

- **Map** — CARTO dark tiles, bounded to Brooklyn + Manhattan (no API key).
- **Markers** — color-coded by price tier; violet for sublets; corner dot if
  the listing has at least one note.
- **Click / tap** — opens the detail panel (desktop) or slides up the bottom
  sheet (phone) with rent, beds/baths, distance to NYU, contact, operator,
  coords, last-updated stamp, amenities, multi-room table, and a notes thread
  with composer.
- **Notes** — threaded, multiple per listing, each with author + timestamp.
  Synced live across all viewers when Firebase is configured. Author name is
  set in the Filters drawer and stored on your device.
- **Status** — `interested / contacted / scheduled / visited / rejected`.
  Single shared value per listing, synced live (or local fallback).
- **Filters** — search, price min/max, lease (standard / 11mo / sublet),
  neighborhood chips, reset.
- **Transit toggles** — subway lines, stations, bus routes, place labels.
- **Quick list** — when no listing is selected, lists everything sorted by
  distance to NYU; tap a row to fly the map there.

## Mobile UX details

- Map is full-screen behind a transparent topbar.
- A pill button top-left toggles the **Filters drawer** (slides in from left
  with a scrim). The drawer holds search, filters, transit toggles, the
  legend, and your author name.
- Tap a marker → the **bottom sheet** slides up to ~88% height. Drag handle
  shows the selected address + price + note count when collapsed.
- Tap the handle to collapse back to peek state. Tap the scrim to close
  everything.
- Marker hit area is enlarged on touch devices.

## Future

- Walking-distance isochrones from each listing to NYU.
- Per-listing nearest-station summary (auto-derive when generating
  `listings.json`).
- Drag-to-resize the bottom sheet (instead of just two states).
- Deploy to GitHub Pages / Netlify / Vercel (zero build step required).
