"""Build reproducible geographic context from the existing OSM snapshot."""
import json, math, csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def distance(a,b,c,d):
    p,q=math.radians(a),math.radians(c)
    v=math.sin((q-p)/2)**2+math.cos(p)*math.cos(q)*math.sin(math.radians(d-b)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(v)))
def points(filename):
    raw=json.loads((ROOT/'data/geo'/filename).read_text())
    result=[]
    for e in raw['elements']:
        c=e.get('center',e); tags=e.get('tags',{})
        if 'lat' not in c or 'lon' not in c: continue
        result.append(dict(lat=c['lat'],lon=c['lon'],name=tags.get('name','Unnamed mapped feature'),kind=tags.get('amenity',tags.get('railway','feature')),osm_id=str(e['id']),osm_type=e['type']))
    return result,raw.get('osm3s',{}).get('timestamp_osm_base','Date unavailable')
def main():
    stations,stamp=points('osm_transit.json'); facilities,_=points('osm_amenities.json')
    stations=[s for s in stations if s['kind'] in ['station','halt']]
    out={'snapshot':stamp,'stations':stations,'facilities':facilities,'sites':{}}
    for s in csv.DictReader((ROOT/'data/candidate_sites.csv').open()):
        def near(items):
            return sorted([dict(x,km=round(distance(float(s['lat']),float(s['lon']),x['lat'],x['lon']),6)) for x in items],key=lambda x:x['km'])
        rail=near(stations); amen=near(facilities)
        out['sites'][s['site_id']]={'nearest_station':rail[0], 'nearest_facilities':amen[:5], 'schools_1km':sum(x['kind']=='school' and x['km']<=1 for x in amen), 'schools_2km':sum(x['kind']=='school' and x['km']<=2 for x in amen),'health_1km':sum(x['kind'] in ['clinic','hospital','doctors','pharmacy'] and x['km']<=1 for x in amen),'health_2km':sum(x['kind'] in ['clinic','hospital','doctors','pharmacy'] and x['km']<=2 for x in amen)}
    (ROOT/'data/geo/site_context.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf8')
    print('Context:',len(stations),'rail points;',len(facilities),'mapped facilities;',len(out['sites']),'sites')
if __name__=='__main__':main()
