"""Create the illustrated field guide from the same payload as the web atlas."""
import sys, math, json
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from build_atlas_payload import build_payload
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'; VIS=OUT/'visuals'; VIS.mkdir(exist_ok=True)
D=build_payload(); S=D['sites']; C=D['context']; B=D['base']; SUM=D['summary']
INK='#183d35'; GREEN='#176b52'; PAPER='#f4f3ed'; MUTED='#60736c'; LIME='#c6de8b'; ORANGE='#be6b35'; BLUE='#567ca2'
for name,file in [('Sans','segoeui.ttf'),('Bold','segoeuib.ttf'),('Serif','georgia.ttf'),('Italic','georgiai.ttf')]:
    p=Path('C:/Windows/Fonts')/file
    if not p.exists():
        from matplotlib.font_manager import findfont, FontProperties
        family='DejaVu Serif' if name in ['Serif','Italic'] else 'DejaVu Sans'
        p=Path(findfont(FontProperties(family=family,weight='bold' if name=='Bold' else 'normal',style='italic' if name=='Italic' else 'normal')))
    pdfmetrics.registerFont(TTFont(name,str(p)))
W,H=595.276,841.89; M=44; PW=W-2*M
pdf=canvas.Canvas(str(OUT/'housing-atlas-ebook.pdf'),pagesize=(W,H))
pdf.setTitle('Cape Town: A Closer Look | Housing Opportunity Report')
pdf.setAuthor('Housing Opportunity Atlas | Analytical field guide')
page=0
RECORD=[];CURRENT=None;CAPTURE=True

def text(x,top,s,size=10,font='Sans',color=INK):
    if CAPTURE and CURRENT is not None and 180<=top<780:CURRENT['blocks'].append({'type':'heading' if size>=14 else 'text','text':str(s),'size':size})
    pdf.setFillColor(HexColor(color));pdf.setFont(font,size);pdf.drawString(x,H-top-size*.82,str(s))
def para(x,top,s,width=PW,size=10,color=MUTED,leading=None):
    if CAPTURE and CURRENT is not None and 130<=top<780:CURRENT['blocks'].append({'type':'paragraph','html':s,'size':size})
    style=ParagraphStyle('p',fontName='Sans',fontSize=size,leading=leading or size*1.55,textColor=HexColor(color),spaceAfter=0)
    p=Paragraph(s,style);w,h=p.wrap(width,900);p.drawOn(pdf,x,H-top-h);return h

def rect(x,top,w,h,fill=PAPER,stroke=None,r=0):
    pdf.setFillColor(HexColor(fill));pdf.setStrokeColor(HexColor(stroke or fill))
    if r:pdf.roundRect(x,H-top-h,w,h,r,fill=1,stroke=bool(stroke))
    else:pdf.rect(x,H-top-h,w,h,fill=1,stroke=bool(stroke))
def rule(top):
    pdf.setStrokeColor(HexColor('#d4dccd'));pdf.setLineWidth(.6);pdf.line(M,H-top,W-M,H-top)
def begin(kicker,title,sub=''):
    global page,CURRENT
    page+=1;CURRENT={'page':page,'title':title,'kicker':kicker,'blocks':[]};RECORD.append(CURRENT)
    rect(0,0,W,H);text(M,31,'CAPE TOWN / HOUSING OPPORTUNITY ATLAS',8,'Bold',GREEN)
    text(M,77,kicker.upper(),8,'Bold',GREEN);text(M,98,title,30,'Serif')
    if sub:para(M,142,sub,size=10)
    rule(788);text(M,802,'REPORT / SEPTEMBER 2026 / DESKTOP SCREENING',7,'Sans',MUTED)
    text(W-M-20,800,f'{page:02}',10,'Bold',GREEN)
    pdf.bookmarkPage(str(page));pdf.addOutlineEntry(title,str(page),0)
def end():pdf.showPage()
def foot(s,top=755):para(M,top,s,size=7.5,leading=10)
def image(name,top,w=PW,h=320,x=M):
    if CAPTURE and CURRENT is not None:CURRENT['blocks'].append({'type':'image','path':'visuals/'+name})
    pdf.drawImage(str(VIS/name),x,H-top-h,width=w,height=h,mask='auto')
def callout(top,title,body,h=91):
    rect(M,top,PW,h,'#e5ecd9',r=8);text(M+17,top+14,title,14,'Serif');para(M+17,top+39,body,PW-34,size=9)
def metric(x,top,value,label,width=150):
    global CAPTURE
    if CURRENT is not None:CURRENT['blocks'].append({'type':'metric','value':value,'label':label})
    old=CAPTURE;CAPTURE=False
    text(x,top,value,31,'Serif');para(x,top+43,label,width,size=8.5)
    CAPTURE=old
def rgb(s):return s

def mapdraw(x,top,w,h,sites=None,bounds=None,labels='rank',dark=False):
    if CAPTURE and CURRENT is not None:CURRENT['blocks'].append({'type':'map','page':page,'box':[x,top,w,h]})
    sites=S if sites is None else sites
    if bounds is None:bounds=(18.27,-34.25,18.98,-33.53)
    lo,bot,hi,up=bounds
    scale=min(w/((hi-lo)*.83),h/(up-bot));ox=x+(w-(hi-lo)*.83*scale)/2;oy=H-top-h+(h-(up-bot)*scale)/2
    def xy(p):return ox+(p[0]-lo)*.83*scale,oy+(p[1]-bot)*scale
    pdf.saveState();clip=pdf.beginPath();clip.rect(x,H-top-h,w,h);pdf.clipPath(clip,stroke=0,fill=0)
    rect(x,top,w,h,'#285849' if dark else '#eceee3')
    def line(coords,stroke,fill=None,width=.6):
        if not coords:return
        p=pdf.beginPath();p.moveTo(*xy(coords[0]));
        for pt in coords[1:]:p.lineTo(*xy(pt))
        if fill:p.close()
        pdf.setStrokeColor(HexColor(stroke));pdf.setLineWidth(width)
        if fill:pdf.setFillColor(HexColor(fill))
        pdf.drawPath(p,stroke=1,fill=bool(fill))
    ocean=B['coast'][0]+[[20,-36],[16,-36],[16,-32],[B['coast'][0][0][0],-32]]
    line(ocean,'#173e37' if dark else '#dfe9e9','#173e37' if dark else '#dfe9e9',width=0)
    for island in B['coast'][1:]:line(island,'#8aa5a1','#285849' if dark else '#eceee3')
    line(B['boundary'],'#6e927d' if dark else '#9ead91','#285849' if dark else '#e8eddf')
    for points in B['coast']:line(points,'#8aaba0' if dark else '#829f98')
    for points in B['rail']:line(points,'#688779' if dark else '#b5aa95',width=.5)
    if len(sites)==1:
        from build_site_context import distance
        site=sites[0];ct=C['sites'][site['site_id']];xx,yy=xy([site['lon'],site['lat']])
        pdf.setStrokeColor(HexColor('#729782'));pdf.setLineWidth(.6);pdf.setDash(2,3)
        for km in (1,2):pdf.circle(xx,yy,km/111.195*scale,stroke=1,fill=0)
        station=ct['nearest_station'];sx,sy=xy([station['lon'],station['lat']]);pdf.line(xx,yy,sx,sy);pdf.setDash()
        for f in C['facilities']:
            if distance(site['lat'],site['lon'],f['lat'],f['lon'])<=2:
                fx,fy=xy([f['lon'],f['lat']]);pdf.setFillColor(HexColor('#b68a49' if f['kind']=='school' else '#88719c'));pdf.circle(fx,fy,1.8,fill=1,stroke=0)
        pdf.setFillColor(HexColor(INK));pdf.rect(sx-3,sy-3,6,6,fill=1,stroke=0)
        pdf.setFont('Bold',6.5);pdf.drawString(sx+6,sy+4,station['name'])
    for s in sites:
        if not(lo<=s['lon']<=hi and bot<=s['lat']<=up):continue
        xx,yy=xy([s['lon'],s['lat']]);col=GREEN if s['rank']<=10 else ORANGE if s['rank']<=20 else BLUE
        pdf.setFillColor(HexColor(LIME if dark else col));pdf.setStrokeColor(HexColor(INK if dark else '#fffefa'));pdf.setLineWidth(.7);rad=4 if dark else 6
        pdf.circle(xx,yy,rad,fill=1,stroke=1)
        if labels and not dark:
            pdf.setFont('Bold',5.3);pdf.setFillColor(HexColor('#ffffff'));pdf.drawCentredString(xx,yy-1.7,str(s['rank']))
    # North arrow and a scale bar in a locally metric equirectangular view.
    pdf.setStrokeColor(HexColor('#b7cebc' if dark else MUTED));pdf.setFillColor(HexColor('#b7cebc' if dark else MUTED));pdf.setLineWidth(1)
    ax=x+w-20;ay=H-top-37;pdf.line(ax,ay,ax,ay+15);pdf.line(ax,ay+15,ax-3,ay+10);pdf.line(ax,ay+15,ax+3,ay+10);pdf.setFont('Bold',7);pdf.drawCentredString(ax,ay+20,'N')
    km=10 if hi-lo>.4 else 2 if hi-lo>.12 else 1;bar=km/111.195*scale
    if bar<w*.5:
        bx=x+17;by=H-top-h+20;pdf.line(bx,by,bx+bar,by);pdf.line(bx,by-2,bx,by+2);pdf.line(bx+bar,by-2,bx+bar,by+2);pdf.setFont('Sans',6);pdf.drawString(bx,by+5,f'{km} km')
    pdf.restoreState()
    return xy

