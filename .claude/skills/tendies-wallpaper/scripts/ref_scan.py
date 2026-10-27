"""Read-only survey of reference .tendies files (untrusted data: parsed in memory, nothing extracted or executed).

usage: python -I ref_scan.py OUT_DIR PATH [PATH ...]
PATH may be a .tendies, a .zip holding .tendies / .tendies.zip (nested to depth 3), or a directory of them.
Writes OUT_DIR/<label>.json per wallpaper, OUT_DIR/<label>/<bundle>.caml copies for later reading,
and prints a one-line summary per wallpaper plus feature counts across all of them.
"""
import collections
import io
import json
import os
import plistlib
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
MAX_MEMBER = 400 * 2 ** 20


def safe_label(s):
    return re.sub(r"[^0-9A-Za-z._-]+", "_", s).strip("_")[:90]


def png_size(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        return struct.unpack(">II", b[16:24])
    return None


def jpg_size(b):
    i = 2
    while i + 9 < len(b) and b[:2] == b"\xff\xd8":
        if b[i] != 0xFF:
            return None
        m = b[i + 1]
        ln = struct.unpack(">H", b[i + 2:i + 4])[0]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        i += 2 + ln
    return None


def short(v, depth=0):
    """Compact view of a plist value."""
    if isinstance(v, dict):
        if depth > 4:
            return "{...}"
        return {k: short(x, depth + 1) for k, x in list(v.items())[:40]}
    if isinstance(v, list):
        return [short(x, depth + 1) for x in v[:6]] + ([f"... +{len(v) - 6}"] if len(v) > 6 else [])
    if isinstance(v, bytes):
        try:
            return {"<bplist>": short(plistlib.loads(v), depth + 1)}
        except Exception:
            return f"<{len(v)} bytes>"
    if isinstance(v, plistlib.UID):
        return f"UID({v.data})"
    if isinstance(v, str) and len(v) > 160:
        return v[:160] + "..."
    return v if isinstance(v, (int, float, bool, str)) or v is None else str(v)


def load_plist(b):
    try:
        return plistlib.loads(b)
    except Exception as e:
        return {"<unparsed>": str(e)[:80]}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def scan_caml(text):
    if re.search(r"<!(DOCTYPE|ENTITY)", text[:4000]):
        return {"error": "DOCTYPE/ENTITY present, skipped"}
    root = ET.fromstring(text)
    tags = collections.Counter()
    layer_kinds = collections.Counter()
    layer_attrs = collections.Counter()
    anims = []
    states, setvals, transitions = [], collections.Counter(), []
    filters = collections.Counter()
    misc = collections.Counter()
    depth_max = 0
    names = []

    def walk(e, depth, layer_depth):
        nonlocal depth_max
        t = local(e.tag)
        tags[t] += 1
        is_layer = t.startswith("CA") and t.endswith("Layer")
        if is_layer:
            layer_kinds[t] += 1
            layer_depth += 1
            depth_max = max(depth_max, layer_depth)
            for a in e.attrib:
                layer_attrs[a] += 1
            if e.get("name"):
                names.append(e.get("name"))
        if t == "animation" or (t == "p" and (e.get("type") or "").endswith("Animation")):
            a = {k: e.get(k) for k in ("type", "keyPath", "duration", "repeatCount", "repeatDuration", "autoreverses",
                                        "calculationMode", "beginTime", "fillMode", "timeOffset", "speed", "mass",
                                        "stiffness", "damping", "velocity", "removedOnCompletion")
                 if e.get(k) is not None}
            kids = [local(c.tag) for c in e]
            if kids:
                a["children"] = sorted(set(kids))
            vals = e.find("{*}values")
            if vals is not None:
                a["n_values"] = len(list(vals))
                a["value_types"] = sorted({c.get("type") or local(c.tag) for c in vals})
            anims.append(a)
        if t == "LKState":
            states.append(e.get("name"))
        if t == "LKStateSetValue":
            setvals[e.get("keyPath")] += 1
        if t == "LKStateTransition":
            tr = {"from": e.get("fromState"), "to": e.get("toState"), "anims": collections.Counter()}
            for el in e.iter():
                if local(el.tag) == "animation" or (local(el.tag) == "p" and (el.get("type") or "").endswith("Animation")):
                    tr["anims"][f'{el.get("type")}:{el.get("keyPath")}:{el.get("duration")}'] += 1
            tr["anims"] = dict(tr["anims"].most_common(6))
            transitions.append(tr)
        if t in ("filter", "compositingFilter", "backgroundFilters") or (t == "filters"):
            for c in [e] + list(e):
                ty = c.get("type") or c.get("filter") or c.get("value")
                if ty:
                    filters[f"{t}:{ty}"] += 1
        if t in ("mask", "CAEmitterCell", "emitterCells", "contentsRect", "contentsCenter", "string", "font",
                 "shadowPath", "path", "colors", "instanceTransform", "instanceCount", "sublayerTransform",
                 "wallpaperParallaxGroups", "wallpaperPropertyGroups", "states", "stateTransitions", "modules",
                 "LKEventHandler", "LKStateAddAnimation", "LKStateAddElement", "LKStateRemoveElement"):
            misc[t] += 1
        for c in e:
            walk(c, depth + 1, layer_depth)

    walk(root, 0, 0)
    keypaths = collections.Counter(f'{a.get("type")}:{a.get("keyPath")}' for a in anims)
    return {
        "layers": sum(layer_kinds.values()), "layer_kinds": dict(layer_kinds), "layer_depth": depth_max,
        "layer_attrs": dict(layer_attrs.most_common()), "n_anims": len(anims), "anim_keypaths": dict(keypaths.most_common()),
        "anims_sample": anims[:400], "states": states, "state_setvalues": dict(setvals.most_common()),
        "transitions": transitions, "filters": dict(filters), "misc": dict(misc), "tags": dict(tags.most_common()),
        "names_sample": names[:300], "root_attrs": dict(list(root[0].attrib.items())[:30]) if len(root) else {},
    }


def scan_tendies(label, z, out_rows):
    names = z.namelist()
    info = {"label": label, "entries": len(names)}
    bundles = sorted({m.group(1) for n in names for m in [re.match(r"(.*?\.ca)/", n)] if m})
    info["bundles"] = bundles
    info["plists"] = {}
    for n in names:
        base = n.rsplit("/", 1)[-1]
        if base.endswith(".plist") and z.getinfo(n).file_size < 2 ** 20:
            info["plists"][n] = short(load_plist(z.read(n)))
    imgs = collections.Counter()
    sizes = []
    total_img = 0
    info["ca"] = {}
    caml_dir = os.path.join(OUT, label)
    for b in bundles:
        members = [n for n in names if n.startswith(b + "/") and not n.endswith("/")]
        rec = {"files": len(members)}
        caml_name = None
        idx = b + "/index.xml"
        if idx in names:
            m = re.search(rb"<rootDocument[^>]*>([^<]+)<", z.read(idx)) or re.search(rb'rootDocument[^"]*"([^"]+)"', z.read(idx))
            if m:
                caml_name = b + "/" + m.group(1).decode().strip()
        if caml_name not in names:
            camls = [n for n in members if n.endswith(".caml") and "assetManifest" not in n]
            caml_name = camls[0] if camls else None
        rec["caml"] = caml_name
        for n in members:
            ext = n.rsplit(".", 1)[-1].lower()
            if ext in ("png", "jpg", "jpeg", "heic", "gif", "webp", "mov", "mp4"):
                zi = z.getinfo(n)
                imgs[ext] += 1
                total_img += zi.file_size
                if ext in ("png", "jpg", "jpeg"):
                    head = z.open(n).read(65536)
                    wh = png_size(head) if ext == "png" else jpg_size(head)
                    if wh:
                        sizes.append((wh[0] * wh[1], wh[0], wh[1], n.rsplit("/", 1)[-1], zi.file_size))
        if caml_name:
            text = z.read(caml_name).decode("utf-8", "replace")
            os.makedirs(caml_dir, exist_ok=True)
            with open(os.path.join(caml_dir, safe_label(b.rsplit("/", 1)[-1]) + ".caml"), "w", encoding="utf-8") as fh:
                fh.write(text)
            try:
                rec.update(scan_caml(text))
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        info["ca"][b] = rec
    sizes.sort(reverse=True)
    info["images"] = dict(imgs)
    info["image_bytes_MB"] = round(total_img / 2 ** 20, 1)
    info["largest_images"] = [f"{w}x{h} {nm} {fs // 1024}KB" for _, w, h, nm, fs in sizes[:12]]
    info["n_sized"] = len(sizes)
    info["max_side"] = max((max(w, h) for _, w, h, _, _ in sizes), default=0)
    with open(os.path.join(OUT, label + ".json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=1, default=str)
    out_rows.append(info)


def visit(label, z, rows, depth):
    names = z.namelist()
    if any(re.match(r".*\.ca/", n) for n in names):
        scan_tendies(label, z, rows)
        return
    for n in names:
        low = n.lower()
        if (low.endswith(".tendies") or low.endswith(".zip")) and depth < 3:
            zi = z.getinfo(n)
            if zi.file_size > MAX_MEMBER:
                print("skip (too large)", n)
                continue
            try:
                inner = zipfile.ZipFile(io.BytesIO(z.read(n)))
            except zipfile.BadZipFile:
                print("not a zip:", n)
                continue
            visit(safe_label(re.sub(r"\.(tendies|zip)$", "", n.rsplit("/", 1)[-1], flags=re.I).replace(".tendies", "")),
                  inner, rows, depth + 1)


rows = []
for p in sys.argv[2:]:
    paths = [os.path.join(p, f) for f in sorted(os.listdir(p))] if os.path.isdir(p) else [p]
    for q in paths:
        if not q.lower().endswith((".tendies", ".zip")):
            continue
        try:
            z = zipfile.ZipFile(q)
        except zipfile.BadZipFile:
            print("not a zip:", q)
            continue
        label = safe_label(os.path.basename(q).rsplit(".", 1)[0])
        visit(label, z, rows, 0)

feat = collections.Counter()
kp_all = collections.Counter()
for r in rows:
    kinds, kps, nl, na, nst = collections.Counter(), collections.Counter(), 0, 0, 0
    for b, c in r["ca"].items():
        kinds.update(c.get("layer_kinds", {}))
        kps.update(c.get("anim_keypaths", {}))
        nl += c.get("layers", 0)
        na += c.get("n_anims", 0)
        nst += len(c.get("states", []))
        for k in c.get("misc", {}):
            feat[k] += 1
        for k in c.get("filters", {}):
            feat["filter " + k] += 1
        for k in c.get("layer_attrs", {}):
            feat["attr " + k] += 1
    for k in kinds:
        feat["kind " + k] += 1
    kp_all.update({k: 1 for k in kps})
    bn = ",".join(b.rsplit("/", 1)[-1] for b in r["ca"])
    print(f'{r["label"][:44]:44s} ca[{bn[:70]}] L{nl} A{na} S{nst} img{sum(r["images"].values())} '
          f'{r["image_bytes_MB"]}MB max{r["max_side"]}')
print("\n== features (number of wallpapers using) ==")
for k, v in sorted(feat.items(), key=lambda x: (-x[1], x[0])):
    print(f"{v:3d}  {k}")
print("\n== animation type:keyPath (number of wallpapers using) ==")
for k, v in kp_all.most_common():
    print(f"{v:3d}  {k}")
