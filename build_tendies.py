# -*- coding: utf-8 -*-
"""
Manosaba Duo: Nugget .tendies for the iPhone Duo (foldable), in iOS 27's per-screen schema.

States: Lock = Hiro's cut-in, Home = Ema's cut-in, Sleep / AOD = the two girls standing together.

Nothing loops. An idle wallpaper is a still frame, so the phone does no work while it sits there; one looping
layer measured ~26% backboardd CPU on an idle Home Screen. All the motion lives in the transitions:
  unlock  the camera pans across the courtroom and leans in. Hiro and her blade leave to the left at two
          speeds while her glass shards burst outward, spinning. Ema's blade swings in from the right and her
          shards fly in and settle around her.
  AOD     the courtroom recedes and dims, Hiro sinks back and her shards fall away, and the duo rise into view
          below the clock. Waking, which also happens on unfolding, plays this in reverse and pushes in.
One composition, framed per posture (the Duo per-screen schema). The scene is authored once in points on an
S x S square, and each posture (cover, inner portrait, inner landscape) frames it like a camera: sized so the
girl's head comes a third of the way up into that screen's clock, in front of it, as in the original. The AOD
pair are framed the same way everywhere: half-body, side by side, heads just below the clock, the screen's
bottom edge cropping them. Nothing is rearranged per posture; only the framing changes.
Coordinates are y-up (root geometryFlipped = 0).

iOS 27 depth + gyro is built in (Clownfish CA bundle name + rendering configuration archives);
import the result with AirCard Depth Test, which keeps the dot-prefixed options plist.
"""
import copy
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from tendies_kit import *  # noqa: F401,F403  (scene graph, CAML, packaging, previews, device model)

HERE = os.path.dirname(os.path.abspath(__file__))
# your own extraction of the game's assets (not distributed); override with MANOSABA_ASSETS
ASSET_ROOT = os.environ.get("MANOSABA_ASSETS", r"D:\Wallpaper\NuggetWallpaper\Manosaba\ManosabaAsset")
DUMP = os.path.join(ASSET_ROOT, "assets_manosaba_WitchTrials", "Unity_Dump_Texture2D")
BG_DIR = os.path.join(ASSET_ROOT, "assets_manosaba_WitchTrials", "Textures", "Naninovel",
                      "Backgrounds", "MainBackground", "RGB")
SPRITES = os.path.join(ASSET_ROOT, "角色")

OUT_NAME = "Manosaba-Duo-Fold"
OUT = os.path.join(HERE, "out")                  # every generated file: .tendies, build/, preview/
BUILD = os.path.join(OUT, "build", "manosaba")
PREVIEW = os.path.join(OUT, "preview", "manosaba")

OFF = 520.0        # slide distance of the character leaving / entering the stage
RUSH = 260.0       # the blades travel this much further than their character: two speeds read as depth
CHAR_TOP = 556.0   # top of the cut-in art (her head) on the scene square
# cut-in art is cropped at the legs: sink it below the bottom edge so gyro never reveals it
CHAR_SINK = 26.0
DUO_H = 600.0      # the AOD pair's nominal full height (pt); each posture scales it (POSTURES)
DUO_KEEP = 0.72    # only the top of each figure ever shows (half-body), so the rest is cropped away
DUO_RISE = 170.0   # how far (pt, before scaling) the pair rise into view on the AOD

# Where each posture puts things, in device pixels from the screen centre, y up (the user's tall clock reaches
# down to about y -24 on the cover, +371 on the inner display and -57 in landscape; see DUO_VIEWS):
#   F         px per scene pt: how large this screen shows the scene
#   head      the top of Hiro's / Ema's head, a third of the way up into the clock (she is in front of it)
#   duo_head  the AOD pair's head top, just below the clock (the AOD has no depth effect)
#   duo_h     the pair's full height; the bottom edge crops them about the hips, so they read as half-body
POSTURES = {
    "cover": dict(F=2.5, head=280, duo_head=-84, duo_h=1700),
    "inner_portrait": dict(F=3.6, head=580, duo_head=80, duo_h=2450),
    "inner_landscape": dict(F=2.4, head=226, duo_head=-140, duo_h=1750),
}
LAND_PAN = 100.0   # landscape is wide: a shorter pan keeps the courtroom image covering the whole screen

rng = random.Random(20261027)
mote_rng = random.Random(2026110801)  # its own stream, so the scene's rng sequence stays as it was