def table(top,headers,rows,widths,row_height=31,font_size=8):
    global CAPTURE
    if CURRENT is not None:CURRENT['blocks'].append({'type':'table','headers':headers,'rows':rows})
    old=CAPTURE;CAPTURE=False
    rect(M,top,PW,29,'#e0e8d8')
    x=M
    for title,width in zip(headers,widths):para(x+7,top+8,escape(str(title)),width-14,7,GREEN,9);x+=width
    for i,row in enumerate(rows):
        y=top+29+i*row_height
        if i%2==0:rect(M,y,PW,row_height,'#ecefe5')
        x=M
        for value,width in zip(row,widths):
            hh=para(x+7,y+7,escape(str(value)),width-14,font_size,INK,font_size*1.35)
            assert hh<=row_height-10,(str(value),hh,row_height)
            x+=width
    CAPTURE=old
    return top+29+len(rows)*row_height

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelcolor':MUTED,'text.color':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':'#d0d8cb','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'figure.facecolor':PAPER,'axes.facecolor':PAPER,'savefig.facecolor':PAPER})
def savefig(fig,name):
    fig.savefig(VIS/(name+'.png'),dpi=210,bbox_inches='tight',pad_inches=.18)
    fig.savefig(VIS/(name+'.svg'),bbox_inches='tight',pad_inches=.18);plt.close(fig)
# Access chart
fig,ax=plt.subplots(figsize=(8,5.1));xs=[C['sites'][s['site_id']]['nearest_station']['km'] for s in S]
ax.axvspan(0,1,color='#e1ecd5',zorder=0);ax.scatter(xs,[s['units_total'] for s in S],s=65,c=[GREEN if s['rank']<=10 else ORANGE if s['rank']<=20 else BLUE for s in S],edgecolors=PAPER,linewidths=1)
for sid,offset in [('S01',(9,1)),('S02',(9,4)),('S07',(12,12)),('S16',(12,5))]:
    s=next(s for s in S if s['site_id']==sid);ax.annotate(s['name'],(C['sites'][sid]['nearest_station']['km'],s['units_total']),xytext=offset,textcoords='offset points',fontsize=8,color=INK)
far=max(S,key=lambda s:C['sites'][s['site_id']]['nearest_station']['km']);ax.annotate(far['name'],(C['sites'][far['site_id']]['nearest_station']['km'],far['units_total']),xytext=(-10,12),ha='right',textcoords='offset points',fontsize=8)
ax.set(xlabel='Straight-line distance to nearest mapped rail station (km)',ylabel='Modelled homes',ylim=(-600,28000),xlim=(-.2,max(xs)+.7));ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v/1000:g}k'));ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);fig.tight_layout();savefig(fig,'access-and-capacity')
# Rank shifts
ss=sorted(S,key=lambda s:abs(s['rank']-s['rank_redress']),reverse=True)[:14];ss=sorted(ss,key=lambda s:s['rank'])
fig,ax=plt.subplots(figsize=(8,5.2));ys=np.arange(len(ss))
for y,s in zip(ys,ss):ax.plot([s['rank'],s['rank_redress']],[y,y],color='#c6cebf',lw=3)
ax.scatter([s['rank'] for s in ss],ys,c=BLUE,s=45,label='Efficiency',zorder=3);ax.scatter([s['rank_redress'] for s in ss],ys,c=GREEN,s=45,label='Redress',zorder=4)
ax.set_yticks(ys,[s['name'] for s in ss]);ax.invert_yaxis();ax.set(xlim=(0,31),xlabel='Rank in the full set of 30 (1 is highest)');ax.grid(axis='x',alpha=.15);ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.11),ncol=2);fig.tight_layout();savefig(fig,'scenario-rank-shifts')
# Uncertainty intervals
ss=sorted(S,key=lambda s:s['rank'])[:12];fig,ax=plt.subplots(figsize=(8,5.5))
for y,s in enumerate(ss):
    ax.plot([s['rank_p05'],s['rank_p95']],[y-.12]*2,color=BLUE,lw=4,solid_capstyle='round',label='Weight noise' if y==0 else None)
    ax.plot([s['in_rank_p05'],s['in_rank_p95']],[y+.12]*2,color=GREEN,lw=4,solid_capstyle='round',label='Input noise' if y==0 else None)
    ax.scatter([s['rank']],[y],c=INK,s=15,zorder=5)
