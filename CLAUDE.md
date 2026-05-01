# NYC Listings — Project Instructions for Claude

This folder is a personal knowledge base for **NYC apartment hunting**. Its purpose is to capture every listing the user evaluates in a structured, comparable, durable format. Treat this as a long-running personal project, not a one-shot task.

The user gives you screenshots from listing sites (NYU off-campus housing portal, StreetEasy, Zillow, etc.) and expects you to extract, normalize, and file each one consistently.

## Folder layout

```
nyc-listings/
├── CLAUDE.md                 — this file
├── Neighborhoods.md          — neighborhood-level overview
├── Schedule-vs-Housing.md    — commute / schedule analysis
├── neighborhoods/            — per-neighborhood notes
│   ├── Bed-Stuy.md
│   ├── Bushwick.md
│   ├── Crown-Heights.md
│   ├── Journal-Square.md
│   └── Sunset-Park.md
└── listings/                 — one file per listing + INDEX.md
    ├── INDEX.md              — comparison table across all listings
    └── YYYY-MM-DD-<neighborhood>-<street>.md
```

## Saving a new listing

When the user sends a screenshot of a listing, **always**:

1. **Extract every visible field.** Don't skip data points. Common fields to capture:
   - Title (listing's own headline)
   - Full address (street, city, state, zip)
   - Neighborhood + borough (infer from zip if not labeled)
   - **Latitude + longitude** (geocode from the address — approximate is fine, note as approximate)
   - Price per bedroom / total monthly price
   - Beds in unit + how many available + baths
   - Square footage (if shown)
   - Availability date / lease term
   - Distance to NYU (or other landmark if user specifies)
   - Contact phone + contact hours
   - Listing platform / source (NYU portal, StreetEasy, etc.)
   - Operator (e.g. June Homes, broker name)
   - Last-updated stamp on the listing
   - Photo count, virtual tour availability
   - Any flags ("New", "Hot listing", etc.)

2. **File naming convention:**
   ```
   YYYY-MM-DD-<neighborhood-kebab>-<street-kebab>.md
   ```
   Example: `2026-04-30-fort-greene-54-cumberland-st.md`
   The date is the **capture date** (when the user saved it), not the listing's posted date.

3. **Frontmatter schema** (YAML, keep keys consistent across files):
   ```yaml
   ---
   title: <listing's own title>
   address: <full street address>
   neighborhood: <name>
   borough: Brooklyn | Queens | Manhattan | Bronx | Staten Island | Jersey City
   lat: <decimal>
   lng: <decimal>
   price_per_bedroom: <number>           # or price_per_bedroom_low / _high if range
   beds_in_unit: <number>
   baths: <number or null>
   sqft: <number or null>
   availability: <YYYY-MM-DD | "Available Now" | null>
   lease_term: <e.g. "std" | "11mo" | "3mo sublet">
   miles_to_nyu: <decimal>
   contact_phone: "<phone>"
   contact_hours: <e.g. "Anytime" | "Mon-Fri 9am-5pm" | null>
   listing_platform: <source>
   operator: <name or null>
   last_updated: <as listed, e.g. "3 days ago (as of YYYY-MM-DD)">
   photos: <count>
   ---
   ```
   Use `null` (not empty string) for missing values. Add new fields as needed but keep existing ones consistent.

4. **Body:** under the frontmatter, write a short bulleted summary (rent, unit, address, coords, distance, contact, operator, availability, notes). Keep it scannable. Include any non-obvious detail visible in the photos (e.g. "1 bath shared by 4", "exposed brick", "covered furniture suggests current tenant moving out").

5. **Update `listings/INDEX.md`** after every add. The INDEX is the comparison view. It should have:
   - A table sorted by **distance to NYU** (ascending) with columns: Address (linked) · Neighborhood · Beds/Baths · $/Room · Mi to NYU · Avail · Lease · Phone
   - "Quick takes" section: cheapest overall, cheapest long-term, closest, best value/distance, best bath ratio, outliers
   - "Lease type split" section grouping standard vs sublet
   - "Operators / source patterns" section noting recurring operators across listings (e.g. "June Homes cluster", "908-area-code cluster")
   - Total listing count at the top

## Handling duplicates and re-screenshots

- **Same address, same room** → update the existing file. Don't create a new file dated today; instead bump `last_updated` and merge any new info (availability changes, new photos, etc.).
- **Same address, different room** → if the building lists rooms separately (different prices, different contacts), consolidate into **one file per address** with a per-room table inside (see `2026-04-30-crown-heights-89-kingston-ave.md` for an example with 3 rooms).
- **Already-saved listing re-sent** → acknowledge it's a duplicate, note any new info, don't recreate.

## Coordinate approximation

If you don't have a geocoding tool, infer lat/lng from the street address using your knowledge of the area. Mark them as approximate. Accuracy of ±200m is fine for filtering/mapping purposes. Do not skip coordinates — the user explicitly requires them on every listing.

## Useful patterns to flag

- **Operator clustering** — when the same phone area code or platform branding appears across multiple listings, call it out. One outreach call may cover several listings.
- **Bath ratios** — flag any unit with >3 beds per bath as a constraint.
- **Lease term traps** — sublets dressed up as listings (3-month windows, summer-only) need to be clearly distinguished from year+ leases.
- **Stale listings** — anything "Last Updated: 2+ weeks ago" deserves a note; verify before contacting.

## What to ask the user when

- If a screenshot is cut off or a key field is missing, ask before fabricating. Coordinates can be inferred; rent / availability / phone cannot.
- If the user asks for a status field (interested / contacted / scheduled / rejected), add it to the frontmatter and the INDEX.

## Tone

Terse, factual, scannable. The user is doing a high-volume comparison — they want signal, not prose. End-of-turn summaries should be one or two lines: what was added, what's notable.

## Source platforms seen so far

- NYU off-campus housing portal (in partnership with Apartments.com) — most current entries
- June Homes (operator across many listings on that portal)

If the user introduces a new source (StreetEasy, Zillow, Craigslist, etc.), capture it in the `listing_platform` field and note any source-specific conventions in this file.
