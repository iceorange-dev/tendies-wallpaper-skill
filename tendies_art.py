# -*- coding: utf-8 -*-
"""
tendies_art — procedural art and source-image helpers shared by the build scripts.

Everything here is a pure function of its arguments: generators that need randomness take the caller's
`rng`, so each wallpaper keeps its own fixed seed and stable layout. Generated art follows the kit's
quality rule (smooth surfaces at >= 1.5 px/pt, fine detail drawn at 4x and reduced to @3x).
"""
import math

import cv2
import numpy as np
from PIL import Image

from tendies_kit import ASSETS, C, PPT, Layer, group, load, resize_premul, trim

WARM = (255, 238, 205)


# ----------------------------------------------------------------------------
# source art
# ----------------------------------------------------------------------------
def clean_alpha(im, floor=8):
    """Real-ESRGAN leaves faint alpha noise in transparent areas."""
    a = np.asarray(im.convert("RGBA")).copy()
    a[..., 3] = np.where(a[..., 3] < floor, 0, a[..., 3])
    return Image.fromarray(a, "RGBA")


def smooth(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def edge_fade(im, left=0.0, right=0.0, top=0.0, bottom=0.0):
    """Dissolve edges where the card illustration was cropped (fractions of width / height)."""
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    m = np.ones((h, w), np.float32)
    if left:
        n = int(w * left)
        m[:, :n] *= smooth(np.linspace(0, 1, n))[None, :]
    if right:
        n = int(w * right)
        m[:, w - n:] *= smooth(np.linspace(1, 0, n))[None, :]
    if top:
        n = int(h * top)
        m[:n, :] *= smooth(np.linspace(0, 1, n))[:, None]
    if bottom:
        n = int(h * bottom)
        m[h - n:, :] *= smooth(np.linspace(1, 0, n))[:, None]
    a[..., 3] *= m
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def radial_fade(im, cx, cy, r0, r1):
    """Soft spotlight: keep everything within r0 of (cx, cy), fade out by r1 (all in image widths)."""
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot(xx / w - cx, (yy - cy * h) / w)
    a[..., 3] *= 1 - smooth((d - r0) / (r1 - r0))
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def load_source(path, fade=None, spot=None, height_pt=None, width_pt=None):
    """Trim, clean and fade a character cut-out, then resample it to exactly @3x at the given size.
    Returns (image, width_pt, height_pt)."""
    im, _ = trim(clean_alpha(load(path)), thr=8, pad=6)
    if fade:
        im = edge_fade(im, **fade)
    if spot:
        im = radial_fade(im, *spot)
    if height_pt:
        width_pt = height_pt * im.width / im.height
    height_pt = width_pt * im.height / im.width
    return resize_premul(im, (width_pt * PPT, height_pt * PPT)), width_pt, height_pt


def cut_sprites(im, min_frac=0.002, join=0.008, alpha_floor=16, solid=40):
    """Split a transparent texture holding several items (e.g. the game's leaf textures) into its items:
    connected components of alpha > solid, dilated by `join` x width so an item's parts stay together; faint
    specks below alpha_floor are dropped. Returns [(crop RGBA, (x0, y0, x1, y1))] in reading order."""
    a = np.asarray(im.convert("RGBA")).copy()
    alpha = a[..., 3]
    h, w = alpha.shape
    k = max(3, int(w * join)) | 1
    core = cv2.dilate((alpha > solid).astype(np.uint8), np.ones((k, k), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(core, 8)
    items = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < min_frac * w * h:
            continue
        x, y, bw, bh = stats[i, :4]
        sub = a[y:y + bh, x:x + bw].copy()
        keep = (lab[y:y + bh, x:x + bw] == i) & (sub[..., 3] >= alpha_floor)
        sub[..., 3] = np.where(keep, sub[..., 3], 0)
        crop, _ = trim(Image.fromarray(sub, "RGBA"), thr=alpha_floor, pad=4)
        items.append((crop, (x, y, x + bw, y + bh)))
    row_h = max(1, h // 12)
    items.sort(key=lambda it: ((it[1][1] + it[1][3]) // 2 // row_h, it[1][0]))
    return items


# ----------------------------------------------------------------------------
# generated art
# ----------------------------------------------------------------------------
def grid(n):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    return xx / n, yy / n


def rgba(rgb, alpha):
    rgb = np.broadcast_to(np.asarray(rgb, np.float32), alpha.shape + (3,))
    return Image.fromarray(np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8), "RGBA")


def ramp3(lum, dark, mid, high):
    """Map 0..1 luminance onto a dark -> mid -> high colour ramp."""
    l = np.clip(lum, 0, 1)[..., None]
    dark, mid, high = (np.array(c, np.float32) for c in (dark, mid, high))
    return np.where(l < 0.5, dark + (mid - dark) * (l / 0.5), mid + (high - mid) * ((l - 0.5) / 0.5))


def beam(w, h, spread=0.92, rgb=WARM):
    """Light cone, narrow at the top (anchor it at (0.5, 1.0) and sway it)."""
    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    half = 0.07 + spread * y
    a = np.exp(-2.4 * (x / half) ** 2) * (0.25 + 0.75 * (1 - y) ** 0.5) * smooth(y * 12)
    a += np.random.default_rng(5).uniform(-0.006, 0.006, a.shape)
    return rgba(rgb, np.clip(a * 0.55, 0, 1))


def pool(w, h, rgb=WARM):
    """Elliptical pool of light on the ground."""
    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    a = np.exp(-2.2 * (x ** 2 + y ** 2)) * 0.6
    return rgba(rgb, a + np.random.default_rng(6).uniform(-0.005, 0.005, a.shape))


def soft_glow(n, rgb, amount):
    xx, yy = grid(n)
    return rgba(rgb, np.exp(-((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.06) * amount)


def vignette(size=1024, strength=190):
    xx, yy = grid(size)
    r = np.hypot(xx - 0.5, yy - 0.5) * 2
    va = np.clip((r - 0.5) / 0.6, 0, 1) ** 1.5 * strength
    va += np.random.default_rng(3).uniform(-1.5, 1.5, va.shape)
    return rgba((4, 4, 18), np.clip(va, 0, 255) / 255)


def star_points(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        rr = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def sparkle(px):
    N = px * 4
    xx, yy = grid(N)
    dx, dy = np.abs(xx - 0.5) * 2, np.abs(yy - 0.5) * 2
    arm = np.maximum(np.exp(-(dx / 0.05) ** 2) * np.clip(1 - dy, 0, 1) ** 2.2,
                     np.exp(-(dy / 0.05) ** 2) * np.clip(1 - dx, 0, 1) ** 2.2)
    core = np.exp(-(np.hypot(dx, dy) / 0.2) ** 2)
    return resize_premul(rgba((255, 246, 220), np.clip(arm + core * 0.85, 0, 1)), (px, px))


def mote(px, rgb=WARM):
    xx, yy = grid(px * 4)
    a = np.exp(-((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.03)
    return resize_premul(rgba(rgb, a), (px, px))


def confetti(px_w, px_h, rgb):
    N = 4
    w, h = px_w * N, px_h * N
    yy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    curl = 0.75 + 0.25 * np.cos(yy * 2.2)                        # a slight paper curl
    col = np.array(rgb, np.float32) * np.broadcast_to(curl, (h, w))[..., None]
    a = np.ones((h, w), np.float32)
    return resize_premul(rgba(col, a), (px_w, px_h))


# ----------------------------------------------------------------------------
# motion helpers (take the caller's rng so each wallpaper keeps its own layout)
# ----------------------------------------------------------------------------
def floating_bit(rng, name, key, size, x, y, alpha_lo=0.6, drift=(8, 24)):
    """Drift (position) -> spin (rotation) -> twinkle (opacity), one animation per layer."""
    r0 = rng.uniform(-25, 25)
    img = Layer(name, size, size, size / 2, size / 2, img=key)
    img.animate("opacity", [alpha_lo, 1.0], rng.uniform(1.8, 3.4), offset=rng.uniform(0, 3))
    spin = Layer(f"{name} Spin", size, size, x, y, rot=math.radians(r0)).add(img)
    d = rng.uniform(14, 30) * rng.choice([-1, 1])
    spin.animate("transform.rotation.z", [math.radians(r0), math.radians(r0 + d)], rng.uniform(4.5, 8),
                 offset=rng.uniform(0, 4))
    mover = group(f"{name} Drift").add(spin)
    a1, a2 = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
    m1, m2 = rng.uniform(drift[0], drift[1] * 0.75), rng.uniform(drift[0] * 1.5, drift[1])
    mover.animate("position", [(C, C), (C + m1 * math.cos(a1), C + m1 * math.sin(a1)),
                               (C + m2 * math.cos(a2), C + m2 * math.sin(a2))],
                  rng.uniform(5.5, 9.5), offset=rng.uniform(0, 6))
    return mover


def hanging(rng, name, key, w_pt, x, top):
    """A prop on a thread, swinging like a pendulum from the top of its thread (thread drawn in the image)."""
    iw, ih = ASSETS[key].size
    h_pt = w_pt * ih / iw
    p = Layer(name, w_pt, h_pt, x, top, img=key, anchor=(0.5, 1.0))
    amp = math.radians(rng.uniform(3, 6))
    p.animate("transform.rotation.z", [-amp, amp], rng.uniform(2.8, 4.4), offset=rng.uniform(0, 4))
    return p