# ----------------------------------------------------------------------------
# assets + layout
# ----------------------------------------------------------------------------
HIRO_RGB = (255, 46, 84)
EMA_RGB = (255, 120, 214)


def tinted_dot(rgb):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    r = np.hypot(xx - 31.5, yy - 31.5) / 32
    dot = np.zeros((64, 64, 4), np.uint8)
    dot[..., :3] = rgb
    dot[..., 3] = np.clip(np.exp(-(r / 0.42) ** 2) * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(dot, "RGBA")


def motes(name, count, size, alpha, keys, parallax):
    """Still motes of light scattered wider than the square, since landscape shows more of it (they replace
    the old particle emitters)."""
    g = group(name, kind="CATransformLayer")
    g.parallax = parallax
    for i in range(count):
        d = mote_rng.uniform(*size)
        g.add(Layer(f"{name} {i + 1}", d, d, mote_rng.uniform(-250, S + 250), mote_rng.uniform(-150, S + 150),
                    img=mote_rng.choice(keys), opacity=mote_rng.uniform(*alpha)))
    return g


def build_background():
    bg = load(os.path.join(BG_DIR, "Background_013_001.png")).convert("RGB")
    # keep the native 2048 px height; crop the unused far left/right to save memory
    cw = 3100
    bg = bg.crop(((bg.width - cw) // 2, 0, (bg.width + cw) // 2, bg.height))
    bg = ImageEnhance.Brightness(bg).enhance(0.74)
    bg = ImageEnhance.Contrast(bg).enhance(1.08)
    bg = bg.filter(ImageFilter.GaussianBlur(1.3))           # gentle depth of field
    asset("bg_court.png", bg)

    # god rays from the stained glass windows
    W = H = 1024
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    palette = [(255, 214, 170), (160, 190, 255), (255, 150, 190), (255, 236, 196), (200, 160, 255)]
    for i in range(11):
        ang = math.radians(-30 + 60 * i / 10 + rng.uniform(-3, 3))
        half = math.radians(rng.uniform(1.4, 3.6))
        ox, oy, L = W / 2, -260, 1700
        pts = [(ox, oy),
               (ox + L * math.sin(ang - half), oy + L * math.cos(ang - half)),
               (ox + L * math.sin(ang + half), oy + L * math.cos(ang + half))]
        beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(beam).polygon(pts, fill=palette[i % len(palette)] + (rng.randint(60, 105),))
        rays = Image.alpha_composite(rays, beam.filter(ImageFilter.GaussianBlur(14)))
    arr = np.asarray(rays).astype(np.float32)
    fall = np.clip(1.0 - np.linspace(0, 1, H) / 0.9, 0, 1) ** 1.6
    side = np.clip(np.minimum(np.arange(W), W - 1 - np.arange(W)) / (W * 0.16), 0, 1) ** 1.5
    arr[..., 3] *= fall[:, None] * side[None, :]       # soft sides: landscape sees past the image's edges
    arr[..., 3] += np.random.default_rng(1).uniform(-1.5, 1.5, arr.shape[:2])   # dither vs banding
    asset("god_rays.png", Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA"))

    # radial vignette; each posture gets its own, shaped to its screen (for_screen)
    yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32)
    r = np.hypot(xx - 511.5, yy - 511.5) / 512
    va = np.clip((r - 0.42) / 0.55, 0, 1) ** 1.4 * 235
    va += np.random.default_rng(2).uniform(-1.5, 1.5, va.shape)
    vig = np.zeros((1024, 1024, 4), np.uint8)
    vig[..., 3] = np.clip(va, 0, 255).astype(np.uint8)
    asset("vignette.png", Image.fromarray(vig, "RGBA"))

    asset("mote_warm.png", tinted_dot((255, 219, 189)))
    asset("mote_cold.png", tinted_dot((191, 209, 255)))
    asset("mote_pink.png", tinted_dot((255, 204, 230)))

    root_bg = group("BACKGROUND")
    root_bg.id = "background"
    base = group("BG Base", w=2800, h=2800, color=(0.035, 0.02, 0.045))

    court = image_layer("BG Court", "bg_court.png", h=950.0, trilinear=True)
    parallax = group("BG Parallax", kind="CATransformLayer")
    parallax.parallax = 14
    pan = group("BG Pan").state("position.x", C + 140, C - 140, C)
    # unlocking leans in toward Ema; the AOD lets the courtroom recede, so waking pushes back in
    lean = group("BG Lean").state("transform.scale.xy", 1.0, 1.06, 0.95)
    lean.add(pan.add(parallax.add(court)))

    tint_hiro = group("Tint Hiro", w=2800, h=2800, color=(0.55, 0.02, 0.10), opacity=0.24) \
        .state("opacity", 0.24, 0.0, 0.10)
    tint_ema = group("Tint Ema", w=2800, h=2800, color=(0.42, 0.14, 0.55), opacity=0.0) \
        .state("opacity", 0.0, 0.24, 0.10)

    rays = image_layer("God Rays", "god_rays.png", w=1000, x=C, y=S + 60, anchor=(0.5, 1.0),
                       rot=math.radians(-1.5))
    rays.state("transform.rotation.z", math.radians(-1.5), math.radians(2.0), 0.0)
    rays_fade = group("God Rays Fade", opacity=0.75).state("opacity", 0.75, 0.62, 0.3).add(rays)

    dust = group("Dust Drift", opacity=0.85).state("position.x", C, C - 70, C) \
        .state("position.y", C, C + 30, C - 20).state("opacity", 0.85, 0.7, 0.35)
    dust.add(motes("Dust", 26, (6, 22), (0.25, 0.7), ["mote_warm.png", "mote_cold.png"], 18))

    sleep_dim = group("Sleep Dim", w=2800, h=2800, color=(0.0, 0.0, 0.0), opacity=0.0) \
        .state("opacity", 0.0, 0.0, 0.42)

    root_bg.add(base, lean, tint_hiro, tint_ema, rays_fade, dust, sleep_dim)
    return root_bg


def build_cutin(who, char_file, blade_file, overlays, frag_file, rgb, positions, leaving):
    """One character's cut-in set: blade + glow + sparkles, aura, character, glass shards.
    leaving: on stage at Lock and gone at Home (Hiro); otherwise she arrives at Home (Ema).
    Every motion is a state value, interpolated by the unlock swipe or the AOD transition."""
    P = who

    def go(rest, away, sleep=None):
        """(lock, home, sleep) for a value that is `rest` while she is on stage."""
        return (rest, away, rest if sleep is None else sleep) if leaving else (away, rest, away)

    # --- character ---------------------------------------------------------
    char, _ = trim(load(os.path.join(DUMP, char_file)).convert("RGBA"))
    k_char = asset(f"{P.lower()}_cutin.png", char)
    ch_h = CHAR_TOP + CHAR_SINK
    ppx = ch_h / char.height                          # pt per source px (2048 px -> 3.53 px/pt)
    ch_w = char.width * ppx
    cx, cy = C, CHAR_TOP - ch_h / 2                   # head just under the default clock

    aura_img, aura_pad = alpha_glow(char.getchannel("A"), rgb, scale=0.25, dilate=5, blur=8, pad=40,
                                    strength=0.95)
    k_aura = asset(f"{P.lower()}_aura.png", aura_img)
    aura = Layer(f"{P} Aura", (char.width + 2 * aura_pad) * ppx, (char.height + 2 * aura_pad) * ppx, cx, cy,
                 img=k_aura, opacity=0.55)
    body = Layer(f"{P} Body", ch_w, ch_h, cx, cy, img=k_char, trilinear=True)
    char_par = group(f"{P} Char Parallax", kind="CATransformLayer").add(aura, body)
    char_par.parallax = 10

    # --- stained glass blade: swings as it travels, faster than she does ----
    blade_src = load(os.path.join(DUMP, blade_file)).convert("RGBA")
    blade, (bx0, by0) = trim(blade_src, pad=6)
    k_blade = asset(f"{P.lower()}_blade.png", blade)
    bw = blade.width / PPT                            # exactly @3x (~649 pt)
    bppx = bw / blade.width
    bh = blade.height * bppx
    swing = Layer(f"{P} Blade Swing", bw, bh, C + 6, 370)
    swing.state("transform.rotation.z", *go(0.0, math.radians(18 if leaving else -18), math.radians(-10)))
    swing.rot = swing.states["transform.rotation.z"][0]

    def local(ox, oy, ow, oh):                        # blade-pixel rect (top-left origin) -> local centre
        return (ox - bx0 + ow / 2) * bppx, bh - (oy - by0 + oh / 2) * bppx

    glow_img, gpad = alpha_glow(blade.getchannel("A"), rgb, scale=0.25, dilate=6, blur=8, pad=36, strength=1.1)
    k_glow = asset(f"{P.lower()}_blade_glow.png", glow_img)
    glow = Layer(f"{P} Blade Glow", (blade.width + 2 * gpad) * bppx, (blade.height + 2 * gpad) * bppx,
                 bw / 2, bh / 2, img=k_glow, opacity=0.6)
    swing.add(glow, Layer(f"{P} Blade", bw, bh, bw / 2, bh / 2, img=k_blade, trilinear=True))

    for i, (fname, dy, is_lum) in enumerate(overlays):
        src = load(os.path.join(DUMP, fname))
        sp = lum_to_alpha(src, (255, 240, 246)) if is_lum else src.convert("RGBA")
        sp, (sx0, sy0) = trim(sp, thr=8, pad=2)
        k_sp = asset(f"{P.lower()}_sparkle{i + 1}.png", sp)
        lx, ly = local(sx0, sy0 - dy, sp.width, sp.height)
        swing.add(Layer(f"{P} Sparkle {i + 1}", sp.width * bppx, sp.height * bppx, lx, ly, img=k_sp,
                        opacity=(0.9, 0.55)[i % 2]))
    blade_par = group(f"{P} Blade Parallax", kind="CATransformLayer").add(swing)
    blade_par.parallax = 24
    rush = group(f"{P} Blade Rush").state("position.x", *go(C, C - RUSH if leaving else C + RUSH))
    rush.x = rush.states["position.x"][0]
    rush.add(blade_par)

    # --- glass shards: burst outward as she leaves, fly in and settle as she arrives, fall on the AOD ----
    shards = extract_shards(load(os.path.join(DUMP, frag_file)).convert("RGBA"), len(positions))
    back = group(f"{P} Shards Back", kind="CATransformLayer")
    back.parallax = 30
    front = group(f"{P} Shards Front", kind="CATransformLayer")
    front.parallax = 46
    for i, (shard, (sx, sy, f, layer_front)) in enumerate(zip(shards, positions)):
        k = asset(f"{P.lower()}_shard{i + 1:02d}.png", shard)
        w, h = shard.width / PPT * f, shard.height / PPT * f
        r0 = math.radians(rng.uniform(-30, 30))
        lo = rng.uniform(0.5, 0.7)
        rng.uniform(1.6, 3.2), rng.uniform(0, 3)      # keep the scene's rng sequence (was a flicker loop)
        turn = 4 * math.radians(rng.uniform(12, 34) * rng.choice([-1, 1]))
        rng.uniform(4.5, 9), rng.uniform(0, 4)        # (was a spin loop)
        a1 = rng.uniform(0, 2 * math.pi)
        rng.uniform(0, 2 * math.pi), rng.uniform(10, 24)
        m2 = rng.uniform(14, 30)
        rng.uniform(6, 11), rng.uniform(0, 6)         # (was a drift loop)
        img = Layer(f"{P} Shard {i + 1}", w, h, w / 2, h / 2, img=k, opacity=(lo + 1) / 2)
        spin = Layer(f"{P} Shard {i + 1} Spin", w, h, sx, sy).add(img)
        spin.state("transform.rotation.z", *go(r0, r0 + turn, r0 - turn / 2))
        spin.rot = spin.states["transform.rotation.z"][0]
        ang = math.atan2(sy - 330, sx - C) + (a1 - math.pi) * 0.15
        dist = 240 + m2 * 6
        bx, by = dist * math.cos(ang), dist * math.sin(ang)
        fly = group(f"{P} Shard {i + 1} Fly")
        fly.state("position.x", *go(C, C + bx, C + bx * 0.25)).state("position.y", *go(C, C + by, C - 240))
        fly.x, fly.y = fly.states["position.x"][0], fly.states["position.y"][0]
        (front if layer_front else back).add(fly.add(spin))

    # the whole set scales from the bottom edge: sinking back on the AOD, pushing in on waking
    zoom = Layer(f"{P} Zoom", S, S, C, 0, anchor=(0.5, 0.0))
    zoom.state("transform.scale.xy", *go(1.0, 0.94 if leaving else 1.08, 0.86))
    zoom.scale = zoom.states["transform.scale.xy"][0]
    return zoom.add(rush, back, char_par, front)


def shard_slots(n, cx=C, cy=330.0):
    """Shard positions on a loose ellipse around the character, clear of the face and the clock."""
    slots = []
    for i in range(n):
        ang = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / n + 0.35
        deg = math.degrees(ang) % 360
        if 62 < deg < 118:                            # straight above the head -> push sideways
            ang += math.radians(60 if deg >= 90 else -60)
        rx, ry = rng.uniform(255, 420), rng.uniform(170, 250)
        slots.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang), rng.uniform(0.62, 1.0), i % 2 == 0))
    return slots


