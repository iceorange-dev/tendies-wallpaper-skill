# -*- coding: utf-8 -*-
"""
日向千夏 (ONGEKI, マーチングポケッツ) — "千夏と、毎日ぎゅー。", an AirCard .tendies for the iPhone Duo.

From her profile and lines: she cannot help hugging people (癖: ぎゅっと抱きつく), her trophy asks
「千夏と毎日ぎゅーーってしよ？」, and her card 【SR+】大好き☆アタック+ is exactly that: a running leap into a hug.
The wallpaper is one school day at the 奏坂学園 courtyard under its great tree.
  Lock   morning: close up in the courtyard she waves at you — "おはよー！" — blinking now and then;
         leaves drift down from the great tree, whose crown glitters
  Home   unlocking is the hug: 大好き☆アタック! she leaps at you with her arms up, the camera's focus pulls
         onto her (the courtyard goes soft) and yellow ☆ burst out around her
  Sleep  Always-On Display: the same courtyard at night under the stars, the great tree glittering, the clock
         tower lit; she holds her hand up and smiles ^^ — "おやすみ～！" — wholly below the clock

Everything drawn is official ONGEKI art from the game data; code only adds light, blur, tint and motion:
  story sprite Chara_00101401 (uniform) with its faces A_00 / A_01 (eyes open / closed: the game's own blink)
    and B_00 (the ^^ smile, on the AOD)
  card 100473 【SR+】日向 千夏[大好き☆アタック+] character layer
  chapter background 9903401 layers: sky (_01), great tree (_02), school and plaza (_03), crown glitter (_04)
  textures FX_mm_leaf_01 / st_2030_leaf (leaves), Star_001 (☆), st_2015_star_df (twinkle), st_2000_sky_df (stars)
  colour ChinatsuYellow #ffd427 from the game's 50-colour table
Large art is Real-ESRGAN x4plus-anime 4x (sources/chinatsu/*_x4.png), resampled here to the size used.
"""
import json
import math
import os
import random
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tendies_kit import *  # noqa: F401,F403  (scene graph, CAML, packaging, previews, device model)
import ongeki
import tendies_art as art
from tendies_art import cut_sprites, rgba, smooth, soft_glow, vignette

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources", "chinatsu")
OUT_NAME = "Hinata-Chinatsu-Fold"
OUT = os.path.join(HERE, "out")                  # every generated file: .tendies, build/, preview/
BUILD = os.path.join(OUT, "build", "chinatsu")
PREVIEW = os.path.join(OUT, "preview", "chinatsu")

GIRL_H = 830.0             # Lock: a half-length shot (the whole story sprite would be 830 pt tall) ...
CUT = 0.70                 # ... with the screen's bottom edge crossing her just above the knees
FEET = -(1 - CUT) * GIRL_H # where her feet would be, below the screen: the sway / scale pivot
CROP = 0.80                # rows below this fraction of the sprite never show, so they are not stored
                           # (bow ~542, waving hand ~581: her head is in front of the clock's lower edge)
SLEEP_TOP = 404.0          # AOD: her raised hand stays under the folded clock bottom (~434), no depth there
SLEEP_SCALE = (SLEEP_TOP - FEET) / GIRL_H
HUG_H, HUG_BASE = 740.0, -80.0           # Home: the leap, closer than the wave, feet below the screen edge
SCHOOL_W, SCHOOL_BOTTOM = 960.0, -40.0   # chapter background layers, arranged for the square root
TREE_W, TREE_BOTTOM = 1000.0, 250.0
SKY_W, SKY_BOTTOM = 1540.0, 300.0
YELLOW = (255, 212, 39)                  # ChinatsuYellow #ffd427
HER = (C, 330.0)                         # centre of the leap, where the ☆ burst from

rng = random.Random(20180822)            # Chinatsu's birthday


def src(name):
    return load(os.path.join(SRC, name))


def sized(im, w_pt, ppt=PPT):
    """Resample to w_pt wide at ppt pixels per point (premultiplied Lanczos)."""
    return resize_premul(im, (max(1, round(w_pt * ppt)), max(1, round(w_pt * ppt * im.height / im.width))))


def place(name, key, im, w_pt, x, y, ppt=PPT, **kw):
    """Register `im` resampled for a w_pt-wide layer centred at (x, y)."""
    return image_layer(name, asset(key, sized(im, w_pt, ppt)), w=w_pt, x=x, y=y, **kw)