ax.set_yticks(range(len(ss)),[s['name'] for s in ss]);ax.invert_yaxis();ax.set(xlim=(.5,20.5),xlabel='Efficiency rank: 5th-95th percentile interval');ax.grid(axis='x',alpha=.15);ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.11),ncol=2);fig.tight_layout();savefig(fig,'ranking-uncertainty')
# Capacity chart
ss=sorted(S,key=lambda s:s['units_total'],reverse=True)[:10];fig,ax=plt.subplots(figsize=(8,4.6));ax.barh([s['name'] for s in ss],[s['units_total'] for s in ss],color=[GREEN]+['#93b087']*9,height=.6);ax.invert_yaxis();ax.set_xlabel('Modelled homes (assumed developable area x density)');ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v/1000:g}k'));ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
for i,s in enumerate(ss):ax.text(s['units_total']+240,i,f"{s['units_total']:,}",va='center',fontsize=8)
ax.set_xlim(0,29500);fig.tight_layout();savefig(fig,'modelled-capacity')
# Cover
page=1;CURRENT={'page':1,'title':'Cape Town. A closer look.','kicker':'Housing opportunity report','blocks':[]};RECORD.append(CURRENT);rect(0,0,W,H,INK);text(M,44,'HOUSING OPPORTUNITY ATLAS',9,'Bold',LIME);text(M,114,'Cape Town.',57,'Serif','#fffefa');text(M,180,'A closer look.',52,'Italic',LIME)
para(M,264,'Better located homes. Better connected lives.<br/>A housing opportunity report: 30 candidate precincts, rental affordability and practical policy choices.',390,12,'#d9e4d7',19)
mapdraw(224,345,340,390,dark=True,labels=None)
text(M,400,'30',48,'Serif',LIME);para(M,457,'CANDIDATE<br/>PRECINCTS',145,9,'#d9e4d7')
text(M,520,'14',48,'Serif',LIME);para(M,577,'SCREENING<br/>CRITERIA',145,9,'#d9e4d7')
text(M,730,'MAPS / AFFORDABILITY / POLICY / EVIDENCE',9,'Bold',LIME);para(M,764,'September 2026 edition. Desktop screening, not a feasibility study.<br/>OSM geography: 30 August 2026 snapshot. Model inputs are partly estimated.',PW,8,'#d9e4d7',12)
pdf.bookmarkPage('1');pdf.addOutlineEntry('Cape Town. A closer look.','1',0);end()
# Publication front matter: pages 2-6.
begin('Contents','A guide to the report.','Follow a question, move between the evidence, and return to the index. Page numbers are clickable.')
contents=[('Executive summary',3),('Decision pathways and recommendations',4),('Scope and analytical method',5),('Criteria, weights and provenance',6),('Metro map',7),('Inner-city map',8),('Rail access and housing capacity',9),('Efficiency and redress rankings',10),('Ranking uncertainty',11),('Site profiles: Founders Garden / Bellville / Wingfield',12),('Capacity concentration',15),('Regional portfolio',16),('Evidence gaps and decision gates',17),('Verification programme',18),('Complete site directory',19),('Methods and limitations',21),('Sources and references',22),('Alphabetical site index',23),('Subject index',24),('Rental affordability and household budgets',25),('Housing challenges and evidence gaps',26),('Solutions and delivery trade-offs',27),('Rent controls and tenant protection',28),('Implementation and outcome dashboard',29),('Policy sources',30)]
for i,(title,target) in enumerate(contents):
    y=193+i*21
    text(M,y,title,9);text(W-M-22,y,str(target),9,'Bold',GREEN)
    pdf.linkRect('',str(target),(M,H-y-17,W-M,H-y+2),relative=0,thickness=0)
    pdf.setStrokeColor(HexColor('#dce1d4'));pdf.setLineWidth(.3);pdf.line(M,H-y-18,W-M,H-y-18)
foot('Reading formats: this indexed PDF, a reflowable EPUB and a browser edition. The interactive atlas remains the place to filter and inspect sites.');end()

begin('Executive summary','Where the evidence points.','The screening identifies different kinds of opportunity. It does not establish a development-ready pipeline.')
near=[s for s in S if C['sites'][s['site_id']]['nearest_station']['km']<=1]
stable=[s for s in S if s['in_pct_top10']>=.9]
metric(M,194,f"{SUM['total_units_potential']:,}",'modelled homes across 30 precincts');metric(228,194,f'{len(near)} / 30','within 1 km of mapped rail');metric(410,194,str(len(stable)),'stable top-ten sites',130)
findings=[('1 / Access and capacity answer different questions.',f"Founders Garden ranks first in both lenses, with 528 modelled homes. Wingfield accounts for 25,200 homes ({25200/SUM['total_units_potential']*100:.1f}% of the total), but its efficiency rank is eighth and its input top-ten stability is {next(s['in_pct_top10'] for s in S if s['site_id']=='S01')*100:.1f}%. Neither measure alone is a delivery recommendation."),('2 / The shortlist depends on contested inputs.',f"Seven sites retain an efficiency top-ten place in at least 90% of input-noise draws. Nine do so under weight changes. The average input-driven 5th-95th percentile rank span is {SUM['input_rank_swing_mean']:.1f} places. Input verification deserves priority over further fine-tuning of weights."),('3 / Proximity is useful, but incomplete.',f"The {len(near)} precincts within 1 km of mapped rail contain {sum(s['units_total'] for s in near):,} modelled homes. This says nothing about service operation, barriers, walking routes or station capacity. Nearby facility counts likewise do not measure places available to new households.")]
y=301
for title,body in findings:
    text(M,y,title,13,'Bold',GREEN);hh=para(M,y+26,body,PW,10);y+=hh+53
callout(658,'Recommended decision','Progress a small, mixed verification shortlist across access, scale and redress. Release further investigation effort only when parcel, tenure, hazard and servicing evidence supports it.',85)
foot('All headline results refer to the existing 30-site model and the saved OSM snapshot; they are not independently verified supply forecasts.');end()

begin('Recommendations','Three investigation pathways.','These are proposed evidence-gathering tracks, not an approved priority list or funded delivery programme.')
tracks=[('01 / Access-led verification','Founders Garden / Bellville CBD','Both remain in the efficiency top ten throughout the estimated-input simulations. Founders Garden ranks 1 in both lenses; Bellville ranks 2 for efficiency and 3 for redress.','Confirm parcel extent and tenure, current occupancy, pedestrian connections and engineering headroom. Strong access cannot substitute for these checks.'),('02 / Strategic capacity','Wingfield / Ysterplaat','Together these two precincts contribute 38,500 modelled homes, approximately 30% of the portfolio. Their large assumed areas make the portfolio sensitive to land availability and usable extent.','Resolve land-release and ownership assumptions, map constraints and investigate remediation and bulk services before treating modelled yield as achievable.'),('03 / Redress-sensitive review','Culemborg / Helen Bowden / District Six','Culemborg moves from rank 18 to 10 under redress; Helen Bowden moves from 15 to 8. District Six ranks 3 for efficiency and 2 for redress. These sites illustrate why one weighting is insufficient.','Verify occupancy, restitution and tenure context through appropriate records and engagement. Test whether proposed housing would improve access without causing displacement.')]
y=193
for title,names,why,action in tracks:
    text(M,y,title,17,'Serif',GREEN);text(M,y+29,names,10,'Bold');h=para(M,y+51,why,PW,9.5);h2=para(M,y+57+h,'Next evidence: '+action,PW,9.5);y+=h+h2+87
foot('Selection logic is explicit: stable access leaders, the two largest capacity inputs, and sites with material redress movement or a strong redress rank.');end()

