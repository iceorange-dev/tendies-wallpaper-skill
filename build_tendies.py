# -*- coding: utf-8 -*-
"""
Manosaba Duo — Nugget .tendies (ParameterizedCA / gyro) for iPhone Duo (foldable).

Layout strategy
---------------
PosterBoard scales the CA root layer to fill the screen, so the root is a square
(S x S pt) and everything important sits in the centre:
  * folded (outer, portrait 466x678)        -> central ~612 pt wide strip
  * unfolded portrait (inner 626x890)        -> central ~626 pt wide strip
  * unfolded landscape (inner 890x626)       -> central ~626 pt tall band
The safe zone visible in every posture is roughly x 139..751, y 132..758.

States (wallpaperPropertyGroups):  Lock = Hiro cut-in, Home = Ema cut-in,
Sleep / AOD = both girls standing together ("Duo").
Coordinates are y-up (root geometryFlipped = 0), same as CAPlayground.

iOS 27 depth + gyro is built in (Clownfish CA bundle name + rendering configuration archives);
import the result with AirCard Depth Test, which keeps the dot-prefixed options plist.
"""
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
BUILD = os.path.join(HERE, "build")
PREVIEW = os.path.join(HERE, "preview")

OFF = 520.0        # slide distance of the character leaving / entering the stage
# The Lock Screen clock fills the top ~37% in every posture (folded: y > ~565 in root pt;
# landscape: y > ~517 but only x 340..550). Characters stand on the bottom edge and stay under it.
CHAR_TOP = 556.0
# cut-in art is cropped at the legs: sink it below the bottom edge so gyro (+10) and bob (+8) never reveal it
CHAR_SINK = 26.0
# AOD has no depth effect, so the clock is drawn over the duo. The user's clock ends lowest when folded
# (root y ~434, see CLOCK); keep the heads clear of it including breathing (+5) and gyro (+10).
DUO_BOTTOM, DUO_TOP = 4.0, 415.0

rng = random.Random(20261027)

