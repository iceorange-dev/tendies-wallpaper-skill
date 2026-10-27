# -*- coding: utf-8 -*-
"""
珠洲島有栖 (ONGEKI, R.B.P.) — "Arisu's little theatre", an AirCard .tendies for the iPhone Duo.

Her official line 「んっしょ、んっしょ（着ぐるみ脱ぎ中）……じゃーん。驚いた？」 is staged as a show
on the R.B.P. stage (the team's official backdrop is a theatre):
  Lock   the indigo velvet curtain is closed; a spotlight finds a suspicious raccoon kigurumi swaying
         on the boards (「もし校内で怪しい着ぐるみを見かけても、暖かい目で見守ろう」), dust drifting in
         the beam, paw prints of her dogs, a playbill for her boss song "Titania" by the curtain
  Home   unlocking raises the show: the kigurumi pops into jelly stars, side lights come on and the
         curtain draws apart on Arisu herself, waiting behind it in her raccoon-hooded Shooter Dress —
         "じゃーん。驚いた？" — with her jelly-star bits and confetti. The set behind is cardboard props on strings, all from her
         profile: a moon and stars, the bear from her favourite picture books, and a hamburger
         (「……お腹減った　ハンバーガーを要求する」)
  Sleep  Always-On Display: the curtain is closed again and she naps on her fluffy dog in front of it,
         kept below the clock

Lock and Home share the same stage and lighting, so the brightness only shifts with the curtain.

Sources (sources/arisu); the character art is Real-ESRGAN x4plus-anime 4x, resampled here to exactly @3x:
  raccoon_kigurumi_x4.png  story sprite Chara_00101210 (her raccoon kigurumi)
  kigurumi_100351_x4.png   game card 100351 【R】シュータードレス：全身ver., character layer
  siesta_101012_x4.png     game card 101012 【SR+】もふもふシエスタ, character layer
  jacket_0098_titania.png  jacket of "Titania" (xi), a song with Arisu as its boss; used at native size
"""
import math
import os
import random
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from tendies_kit import *  # noqa: F401,F403  (scene graph, CAML, packaging, previews, device model)
import tendies_art as art
from tendies_art import *  # noqa: F401,F403  (shared generators: glows, beams, motes, fades)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources", "arisu")
OUT_NAME = "Suzushima-Arisu-Fold"
OUT = os.path.join(HERE, "out")                  # every generated file: .tendies, build/, preview/
BUILD = os.path.join(OUT, "build", "arisu")
PREVIEW = os.path.join(OUT, "preview", "arisu")

CHAR_TOP = 556.0   # Lock: head just under the user's folded clock; the depth effect lets it overlap
AOD_TOP = 410.0    # Sleep: AOD has no depth, the clock bottom is at root y ~434 when folded

FLOOR_Y = 190.0    # back edge of the stage boards, where the painted cloth starts
CURTAIN_HEM = 140.0   # the curtain hangs over the boards in front of that: Arisu waits on the strip behind it
CURTAIN_W, CURTAIN_TOP = 600.0, 1010.0

AQUA = (90, 214, 255)
ICE = (160, 226, 255)
LAVENDER = (190, 168, 255)
PINK = (255, 186, 226)
GOLD = (236, 196, 112)
INK = (44, 36, 74)       # cardboard outline

rng = random.Random(20180906)   # Arisu's birthday


# ----------------------------------------------------------------------------
# source art
# ----------------------------------------------------------------------------
def source(name, **kw):
    return load_source(os.path.join(SRC, name), **kw)


# ----------------------------------------------------------------------------
# generated art (smooth surfaces at >= 1.5 px/pt, fine detail drawn at 4x and reduced to @3x)
# ----------------------------------------------------------------------------
VELVET = ((7, 10, 36), (30, 44, 124), (112, 140, 236))


