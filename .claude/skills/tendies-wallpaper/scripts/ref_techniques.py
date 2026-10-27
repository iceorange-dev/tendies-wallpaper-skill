"""Pull concrete technique examples out of the CAML copies saved by ref_scan.py (read-only XML parsing).

usage: python -I ref_techniques.py REFSCAN_DIR
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

D = sys.argv[1]


def local(t):
    return t.rsplit("}", 1)[-1]


def is_anim(e):
    return local(e.tag) in ("animation", "p") and (e.get("type") or "").endswith("Animation")


def vals(e):
    v = e.find("{*}values")
    if v is None:
        return []
    out = []
    for c in v:
        out.append(c.get("value") if c.get("value") is not None else
                   (c[0].get("src") if len(c) and c[0].get("src") else local(c.tag)))
    return out


def fmt_vals(vs, n=8):
    def s(x):
        try:
            return f"{float(x):.3g}"
        except (TypeError, ValueError):
            return str(x)
    vs2 = [s(x) for x in vs]
    return "[" + ", ".join(vs2[:n]) + (f", … ({len(vs2)})" if len(vs2) > n else "") + "]"


anim_ex = collections.defaultdict(list)
blinks, comp, emit, setv, trans, filt, contents_anim, roots, fg, names = ([] for _ in range(10))
setv_kp = collections.Counter()
comp_c = collections.Counter()
layer_kw = collections.Counter()

for label in sorted(os.listdir(D)):
    p = os.path.join(D, label)
    if not os.path.isdir(p):
        continue
    for fn in sorted(os.listdir(p)):
        if not fn.endswith(".caml"):
            continue
        part = ("BG" if "Background" in fn else "FL" if "Floating" in fn else "FG" if "Foreground" in fn else fn[:12])
        text = open(os.path.join(p, fn), encoding="utf-8").read()
        if re.search(r"<!(DOCTYPE|ENTITY)", text[:4000]):
            continue
        root = ET.fromstring(text)
        parent = {c: q for q in root.iter() for c in q}
        top = root[0] if len(root) else root
        roots.append(f"{label}/{part}: root bounds={top.get('bounds')} flipped={top.get('geometryFlipped')} "
                     f"layers={sum(1 for e in root.iter() if local(e.tag).endswith('Layer'))}")
        ids = {e.get("id"): e.get("name") for e in root.iter() if e.get("id")}
        if part == "FG":
            n = sum(1 for e in root.iter() if local(e.tag).endswith("Layer"))
            if n > 1:
                fg.append(f"{label}: {n} layers: " + ", ".join(e.get("name") or "?" for e in root.iter()
                                                                 if local(e.tag).endswith("Layer"))[:200])
        for e in root.iter():
            t = local(e.tag)
            if t.endswith("Layer") and e.get("name"):
                for w in re.findall(r"[A-Za-z]+", e.get("name").lower()):
                    layer_kw[w] += 1
            if is_anim(e):
                lay = e
                while lay in parent and not local(lay.tag).endswith("Layer"):
                    lay = parent[lay]
                in_trans = any(local(a.tag) == "LKStateTransition" for a in [lay] + [parent.get(lay)])
                vs = vals(e)
                key = f'{e.get("type")}:{e.get("keyPath")}'
                kt = e.find("{*}keyTimes")
                tf = e.find("{*}timingFunctions")
                ex = (f'{label}/{part} [{lay.get("name")}] dur={e.get("duration")} rev={e.get("autoreverses")} '
                      f'calc={e.get("calculationMode")} n={len(vs)} kt={"y" if kt is not None else "n"} '
                      f'tf={"y" if tf is not None else "n"} off={e.get("timeOffset")} vals={fmt_vals(vs)}')
                if e.get("type") == "CASpringAnimation":
                    ex += f' mass={e.get("mass")} stiff={e.get("stiffness")} damp={e.get("damping")} vel={e.get("initialVelocity") or e.get("velocity")}'
                if not in_trans:
                    anim_ex[key].append(ex)
                if e.get("keyPath") == "opacity" and len(vs) >= 6:
                    try:
                        fv = [float(x) for x in vs]
                        maj = collections.Counter(fv).most_common(1)[0][0]
                        odd = [i for i, x in enumerate(fv) if x != maj]
                        blinks.append(f"{label}/{part} [{lay.get('name')}] n={len(fv)} majority={maj} "
                                      f"odd_idx={odd[:12]} odd_vals={[fv[i] for i in odd[:6]]} dur={e.get('duration')} "
                                      f"rev={e.get('autoreverses')} calc={e.get('calculationMode')}")
                    except ValueError:
                        pass
                if e.get("keyPath") == "contents":
                    contents_anim.append(f"{label}/{part} [{lay.get('name')}] frames={len(vs)} dur={e.get('duration')} "
                                         f"calc={e.get('calculationMode')} first={vs[:2]}")
            if t == "compositingFilter":
                lay = parent.get(e)
                comp_c[e.get("filter")] += 1
                if e.get("filter") != "normalBlendMode":
                    comp.append(f"{label}/{part} [{lay.get('name') if lay is not None else '?'}] {e.get('filter')} "
                                f"opacity={lay.get('opacity') if lay is not None else '?'}")
            if t == "CAEmitterLayer":
                attrs = {k: e.get(k) for k in ("emitterShape", "emitterMode", "renderMode", "emitterSize",
                                               "emitterPosition", "birthRate", "lifetime", "seed", "preservesDepth")
                         if e.get(k) is not None}
                cells = []
                for c in e.iter():
                    if local(c.tag) == "CAEmitterCell":
                        ca = {k: v for k, v in c.attrib.items() if k not in ("id", "name", "enabled")}
                        img = c.find(".//{*}CGImage")
                        ca["img"] = img.get("src") if img is not None else None
                        cells.append(ca)
                emit.append(f"{label}/{part} [{e.get('name')}] {attrs}\n      cells({len(cells)}): {cells[:2]}")
            if t == "LKStateSetValue":
                kp = e.get("keyPath")
                setv_kp[kp] += 1
                st = parent[parent[e]].get("name") if parent.get(e) is not None and parent.get(parent[e]) is not None else "?"
                v = e.find("{*}value")
                setv.append((label, part, ids.get(e.get("targetId"), e.get("targetId")), kp, st,
                             v.get("value") if v is not None else None))
            if t == "LKStateTransition":
                els = [c for c in e.iter() if local(c.tag) == "LKStateTransitionElement"]
                if els:
                    a = [x for x in e.iter() if is_anim(x)]
                    trans.append(f"{label}/{part} {e.get('fromState')}->{e.get('toState')} elements={len(els)} "
                                 + "; ".join(sorted({f'{x.get("type")}:{x.get("keyPath")} dur={x.get("duration")} '
                                                     f'mass={x.get("mass")} stiff={x.get("stiffness")} damp={x.get("damping")}'
                                                     for x in a}))[:300])
            if t in ("filters", "backgroundFilters"):
                lay = parent.get(e)
                for c in e:
                    filt.append(f"{label}/{part} [{lay.get('name') if lay is not None else '?'}] {t}:{c.get('type') or c.get('filter')} "
                                + " ".join(f"{local(x.tag)}={x.get('value')}" for x in c)[:200] + " " + str(dict(c.attrib))[:160])

print("== canvas (root) per bundle ==")
seen = set()
for r in roots:
    k = r.split(":")[1]
    print(" ", r)
print("\n== Foreground .ca with content ==")
for x in fg:
    print(" ", x)
print("\n== animation examples per type:keyPath (max 6 each) ==")
for k, exs in sorted(anim_ex.items(), key=lambda x: -len(x[1])):
    print(f"[{k}] x{len(exs)}")
    for x in exs[:6]:
        print("   ", x)
print("\n== opacity keyframe lists with >= 6 values (blink / flicker patterns) ==")
for x in blinks[:40]:
    print("  ", x)
print("\n== contents (frame) animations ==")
for x in contents_anim:
    print("  ", x)
print("\n== compositingFilter counts ==", dict(comp_c))
for x in comp[:40]:
    print("  ", x)
print("\n== filters ==")
for x in filt[:30]:
    print("  ", x)
print("\n== emitters ==")
for x in emit[:16]:
    print("  ", x)
print("\n== state set values: keyPath counts ==", dict(setv_kp))
by = collections.defaultdict(dict)
for label, part, lay, kp, st, v in setv:
    by[(label, part, lay, kp)][st] = v
for (label, part, lay, kp), m in list(by.items())[:80]:
    print(f"   {label}/{part} [{lay}] {kp}: " + ", ".join(f"{s}={v}" for s, v in m.items()))
print("\n== transitions carrying animations ==")
for x in trans[:40]:
    print("  ", x)
print("\n== frequent layer-name words ==")
print(", ".join(f"{w}:{n}" for w, n in layer_kw.most_common(120)))