def tint(im, mul, sat=1.0):
    a = np.asarray(im).astype(np.float32)
    lum = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    a[..., :3] = (lum[..., None] + (a[..., :3] - lum[..., None]) * sat) * np.array(mul, np.float32)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def soft(im, w_pt, radius_pt, ppt=0.6):
    """A defocused copy for the Home rack focus: blurred art needs very few pixels."""
    small = sized(im, w_pt, ppt)
    a = np.asarray(small).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]                                   # blur in premultiplied space: no dark fringes
    sharp_alpha = a[..., 3:4].copy()
    a = cv2.GaussianBlur(a, (0, 0), radius_pt * ppt)
    rgb = np.where(a[..., 3:4] > 1e-4, a[..., :3] / np.maximum(a[..., 3:4], 1e-4), 0)
    a[..., 3:4] = np.maximum(a[..., 3:4], sharp_alpha)          # cover the sharp layer fully: no crisp edge peeks out
    return Image.fromarray((np.dstack([rgb, a[..., 3:4]]).clip(0, 1) * 255).round().astype(np.uint8), "RGBA")


def glow_alpha(im, rgb=None, gain=1.0, gamma=1.0):
    """Black-background glow texture (made for additive blending) -> RGBA with alpha = brightness."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    lum = a[..., :3].max(axis=2) / 255 * (a[..., 3] / 255)
    alpha = np.clip(lum * gain, 0, 1) ** gamma
    col = a[..., :3] / np.maximum(lum[..., None], 1e-3) if rgb is None else np.broadcast_to(np.array(rgb, np.float32), a[..., :3].shape)
    return rgba(np.clip(col, 0, 255), alpha)


def vgrad(w, h, stops):
    t = np.linspace(0, 1, h, dtype=np.float32)
    col = np.stack([np.interp(t, [s for s, _ in stops], [c[i] for _, c in stops]) for i in range(3)], 1)
    return rgba(np.broadcast_to(col[:, None, :], (h, w, 3)), np.ones((h, w), np.float32))


# ----------------------------------------------------------------------------
# official sprites
# ----------------------------------------------------------------------------
def leaves(name):
    """The leaves on one of the game's leaf textures, cut apart."""
    return [c for c, _ in cut_sprites(ongeki.texture(name), min_frac=0.01, join=0.02)][:4]


def yellow_star(px_):
    """The game's Star_001 shape in ChinatsuYellow with a soft glow and a pale core."""
    st = ongeki.texture("Star_001")
    a = np.asarray(st)[..., 3].astype(np.float32) / 255
    N = st.width
    glow = cv2.GaussianBlur(a, (0, 0), N * 0.06) * 0.7
    core = cv2.GaussianBlur(cv2.erode(a, np.ones((int(N * 0.12),) * 2, np.uint8)), (0, 0), N * 0.03)
    col = np.array(YELLOW, np.float32) * (1 - core[..., None] * 0.6) + 255 * core[..., None] * 0.6
    img = Image.alpha_composite(rgba(YELLOW, glow), rgba(col, a))
    pad = Image.new("RGBA", (int(N * 1.3), int(N * 1.3)), (0, 0, 0, 0))
    pad.alpha_composite(img, (int(N * 0.15), int(N * 0.15)))
    return resize_premul(pad, (px_, px_))


def drifting_leaf(i, key, size, x0, dur_rng, sway_rng, alpha=1.0):
    """Falls (position.y) -> sways (position.x) -> tumbles (rotation): one animation per layer (techniques C3)."""
    iw, ih = ASSETS[key].size
    w, h = (size, size * ih / iw) if iw >= ih else (size * iw / ih, size)
    leaf = Layer(f"Leaf {i} Tumble", w, h, C, C, img=key, opacity=alpha)
    leaf.animate("transform.rotation.z", [0.0, rng.choice([-1, 1]) * rng.uniform(3, 6)], rng.uniform(4, 8),
                 autoreverses=False, timing="linear", offset=rng.uniform(0, 4))
    sway = group(f"Leaf {i} Sway", x=x0).add(leaf)
    amp = rng.uniform(*sway_rng)
    sway.animate("position.x", [x0 - amp, x0 + amp], rng.uniform(2.4, 4.0), offset=rng.uniform(0, 3))
    fall = group(f"Leaf {i} Fall").add(sway)
    dur = rng.uniform(*dur_rng)
    fall.animate("position.y", [C + 520, C - 520], dur, autoreverses=False, timing="linear", offset=rng.uniform(0, dur))
    return fall


