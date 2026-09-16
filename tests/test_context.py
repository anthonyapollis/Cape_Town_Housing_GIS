"""Check the geographic context independently against the saved points."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_atlas_payload import build_payload
from build_site_context import distance
D=build_payload();C=D['context'];S=D['sites']
def test_context_covers_every_precinct():
    assert set(C['sites'])=={s['site_id'] for s in S}
    assert len(C['stations'])==131 and len(C['facilities'])==1642

def test_nearest_stations_match_independent_distance_and_original_measurements():
    for s in S:
        station=C['sites'][s['site_id']]['nearest_station']
        nearest=min(distance(s['lat'],s['lon'],p['lat'],p['lon']) for p in C['stations'])
        assert abs(nearest-station['km'])<.000001
        assert abs(round(station['km'],2)-s['dist_transit_km'])<.00001

def test_facility_catchments_are_nested_and_reproducible():
    for s in S:
        c=C['sites'][s['site_id']]
        for category,kinds in [('schools',{'school'}),('health',{'clinic','hospital','doctors','pharmacy'})]:
            for radius in [1,2]:
                expected=sum(p['kind'] in kinds and distance(s['lat'],s['lon'],p['lat'],p['lon'])<=radius for p in C['facilities'])
                assert c[f'{category}_{radius}km']==expected
            assert c[f'{category}_1km']<=c[f'{category}_2km']

def test_context_thresholds_match_published_headlines():
    assert sum(C['sites'][s['site_id']]['nearest_station']['km']<=1 for s in S)==14
    assert sum(s['in_pct_top10']>=.9 for s in S)==7
