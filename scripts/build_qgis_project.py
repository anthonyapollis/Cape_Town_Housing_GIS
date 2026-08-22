"""
Build a ready-to-open QGIS project for the Cape Town housing screen.

QGIS is where this analysis gets real basemaps: Esri World Imagery for
satellite, OSM for streets, and a hillshade for terrain -- all as XYZ tile
layers, which a sandboxed browser artifact can never load.

Run it either way:

  # headless, from a normal shell (needs QGIS on PYTHONPATH)
  python scripts/build_qgis_project.py

  # or paste into the QGIS Python console, which already has qgis.core
  exec(open('scripts/build_qgis_project.py').read())

Output: qgis/cape_town_housing.qgz

Layers, bottom to top:
  Esri World Imagery (satellite)      XYZ
  OSM Standard                        XYZ, off by default
  Municipal boundary                  real OSM admin_level=6 relation
  Coastline / rail                    real OSM geometry
  Site catchments 1 km                buffered in EPSG:32734 so metres are metres
  Candidate sites - suitability       graduated fill, size by dwelling yield
  Candidate sites - spatial redress   graduated fill on the redress index
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qgis"
OUT.mkdir(exist_ok=True)

try:
    from qgis.core import (
        QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
        QgsGraduatedSymbolRenderer, QgsRendererRange, QgsSymbol, QgsFillSymbol,
        QgsMarkerSymbol, QgsCoordinateReferenceSystem, QgsPalLayerSettings,
        QgsTextFormat, QgsVectorLayerSimpleLabeling, QgsProperty,
        QgsSymbolLayer, QgsLayerTreeLayer,
    )
    from qgis.PyQt.QtGui import QColor, QFont
except ImportError:
    sys.exit("QGIS Python bindings not found.\n"
             "Run this from the OSGeo4W shell, or paste it into the QGIS Python console:\n"
             "  exec(open(r'%s').read())" % (ROOT / 'scripts' / 'build_qgis_project.py'))

# Same palette as the atlas, validated for colour-vision deficiency.
TEAL = ["#D8EAE6", "#A9D4CC", "#6DB8AC", "#2F9A8B", "#00887A", "#005F55"]
PLUM = ["#EDE6F2", "#C9B8DE", "#9E86C4", "#7458AC", "#4B3FA8"]

XYZ = [
    ("Esri World Imagery (satellite)",
     "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D", True),
    ("OSM Standard",
     "https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png", False),
    ("Esri World Hillshade",
     "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D", False),
]


def graduated(layer, field, ramp, label, n=5, marker=True):
    """Equal-interval graduated renderer over `ramp`."""
    vals = [f[field] for f in layer.getFeatures() if f[field] is not None]
    lo, hi = min(vals), max(vals)
    step = (hi - lo) / n
    ranges = []
    for i in range(n):
        a, b = lo + i * step, lo + (i + 1) * step
        sym = (QgsMarkerSymbol.createSimple(
                   {"name": "circle", "color": ramp[min(i, len(ramp) - 1)],
                    "outline_color": "#ffffff", "outline_width": "0.4"})
               if marker else
               QgsFillSymbol.createSimple(
                   {"color": ramp[min(i, len(ramp) - 1)], "outline_color": "#ffffff"}))
        ranges.append(QgsRendererRange(a, b + (1e-6 if i == n - 1 else 0), sym,
                                       f"{a:.0f} – {b:.0f}"))
    r = QgsGraduatedSymbolRenderer(field, ranges)
    layer.setRenderer(r)
    layer.setName(label)
    return layer


def size_by_units(layer):
    """Data-defined marker size: sqrt scaling on dwelling yield."""
    sl = layer.renderer().sourceSymbol().symbolLayer(0)
    sl.setDataDefinedProperty(
        QgsSymbolLayer.PropertySize,
        QgsProperty.fromExpression('3 + sqrt("units_total") / 12'))


def label_by(layer, field, size=8):
    s = QgsPalLayerSettings()
    s.fieldName = field
    s.placement = QgsPalLayerSettings.AroundPoint
    fmt = QgsTextFormat()
    fmt.setFont(QFont("IBM Plex Sans", size))
    fmt.setSize(size)
    fmt.setColor(QColor("#0F1A17"))
    buf = fmt.buffer(); buf.setEnabled(True); buf.setSize(0.9)
    buf.setColor(QColor("#FFFFFF")); fmt.setBuffer(buf)
    s.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
    layer.setLabelsEnabled(True)


def main():
    headless = "qgis.utils" not in sys.modules
    if headless:
        QgsApplication.setPrefixPath(os.environ.get("QGIS_PREFIX_PATH", "/usr"), True)
        app = QgsApplication([], False)
        app.initQgis()

    proj = QgsProject.instance()
    proj.clear()
    proj.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    proj.setTitle("Cape Town Housing Ground")

    for name, url, visible in XYZ:
        lyr = QgsRasterLayer(f"type=xyz&url={url}&zmax=19&zmin=0", name, "wms")
        if lyr.isValid():
            proj.addMapLayer(lyr)
            node = proj.layerTreeRoot().findLayer(lyr.id())
            if node:
                node.setItemVisibilityChecked(visible)
        else:
            print("  ! basemap failed to load:", name)

    base = ROOT / "data" / "geo" / "basemap.geojson"
    if base.exists():
        for layer_name, style in (
                ("municipal_boundary", {"color": "0,0,0,0", "outline_color": "#4E5F5A",
                                        "outline_width": "0.5", "outline_style": "dash"}),
                ("coastline", {"color": "0,0,0,0", "outline_color": "#00887A",
                               "outline_width": "0.35"}),
                ("rail", {"color": "0,0,0,0", "outline_color": "#B4620F",
                          "outline_width": "0.3"})):
            uri = f"{base}|layername=basemap|subset=\"layer\" = '{layer_name}'"
            lyr = QgsVectorLayer(uri, layer_name.replace("_", " ").title(), "ogr")
            if lyr.isValid():
                lyr.setRenderer(lyr.renderer())
                lyr.renderer().setSymbol(QgsSymbol.defaultSymbol(lyr.geometryType()))
                lyr.renderer().symbol().setColor(QColor(style["outline_color"]))
                proj.addMapLayer(lyr)

    sites_path = ROOT / "outputs" / "candidate_sites.geojson"
    sites = QgsVectorLayer(str(sites_path), "sites", "ogr")
    if not sites.isValid():
        sys.exit(f"could not load {sites_path} - run suitability_model.py first")

    # 1 km catchment, buffered in UTM 34S so the radius is honestly metric
    try:
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
        utm = processing.run("native:reprojectlayer",
                             {"INPUT": str(sites_path), "TARGET_CRS": "EPSG:32734",
                              "OUTPUT": "memory:"})["OUTPUT"]
        buf = processing.run("native:buffer",
                             {"INPUT": utm, "DISTANCE": 1000, "SEGMENTS": 24,
                              "OUTPUT": "memory:"})["OUTPUT"]
        buf.setName("Site catchments (1 km)")
        buf.setRenderer(buf.renderer())
        buf.renderer().setSymbol(QgsFillSymbol.createSimple(
            {"color": "0,136,122,40", "outline_color": "#00887A", "outline_width": "0.26"}))
        proj.addMapLayer(buf)
    except Exception as exc:                       # processing is optional
        print("  ! skipped catchment buffers:", exc)

    redress = QgsVectorLayer(str(sites_path), "redress", "ogr")
    graduated(redress, "redress_index", PLUM, "Candidate sites — spatial redress")
    size_by_units(redress)
    proj.addMapLayer(redress)
    node = proj.layerTreeRoot().findLayer(redress.id())
    if node:
        node.setItemVisibilityChecked(False)

    graduated(sites, "suitability", TEAL, "Candidate sites — suitability")
    size_by_units(sites)
    label_by(sites, "name")
    proj.addMapLayer(sites)

    dest = OUT / "cape_town_housing.qgz"
    proj.write(str(dest))
    print("wrote", dest)
    print("layers:", len(proj.mapLayers()))

    if headless:
        app.exitQgis()


if __name__ == "__main__":
    main()
