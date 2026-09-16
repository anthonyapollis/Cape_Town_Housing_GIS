# Improvement backlog

Work for Codex (or anyone) to pick up. **Read `AGENTS.md` first** — it lists the
generated files you must not hand-edit and the constraints that have already
bitten once.

Every task has to leave CI green: `python -m pytest tests/ -q` passes, and
re-running the build pipeline produces no diff. Do one task per PR. Write down in
the PR what you could **not** verify.

Priority: **P1** makes the analysis more true. **P2** makes the product better.
**P3** is polish.

---

## P1 — replace estimates with data

Eight of the fourteen criteria are still desktop analyst estimates. These tasks
matter more than any UI work: input uncertainty moves rankings more than the
weights do (mean 5th-95th percentile rank swing 4.9 places under input
noise vs 3.2 under weight noise; see `outputs/input_sensitivity.csv`).

### 1. Real zoning from the City's cadastral layer
Right now each site's zone in `data/candidate_sites.csv` (`zone`,
`height_storeys`, `asofright_u_ha`) is analyst-coded from its known use. The
"50% of land is zoning-blocked" headline rests on it.

- Pull the City of Cape Town zoning layer from the Open Data Portal
  (https://odp-cctegis.opendata.arcgis.com — search "Zoning").
- For each site, take the zone(s) intersecting a 500 m buffer, weighted by area.
- Write a `scripts/measure_zoning.py` following the pattern of
  `scripts/measure_site_context.py`: cached raw download, recomputes offline, logs
  estimated-vs-measured to `outputs/measurement_log.csv`.
- **Done when:** zone columns come from the layer; `DimCriterion.provenance` and
  the README provenance table say so; the summary numbers (`units_asofright`,
  `ha_blocked_by_zoning`) are regenerated and the README/atlas prose that quotes
  them is updated to the new figures.

### 2. Flood risk from real floodlines
`flood_risk` is estimated. Replace it with the City's 1:100-year floodline layer
(Open Data Portal) plus distance to wetlands.

- Score = share of the site buffer inside the floodline, blended with proximity.
- **Done when:** measured, logged, provenance updated, tests still pass.

### 3. Remote-sensing columns without an Earth Engine account
`ndvi`, `ndbi`, `lst_anom_c`, `impervious_pct` are estimates. `scripts/gee_remote_sensing.js`
exists but needs a GEE account. Do it in Python instead against Microsoft
Planetary Computer STAC (no key needed for reads):

- Sentinel-2 L2A summer median → NDVI, NDBI, impervious fraction per 500 m buffer.
- Landsat 8/9 Collection 2 L2 thermal → LST, expressed as anomaly vs metro mean.
- Suggested libs: `pystac-client`, `planetary-computer`, `stackstac` or `odc-stac`.
- Keep the network fetch behind a `--fetch` flag and commit a small cached CSV so
  CI stays offline.
- **Done when:** `lst_anom_c` (the only one of the four that is scored) is measured;
  the other three are measured and displayed.

### 4. Transit as travel time, not straight-line distance
`dist_transit_km` is great-circle distance to the nearest OSM rail station. That
flatters sites across rivers and highways.

- Use MyCiTi and PRASA GTFS if obtainable, otherwise an OSM walking network
  (`osmnx`) to compute walk time to the nearest station/stop.
- Add MyCiTi BRT stops — the current OSM query found none under the `network` tag;
  try `operator=MyCiTi` or `route=bus` relations.
- **Done when:** a `walk_min_to_transit` column replaces or supplements the
  distance, and the criterion uses it.

### 5. Bulk infrastructure and contamination
Both estimated. Bulk: City water/sewer capacity maps or the Municipal Spatial
Development Framework infrastructure layers. Contamination: DFFE contaminated
land register, or land-use history (industrial/rail/military = elevated).
Document clearly if only a proxy is achievable — a labelled proxy beats a guess.

---

## P2 — product

### 6. Power BI report pages
`powerbi/CapeTownHousing.pbip` has a validated semantic model (23 measures) but
**no report pages** — `report.json` was deliberately not hand-written because it
could not be tested.

- Author pages in Power BI Desktop and save as PBIP so the report definition is
  text: Overview (KPI cards: Total Units, Buildable Now, Needs Rezoning, % Blocked;
  map by lat/lon), Zoning, Scenarios (rank efficiency vs redress, rank shift),
  Delivery (cumulative units by year), Robustness (rank swing weights vs inputs),
  Provenance (criteria by Measured/Estimated).
- Use the project palette: teal `#00887A`, ochre `#B4620F`, indigo `#4B3FA8`.
- **Done when:** the .pbip opens and refreshes from `powerbi/data/` on a clean
  clone. **This needs Power BI Desktop to verify** — say so if you could not.

### 7. Run and fix the QGIS builder
`scripts/build_qgis_project.py` has **never been executed**. Run it (the
`qgis/qgis` Docker image works headless) and fix what breaks.

- **Done when:** it produces `qgis/cape_town_housing.qgz` that opens with all
  layers styled; ideally add it to CI via the Docker image.

### 8. Deploy to Netlify
`netlify.toml` is ready (publishes the repo root, `/` redirects to the atlas).
Connect the repo, deploy, and confirm on the live URL that: the precincts load, the
satellite basemap chips are enabled (they should be — Netlify is not sandboxed),
and `/satellite` works. Add the live URL to the README.

### 9. JavaScript tests
All tests are Python. The atlas has non-trivial JS with no coverage: the Mercator
projection (`px`/`py`), `clipNear()` (Sutherland–Hodgman — easy to break),
tile maths (`tileX`/`tileY`), label collision placement.

- Extract the pure functions or test them in-page with Playwright.
- **Done when:** a regression in `clipNear` (e.g. discarding a polygon with one
  vertex behind the camera) fails CI.

### 10. Browser smoke test in CI
Add a Playwright job that serves the repo and checks: no console errors; 30
precincts render; every one of the 30 map layers paints 30 symbols; the 3D scene
paints at tilt 4°, 46° and 89°; no horizontal overflow at 375 px and 1400 px.
Previous manual QA runs did exactly this — automate it.

---

## P3 — polish

### 11. README screenshots
The README has no images. Generate them with Playwright in CI (plan view, 3D
scene, zoning section) into `docs/img/` and embed them. Don't hand-capture —
make it reproducible.

### 12. 3D scene accessibility
The canvas scene is mouse-only. Add keyboard orbit/zoom (arrows, +/−), and make
the view presets real buttons with visible focus. Respect
`prefers-reduced-motion` for any camera animation.

### 13. Verify the Google Maps page with a key
`docs/google_maps.html` has only been tested without an API key. Test with a
restricted key (never commit it) and fix anything in the map/Street View path.

### 14. Demand side
The model ranks land supply only. Add who the land would serve: StatsSA Census
small-area population and household income, or the City housing needs register if
available, as a demand criterion or a separate lens.

---

## Things not to do

- Don't hand-edit anything listed as generated in `AGENTS.md`.
- Don't describe an estimated column as measured or as municipal data.
- Don't add a CDN, mapping library or tile server as a hard dependency of
  `docs/_atlas.body.html` — the Artifact build must keep working sandboxed.
- Don't introduce non-ASCII characters into the atlas.
- Don't collapse the two scenarios into one ranking — the movement between
  efficiency and redress is the finding.
