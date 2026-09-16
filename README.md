# Cape Town Housing Opportunity Atlas

An indexed report library, reflowable ebook and redesigned map-first atlas for the existing 30-precinct housing screening model.

## Open the result

- `index.html`: publication landing page with report index and all downloads.
- `docs/report.html`: browser reading edition with linked chapter navigation.
- `outputs/housing-atlas-ebook.epub`: reflowable EPUB ebook with maps, tables and indexes.
- `docs/index.html`: interactive atlas; opens directly from disk and works offline.
- `outputs/housing-atlas-ebook.pdf`: 30-page report with executive summary, linked contents, recommendations, sources, site index and subject index.
- `outputs/visuals/`: four analytical charts in PNG and editable SVG.
- `docs/legacy.html`: the original atlas, including its conceptual 3D scene.
- `powerbi/`: the existing Power BI model, preserved from the latest source project.

The main atlas embeds its data and vendored Leaflet 1.9.4 / Chart.js 4.5.1 code. There are no required CDN requests. Streets and satellite layers require internet access; the offline atlas remains available. Library licence notices are retained in `docs/vendor/`.

## Improvements

- Large map, grouped markers for dense precincts, geographic labels and a focused site inspector.
- Efficiency/redress ranking switch; search, regional and stability filters; filtered CSV export.
- Three-site comparison and linked access/capacity and uncertainty charts.
- Named nearest rail station; school and health-feature counts within 1 / 2 km; optional facility points and straight-line rings.
- A matching ebook with metro and inner-city maps, three site profiles, charts and all 30 directory entries.
- Keyboard-accessible site markers, responsive phone layout, and an explicit no-results state.

## Evidence contract

The existing model scores, rankings and assumptions are preserved. New geography is derived from the project's 30 August 2026 OSM snapshot (131 rail points, 1,642 facility features).

Precinct points are not cadastral boundaries. Zoning assignments, ownership, area, density, land value and job weights are not independently validated here. Eight qualitative criteria remain desktop estimates. The earlier model's `units_asofright` and tranche fields do not establish legal rights or delivery commitments.

Rail distance is straight-line proximity to a mapped station, not operating service or walking time. New facility counts are raw mapped features, unlike the original weighted facility-access score; they may include overlapping campus representations. Stability statistics apply to the efficiency ranking only and are not delivery probabilities.

## Rebuild

```bash
pip install pandas numpy pytest reportlab matplotlib pymupdf
python scripts/suitability_model.py
python scripts/build_atlas_payload.py
python scripts/build_powerbi_model.py
python scripts/build_kml.py
python scripts/build_ebook.py
python scripts/build_publication.py
python -m pytest tests/ -q
```

`data/geo/site_context.json` is committed so ordinary builds need no raw OSM dumps or network. To refresh it from the saved raw inputs, run `python scripts/build_site_context.py` before building the atlas and ebook. The optional original measurement/basemap pipeline is documented in `README-legacy.md` and `AGENTS.md`.

Edit `docs/_atlas.body.html`, not the built HTML. `build_atlas_payload.py` injects the payload and vendored libraries. It retains the ASCII artifact build and standalone viewport metadata.

Serve the repository root for companion links: `python -m http.server 8777`. Open `/index.html` for the report library or `/docs/index.html` for the atlas. Netlify publishes the root and opens the report library.

## Validation

33 Python tests passed (26 original, 4 geographic context and 3 publication-integrity checks). Browser verification passed 21 checks covering offline startup, grouped-marker zoom, search, ranking lens, no-results state, filters, sorting, comparisons, facility layers, CSV download, basemap recovery and layouts at 390/768/1440 px. The 30-page PDF was rendered and visually reviewed. Its 124 internal links and 30 bookmarks were inspected. EPUB XML, internal resources and all 30 spine entries were validated. Nine additional browser checks verified the landing page, report navigation, indexes, offline reading and mobile layouts. Street and satellite imagery were also loaded successfully. Optional online imagery availability depends on providers; QGIS and the Google Maps API-key path retain their original unverified status.

## Publication source

Edit `scripts/build_ebook.py` to change report content. It creates the PDF and `outputs/report-content.json` together. Then `scripts/build_publication.py` generates the EPUB, root index, browser report and book assets from that same content. Never edit those generated reading editions by hand. PDF page references in the source are checked against the 30-page structure.


### Affordability and policy extension / edition 3

Pages 25–30 cover household rent, utility and transport costs; housing delivery challenges; social and affordable rental, serviced infill and targeted support; rent-control design and the South African rental framework; proposed delivery monitoring; and seven linked policy references. Market observations are dated and geographically labelled. Budget examples are illustrative. Policy proposals are separate from current law, and no rent forecast or extra feasibility score has been added to the model.


## LinkedIn materials and downloadable bundles

- [Launch-pack index](linkedin/index.html): 15 portrait posters, a 15-page carousel, post, article, caption/alt-text pairs and enquiry replies.
- [Housing project ZIP](downloads/Cape-Town-Housing-Atlas.zip): the report, ebook, atlas, data and source.
- [LinkedIn pack ZIP](downloads/LinkedIn-Launch-Pack.zip): the standalone promotional materials and editable layouts.

The publication is edition 3 (September 2026). Pages 25–30 distinguish dated rental-market observations, illustrative household budgets, current legal guidance and policy proposals. The original GitHub-hosted portfolio links in the LinkedIn article may point to other revisions; this branch contains the edition shown here.
