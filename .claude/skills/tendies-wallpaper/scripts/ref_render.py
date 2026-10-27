"""Static preview of LayeredAnimation reference tendies (read-only; images decoded in memory).

usage: python -I ref_render.py OUT.png WIDTH SOURCE[::member] [SOURCE[::member] ...]
SOURCE is a .tendies, or an outer .zip with ::<inner .tendies.zip member name>.
Each wallpaper becomes one row: Locked | Unlock | Sleep, Background + Floating + Foreground stacked
(no animations, emitters drawn as a dot, blend modes approximated as normal; lighten/overlay at half alpha).
"""
import io
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image, ImageDraw, ImageFont

OUT, TW = sys.argv[1], int(sys.argv[2])
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 14)


def local(t):
    return t.rsplit("}", 1)[-1]


def nums(s, n):
    v = [float(x) for x in (s or "").split()]
    return v + [0.0] * (n - len(v))


def open_src(spec):
    if "::" in spec:
        outer, member = spec.split("::", 1)
        z = zipfile.ZipFile(outer)
        name = next(n for n in z.namelist() if n.endswith(member))
        return zipfile.ZipFile(io.BytesIO(z.read(name))), member
    return zipfile.ZipFile(spec), spec.replace("\\", "/").rsplit("/", 1)[-1]


class Ctx:
    def __init__(self, z, bundle):
        self.z, self.bundle, self.cache = z, bundle, {}

    def img(self, src):
        if src not in self.cache:
            try:
                im = Image.open(io.BytesIO(self.z.read(self.bundle + "/" + src)))
                im.draft("RGBA", (1024, 1024))
                im = im.convert("RGBA")
                if max(im.size) > 1024:
                    im.thumbnail((1024, 1024))
                self.cache[src] = im
            except Exception:
                self.cache[src] = None
        return self.cache[src]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def render_bundle(ctx, root_el, state, canvas, k, H):
    ids = {}
    for e in root_el.iter():
        if e.get("id"):
            ids[e.get("id")] = e
    over = {}
    for st in root_el.iter():
        if local(st.tag) == "LKState" and st.get("name") == state:
            for sv in st.iter():
                if local(sv.tag) == "LKStateSetValue":
                    v = sv.find("{*}value")
                    if v is not None and v.get("value") is not None:
                        over.setdefault(sv.get("targetId"), {})[sv.get("keyPath")] = v.get("value")

    def draw(e, M, alpha):
        if e.get("hidden") in ("1", "true"):
            return
        o = over.get(e.get("id"), {})
        bw, bh = nums(e.get("bounds"), 4)[2:4]
        bw = float(o.get("bounds.size.width", bw))
        bh = float(o.get("bounds.size.height", bh))
        px, py = nums(e.get("position"), 2)
        px = float(o.get("position.x", px))
        py = float(o.get("position.y", py))
        ax, ay = nums(e.get("anchorPoint") or "0.5 0.5", 2)
        rz = float(o.get("transform.rotation.z", e.get("transform.rotation.z") or 0))
        sc = float(o.get("transform.scale.xy", 1))
        op = float(o.get("opacity", e.get("opacity") or 1)) * alpha
        if op <= 0.003:
            return
        c, s = math.cos(rz) * sc, math.sin(rz) * sc
        L = [[c, -s, px - (c * ax * bw - s * ay * bh)], [s, c, py - (s * ax * bw + c * ay * bh)], [0, 0, 1]]
        M2 = matmul(M, L)       # local (y-up) -> canvas (y-up)
        bg = e.get("backgroundColor")
        if bg and local(e.tag) == "CALayer" and e is not root_el[0]:
            col = tuple(int(255 * x) for x in nums(bg, 3)) + (int(255 * op),)
            pts = [(M2[0][0] * x + M2[0][1] * y + M2[0][2], H - (M2[1][0] * x + M2[1][1] * y + M2[1][2]))
                   for x, y in ((0, 0), (bw, 0), (bw, bh), (0, bh))]
            ImageDraw.Draw(canvas, "RGBA").polygon([(x * k, y * k) for x, y in pts], fill=col)
        cg = e.find("{*}contents/{*}CGImage")
        if cg is not None and cg.get("src") and bw > 0 and bh > 0:
            im = ctx.img(cg.get("src"))
            if im is not None:
                comp = e.find("{*}compositingFilter")
                mode = comp.get("filter") if comp is not None else "normalBlendMode"
                a = op * (0.5 if mode in ("lightenBlendMode", "overlayBlendMode", "colorDodgeBlendMode") else
                          0.35 if mode == "multiplyBlendMode" else 1.0)
                iw, ih = im.size
                # image px (y-down) -> local: x*bw/iw, (ih - y)*bh/ih ; local -> canvas px: M2 then flip, *k
                A = [[bw / iw, 0, 0], [0, -bh / ih, bh], [0, 0, 1]]
                T = matmul(M2, A)
                F = [[k, 0, 0], [0, -k, H * k], [0, 0, 1]]
                T = matmul(F, T)
                det = T[0][0] * T[1][1] - T[0][1] * T[1][0]
                if abs(det) > 1e-9:
                    inv = [[T[1][1] / det, -T[0][1] / det], [-T[1][0] / det, T[0][0] / det]]
                    tx = -(inv[0][0] * T[0][2] + inv[0][1] * T[1][2])
                    ty = -(inv[1][0] * T[0][2] + inv[1][1] * T[1][2])
                    layer = im.transform(canvas.size, Image.AFFINE, (inv[0][0], inv[0][1], tx, inv[1][0], inv[1][1], ty),
                                         resample=Image.BILINEAR)
                    if a < 1:
                        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
                    canvas.alpha_composite(layer)
        if local(e.tag) == "CAEmitterLayer":
            ex, ey = nums(e.get("emitterPosition"), 2)
            X = (M2[0][0] * ex + M2[0][1] * ey + M2[0][2]) * k
            Y = (H - (M2[1][0] * ex + M2[1][1] * ey + M2[1][2])) * k
            ImageDraw.Draw(canvas).ellipse((X - 4, Y - 4, X + 4, Y + 4), outline=(255, 80, 80, 255), width=2)
        subs = e.find("{*}sublayers")
        if subs is not None:
            kids = [x for x in subs if local(x.tag).endswith("Layer")]
            kids.sort(key=lambda x: float(over.get(x.get("id"), {}).get("zPosition", x.get("zPosition") or 0)))
            for kch in kids:
                draw(kch, M2, op)

    top = root_el[0]
    draw(top, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 1.0)


