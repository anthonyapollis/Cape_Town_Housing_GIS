# Cape Town Housing Ground

Land screening for low-income housing development across the City of Cape Town metro.
Thirty candidate precincts, twelve criteria, multi-criteria decision analysis with a
Monte Carlo robustness test, dwelling-yield estimates, a 4D delivery programme and a
remote-sensing layer.

## Read this first — provenance

| Layer | Status |
|---|---|
| Site coordinates, employment nodes, all distances | **Real.** Computed from coordinates by haversine. |
| Job accessibility index | **Derived.** Gravity model over eight weighted metro employment nodes. |
| Suitability / impact / tranche / yield | **Derived** from the inputs below. |
| Twelve criteria values (flood, contamination, bulk infra, complexity, land value, …) | **Desktop analyst estimates.** Not municipal records. |
| NDVI, NDBI, LST anomaly, impervious %, slope, elevation | **Desktop estimates.** `scripts/gee_remote_sensing.js` replaces them with measured values. |
| Basemap coastline, relief, rail lines | **Schematic**, hand-simplified. Site markers are at true coordinates. |

This is a screening layer for deciding where to spend survey budget — not a feasibility study.

## Layout

```
data/candidate_sites.csv      30 precincts x 22 attributes (the model input)
scripts/suitability_model.py  MCDA + yield + tranching + sensitivity
scripts/gee_remote_sensing.js Earth Engine: Sentinel-2, Landsat 9, SRTM, JRC GHSL
scripts/validate_palette.py   colour-vision validator for the chart palette
scripts/build_basemap.py      OSM Overpass downloads -> basemap.geojson / basemap.json
scripts/build_kml.py          3D + 4D KML/KMZ for Google Earth Pro
scripts/build_atlas_payload.py  inlines model outputs + basemap into docs/index.html
scripts/build_qgis_project.py   PyQGIS project builder (UNTESTED - no QGIS here)
outputs/site_rankings.csv     ranked table
outputs/criteria_scores.csv   normalised 0-100 score per criterion per site
outputs/sensitivity.csv       rank intervals over 5 000 weight draws
outputs/candidate_sites.geojson  point layer for QGIS / ArcGIS / kepler.gl
outputs/summary.json          headline figures
docs/index.html               the interactive atlas (pan/zoom, full-screen, layer + style switches)
docs/satellite_map.html       Leaflet satellite/multi-layer map, no API key
docs/google_maps.html         Google Maps + Street View, needs your own key
```

## Run it

```bash
python scripts/suitability_model.py
```

Then open `docs/index.html`, or serve it:

```bash
python -m http.server 8777 --directory docs
```

## Method

1. **Normalise** every criterion to 0–100 across the 30 sites; cost criteria inverted.
2. **Weight and sum.** Weights sum to 1.0, led by job accessibility (0.18) and transit (0.16) —
   the spatial-justice reading of the problem, where distance from work is the primary harm.
3. **Yield** = developable hectares × typology density (60–260 u/ha), 65% at the sub-R3 500 band.
4. **Impact** = suitability × log₁₀(units), renormalised. A weighted sum systematically
   over-rewards small, perfectly-located parcels; this is the correction.
5. **Tranche** from a readiness composite (delivery complexity, bulk-infrastructure headroom,
   contamination). A readiness signal, not a commitment date.
6. **Sensitivity**: 5 000 draws with every weight jittered ±30% and renormalised; report the
   5th–95th percentile rank and the share of draws in which each site holds a top-ten place.

## Replacing the estimates

- **Remote sensing** — run `scripts/gee_remote_sensing.js` in the Earth Engine code editor;
  it exports `candidate_sites_rs.csv` (join on `site_id`).
- **Parcels, ownership, zoning** — City of Cape Town Open Data Portal; DPWI immovable asset register.
- **Flood** — the City's 1:100-year floodline layer and Cape Flats Aquifer extent.
- **Transit** — PRASA station points and MyCiTi GTFS, for network rather than straight-line distance.
- **Terrain** — the City's 0.5 m LiDAR DSM/DTM where real massing is needed; SRTM is screening-grade only.
- **Demand** — housing needs register + StatsSA Census small-area data, to weight sites by the
  backlog they serve rather than by supply alone.


## Real basemaps: QGIS, Google Earth, Google Maps

The published atlas runs under a CSP that blocks every external host, so it inlines real
OpenStreetMap vector geometry but cannot stream satellite tiles. Three companion outputs do
what the browser page cannot.

