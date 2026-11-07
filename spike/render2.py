#!/usr/bin/env python3
"""Render v2: Pyramide korrekt verschachtelt (Ausschnitt = groebste Kachel),
Polylinien im echten Metermassstab mit Kachelrand."""
import pickle, math, struct
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
def polylines(b,N=10):
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

PS=380; GAP=54; MARG=28
W = MARG*2 + PS*3 + GAP*2
H = MARG + 40 + (PS+78)*2
P=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
   f'viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,sans-serif">',
   f'<rect width="{W}" height="{H}" fill="#fbfaf8"/>',
   f'<text x="{MARG}" y="26" font-size="19" font-weight="600" fill="#141414">'
   f'GermanyWest_Basic.psf — Kachelpyramide (bewiesen) und Polylinien (Form gesichert, Lage Hypothese)</text>']

ytop=MARG+40
for name,(tlon,tlat) in TARGETS.items():
    g=sorted([k for k in keep if k[0]==name], key=lambda k:k[1])
    coarse=g[0]; fine=g[-1]
    P.append(f'<text x="{MARG}" y="{ytop-8}" font-size="15" font-weight="600" '
             f'fill="#141414">{name} — {tlon:.4f}° O / {tlat:.4f}° N</text>')

    # Panel 1: volle Pyramide, Ausschnitt = groebste Kachel
    for pi,(ref,lbl) in enumerate(((coarse,'volle Pyramide (Ausschnitt = Level %d)'%coarse[1]),
                                   (fine,'Zoom auf tiefste Kachel (Level %d)'%fine[1]))):
        X=MARG+pi*(PS+GAP); Y=ytop
        _,L,off,b,x0,y0,x1,y1 = ref
        w0,e0=lon_of(x0),lon_of(x1); s0,n0=lat_of(y0),lat_of(y1)
        P.append(f'<text x="{X}" y="{Y-6}" font-size="11" fill="#8a8a8a">{lbl}</text>')
        P.append(f'<rect x="{X}" y="{Y}" width="{PS}" height="{PS}" fill="#fff" stroke="#e2e0dc"/>')
        P.append(f'<clipPath id="c{name}{pi}"><rect x="{X}" y="{Y}" '
                 f'width="{PS}" height="{PS}"/></clipPath>')
        P.append(f'<g clip-path="url(#c{name}{pi})">')
        for _,LL,o2,b2,ax0,ay0,ax1,ay1 in g:
            aw,ae=lon_of(ax0),lon_of(ax1); as_,an=lat_of(ay0),lat_of(ay1)
            rx=X+(aw-w0)/(e0-w0)*PS; ry=Y+(n0-an)/(n0-s0)*PS
            rw=(ae-aw)/(e0-w0)*PS; rh=(an-as_)/(n0-s0)*PS
            if rw<2 or rh<2: continue
            P.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
                     f'fill="none" stroke="#c2410c" stroke-width="1.1" '
                     f'opacity="{0.25+0.1*(LL-6):.2f}"/>')
            if rw>34:
                P.append(f'<text x="{rx+3:.1f}" y="{ry+12:.1f}" font-size="9" '
                         f'fill="#c2410c">L{LL}</text>')
        px=X+(tlon-w0)/(e0-w0)*PS; py=Y+(n0-tlat)/(n0-s0)*PS
        P.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="#0369a1"/>')
        P.append('</g>')
        P.append(f'<text x="{px+9:.1f}" y="{py+4:.1f}" font-size="11" fill="#0369a1">'
                 f'{name}</text>')

    # Panel 3: Polylinien der tiefsten Kachel, echter Metermassstab
    X=MARG+2*(PS+GAP); Y=ytop
    _,L,off,b,x0,y0,x1,y1 = fine
    tw=x1-x0
    pls=polylines(b,10)
    mpu=tw/1024.0
    P.append(f'<text x="{X}" y="{Y-6}" font-size="11" fill="#8a8a8a">'
             f'Polylinien der Level-{L}-Kachel — {len(pls)} Zuege, '
             f'{mpu:.1f} m/Einheit, Kachel {tw/1000:.1f} km</text>')
    P.append(f'<rect x="{X}" y="{Y}" width="{PS}" height="{PS}" fill="#fff" stroke="#e2e0dc"/>')
    for pts in pls:
        dd=' '.join(f'{X+ux/1024*PS:.1f},{Y+(1-uy/1024)*PS:.1f}' for ux,uy in pts)
        P.append(f'<polyline points="{dd}" fill="none" stroke="#166534" '
                 f'stroke-width="1.1" opacity="0.8"/>')
    P.append(f'<text x="{X+4}" y="{Y+PS-8}" font-size="10" fill="#999">'
             f'Kachelrand = Panelrand</text>')
    ytop += PS+78

P.append(f'<text x="{MARG}" y="{H-14}" font-size="10.5" fill="#8a8a8a">'
         f'Orange: Kachelraster, exakt (Mercator R=6371000 m, Raster 360/2^L, 99,7 % rastertreu). '
         f'Gruen: Delta-Dekodierung gesichert (Kohaerenz 0,62-0,91 gegen 0,10-0,24 bei Zufall), '
         f'Startpunkt unbewiesen.</text>')
P.append('</svg>')
open('../spike/render2.svg','w').write('\n'.join(P))
print("render2.svg geschrieben")
for name in TARGETS:
    g=sorted([k for k in keep if k[0]==name], key=lambda k:k[1])
    print(f"  {name}: Level {[k[1] for k in g]}, tiefste Kachel "
          f"{(g[-1][6]-g[-1][4])/1000:.1f} km, {len(polylines(g[-1][3],10))} Polylinien")
