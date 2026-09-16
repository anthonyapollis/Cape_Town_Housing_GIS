"""
Build a 3D + 4D KML for Google Earth Pro (and Google My Maps).

Google Earth gives what a browser artifact cannot: real satellite imagery, real
terrain, a true 3D camera, and a time slider. This script writes the sites into
that environment as extruded massing blocks.

  3D  each precinct becomes a square footprint sized by its developable area and
      extruded to storeys x 3.2 m, coloured by delivery tranche
  4D  each block carries a <TimeSpan>, so Google Earth's time slider runs the
      2027-2037 delivery programme
  +   a second folder extrudes the same footprints by SPATIAL REDRESS score, so
      you can fly the Group Areas geography rather than read it off a table

Output: outputs/cape_town_housing.kml  (drag into Google Earth Pro)
        outputs/cape_town_housing.kmz  (zipped, for sharing / My Maps import)
"""
import math
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRANCHE_WINDOW = {"Tranche 1 (2027-2029)": (2027, 2029),
                  "Tranche 2 (2030-2033)": (2030, 2033),
                  "Tranche 3 (2034-2037)": (2034, 2037)}
# KML colour is aabbggrr, not rrggbb.
TRANCHE_ABGR = {"Tranche 1 (2027-2029)": "cc957a00",   # teal
                "Tranche 2 (2030-2033)": "cc1c7ace",   # ochre
                "Tranche 3 (2034-2037)": "cce06c7b"}   # indigo
M_PER_DEG_LAT = 110574.0


def square(lat, lon, area_ha, alt):
    """A north-aligned square footprint of the given area, centred on the site."""
    side_m = math.sqrt(area_ha * 10_000)
    dlat = (side_m / 2) / M_PER_DEG_LAT
    dlon = (side_m / 2) / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
    ring = [(lon - dlon, lat - dlat), (lon + dlon, lat - dlat),
            (lon + dlon, lat + dlat), (lon - dlon, lat + dlat),
            (lon - dlon, lat - dlat)]
    return " ".join(f"{x:.6f},{y:.6f},{alt:.1f}" for x, y in ring)


def balloon(r):
    rows = [
        ("Suitability rank", f"#{r['rank']} of 30"),
        ("Rank once redress is priced in", f"#{r['rank_redress']}"
         + (f" ({r['rank_shift']:+d})" if r['rank_shift'] else " (no change)")),
        ("Impact rank (quality x yield)", f"#{r['impact_rank']}"),
        ("Group Areas Act designation", r["group_area_1950"]),
        ("Spatial redress score", f"{r['redress_index']}/100"),
        ("Displacement risk", f"{r['displacement_risk']}/100"),
        ("Zoning", f"{r['zone']} - " + (f"{r['height_storeys']} storeys as of right"
         if r['height_storeys'] else "NO residential right; rezoning required")),
        ("Buildable now", f"{int(r['units_asofright']):,} units"),
        ("Needs rezoning", f"{int(r['units_rezoning']):,} units"),
        ("Developable land", f"{r['dev_ha']} ha at {r['density_u_ha']} u/ha"),
        ("Dwelling yield", f"{int(r['units_total']):,} units"),
        ("Sub-R3 500 band", f"{int(r['units_social']):,} units"),
        ("Distance to CBD", f"{r['dist_cbd_km']} km"),
        ("Distance to transit", f"{r['dist_transit_km']} km"),
        ("Ownership", r["ownership"]),
        ("Delivery tranche", r["tranche"]),
    ]
    body = "".join(
        f'<tr><td style="padding:3px 10px 3px 0;color:#5a6b66">{escape(str(k))}</td>'
        f'<td style="padding:3px 0;font-weight:600">{escape(str(v))}</td></tr>'
        for k, v in rows)
    return (f'<![CDATA[<div style="font-family:Helvetica,Arial,sans-serif;font-size:13px">'
            f'<h3 style="margin:0 0 6px">{escape(r["name"])}</h3>'
            f'<table>{body}</table>'
            f'<p style="color:#7c8c87;font-size:11px;margin-top:8px">Criteria values are desktop '
            f'estimates pending survey. Group Areas designation is historical record.</p></div>]]>')


def placemark(r, alt, colour, timespan=True, suffix=""):
    a, b = TRANCHE_WINDOW[r["tranche"]]
    ts = (f"<TimeSpan><begin>{a}-01-01</begin></TimeSpan>" if timespan else "")
    return f"""    <Placemark>
      <name>{escape(r['name'])}{suffix}</name>
      <description>{balloon(r)}</description>
      {ts}
      <Style><PolyStyle><color>{colour}</color></PolyStyle>
        <LineStyle><color>ff1a1a1a</color><width>1.4</width></LineStyle></Style>
      <Polygon>
        <extrude>1</extrude><altitudeMode>relativeToGround</altitudeMode>
        <outerBoundaryIs><LinearRing><coordinates>
          {square(r['lat'], r['lon'], min(r['dev_ha'], 40), alt)}
        </coordinates></LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
"""


def main():
    df = pd.read_csv(ROOT / "outputs" / "site_rankings.csv").merge(
        pd.read_csv(ROOT / "data" / "candidate_sites.csv")[
            ["site_id", "lat", "lon", "group_area_1950", "redress_index", "displacement_risk"]],
        on="site_id")

    massing, redress, legal = [], [], []
    for _, r in df.iterrows():
        storeys = max(3, min(16, round(r["density_u_ha"] / 19)))
        massing.append(placemark(r, storeys * 3.2, TRANCHE_ABGR[r["tranche"]]))
        # What current zoning actually permits. Flat where the answer is nothing.
        permitted = min(storeys, r["height_storeys"])
        legal.append(placemark(r, max(permitted, 0.4) * 3.2,
                               "cc4a4a4a" if permitted == 0 else "cc957a00",
                               timespan=False, suffix=" - as of right"))
        # Redress folder: height IS the redress score, so the apartheid geography
        # reads as topography from the air.
        shade = "cc00887a" if r["redress_index"] >= 60 else "cc3f3fb4"
        redress.append(placemark(r, r["redress_index"] * 12, shade,
                                 timespan=False, suffix=" - redress"))

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Cape Town Housing Ground</name>
  <description>{escape('Land screening for low-income housing, 30 precincts. '
      'Massing folder is extruded by storeys and carries the 2027-2037 delivery '
      'programme on the time slider. Redress folder is extruded by spatial-redress '
      'score. Criteria values are desktop estimates pending survey.')}</description>
  <Folder>
    <name>Massing and delivery programme (3D + time slider)</name>
    <open>1</open>
{''.join(massing)}  </Folder>
  <Folder>
    <name>As of right (height = what current zoning permits)</name>
    <visibility>0</visibility>
{''.join(legal)}  </Folder>
  <Folder>
    <name>Spatial redress relief (height = redress score)</name>
    <visibility>0</visibility>
{''.join(redress)}  </Folder>
</Document>
</kml>
"""
    out = ROOT / "outputs"
    (out / "cape_town_housing.kml").write_text(kml, encoding="utf-8")
    # Fixed timestamp: a ZIP records mtime, so without this the KMZ is a new
    # file on every build and shows up as a spurious diff in every commit.
    with zipfile.ZipFile(out / "cape_town_housing.kmz", "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("doc.kml", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, kml)
    print(f"wrote {len(df)} precincts x 3 folders")
    print(" ", out / "cape_town_housing.kml")
    print(" ", out / "cape_town_housing.kmz")


if __name__ == "__main__":
    main()