begin('Scope & method','What this study can answer.','A comparative desktop screening of 30 candidate precincts across Cape Town, using an existing MCDA model.')
text(M,192,'Decision question',15,'Serif',GREEN);para(M,218,'Which candidate precincts justify closer investigation when geographic access, land supply, delivery burdens and spatial redress are considered together?',PW,10)
steps=[('01 / Assemble the candidate set','The source CSV provides location, area, ownership, typology and criterion inputs. This is a supplied candidate set; it is not an exhaustive inventory of municipal land.'),('02 / Derive access and normalise criteria','Job access uses eight employment nodes and assumed job weights. Rail distance is computed from coordinates. Fourteen criteria are normalised within the 30-site set; cost criteria are reversed.'),('03 / Apply two value choices','Efficiency and redress each sum to 100% weight. Both use the same candidate set. Relative scores cannot be compared directly with a different city or a different candidate universe.'),('04 / Separate yield from suitability','Modelled homes equal assumed developable hectares multiplied by typology density. The separate impact measure combines suitability and the logarithm of housing yield; it is not a financial return.'),('05 / Stress-test and inspect','Weight and input perturbations test rank stability. The atlas adds named station proximity and unweighted facility context. It does not run a transport network or engineering feasibility model.')]
y=285
for title,body in steps:
    text(M,y,title,11,'Bold');h=para(M,y+22,body,PW,9.5);y+=h+39
foot('Analytical unit: a precinct point. Spatial extents, developable area and rights require parcel-level validation. No travel-time, cost-benefit or demand model is claimed.');end()

begin('Criteria & assumptions','What carries the weight.','Weights sum to 100% in each lens. All normalised scores run from 0 to 100 within this candidate set.')
prov={'Job accessibility':'Derived; assumed job weights','Transit access':'Measured straight-line proximity','Developable land supply':'Input; area unverified','Land cost':'Input; land value unverified','Bulk infrastructure':'Desktop estimate','Flood / water risk':'Desktop estimate','Terrain buildability':'Derived from SRTM samples','Environmental constraint':'Desktop estimate','Contamination burden':'Desktop estimate','Social facility access':'Derived from mapped facilities','Heat / green deficit':'Desktop estimate','Delivery complexity':'Desktop estimate','Spatial redress':'Desktop estimate','Displacement risk':'Desktop estimate'}
rows=[[k,prov[k],f"{SUM['scenarios']['efficiency'][k]*100:.0f}%",f"{SUM['scenarios']['redress'][k]*100:.0f}%"] for k in SUM['scenarios']['efficiency']]
table(192,['CRITERION','EVIDENCE BASIS','EFF.','REDRESS'],rows,[177,213,56,PW-446],32,8)
para(M,690,'Eight qualitative criteria remain desktop estimates. The six other criteria include derivations from inputs whose accuracy still needs checking; they should not all be read as field measurements.',PW,9.5)
foot('Source: suitability_model.py and summary.json. Weights are the existing project choices; this report does not claim an independently validated AHP elicitation.');end()

near=len(near)
# 3
begin('01 / Metro geography','One city. Many trade-offs.','Candidate points shown on OSM municipal, coastal and rail geometry. Numbers are efficiency ranks.')
mapdraw(M,187,PW,481)
for x,col,label in [(M,GREEN,'Ranks 1-10'),(M+145,ORANGE,'Ranks 11-20'),(M+295,BLUE,'Ranks 21-30')]:
    rect(x,683,8,8,col,r=4);text(x+16,681,label,8)
para(M,714,'The inner-city concentration is enlarged on the next page. The metro view retains peripheral sites so their distance from central employment is visible.',PW,9)
foot('Map: OpenStreetMap contributors, ODbL. Points are precinct coordinates; neither markers nor municipal outlines are parcel boundaries.');end()
# 4
begin('02 / Inner-city detail','Read the close-up.','The dense central cluster needs its own scale. Ranks refer to the efficiency lens.')
central=[s for s in S if 18.40<=s['lon']<=18.48 and -33.97<=s['lat']<=-33.89]
mapdraw(M,189,PW,313,central,(18.40,-33.97,18.48,-33.89))
cols=[sorted(central,key=lambda s:s['rank'])[::2],sorted(central,key=lambda s:s['rank'])[1::2]]
for j,col in enumerate(cols):
    for i,s in enumerate(col):text(M+j*258,524+i*25,f"{s['rank']:02}  {s['name']}",9)
para(M,708,'Small central sites can score strongly on access while contributing less housing capacity than large strategic precincts. Location and scale need separate readings.',PW,9)
foot('Source: saved precinct coordinates and OSM geometry. Rank numbers are identifiers on this plate, not measures of buildability.');end()
# 5
begin('03 / Geo intelligence','Access is not the same as scale.','The green band marks sites within 1 km of a mapped rail point, measured in a straight line.')
image('access-and-capacity.png',193,h=348)
callout(571,f'{near} of 30 precincts fall within the 1 km rail threshold.','Founders Garden combines a central location with modest modelled yield. Wingfield contributes the largest assumed capacity, with a longer straight-line rail connection. Neither pattern settles a delivery decision.',116)
foot('Sources: candidate coordinates; 131 OSM station/halt points; original area and density assumptions. Rail presence does not verify an operating service.');end()
# 6
begin('04 / Ranking lenses','Values change the shortlist.','The fourteen largest rank movements between the efficiency and spatial-redress weightings.')
image('scenario-rank-shifts.png',190,h=373)
callout(590,'Treat scenario movement as a question for review.','Redress adds an explicit spatial-redress weight of 17% and a displacement-risk weight of 6%. Those criterion scores are analyst estimates. A change in rank reveals sensitivity to these choices, not independent evidence of suitability.',110)
foot('Source: outputs/site_rankings.csv and outputs/summary.json. Both lenses rank the same 30 sites. Chart is a selected set of the largest movements.');end()
# 7
begin('05 / Uncertainty','A stable rank is not a ready site.','The twelve highest efficiency-ranked precincts. Dots show the base rank; lines show simulated rank intervals.')
image('ranking-uncertainty.png',193,h=379)
callout(601,'7 stable sites under input noise. 9 under weight noise.','Stability means retaining a top-ten position in at least 90% of draws. The weight test uses 5,000 draws; the estimated-input test uses 2,000. These are conditional simulations, not probabilities of approval or delivery.',107)
foot('Sources: sensitivity.csv and input_sensitivity.csv. Tests apply to the efficiency ranking. Intervals are the 5th-95th percentiles.');end()
# 8-10 profiles
profiles=[('S07','A central, compact opportunity.','Its leading score reflects strong access in the existing model. The small assumed area limits the scale of housing contribution.','Confirm the parcel extent, existing use, tenure and service capacity; check the walking connection to Cape Town Station.'),('S16','An employment-centre candidate.','Bellville CBD combines high modelled suitability with materially more assumed capacity than the small inner-city sites.','Verify redevelopment availability, existing occupancy, municipal capacity and actual pedestrian links to rail and local employment.'),('S01','Scale brings a larger evidence burden.','Wingfield has the largest assumed developable area and yield in this dataset. Its scale should be assessed alongside tenure, remediation and infrastructure questions.','Establish land-release feasibility and parcel rights; commission contamination, flood and infrastructure checks before interpreting capacity as deliverable.')]
for sid,headline,reading,nextstep in profiles:
    s=next(s for s in S if s['site_id']==sid);ct=C['sites'][sid];st=ct['nearest_station']
    begin('06 / Site profile / '+sid,s['name'],headline)
    metric(M,195,str(s['rank']),'efficiency rank');metric(220,195,str(s['rank_redress']),'redress rank');metric(395,195,f"{s['units_total']:,}",'modelled homes',150)
    mapdraw(M,302,245,260,[s],(s['lon']-.04,s['lat']-.032,s['lon']+.04,s['lat']+.032))
    CURRENT['blocks'].append({'type':'table','headers':['Geographic context','Value'], 'rows':[['Nearest mapped station',st['name']],['Straight-line rail distance',f"{st['km']:.2f} km"],['Schools / health within 2 km',f"{ct['schools_2km']} / {ct['health_2km']} features"],['Input top-ten stability',f"{round(s['in_pct_top10']*100)}% of draws"],['Assumed area / density',f"{s['dev_ha']} ha / {s['density_u_ha']} units/ha"]]})
    CAPTURE=False
    tx=315;text(tx,304,'GEOGRAPHIC CONTEXT',8,'Bold',GREEN)
    for y,title,value in [(333,'Nearest mapped station',st['name']),(381,'Straight-line rail distance',f"{st['km']:.2f} km"),(429,'Schools / health within 2 km',f"{ct['schools_2km']} / {ct['health_2km']} features"),(477,'Input top-ten stability',f"{round(s['in_pct_top10']*100)}% of draws"),(525,'Assumed area / density',f"{s['dev_ha']} ha / {s['density_u_ha']} units/ha")]:
        text(tx,y,title,8,'Sans',MUTED);para(tx,y+15,escape(value),230,11,INK,14)
    CAPTURE=True
    text(M,572,'Rings: 1 / 2 km. Square: mapped station. Dots: facilities.',7,'Sans',MUTED)
    para(M,592,reading,PW,9.5)
    callout(646,'What to verify next',nextstep,88)
    foot('Rail and facility context: saved OSM snapshot. Area, density, ownership and zoning are project inputs. The map shows a candidate point, not a site boundary.');end()
