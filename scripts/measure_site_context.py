"""
Replace three desktop estimates with measurements.

The screen originally carried analyst estimates for every criterion. Three of
them can be measured from open data without a Google Earth Engine account, so
they are, and the provenance table shrinks accordingly:

    dist_transit_km   -> great-circle distance to the nearest real OSM rail
                         station or halt (131 of them across the metro)
    social_facility   -> a 0-100 index built from the actual count of schools,
                         clinics, hospitals, doctors and pharmacies within
                         1 km and 2 km of the site (1 642 facilities)
    elev_m, slope_pct -> SRTM 30 m elevation at the site, and slope derived
                         from a 300 m cross sampled around it

Inputs (fetched by scripts/fetch_osm.sh, or the curl calls in the README):
    data/geo/osm_transit.json      railway=station|halt
    data/geo/osm_amenities.json    schools, clinics, hospitals, doctors, pharmacies
    data/geo/srtm_elevation.csv    written by --fetch-dem (OpenTopoData SRTM 30 m)

Usage:
    python scripts/measure_site_context.py --fetch-dem   # network, ~30 s
    python scripts/measure_site_context.py               # recompute from cache

Writes the measured columns back into data/candidate_sites.csv and records what
changed in outputs/measurement_log.csv.
"""
import argparse
import json
import math
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "geo"
SITES = ROOT / "data" / "candidate_sites.csv"

# Weight by how much each facility type matters to a household with no car.
FACILITY_WEIGHT = {"school": 1.0, "kindergarten": 0.6, "clinic": 1.2,
                   "hospital": 1.5, "doctors": 0.5, "pharmacy": 0.4}
DEM_OFFSET_M = 150.0


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_points(fn, want_tags=False):
    """Overpass nodes and ways (via `out center`) as (lat, lon, tags)."""
    d = json.loads((GEO / fn).read_text())
    pts = []
    for e in d["elements"]:
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        pts.append((lat, lon, e.get("tags", {}) if want_tags else None))
    return pts


def nearest_transit(df):
    stops = load_points("osm_transit.json")
    print(f"  transit stops: {len(stops)}")
    out = []
    for r in df.itertuples():
        d = min(haversine(r.lat, r.lon, a, b) for a, b, _ in stops)
        out.append(round(d, 2))
    return out


def facility_index(df):
    """Weighted facility count within 1 km (full) and 2 km (half), scaled 0-100."""
    fac = load_points("osm_amenities.json", want_tags=True)
    print(f"  facilities: {len(fac)}")
    raw = []
    for r in df.itertuples():
        score = 0.0
        for a, b, tags in fac:
            d = haversine(r.lat, r.lon, a, b)
            if d > 2.0:
                continue
            w = FACILITY_WEIGHT.get(tags.get("amenity"), 0.3)
            score += w if d <= 1.0 else w * 0.5
        raw.append(score)
    lo, hi = min(raw), max(raw)
    # Square-root compression: the tenth clinic matters less than the first.
    sq = [math.sqrt(v - lo) for v in raw]
    m = max(sq) or 1
    return [round(v / m * 100) for v in sq], raw


def fetch_dem(df):
    """SRTM 30 m at the site plus a 300 m cross, for elevation and real slope."""
    pts, index = [], []
    for r in df.itertuples():
        dlat = DEM_OFFSET_M / 110574.0
        dlon = DEM_OFFSET_M / (110574.0 * math.cos(math.radians(r.lat)))
        for p in [(r.lat, r.lon), (r.lat + dlat, r.lon), (r.lat - dlat, r.lon),
                  (r.lat, r.lon + dlon), (r.lat, r.lon - dlon)]:
            pts.append(p)
            index.append(r.site_id)

    vals = []
    for i in range(0, len(pts), 90):                      # API caps at 100 per call
        loc = "|".join(f"{a:.6f},{b:.6f}" for a, b in pts[i:i + 90])
        url = f"https://api.opentopodata.org/v1/srtm30m?locations={loc}"
        with urllib.request.urlopen(url, timeout=60) as f:
            j = json.load(f)
        if j.get("status") != "OK":
            raise RuntimeError(j.get("error", j["status"]))
        vals += [d["elevation"] for d in j["results"]]
        time.sleep(1.1)                                   # public API: 1 call/sec

    rows = {}
    for sid, v in zip(index, vals):
        rows.setdefault(sid, []).append(v)
    rec = []
    for sid, (c, n, s, e, w) in rows.items():
        rise = max(abs(n - s), abs(e - w))
        rec.append({"site_id": sid, "elev_srtm_m": round(c, 1),
                    "slope_srtm_pct": round(rise / (2 * DEM_OFFSET_M) * 100, 2)})
    out = pd.DataFrame(rec)
    out.to_csv(GEO / "srtm_elevation.csv", index=False)
    print(f"  SRTM: {len(pts)} samples -> {len(out)} sites")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-dem", action="store_true",
                    help="re-query OpenTopoData instead of using the cached CSV")
    args = ap.parse_args()

    df = pd.read_csv(SITES)
    before = df[["site_id", "name", "dist_transit_km", "social_facility",
                 "elev_m", "slope_pct"]].copy()

    print("measuring:")
    df["dist_transit_km"] = nearest_transit(df)
    df["social_facility"], raw_fac = facility_index(df)

    dem_path = GEO / "srtm_elevation.csv"
    dem = fetch_dem(df) if (args.fetch_dem or not dem_path.exists()) \
        else pd.read_csv(dem_path)
    dem = dem.set_index("site_id")
    df["elev_m"] = df.site_id.map(dem.elev_srtm_m).round().astype(int)
    df["slope_pct"] = df.site_id.map(dem.slope_srtm_pct)

    df.to_csv(SITES, index=False)

    log = before.merge(
        df[["site_id", "dist_transit_km", "social_facility", "elev_m", "slope_pct"]],
        on="site_id", suffixes=("_estimated", "_measured"))
    log["facilities_within_2km"] = [round(v, 1) for v in raw_fac]
    log.to_csv(ROOT / "outputs" / "measurement_log.csv", index=False)

    print("\nestimate vs measurement (Pearson r):")
    for c in ["dist_transit_km", "social_facility", "elev_m", "slope_pct"]:
        r = log[f"{c}_estimated"].corr(log[f"{c}_measured"])
        print(f"  {c:18} r = {r:+.3f}")
    print(f"\nwrote {SITES}\nwrote {ROOT / 'outputs' / 'measurement_log.csv'}")


if __name__ == "__main__":
    main()
