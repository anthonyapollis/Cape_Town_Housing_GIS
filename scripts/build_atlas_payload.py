"""
Inline the model outputs and the OSM basemap into the atlas, and emit both builds.

The atlas has two destinations with different rules:

  docs/index.html          a complete standalone document, for local serving,
                           Git and Netlify. Needs its own <head> -- above all a
                           viewport meta, without which phones lay the page out
                           at 980px and zoom out.
  docs/_atlas.artifact.html  the same page as a bare body fragment, for
                           publishing as an Artifact, where the platform
                           generates <head> and rejects one of ours.

Both are generated from docs/_atlas.body.html, which is the source of truth.

Pipeline:
    python scripts/build_basemap.py        # OSM -> data/geo/basemap.json
    python scripts/suitability_model.py    # model -> outputs/*
    python scripts/build_atlas_payload.py  # both  -> docs/

Safe to run repeatedly; it replaces whatever currently follows `const DATA = `.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "_atlas.body.html"
STANDALONE = ROOT / "docs" / "index.html"
FRAGMENT = ROOT / "docs" / "_atlas.artifact.html"

SITE_COLS = [
    "site_id", "lat", "lon", "ndvi", "ndbi", "lst_anom_c", "impervious_pct",
    "flood_risk", "enviro_sensitivity", "contamination", "slope_pct", "bulk_infra",
    "social_facility", "delivery_complexity", "group_area_1950", "redress_index",
    "displacement_risk", "zoning_note",
]

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Land screening for low-income housing across the
 City of Cape Town: 30 candidate precincts scored on fourteen criteria, weighted twice
 -- once on land economics, once on undoing Group Areas geography.">
<meta name="color-scheme" content="light dark">
</head>
<body>
"""
FOOT = "\n</body>\n</html>\n"


def build_payload():
    rank = pd.read_csv(ROOT / "outputs" / "site_rankings.csv")
    sens = pd.read_csv(ROOT / "outputs" / "sensitivity.csv")[
        ["site_id", "rank_p05", "rank_p95", "pct_top10"]]
    isens = pd.read_csv(ROOT / "outputs" / "input_sensitivity.csv")[
        ["site_id", "in_rank_p05", "in_rank_p95", "in_pct_top10"]]
    src = pd.read_csv(ROOT / "data" / "candidate_sites.csv")[SITE_COLS]
    crit = pd.read_csv(ROOT / "outputs" / "criteria_scores.csv").drop(columns=["name"])

    df = (rank.merge(sens, on="site_id").merge(isens, on="site_id")
              .merge(src, on="site_id").merge(crit, on="site_id"))
    df.columns = [c.replace("score::", "s_") for c in df.columns]

    return {
        "sites": json.loads(df.to_json(orient="records")),
        "summary": json.loads((ROOT / "outputs" / "summary.json").read_text()),
        "base": json.loads((ROOT / "data" / "geo" / "basemap.json").read_text()),
    }


def main():
    payload = json.dumps(build_payload(), separators=(",", ":"))
    body = SOURCE.read_text(encoding="utf-8")

    marker = "const DATA = "
    start = body.index(marker)
    # The payload is one line, so the declaration ends at the newline -- NOT at the
    # first ";", which occurs inside the data ("Declared White 1966; ~60 000 removed").
    end = body.index("\n", start)
    assert body[end - 1] == ";", "const DATA must be one line ending in a semicolon"
    assert body.index("const SITES", start) > end, "unexpected layout around const DATA"
    body = body[:start] + marker + payload + body[end - 1:]

    non_ascii = [c for c in body if ord(c) > 127]
    assert not non_ascii, (f"{len(non_ascii)} non-ASCII chars: the Artifact build gets no "
                           "charset meta, so they would render as mojibake")

    FRAGMENT.write_text(body, encoding="utf-8")
    STANDALONE.write_text(HEAD + body + FOOT, encoding="utf-8")
    print(f"payload {len(payload):,} bytes")
    print(f"  {STANDALONE}  {len(HEAD + body + FOOT):,} bytes (standalone, has viewport meta)")
    print(f"  {FRAGMENT}  {len(body):,} bytes (Artifact fragment)")


if __name__ == "__main__":
    main()