# 11
begin('07 / Capacity','Large sites dominate the total.','Ten largest modelled yields. Capacity is the product of assumed developable hectares and typology density.')
image('modelled-capacity.png',191,h=338)
large=sorted(S,key=lambda s:s['units_total'],reverse=True)[:3];share=sum(s['units_total'] for s in large)/SUM['total_units_potential']*100
callout(563,f'The three largest precincts represent {share:.0f}% of modelled capacity.','This concentration means errors in a few area or density assumptions can materially change the portfolio total. Treat the 126,380-home headline as a scenario total, not a supply commitment.',110)
para(M,698,'The social-housing share is also an assumption: the original model assigns 65% of units to its target income band. No demand or funding validation is implied.',PW,9)
foot('Source: outputs/site_rankings.csv. No municipal zoning record or surveyed developable-area polygon was joined to this calculation.');end()
# Additional analytical and decision material: pages 16-18.
begin('Regional portfolio','Where the modelled capacity sits.','Subregions are the source model groupings. They are not presented as official municipal planning districts.')
from collections import defaultdict
regions=defaultdict(list)
for site in S:regions[site['subregion']].append(site)
rows=[]
for region,sites in sorted(regions.items(),key=lambda x:sum(s['units_total'] for s in x[1]),reverse=True):
    homes=sum(s['units_total'] for s in sites)
    rows.append([region,str(len(sites)),f'{homes:,}',f'{homes/SUM["total_units_potential"]*100:.1f}%',str(sum(C['sites'][s['site_id']]['nearest_station']['km']<=1 for s in sites)),str(sum(s['in_pct_top10']>=.9 for s in sites))])
table(193,['SOURCE SUBREGION','SITES','HOMES*','SHARE','RAIL <1 KM','STABLE**'],rows,[154,43,89,62,79,PW-427],33,8)
callout(620,'Northern Metro contains 46.1% of modelled capacity.','Its seven candidate precincts contribute 58,280 assumed homes. This concentration reflects which sites and areas entered the model; it does not establish that this is the optimal geographic allocation of housing.',101)
foot('*Assumed capacity. **Efficiency top-ten membership in at least 90% of input-noise draws. Rail counts refer to precinct points, not homes or residents.');end()

begin('Evidence gaps','Separate a score from a decision.','A practical boundary between what the current screening supports and what remains to be established.')
rows=[['Land extent / availability','Candidate location and an assumed developable area.','Verified parcel geometry, ownership and availability.','Do not treat hectares as confirmed supply.'],['Planning rights','An analyst-assigned zone and a modelled capacity split.','Current municipal zoning records, overlays and applicable rights.','Do not describe the output as approved yield.'],['Transport access','Distance to a mapped station or halt.','Operating service, pedestrian routes, barriers and frequency.','Do not report walking or journey times.'],['Facilities','Mapped school and health features near the point.','Capacity, access rules, condition and duplication review.','Counts do not establish service adequacy.'],['Hazards / services','Estimated flood, environmental, contamination and infrastructure scores.','Official layers, site investigation and engineering assessment.','Do not substitute the index for a technical study.'],['People / redress','Analyst redress and displacement scores.','Occupancy, tenure, restitution context and community engagement.','Do not infer consent or social acceptability.']]
table(193,['DECISION AREA','CURRENT EVIDENCE','REQUIRED NEXT EVIDENCE','INTERPRETATION LIMIT'],rows,[104,139,147,PW-390],78,8)
para(M,705,'A material contradiction should trigger a review of the input and re-run of the model, not an attempt to explain away the new evidence.',PW,9.5)
foot('Proposed decision gates for further investigation. No municipality, owner or community has endorsed a site through this report.');end()

begin('Verification programme','A sequence that can be audited.','Suggested responsibilities describe functions, not named or appointed delivery partners.')
rows=[['01 / Establish the land','GIS / land administration','Parcel overlay; tenure and ownership evidence; verified availability; current zoning record.','Pause if the assumed area or availability cannot be established.'],['02 / Check real access','Transport / social planning','Station service check; walkable routes and barriers; facility capacity and access review.','Re-score access if a mapped feature is unusable or misleading.'],['03 / Test constraints','Engineering / environmental team','Flood and environmental overlays; contamination review; servicing assessment; usable area.','Revise developable extent and costs before refining housing yield.'],['04 / Review and re-rank','Planning / community engagement','Document occupancy, rights and engagement; update assumptions; re-run both lenses and sensitivity.','Record changes and only then agree the next investigation shortlist.']]
table(193,['GATE','PROPOSED FUNCTION','EVIDENCE TO RETAIN','DECISION RULE'],rows,[91,101,173,PW-365],96,8.5)
callout(638,'Keep a change register.','Record site ID, input field, old value, replacement value, source, source date, reviewer and reason. Rebuild maps, charts and the report from the same versioned data.',93)
foot('Sequence is indicative. It is not a project schedule, budget, procurement instruction or substitute for professional and community review.');end()

