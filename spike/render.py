#!/usr/bin/env python3
"""SVG-Render: bewiesene Kachelpyramide + Polylinien unter Startpunkt-Hypothese."""
import pickle, math, struct, collections
def s8(v): return v-256 if v>127 else v
R=6371000.0
def lon_of(x): return math.degrees(x/R)
def lat_of(y): return math.degrees(2*math.atan(math.exp(y/R))-math.pi/2)

keep=pickle.load(open('../spike/gw_tiles.pkl','rb'))
TARGETS={'Testort':(7.7,50.1),'Niederortbeta':(8.3,50.3)}

def bits_msb(b,bp,n):
    v=0
    for i in range(n):
        by=(bp+i)//8; bi=7-((bp+i)%8)
        if by>=len(b): return None
        v=(v<<1)|((b[by]>>bi)&1)
    return v

def runs(b,thr=40,minlen=24):
    out=[]; cur=None
    for i in range(16,len(b)):
        if abs(s8(b[i]))<=thr:
            if cur is None: cur=i
        else:
            if cur is not None and i-cur>=minlen: out.append((cur,i))
            cur=None
    if cur is not None and len(b)-cur>=minlen: out.append((cur,len(b)))
    return out

def polylines(b, N):
    G=2**N; out=[]
    for s,e in runs(b):
        raw=b[s:e]
        pr=[(s8(raw[i]),s8(raw[i+1])) for i in range(0,len(raw)-1,2)]
        if len(pr)<8: continue
        bp=s*8-8
        if bp<0: continue
        x=bits_msb(b,bp,N); y=bits_msb(b,bp+N,N)
        if x is None or y is None or not(0<=x<G and 0<=y<G): continue
        pts=[(x,y)]
        for dx,dy in pr:
            x+=dx; y+=dy
            if not(0<=x<G and 0<=y<G): break
            pts.append((x,y))
        if len(pts)>=6: out.append(pts)
    return out

W,H=1180,1500
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
       f'viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#fbfaf8"/>',
       f'<text x="24" y="38" font-size="21" font-weight="600" fill="#1a1a1a">'
       f'MIB2-Kartendaten: Kachelpyramide und rekonstruierte Polylinien</text>',
       f'<text x="24" y="60" font-size="13" fill="#666">GermanyWest_Basic.psf — '
       f'Kacheln exakt georeferenziert (bewiesen), Polylinien-Platzierung Hypothese</text>']

y0=86
for ti,(name,(tlon,tlat)) in enumerate(TARGETS.items()):
    g=[k for k in keep if k[0]==name]
    g.sort(key=lambda k:k[1])
    parts.append(f'<text x="24" y="{y0+16}" font-size="16" font-weight="600" '
                 f'fill="#1a1a1a">{name} — {tlon:.4f}° O / {tlat:.4f}° N</text>')
    # --- links: Kachelpyramide in lon/lat
    PX,PY,PS=24,y0+30,300
    fine=[k for k in g if k[1]>=10]
    ref=max(g,key=lambda k:k[1])
    _,L,off,b,x0,yy0,x1,yy1 = ref
    w0,e0=lon_of(x0),lon_of(x1); s0,n0=lat_of(yy0),lat_of(yy1)
    parts.append(f'<rect x="{PX}" y="{PY}" width="{PS}" height="{PS}" '
                 f'fill="#fff" stroke="#ddd"/>')
    parts.append(f'<text x="{PX}" y="{PY-6}" font-size="11" fill="#888">'
                 f'Kachelpyramide, Ausschnitt der tiefsten Kachel (Level {L})</text>')
    for _,LL,o2,b2,ax0,ay0,ax1,ay1 in g:
        aw,ae=lon_of(ax0),lon_of(ax1); as_,an=lat_of(ay0),lat_of(ay1)
        rx=PX+(aw-w0)/(e0-w0)*PS; ry=PY+(n0-an)/(n0-s0)*PS
        rw=(ae-aw)/(e0-w0)*PS; rh=(an-as_)/(n0-s0)*PS
        op=0.10+0.09*(LL-6)
        parts.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" '
                     f'height="{rh:.1f}" fill="none" stroke="#c2410c" '
                     f'stroke-width="1.2" opacity="{min(op,0.95):.2f}"/>')
        if LL>=9:
            parts.append(f'<text x="{max(PX+2,rx+3):.1f}" y="{max(PY+12,ry+13):.1f}" '
                         f'font-size="9" fill="#c2410c">L{LL}</text>')
    px=PX+(tlon-w0)/(e0-w0)*PS; py=PY+(n0-tlat)/(n0-s0)*PS
    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#0369a1"/>')
    parts.append(f'<text x="{px+8:.1f}" y="{py+4:.1f}" font-size="11" '
                 f'fill="#0369a1">{name}</text>')

    # --- rechts: Polylinien der tiefsten zwei Kacheln, zwei Rastergroessen
    for vi,N in enumerate((10,12)):
        QX=PX+PS+40+vi*(PS+40); QY=PY
        parts.append(f'<rect x="{QX}" y="{QY}" width="{PS}" height="{PS}" '
                     f'fill="#fff" stroke="#ddd"/>')
        allp=[]
        for _,LL,o2,b2,ax0,ay0,ax1,ay1 in g[-2:]:
            allp += polylines(b2,N)
        G=2**N
        mpu = (x1-x0)/G
        parts.append(f'<text x="{QX}" y="{QY-6}" font-size="11" fill="#888">'
                     f'Polylinien, Raster 2^{N}={G} ({mpu:.1f} m/Einheit) — '
                     f'{len(allp)} Zuege</text>')
        for pts in allp:
            dd=' '.join(f'{QX+px_/G*PS:.1f},{QY+(1-py_/G)*PS:.1f}' for px_,py_ in pts)
            parts.append(f'<polyline points="{dd}" fill="none" stroke="#166534" '
                         f'stroke-width="1" opacity="0.75"/>')
    y0 += PS+90

parts.append(f'<text x="24" y="{H-20}" font-size="11" fill="#888">'
             f'Kachelrechtecke: bewiesen (Mercator R=6371000, Raster 360/2^L, '
             f'99,7 % rastertreu). Polylinien: Deltas gesichert, Startpunkt Hypothese.</text>')
parts.append('</svg>')
open('../spike/render.svg','w').write('\n'.join(parts))
print("geschrieben: render.svg")
for name in TARGETS:
    g=[k for k in keep if k[0]==name]
    for N in (10,12):
        tot=sum(len(polylines(k[3],N)) for k in g[-2:])
        print(f"  {name} N={N}: {tot} Polylinien aus den 2 tiefsten Kacheln")
