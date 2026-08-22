"""
Turn raw Overpass/OSM downloads into a compact basemap for the atlas and QGIS.

Inputs  (data/geo/*.json, fetched by scripts/fetch_osm.sh)
    osm_coastline.json   natural=coastline ways over the metro bbox
    osm_admin.json       admin_level=6 relation, City of Cape Town
    osm_rail.json        main/branch rail + light rail

Outputs
    data/geo/basemap.geojson   real geometry, for QGIS / kepler / ArcGIS
    data/geo/basemap.json      simplified, rounded, for inlining in the atlas

Everything is real OSM geometry. The only processing is stitching coastline
ways end-to-end, Douglas-Peucker simplification, and coordinate rounding.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "geo"
BBOX = (18.26, -34.42, 19.05, -33.42)  # w, s, e, n


# ---------------------------------------------------------------- geometry
def perp(p, a, b):
    """Perpendicular distance from p to segment ab, in degrees."""
    (px_, py_), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px_ - ax, py_ - ay)
    t = max(0, min(1, ((px_ - ax) * dx + (py_ - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))


def simplify(pts, tol):
    """Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = perp(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def stitch(ways, tol=1e-7):
    """Join OSM ways head-to-tail into the longest continuous lines possible."""
    segs = [list(w) for w in ways if len(w) > 1]
    out = []
    while segs:
        cur = segs.pop(0)
        joined = True
        while joined:
            joined = False
            for i, s in enumerate(segs):
                if math.dist(cur[-1], s[0]) < tol:
                    cur += s[1:]; segs.pop(i); joined = True; break
                if math.dist(cur[-1], s[-1]) < tol:
                    cur += s[::-1][1:]; segs.pop(i); joined = True; break
                if math.dist(cur[0], s[-1]) < tol:
                    cur = s[:-1] + cur; segs.pop(i); joined = True; break
                if math.dist(cur[0], s[0]) < tol:
                    cur = s[::-1][:-1] + cur; segs.pop(i); joined = True; break
        out.append(cur)
    return out


def load_ways(fn):
    """Every way's geometry as [(lon, lat), ...]."""
    d = json.loads((GEO / fn).read_text())
    return [[(p["lon"], p["lat"]) for p in e.get("geometry", [])]
            for e in d["elements"] if e.get("type") == "way" and e.get("geometry")]


def load_relation_rings(fn, name_contains=None):
    """Outer rings of matching relations, from their member way geometries."""
    d = json.loads((GEO / fn).read_text())
    rings = []
    for e in d["elements"]:
        if e.get("type") != "relation":
            continue
        nm = e.get("tags", {}).get("name", "")
        if name_contains and name_contains.lower() not in nm.lower():
            continue
        outer = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                 for m in e.get("members", [])
                 if m.get("role") == "outer" and m.get("geometry")]
        for r in stitch(outer):
            if len(r) > 20:
                rings.append((nm, r))
    return rings


def inbox(pts):
    w, s, e, n = BBOX
    return [p for p in pts if w <= p[0] <= e and s <= p[1] <= n]


def rnd(pts, nd=4):
    return [[round(x, nd), round(y, nd)] for x, y in pts]


# ---------------------------------------------------------------- build
def main():
    feats_full, atlas = [], {}

    # --- coastline -------------------------------------------------------
    coast = [c for c in stitch(load_ways("osm_coastline.json")) if len(c) > 40]
    coast.sort(key=len, reverse=True)
    coast_s = [simplify(c, 0.0012) for c in coast[:8]]
    coast_s = [c for c in coast_s if len(c) > 6]
    atlas["coast"] = [rnd(c) for c in coast_s]
    for c in coast_s:
        feats_full.append({"type": "Feature", "properties": {"layer": "coastline"},
                           "geometry": {"type": "LineString", "coordinates": rnd(c, 6)}})
    print(f"coastline: {len(coast)} stitched lines -> {len(coast_s)} kept, "
          f"{sum(len(c) for c in coast_s)} points")

    # --- municipal boundary ---------------------------------------------
    rings = load_relation_rings("osm_admin.json", "Cape Town")
    if rings:
        nm, ring = max(rings, key=lambda r: len(r[1]))
        ring_s = simplify(ring, 0.002)
        atlas["boundary"] = rnd(ring_s)
        feats_full.append({"type": "Feature",
                           "properties": {"layer": "municipal_boundary", "name": nm},
                           "geometry": {"type": "Polygon", "coordinates": [rnd(ring, 6)]}})
        print(f"boundary:  {nm}, {len(ring)} pts -> {len(ring_s)}")

    # --- rail ------------------------------------------------------------
    rail = [inbox(r) for r in stitch(load_ways("osm_rail.json"))]
    rail = [simplify(r, 0.0018) for r in rail if len(r) > 25]
    rail = [r for r in rail if len(r) > 4]
    atlas["rail"] = [rnd(r) for r in rail]
    for r in rail:
        feats_full.append({"type": "Feature", "properties": {"layer": "rail"},
                           "geometry": {"type": "LineString", "coordinates": rnd(r, 6)}})
    print(f"rail:      {len(rail)} lines, {sum(len(r) for r in rail)} points")

    (GEO / "basemap.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": feats_full}))
    (GEO / "basemap.json").write_text(json.dumps(atlas, separators=(",", ":")))
    print("atlas payload:", len((GEO / 'basemap.json').read_text()), "bytes")


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(20000)
    main()