# 12-13 directory
for part in range(2):
    begin('08 / Site directory',f'The portfolio / {part*15+1:02}-{part*15+15:02}','Efficiency order. Rail distances are straight-line; stability is the input-noise share in the top ten.')
    CURRENT['blocks'].append({'type':'table','headers':['Rank / site','Subregion','Redress rank','Modelled homes','Rail km','Stability'], 'rows':[[str(s['rank'])+' / '+s['name'],s['subregion'],str(s['rank_redress']),f"{s['units_total']:,}",f"{C['sites'][s['site_id']]['nearest_station']['km']:.2f}",f"{round(s['in_pct_top10']*100)}%"] for s in sorted(S,key=lambda s:s['rank'])[part*15:part*15+15]]})
    CAPTURE=False
    top=193;rect(M,top,PW,30,'#e0e8d8')
    for x,label in [(M+8,'SITE / PRECINCT'),(M+260,'REDRESS'),(M+327,'HOMES'),(M+395,'RAIL KM'),(M+454,'STABLE')]:text(x,top+10,label,7,'Bold',GREEN)
    for i,s in enumerate(sorted(S,key=lambda s:s['rank'])[part*15:part*15+15]):
        y=top+30+i*31
        if i%2==0:rect(M,y,PW,31,'#ecefe5')
        name=s['name'];size=8 if len(name)<29 else 7
        text(M+8,y+7,f"{s['rank']:02}  {name}",size,'Bold');text(M+8,y+19,s['site_id']+' / '+s['subregion'],6.5,'Sans',MUTED)
        for x,val in [(M+275,str(s['rank_redress'])),(M+327,f"{s['units_total']:,}"),(M+401,f"{C['sites'][s['site_id']]['nearest_station']['km']:.2f}"),(M+462,f"{round(s['in_pct_top10']*100)}%")]:text(x,y+11,val,8)
    CAPTURE=True
    para(M,715,'A low stability value means the site rarely enters the efficiency top ten under the tested input perturbations. It does not mean a low probability of housing delivery.',PW,9)
    foot('Sources: rankings and input-sensitivity outputs; site_context.json. All home counts are modelled, not approved.');end()
# 14
begin('09 / Evidence & method','Better evidence. Better decisions.','A practical reading guide to the data behind the atlas and its remaining gaps.')
entries=[('Mapped / measured','OSM snapshot, 30 August 2026: 131 railway station/halt points and 1,642 facility features. The new context uses haversine distances, unweighted school and health-feature counts within 1 km / 2 km, and named nearby features. OSM may contain incomplete coverage or overlapping representations.'),('Derived / modelled','Fourteen normalised criteria, two weighting scenarios and density-based yields. Job access uses eight employment nodes with assumed job weights. The model ranks only these 30 candidates. A score out of 100 is a relative index, not a feasibility percentage.'),('Estimated / unverified','Flood, environment, contamination, infrastructure, heat, delivery complexity, redress and displacement contain analyst estimates. Area, land value, density, tenure and zoning inputs also need independent validation. Remote-sensing indicators have not been replaced with newly measured imagery here.'),('Sensitivity / limitations','Weight noise: 5,000 draws, each weight varied by up to 30% and renormalised. Input noise: 2,000 draws varying the estimated criteria by 15% of their range. Neither test covers every uncertainty, including errors in assumed parcel extent, legal rights or future transport service.'),('Next evidence to obtain','Join verified cadastral parcels and zoning; review tenure and availability; measure network walking access; obtain flood and environmental layers; assess engineering capacity; and consult affected communities on occupancy, displacement and priorities.')]
y=191
for title,body in entries:
    text(M,y,title,12,'Bold',GREEN);h=para(M,y+22,body,PW,9,leading=13.5);y+=h+44
text(M,701,'SOURCE REGISTER',8,'Bold',GREEN)
para(M,720,'Project files: candidate_sites.csv, site_rankings.csv, criteria_scores.csv, sensitivity.csv, input_sensitivity.csv, summary.json and data/geo/site_context.json. Base geography: OpenStreetMap contributors, ODbL. Original terrain: SRTM measurements retained from the project.',PW,8,leading=11)
pdf.linkURL('https://www.openstreetmap.org/copyright',(M,H-768,W-M,H-754),relative=0,thickness=0);text(M,757,'openstreetmap.org/copyright',7,'Sans',GREEN)
end()
# Sources and navigable indexes: pages 22-24.
begin('Sources & references','Trace the finding to its source.','Project evidence and external reference material are separated below. Reference pages were checked on 16 September 2026.')
rows=[['S01','data/candidate_sites.csv','Candidate set, coordinates, attributes and assumptions.'],['S02','outputs/site_rankings.csv / summary.json','Rankings, yields, regional totals and scenario weights.'],['S03','outputs/sensitivity.csv / input_sensitivity.csv','Weight-noise and estimated-input rank simulations.'],['S04','data/geo/site_context.json / basemap.json','Derived OSM geography and proximity calculations; snapshot 30 Aug 2026.'],['S05','scripts/suitability_model.py / measure_site_context.py','Scoring, density assumptions and original measurement method.']]
table(193,['ID','PROJECT SOURCE','WHAT IT SUPPORTS'],rows,[38,222,PW-260],44,8)
refs=[('R01 / OpenStreetMap copyright and licence','https://www.openstreetmap.org/copyright','Attribution and licence reference for the OSM-derived geography. The report uses the saved snapshot rather than a newly collected OSM dataset.'),('R02 / USGS: SRTM 1 Arc-Second Global','https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1','Authoritative product description: approximately 30 m postings. Original project terrain values were retained; this revision did not collect new terrain measurements.'),('R03 / City of Cape Town: Zoning layer','https://citymaps.capetown.gov.za/agsext/rest/services/Theme_Based/Open_Data_Service_Zonning/MapServer/0','A relevant source for future parcel verification. The official service describes an integrated zoning view for approved and registered parcels. It was not joined to the model.')]
y=475
for title,url,body in refs:
    text(M,y,title,10,'Bold',GREEN);pdf.linkURL(url,(M,H-y-17,W-M,H-y+2),relative=0,thickness=0)
    CURRENT['blocks'].append({'type':'link','text':title,'url':url})
    h=para(M,y+23,body,PW,8.5);y+=h+43
foot('External links are clickable. Municipal zoning is listed as a verification source, not as evidence that any candidate has a particular zoning designation.');end()

begin('Alphabetical index','Find a precinct by name.','Every candidate appears here. Directory entries contain both rankings, modelled homes, rail distance and stability.')
indexrows=[]
for site in sorted(S,key=lambda s:s['name'].casefold()):
    directory=19 if site['rank']<=15 else 20
    profile={'S07':12,'S16':13,'S01':14}.get(site['site_id'])
    pages=[directory,7]+([profile] if profile else [])
    indexrows.append([site['name'],site['site_id'],str(directory),str(profile or '-'),'7'])
CURRENT['blocks'].append({'type':'table','headers':['Precinct','Site ID','Directory page','Profile page','Metro map'],'rows':indexrows})
CAPTURE=False
for j,site in enumerate(sorted(S,key=lambda s:s['name'].casefold())):
    col=j//15;row=j%15;x=M+col*260;y=196+row*33
    directory=19 if site['rank']<=15 else 20;profile={'S07':12,'S16':13,'S01':14}.get(site['site_id'])
    text(x,y,site['name'],8.5,'Bold');text(x,y+15,site['site_id']+' / Directory '+str(directory)+(' / Profile '+str(profile) if profile else '')+' / Map 7',7,'Sans',MUTED)
    pdf.linkRect('',str(directory),(x,H-y-29,x+247,H-y+2),relative=0,thickness=0)
