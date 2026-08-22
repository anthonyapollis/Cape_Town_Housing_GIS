/**
 * Cape Town Housing Suitability - Remote Sensing Layer
 * ----------------------------------------------------
 * Google Earth Engine script. Paste into https://code.earthengine.google.com/
 *
 * Replaces the DESKTOP-ESTIMATE columns in data/candidate_sites.csv
 * (ndvi, ndbi, lst_anom_c, impervious_pct) with measured values, and adds
 * slope/elevation from a real DEM plus a 4D built-up change signal.
 *
 * Export lands in Google Drive as candidate_sites_rs.csv; join on site_id.
 */

// ---------------------------------------------------------------- 1. Sites
var sites = ee.FeatureCollection([
  ee.Feature(ee.Geometry.Point([18.5230, -33.9070]), {site_id: 'S01', name: 'Wingfield'}),
  ee.Feature(ee.Geometry.Point([18.4930, -33.9040]), {site_id: 'S02', name: 'Ysterplaat'}),
  ee.Feature(ee.Geometry.Point([18.4380, -33.9160]), {site_id: 'S03', name: 'Culemborg'}),
  ee.Feature(ee.Geometry.Point([18.4630, -33.9280]), {site_id: 'S04', name: 'Salt River Market'}),
  ee.Feature(ee.Geometry.Point([18.4520, -33.9310]), {site_id: 'S05', name: 'Woodstock Hospital'}),
  ee.Feature(ee.Geometry.Point([18.4590, -33.9300]), {site_id: 'S06', name: 'Pickwick Road'}),
  ee.Feature(ee.Geometry.Point([18.4230, -33.9210]), {site_id: 'S07', name: 'Founders Garden'}),
  ee.Feature(ee.Geometry.Point([18.4180, -33.9070]), {site_id: 'S08', name: 'Helen Bowden'}),
  ee.Feature(ee.Geometry.Point([18.4180, -33.9130]), {site_id: 'S09', name: 'Prestwich Precinct'}),
  ee.Feature(ee.Geometry.Point([18.4310, -33.9290]), {site_id: 'S10', name: 'District Six'}),
  ee.Feature(ee.Geometry.Point([18.5040, -33.9400]), {site_id: 'S11', name: 'Conradie Park'}),
  ee.Feature(ee.Geometry.Point([18.4780, -33.9370]), {site_id: 'S12', name: 'Two Rivers'}),
  ee.Feature(ee.Geometry.Point([18.4880, -33.9250]), {site_id: 'S13', name: 'Ndabeni'}),
  ee.Feature(ee.Geometry.Point([18.5350, -33.9330]), {site_id: 'S14', name: 'Epping Market'}),
  ee.Feature(ee.Geometry.Point([18.5170, -33.9600]), {site_id: 'S15', name: 'Athlone Power Stn'}),
  ee.Feature(ee.Geometry.Point([18.6300, -33.8990]), {site_id: 'S16', name: 'Bellville CBD'}),
  ee.Feature(ee.Geometry.Point([18.5850, -33.9090]), {site_id: 'S17', name: 'Parow'}),
  ee.Feature(ee.Geometry.Point([18.6470, -33.9760]), {site_id: 'S18', name: 'Delft Symphony'}),
  ee.Feature(ee.Geometry.Point([18.5700, -34.0110]), {site_id: 'S19', name: 'Philippi East'}),
  ee.Feature(ee.Geometry.Point([18.7460, -34.0640]), {site_id: 'S20', name: 'Macassar'}),
  ee.Feature(ee.Geometry.Point([18.6690, -34.0350]), {site_id: 'S21', name: 'Kuyasa'}),
  ee.Feature(ee.Geometry.Point([18.4250, -34.1780]), {site_id: 'S22', name: 'Dido Valley'}),
  ee.Feature(ee.Geometry.Point([18.3620, -34.0270]), {site_id: 'S23', name: 'Imizamo Yethu'}),
  ee.Feature(ee.Geometry.Point([18.4400, -33.9270]), {site_id: 'S24', name: 'Sir Lowrys Road'}),
  ee.Feature(ee.Geometry.Point([18.8930, -34.0770]), {site_id: 'S25', name: 'Sir Lowrys Pass'}),
  ee.Feature(ee.Geometry.Point([18.6200, -34.0410]), {site_id: 'S26', name: 'Highlands Drive'}),
  ee.Feature(ee.Geometry.Point([18.6900, -34.0000]), {site_id: 'S27', name: 'Blue Downs'}),
  ee.Feature(ee.Geometry.Point([18.4900, -33.5680]), {site_id: 'S28', name: 'Atlantis'}),
  ee.Feature(ee.Geometry.Point([18.7180, -33.8460]), {site_id: 'S29', name: 'Wallacedene'}),
  ee.Feature(ee.Geometry.Point([18.5170, -33.8720]), {site_id: 'S30', name: 'Phoenix Milnerton'})
]);