# ----------------------------------------------------------------------------
# assets + layout
# ----------------------------------------------------------------------------
HIRO_RGB = (255, 46, 84)
EMA_RGB = (255, 120, 214)


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
    arr[..., 3] *= fall[:, None]
    arr[..., 3] += np.random.default_rng(1).uniform(-1.5, 1.5, arr.shape[:2])   # dither vs banding
    asset("god_rays.png", Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA"))

    # radial vignette (circular, so it behaves the same in every posture)
    yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32)
    r = np.hypot(xx - 511.5, yy - 511.5) / 512
    va = np.clip((r - 0.42) / 0.55, 0, 1) ** 1.4 * 235
    va += np.random.default_rng(2).uniform(-1.5, 1.5, va.shape)
    vig = np.zeros((1024, 1024, 4), np.uint8)
    vig[..., 3] = np.clip(va, 0, 255).astype(np.uint8)
    asset("vignette.png", Image.fromarray(vig, "RGBA"))

    # particle sprite
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    r = np.hypot(xx - 31.5, yy - 31.5) / 32
    dot = np.zeros((64, 64, 4), np.uint8)
    dot[..., :3] = 255
    dot[..., 3] = np.clip(np.exp(-(r / 0.42) ** 2) * 255, 0, 255).astype(np.uint8)
    asset("mote.png", Image.fromarray(dot, "RGBA"))

    root_bg = group("BACKGROUND")
    root_bg.id = "background"
    base = group("BG Base", w=2800, h=2800, color=(0.035, 0.02, 0.045))

    court_h = 950.0
    court = image_layer("BG Court", "bg_court.png", h=court_h, trilinear=True)
    court.animate("transform.scale", [1.0, 1.045], 23.0)                       # slow Ken Burns
    parallax = group("BG Parallax", kind="CATransformLayer")
    parallax.parallax = 14
    pan = group("BG Pan").state("position.x", C + 140, C - 140, C)
    pan.add(parallax.add(court))

    tint_hiro = group("Tint Hiro", w=2800, h=2800, color=(0.55, 0.02, 0.10), opacity=0.24) \
        .state("opacity", 0.24, 0.0, 0.10)
    tint_ema = group("Tint Ema", w=2800, h=2800, color=(0.42, 0.14, 0.55), opacity=0.0) \
        .state("opacity", 0.0, 0.24, 0.10)

    rays = image_layer("God Rays", "god_rays.png", w=1000, x=C, y=S + 60, anchor=(0.5, 1.0))
    rays.animate("transform.rotation.z", [math.radians(-2.4), math.radians(2.4)], 14.0)
    rays_fade = group("God Rays Pulse").add(rays)
    rays_fade.animate("opacity", [0.45, 0.9], 7.0)

    dust = Layer("Dust Back", S, S, C, C, kind="CAEmitterLayer")
    dust.emitter = dict(size=(1150, 1150), mode="surface", render="additive", cells=[
        dict(name="Mote Warm", birthRate=7, lifetime=16, lifetimeRange=6, velocity=9, velocityRange=7,
             scale=0.16, scaleRange=0.1, alphaSpeed=-0.05, spinRange=0.4, color=(1.0, 0.86, 0.74), alpha=0.75),
        dict(name="Mote Cold", birthRate=3, lifetime=14, lifetimeRange=5, velocity=7, velocityRange=6,
             scale=0.12, scaleRange=0.08, alphaSpeed=-0.06, spinRange=0.4, color=(0.75, 0.82, 1.0), alpha=0.7),
    ])

    vignette = image_layer("Vignette", "vignette.png", w=1260)
    sleep_dim = group("Sleep Dim", w=2800, h=2800, color=(0.0, 0.0, 0.0), opacity=0.0) \
        .state("opacity", 0.0, 0.0, 0.42)

    root_bg.add(base, pan, tint_hiro, tint_ema, rays_fade, dust, vignette, sleep_dim)
    return root_bg