rows = []
for spec in sys.argv[3:]:
    z, label = open_src(spec)
    names = z.namelist()
    wp = next(n for n in names if n.endswith("Wallpaper.plist"))
    base = wp.rsplit("/", 1)[0]
    import plistlib
    pl = plistlib.loads(z.read(wp))
    d = list(pl["assets"].values())[0]["default"] if "assets" in pl else {}
    order = [d.get("backgroundAnimationFileName"), d.get("floatingAnimationFileNameKey") or d.get("floatingAnimationFileName"),
             d.get("foregroundAnimationFileName")]
    order = [o for o in order if o]
    bundles = []
    for o in order:
        b = base + "/" + o
        idx = z.read(b + "/index.xml").decode("utf-8", "replace") if b + "/index.xml" in names else ""
        m = re.search(r"<rootDocument[^>]*>([^<]+)<", idx)
        caml = b + "/" + (m.group(1).strip() if m else "main.caml")
        text = z.read(caml).decode("utf-8", "replace")
        if re.search(r"<!(DOCTYPE|ENTITY)", text[:4000]):
            continue
        bundles.append((Ctx(z, b), ET.fromstring(text)))
    W0, H0 = nums(bundles[0][1][0].get("bounds"), 4)[2:4]
    states = []
    for st in bundles[0][1].iter():
        if local(st.tag) == "LKState":
            states.append(st.get("name"))
    tiles = []
    for state in states[:6]:
        k = TW / W0
        canvas = Image.new("RGBA", (TW, int(H0 * k)), (40, 40, 48, 255))
        for i, (ctx, el) in enumerate(bundles):
            bw, bh = nums(el[0].get("bounds"), 4)[2:4]
            if (bw, bh) != (W0, H0) and bw > 0:      # e.g. a 390x844 foreground over a larger canvas
                continue
            render_bundle(ctx, el, state, canvas, k, H0)
        d = ImageDraw.Draw(canvas)
        d.rectangle((0, 0, TW, 18), fill=(0, 0, 0, 160))
        d.text((4, 1), f"{label[:28]} | {state}", fill=(255, 255, 255, 255), font=FONT)
        tiles.append(canvas)
    rows.append(tiles)

cw = max(t.width for r in rows for t in r)
ch = max(t.height for r in rows for t in r)
ncol = max(len(r) for r in rows)
sheet = Image.new("RGB", (ncol * (cw + 6) + 6, len(rows) * (ch + 6) + 6), (16, 16, 20))
for j, r in enumerate(rows):
    for i, t in enumerate(r):
        sheet.paste(t, (6 + i * (cw + 6), 6 + j * (ch + 6)), t)
sheet.save(OUT)
print(OUT, sheet.size)
