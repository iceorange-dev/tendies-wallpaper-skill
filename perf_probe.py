# -*- coding: utf-8 -*-
"""
Power probes: why do looping wallpapers keep backboardd at ~30% CPU on an idle Home Screen?

Each variant is the Chinatsu wallpaper with one thing changed, measured the same way as the baseline:
  A  NoAnim       every looping animation removed (states and gyro kept)      -> is the looping the cause?
  B  OneStar      only the smallest animation visible on Home kept            -> does any motion cost the full price?
  C  HideOnHome   animated trees fade out on Home/AOD, a still twin fades in  -> do invisible animations still cost?
  D  SpeedFreeze  `speed` state 1/0/0 wraps every looping animation           -> can a state pause them?
  E  30fps        animations carry frame-rate keys (private CAAnimation)      -> is a frame-rate cap honoured?
  F  LockOnly     loops never seen on Lock are removed; the rest pause by `speed` on Home/AOD and hide
                  (`hidden` 0/50/50) the moment a transition starts, while a still twin (opacity 0/50/50,
                  so it is opaque from 2% of the way) stands in   -> still Home without the D jitter?
  G  LockOnly2    F with 10000 in place of 50: on device F showed the still twin fading in over the first
                  frames after the live element hid, so elements blinked out for an instant
  H  LockOnly3    G with every still copy posed at its animation's t=0 frame: G's copies sat at the model
                  values, and all falling leaves share y=C there, so on Home they lined up
"""
import copy
import os
import sys

import tendies_kit as kit
from tendies_kit import Layer, S, C, walk, build_caml, package

try:
    import chinatsu_loops as base   # build_chinatsu.py as of commit 2a0ccd6, the last version that looped
except ImportError:
    sys.exit("perf_probe measures what loops cost, on the looping Chinatsu: "
             "git show 2a0ccd6:build_chinatsu.py > chinatsu_loops.py")

OUT = os.path.join(base.OUT, "perf")
VARIANTS = ("A", "B", "C", "D", "E", "F", "G", "H")
NAMES = dict(A="NoAnim", B="OneStar", C="HideOnHome", D="SpeedFreeze", E="30fps", F="LockOnly", G="LockOnly2", H="LockOnly3")
FRAME_KEYS = ' frameInterval="0.033333" discretizesTime="1" preferredFramesPerSecond="30"'


def effective(root):
    """name -> (layer, parent, (lock, home, sleep) effective opacity)."""
    out = {}

    def rec(l, parent, eff):
        st = l.states.get("opacity", (l.opacity,) * 3)
        me = tuple(e * s for e, s in zip(eff, st))
        out[l.name] = (l, parent, me)
        for c in l.children:
            rec(c, l, me)

    rec(root, None, (1.0, 1.0, 1.0))
    return out


def strip(l):
    for x, _ in walk(l):
        x.anim = None


def outermost_animated(l):
    """Animated layers with no animated ancestor, as (layer, parent) pairs."""
    found = []

    def rec(x, parent):
        if x.anim:
            found.append((x, parent))
            return
        for c in x.children:
            rec(c, x)

    rec(l, None)
    return found


def frame(parent, name):
    """A transparent layer with the parent's bounds, so children keep their coordinates."""
    return Layer(name, parent.w, parent.h, parent.w / 2, parent.h / 2)


def variant_b(root):
    info = effective(root)
    # an outermost one, so it stays where its own model puts it once its ancestors' motion is gone
    cands = [(x.w * x.h, x.name) for x, _ in outermost_animated(root) if info[x.name][2][1] > 0.001]
    keep = min(cands)[1]
    for x, _ in walk(root):
        if x.name != keep:
            x.anim = None
    return f"kept: {keep} ({info[keep][0].anim['keyPath']}, {info[keep][0].w:.0f}x{info[keep][0].h:.0f} pt)"


def variant_c(root):
    for top in root.children:                       # BACKGROUND, FLOATING
        twin = frame(top, f"{top.name} Still")
        for c in copy.deepcopy(top.children):
            twin.add(c)
        for x, _ in walk(twin):
            if x is not twin:
                x.name += " Still"
                x.id += "-still"
            x.anim = None
        live = frame(top, f"{top.name} Live")
        live.add(*top.children)
        twin.state("opacity", 0, 1, 1)
        twin.opacity = 0
        live.state("opacity", 1, 0, 0)
        top.children = [twin, live]
    return "Live trees fade 1/0/0, Still twins 0/1/1"


