"""Python port of the dataviz skill's validate_palette.js (no node on this box).
Same thresholds and Machado-Oliveira-Fernandes (2009) severity-1.0 matrices."""
import itertools, math, sys

BAND = {"light": (0.43, 0.77), "dark": (0.48, 0.67)}
CHROMA_FLOOR, CVD_TARGET, CVD_FLOOR, NORMAL_FLOOR, CONTRAST_MIN = 0.10, 8.0, 6.0, 15.0, 3.0
MACHADO = {
 "protan": ((0.152286,1.052583,-0.204868),(0.114503,0.786281,0.099216),(-0.003882,-0.048116,1.051998)),
 "deutan": ((0.367322,0.860646,-0.227968),(0.280085,0.672501,0.047413),(-0.011820,0.042940,0.968881)),
 "tritan": ((1.255528,-0.076749,-0.178779),(-0.078411,0.930809,0.147602),(0.004733,0.691367,0.303900)),
}
s2lin = lambda c: c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
lin = lambda h: [s2lin(int(h.lstrip('#')[i:i+2],16)/255) for i in (0,2,4)]
def relLum(h):
    r,g,b = lin(h); return 0.2126*r+0.7152*g+0.0722*b
def contrast(a,b):
    hi,lo = sorted((relLum(a),relLum(b)),reverse=True); return (hi+0.05)/(lo+0.05)
def oklab_lin(rgb):
    r,g,b = rgb
    l = (0.4122214708*r+0.5363325363*g+0.0514459929*b)**(1/3)
    m = (0.2119034982*r+0.6806995451*g+0.1073969566*b)**(1/3)
    s = (0.0883024619*r+0.2817188376*g+0.6299787005*b)**(1/3)
    return (0.2104542553*l+0.7936177850*m-0.0040720468*s,
            1.9779984951*l-2.4285922050*m+0.4505937099*s,
            0.0259040371*l+0.7827717662*m-0.8086757660*s)
def oklch(h):
    L,a,b = oklab_lin(lin(h)); return L, math.hypot(a,b)
def sim(h,kind):
    r,g,b = lin(h); M = MACHADO[kind]
    return [min(1,max(0,M[i][0]*r+M[i][1]*g+M[i][2]*b)) for i in range(3)]
def dE(h1,h2,kind=None):
    a = oklab_lin(sim(h1,kind) if kind else lin(h1))
    b = oklab_lin(sim(h2,kind) if kind else lin(h2))
    return 100*math.dist(a,b)

def validate(pal, mode="light", surface=None, pairs="adjacent"):
    surface = surface or {"light":"#fcfcfb","dark":"#1a1a19"}[mode]
    lo,hi = BAND[mode]; fails = 0
    print(f"--- {mode}  surface {surface}  pairs={pairs} ---")
    for h in pal:
        L,C = oklch(h); ct = contrast(h,surface)
        f = []
        if not (lo <= L <= hi): f.append(f"L={L:.3f} outside {lo}-{hi}")
        if C < CHROMA_FLOOR: f.append(f"C={C:.3f} < {CHROMA_FLOOR}")
        w = "" if ct >= CONTRAST_MIN else f"  WARN contrast {ct:.2f}:1"
        fails += len(f)
        print(f"  {h}  L={L:.3f} C={C:.3f} contrast={ct:.2f}:1 " +
              ("FAIL " + "; ".join(f) if f else "ok") + w)
    plist = list(zip(pal, pal[1:])) if pairs == "adjacent" else list(itertools.combinations(pal,2))
    for a,b in plist:
        nrm = dE(a,b); p,d,t = dE(a,b,"protan"), dE(a,b,"deutan"), dE(a,b,"tritan")
        cvd = min(p,d)
        st = "ok" if cvd >= CVD_TARGET else ("WARN floor band" if cvd >= CVD_FLOOR else "FAIL")
        if cvd < CVD_FLOOR: fails += 1
        if nrm < NORMAL_FLOOR: st += "  FAIL normal-vision floor"; fails += 1
        print(f"  {a} vs {b}: normal={nrm:.1f} protan={p:.1f} deutan={d:.1f} tritan={t:.1f}  {st}")
    print("RESULT:", "PASS" if fails == 0 else f"{fails} FAIL(s)")
    return fails

if __name__ == "__main__":
    pal = [x.strip() for x in sys.argv[1].split(",") if x.strip()]
    mode = sys.argv[2] if len(sys.argv) > 2 else "light"
    surf = sys.argv[3] if len(sys.argv) > 3 else None
    prs = sys.argv[4] if len(sys.argv) > 4 else "all"
    sys.exit(1 if validate(pal, mode, surf, prs) else 0)
