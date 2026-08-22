"""
Inline the model outputs and the OSM basemap into docs/index.html.

The atlas is published as a sandboxed artifact that cannot fetch anything at
runtime, so every byte it needs is embedded at build time. This script is the
last step of the pipeline:

    python scripts/build_basemap.py        # OSM -> data/geo/basemap.json
    python scripts/suitability_model.py    # model -> outputs/*
    python scripts/build_atlas_payload.py  # both  -> docs/index.html

It replaces whatever currently follows `const DATA = ` in docs/index.html, so it
is safe to run repeatedly.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SITE_COLS = [
    "site_id", "lat", "lon", "ndvi", "ndbi", "lst_anom_c", "impervious_pct",
    "flood_risk", "enviro_sensitivity", "contamination", "slope_pct", "bulk_infra",
    "social_facility", "delivery_complexity", "group_area_1950", "redress_index",
    "displacement_risk", "zoning_note",
]


def build_payload():
    rank = pd.read_csv(ROOT / "outputs" / "site_rankings.csv")
    sens = pd.read_csv(ROOT / "outputs" / "sensitivity.csv")[
        ["site_id", "rank_p05", "rank_p95", "pct_top10"]]
    src = pd.read_csv(ROOT / "data" / "candidate_sites.csv")[SITE_COLS]
    crit = pd.read_csv(ROOT / "outputs" / "criteria_scores.csv").drop(columns=["name"])

    df = rank.merge(sens, on="site_id").merge(src, on="site_id").merge(crit, on="site_id")
    df.columns = [c.replace("score::", "s_") for c in df.columns]

    return {
        "sites": json.loads(df.to_json(orient="records")),
        "summary": json.loads((ROOT / "outputs" / "summary.json").read_text()),
        "base": json.loads((ROOT / "data" / "geo" / "basemap.json").read_text()),
    }


def main():
    payload = json.dumps(build_payload(), separators=(",", ":"))
    page = ROOT / "docs" / "index.html"
    html = page.read_text(encoding="utf-8")

    marker = "const DATA = "
    start = html.index(marker)
    # The payload is emitted as a single line, so the declaration ends at the
    # newline -- NOT at the first ";", which appears inside the data itself
    # ("Declared White 1966; ~60 000 removed").
    end = html.index("\n", start)
    assert html[end - 1] == ";", "const DATA must be one line ending in a semicolon"
    assert html.index("const SITES", start) > end, "unexpected layout around const DATA"
    end -= 1

    html = html[:start] + marker + payload + html[end:]
    page.write_text(html, encoding="utf-8")

    non_ascii = [c for c in html if ord(c) > 127]
    assert not non_ascii, f"{len(non_ascii)} non-ASCII chars would mis-render without a charset meta"
    print(f"inlined {len(payload):,} bytes into {page} ({len(html):,} total)")


if __name__ == "__main__":
    main()