def build_floating():
    root_fl = group("FLOATING")
    root_fl.id = "floating"

    hiro = build_cutin("Hiro", "Hiro_CutIn_003.png", "Hiro_CutIn_StainedGlass_003.png",
                       [("Hiro_CutIn_StainedGlass_003_kirakira1.png", 0, True),
                        ("Hiro_CutIn_StainedGlass_003_kirakira2.png", 0, True)],
                       "Hiro_GlassFragment_003.png", HIRO_RGB, shard_slots(12), leaving=True)
    ema = build_cutin("Ema", "RefuteCutIn_Ema_003.png", "RefuteCutIn_StainedGlass_003.png",
                      [("RefuteCutIn_StainedGlass_003_kirakira_0.png", 52, False),
                       ("RefuteCutIn_StainedGlass_003_kirakira2_0.png", 81, False)],
                      "GlassFragment_003.png", EMA_RGB, shard_slots(12), leaving=False)
    # unlock = slide + cross-fade, so the two girls pass each other mid-swipe; Hiro fades as (1-u)^2 (one more
    # opacity level), so she is mostly gone by the time Ema or the AOD pair are half in
    hiro_stage = group("Hiro Stage").state("position.x", C, C - OFF, C).state("opacity", 1.0, 0.0, 0.0)
    hiro_stage.add(chained("Hiro", (1.0, 0.0, 0.0), 1, hiro))
    ema_stage = group("Ema Stage", x=C + OFF, opacity=0.0).state("position.x", C + OFF, C, C + OFF) \
        .state("opacity", 0.0, 1.0, 0.0)
    ema_stage.add(ema)

    # --- sleep / AOD: the pair, half-body side by side, rising into view just below the clock ----
    # They stand on y = 0 with their heads at DUO_H; only the top DUO_KEEP of each figure is kept, since the
    # screen's bottom edge crops them there or higher in every posture. The Duo Zoom (anchored at their feet)
    # sizes and places the pair per posture (for_screen).
    duo_par = group("Duo Parallax", kind="CATransformLayer")
    duo_par.parallax = 10
    most = max(q["duo_h"] for q in POSTURES.values())       # the most pixels any posture shows of a figure
    figures = []
    for who, folder, rgb in (("Hiro", "二阶堂 希罗", HIRO_RGB), ("Ema", "樱羽 艾玛", EMA_RGB)):
        full, _ = trim(load(os.path.join(SPRITES, folder, "正常立绘", "原图", "1.png")).convert("RGBA"))
        full = resize_premul(full, (full.width * most / full.height, most))
        figures.append((who, rgb, full.crop((0, 0, full.width, round(full.height * DUO_KEEP)))))
    h = DUO_H * DUO_KEEP
    widths = [h * im.width / im.height for _, _, im in figures]
    apart = 0.82 * sum(widths) / 2                          # centre to centre: shoulder to shoulder
    for (who, rgb, im), x in zip(figures, (C - apart / 2, C + apart / 2)):
        k = asset(f"duo_{who.lower()}.png", im)
        glow_img, gpad = alpha_glow(im.getchannel("A"), rgb, scale=0.1, dilate=4, blur=8, pad=34, strength=0.8)
        kg = asset(f"duo_{who.lower()}_glow.png", glow_img)
        gpt = h / im.height
        duo_par.add(Layer(f"Duo {who} Glow", (im.width + 2 * gpad) * gpt, (im.height + 2 * gpad) * gpt,
                          x, DUO_H - h / 2, img=kg, opacity=0.45),
                    Layer(f"Duo {who}", h * im.width / im.height, h, x, DUO_H - h / 2, img=k, trilinear=True))
    duo_stage = group("Duo Stage", y=C - DUO_RISE, opacity=0.0).state("opacity", 0.0, 0.0, 1.0) \
        .state("position.y", C - DUO_RISE, C - DUO_RISE, C)
    duo_stage.add(duo_par)
    duo_zoom = Layer("Duo Zoom", S, S, C, 0, anchor=(0.5, 0.0)).add(duo_stage)

    glints = group("Glints Drift", opacity=0.75).state("position.x", C, C - 110, C) \
        .state("opacity", 0.75, 0.7, 0.0)
    glints.add(motes("Glint", 8, (14, 34), (0.3, 0.75), ["mote_pink.png", "mote_warm.png"], 40))

    root_fl.add(hiro_stage, ema_stage, duo_zoom, glints)
    return root_fl