| Output | Opens in | Gives you |
|---|---|---|
| `outputs/cape_town_housing.kml` / `.kmz` | Google Earth Pro, Google My Maps | True 3D extruded massing on real imagery + terrain, driven by Earth's time slider (2027-2037). Second folder extrudes by spatial-redress score. |
| `docs/satellite_map.html` | Any browser, **no API key** | Leaflet + Esri World Imagery, OSM, CartoDB light/dark, OpenTopoMap, hillshade. Every vector layer as a toggleable overlay; colour-by and size-by controls. Serve the repo root, open `/docs/satellite_map.html`. |
| `docs/google_maps.html` | Any browser, your own Maps JS API key | Street View on any precinct, plus 45 deg tilt. Run `python -m http.server 8777` from the repo root and open `/docs/google_maps.html?key=YOUR_KEY`. |
| `scripts/build_qgis_project.py` | QGIS | Esri World Imagery + OSM + hillshade as XYZ layers, real boundary/coastline/rail vectors, 1 km catchments buffered in EPSG:32734, graduated renderers on suitability and redress. **Not executed — QGIS was not installed on the build machine. Treat the first run as a test.** |

`outputs/candidate_sites.geojson` and `data/geo/basemap.geojson` load straight into QGIS,
ArcGIS or kepler.gl with no script at all.


### Basemaps inside the atlas itself

`docs/index.html` probes for a tile server at boot. When it can reach one, four extra basemaps
appear next to the three vector styles and draw as live XYZ tiles straight into the map plate,
with every analysis layer still on top:

| Basemap | Source | Max zoom |
|---|---|---|
| Satellite | Esri World Imagery (Maxar, Earthstar Geographics) | 19 |
| Streets | OpenStreetMap | 19 |
| Terrain | OpenTopoMap | 17 |
| Hillshade | Esri World Hillshade | 16 |

No API key for any of them. Published as an Artifact the probe fails, the four chips render
disabled with an explanation, and the map falls back to its vector styles - so the same file
works in both places.


## Deploying to Netlify

`netlify.toml` publishes the **repository root**, not `docs/` — the map pages fetch
`../outputs/*.geojson` and `../data/geo/*.geojson` at runtime, so serving `docs/` alone
gives you a map with no precincts on it. `/` redirects to `/docs/index.html` and
`/satellite` to the Leaflet page.

```bash
netlify deploy --prod
```

Deployed on Netlify the page is **not** sandboxed, so the four raster basemaps
(satellite, streets, terrain, hillshade) switch on by themselves — same as running it
locally, unlike the Artifact build where the CSP blocks tile fetches.

Raw Overpass dumps (`data/geo/osm_*.json`, 3.3 MB) are gitignored. The derived
`basemap.geojson` and `basemap.json` are committed, so nothing needs refetching to build.

## The 3D scene

`docs/index.html` has two view modes. **Plan** is the projected map. **3D scene** is a
perspective camera over the same geometry — drag to orbit, shift-drag to pan, scroll to
zoom, with top-down / bird's eye / low-oblique presets and a compass readout. Written as
plain Canvas 2D with the projection and near-plane clipping done explicitly, because the
Artifact sandbox forbids loading a mapping library and thirty boxes over ~1 100 ground
vertices does not need one.

Each precinct is its real footprint at ground scale, extruded to the storeys its density
implies. The **solid volume is what current zoning permits as of right; the ghosted volume
above it needs rezoning first** — on ten sites the whole building is ghosted. Height is
exaggerated 26x or a 35 m block is invisible at metro scale.

## Spatial and racial inequality

The model runs the same fourteen criteria under two weightings, because a weighted sum over land
economics is not neutral in a city that was zoned by race:

- **Efficiency** — land economics only. Left alone it recommends the periphery, because apartheid
  planning is what made the periphery cheap.
- **Redress** — adds **spatial redress** (0.17), high where a site returns low-income households to
  well-located land the Group Areas Act reserved for white occupation, and **displacement risk**
  (0.06, a cost), which penalises inner-city sites currently evicting the working-class, largely
  coloured community already living there.

`group_area_1950` in `data/candidate_sites.csv` records each location's Group Areas Act designation.
Those designations are historical record. The redress and displacement scores built on them are
analyst judgements and are meant to be contested — `rank_shift` in the outputs is the finding, not
either ranking on its own.

## Data fetched

`data/geo/osm_*.json` are raw Overpass API downloads (coastline, admin_level=6 boundary, rail).
`scripts/build_basemap.py` stitches, simplifies and clips them. Basemap data (c) OpenStreetMap
contributors, ODbL.
