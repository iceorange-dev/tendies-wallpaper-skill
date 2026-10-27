# -*- coding: utf-8 -*-
"""
ongeki — read official ONGEKI art straight out of an AssetRipper export of the game (not distributed).

  card(id, full=False)        card character cut-out (768x1052), or the full illustration with background
  story_sprite(id, face)      story sprite body with one of its expression faces composited on, the way the
                              game's chara2d prefab lays it out (faces A_00 / A_01 = eyes open / blinking,
                              B..F = other expressions)
  chapter_bg(id, layer=None)  chapter background (1080x1080) or one of its separate layers (_01 .. _05)
  texture(name)               any Texture2D by file name stem

Set ONGEKI_EXPORT to the export's Assets folder if it is not at the default location.
"""
import os
import re

from PIL import Image

ASSETS = os.environ.get("ONGEKI_EXPORT", r"D:\SDDT_1.50.00_20250310133951_0\exported"
                        r"\AssetRipper_export_20260616_205625\ExportedProject\Assets")
TEX = os.path.join(ASSETS, "Texture2D")
SPRITE = os.path.join(ASSETS, "Sprite")
UI = os.path.join(ASSETS, "assetbundles", "ui")
CHARA2D = os.path.join(ASSETS, "assetbundles", "chara2d")


def card(card_id, full=False):
    if full:
        return Image.open(os.path.join(UI, "ui_card_chara_p", f"UI_Card_Chara_{card_id}_P.png")).convert("RGBA")
    return Image.open(os.path.join(UI, "ui_card_chara", f"UI_Card_Chara_{card_id}.png")).convert("RGBA")


def texture(name):
    return Image.open(os.path.join(TEX, name + ".png")).convert("RGBA")


def chapter_bg(bg_id, layer=None):
    return texture(f"FX_Chapter_BG_{bg_id}" + (f"_{layer:02d}" if layer else ""))


_GUID_FILE = {}


def _guid_index(folder):
    if folder not in _GUID_FILE:
        idx = {}
        for n in os.listdir(folder):
            if n.endswith(".meta"):
                with open(os.path.join(folder, n), encoding="utf-8", errors="replace") as fh:
                    m = re.search(r"^guid: ([0-9a-f]{32})", fh.read(), re.M)
                if m:
                    idx[m.group(1)] = os.path.join(folder, n[:-5])
        _GUID_FILE[folder] = idx
    return _GUID_FILE[folder]


def _sprite_info(path):
    """m_Rect (pixels in the source texture, y from the bottom), pivot and the packed atlas texture."""
    with open(path, encoding="utf-8") as fh:
        t = fh.read()

    def block(key):
        m = re.search(key + r":\s*\n\s*serializedVersion: \d+\s*\n\s*x: ([-\d.eE]+)\s*\n\s*y: ([-\d.eE]+)\s*\n"
                            r"\s*width: ([-\d.eE]+)\s*\n\s*height: ([-\d.eE]+)", t)
        return tuple(float(v) for v in m.groups())
    rect = block(r"textureRect")
    pivot = tuple(float(v) for v in re.search(r"m_Pivot: \{x: ([-\d.eE]+), y: ([-\d.eE]+)\}", t).groups())
    guid = re.search(r"texture: \{fileID: \d+, guid: ([0-9a-f]{32})", t).group(1)
    return rect, pivot, guid


def _atlas_crop(rect, guid):
    tex_path = _guid_index(TEX).get(guid)
    atlas = Image.open(tex_path).convert("RGBA")
    x, y, w, h = rect
    H = atlas.height
    return atlas.crop((round(x), round(H - y - h), round(x + w), round(H - y)))


def _prefab_layout(chara):
    """Centres / sizes of the Base and PAT_Face rects (UI pixels, y up) and the face sprite guids."""
    with open(os.path.join(CHARA2D, f"ANM_Chara_{chara}.prefab"), encoding="utf-8") as fh:
        t = fh.read()
    docs = re.split(r"^--- ", t, flags=re.M)
    names, rects, sprite_of = {}, {}, {}
    for d in docs:
        m = re.match(r"!u!(\d+) &(\d+)", d)
        if not m:
            continue
        kind, fid = m.groups()
        go = re.search(r"m_GameObject: \{fileID: (\d+)\}", d)
        if kind == "1":
            names[fid] = re.search(r"m_Name: (.*)", d).group(1).strip()
        elif kind == "224":
            pos = tuple(float(v) for v in re.search(r"m_AnchoredPosition: \{x: ([-\d.eE]+), y: ([-\d.eE]+)\}", d).groups())
            size = tuple(float(v) for v in re.search(r"m_SizeDelta: \{x: ([-\d.eE]+), y: ([-\d.eE]+)\}", d).groups())
            rects[go.group(1)] = (pos, size)
        elif kind == "114" and go:
            s = re.search(r"m_Sprite: \{fileID: \d+, guid: ([0-9a-f]{32})", d)
            if s:
                sprite_of[go.group(1)] = s.group(1)
    by_name = {names[g]: (rects.get(g), sprite_of.get(g)) for g in names}
    return by_name


def story_face(chara, face):
    """One expression face of a story sprite and where its top-left goes on the body (body pixels, y down),
    following the prefab: the body is drawn with its pivot on the Base anchor and the face with its pivot on
    the PAT_Face anchor (UI pixels, y up)."""
    lay = _prefab_layout(chara)
    (bpos, _), _ = lay["Base"]
    (fpos, _), _ = lay["PAT_EyeFace"]
    brect, bpiv, _ = _sprite_info(os.path.join(SPRITE, f"Chara_{chara}_Base_00.asset"))
    frect, fpiv, fguid = _sprite_info(os.path.join(SPRITE, f"Chara_{chara}_Face_{face}.asset"))
    f = _atlas_crop(frect, fguid)
    bw, bh = round(brect[2]), round(brect[3])
    bx0, btop = bpos[0] - bpiv[0] * bw, bpos[1] + (1 - bpiv[1]) * bh
    fx0, ftop = fpos[0] - fpiv[0] * f.width, fpos[1] + (1 - fpiv[1]) * f.height
    return f, (round(fx0 - bx0), round(btop - ftop))


def story_sprite(chara, face="A_00"):
    """Compose a story sprite (e.g. chara '00101401' = 日向千夏 uniform) with an expression face
    (A_00 / A_01 = eyes open / closed for blinking, B..F = other expressions). Returns RGBA at native size."""
    brect, _, bguid = _sprite_info(os.path.join(SPRITE, f"Chara_{chara}_Base_00.asset"))
    out = _atlas_crop(brect, bguid)
    if face:
        f, pos = story_face(chara, face)
        out.alpha_composite(f, pos)
    return out
