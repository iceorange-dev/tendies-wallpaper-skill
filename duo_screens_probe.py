# -*- coding: utf-8 -*-
"""
Probe for Apple's per-screen ParameterizedCA schema on the iPhone Duo.

iOS 27.2's own Duo wallpaper (Clownfish-V68) does not use wallpaperPropertyGroups. Its root <style> holds
<wallpapers>: one dictionary per screen ("Cover Screen", "Inner Display"), each naming its own BACKGROUND /
FLOATING layer trees, with state values split into portrait_* and landscape_*. WallpaperKit reads both schemas.

This probe builds the same shape with our packaging (iOS 27 depth naming) and makes each question answerable
from device screenshots:
  1. Is the schema accepted for an imported poster at all?
  2. Which tree shows on which screen (INNER blue / COVER orange), and which part of the root each screen
     shows: the grid is labelled in root points (y up, root centre 445,445)
  3. Do portrait_* / landscape_* values follow the orientation (PORTRAIT / LANDSCAPE tags)?
  4. Lock / Home / Sleep tags
  5. Gyro through background/floatingParallaxGroups (grid +-10 pt, floating bands +-25 pt)
  6. Depth: FLOATING bands at three heights, which should cover the clock where they cross it on Lock

v2, after the first device run (2026-11-08): in portrait both screens show 1 root unit per device pixel with the
root centre at the screen centre; the inner display in landscape scales that by 2853/2007. So the grid now spans
3200 units, the predicted windows are outlined, and the bands sit on each posture's measured clock.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from tendies_kit import *  # noqa: F401,F403
import tendies_kit as kit

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BUILD = os.path.join(OUT, "build", "duo_screens_probe")
OUT_NAME = "Duo-Screens-Probe"

GRID = 3200                     # units, centred on the root centre: wider than any screen shows
GRID_PPT = 0.5
# predicted visible windows (units), drawn on the grid to check against the screen edges
WINDOWS = (("inner portrait", 2007, 2853, (90, 220, 255)), ("inner landscape", 2007, 1412, (255, 120, 220)),
           ("cover", 1398, 2034, (120, 255, 140)))
# each posture's clock centre measured from the v1 screenshots, in root units
BANDS = ((910, "landscape clock"), (1120, "cover clock"), (1480, "inner clock"))
# Apple's numbers from Clownfish-V68, copied as they are
SCREENS = (
    dict(screenName="Cover Screen", key="TWO", tag="COVER", base=(92, 46, 14), idealWidth=466, idealHeight=678,
         pixelWidth=1398, pixelHeight=2034, pixelParallaxBleed=64, pixelSquareWithParallax=3553,
         pixelSquareWithoutParallax=3489),
    dict(screenName="Inner Display", key="ONE", tag="INNER", base=(16, 38, 92), idealWidth=669, idealHeight=951,
         pixelWidth=2007, pixelHeight=2853, pixelParallaxBleed=119, pixelSquareWithParallax=3608,
         pixelSquareWithoutParallax=3489),
)


def font(px):
    return ImageFont.truetype(CLOCK_FONT, px)


def grid_image():
    n = int(GRID * GRID_PPT)
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(int(28 * GRID_PPT))
    lo = C - GRID / 2
    for v in range(int(lo // 100 * 100), int(lo + GRID) + 1, 100):
        p = (v - lo) * GRID_PPT
        major = v % 500 == 0
        col = (255, 255, 255, 170 if major else 70)
        w = 3 if major else 1
        d.line([(p, 0), (p, n)], fill=col, width=w)
        d.line([(0, n - p), (n, n - p)], fill=col, width=w)
    for x in range(int(lo // 200 * 200), int(lo + GRID) + 1, 200):
        for y in range(int(lo // 200 * 200), int(lo + GRID) + 1, 200):
            px, py = (x - lo) * GRID_PPT, n - (y - lo) * GRID_PPT
            d.text((px + 4, py - 4), f"{x},{y}", font=f, fill=(255, 255, 255, 220), anchor="ld")
    # the root square's edge, so the 890 pt root is easy to find
    a, b = (0 - lo) * GRID_PPT, (S - lo) * GRID_PPT
    d.rectangle([a, n - b, b, n - a], outline=(255, 230, 0, 255), width=4)
    for i, (label, w, h, rgb) in enumerate(WINDOWS):
        x0, x1 = (C - w / 2 - lo) * GRID_PPT, (C + w / 2 - lo) * GRID_PPT
        y0, y1 = n - (C + h / 2 - lo) * GRID_PPT, n - (C - h / 2 - lo) * GRID_PPT
        d.rectangle([x0, y0, x1, y1], outline=rgb + (255,), width=3)
        d.text((x0 + 8, y0 + 8 + i * 22), label, font=font(int(40 * GRID_PPT)), fill=rgb + (255,), anchor="lt")
    return im


def text_layer(name, text, size, x, y, rgb=(255, 255, 255), **kw):
    key = "txt_" + "".join(ch if ch.isalnum() else "_" for ch in text) + f"_{size}_{rgb[0]}.png"
    if key not in kit.ASSETS:
        f = font(int(size * PPT))
        l, t, r, bt = f.getbbox(text)
        im = Image.new("RGBA", (r - l + 8, bt - t + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=f, fill=rgb + (255,))
        asset(key, im)
    w, h = kit.ASSETS[key].size
    return Layer(name, w / PPT, h / PPT, x, y, img=key, **kw)


def band(name, text, y, rgb):
    key = f"band_{rgb[0]}.png"
    if key not in kit.ASSETS:
        asset(key, Image.new("RGBA", (4, 4), rgb + (170,)))
    g = group(name)
    g.add(Layer(f"{name} Fill", 2600, 60, C, y, img=key), text_layer(f"{name} Text", text, 40, C, y))
    return g


def screen_trees(sc):
    k, tag = sc["key"], sc["tag"]
    bg = group(f"BACKGROUND {k}")
    grid = Layer(f"Grid {k}", GRID, GRID, C, C, img="grid.png")
    grid_par = group(f"Grid Parallax {k}", kind="CATransformLayer").add(grid)
    grid_par.parallax = 30
    bg.add(Layer(f"Base {k}", GRID, GRID, C, C, color=tuple(c / 255 for c in sc["base"])), grid_par,
           text_layer(f"Title {k}", tag, 90, C, C - 5))
    for st, vals in (("LOCK", (1, 0, 0)), ("HOME", (0, 1, 0)), ("SLEEP", (0, 0, 1))):
        bg.add(text_layer(f"State {st} {k}", st, 40, C, C - 75, opacity=vals[0]).state("opacity", *vals))
    p = text_layer(f"Portrait Tag {k}", "PORTRAIT", 34, C, C - 135, rgb=(120, 255, 160)).state("opacity", 1, 1, 1)
    p.landscape = {"opacity": (0, 0, 0)}
    q = text_layer(f"Landscape Tag {k}", "LANDSCAPE", 34, C, C - 135, rgb=(255, 140, 200), opacity=0)
    q.state("opacity", 0, 0, 0).landscape = {"opacity": (1, 1, 1)}
    bg.add(p, q)
    fl = group(f"FLOATING {k}")
    for y, what in BANDS:
        b = band(f"Band {y} {k}", f"{tag} FLOATING  y={y} ({what})", y, (200, 30, 60) if k == "ONE" else (20, 140, 90))
        par = group(f"Band Parallax {y} {k}", kind="CATransformLayer").add(b)
        par.parallax = 60
        fl.add(par)
    return bg, fl


def groups(tree, view):
    par, props = [], []

    def walk_(l):
        if l.parallax:
            for axis in ("x", "y"):
                par.append([("axis", "string", axis), ("image", "string", "null"),
                            ("keyPath", "string", f"transform.translation.{axis}"), ("layerName", "string", l.name),
                            ("mapMaxTo", "integer", l.parallax), ("mapMinTo", "integer", -l.parallax),
                            ("title", "string", "Gyro"), ("view", "string", view)])
        land = getattr(l, "landscape", {})
        for kp, (lock, home, sleep) in l.states.items():
            ll, lh, ls = land.get(kp, (lock, home, sleep))
            props.append([("keyPath", "string", kp), ("landscape_home", "real", lh), ("landscape_lock", "real", ll),
                          ("landscape_sleep", "real", ls), ("layerName", "string", l.name),
                          ("portrait_home", "real", home), ("portrait_lock", "real", lock),
                          ("portrait_sleep", "real", sleep)])
        for c in l.children:
            walk_(c)

    walk_(tree)
    return par, props


def dict_xml(items, ind):
    out = [f"{ind}<NSDictionary>"]
    for key, typ, val in items:
        v = kit.f(float(val)) if typ in ("real", "integer") else kit.esc(str(val))
        if typ == "integer":
            v = str(int(val))
        out.append(f'{ind}  <{key} type="{typ}" value="{v}"/>')
    out.append(f"{ind}</NSDictionary>")
    return out


def array_xml(tag, dicts, ind):
    if not dicts:
        return [f'{ind}<{tag} type="NSArray"/>']
    out = [f'{ind}<{tag} type="NSArray">']
    for d in dicts:
        out += dict_xml(d, ind + "  ")
    return out + [f"{ind}</{tag}>"]


def build():
    asset("grid.png", grid_image())
    trees, style = [], ["    <style>", '      <wallpapers type="NSArray">']
    for sc in SCREENS:
        bg, fl = screen_trees(sc)
        trees.append((sc, bg, fl))
        bpar, bprops = groups(bg, "Background")
        fpar, fprops = groups(fl, "Floating")
        ind = "          "
        style.append("        <NSDictionary>")
        style.append(f'{ind}<backgroundAssetNames type="NSArray"/>')
        style.append(f'{ind}<backgroundLayerName type="string" value="{bg.name}"/>')
        style += array_xml("backgroundParallaxGroups", bpar, ind)
        style += array_xml("backgroundPropertyGroups", bprops, ind)
        style.append(f'{ind}<floatingAssetNames type="NSArray"/>')
        style.append(f'{ind}<floatingLayerName type="string" value="{fl.name}"/>')
        style += array_xml("floatingParallaxGroups", fpar, ind)
        style += array_xml("floatingPropertyGroups", fprops, ind)
        for key in ("idealHeight", "idealWidth", "pixelHeight", "pixelParallaxBleed", "pixelSquareWithParallax",
                    "pixelSquareWithoutParallax", "pixelWidth"):
            style.append(f'{ind}<{key} type="integer" value="{sc[key]}"/>')
        style.append(f'{ind}<retinaMultiplier type="integer" value="3"/>')
        style.append(f'{ind}<screenName type="string" value="{sc["screenName"]}"/>')
        style.append(f'{ind}<supportsLandscape type="integer" value="1"/>')
        style.append("        </NSDictionary>")
    style += ["      </wallpapers>", "    </style>"]
    # Apple's order: the Inner Display's trees first
    root = Layer("Root Layer", S, S, C, C)
    for sc, bg, fl in sorted(trees, key=lambda t: t[0]["key"] != "ONE"):
        root.add(bg, fl)
    names = [l.name for l, _ in kit.walk(root)]
    assert len(names) == len(set(names)), "duplicate layer names"
    head = (f'  <CALayer id="root" name="Root Layer" bounds="0 0 {kit.f(S)} {kit.f(S)}" '
            f'position="{kit.f(C)} {kit.f(C)}" zPosition="0" geometryFlipped="0" opacity="1" '
            'backgroundColor="0 0 0" allowsEdgeAntialiasing="1" allowsGroupOpacity="1" contentsFormat="RGBA8" '
            'cornerCurve="circular">')
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<caml xmlns="http://www.apple.com/CoreAnimation/1.0">', head]
    lines += style + ["    <sublayers>"]
    for c in root.children:
        lines += kit.layer_xml(c, "      ")
    lines += ["    </sublayers>", "    <modules/>", "  </CALayer>", "</caml>", ""]
    return root, "\n".join(lines)


def main():
    root, caml = build()
    out, ident, _, ca_name = package(caml, os.path.join(OUT, f"{OUT_NAME}.tendies"), BUILD)
    mem = sum(im.width * im.height * 4 for im in kit.ASSETS.values()) / 2 ** 20
    print(f"layers: {sum(1 for _ in kit.walk(root))}, assets: {len(kit.ASSETS)}, decoded ~{mem:.0f} MB")
    print(f"tendies: {out}  identity: {ident}  CA: {ca_name}")
    if "--sheet" in sys.argv:
        kit.ASSETS["grid.png"].resize((700, 700)).save(os.path.join(BUILD, "grid_small.png"))


if __name__ == "__main__":
    main()