var BUFFER_M = 500;                       // site catchment radius
var buffers  = sites.map(function (f) { return f.buffer(BUFFER_M); });
var metro    = ee.Geometry.Rectangle([18.30, -34.36, 18.98, -33.47]);

// ------------------------------------------------- 2. Sentinel-2 indices
// Summer window: peak thermal stress + minimum cloud over the Cape.
var S2_START = '2025-11-01', S2_END = '2026-03-31';

function maskS2(img) {
  var scl = img.select('SCL');
  var ok = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return img.updateMask(ok).divide(10000);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(metro)
  .filterDate(S2_START, S2_END)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(maskS2)
  .median();

var ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi');   // vegetation
var ndbi = s2.normalizedDifference(['B11', 'B8']).rename('ndbi');  // built-up
var ndwi = s2.normalizedDifference(['B3', 'B8']).rename('ndwi');   // surface water
var bsi  = s2.expression(
  '((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))',
  {SWIR: s2.select('B11'), RED: s2.select('B4'),
   NIR: s2.select('B8'),   BLUE: s2.select('B2')}).rename('bsi'); // bare soil

// Impervious proxy: built-up and not vegetated, as a 0-100 fraction.
var impervious = ndbi.gt(0.0).and(ndvi.lt(0.20)).rename('impervious').multiply(100);

// ------------------------------------------------- 3. Land surface temperature
// Landsat 9 thermal, summer mean, expressed as an anomaly vs the metro mean.
var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
  .filterBounds(metro)
  .filterDate(S2_START, S2_END)
  .filter(ee.Filter.lt('CLOUD_COVER', 20))
  .map(function (img) {
    return img.select('ST_B10').multiply(0.00341802).add(149.0)
              .subtract(273.15).rename('lst')
              .copyProperties(img, ['system:time_start']);
  }).mean();

var metroMeanLst = ee.Number(l9.reduceRegion({
  reducer: ee.Reducer.mean(), geometry: metro, scale: 100, maxPixels: 1e10
}).get('lst'));
var lstAnom = l9.subtract(ee.Image.constant(metroMeanLst)).rename('lst_anom_c');

// ------------------------------------------------- 4. Terrain (DEM)
var dem     = ee.Image('USGS/SRTMGL1_003');
var terrain = ee.Terrain.products(dem);
var slopePct = terrain.select('slope').multiply(Math.PI / 180).tan()
                      .multiply(100).rename('slope_pct');
var elev     = dem.rename('elev_m');

// Low-lying + wet = flood exposure. Height above nearest drainage would be
// better; SRTM elevation plus NDWI is the open-data stand-in.
var floodProxy = elev.lt(15).multiply(50)
  .add(ndwi.gt(0.0).multiply(50)).rename('flood_proxy');

// ------------------------------------------------- 5. 4D: built-up change
// Two epochs of the JRC Global Human Settlement built surface series.
var built2000 = ee.Image('JRC/GHSL/P2023A/GHS_BUILT_S/2000').select('built_surface');
var built2020 = ee.Image('JRC/GHSL/P2023A/GHS_BUILT_S/2020').select('built_surface');
var builtDelta = built2020.subtract(built2000).rename('built_delta_m2');

// ------------------------------------------------- 6. Zonal statistics
var stack = ndvi.addBands([ndbi, ndwi, bsi, impervious, lstAnom,
                           slopePct, elev, floodProxy, builtDelta]);

var stats = stack.reduceRegions({
  collection: buffers,
  reducer: ee.Reducer.mean(),
  scale: 20,
  tileScale: 4
});

print('Site remote-sensing statistics', stats);

Export.table.toDrive({
  collection: stats,
  description: 'candidate_sites_rs',
  fileFormat: 'CSV',
  selectors: ['site_id', 'name', 'ndvi', 'ndbi', 'ndwi', 'bsi', 'impervious',
              'lst_anom_c', 'slope_pct', 'elev_m', 'flood_proxy', 'built_delta_m2']
});

// ------------------------------------------------- 7. Visual QA layers
Map.centerObject(metro, 11);
Map.addLayer(ndvi, {min: 0, max: 0.7, palette: ['#8c510a', '#f6e8c3', '#1a9850']}, 'NDVI');
Map.addLayer(lstAnom, {min: -4, max: 6,
  palette: ['#2c7bb6', '#ffffbf', '#d7191c']}, 'LST anomaly (C)', false);
Map.addLayer(impervious, {min: 0, max: 100,
  palette: ['#ffffff', '#252525']}, 'Impervious %', false);
Map.addLayer(builtDelta, {min: 0, max: 4000,
  palette: ['#ffffff', '#fdae61', '#7b3294']}, 'Built-up growth 2000-2020', false);
Map.addLayer(buffers.style({color: '#00e0c6', fillColor: '00000000', width: 2}), {}, 'Sites');
