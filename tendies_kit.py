# -*- coding: utf-8 -*-
"""
tendies_kit — shared engine for AirCard .tendies lock-screen wallpapers on the iPhone Duo.

* scene graph (Layer) -> CAPlayground-style ParameterizedCA main.caml with gyro (wallpaperParallaxGroups)
  and Lock/Home/Sleep values (wallpaperPropertyGroups); coordinates are y-up (geometryFlipped = 0)
* packaging with the iOS 27 depth + gyro fix built in (Clownfish CA bundle name + rendering
  configuration archives); import the result with AirCard Depth Test
* device model: PosterBoard aspect-fills the square S x S root, so the folded screen, the unfolded
  portrait screen and the unfolded landscape screen each show a centred crop (VIEWS); the user's clock
  position per posture was measured from device screenshots (CLOCK)
* preview renderer that composites BACKGROUND, clock and FLOATING per posture
"""
import hashlib
import math
import os
import plistlib
import random
import shutil
import uuid
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

# PosterKit metadata of a device-verified CAPlayground gyro export (its wallpaper.ca removed), copied into
# every package; only the CA bundle and the identity fields are replaced
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")
REF_UUID = "99990000-0000-0000-0000-000000000000"
WALLPAPER_DIR = "7400.WWDC_2022-390w-844h@3x~iphone.wallpaper"
PRODUCT_TYPES = ["iPhone19,4", "iPhone18,4"]   # iPhone Duo, iPhone Air
CLOCK_FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
LABEL_FONT = r"C:\Windows\Fonts\msjh.ttc"

S = 890.0          # square root canvas (pt) == inner display long side
C = S / 2
PPT = 3.0          # target pixels per point (@3x)

VIEWS = {          # name: (crop rect in root pt (x0, y0, x1, y1), device size in pt)
    "folded":           ((C - S * 466 / 678 / 2, 0, C + S * 466 / 678 / 2, S), (466, 678)),
    "unfolded_portrait": ((C - S * 626 / 890 / 2, 0, C + S * 626 / 890 / 2, S), (626, 890)),
    "unfolded_landscape": ((0, C - S * 626 / 890 / 2, S, C + S * 626 / 890 / 2), (890, 626)),
}
# the user's Lock Screen clock as fractions of the view (x0, x1, top, bottom), measured from device
# screenshots. Root-space bottoms: folded y~434, unfolded portrait y~561, unfolded landscape y~479.
CLOCK = {
    "folded":             (0.084, 0.753, 0.1075, 0.5125),
    "unfolded_portrait":  (0.272, 0.729, 0.095, 0.37),
    "unfolded_landscape": (0.341, 0.659, 0.117, 0.445),
}
STATES = ("lock", "home", "sleep")


# ----------------------------------------------------------------------------
# image helpers
# ----------------------------------------------------------------------------
def load(path):
    im = Image.open(path)
    im.load()
    return im


def trim(im, thr=3, pad=4):
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > thr)
    x0, x1 = max(0, xs.min() - pad), min(im.width, xs.max() + 1 + pad)
    y0, y1 = max(0, ys.min() - pad), min(im.height, ys.max() + 1 + pad)
    return im.crop((x0, y0, x1, y1)), (x0, y0)


def resize_premul(im, size):
    """Lanczos resize without dark fringes on transparent edges."""
    size = (max(1, int(round(size[0]))), max(1, int(round(size[1]))))
    if im.size == size:
        return im
    return im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def alpha_glow(alpha_img, rgb, scale=0.25, dilate=8, blur=10, pad=60, strength=1.0):
    """Soft coloured glow built from an alpha mask (perfectly aligned with its source)."""
    a = alpha_img.resize((max(1, int(alpha_img.width * scale)), max(1, int(alpha_img.height * scale))),
                         Image.BILINEAR)
    a = np.pad(np.asarray(a), pad)
    if dilate:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1, dilate * 2 + 1))
        a = cv2.dilate(a, k)
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), blur)
    a = np.clip(a * strength, 0, 255).astype(np.uint8)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = rgb
    out[..., 3] = a
    return Image.fromarray(out, "RGBA"), pad / scale   # pad expressed in source pixels