# ----------------------------------------------------------------------------
# scene
# ----------------------------------------------------------------------------
def build_background():
    root_bg = group("BACKGROUND")
    root_bg.id = "background"
    base = group("Sky Base", w=2800, h=2800, color=(0.30, 0.55, 0.85))

    sky = src("academy_sky_x4.png")
    tree = src("academy_tree_x4.png")
    school = src("academy_school_x4.png")
    sky_h = SKY_W * sky.height / sky.width
    tree_h = TREE_W * tree.height / tree.width
    school_h = SCHOOL_W * school.height / school.width
    sky_y, tree_y, school_y = SKY_BOTTOM + sky_h / 2, TREE_BOTTOM + tree_h / 2, SCHOOL_BOTTOM + school_h / 2

    # --- sky: day (drifting clouds) / night (gradient + the game's star field + twinkles + moon) ----------
    day_sky = place("Sky Day", "sky_day.png", sky, SKY_W, C, sky_y, ppt=1.6)
    day_sky.animate("position.x", [C - 22, C + 22], 60.0)
    night = group("Night Sky", opacity=0.0).state("opacity", 0.0, 0.0, 1.0)
    night.add(image_layer("Night Gradient", asset("night_grad.png", vgrad(16, 256, [(0, (5, 9, 30)), (0.65, (14, 22, 58)),
                                                                                (1, (32, 42, 88))])),
                          w=SKY_W, h=sky_h, x=C, y=sky_y))
    stars = glow_alpha(ongeki.texture("st_2000_sky_df"), rgb=(232, 238, 255), gain=2.2)
    night.add(image_layer("Star Field", asset("star_field.png", stars), w=1100, x=C, y=sky_y + 40))
    asset("twinkle.png", resize_premul(glow_alpha(ongeki.texture("st_2015_star_df"), rgb=(240, 244, 255), gain=1.2), (72, 72)))
    for i in range(10):
        s = rng.uniform(10, 20)
        t = Layer(f"Twinkle {i + 1}", s, s, rng.uniform(150, 740), rng.uniform(520, 880), img="twinkle.png")
        t.animate("opacity", [0.1, 1.0, 0.1], rng.uniform(2.4, 4.6), autoreverses=False, key_times=[0, 0.5, 1],
                  offset=rng.uniform(0, 4))
        night.add(t)
    asset("moon_glow.png", soft_glow(256, (226, 232, 255), 0.55))
    asset("moon_disc.png", soft_glow(128, (255, 252, 236), 1.0))
    night.add(image_layer("Moon Glow", "moon_glow.png", w=300, x=705, y=760),
              image_layer("Moon Disc", "moon_disc.png", w=58, x=705, y=760))
    sky_par = group("Sky Parallax", kind="CATransformLayer").add(day_sky, night)
    sky_par.parallax = 3

    # --- the great tree: day, night (moonlit), and the glitter in its crown (stronger at night) ------------
    tree_day = place("Tree Day", "tree_day.png", tree, TREE_W, C, tree_y)
    tree_night = place("Tree Night", "tree_night.png", tint(tree, (0.22, 0.30, 0.50), sat=0.7), TREE_W, C, tree_y, ppt=1.5,
                       opacity=0.0)
    tree_night.state("opacity", 0.0, 0.0, 1.0)
    glitter = glow_alpha(ongeki.chapter_bg(9903401, 4), gain=2.0)
    sparkle = place("Crown Glitter", "crown_glitter.png", glitter, TREE_W, C, tree_y, ppt=1.46)
    sparkle.animate("opacity", [0.55, 1.0], 3.2)
    sparkle_g = group("Crown Glitter Level", opacity=0.3).state("opacity", 0.3, 0.3, 1.0).add(sparkle)
    tree_par = group("Tree Parallax", kind="CATransformLayer").add(tree_day, tree_night, sparkle_g)
    tree_par.parallax = 6

    # --- the school and its plaza: day, night, the clock tower's light at night -----------------------------
    school_day = place("School Day", "school_day.png", school, SCHOOL_W, C, school_y)
    school_night = place("School Night", "school_night.png", tint(school, (0.24, 0.30, 0.48), sat=0.65), SCHOOL_W, C,
                         school_y, ppt=1.5, opacity=0.0)
    school_night.state("opacity", 0.0, 0.0, 1.0)
    a = np.asarray(school)[..., 3]
    cols = a[:, int(a.shape[1] * 0.44):int(a.shape[1] * 0.56)]
    top_row = int(np.argmax((cols > 200).any(axis=1)))
    tower = (C, school_y + school_h / 2 - top_row / a.shape[0] * school_h - 14)
    asset("tower_light.png", soft_glow(256, (255, 226, 160), 0.9))
    tower_light = image_layer("Tower Light", "tower_light.png", w=120, x=tower[0], y=tower[1], opacity=0.0)
    tower_light.state("opacity", 0.0, 0.0, 1.0)
    school_par = group("School Parallax", kind="CATransformLayer").add(school_day, school_night, tower_light)
    school_par.parallax = 9

    # --- morning light through the great tree's crown (komorebi), swaying slowly ---------------------------
    asset("beam.png", art.beam(390, 1350, spread=0.45, rgb=(255, 246, 214)))
    beams = group("Komorebi", opacity=0.9).state("opacity", 0.9, 0.6, 0.0)
    for i, (x, deg, op) in enumerate(((290, -14, 0.35), (520, 5, 0.45), (690, 17, 0.3))):
        b = Layer(f"Beam {i + 1}", 260, 900, x, 880, img="beam.png", anchor=(0.5, 1.0), rot=math.radians(deg), opacity=op)
        b.animate("transform.rotation.z", [math.radians(deg - 2.5), math.radians(deg + 2.5)], 9.0 + i * 2.3, offset=i * 1.7)
        beams.add(b)
    beam_par = group("Komorebi Parallax", kind="CATransformLayer").add(beams)
    beam_par.parallax = 7

    # --- Home: the focus pulls onto her — the whole courtyard goes soft ------------------------------------
    focus = group("Defocus", opacity=0.0).state("opacity", 0.0, 1.0, 0.0)
    for nm, im, w, y, par in (("Sky", sky, SKY_W, sky_y, 3), ("Tree", tree, TREE_W, tree_y, 6),
                              ("School", school, SCHOOL_W, school_y, 9)):
        blur = image_layer(f"{nm} Soft", asset(f"{nm.lower()}_soft.png", soft(im, w, 7.0)), w=w, x=C, y=y)
        g = group(f"{nm} Soft Parallax", kind="CATransformLayer").add(blur)
        g.parallax = par
        focus.add(g)
    warm = image_layer("Her Warmth", asset("warmth.png", soft_glow(512, (255, 232, 160), 0.9)), w=820, x=C, y=430,
                       opacity=0.0)
    warm.state("opacity", 0.0, 0.32, 0.0)

    # --- leaves far away, soft (st_2030_leaf); the near ones fall in front of her (FLOATING) -----------------
    far = [asset(f"leaf_soft{i + 1}.png", resize_premul(l, (l.width // 2, l.height // 2)))
           for i, l in enumerate(leaves("st_2030_leaf"))]
    far_g = group("Far Leaves", opacity=0.85).state("opacity", 0.85, 1.0, 0.0)
    for i in range(9):
        far_g.add(drifting_leaf(f"F{i + 1}", far[i % len(far)], rng.uniform(9, 15), rng.uniform(80, 810), (14, 22), (12, 26)))
    far_par = group("Far Leaf Parallax", kind="CATransformLayer").add(far_g)
    far_par.parallax = 8

    vig = image_layer("Vignette", asset("vignette.png", vignette(512, 110)), w=1300)
    sleep_dim = group("Sleep Dim", w=2800, h=2800, color=(0.0, 0.0, 0.03), opacity=0.0)
    sleep_dim.state("opacity", 0.0, 0.0, 0.18)
    root_bg.add(base, sky_par, tree_par, school_par, focus, beam_par, warm, far_par, vig, sleep_dim)
    return root_bg


def wave_rig(body):
    """Cut her raised cuff and hand off the story sprite (x4 pixels) so they can wave from the wrist
    (techniques B6). The cut runs through the navy sleeve just below the cuff; under the cuff the sleeve is
    continued (inpainted) so a turning cuff never opens onto the background. Returns the body without the
    hand, the hand piece, its box on the body and the pivot (body pixels, y down)."""
    a = np.asarray(art.clean_alpha(body)).copy()
    H, W = a.shape[:2]
    p0, p1 = (1420, 830), (1880, 900)
    poly = [(1440, 0), (W, 0), (W, p1[1]), p1, p0, (1440, p0[1])]
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    m = cv2.GaussianBlur(np.asarray(m, np.float32) / 255, (0, 0), 3.0)      # a soft seam
    hand = a.copy()
    hand[..., 3] = (a[..., 3] * m).astype(np.uint8)
    rest = a.copy()
    rest[..., 3] = (a[..., 3] * (1 - m)).astype(np.uint8)
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).polygon([p0, p1, (p1[0], p1[1] - 70), (p0[0], p0[1] - 70)], fill=255)
    band = (np.asarray(band) > 0) & (a[..., 3] > 200)
    fill = cv2.inpaint(np.ascontiguousarray(rest[..., :3]), band.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA)
    rest[..., :3][band] = fill[band]
    rest[..., 3][band] = a[..., 3][band]
    box = (1380, 0, W, p1[1] + 20)
    hand_im = Image.fromarray(hand, "RGBA").crop(box)
    pivot = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    return Image.fromarray(rest, "RGBA"), hand_im, box, pivot


def face_patch(face_x4, name):
    """One of the game's faces as an opaque patch over another face baked into the body.

    The game's face sprites are transparent where another face's eyes would be (they are drawn on the
    faceless body), so a face sprite laid over a composited face lets the old eyes show through. Instead each
    full face is composited on the body at native size (story_uniform_A00 / _A01 / _B00), upscaled the same
    way, and cut out with a feathered mask of the pixels where two faces differ.
    name: the mask to cut with — "blink" (where A_00 and A_01 differ: eyes, lashes) or "smile" (where A_00
    and B_00 differ: brows, eyes, mouth). Returns the patch and its box on the x4 body."""
    info = json.load(open(os.path.join(SRC, "story_uniform_faces.json")))
    box = tuple(v * 4 for v in info[f"{name}_box"])
    mask = src(f"story_uniform_{name}_mask.png").convert("L").resize((box[2] - box[0], box[3] - box[1]), Image.BICUBIC)
    patch = np.asarray(face_x4.crop(box)).copy()
    patch[..., 3] = (patch[..., 3].astype(np.float32) * np.asarray(mask, np.float32) / 255).astype(np.uint8)
    return Image.fromarray(patch, "RGBA"), box


def build_girl():
    """Lock: the story sprite in a half-length shot, waving good morning and blinking with the game's own
    closed-eye face. Sleep: the same girl, smaller and moonlit, her hand raised still and smiling ^^ —
    "おやすみ～！" (the game's B_00 smile, made to be held; the blink frame would look frozen mid-blink)."""
    # the body carries the ^^ smile (what the AOD shows); on Lock the open face is laid over it and on the way
    # to the AOD it fades as (1-u)^5: she smiles as soon as the screen starts to dim, never half-and-half
    body = src("story_uniform_B00_x4.png")
    k = GIRL_H / body.height                                      # pt per x4 pixel
    w = body.width * k

    def face_layer(name, key, patch, box, ppt=PPT, **kw):
        fw, fh = (box[2] - box[0]) * k, (box[3] - box[1]) * k
        if key not in ASSETS:                                     # layers showing the same face share one image
            asset(key, sized(patch, fw, ppt))
        return Layer(name, fw, fh, box[0] * k + fw / 2, GIRL_H - (box[1] * k + fh / 2), img=key, **kw)

    rest, hand, box, pivot = wave_rig(body)
    rest = rest.crop((0, 0, rest.width, round(rest.height * CROP)))
    ch = GIRL_H * CROP
    moon = lambda im: tint(im, (0.62, 0.66, 0.84), sat=0.8)  # noqa: E731  (moonlit, for the AOD)
    day_b = Layer("Girl Body", w, ch, w / 2, GIRL_H - ch / 2, img=asset("girl.png", sized(rest, w)), trilinear=True)
    night_b = Layer("Girl Body Night", w, ch, w / 2, GIRL_H - ch / 2,
                    img=asset("girl_night.png", sized(moon(rest), w, 2.0)), opacity=0.0)
    night_b.state("opacity", 0.0, 0.0, 1.0)
    # the waving hand: cuff and hand cut from the same sprite, swung from the wrist in little bursts (Lock).
    # On the AOD, where frames are few, the hand is held still: the night hand sits outside the waving layer
    hw, hh = (box[2] - box[0]) * k, (box[3] - box[1]) * k
    hand_at = dict(x=pivot[0] * k, y=GIRL_H - pivot[1] * k,
                   anchor=((pivot[0] - box[0]) / (box[2] - box[0]), 1 - (pivot[1] - box[1]) / (box[3] - box[1])))
    wave = Layer("Hand Wave", hw, hh, **hand_at)
    hand_d = Layer("Hand", hw, hh, hw / 2, hh / 2, img=asset("hand.png", sized(hand, hw)), trilinear=True)
    wave.state("opacity", 1.0, 1.0, 0.0)
    r = math.radians
    wave.add(hand_d).animate("transform.rotation.z", [0, 0, r(9), r(-7), r(9), r(-7), r(5), 0, 0], 5.5,
                             autoreverses=False, key_times=[0, 0.52, 0.58, 0.64, 0.70, 0.76, 0.82, 0.88, 1])
    hand_n = Layer("Hand Night", hw, hh, img=asset("hand_night.png", sized(moon(hand), hw, 2.0)), opacity=0.0, **hand_at)
    hand_n.state("opacity", 0.0, 0.0, 1.0)

    open_face, obox = face_patch(src("story_uniform_A00_x4.png"), "smile")   # where the open face and the smile differ
    eyes = chained("Open Face", (1.0, 1.0, 0.0), 5, face_layer("Open Face", "open_face.png", open_face, obox))
    blink, bbox = face_patch(src("story_uniform_A01_x4.png"), "blink")
    blinks = group("Blinks").state("opacity", 1.0, 1.0, 0.0)
    for i, (dur, off) in enumerate(((4.3, 0.0), (11.7, 2.9))):     # two rhythms: now and then a double blink
        b = face_layer(f"Blink {i + 1}", "blink.png", blink, bbox, opacity=0.0)
        b.animate("opacity", [0, 0, 1, 1, 0], dur, autoreverses=False, timing="linear",
                  key_times=[0, 0.955, 0.962, 0.992, 1.0], offset=off)
        blinks.add(b)
    # the whole figure sways from her feet, far below the screen edge
    sway = Layer("Girl Sway", w, GIRL_H, C, FEET, anchor=(0.5, 0.0)).add(day_b, night_b, eyes, wave, hand_n, blinks)
    sway.animate("transform.rotation.z", [math.radians(-0.6), math.radians(0.6)], 5.6)
    breathe = Layer("Girl Breathe", S, S, C, FEET, anchor=(0.5, FEET / S)).add(sway)
    breathe.animate("transform.scale", [1.0, 1.005], 4.2)
    par = group("Girl Parallax", kind="CATransformLayer").add(breathe)
    par.parallax = 12
    # Home: she springs off (rising, growing) and gives way to the leap; Sleep: smaller, below the clock
    stage = Layer("Girl Stage", S, S, C, FEET, anchor=(0.5, FEET / S))
    stage.state("position.y", FEET, FEET + 40, FEET).state("transform.scale.xy", 1.0, 1.15, SLEEP_SCALE)
    # (1-u)^3: she is mostly gone before the leap is half in, so the two poses barely overlap
    return stage.add(chained("Girl", (1.0, 0.0, 1.0), 3, par))


def build_hug():
    """Home: 大好き☆アタック — the card's leap, close to us; the ☆ burst from where she took off."""
    card = src("card_100473_daisuki_attack_x4.png")
    a = np.asarray(card)[..., 3]
    ys, xs = np.nonzero(a > 16)
    card = card.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    w = HUG_H * card.width / card.height
    leap = Layer("Leap", w, HUG_H, C, HUG_BASE + HUG_H / 2, img=asset("leap.png", sized(card, w)), trilinear=True)
    rim_img, pad = alpha_glow(card.getchannel("A"), (255, 240, 190), scale=0.05, dilate=2, blur=8, pad=24, strength=0.7)
    k = HUG_H / card.height
    rim = Layer("Leap Rim", (card.width + 2 * pad) * k, (card.height + 2 * pad) * k, C, HUG_BASE + HUG_H / 2,
                img=asset("leap_rim.png", rim_img), opacity=0.5)
    hover = group("Leap Hover").add(rim, leap)
    hover.animate("position.y", [C, C + 10], 2.6)
    par = group("Leap Parallax", kind="CATransformLayer").add(hover)
    par.parallax = 14
    stage = Layer("Leap Stage", S, S, C, HUG_BASE - 40, anchor=(0.5, HUG_BASE / S), opacity=0.0, scale=0.85)
    stage.state("opacity", 0.0, 1.0, 0.0).state("transform.scale.xy", 0.85, 1.0, 0.85) \
         .state("position.y", HUG_BASE - 40, HUG_BASE, HUG_BASE - 40)

    asset("star.png", yellow_star(150))
    burst = group("Star Burst", kind="CATransformLayer")
    burst.parallax = 24
    for i in range(12):
        for _ in range(60):                                   # land around her, clear of her face
            ang = 2 * math.pi * i / 12 + rng.uniform(-0.25, 0.25)
            r = rng.uniform(250, 390)
            hx, hy = C + r * math.cos(ang) * 1.05, 430 + r * math.sin(ang) * 0.9
            if not (300 < hx < 590 and 360 < hy < 600):
                break
        s = rng.uniform(26, 46)
        spin = Layer(f"Star {i + 1} Spin", s, s, s / 2, s / 2, img="star.png", rot=rng.uniform(0, 6.28))
        spin.animate("transform.rotation.z", [spin.rot, spin.rot + rng.choice([-1, 1]) * rng.uniform(0.3, 0.7)],
                     rng.uniform(3.5, 6.5), offset=rng.uniform(0, 4))
        twinkle = Layer(f"Star {i + 1}", s, s, HER[0] + rng.uniform(-30, 30), HER[1] + rng.uniform(-20, 40), opacity=0.0)
        twinkle.add(spin)
        twinkle.state("position.x", twinkle.x, hx, twinkle.x).state("position.y", twinkle.y, hy, twinkle.y) \
               .state("opacity", 0.0, 0.9, 0.0)
        burst.add(twinkle)
    return stage.add(par), burst


def build_near_leaves():
    near = [asset(f"leaf{i + 1}.png", l) for i, l in enumerate(leaves("FX_mm_leaf_01"))]
    g = group("Near Leaves", opacity=0.9).state("opacity", 0.9, 1.0, 0.0)
    for i in range(8):
        g.add(drifting_leaf(f"N{i + 1}", near[i % len(near)], rng.uniform(18, 28), rng.uniform(60, 830), (9, 15), (18, 40)))
    par = group("Near Leaf Parallax", kind="CATransformLayer").add(g)
    par.parallax = 22
    return par


def build_floating():
    root_fl = group("FLOATING")
    root_fl.id = "floating"
    hug, burst = build_hug()
    root_fl.add(build_girl(), hug, burst, build_near_leaves())
    return root_fl


def build_root():
    return Layer("Root Layer", S, S, C, C).add(build_background(), build_floating())


def main():
    root = build_root()
    caml = build_caml(root)
    out, ident, desc_uuid, ca_name = package(caml, os.path.join(OUT, f"{OUT_NAME}.tendies"), BUILD)

    mem = sum(im.width * im.height * 4 for im in ASSETS.values()) / 2 ** 20
    print(f"layers: {sum(1 for _ in walk(root))}, assets: {len(ASSETS)}, decoded ~{mem:.0f} MB")
    print(f"tendies: {out} ({os.path.getsize(out) / 2 ** 20:.1f} MB)")
    print(f"identity: {ident}  descriptor: {desc_uuid}  CA bundle: {ca_name}")
    big = sorted(ASSETS.items(), key=lambda kv: -kv[1].width * kv[1].height)[:6]
    print("largest:", ", ".join(f"{k} {im.width}x{im.height}" for k, im in big))
    if "--no-preview" not in sys.argv:
        make_previews(root, PREVIEW, {"lock": "鎖定 おはよー！（學園中庭）", "home": "主畫面 大好き☆アタック！",
                                      "sleep": "待機 AOD・おやすみ～"})
        print(f"previews: {PREVIEW}")


if __name__ == "__main__":
    main()