CAPTURE=True
callout(702,'Use the atlas for a geographic search.','The interactive version also supports name / site-ID search, map selection, regional filtering and three-site comparison.',72)
end()

begin('Subject index','Find the question that matters.','Page references link to the relevant discussion. The indexes are also included in the reading editions.')
subjects=[('Access to employment',[5,6,9]),('Analyst estimates / provenance',[6,17,21]),('Capacity / housing yield',[3,9,15,16]),('Community engagement / displacement',[4,17,18]),('Criteria and weighting choices',[5,6,10]),('Data sources and references',[21,22]),('Developable area assumptions',[5,15,17]),('Efficiency ranking',[6,10,19]),('Facility access and counts',[9,12,13,14,17]),('Flood / contamination / servicing',[6,17,18]),('Geographic scope and maps',[5,7,8]),('Input uncertainty',[3,11,21]),('Land ownership / tenure',[4,17,18]),('Monte Carlo sensitivity',[11,21]),('Rail station proximity',[9,12,13,14]),('Recommendations and decision gates',[4,17,18]),('Regional distribution',[16]),('Site directory and profiles',[12,13,14,19,20,23]),('Spatial redress',[4,6,10]),('Verification sequence',[18]),('Zoning and planning rights',[17,22]),('Affordability / rent and household budgets',[25]),('Housing challenges / short-term rentals',[26]),('Rental protection / rent controls',[28]),('Social housing and supply solutions',[27]),('Policy implementation and monitoring',[29]),('Policy sources',[30])]
subjects.sort(key=lambda x:x[0].lower())
CURRENT['blocks'].append({'type':'table','headers':['Subject','PDF pages'],'rows':[[topic,', '.join(map(str,pages))] for topic,pages in subjects]})
CAPTURE=False
for i,(topic,pages) in enumerate(subjects):
    y=193+i*20;text(M,y,topic,9);x=391
    for target in pages:
        label=str(target);text(x,y,label,9,'Bold',GREEN);pdf.linkRect('',label,(x,H-y-15,x+24,H-y+2),relative=0,thickness=0);x+=28
CAPTURE=True
foot('Edition 3 / September 2026. A comparative desktop screening report, an interactive atlas and an evidence register should be read together.');end()

# Housing affordability and policy extension: pages 25-30.
begin('Housing affordability / 25','What can households actually afford?','High rent is a household-budget problem as well as a land-supply problem. Add income, transport and recurring charges to the analysis.')
metric(M,190,'R11,894','Western Cape average rent / Q4 2025',230);metric(315,190,'R9,462','South Africa average / Q4 2025',220)
para(M,259,'PayProp reported these averages for its rental index, published 24 March 2026 [P01]. This is dated provincial context, not a Cape Town neighbourhood rent survey or a current asking-price quote. The provincial figure is 25.7% above the national figure (our calculation).',PW,9,leading=13.2)
# Explicitly illustrative budget chart, independent of PayProp observations.
fig,ax=plt.subplots(figsize=(8.2,3.2));incomes=np.array([10000,20000,30000]);rent=6000/incomes*100;other=2800/incomes*100;y=np.arange(3)
ax.barh(y,rent,color=GREEN,label='Rent: R6,000');ax.barh(y,other,left=rent,color=ORANGE,label='Utilities + travel: R2,800')
for yy,rr,oo in zip(y,rent,other):ax.text(rr+oo+1.5,yy,f'{rr+oo:.1f}%',va='center',fontsize=10)
ax.set_yticks(y,['R10,000 income','R20,000 income','R30,000 income']);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Share of monthly gross household income (%)');ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True);ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.2),ncol=2);fig.tight_layout();savefig(fig,'household-affordability')
text(M,330,'ILLUSTRATIVE BUDGET / NOT SURVEY DATA',8,'Bold',GREEN);image('household-affordability.png',354,h=222)
para(M,589,'Example assumptions: R6,000 rent + R1,000 utilities + R1,800 travel per month. At R20,000 gross income, rent alone takes 30%; the combined amount takes 44%. Tax, food, care costs and debt are still excluded. A 30% rent-to-income line is a comparison benchmark here, not a legal cap or a guarantee of affordability.',PW,9,leading=13.3)
callout(672,'Add an affordability test to each candidate.','Specify target incomes, unit sizes, all-in costs and the subsidy or operating model needed. The existing suitability score does not calculate achievable rents.',72)
foot('P01: PayProp Q4 2025, published 24 March 2026. Illustration: author assumptions; it is not an observed household or a project rental forecast.');end()

begin('Challenges / 26','Why cheaper homes are hard to deliver.','These are mechanisms to investigate locally. The screening model does not estimate their individual contribution to Cape Town rents.')
rows=[['Rents and incomes diverge','A rent can rise faster than a household can absorb, while deposits and recurring charges add pressure.','Track agreed rents by unit type, income band, utilities and deposit burden.'],['Well-located land is difficult to unlock','Tenure, competing uses, approvals and service capacity can delay delivery even when a map score is strong.','Verify parcels, ownership, rights, infrastructure budgets and actual milestones.'],['Building and operating costs must be covered','Construction finance, maintenance, insurance, rates and vacancies affect viable rents.','Test whole-life costs and subsidy needs; retain realistic maintenance reserves.'],['A cheaper address can mean a costly commute','Distance, transfers, fares and unreliable service can absorb apparent rent savings.','Measure door-to-door journeys and household transport spending.'],['Displacement and unequal access','Existing residents and informal tenants may lose access through redevelopment or poorly targeted allocation.','Map occupancy and tenure; plan engagement, relocation safeguards and transparent allocation.'],['Short-term use and vacancies may matter locally','Tourism-linked use can compete with long-term housing in some areas; listings alone do not prove the scale of conversion.','Separate entire-home commercial activity from occasional letting and count actual long-term stock changes.']]
table(193,['CHALLENGE','WHY IT MATTERS','EVIDENCE NEEDED'],rows,[115,192,PW-307],78,8.2)
para(M,705,'Design implication: show a candidate’s land, service, cost and community evidence beside its score. Keep unknowns explicit rather than giving unmeasured constraints a false precision.',PW,9.2)
foot('Analytical framework proposed for this report. See P06 for general housing-policy context; no causal ranking of these pressures is asserted.');end()

begin('Solutions / 27','Match the intervention to the problem.','A combined programme should protect households now while creating and retaining affordable homes over time. Proposed options below require local feasibility and authority checks.')
rows=[['Social and affordable rental','Public land or subsidy with an operating partner; protect affordability through enforceable covenants.','Long-term funding, maintenance and fair allocation.','Occupied homes by income band; rent + service costs.'],['Serviced land and infill','Resolve title, engineering and approvals; support suitable density and conversions near jobs.','Environmental, heritage and safety checks; measure delivery, not only land released.','Time to occupation; net additional homes; service capacity.'],['Small-scale / backyard rental','Technical assistance, safe service connections and suitable finance for compliant small landlords.','Habitability and affordable tenancy terms; avoid displacement during upgrades.','Safe occupied units; repairs; tenant cost changes.'],['Targeted tenant support','Time-limited hardship help, deposit assistance and accessible dispute support.','Fund eligibility and review; avoid excluding informal-income households.','Housing retention; arrears resolution; cost per household.'],['Transparent rental rules','Clear leases and charges, maintenance enforcement and predictable review processes.','Capacity to investigate and enforce; keep access fair for new tenants too.','Dispute time; conditions; entry rents and available stock.']]
table(193,['RESPONSE','DELIVERY ROUTE','TRADE-OFF / SAFEGUARD','MEASURE'],rows,[100,154,146,PW-400],82,8)
callout(650,'Track the public pipeline separately.','The City reported more than 14,000 units in active land release or packaging on 18 August 2026 [P07]. That announced pipeline is separate from this model and is not a completed-home count.',94)
foot('Proposals: author synthesis, informed by P06. City announcement: P07. Do not add municipal pipeline figures to the modelled precinct capacities.');end()