def lum_to_alpha(im, rgb=(255, 255, 255), gain=1.6):
    l = np.asarray(im.convert("L"), np.float32) * gain
    out = np.zeros(l.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = rgb
    out[..., 3] = np.clip(l, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def extract_shards(im, count, min_area=500):
    a = np.asarray(im.getchannel("A"))
    n, lab, stats, _ = cv2.connectedComponentsWithStats((a > 24).astype(np.uint8), connectivity=8)
    comps = [(stats[i, cv2.CC_STAT_AREA], i) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area]
    comps.sort(reverse=True)
    shards = []
    for _, i in comps[:count]:
        x, y, w, h = (int(v) for v in stats[i, :4])
        x0, y0 = max(0, x - 4), max(0, y - 4)
        x1, y1 = min(im.width, x + w + 4), min(im.height, y + h + 4)
        crop = np.asarray(im.crop((x0, y0, x1, y1))).copy()
        crop[..., 3] = np.where(lab[y0:y1, x0:x1] == i, crop[..., 3], 0)  # drop neighbours inside bbox
        shards.append(Image.fromarray(crop, "RGBA"))
    return shards


# ----------------------------------------------------------------------------
# scene graph
# ----------------------------------------------------------------------------
class Layer:
    _ids = {}

    def __init__(self, name, w, h, x, y, kind="CALayer", img=None, color=None, opacity=1.0,
                 rot=0.0, scale=1.0, anchor=(0.5, 0.5), trilinear=False):
        self.name, self.w, self.h, self.x, self.y = name, float(w), float(h), float(x), float(y)
        self.kind, self.img, self.color, self.opacity = kind, img, color, opacity
        self.rot, self.scale, self.anchor, self.trilinear = rot, scale, anchor, trilinear
        self.children, self.anim, self.states, self.parallax, self.emitter = [], None, {}, None, None
        base = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
        Layer._ids[base] = Layer._ids.get(base, 0) + 1
        self.id = base if Layer._ids[base] == 1 else f"{base}-{Layer._ids[base]}"

    def add(self, *layers):
        self.children.extend(layers)
        return self

    def animate(self, key_path, values, duration, autoreverses=True, timing="easeInEaseOut",
                key_times=None, offset=0.0):
        self.anim = dict(keyPath=key_path, values=values, duration=duration, autoreverses=autoreverses,
                         timing=timing, keyTimes=key_times, offset=offset)
        return self

    def state(self, key_path, lock, home, sleep):
        self.states[key_path] = (lock, home, sleep)
        return self


ASSETS = {}


def asset(name, im):
    ASSETS[name] = im.convert("RGBA")
    return name


def image_layer(name, key, h=None, w=None, x=C, y=C, **kw):
    iw, ih = ASSETS[key].size
    if w is None:
        w = h * iw / ih
    if h is None:
        h = w * ih / iw
    return Layer(name, w, h, x, y, img=key, **kw)


def group(name, kind="CALayer", w=S, h=S, x=C, y=C, **kw):
    return Layer(name, w, h, x, y, kind=kind, **kw)



# ----------------------------------------------------------------------------
# CAML
# ----------------------------------------------------------------------------
def f(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    s = f"{v:.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def anim_xml(a, ind):
    kp = a["keyPath"]
    attrs = (f'key="animation-0" type="CAKeyframeAnimation" keyPath="{kp}" autoreverses="{f(a["autoreverses"])}" '
             f'beginTime="1e-100" duration="{f(a["duration"])}" speed="1" removedOnCompletion="0" '
             f'repeatCount="inf" repeatDuration="inf" calculationMode="linear" timingFunction="{a["timing"]}"')
    if a["offset"]:
        attrs += f' timeOffset="{f(a["offset"])}"'
    out = [f"{ind}<animations>", f"{ind}  <animation {attrs}>"]
    if a["keyTimes"]:
        out.append(f"{ind}    <keyTimes>")
        out += [f'{ind}      <real value="{f(t)}"/>' for t in a["keyTimes"]]
        out.append(f"{ind}    </keyTimes>")
    out.append(f"{ind}    <values>")
    for v in a["values"]:
        if kp == "position":
            out.append(f'{ind}      <CGPoint value="{f(v[0])} {f(v[1])}"/>')
        elif kp in ("position.x", "position.y"):
            out.append(f'{ind}      <integer value="{int(round(v))}"/>')
        else:
            out.append(f'{ind}      <real value="{f(v)}"/>')
    out += [f"{ind}    </values>", f"{ind}  </animation>", f"{ind}</animations>"]
    return out


def layer_xml(l, ind="    "):
    a = [("id", l.id), ("name", l.name), ("bounds", f"0 0 {f(l.w)} {f(l.h)}"), ("position", f"{f(l.x)} {f(l.y)}")]
    if l.anchor != (0.5, 0.5):
        a.append(("anchorPoint", f"{f(l.anchor[0])} {f(l.anchor[1])}"))
    a += [("zPosition", "0"), ("geometryFlipped", "0"), ("masksToBounds", "0"), ("opacity", f(l.opacity))]
    if l.rot or l.scale != 1:
        a.append(("transform.rotation.z", f(l.rot)))
        t = f"rotate({f(math.degrees(l.rot))}deg)"
        if l.scale != 1:
            t += f" scale({f(l.scale)}, {f(l.scale)}, 1)"
        a.append(("transform", t))
    if l.color:
        a.append(("backgroundColor", " ".join(f(c) for c in l.color)))
    if l.trilinear:
        a.append(("minificationFilter", "trilinear"))
    if l.emitter:
        e = l.emitter
        a += [("emitterPosition", f"{f(l.w / 2)} {f(l.h / 2)}"), ("emitterSize", f"{f(e['size'][0])} {f(e['size'][1])}"),
              ("emitterShape", "rectangle"), ("emitterMode", e["mode"]), ("renderMode", e["render"]),
              ("birthRate", "1")]
    a += [("allowsEdgeAntialiasing", "1"), ("allowsGroupOpacity", "1"), ("contentsFormat", "RGBA8"),
          ("cornerCurve", "circular")]
    out = [f"{ind}<{l.kind} " + " ".join(f'{k}="{esc(v)}"' for k, v in a) + ">"]
    i2 = ind + "  "
    if l.img:
        out += [f"{i2}<contents>", f'{i2}  <CGImage src="assets/{l.img}"/>', f"{i2}</contents>"]
    if l.emitter:
        out.append(f"{i2}<emitterCells>")
        for c in l.emitter["cells"]:
            ca = [("id", c["name"].lower().replace(" ", "-")), ("name", c["name"]), ("enabled", "1"),
                  ("contentsScale", "1"), ("birthRate", f(c["birthRate"])), ("lifetime", f(c["lifetime"])),
                  ("lifetimeRange", f(c["lifetimeRange"])), ("velocity", f(c["velocity"])),
                  ("velocityRange", f(c["velocityRange"])), ("emissionRange", f(2 * math.pi)),
                  ("emissionLongitude", "0"), ("emissionLatitude", "0"), ("scale", f(c["scale"])),
                  ("scaleRange", f(c["scaleRange"])), ("scaleSpeed", "0"), ("alphaRange", "0.3"),
                  ("alphaSpeed", f(c["alphaSpeed"])), ("spin", "0"), ("spinRange", f(c["spinRange"])),
                  ("xAcceleration", "0"), ("yAcceleration", "0")]
            out.append(f"{i2}  <CAEmitterCell " + " ".join(f'{k}="{v}"' for k, v in ca) + ">")
            out.append(f'{i2}    <color value="{" ".join(f(v) for v in c["color"])}" opacity="{f(c["alpha"])}"/>')
            out += [f"{i2}    <contents>", f'{i2}      <CGImage src="assets/{c.get("img", "mote.png")}"/>', f"{i2}    </contents>"]
            out.append(f"{i2}  </CAEmitterCell>")
        out.append(f"{i2}</emitterCells>")
    if l.children:
        out.append(f"{i2}<sublayers>")
        for c in l.children:
            out += layer_xml(c, i2 + "  ")
        out.append(f"{i2}</sublayers>")
    if l.anim:
        out += anim_xml(l.anim, i2)
    out.append(f"{ind}</{l.kind}>")
    return out


def walk(l, view=None):
    view = view or {"BACKGROUND": "Background", "FLOATING": "Floating"}.get(l.name)
    yield l, view
    for c in l.children:
        yield from walk(c, view)


def style_xml(root):
    par, props = [], []
    for l, view in walk(root):
        if l.parallax:
            for axis in ("x", "y"):
                par += ["        <NSDictionary>",
                        f'          <axis type="string" value="{axis}"/>',
                        '          <image type="string" value="null"/>',
                        f'          <keyPath type="string" value="transform.translation.{axis}"/>',
                        f'          <layerName type="string" value="{esc(l.name)}"/>',
                        f'          <mapMaxTo type="integer" value="{l.parallax}"/>',
                        f'          <mapMinTo type="integer" value="{-l.parallax}"/>',
                        '          <title type="string" value="Gyro"/>',
                        f'          <view type="string" value="{view}"/>',
                        "        </NSDictionary>"]
        for kp, (lock, home, sleep) in l.states.items():
            props += ["        <NSDictionary>",
                      '          <image type="null"/>',
                      f'          <keyPath type="string" value="{kp}"/>',
                      f'          <layerName type="string" value="{esc(l.name)}"/>',
                      f'          <v_home type="real" value="{f(float(home))}"/>',
                      f'          <v_lock type="real" value="{f(float(lock))}"/>',
                      f'          <v_sleep type="real" value="{f(float(sleep))}"/>',
                      f'          <view type="string" value="{view}"/>',
                      "        </NSDictionary>"]
    return (["    <style>",
             '      <wallpaperBackgroundAssetNames type="NSArray"/>',
             '      <wallpaperFloatingAssetNames type="NSArray"/>',
             '      <wallpaperParallaxGroups type="NSArray">'] + par +
            ["      </wallpaperParallaxGroups>",
             '      <wallpaperPropertyGroups type="NSArray">'] + props +
            ["      </wallpaperPropertyGroups>", "    </style>"])


def build_caml(root):
    names = [l.name for l, _ in walk(root)]
    dup = {n for n in names if names.count(n) > 1}
    assert not dup, f"duplicate layer names: {dup}"
    head = (f'  <CALayer id="root" name="Root Layer" bounds="0 0 {f(S)} {f(S)}" position="{f(C)} {f(C)}" '
            'zPosition="0" geometryFlipped="0" opacity="1" backgroundColor="0.035 0.02 0.045" '
            'allowsEdgeAntialiasing="1" allowsGroupOpacity="1" contentsFormat="RGBA8" cornerCurve="circular">')
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<caml xmlns="http://www.apple.com/CoreAnimation/1.0">', head]
    lines += style_xml(root)
    lines.append("    <sublayers>")
    for c in root.children:
        lines += layer_xml(c, "      ")
    lines += ["    </sublayers>", "    <modules/>", "  </CALayer>", "</caml>", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# preview renderer (approximation of Core Animation, y-up)
# ----------------------------------------------------------------------------
def ease(u):
    return u * u * (3 - 2 * u)


def anim_value(a, t):
    d = a["duration"]
    tt = t + a["offset"]
    if a["autoreverses"]:
        ph = tt % (2 * d)
        u = ph / d if ph < d else 2 - ph / d
    else:
        u = (tt % d) / d
    if a["timing"] == "easeInEaseOut":
        u = ease(u)
    vals = a["values"]
    kts = a["keyTimes"] or [i / (len(vals) - 1) for i in range(len(vals))]
    for i in range(len(kts) - 1):
        if u <= kts[i + 1] or i == len(kts) - 2:
            s = 0 if kts[i + 1] == kts[i] else min(1, max(0, (u - kts[i]) / (kts[i + 1] - kts[i])))
            v0, v1 = vals[i], vals[i + 1]
            if isinstance(v0, tuple):
                return tuple(p + (q - p) * s for p, q in zip(v0, v1))
            return v0 + (v1 - v0) * s
    return vals[-1]


_cache = {}


def preview_img(key, w_px, h_px):
    w_px, h_px = max(2, int(w_px)), max(2, int(h_px))
    src = ASSETS[key]
    tw = min(src.width, max(8, w_px * 2))           # keep 2x supersampling for the affine warp
    th = max(2, int(round(tw * src.height / src.width)))
    ck = (key, tw)
    if ck not in _cache:
        _cache[ck] = resize_premul(src, (tw, th)).convert("RGBa")
    return _cache[ck]


def render(root, t, state_vals, k, only=None, opaque=True, tilt=(0.0, 0.0)):
    """tilt: simulated device motion in -1..1 per axis, applied to every gyro (parallax) layer."""
    W = int(S * k)
    canvas = Image.new("RGBa", (W, W), (0, 0, 0, 255 if opaque else 0))
    prng = random.Random(7)

    def draw(l, M, op):
        vals = state_vals.get(l.name, {})
        x, y, o = vals.get("position.x", l.x), vals.get("position.y", l.y), vals.get("opacity", l.opacity)
        rot = vals.get("transform.rotation.z", l.rot)
        sc = vals.get("transform.scale.xy", l.scale)
        if l.anim:
            v = anim_value(l.anim, t)
            kp = l.anim["keyPath"]
            if kp == "position":
                x, y = v
            elif kp == "position.x":
                x = v
            elif kp == "position.y":
                y = v
            elif kp == "opacity":
                o = v
            elif kp == "transform.rotation.z":
                rot = v
            elif kp == "transform.scale":
                sc = v
        op *= o
        if op <= 0.003:
            return
        if l.parallax:
            x, y = x + tilt[0] * l.parallax, y + tilt[1] * l.parallax
        c, s = math.cos(rot), math.sin(rot)
        local = (np.array([[1, 0, x], [0, 1, y], [0, 0, 1]]) @
                 np.array([[c * sc, -s * sc, 0], [s * sc, c * sc, 0], [0, 0, 1]]) @
                 np.array([[1, 0, -l.anchor[0] * l.w], [0, 1, -l.anchor[1] * l.h], [0, 0, 1]]))
        M = M @ local
        to_canvas = np.array([[k, 0, 0], [0, -k, S * k], [0, 0, 1]])
        if l.img or l.color:
            if l.img:
                im = preview_img(l.img, l.w * k * sc, l.h * k * sc)
            else:
                im = Image.new("RGBa", (4, 4), tuple(int(255 * ch) for ch in l.color) + (255,))
            iw, ih = im.size
            px2local = np.array([[l.w / iw, 0, 0], [0, -l.h / ih, l.h], [0, 0, 1]])
            A = to_canvas @ M @ px2local
            inv = np.linalg.inv(A)
            warped = im.transform((W, W), Image.AFFINE, tuple(inv[:2].flatten()), resample=Image.BILINEAR)
            arr = np.asarray(warped).astype(np.float32) * op
            base = np.asarray(canvas).astype(np.float32)
            out = arr + base * (1 - arr[..., 3:4] / 255)
            canvas.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBa"))
        if l.emitter:
            d = ImageDraw.Draw(canvas)
            for cell in l.emitter["cells"]:
                for _ in range(int(cell["birthRate"] * cell["lifetime"] * 0.6)):
                    px = prng.uniform(-575, 575) + l.w / 2 + 6 * math.sin(t * 0.7 + prng.random() * 6)
                    py = prng.uniform(-575, 575) + l.h / 2 + 6 * math.cos(t * 0.5 + prng.random() * 6)
                    X, Y, _ = to_canvas @ M @ np.array([px, py, 1])
                    r = max(1, 32 * cell["scale"] * prng.uniform(0.6, 1.4) * k)
                    a = int(255 * cell["alpha"] * op * prng.uniform(0.3, 1))
                    col = tuple(int(a * ch) for ch in cell["color"]) + (a,)
                    d.ellipse((X - r, Y - r, X + r, Y + r), fill=col)
        for ch in l.children:
            draw(ch, M, op)

    for ch in root.children:
        if only is None or ch.name == only:
            draw(ch, np.eye(3), 1.0)
    return canvas.convert("RGBA")


def posture_views(root, t, svals, k, clock_alpha, stretch=0.0, tilt=(0.0, 0.0), depth=True):
    """BACKGROUND, clock, FLOATING (depth effect), cropped per posture.
    depth=False draws the clock last, as on the Always-On Display."""
    bg = render(root, t, svals, k, only="BACKGROUND", tilt=tilt)
    fl = render(root, t, svals, k, only="FLOATING", opaque=False, tilt=tilt)
    out = []
    for v in VIEWS:
        im = crop_view(bg, v, k).convert("RGBA")
        if depth:
            im = with_clock(im, v, clock_alpha, stretch)
            im.alpha_composite(crop_view(fl, v, k))
        else:
            im.alpha_composite(crop_view(fl, v, k))
            im = with_clock(im, v, clock_alpha, stretch)
        out.append(im.convert("RGB"))
    return out


def state_values(root, mix):
    """mix: dict state -> weight (sums to 1)."""
    out = {}
    for l, _ in walk(root):
        for kp, vals in l.states.items():
            out.setdefault(l.name, {})[kp] = sum(vals[STATES.index(s)] * w for s, w in mix.items())
    return out


def crop_view(img, view, k):
    (x0, y0, x1, y1), dev = VIEWS[view]
    box = (int(x0 * k), int((S - y1) * k), int(x1 * k), int((S - y0) * k))
    return img.crop(box)


def with_clock(img, view, alpha, stretch=0.0):
    """Overlay a mock iOS tall clock where the iPhone Duo Lock Screen draws it.
    stretch: extra clock height as a fraction of the view (the clock length is user-adjustable)."""
    if alpha <= 0.01:
        return img
    x0, x1, t, b = CLOCK[view]
    b += stretch
    W, H = img.size
    bw, bh = int((x1 - x0) * W), int((b - t) * H)
    big = ImageFont.truetype(CLOCK_FONT, 220)
    glyphs = Image.new("L", (1000, 320), 0)
    ImageDraw.Draw(glyphs).text((10, 10), "9:41", font=big, fill=255)
    glyphs = glyphs.crop(glyphs.getbbox()).resize((bw, bh), Image.LANCZOS)  # stretched like the tall clock
    ink = Image.new("RGBA", (bw, bh), (255, 255, 255, 255))
    ink.putalpha(glyphs.point(lambda v: int(v * 0.92 * alpha)))
    out = img.convert("RGBA")
    out.alpha_composite(ink, (int(x0 * W), int(t * H)))
    small = ImageFont.truetype(CLOCK_FONT, max(8, int(H * 0.03)))
    ImageDraw.Draw(out).text(((x0 + x1) / 2 * W, t * H - H * 0.014), "Wed Oct 28", font=small,
                             fill=(255, 255, 255, int(235 * alpha)), anchor="ms")
    return out




def make_previews(root, preview_dir, names):
    """names: display name per state, e.g. {"lock": "鎖定 Hiro", "home": "主畫面 Ema", "sleep": "待機 AOD・Duo"}."""
    os.makedirs(preview_dir, exist_ok=True)
    k = 1.0
    view_names = {"folded": "闔上（外螢幕）", "unfolded_portrait": "打開・直向", "unfolded_landscape": "打開・橫向"}
    rows = [(f"{names['lock']}・你的時鐘（景深：角色在時鐘前）", "lock", 1.0, 0.0, (0, 0), True),
            (f"{names['lock']}・陀螺儀極限傾斜（檢查邊緣）", "lock", 1.0, 0.0, (-1, 1), True),
            (names["home"], "home", 0.0, 0.0, (0, 0), True),
            (f"{names['sleep']}（無景深，時鐘在最上層）", "sleep", 1.0, 0.0, (0, 0), False)]
    tiles = [posture_views(root, 1.2, state_values(root, {st: 1.0}), k, ca, stretch, tilt, depth)
             for _, st, ca, stretch, tilt, depth in rows]
    for st in STATES:
        render(root, 1.2, state_values(root, {st: 1.0}), k).save(os.path.join(preview_dir, f"square_{st}.png"))
    font = ImageFont.truetype(LABEL_FONT, 20)
    pad, lab = 24, 34
    colw = [max(t[i].width for t in tiles) for i in range(3)]
    rowh = [max(im.height for im in row) for row in tiles]
    sheet = Image.new("RGB", (sum(colw) + pad * 4, sum(rowh) + (pad + lab) * len(rows) + pad), (22, 20, 26))
    d = ImageDraw.Draw(sheet)
    y = pad
    for (label, *_), row in zip(rows, tiles):
        x = pad
        for i, (v, im) in enumerate(zip(VIEWS, row)):
            d.text((x, y + 6), f"{label}｜{view_names[v]}", fill=(235, 220, 230), font=font)
            sheet.paste(im, (x, y + lab))
            x += colw[i] + pad
        y += max(im.height for im in row) + lab + pad
    sheet.save(os.path.join(preview_dir, "states_x_postures.png"))

    # animated preview: idle -> unlock -> idle -> lock -> sleep, with a slow simulated device tilt
    k = 0.42
    fps = 12
    plan = [("lock", None, 2.5), ("lock", "home", 0.8), ("home", None, 2.5), ("home", "lock", 0.6),
            ("lock", None, 1.0), ("lock", "sleep", 0.9), ("sleep", None, 2.5), ("sleep", "lock", 0.6)]
    frames, t = [], 0.0
    for a, b, dur in plan:
        for i in range(int(dur * fps)):
            u = ease(i / max(1, dur * fps - 1)) if b else 0
            mix = {a: 1 - u, b: u} if b else {a: 1.0}
            tilt = (0.8 * math.sin(t * 0.9), 0.6 * math.cos(t * 0.7))
            views = posture_views(root, t, state_values(root, mix), k, 1.0 - mix.get("home", 0.0),
                                  tilt=tilt, depth=mix.get("sleep", 0.0) < 0.5)
            Wt = sum(v.width for v in views) + 10 * 4
            Ht = max(v.height for v in views) + 20
            fr = Image.new("RGB", (Wt, Ht), (22, 20, 26))
            x = 10
            for v in views:
                fr.paste(v, (x, 10 + (Ht - 20 - v.height) // 2))
                x += v.width + 10
            frames.append(fr.quantize(colors=200, method=Image.Quantize.MEDIANCUT))
            t += 1 / fps
    frames[0].save(os.path.join(preview_dir, "animation_preview.gif"), save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, optimize=False)

    transition_strip(root, "lock", "home", os.path.join(preview_dir, "transition_lock_home.png"))
    transition_strip(root, "lock", "sleep", os.path.join(preview_dir, "transition_lock_sleep.png"))
    lum = state_luminance(root)
    print("luminance (Y, L*):", lum, f" home/lock Y ratio {lum['home'][0] / lum['lock'][0]:.2f}")


def state_luminance(root, view="folded", k=0.5):
    """Mean linear luminance Y and L* of each state as seen in one posture (clock hidden).
    The user wants Lock / Home / Sleep in one lighting world: keep the home/lock Y ratio at about 1.5 or less."""
    i = list(VIEWS).index(view)
    out = {}
    for st in STATES:
        im = posture_views(root, 1.2, state_values(root, {st: 1.0}), k, 0.0)[i]
        a = np.asarray(im).astype(np.float32) / 255
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        y = float((lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean())
        out[st] = (round(y, 4), round(116 * y ** (1 / 3) - 16, 1))
    return out


def transition_strip(root, a, b, path, steps=6, k=0.5, views=("folded", "unfolded_portrait")):
    """Frames of the a -> b swipe (u = 0 .. 1, linear like the device), one row per posture.
    Use it to check reveals, occlusion and cross-fades mid-transition, which the end-state previews never show."""
    idx = [list(VIEWS).index(v) for v in views]
    cols = []
    for j in range(steps):
        u = j / (steps - 1)
        mix = {a: 1 - u, b: u} if a != b else {a: 1.0}
        vs = posture_views(root, 1.2, state_values(root, mix), k, 1.0 - mix.get("home", 0.0),
                           depth=mix.get("sleep", 0.0) < 0.5)
        cols.append([vs[i] for i in idx])
    cw = max(c[r].width for c in cols for r in range(len(idx)))
    rh = [max(c[r].height for c in cols) for r in range(len(idx))]
    sheet = Image.new("RGB", (steps * (cw + 8) + 8, sum(rh) + 8 * (len(idx) + 1)), (22, 20, 26))
    for j, c in enumerate(cols):
        y = 8
        for r, im in enumerate(c):
            sheet.paste(im, (8 + j * (cw + 8), y))
            y += rh[r] + 8
    sheet.save(path)
    return path


# ----------------------------------------------------------------------------
# packaging
# ----------------------------------------------------------------------------
INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>rootDocument</key>
  <string>main.caml</string>
</dict>
</plist>
"""
MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>

<caml xmlns="http://www.apple.com/CoreAnimation/1.0">
  <MicaAssetManifest>
    <modules type="NSArray"/>
  </MicaAssetManifest>
</caml>
"""


RENDER_CLASS = {"$classname": "PRPosterRenderingConfiguration",
                "$classes": ["PRPosterRenderingConfiguration", "NSObject"]}
EFFECTS_ON = {"depthEffectDisabled": False, "motionEffectsDisabled": False}


def binplist(value):
    return plistlib.dumps(value, fmt=plistlib.FMT_BINARY, sort_keys=False)


def keyed(archive):
    objects = archive["$objects"]
    return objects, objects[archive["$top"]["root"].data]


def check_uids(value, count):
    if isinstance(value, plistlib.UID):
        assert 0 <= value.data < count, "dangling keyed-archive reference"
    elif isinstance(value, dict):
        for v in value.values():
            check_uids(v, count)
    elif isinstance(value, list):
        for v in value:
            check_uids(v, count)


def package(caml, out_path, build_dir):
    """Write the .tendies, plus an inspectable copy of main.caml and the assets in build_dir."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    pngs = {}
    for key, im in ASSETS.items():
        p = os.path.join(build_dir, "assets", key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        im.save(p, compress_level=7)
        with open(p, "rb") as fh:
            pngs[key] = fh.read()
    with open(os.path.join(build_dir, "main.caml"), "w", encoding="utf-8") as fh:
        fh.write(caml)

    # Poster identity follows the content: re-exporting an unchanged build keeps it, any change gets a
    # fresh descriptor/gallery identity so iOS never serves a cached older import.
    h = hashlib.sha256(caml.encode("utf-8"))
    for key in sorted(pngs):
        h.update(key.encode())
        h.update(pngs[key])
    digest = h.digest()
    ident = 100000 + int.from_bytes(digest[:4], "big") % 900000
    desc_uuid = str(uuid.UUID(bytes=digest[4:20], version=4)).upper()
    gallery_uuid = str(uuid.UUID(bytes=digest[16:32], version=4)).upper()

    # iOS 27 ParameterizedCA depth effect (verified on device 2026-10-25): WallpaperKit only enables it
    # when the CA bundle path contains "Clownfish" (case-sensitive), so the bundle is named for it.
    ca_name = f"{ident}.Clownfish_Gyro.ca"
    desc = f"descriptors/{desc_uuid}"
    version = f"{desc}/versions/0"
    contents = f"{version}/contents"
    bundle = f"{contents}/{WALLPAPER_DIR}"
    ca = f"{bundle}/{ca_name}"

    files = {}
    for dirpath, _, names in os.walk(TEMPLATE_DIR):
        for n in names:
            path = os.path.join(dirpath, n)
            name = os.path.relpath(path, TEMPLATE_DIR).replace(os.sep, "/")
            if name.endswith("Wallpaper.plist"):
                continue
            with open(path, "rb") as fh:
                files[name.replace(f"descriptors/{REF_UUID}", desc)] = fh.read()
    with open(os.path.join(TEMPLATE_DIR, "descriptors", REF_UUID, "versions", "0", "contents", WALLPAPER_DIR,
                           "Wallpaper.plist"), "rb") as fh:
        wp = plistlib.loads(fh.read())

    # keep ParameterizedCA (LayeredAnimation loses gyro), the family and the nested asset identifier
    wp["assets"]["lockAndHome"]["default"]["assetFileName"] = ca_name
    wp["identifier"] = ident
    wp["wantsDeviceMotion"] = True
    wp["productTypes"] = list(dict.fromkeys(wp.get("productTypes", []) + PRODUCT_TYPES))
    files[f"{bundle}/Wallpaper.plist"] = binplist(wp)

    ui_path = f"{contents}/com.apple.posterkit.provider.contents.userInfo"
    ui = plistlib.loads(files[ui_path])
    ui["wallpaperRepresentingIdentifier"] = str(ident)        # string, like every shipped template
    files[ui_path] = binplist(ui)
    files[f"{desc}/com.apple.posterkit.provider.descriptor.identifier"] = str(ident).encode()

    meta_path = f"{desc}/com.apple.posterkit.provider.identifierURL.suggestionMetadata.plist"
    meta = plistlib.loads(files[meta_path])
    objects, root = keyed(meta)
    gallery = objects[root["suggestedGalleryItem"].data]
    objects[gallery["identifier"].data] = gallery_uuid
    objects[gallery["descriptorIdentifier"].data] = f"{ident}.DYNAMIC"
    files[meta_path] = binplist(meta)

    # depth + motion switches. The options file is dot-prefixed: the importer must keep hidden files
    # (AirCard Depth Test does; stock AirCard drops them).
    opt_path = f"{contents}/.com.apple.posterkit.provider.contents.configurableOptions.plist"
    opts = plistlib.loads(files[opt_path])
    objects, root = keyed(opts)
    if "preferredRenderingConfiguration" in root:
        objects[root["preferredRenderingConfiguration"].data].update(EFFECTS_ON)
    else:
        class_id = len(objects)
        objects.append(dict(RENDER_CLASS))
        root["preferredRenderingConfiguration"] = plistlib.UID(len(objects))
        objects.append({"$class": plistlib.UID(class_id), **EFFECTS_ON})
    if "role" not in root:
        root["role"] = plistlib.UID(len(objects))
        objects.append("PRPosterRoleLockScreen")
    files[opt_path] = binplist(opts)
    files[f"{version}/com.apple.posterkit.provider.instance.renderingConfiguration.plist"] = binplist({
        "$version": 100000, "$archiver": "NSKeyedArchiver", "$top": {"root": plistlib.UID(1)},
        "$objects": ["$null", {"$class": plistlib.UID(2), **EFFECTS_ON}, dict(RENDER_CLASS)]})

    files[f"{ca}/index.xml"] = INDEX_XML.encode()
    files[f"{ca}/assetManifest.caml"] = MANIFEST.encode()
    files[f"{ca}/main.caml"] = caml.encode("utf-8")
    for key, data in pngs.items():
        files[f"{ca}/assets/{key}"] = data
    for name, data in files.items():
        if name.endswith((".plist", ".userInfo")):
            obj = plistlib.loads(data)
            if isinstance(obj, dict) and "$objects" in obj:
                check_uids(obj, len(obj["$objects"]))

    dirs = set()
    for name in files:
        parts = name.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]) + "/")
    out = out_path
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dname in sorted(dirs):
            z.writestr(zipfile.ZipInfo(dname), b"")
        for name in sorted(files):
            z.writestr(name, files[name])
    return out, ident, desc_uuid, ca_name