def framing(posture):
    """One posture's numbers. The frame maps a scene point to device px around the screen centre as
    (F * (x - C), dy + F * (y - C)); the Duo Zoom, anchored at the pair's feet, then sizes and lifts them."""
    q = POSTURES[posture]
    F = q["F"]
    dy = q["head"] - F * (CHAR_TOP - C)
    z = q["duo_h"] / (F * DUO_H)
    feet = (q["duo_head"] - dy) / F + C - z * DUO_H
    w, h = DUO_VIEWS[posture][2]
    # the vignette: an ellipse around this screen, about as strong at its edges as the original's
    return dict(F=F, dy=dy, z=z, feet=feet, vignette=(1.6 * w / F, 1.42 * h / F, C - dy / F))


def find(tree, name):
    return next(l for l, _ in walk(tree) if l.name == name)


def for_screen(scene, scr):
    """One screen's BACKGROUND / FLOATING pair: a renamed copy of the scene in a frame, with every
    posture-dependent value set. The inner display carries its landscape framing as landscape values."""
    key = DUO_SCREENS[scr]["key"]
    views = [p for p, v in DUO_VIEWS.items() if v[0] == scr]
    port = framing(next(p for p in views if not DUO_VIEWS[p][1]))
    land = next((framing(p) for p in views if DUO_VIEWS[p][1]), None)

    def put(layer, key_path, portrait, landscape):     # constant within each orientation
        layer.state(key_path, portrait, portrait, portrait)
        if land:
            layer.land(key_path, landscape, landscape, landscape)

    pair = []
    for part in scene:
        frame = Layer(f"{part.name} Frame", S, S, DUO_C, DUO_C + port["dy"], scale=port["F"])
        put(frame, "transform.scale.xy", port["F"], land and land["F"])
        put(frame, "position.y", DUO_C + port["dy"], land and DUO_C + land["dy"])
        kids = copy.deepcopy(part.children)
        if part.name == "BACKGROUND":
            at = [k.name for k in kids].index("Sleep Dim")
            for tag, fr, show in (("Portrait", port, (1.0, 0.0)), ("Landscape", land, (0.0, 1.0))):
                if fr:
                    vw, vh, vy = fr["vignette"]
                    v = Layer(f"Vignette {tag}" if land else "Vignette", vw, vh, C, vy, img="vignette.png",
                              opacity=show[0])
                    if land:
                        put(v, "opacity", *show)
                    kids.insert(at, v)
                    at += 1
        frame.add(*kids)
        for l, _ in walk(frame):
            l.name, l.id = f"{l.name} {key}", f"{l.id}-{key.lower()}"
        pair.append(duo_tree(f"{part.name} {key}").add(frame))
    bg, fl = pair
    duo = find(fl, f"Duo Zoom {key}")
    duo.scale, duo.y = port["z"], port["feet"]
    put(duo, "transform.scale.xy", port["z"], land and land["z"])
    put(duo, "position.y", port["feet"], land and land["feet"])
    if land:
        find(bg, f"BG Pan {key}").land("position.x", C + LAND_PAN, C - LAND_PAN, C)
    return bg, fl


def build_screens():
    scene = (build_background(), build_floating())
    return {"inner": for_screen(scene, "inner"), "cover": for_screen(scene, "cover")}


def main():
    screens = build_screens()
    caml = duo_caml(screens)
    out, ident, desc_uuid, ca_name = package(caml, os.path.join(OUT, f"{OUT_NAME}.tendies"), BUILD)

    mem = sum(im.width * im.height * 4 for im in ASSETS.values()) / 2 ** 20
    layers = sum(1 for pair in screens.values() for t in pair for _ in walk(t))
    print(f"layers: {layers}, assets: {len(ASSETS)}, decoded ~{mem:.0f} MB, looping animations: 0")
    print(f"tendies: {out} ({os.path.getsize(out) / 2 ** 20:.1f} MB)")
    print(f"identity: {ident}  descriptor: {desc_uuid}  CA bundle: {ca_name}")
    if "--no-preview" not in sys.argv:
        make_duo_previews(screens, PREVIEW, {"lock": "鎖定 Hiro", "home": "主畫面 Ema", "sleep": "待機 AOD・Duo"})
        print(f"previews: {PREVIEW}")


if __name__ == "__main__":
    main()