begin('Rent controls / 28','Protection today. Supply tomorrow.','Rent control is a family of policies. A freeze, an annual increase limit and an affordable-housing covenant work differently.')
rows=[['Rent freeze / hard ceiling','Can give covered tenants immediate payment certainty.','May reduce maintenance or rental availability if costs cannot be covered; allocation can exclude newcomers.'],['Rent stabilisation','Can make increases within a tenancy more predictable.','Needs rules for new lets, new construction, allowable costs, enforcement and anti-avoidance.'],['Subsidised affordable rents','A subsidy or public-land agreement can target below-market rents to eligible households.','Requires durable funding, operating oversight and a clear affordability period.']]
table(193,['APPROACH','POTENTIAL BENEFIT','DESIGN RISK'],rows,[119,162,PW-281],67,8.2)
text(M,442,'WHAT CURRENT SOUTH AFRICAN GUIDANCE SAYS',9,'Bold',GREEN)
para(M,463,'The Rental Housing Act 50 of 1999 repealed the old Rent Control Act [P02]. Western Cape guidance points to the lease or agreed terms for increases and to negotiation where these are unspecified [P03]. Do not treat 10% or CPI as an automatic legal ceiling. The provincial Rental Housing Tribunal offers free dispute-resolution services [P04]. These are current-framework notes, not a ruling on a particular lease.',PW,9,leading=13)
text(M,542,'WHAT THE INTERNATIONAL EVIDENCE CAN AND CANNOT TELL US',9,'Bold',GREEN)
para(M,563,'Diamond, McQuade and Qian (2019) found less displacement among covered San Francisco tenants, alongside a 15% reduction in rental supply from affected landlords [P05]. That historical finding illustrates a trade-off; it is not a forecast for Cape Town.',PW,9,leading=13)
callout(632,'If considering stabilisation, test the whole design.','Establish legal authority and a rental baseline; consult tenants and landlords; define coverage, vacancy rules and fair cost review; enforce habitability; monitor new supply, conversions and access for newcomers. Pair protection with affordable supply.',104)
foot('Sources P02-P06. Options are proposals for appraisal, not existing Cape Town rules or a recommendation for a particular percentage cap.');end()

begin('Implementation / 29','Turn proposals into accountable work.','An indicative sequence for discussion, not an adopted municipal programme or a funded project schedule.')
rows=[['First 0-3 months','Establish the baseline','Housing / GIS / statistics teams','Agreed rents, income bands, unit type, tenure, service costs, commuting and stock definitions.'],['Months 3-12','Verify and package sites','Land / planning / engineering teams','Parcel, rights and services evidence; transparent site status and milestone register.'],['Months 3-12','Test targeted protection','Housing / legal / community teams','Costed tenant-support or stabilisation design; authority review, consultation and delivery capacity.'],['Months 12-36','Deliver and evaluate','Funders / delivery partners / residents','Track occupied affordable homes, operating costs, repairs and displacement; compare with the baseline.']]
table(193,['INDICATIVE HORIZON','ACTION','PROPOSED FUNCTION','OUTPUT TO RETAIN'],rows,[90,101,124,PW-315],73,8.2)
text(M,541,'A MINIMUM PUBLIC DASHBOARD',10,'Bold',GREEN)
para(M,565,'Publish agreed-rent medians by unit type and area; rent + utilities + travel as an income share; net long-term rental stock; verified and occupied affordable units; approvals-to-occupation time; tenancy disputes and resolution time; maintenance performance; and displacement or relocation outcomes.',PW,10,leading=15)
callout(650,'Judge outcomes, not announcements.','A land release is not an occupied home. A protected existing tenant does not prove access improved for a new tenant. Report both household outcomes and supply changes, with definitions and dates.',86)
foot('Governance and monitoring proposals by the author. Protect personal tenant information and publish aggregated statistics; record definitions and missing coverage.');end()

begin('Policy sources / 30','The evidence behind the discussion.','Policy and affordability references checked on 16 September 2026. P01 is a dated market observation; proposed actions remain author analysis.')
policy_refs=[
('P01 / PayProp: Q4 2025 Rental Index summary','https://www.payprop.com/blog/rental-growth-cooled-in-q4-says-new-payprop-rental-index','Published 24 March 2026. Provincial and national average rent context; not a Cape Town local rent survey.'),
('P02 / South African Government: Rental Housing Act','https://www.gov.za/documents/rental-housing-act','Act 50 of 1999; repeal of the former Rent Control Act and the rental dispute framework.'),
('P03 / Western Cape: Tenant frequently asked questions','https://www.westerncape.gov.za/infrastructure/frequently-asked-questions-tenants','Official guidance on lease terms, negotiated increases and referral for individual disputes.'),
('P04 / Western Cape: Rental Housing Tribunal','https://www.westerncape.gov.za/service/rental-housing-tribunal-0','Free tenant / landlord dispute services and the current complaint route.'),
('P05 / Diamond, McQuade & Qian: Rent control study','https://www.aeaweb.org/articles?id=10.1257/aer.20181289','American Economic Review 109(9), 2019, pp. 3365-3394. San Francisco evidence, not a Cape Town forecast.'),
('P06 / OECD: An Agenda for Housing Policy Reform','https://www.oecd.org/content/dam/oecd/en/publications/reports/2024/10/an-agenda-for-housing-policy-reform_450b3a9a/ddb57031-en.pdf','2024 policy framework; balancing access, tenant protection, maintenance and rental supply incentives.'),
('P07 / City: Affordable Housing Investment Connect','https://web1.capetown.gov.za/web1/newsandnotices/Home/Release/Cape-Town-s-affordable-housing-investment-summit-seeks-partnerships-for-14-000-u?category=Media+releases','18 August 2026 municipal announcement. Active land-release / packaging pipeline, separately defined from occupied units.')]
y=192
for title,url,body in policy_refs:
    text(M,y,title,10,'Bold',GREEN);pdf.linkURL(url,(M,H-y-17,W-M,H-y+2),relative=0,thickness=0)
    CURRENT['blocks'].append({'type':'link','text':title,'url':url})
    para(M,y+22,body,PW,8.5,leading=12);y+=76
foot('External references support the stated observations. The affordable-rent examples, proposed programme and monitoring dashboard are analytical suggestions.');end()

pdf.save()
(OUT/'report-content.json').write_text(json.dumps(RECORD,ensure_ascii=False,indent=2),encoding='utf8')
assert page==30, page
print('Created',OUT/'housing-atlas-ebook.pdf','pages:',page)