def fringe(w, h, seed):
    """Gold bullion fringe: fine strands of slightly different lengths."""
    r = np.random.default_rng(seed)
    x = np.arange(w)
    strand = 0.5 + 0.5 * np.cos(2 * np.pi * x / 5.0)
    length = np.repeat(r.uniform(0.78, 1.0, w // 5 + 1), 5)[:w]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    alpha = (yy < length[None, :]) * (0.55 + 0.45 * strand[None, :])
    alpha *= smooth((length[None, :] - yy) * 12)
    lum = 0.55 + 0.45 * strand[None, :] - 0.25 * yy
    col = np.array(GOLD, np.float32) * lum[..., None]
    return col, alpha


def velvet_panel(w, h, folds, seed, edge):
    """Theatre curtain panel: irregular vertical folds, velvet sheen, gold trim and fringed hem."""
    r = np.random.default_rng(seed)
    x = np.linspace(0, 1, w, dtype=np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    freq = folds * (1 + 0.32 * np.sin(2 * np.pi * (x * 1.3 + r.uniform())) +
                    0.14 * np.sin(2 * np.pi * (x * 3.7 + r.uniform())))
    phase = 2 * np.pi * np.cumsum(freq) / w
    lean = 0.8 * np.sin(np.pi * y * 0.85 + r.uniform(0, 3))
    s = 0.5 + 0.5 * np.cos(phase[None, :] + lean)
    lum = 0.10 + 0.68 * s ** 2.2 + 0.16 * np.exp(-((s - 0.6) / 0.1) ** 2)
    lum *= 0.70 + 0.30 * np.sin(np.pi * np.clip(0.06 + y * 0.97, 0, 1))
    lum += cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.1) * 0.035
    col = ramp3(lum, *VELVET)
    alpha = np.ones((h, w), np.float32)
    tw = int(w * 0.024)                                         # gold trim on the leading edge
    bevel = (0.55 + 0.45 * np.cos(np.linspace(-np.pi / 2, np.pi / 2, tw)))[None, :, None]
    trim_col = np.array(GOLD, np.float32) * bevel * (0.75 + 0.25 * s[:, :tw, None])
    if edge == "right":
        col[:, -tw:] = trim_col
    else:
        col[:, :tw] = trim_col[:, ::-1]
    fh = int(h * 0.05)                                          # fringe below a gold hem band
    band = int(h * 0.012)
    col[h - fh - band:h - fh] = np.array(GOLD, np.float32) * (0.7 + 0.3 * np.cos(np.linspace(-1.5, 1.5, band)))[:, None, None]
    fcol, fa = fringe(w, fh, seed + 1)
    col[h - fh:] = fcol
    alpha[h - fh:] = fa
    return Image.fromarray(np.dstack([col, alpha * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def valance(w, h, swags, seed):
    """Swagged top drape with fringe along the scalloped edge."""
    x = np.linspace(0, 1, w, dtype=np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    u = (x * swags) % 1
    edge = 0.60 + 0.26 * np.sin(np.pi * u)                    # bottom of each swag (fraction of height)
    t = y / edge[None, :]
    s = 0.5 + 0.5 * np.cos(2 * np.pi * (t * 4.2 + 0.2 * np.sin(np.pi * u)[None, :]))
    lum = (0.12 + 0.62 * s ** 2 + 0.14 * np.exp(-((s - 0.6) / 0.1) ** 2)) * (0.6 + 0.4 * np.sin(np.pi * u))[None, :]
    lum += cv2.GaussianBlur(np.random.default_rng(seed).normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.1) * 0.03
    col = ramp3(lum, *VELVET)
    alpha = smooth((edge[None, :] - y) * h / 3)
    fh = 0.12
    fcol, fa = fringe(w, int(h * fh), seed + 1)
    rows = ((y - edge[None, :]) / fh)                          # 0..1 inside the fringe under the edge
    inside = (rows >= 0) & (rows < 1)
    idx = np.clip((rows * fa.shape[0]).astype(int), 0, fa.shape[0] - 1)
    cols = np.broadcast_to(np.arange(w)[None, :], idx.shape)
    col = np.where(inside[..., None], fcol[idx, cols], col)
    alpha = np.where(inside, fa[idx, cols], alpha)
    band = np.abs(y - edge[None, :]) < 0.012                    # gold hem along the scallops
    col = np.where(band[..., None], np.array(GOLD, np.float32), col)
    alpha = np.where(band, 1.0, alpha)
    return Image.fromarray(np.dstack([col, alpha * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def stage_floor(w, h, seed):
    """Dark boards running toward the back of the stage; shadow where the curtain meets them."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2(xx - w / 2, yy + 2.6 * h)                 # vanishing point above the image
    k = 0.0105
    plank = np.floor(ang / k)
    frac = ang / k - plank
    tone = r.uniform(0.82, 1.12, 400)[(plank.astype(int) + 200) % 400]
    grain = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=0.8, sigmaY=9) * 0.06
    lum = (0.48 + 0.25 * (yy / h)) * tone + grain
    lum *= 1 - 0.55 * np.exp(-(np.minimum(frac, 1 - frac) / 0.035) ** 2)   # seams
    lum *= 0.45 + 0.55 * smooth(yy / (h * 0.35))                           # shadow under the curtain
    col = ramp3(lum, (16, 10, 12), (62, 40, 34), (120, 84, 64))
    return Image.fromarray(col.clip(0, 255).astype(np.uint8), "RGB")


def backdrop(w, h, seed):
    """Painted night cloth behind the curtain (kept plain low down, where Arisu stands in front of it)."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    col = np.array([10, 22, 54], np.float32) * (1 - v[..., None]) + np.array([20, 74, 100], np.float32) * v[..., None]
    paint = cv2.resize(cv2.GaussianBlur(r.normal(0, 1, (h // 16, w // 16)).astype(np.float32), (0, 0), 1.5),
                       (w, h), interpolation=cv2.INTER_CUBIC)
    strokes = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=14, sigmaY=2)
    col *= (1 + 0.08 * paint + 0.05 * strokes)[..., None]
    img = Image.fromarray(col.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    dots = Image.new("RGBA", (w, h), (0, 0, 0, 0))              # painted dots of stars, blended over the cloth
    dd = ImageDraw.Draw(dots)
    for _ in range(140):
        x, y, s = r.uniform(0, w), r.uniform(0, h * 0.7), r.uniform(1.5, 4)
        dd.ellipse((x - s, y - s, x + s, y + s), fill=(220, 236, 255, int(r.uniform(60, 170))))
    img.alpha_composite(dots)
    return img


def jelly_star(px, rgb):
    """Translucent aqua 'bit' like the stars of her Shooter Dress, with rim light and glow."""
    N = px * 4
    m = Image.new("L", (N, N), 0)
    ImageDraw.Draw(m).polygon(star_points(N / 2, N * 0.53, N * 0.34, N * 0.165), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(N * 0.03)).point(lambda v: 255 if v > 120 else 0)
    m = m.filter(ImageFilter.GaussianBlur(2.4))
    ma = np.asarray(m, np.float32) / 255
    xx, yy = grid(N)
    t = np.clip(xx * 0.35 + yy * 0.85, 0, 1)[..., None]
    col = np.array([236, 252, 255], np.float32) * (1 - t) + np.array(rgb, np.float32) * t
    er = cv2.erode((ma * 255).astype(np.uint8), np.ones((int(N * 0.05),) * 2, np.uint8)).astype(np.float32) / 255
    rim = np.clip(ma - er, 0, 1)
    hl = np.exp(-(((xx - 0.40) / 0.09) ** 2 + ((yy - 0.40) / 0.05) ** 2)) * ma
    col = col * (1 - rim[..., None] * 0.55) + 255 * rim[..., None] * 0.55
    col = col * (1 - hl[..., None] * 0.9) + 255 * hl[..., None] * 0.9
    alpha = np.clip(ma * 0.6 + rim * 0.4 + hl * 0.4, 0, 1)
    glow = cv2.GaussianBlur(ma, (0, 0), N * 0.06) * 0.55
    return resize_premul(Image.alpha_composite(rgba(rgb, glow), rgba(col, alpha)), (px, px))


def paw(px):
    N = px * 4
    m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((0.25 * N, 0.45 * N, 0.75 * N, 0.92 * N), fill=255)
    for cx, cy in ((0.16, 0.40), (0.37, 0.19), (0.63, 0.19), (0.84, 0.40)):
        d.ellipse(((cx - 0.10) * N, (cy - 0.125) * N, (cx + 0.10) * N, (cy + 0.125) * N), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2.5))
    return resize_premul(rgba((228, 220, 250), np.asarray(m, np.float32) / 255), (px, px))


def glyph_z(px):
    font = ImageFont.truetype(CLOCK_FONT, px * 3)
    im = Image.new("L", (px * 4, px * 4), 0)
    ImageDraw.Draw(im).text((px * 0.6, 0), "z", font=font, fill=255)
    im = im.crop(im.getbbox())
    a = np.pad(np.asarray(im, np.float32) / 255, px // 3)
    glow = cv2.GaussianBlur(a, (0, 0), px * 0.12) * 0.6
    out = Image.alpha_composite(rgba(LAVENDER, np.clip(glow, 0, 1)), rgba((250, 248, 255), a))
    return resize_premul(out, (out.width / 4, out.height / 4))


# --- cardboard props on strings ------------------------------------------------
def cardboard(draw, px, thread_pt):
    """Flat painted cardboard cut-out hung on a gold thread: ink outline, cut-edge thickness, soft shadow.
    `draw(d, N)` paints the prop on an N x N canvas (4x supersampled). The returned image is anchored at
    the top of its thread."""
    N = px * 4
    art = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    draw(ImageDraw.Draw(art), N)
    a = np.asarray(art)[..., 3].astype(np.float32) / 255
    ring = np.clip(cv2.dilate(a, np.ones((int(N * 0.035),) * 2, np.uint8)) - a, 0, 1)
    edge = np.roll(np.roll(a, int(N * 0.02), 0), int(N * 0.02), 1)
    shadow = cv2.GaussianBlur(np.roll(np.roll(a, int(N * 0.07), 0), int(N * 0.05), 1), (0, 0), N * 0.03) * 0.45
    out = rgba((0, 0, 0), shadow)
    out = Image.alpha_composite(out, rgba((70, 52, 46), edge))
    out = Image.alpha_composite(out, art)
    out = Image.alpha_composite(out, rgba(INK, ring))
    L = int(thread_pt * PPT * 4)
    full = Image.new("RGBA", (N, N + L), (0, 0, 0, 0))
    ImageDraw.Draw(full).line((N // 2, 0, N // 2, L + int(N * 0.12)), fill=GOLD + (230,), width=6)
    full.alpha_composite(out, (0, L))
    return resize_premul(full, (px, (N + L) / 4))


def draw_moon(d, N):
    d.ellipse((0.12 * N, 0.12 * N, 0.88 * N, 0.88 * N), fill=(255, 232, 160, 255))
    d.ellipse((0.34 * N, 0.02 * N, 1.02 * N, 0.70 * N), fill=(0, 0, 0, 0))
    d.ellipse((0.30 * N, 0.52 * N, 0.40 * N, 0.62 * N), fill=(236, 200, 120, 255))      # painted craters
    d.ellipse((0.20 * N, 0.36 * N, 0.27 * N, 0.43 * N), fill=(236, 200, 120, 255))


def draw_star(rgb):
    def f(d, N):
        d.polygon(star_points(N / 2, N * 0.52, N * 0.40, N * 0.18), fill=rgb + (255,))   # room for the shadow
        d.polygon(star_points(N * 0.47, N * 0.48, N * 0.12, N * 0.055), fill=(255, 255, 255, 255))
    return f


def draw_bear(d, N):
    """The bear from her favourite picture books."""
    fur, inner, dark = (196, 146, 104, 255), (238, 206, 170, 255), (70, 44, 34, 255)
    for ex in (0.24, 0.76):
        d.ellipse(((ex - 0.15) * N, 0.10 * N, (ex + 0.15) * N, 0.40 * N), fill=fur)
        d.ellipse(((ex - 0.08) * N, 0.17 * N, (ex + 0.08) * N, 0.33 * N), fill=inner)
    d.ellipse((0.12 * N, 0.20 * N, 0.88 * N, 0.92 * N), fill=fur)
    d.ellipse((0.33 * N, 0.56 * N, 0.67 * N, 0.84 * N), fill=inner)
    for ex in (0.36, 0.64):
        d.ellipse(((ex - 0.04) * N, 0.46 * N, (ex + 0.04) * N, 0.54 * N), fill=dark)
    d.ellipse((0.44 * N, 0.60 * N, 0.56 * N, 0.68 * N), fill=dark)
    d.arc((0.42 * N, 0.62 * N, 0.58 * N, 0.76 * N), 20, 160, fill=dark, width=max(2, N // 60))
    d.ellipse((0.20 * N, 0.60 * N, 0.29 * N, 0.66 * N), fill=(255, 170, 170, 200))
    d.ellipse((0.71 * N, 0.60 * N, 0.80 * N, 0.66 * N), fill=(255, 170, 170, 200))


def draw_burger(d, N):
    """「……お腹減った　ハンバーガーを要求する」"""
    d.rounded_rectangle((0.10 * N, 0.70 * N, 0.90 * N, 0.86 * N), radius=N * 0.07, fill=(226, 150, 74, 255))
    d.rounded_rectangle((0.08 * N, 0.56 * N, 0.92 * N, 0.70 * N), radius=N * 0.06, fill=(112, 64, 42, 255))
    d.polygon([(0.10 * N, 0.56 * N), (0.90 * N, 0.56 * N), (0.78 * N, 0.66 * N), (0.62 * N, 0.58 * N),
               (0.44 * N, 0.67 * N), (0.30 * N, 0.58 * N)], fill=(255, 204, 64, 255))
    pts = [(0.06 * N + i * 0.088 * N, (0.50 if i % 2 else 0.56) * N) for i in range(11)]
    d.polygon([(0.06 * N, 0.48 * N)] + pts + [(0.94 * N, 0.48 * N)], fill=(124, 200, 96, 255))
    d.chord((0.08 * N, 0.14 * N, 0.92 * N, 0.82 * N), 180, 360, fill=(232, 160, 80, 255))
    for sx, sy in ((0.30, 0.30), (0.46, 0.24), (0.62, 0.29), (0.38, 0.40), (0.56, 0.38), (0.72, 0.40)):
        d.ellipse(((sx - 0.025) * N, (sy - 0.015) * N, (sx + 0.025) * N, (sy + 0.015) * N), fill=(255, 246, 220, 255))


def playbill(jacket, w_pt, h_pt):
    """Tonight's programme: the song jacket in a gold frame on a wooden easel."""
    N = 4
    W, H = int(w_pt * PPT * N), int(h_pt * PPT * N)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    wood, wood_dark = (112, 74, 52, 255), (70, 46, 34, 255)
    side = int(W * 0.84)
    x0, y0 = (W - side) // 2, int(H * 0.02)
    d.polygon([(W * 0.47, y0 + side * 0.4), (W * 0.53, y0 + side * 0.4), (W * 0.56, H), (W * 0.50, H)], fill=wood_dark)
    for top_x, foot_x in ((0.30, 0.10), (0.70, 0.90)):
        d.polygon([(W * (top_x - 0.035), y0 + side * 0.3), (W * (top_x + 0.035), y0 + side * 0.3),
                   (W * (foot_x + 0.04), H), (W * (foot_x - 0.04), H)], fill=wood)
    d.rectangle((x0 - W * 0.04, y0 + side, x0 + side + W * 0.04, y0 + side + W * 0.06), fill=wood)
    bevel = int(W * 0.045)
    for i in range(bevel):
        t = i / bevel
        g = tuple(int(c * (0.65 + 0.35 * math.sin(math.pi * t))) for c in GOLD) + (255,)
        d.rectangle((x0 + i, y0 + i, x0 + side - i, y0 + side - i), outline=g)
    art = jacket.convert("RGB").resize((side - 2 * bevel, side - 2 * bevel), Image.LANCZOS)
    im.paste(art, (x0 + bevel, y0 + bevel))
    return resize_premul(im, (W / N, H / N))


# ----------------------------------------------------------------------------
# reusable motion pieces
# ----------------------------------------------------------------------------
def floating_bit(*args, **kw):
    return art.floating_bit(rng, *args, **kw)


def hanging(*args, **kw):
    return art.hanging(rng, *args, **kw)


# ----------------------------------------------------------------------------
# scene
# ----------------------------------------------------------------------------
def build_background():
    asset("backdrop.png", backdrop(1800, 1150, seed=21))
    asset("floor.png", stage_floor(2800, 440, seed=22))
    asset("curtain_left.png", velvet_panel(1200, 1760, folds=9.5, seed=23, edge="right"))
    asset("curtain_right.png", velvet_panel(1200, 1760, folds=9.5, seed=24, edge="left"))
    asset("valance.png", valance(2800, 440, swags=6, seed=25))
    asset("beam.png", beam(360, 900))
    asset("pool.png", pool(512, 160))
    asset("stage_glow.png", soft_glow(512, (255, 214, 170), 0.55))
    asset("vignette.png", vignette())
    asset("sparkle.png", sparkle(96))
    asset("mote.png", mote(36))
    asset("paw.png", paw(60))
    # threads hang from above the valance (bottom edge ~736-793) so every prop clears it
    asset("prop_moon.png", cardboard(draw_moon, 540, 180))
    asset("prop_bear.png", cardboard(draw_bear, 270, 230))
    asset("prop_burger.png", cardboard(draw_burger, 220, 330))
    for i, rgb in enumerate(((255, 214, 102), (124, 222, 255), (255, 214, 102), (196, 176, 255), (255, 190, 220))):
        asset(f"prop_star{i + 1}.png", cardboard(draw_star(rgb), 150, (220, 260, 180, 320, 240)[i]))

    root_bg = group("BACKGROUND")
    root_bg.id = "background"
    base = group("Stage Base", w=2800, h=2800, color=(0.02, 0.02, 0.07))

    # the set behind the curtain: painted cloth + cardboard props, revealed when the curtain opens
    cloth = image_layer("Backdrop", "backdrop.png", w=1200, x=C, y=560, trilinear=True)
    set_glow = image_layer("Set Glow", "stage_glow.png", w=1000, x=C, y=470, opacity=0.0)
    set_glow.state("opacity", 0.0, 0.35, 0.0)
    cloth_par = group("Backdrop Parallax", kind="CATransformLayer").add(cloth, set_glow)
    cloth_par.parallax = 6
    props = group("Props Parallax", kind="CATransformLayer")
    props.parallax = 9
    for name, key, w, x in (("Prop Moon", "prop_moon.png", 180, 240), ("Prop Bear", "prop_bear.png", 90, 650),
                            ("Prop Burger", "prop_burger.png", 72, 560), ("Prop Star 1", "prop_star1.png", 50, 140),
                            ("Prop Star 2", "prop_star2.png", 42, 370), ("Prop Star 3", "prop_star3.png", 36, 470),
                            ("Prop Star 4", "prop_star4.png", 46, 760), ("Prop Star 5", "prop_star5.png", 38, 840)):
        props.add(hanging(name, key, w, x, 930))

    floor = image_layer("Stage Floor", "floor.png", w=1400, x=C, y=FLOOR_Y - 220 + 220 / 2 + 5, trilinear=True)
    pool_ = image_layer("Light Pool", "pool.png", w=560, x=C, y=MASCOT_FEET)
    pool_.state("opacity", 1.0, 0.55, 0.45)   # follows the centre spot dimming for the show
    paws = group("Paw Trail", opacity=0.8).state("opacity", 0.8, 0.8, 0.0)
    step, period = 0.42, 9.0
    for i in range(14):
        px = 70 + i * 54
        py = 70 + 8 * math.sin(i * 0.55) + (7 if i % 2 else -7)
        p = Layer(f"Paw {i + 1}", 15, 15, px, py, img="paw.png", rot=math.radians(-90 + 8 * math.sin(i)))
        p.animate("opacity", [0, 0.7, 0.7, 0, 0], period, autoreverses=False, timing="linear",
                  key_times=[0, 0.03, 0.30, 0.50, 1], offset=(period - i * step) % period)
        paws.add(p)
    floor_par = group("Floor Parallax", kind="CATransformLayer").add(floor, pool_, paws)
    floor_par.parallax = 10

    # the curtain: each panel slides on its track (state) and sways a little (animation)
    ch = CURTAIN_TOP + 10 - CURTAIN_HEM
    cy = CURTAIN_HEM + ch / 2
    curtains = group("Curtain Parallax", kind="CATransformLayer")
    curtains.parallax = 12
    for side, key, closed, opened in (("Left", "curtain_left.png", C + 8 - CURTAIN_W / 2, 176 - CURTAIN_W / 2),
                                      ("Right", "curtain_right.png", C - 8 + CURTAIN_W / 2, 714 + CURTAIN_W / 2)):
        panel = Layer(f"Curtain {side}", CURTAIN_W, ch, CURTAIN_W / 2, ch, img=key, anchor=(0.5, 1.0))
        panel.animate("transform.rotation.z", [math.radians(-0.35), math.radians(0.35)],
                      7.0 if side == "Left" else 8.3, offset=0 if side == "Left" else 2.5)
        track = Layer(f"Curtain {side} Track", CURTAIN_W, ch, closed, cy).add(panel)
        track.state("position.x", closed, opened, closed)
        curtains.add(track)
    drape = image_layer("Valance", "valance.png", w=1400, x=C, y=925 - 220 / 2)
    glints = group("Fringe Glints")
    for i in range(9):
        s = rng.uniform(10, 18)
        gx = rng.uniform(30, 860)
        g = Layer(f"Glint {i + 1}", s, s, gx, 925 - 220 * (0.60 + 0.26 * abs(math.sin(math.pi * ((gx + 255) / 1400 * 6 % 1)))) - 8,
                  img="sparkle.png")
        g.animate("opacity", [0.0, 0.0, 0.95, 0.0], rng.uniform(2.6, 4.2), autoreverses=False, timing="easeInEaseOut",
                  key_times=[0, 0.55, 0.75, 1], offset=rng.uniform(0, 4))
        glints.add(g)
    drape_par = group("Valance Parallax", kind="CATransformLayer").add(drape, glints)
    drape_par.parallax = 12

    # lighting: one spot on the closed curtain, the stage lights join when the show starts
    spot = Layer("Spot Centre", 470, 1030, C, 1030, img="beam.png", anchor=(0.5, 1.0))
    spot.animate("transform.rotation.z", [math.radians(-1.4), math.radians(1.4)], 9.0)
    spot_fade = group("Spot Centre Fade").state("opacity", 1.0, 0.45, 0.35).add(spot)
    # the spot spilling onto the closed curtain behind the kigurumi
    wash = image_layer("Curtain Wash", "stage_glow.png", w=820, x=C, y=430, opacity=0.9)
    wash.state("opacity", 0.9, 0.0, 0.25)
    sides = group("Side Lights", opacity=0.0).state("opacity", 0.0, 0.5, 0.0)
    for name, x, deg in (("Side Light Left", 30, 19.0), ("Side Light Right", 860, -19.0)):
        b = Layer(name, 420, 1120, x, 1040, img="beam.png", anchor=(0.5, 1.0), rot=math.radians(deg))
        b.animate("transform.rotation.z", [math.radians(deg - 2.5), math.radians(deg + 2.5)], 6.5,
                  offset=0 if x < C else 3.2)
        sides.add(b)
    motes = group("Beam Motes").state("opacity", 1.0, 0.6, 0.3)
    for i in range(16):
        y = rng.uniform(180, 900)
        half = 30 + (900 - y) / 900 * 190
        motes.add(floating_bit(f"Mote {i + 1}", "mote.png", rng.uniform(3, 7), C + rng.uniform(-half, half), y,
                               alpha_lo=0.15, drift=(10, 34)))
    light_par = group("Light Parallax", kind="CATransformLayer").add(wash, spot_fade, sides, motes)
    light_par.parallax = 7

    # tonight's programme, standing by the curtain at stage right (packed away for the nap)
    asset("playbill.png", playbill(load(os.path.join(SRC, "jacket_0098_titania.png")), 120, 250))
    bill = image_layer("Playbill", "playbill.png", w=120, x=688, y=122 + 125)
    bill_fade = group("Playbill Fade").state("opacity", 1.0, 1.0, 0.0).add(bill)
    bill_par = group("Playbill Parallax", kind="CATransformLayer").add(bill_fade)
    bill_par.parallax = 11

    vig = image_layer("Vignette", "vignette.png", w=1300)
    sleep_dim = group("Sleep Dim", w=2800, h=2800, color=(0.0, 0.0, 0.03), opacity=0.0)
    sleep_dim.state("opacity", 0.0, 0.0, 0.3)

    root_bg.add(base, cloth_par, props, floor_par, curtains, drape_par, bill_par, light_par, vig, sleep_dim)
    return root_bg


MASCOT_FEET = 105.0   # the kigurumi stands on the boards, its head just reaching the clock


def build_mascot():
    """Lock: a suspicious raccoon kigurumi swaying in the spotlight."""
    top = CHAR_TOP - 12
    im, w, h = source("raccoon_kigurumi_x4.png", height_pt=top - MASCOT_FEET)
    k = asset("raccoon_kigurumi.png", im)
    asset("shadow.png", soft_glow(256, (0, 0, 0), 0.85))
    ppt = h / im.height
    rim_img, pad = alpha_glow(im.getchannel("A"), WARM, scale=0.2, dilate=3, blur=8, pad=30, strength=0.7)
    kr = asset("raccoon_kigurumi_rim.png", rim_img)
    rim = Layer("Mascot Rim", (im.width + 2 * pad) * ppt, (im.height + 2 * pad) * ppt, w / 2, h / 2, img=kr,
                opacity=0.5)
    # mascot wobble: rocks from its feet
    wobble = Layer("Mascot Wobble", w, h, C, MASCOT_FEET, anchor=(0.5, 0.0))
    wobble.add(rim, Layer("Mascot Body", w, h, w / 2, h / 2, img=k, trilinear=True))
    wobble.animate("transform.rotation.z", [math.radians(-3.0), math.radians(3.0)], 2.4)
    hop = group("Mascot Hop").add(wobble)
    hop.animate("position.y", [C, C, C + 7, C, C], 4.8, autoreverses=False, timing="linear",
                key_times=[0, 0.42, 0.5, 0.58, 1])
    shadow = Layer("Mascot Shadow", w * 1.05, 26, C, MASCOT_FEET + 4, img="shadow.png", opacity=0.75)
    par = group("Mascot Parallax", kind="CATransformLayer").add(shadow, hop)
    par.parallax = 12
    cy = MASCOT_FEET + h / 2
    # a second fade inside the first: the opacities multiply to (1 - u)^2 over the swipe, so the
    # kigurumi is mostly gone before the curtain has opened far enough to show Arisu behind it
    fade = group("Mascot Fade").state("opacity", 1.0, 0.0, 0.0).add(par)
    stage = Layer("Mascot Stage", S, S, C, cy, anchor=(0.5, cy / S))
    stage.state("opacity", 1.0, 0.0, 0.0).state("transform.scale.xy", 1.0, 1.22, 1.0)
    return stage.add(fade), (C, cy)


SHOOTER_FEET = 190.0   # Home: she stands on the back edge of the boards, so the closed curtain hides her
SHOOTER_H = 518.0      # her hood clears the valance swags (lowest ~736) through the float and sway


def build_shooter():
    """Home: じゃーん — the curtain opens on Arisu herself, in her raccoon-hooded Shooter Dress.

    Returns (behind, front). `behind` (Arisu and the bits behind her) goes into BACKGROUND under the
    curtain panels, which reveal her as they open; the bits nearest the audience stay in FLOATING.
    """
    im, w, h = source("kigurumi_100351_x4.png", fade=dict(right=0.05), height_pt=SHOOTER_H)
    k = asset("arisu_shooter.png", im)
    cx, cy = C, SHOOTER_FEET + h / 2
    ppt = h / im.height
    kk = SHOOTER_H / 600   # the bits' orbit was laid out around a 600 pt figure
    aura_img, pad = alpha_glow(im.getchannel("A"), AQUA, scale=0.2, dilate=5, blur=10, pad=36, strength=0.9)
    ka = asset("arisu_shooter_aura.png", aura_img)
    aura = Layer("Shooter Aura", (im.width + 2 * pad) * ppt, (im.height + 2 * pad) * ppt, w / 2, h / 2, img=ka)
    aura.animate("opacity", [0.25, 0.55], 3.0)
    sway = Layer("Shooter Sway", w, h, cx, cy).add(aura, Layer("Shooter Body", w, h, w / 2, h / 2, img=k,
                                                                 trilinear=True))
    sway.animate("transform.rotation.z", [math.radians(-1.2), math.radians(1.2)], 7.0)
    float_ = group("Shooter Float").add(sway)
    float_.animate("position.y", [C, C + 10], 5.2)
    # the shadow stays on the boards while she floats
    shadow = Layer("Shooter Shadow", w * 0.75, 22, cx, SHOOTER_FEET - 2, img="shadow.png", opacity=0.55)
    # between the floor (10) and the curtain (12): she is upstage of the curtain line
    char_par = group("Shooter Char Parallax", kind="CATransformLayer").add(shadow, float_)
    char_par.parallax = 11

    for key, rgb in (("jelly_aqua.png", AQUA), ("jelly_ice.png", ICE), ("jelly_lavender.png", LAVENDER)):
        asset(key, jelly_star(150, rgb))
    keys = ("jelly_aqua.png", "jelly_ice.png", "jelly_lavender.png")
    back = group("Shooter Bits Back", kind="CATransformLayer")
    back.parallax = 9
    front = group("Shooter Bits Front", kind="CATransformLayer")
    front.parallax = 44
    for i in range(9):
        ang = 2 * math.pi * (i + rng.uniform(-0.25, 0.25)) / 9 + 0.4
        deg = math.degrees(ang) % 360
        if 60 < deg < 120:                       # keep her face clear
            ang += math.radians(55 if deg >= 90 else -55)
        x = cx + kk * rng.uniform(220, 330) * math.cos(ang)
        y = cy + kk * (40 + rng.uniform(160, 240) * math.sin(ang))
        (front if i % 3 == 0 else back).add(floating_bit(f"Shooter Bit {i + 1}", keys[i % 3], rng.uniform(26, 46), x, y))

    # already standing behind the closed curtain on Lock (fully covered, CURTAIN_HEM < her feet), so the
    # opening curtain reveals her crisply; she grows from her feet as it parts, staying planted on the boards
    behind = Layer("Shooter Stage", S, S, C, SHOOTER_FEET, anchor=(0.5, SHOOTER_FEET / S), scale=0.9)
    behind.state("opacity", 1.0, 1.0, 0.0).state("transform.scale.xy", 0.9, 1.0, 0.9)
    spill = Layer("Shooter Bits Stage", S, S, C, cy, anchor=(0.5, cy / S), opacity=0.0, scale=0.82)
    spill.state("opacity", 0.0, 1.0, 0.0).state("transform.scale.xy", 0.82, 1.0, 0.82)
    return behind.add(back, char_par), spill.add(front)


def build_show(mascot_centre):
    """Home: the jelly stars burst out of the kigurumi and confetti falls over the stage."""
    burst = group("Burst Stars", kind="CATransformLayer")
    burst.parallax = 26
    keys = ("jelly_aqua.png", "jelly_lavender.png", "jelly_ice.png")
    kx, ky = mascot_centre
    for i in range(12):
        ang = 2 * math.pi * i / 12 + rng.uniform(-0.2, 0.2) + 0.3
        hx = C + rng.uniform(250, 400) * math.cos(ang)
        hy = 400 + rng.uniform(190, 320) * math.sin(ang)
        lx, ly = kx + rng.uniform(-40, 40), ky + rng.uniform(-30, 60)
        s = rng.uniform(30, 50)
        spin = Layer(f"Burst Star {i + 1} Spin", s, s, s / 2, s / 2, img=keys[i % 3])
        spin.animate("transform.rotation.z", [0.0, math.radians(rng.choice([-1, 1]) * rng.uniform(20, 40))],
                     rng.uniform(3.5, 6.5), offset=rng.uniform(0, 4))
        star = Layer(f"Burst Star {i + 1}", s, s, lx, ly, opacity=0.0).add(spin)
        star.state("position.x", lx, hx, lx).state("position.y", ly, hy, ly).state("opacity", 0.0, 0.85, 0.0)
        burst.add(star)

    colours = (AQUA, LAVENDER, PINK, GOLD)
    for i, rgb in enumerate(colours):
        asset(f"confetti{i + 1}.png", confetti(30, 54, rgb))
    rain = group("Confetti", opacity=0.0).state("opacity", 0.0, 1.0, 0.0)
    for i in range(26):
        piece = Layer(f"Confetti {i + 1}", rng.uniform(7, 10), rng.uniform(12, 17), rng.uniform(40, 850), C,
                      img=f"confetti{i % 4 + 1}.png")
        turns = rng.choice([-1, 1]) * 2 * math.pi
        piece.animate("transform.rotation.z", [0.0, turns], rng.uniform(1.8, 3.6), autoreverses=False,
                      timing="linear", offset=rng.uniform(0, 3))
        sway = group(f"Confetti {i + 1} Sway").add(piece)
        amp = rng.uniform(10, 24)
        sway.animate("position.x", [C - amp, C + amp], rng.uniform(1.6, 2.8), offset=rng.uniform(0, 3))
        fall = group(f"Confetti {i + 1} Fall").add(sway)
        dur = rng.uniform(7, 12)
        fall.animate("position.y", [960, -40], dur, autoreverses=False, timing="linear", offset=rng.uniform(0, dur))
        rain.add(fall)
    rain_par = group("Confetti Parallax", kind="CATransformLayer").add(rain)
    rain_par.parallax = 34
    return burst, rain_par


def build_siesta():
    """Sleep / AOD: もふもふシエスタ in front of the closed curtain, wholly below the clock."""
    # the card crops the dog at the left and right: a spotlight around Arisu dissolves both edges in a curve
    im, w, h = source("siesta_101012_x4.png", fade=dict(left=0.05), spot=(0.42, 0.40, 0.40, 0.62), width_pt=640)
    k = asset("arisu_siesta.png", im)
    top = AOD_TOP
    bottom = top - h
    ppt = h / im.height
    glow_img, pad = alpha_glow(im.getchannel("A"), LAVENDER, scale=0.2, dilate=4, blur=10, pad=30, strength=0.7)
    kg = asset("arisu_siesta_glow.png", glow_img)
    glow = Layer("Siesta Glow", (im.width + 2 * pad) * ppt, (im.height + 2 * pad) * ppt, w / 2, h / 2, img=kg,
                 opacity=0.45)
    breathe = Layer("Siesta Breathe", w, h, C, bottom, anchor=(0.5, 0.0))
    breathe.add(glow, Layer("Siesta Body", w, h, w / 2, h / 2, img=k, trilinear=True))
    breathe.animate("transform.scale", [1.0, 1.008], 4.8)

    asset("z.png", glyph_z(84))
    zs = []
    head_x, head_y = C - w / 2 + 0.43 * w, top - 0.21 * h          # her head in the card art
    for i in range(3):
        s = 15 + i * 4
        z = Layer(f"Zzz {i + 1}", s, s * 1.15, head_x + 70 + i * 16, head_y + 30 + i * 6, img="z.png")
        z.animate("opacity", [0, 0.85, 0], 4.2, autoreverses=False, timing="linear", key_times=[0, 0.3, 1],
                  offset=i * 1.4)
        rise = group(f"Zzz {i + 1} Rise").add(z)
        rise.animate("position.y", [C, C + 44], 4.2, autoreverses=False, timing="easeOut", offset=i * 1.4)
        zs.append(rise)

    par = group("Siesta Parallax", kind="CATransformLayer").add(breathe, *zs)
    par.parallax = 6
    stage = group("Siesta Stage", y=C - 120, opacity=0.0)
    stage.state("opacity", 0.0, 0.0, 1.0).state("position.y", C - 120, C - 120, C)
    return stage.add(par)


def build_floating():
    root_fl = group("FLOATING")
    root_fl.id = "floating"
    mascot, mascot_centre = build_mascot()
    burst, rain = build_show(mascot_centre)
    siesta = build_siesta()
    shooter, shooter_bits = build_shooter()
    root_fl.add(siesta, mascot, shooter_bits, burst, rain)
    return root_fl, shooter


def build_root():
    root = Layer("Root Layer", S, S, C, C)
    # built in this order so the random layout of everything else stays as it was
    bg = build_background()
    fl, shooter = build_floating()
    # Arisu waits behind the curtain: home has no clock, so she needs no depth layer
    bg.children.insert(next(i for i, l in enumerate(bg.children) if l.name == "Curtain Parallax"), shooter)
    return root.add(bg, fl)


def main():
    root = build_root()
    caml = build_caml(root)
    out, ident, desc_uuid, ca_name = package(caml, os.path.join(OUT, f"{OUT_NAME}.tendies"), BUILD)

    mem = sum(im.width * im.height * 4 for im in ASSETS.values()) / 2 ** 20
    print(f"layers: {sum(1 for _ in walk(root))}, assets: {len(ASSETS)}, decoded ~{mem:.0f} MB")
    print(f"tendies: {out} ({os.path.getsize(out) / 2 ** 20:.1f} MB)")
    print(f"identity: {ident}  descriptor: {desc_uuid}  CA bundle: {ca_name}")
    for key, im in sorted(ASSETS.items()):
        print(f"  {key:28s} {im.width}x{im.height}")
    if "--no-preview" not in sys.argv:
        make_previews(root, PREVIEW, {"lock": "鎖定 可疑的浣熊布偶裝（開演前）", "home": "主畫面 有栖（開幕・じゃーん）",
                                      "sleep": "待機 AOD・散場後的午睡"})
        print(f"previews: {PREVIEW}")


if __name__ == "__main__":
    main()