def variant_d(root):
    n = 0
    for x, parent in outermost_animated(root):
        clock = frame(parent, f"{x.name} Clock").state("speed", 1, 0, 0)
        parent.children[parent.children.index(x)] = clock
        clock.add(x)
        n += 1
    return f"{n} speed wrappers"


def pose(l):
    """Stop every animation under `l` at its own t=0 frame. Model values are often a shared rest point (all
    leaves fall through y=C), so a plain strip lines the copies up; t=0 keeps each one's staggered phase."""
    for x, _ in walk(l):
        if not x.anim:
            continue
        v, kp = kit.anim_value(x.anim, 0.0), x.anim["keyPath"]
        if kp == "position":
            x.x, x.y = v
        else:
            attr = {"position.x": "x", "position.y": "y", "transform.rotation.z": "rot",
                    "transform.scale": "scale", "opacity": "opacity"}[kp]
            setattr(x, attr, v)
        x.anim = None


def variant_f(root, step=50, freeze=strip):
    # a state value `step` times past 1 takes full effect 1/step of the way into a transition
    info = effective(root)
    stripped = paired = 0
    for x, parent in outermost_animated(root):
        if info[x.name][2][0] <= 0.001:             # never seen on Lock: it has no reason to move
            freeze(x)
            stripped += 1
            continue
        twin = copy.deepcopy(x)
        freeze(twin)
        for y, _ in walk(twin):
            y.name += " Still"
            y.id += "-still"
        box = frame(parent, f"{x.name} Still Box").state("opacity", 0, step, step).add(twin)
        box.opacity = 0
        clock = frame(parent, f"{x.name} Clock").state("speed", 1, 0, 0).state("hidden", 0, step, step).add(x)
        i = parent.children.index(x)
        parent.children[i:i + 1] = [box, clock]
        paired += 1
    return f"{stripped} loops removed (never on Lock), {paired} live/still pairs"


def variant_e(root):
    orig = kit.anim_xml

    def anim_xml(a, ind):
        out = orig(a, ind)
        out[1] = out[1].replace(' calculationMode=', FRAME_KEYS + ' calculationMode=')
        return out

    kit.anim_xml = anim_xml
    return "frame keys:" + FRAME_KEYS


def badge(v):
    """A still 'TEST X' tag over everything, below the clock in every posture, so the applied file is obvious."""
    from PIL import Image, ImageDraw, ImageFont
    text = f"TEST {v} · {NAMES[v]}"
    f = ImageFont.truetype(kit.CLOCK_FONT, int(30 * kit.PPT))
    l, t, r, b = f.getbbox(text, stroke_width=6)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=f, fill=(255, 255, 255, 255), stroke_width=6,
                            stroke_fill=(0, 0, 0, 255))
    key = kit.asset(f"perf_badge_{v}.png", im)
    return Layer(f"Perf Badge {v}", im.width / kit.PPT, im.height / kit.PPT, C, 330, img=key)


def main():
    want = [v for v in sys.argv[1:] if v in VARIANTS] or list(VARIANTS)
    master = base.build_root()                      # build once: the scene's rng must not run twice
    orig_anim_xml = kit.anim_xml
    for v in want:
        kit.anim_xml = orig_anim_xml
        root = copy.deepcopy(master)
        note = {"A": lambda r: strip(r) or "all loops removed", "B": variant_b, "C": variant_c,
                "D": variant_d, "E": variant_e, "F": variant_f,
                "G": lambda r: variant_f(r, 10000), "H": lambda r: variant_f(r, 10000, pose)}[v](root)
        next(c for c in root.children if c.name == "FLOATING").add(badge(v))
        caml = build_caml(root, allow_loops=True)  # the probes measure what loops cost
        name = f"Perf-{v}-{NAMES[v]}"
        out, ident, _, _ = package(caml, os.path.join(OUT, f"{name}.tendies"), os.path.join(base.OUT, "build", f"perf_{v}"))
        layers = sum(1 for _ in walk(root))
        anims = sum(1 for x, _ in walk(root) if x.anim)
        print(f"{name}: identity {ident}, layers {layers}, animations {anims}; {note}")
    kit.anim_xml = orig_anim_xml


if __name__ == "__main__":
    main()
