# Working in this repo

Guardrails for anyone â€” human or agent â€” changing this project. Most of these
encode a mistake that has already been made once.

**Looking for something to work on?** The prioritised backlog, with acceptance
criteria for each task, is in [`CODEX_TASKS.md`](CODEX_TASKS.md).

## The build pipeline

Run in this order. Later steps consume earlier outputs.

```bash
python scripts/measure_site_context.py   # optional; --fetch-dem hits the network
python scripts/suitability_model.py      # data/ -> outputs/
python scripts/build_basemap.py          # data/geo/osm_*.json -> basemap.geojson/json
python scripts/build_atlas_payload.py    # outputs/ + basemap -> docs/
python scripts/build_powerbi_model.py    # outputs/ -> powerbi/
python scripts/build_kml.py              # outputs/ -> outputs/*.kml/kmz
python -m pytest tests/ -q
```

## Generated files â€” never edit these by hand

| Generated | Edit this instead |
|---|---|
| `index.html`, `library.html`, `docs/report.html`, `outputs/*.epub`, `outputs/book-assets/*` | `scripts/build_publication.py` |
| `outputs/housing-atlas-ebook.pdf`, `outputs/report-content.json` | `scripts/build_ebook.py` |
| `docs/index.html` | `docs/_atlas.body.html` |
| `docs/_atlas.artifact.html` | `docs/_atlas.body.html` |
| `outputs/*.csv`, `outputs/*.json`, `outputs/*.geojson` | `data/candidate_sites.csv` or `scripts/suitability_model.py` |
| `outputs/cape_town_housing.kml` / `.kmz` | `scripts/build_kml.py` |
| `powerbi/data/*.csv`, `powerbi/**/*.tmdl`, `measures.dax` | `scripts/build_powerbi_model.py` |
| `data/geo/basemap.geojson`, `basemap.json` | `scripts/build_basemap.py` |

CI fails the build if a generated file differs from what the scripts produce, so
an edit to `docs/index.html` will be caught rather than silently overwritten.

## Non-obvious constraints

**The atlas must stay pure ASCII.** It is published two ways: as a standalone
document (`docs/index.html`, has a charset meta) and as a bare body fragment for
a Claude Artifact (`docs/_atlas.artifact.html`, where the platform generates
`<head>` and there is no charset meta). Any real UTF-8 character renders as
mojibake in the second. Use `\uXXXX` escapes in JS strings and HTML entities in
markup. `build_atlas_payload.py` asserts this and `tests/` checks it.

**`const DATA = ` is one line ending in `;`.** The payload injector finds the end
of the declaration by newline, **not** by the first `;` â€” one of the Group Areas
strings contains a semicolon (`"Declared White 1966; ~60 000 removed"`). Do not
"simplify" that back to a semicolon search.

**The 3D scene needs near-plane clipping.** `clipNear()` is Sutherlandâ€“Hodgman
against `depth >= NEAR`. Without it a single vertex behind the camera discards an
entire polygon and the ground vanishes at low tilt â€” which is exactly the view
worth having. Easy to reintroduce if you refactor the projection.

**Artifact CSP may block external imagery.** The atlas starts with Esri satellite
imagery unless the reader saved another basemap. Embedded geography stays available
and is automatically restored on failed or stalled tile loads. Optional imagery labels
fail independently. Do not add a hard dependency on a CDN, tile server or mapping library.

**Netlify publishes the repo root, not `docs/`.** The map pages fetch
`../outputs/` and `../data/geo/` at runtime. Serving `docs/` alone gives a map
with no precincts on it.

## Provenance â€” the thing not to get wrong

Six of the fourteen criteria are measured or derived. **Eight are desktop analyst
estimates.** `DimCriterion.provenance` in the Power BI model and the README table
record which is which.

Never describe an estimated column as measured, survey data or a municipal
record. Specifically still estimated: flood risk, environmental sensitivity,
contamination, bulk infrastructure, delivery complexity, heat anomaly, spatial
redress, displacement risk.

Group Areas Act designations are historical record. The redress and displacement
indices built on them are analyst judgements and are meant to be contested â€” the
`rank_shift` between the two scenarios is the finding, not either ranking alone.

Zone codes come from the City's Development Management Scheme, but the assignment
of a zone to each site is analyst-coded from its current use, **not** read off the
City's cadastral zoning layer.

## Untested

`scripts/build_qgis_project.py` has never been executed â€” QGIS was not installed
on the machine that wrote it. It uses stable PyQGIS classes but treat the first
run as a test. `docs/google_maps.html` has only been exercised without an API
key (the key prompt path); the Google Maps path itself is unverified.

## Local note

This project folder sits inside a git repository rooted at the Windows home
directory, which tracks `.aws`, `.ssh` and `.claude.json`. It has its own repo,
but always confirm before staging:

```bash
git rev-parse --show-toplevel   # must end in Cape_Town_Housing_GIS
```

## Publication edition 3

The root index is the report reading edition; the download library is `library.html`; the atlas stays at `docs/index.html`. Build the report with `build_ebook.py`, then run `build_publication.py` for the EPUB and reading editions. These two commands need reportlab, matplotlib and pymupdf in addition to the model dependencies. The publication tests use the standard library and validate the committed artifacts. Rebuild both publication commands after report-content edits.
