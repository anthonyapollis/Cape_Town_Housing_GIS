"""Publication integrity checks using only the Python standard library."""
import json,zipfile,posixpath,xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag in ['a','img','link']:
            v=a.get('href') or a.get('src')
            if v:self.links.append(v)
def parse(path):
    p=Links();p.feed(path.read_text(encoding='utf8'));return p

def test_report_has_all_chapters_and_all_precincts():
    chapters=json.loads((ROOT/'outputs/report-content.json').read_text(encoding='utf8'))
    assert [c['page'] for c in chapters]==list(range(1,31))
    index=next(b for b in chapters[22]['blocks'] if b['type']=='table')
    assert len(index['rows'])==30
    assert len({r[1] for r in index['rows']})==30

def test_epub_resources_and_spine_are_complete():
    with zipfile.ZipFile(ROOT/'outputs/housing-atlas-ebook.epub') as z:
        names=set(z.namelist())
        assert z.namelist()[0]=='mimetype'
        assert z.read('mimetype')==b'application/epub+zip'
        assert z.getinfo('mimetype').compress_type==zipfile.ZIP_STORED
        for name in names:
            if name.endswith(('.xhtml','.xml','.opf')):
                for el in ET.fromstring(z.read(name)).iter():
                    for key in ['href','src']:
                        val=el.get(key,'')
                        if val and not urlsplit(val).scheme and not val.startswith('#'):
                            assert posixpath.normpath(posixpath.join(posixpath.dirname(name),val.split('#')[0])) in names
        opf=ET.fromstring(z.read('OEBPS/content.opf'))
        assert len(opf.findall('{http://www.idpf.org/2007/opf}spine/{http://www.idpf.org/2007/opf}itemref'))==30

def test_publication_links_resolve_to_files_and_chapters():
    for source in [ROOT/'index.html',ROOT/'docs/report.html']:
        for link in parse(source).links:
            u=urlsplit(link)
            if u.scheme or u.netloc:continue
            target=(source.parent/unquote(u.path)).resolve() if u.path else source
            assert target.is_file(),(source.name,link)
            if u.fragment and target.suffix=='.html':assert unquote(u.fragment) in parse(target).ids,(source.name,link)