def build_cutin(who, char_file, blade_file, overlays, frag_file, rgb, positions):
    """One character's cut-in set: blade + glow + sparkles, aura, character, glass shards."""
    P = who
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
                 img=k_aura)
    aura.animate("opacity", [0.3, 0.75], 2.8)

    body = Layer(f"{P} Body", ch_w, ch_h, cx, cy, img=k_char, trilinear=True)
    bob = group(f"{P} Bob").add(aura, body)
    bob.animate("position.y", [C, C + 8], 4.6)
    char_par = group(f"{P} Char Parallax", kind="CATransformLayer").add(bob)
    char_par.parallax = 10

    # --- stained glass blade ------------------------------------------------
    blade_src = load(os.path.join(DUMP, blade_file)).convert("RGBA")
    blade, (bx0, by0) = trim(blade_src, pad=6)
    k_blade = asset(f"{P.lower()}_blade.png", blade)
    bw = blade.width / PPT                            # exactly @3x (~649 pt)
    bppx = bw / blade.width
    bh = blade.height * bppx
    sway = Layer(f"{P} Blade Sway", bw, bh, C + 6, 370)
    sway.animate("transform.rotation.z", [math.radians(-1.1), math.radians(1.3)], 8.5)

    def local(ox, oy, ow, oh):                        # blade-pixel rect (top-left origin) -> local centre
        return (ox - bx0 + ow / 2) * bppx, bh - (oy - by0 + oh / 2) * bppx

    glow_img, gpad = alpha_glow(blade.getchannel("A"), rgb, scale=0.25, dilate=6, blur=8, pad=36, strength=1.1)
    k_glow = asset(f"{P.lower()}_blade_glow.png", glow_img)
    glow = Layer(f"{P} Blade Glow", (blade.width + 2 * gpad) * bppx, (blade.height + 2 * gpad) * bppx,
                 bw / 2, bh / 2, img=k_glow)
    glow.animate("opacity", [0.3, 0.85], 3.4)
    sway.add(glow, Layer(f"{P} Blade", bw, bh, bw / 2, bh / 2, img=k_blade, trilinear=True))

    flicker = [([0.0, 1.0, 0.15, 0.85, 0.0], 3.1), ([0.85, 0.1, 1.0, 0.2, 0.85], 2.3)]
    for i, (fname, dy, is_lum) in enumerate(overlays):
        src = load(os.path.join(DUMP, fname))
        sp = lum_to_alpha(src, (255, 240, 246)) if is_lum else src.convert("RGBA")
        sp, (sx0, sy0) = trim(sp, thr=8, pad=2)
        k_sp = asset(f"{P.lower()}_sparkle{i + 1}.png", sp)
        lx, ly = local(sx0, sy0 - dy, sp.width, sp.height)
        lay = Layer(f"{P} Sparkle {i + 1}", sp.width * bppx, sp.height * bppx, lx, ly, img=k_sp)
        vals, dur = flicker[i % 2]
        lay.animate("opacity", vals, dur, autoreverses=False, timing="linear",
                    key_times=[0, 0.25, 0.5, 0.75, 1.0])
        sway.add(lay)
    blade_par = group(f"{P} Blade Parallax", kind="CATransformLayer").add(sway)
    blade_par.parallax = 24

    # --- glass shards -------------------------------------------------------
    shards = extract_shards(load(os.path.join(DUMP, frag_file)).convert("RGBA"), len(positions))
    back = group(f"{P} Shards Back", kind="CATransformLayer")
    back.parallax = 30
    front = group(f"{P} Shards Front", kind="CATransformLayer")
    front.parallax = 46
    for i, (shard, (sx, sy, f, layer_front)) in enumerate(zip(shards, positions)):
        k = asset(f"{P.lower()}_shard{i + 1:02d}.png", shard)
        w, h = shard.width / PPT * f, shard.height / PPT * f
        r0 = rng.uniform(-30, 30)
        img = Layer(f"{P} Shard {i + 1}", w, h, w / 2, h / 2, img=k)
        img.animate("opacity", [rng.uniform(0.5, 0.7), 1.0], rng.uniform(1.6, 3.2), offset=rng.uniform(0, 3))
        spin = Layer(f"{P} Shard {i + 1} Spin", w, h, sx, sy, rot=math.radians(r0)).add(img)
        d = rng.uniform(12, 34) * rng.choice([-1, 1])
        spin.animate("transform.rotation.z", [math.radians(r0), math.radians(r0 + d)], rng.uniform(4.5, 9),
                     offset=rng.uniform(0, 4))
        drift = group(f"{P} Shard {i + 1} Drift").add(spin)
        a1, a2 = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
        m1, m2 = rng.uniform(10, 24), rng.uniform(14, 30)
        drift.animate("position", [(C, C), (C + m1 * math.cos(a1), C + m1 * math.sin(a1)),
                                   (C + m2 * math.cos(a2), C + m2 * math.sin(a2))],
                      rng.uniform(6, 11), offset=rng.uniform(0, 6))
        (front if layer_front else back).add(drift)

    return blade_par, back, char_par, front


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
                       "Hiro_GlassFragment_003.png", HIRO_RGB, shard_slots(12))
    ema = build_cutin("Ema", "RefuteCutIn_Ema_003.png", "RefuteCutIn_StainedGlass_003.png",
                      [("RefuteCutIn_StainedGlass_003_kirakira_0.png", 52, False),
                       ("RefuteCutIn_StainedGlass_003_kirakira2_0.png", 81, False)],
                      "GlassFragment_003.png", EMA_RGB, shard_slots(12))
    # unlock = slide + cross-fade, so the two girls pass each other mid-swipe
    hiro_stage = group("Hiro Stage").state("position.x", C, C - OFF, C).state("opacity", 1.0, 0.0, 0.0)
    hiro_stage.add(*hiro)
    ema_stage = group("Ema Stage", x=C + OFF, opacity=0.0).state("position.x", C + OFF, C, C + OFF) \
        .state("opacity", 0.0, 1.0, 0.0)
    ema_stage.add(*ema)

    # --- sleep / AOD: the duo standing together -----------------------------
    duo_h = DUO_TOP - DUO_BOTTOM
    duo_y = DUO_BOTTOM + duo_h / 2
    duo_par = group("Duo Parallax", kind="CATransformLayer")
    duo_par.parallax = 10
    for who, folder, fname, x, rgb, dur in (("Hiro", "二阶堂 希罗", "1.png", C - 90, HIRO_RGB, 5.2),
                                            ("Ema", "樱羽 艾玛", "1.png", C + 92, EMA_RGB, 5.9)):
        sprite, _ = trim(load(os.path.join(SPRITES, folder, "正常立绘", "原图", fname)).convert("RGBA"))
        sprite = resize_premul(sprite, (sprite.width * duo_h * PPT / sprite.height, duo_h * PPT))
        k = asset(f"duo_{who.lower()}.png", sprite)
        w = duo_h * sprite.width / sprite.height
        glow_img, gpad = alpha_glow(sprite.getchannel("A"), rgb, scale=0.2, dilate=4, blur=8, pad=34,
                                    strength=0.8)
        kg = asset(f"duo_{who.lower()}_glow.png", glow_img)
        gpt = duo_h / sprite.height
        glow = Layer(f"Duo {who} Glow", (sprite.width + 2 * gpad) * gpt, (sprite.height + 2 * gpad) * gpt,
                     x, duo_y, img=kg, opacity=0.45)
        body = Layer(f"Duo {who}", w, duo_h, x, duo_y, img=k, trilinear=True)
        breathe = group(f"Duo {who} Breathe").add(glow, body)
        breathe.animate("position.y", [C, C + 5], dur, offset=1.3 if who == "Ema" else 0.0)
        duo_par.add(breathe)
    duo_stage = group("Duo Stage", y=C - 140, opacity=0.0).state("opacity", 0.0, 0.0, 1.0) \
        .state("position.y", C - 140, C - 140, C)
    duo_stage.add(duo_par)

    front_dust = Layer("Dust Front", S, S, C, C, kind="CAEmitterLayer")
    front_dust.emitter = dict(size=(1150, 1150), mode="surface", render="additive", cells=[
        dict(name="Glint", birthRate=1.6, lifetime=12, lifetimeRange=4, velocity=14, velocityRange=8,
             scale=0.32, scaleRange=0.18, alphaSpeed=-0.07, spinRange=0.6, color=(1.0, 0.8, 0.9), alpha=0.55),
    ])

    root_fl.add(hiro_stage, ema_stage, duo_stage, front_dust)
    return root_fl


def build_root():
    return Layer("Root Layer", S, S, C, C).add(build_background(), build_floating())


def main():
    root = build_root()
    caml = build_caml(root)
    out, ident, desc_uuid, ca_name = package(caml, os.path.join(HERE, f"{OUT_NAME}.tendies"), BUILD)

    mem = sum(im.width * im.height * 4 for im in ASSETS.values()) / 2 ** 20
    print(f"layers: {sum(1 for _ in walk(root))}, assets: {len(ASSETS)}, decoded ~{mem:.0f} MB")
    print(f"tendies: {out} ({os.path.getsize(out) / 2 ** 20:.1f} MB)")
    print(f"identity: {ident}  descriptor: {desc_uuid}  CA bundle: {ca_name}")
    for key, im in sorted(ASSETS.items()):
        print(f"  {key:28s} {im.width}x{im.height}")
    if "--no-preview" not in sys.argv:
        make_previews(root, PREVIEW, {"lock": "鎖定 Hiro", "home": "主畫面 Ema", "sleep": "待機 AOD・Duo"})
        print(f"previews: {PREVIEW}")


if __name__ == "__main__":
    main()
