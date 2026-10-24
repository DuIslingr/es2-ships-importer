"""The Mobile Homebase's own hangar and casino as the remake's interiors.json rooms (Modding/README.md, "Custom hangars and
bars"): EVERSPACE 2's carrier level POI_HomebaseCarrier_001 (Maps/POIs), the hall inside SM_Warship_010 where the player
lands: its interior, platform and detailing meshes, the six landing pads, the containers and hangar props, the robots (in
their bind pose), the force fields along both long sides. One model serves both rooms: the hangar looks at the landing pads,
the bar at the casino at the back of the hall.

The level's actors are read from FModel's .json of the map (its StaticMeshComponents / SkeletalMeshComponents without a
parent, their Unreal transforms applied to the meshes); the meshes the user's FModel export lacked come from the export
mode of es2_re's ShaderDump (CUE4Parse), into the same folder. Markers are glTF nodes named as interiors.json wants them
(the pads' tops, the gate in the side force field, the cameras, the light, the casino's visitors)."""
import json, math, os, re
import numpy as np
import warships
from warships import read_prims, split_prims, material_entries
import glbtool

MAP = 'Maps/POIs/POI_HomebaseCarrier_001.json'
SCALE = 2.8                   # ES2's 36 m pads hold its ~18 m fighters; x2.8 they take a GoF2 hull (~47 m) about as full
BAR_SCALE = 7.5               # the casino as the bar: the game's visitor billboards are ~26 m tall and ~30 m wide (the
                              # original bars' scale), a person in ES2 1.8 m; at the hangar's x2.8 they stuck through walls
VISITOR_HALF_WIDTH = 2.0      # the billboard's half width and height, in the casino's own metres (x BAR_SCALE in the game)
VISITOR_HEIGHT = 3.5
SKIP = ('SM_Warship_010.', 'HLOD', 'SK_Homebase_Turret', 'SK_Turret_', 'SM_Warship_010_Caustics', 'SM_Sphere')
PLAYER_PAD = (12444, 4)      # the pad BP_DockableStation_C_1 rides on (Unreal cm)


def _rot(p, y, r):
    """FRotationMatrix's rows (Unreal: X forward, Y right, Z up; a point v goes to v @ M)."""
    p, y, r = (math.radians(v) for v in (p, y, r))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return np.array([[cp * cy, cp * sy, sp],
                     [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
                     [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]], np.float32)


def _placed(prims, loc, rot, scale):
    """The export's glTF metres (X, Z, Y of Unreal) -> Unreal cm, the component's transform, back to glTF metres."""
    M = _rot(*rot)
    s = np.array(scale, np.float32)
    t = np.array(loc, np.float32)
    out = []
    for a, tri, name in prims:
        a = dict(a)
        p = a['POSITION'][:, [0, 2, 1]] * 100.0
        p = (p * s) @ M + t
        a['POSITION'] = (p[:, [0, 2, 1]] / 100.0).astype(np.float32)
        for k in ('NORMAL', 'TANGENT'):
            if k not in a: continue
            v = a[k][:, :3][:, [0, 2, 1]]
            v = (v / s) @ M
            v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-8)
            v = v[:, [0, 2, 1]]
            a[k] = np.hstack([v, a[k][:, 3:]]).astype(np.float32) if k == 'TANGENT' else v.astype(np.float32)
        out.append((a, tri, name))
    return out


def _g(ue_cm):
    """Unreal cm -> glTF metres (a marker node's translation)."""
    return [ue_cm[0] / 100.0, ue_cm[2] / 100.0, ue_cm[1] / 100.0]


def _actors(src):
    d = json.load(open(os.path.join(src, MAP), encoding='utf-8-sig'))
    out = []
    for e in d:
        if e.get('Type') not in ('StaticMeshComponent', 'SkeletalMeshComponent'): continue
        pr = e.get('Properties', {})
        if pr.get('AttachParent'): continue           # the pads' parked fighters and grav pads, the lights' spheres
        mesh = (pr.get('StaticMesh') or pr.get('SkeletalMesh') or pr.get('SkinnedAsset') or {}).get('ObjectPath')
        if not mesh or not mesh.startswith('/Game/') or any(k in mesh for k in SKIP): continue
        l = pr.get('RelativeLocation') or {}; r = pr.get('RelativeRotation') or {}; s = pr.get('RelativeScale3D') or {}
        out.append((mesh.split('.')[0].replace('/Game/', ''), [l.get(k, 0.0) for k in 'XYZ'],
                    [r.get(k, 0.0) for k in ('Pitch', 'Yaw', 'Roll')], [s.get(k, 1.0) for k in 'XYZ']))
    return out


def _floor_at(prims, x, y, below, above=-1e9):
    """The highest surface (glTF metres, its y) under the Unreal point (x, y) cm between 'above' and 'below' metres: a
    vertical ray through every triangle facing up."""
    best = None
    px, pz = x / 100.0, y / 100.0
    for a, tri, _ in prims:
        P = a['POSITION']; t = tri.reshape(-1, 3)
        A, B, C = P[t[:, 0]], P[t[:, 1]], P[t[:, 2]]
        # barycentric in the glTF x / z plane
        d = (B[:, 2] - C[:, 2]) * (A[:, 0] - C[:, 0]) + (C[:, 0] - B[:, 0]) * (A[:, 2] - C[:, 2])
        ok = np.abs(d) > 1e-9
        if not ok.any(): continue
        w1 = ((B[:, 2] - C[:, 2]) * (px - C[:, 0]) + (C[:, 0] - B[:, 0]) * (pz - C[:, 2])) / np.where(ok, d, 1)
        w2 = ((C[:, 2] - A[:, 2]) * (px - C[:, 0]) + (A[:, 0] - C[:, 0]) * (pz - C[:, 2])) / np.where(ok, d, 1)
        w3 = 1 - w1 - w2
        hit = ok & (w1 >= 0) & (w2 >= 0) & (w3 >= 0)
        if not hit.any(): continue
        h = w1[hit] * A[hit, 1] + w2[hit] * B[hit, 1] + w3[hit] * C[hit, 1]
        n = np.cross(B[hit] - A[hit], C[hit] - A[hit])
        up = np.abs(n[:, 1]) > 0.7 * np.linalg.norm(n, axis=1)
        h = h[up & (h < below) & (h > above)]
        if h.size: best = max(best, float(h.max())) if best is not None else float(h.max())
    return best


def _less_metal(mod, rel, k=0.1, smooth=0.6):
    """A metallicSmoothness map with a tenth of its metal and 60 % of its smoothness: ES2 lights this polished hall with
    reflection captures; the remake's room reflects black space instead (checked against a Blender render of the room)."""
    from PIL import Image
    out = rel[:-4] + '_room2.png'
    if not os.path.exists(os.path.join(mod, out)):
        a = np.array(Image.open(os.path.join(mod, rel)).convert('RGBA')).astype(np.float32)
        a[..., :3] *= k; a[..., 3] *= smooth
        Image.fromarray(a.astype(np.uint8)).save(os.path.join(mod, out), optimize=True)
    return out


def _structure_colour(mod, rel, tint):
    """ES2's structure base colour, as its shader computes it (MI_Structures_PortableHomebase_Parent's base-pass pixel
    shader, read with es2_re/ShaderDump): saturate(C x 2 x tint) in linear light, C the masks texture's colour channel (linear
    data), tint the vertex-colour-chosen BaseColor (sRGB parameter). Baked per tint into a colour map: Unity would read the
    channel as sRGB and has no saturate for a colour above 1, so a 'color' can't do it."""
    from PIL import Image
    key = '%02x%02x%02x' % tuple(int(round(c * 255)) for c in tint[:3])
    out = re.sub(r'\.png$', f'_x2_{key}.jpg', rel)
    p = os.path.join(mod, out)
    if not os.path.exists(p):
        im = Image.open(os.path.join(mod, rel))
        a = np.asarray(im.convert('RGBA' if im.mode in ('RGBA', 'LA') else 'RGB')).astype(np.float32) / 255.0
        lin = np.clip(a[..., :1] * 2.0 * (np.array(tint[:3], np.float32) ** 2.2), 0.0, 1.0)
        rgb = (lin ** (1 / 2.2) * 255.0 + 0.5).astype(np.uint8)
        if a.shape[2] == 4:
            out = out[:-4] + '.png'; p = os.path.join(mod, out)
            Image.fromarray(np.dstack([rgb, (a[..., 3:] * 255).astype(np.uint8)])).save(p, optimize=True)
        else:
            Image.fromarray(rgb).save(p, quality=92)
    return out


def _visible_spots(prims, cam, target, floor, fov_deg, n=6, aspect=16 / 9):
    """Where the bar's visitors stand (glTF metres): points of the lounge floor itself (no table or counter on them) in the
    camera's view, 12-38 m from it and in front of the facade, whose feet and head the camera sees and whose billboard
    (VISITOR_HALF_WIDTH either side, VISITOR_HEIGHT up) no wall or furniture cuts (rays against the casino's triangles),
    spread across the screen. The guessed spots left some behind the facade's side panels."""
    tri = []
    for a, t, _ in prims:
        P = a['POSITION'].astype(np.float64); T = t.reshape(-1, 3)
        A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        c = (A + B + C) / 3
        keep = (c[:, 0] > -5) & (c[:, 0] < 90) & (np.abs(c[:, 2]) < 80) & (c[:, 1] > floor - 5) & (c[:, 1] < floor + 45)
        if keep.any(): tri.append((A[keep], B[keep], C[keep]))
    A = np.concatenate([x[0] for x in tri]); B = np.concatenate([x[1] for x in tri]); C = np.concatenate([x[2] for x in tri])
    E1, E2 = B - A, C - A
    N = np.cross(E1, E2)

    def blocked(o, p):
        d = p - o; L = np.linalg.norm(d); d = d / L
        h = np.cross(d, E2); det = np.einsum('ij,ij->i', E1, h)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
        s = o - A
        u = np.einsum('ij,ij->i', s, h) * inv
        q = np.cross(s, E1)
        v = (q @ d) * inv
        tt = np.einsum('ij,ij->i', E2, q) * inv
        return bool((ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > 0.05) & (tt < L - 0.05)).any())

    def floor_under(x, z):
        # the highest upward surface under (x, z) below 3 m over the floor
        d = np.array([0.0, -1.0, 0.0]); o = np.array([x, floor + 3.0, z])
        h = np.cross(d, E2); det = np.einsum('ij,ij->i', E1, h)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
        s = o - A
        u = np.einsum('ij,ij->i', s, h) * inv
        q = np.cross(s, E1)
        v = (q @ d) * inv
        tt = np.einsum('ij,ij->i', E2, q) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > 0)
        up = np.abs(N[:, 1]) > 0.7 * np.linalg.norm(N, axis=1)
        hit &= up
        return float(o[1] - tt[hit].min()) if hit.any() else None

    cam = np.array(cam, np.float64); fwd = np.array(target, np.float64) - cam; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 1.0, 0.0]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    tv = math.tan(math.radians(fov_deg / 2)) * 0.8; th = tv * aspect * 0.8
    cands = []
    for x in np.arange(20.0, 78.0, 2.0):
        for z in np.arange(-50.0, 52.0, 2.0):
            h = floor_under(x, z)
            if h is None or abs(h - floor) > 0.4: continue
            p = np.array([x, h, z]); d = p - cam; dist = float(np.linalg.norm(d))
            if not 12.0 <= dist <= 38.0 or x < 40.0: continue   # (x < 40: behind the lounge, at the facade)
            f = d @ fwd
            if f <= 0 or abs(d @ right) / f > th or abs((p + [0, 1.1, 0] - cam) @ up) / f > tv: continue
            if blocked(cam, p + [0, 0.15, 0]) or blocked(cam, p + [0, 2.0, 0]): continue
            # the billboard faces the camera: nothing along its width at the figure's heights, nothing over its top
            if any(blocked(p + [0, hh, 0], p + [0, hh, 0] + sg * VISITOR_HALF_WIDTH * right)
                   for hh in (0.3, 1.0, 1.8, 2.8) for sg in (-1, 1)): continue
            if blocked(p + [0, 0.3, 0], p + [0, VISITOR_HEIGHT, 0]): continue
            cands.append((p, (d @ right) / f))
    if not cands: return []
    # Spread across the screen: the visitors' billboards are taller than a person here, so one standing in front of
    # another along the camera's line hid it. Each pick is the spot farthest across the screen from those taken (and at
    # least 6 m from them), the first the one nearest the view's centre.
    picks = [min(cands, key=lambda c: abs(c[1]))]
    while len(picks) < n:
        rest = [c for c in cands if min(np.linalg.norm(c[0] - q[0]) for q in picks) >= 2.2 * VISITOR_HALF_WIDTH]
        if not rest: break
        best = max(rest, key=lambda c: (min(abs(c[1] - q[1]) for q in picks), np.linalg.norm(c[0] - cam)))
        if min(abs(best[1] - q[1]) for q in picks) < 0.06: break
        picks.append(best)
    return [[round(float(c), 3) for c in p] for p, _ in picks]


def build(src, mod, log=print):
    """Writes warships/homebase_room.glb; returns interiors.json's two rooms (the hangar, the casino as the bar)."""
    prims, pads = [], []
    missing = set()
    for mesh, loc, rot, scale in _actors(src):
        p = os.path.join(src, mesh + '.glb')
        if not os.path.exists(p): missing.add(mesh); continue
        prims += _placed(read_prims(p), loc, rot, scale)
        if 'Landingpad' in mesh: pads.append(loc)
    if missing: log(f'  Homebase hangar: missing {sorted(missing)} (export them with es2_re/ShaderDump export)')
    if len(pads) < 2: log('  Homebase hangar: no landing pads found'); return []

    # The pads' tops: the pad's landing surface, measured on the placed pads themselves.
    def pad_top(loc):
        h = _floor_at(prims, loc[0], loc[1], below=loc[2] / 100.0 + 20.0)
        return h if h is not None else loc[2] / 100.0 + 12.35
    pads.sort(key=lambda l: (abs(l[0] - PLAYER_PAD[0]) + abs(l[1] - PLAYER_PAD[1])))
    marks = {}
    top0 = pad_top(pads[0])
    marks['pad'] = [pads[0][0] / 100.0, top0, pads[0][1] / 100.0]
    for k, l in enumerate(pads[1:], 1):
        marks[f'parked_{k}'] = [l[0] / 100.0, pad_top(l), l[1] / 100.0]

    # The flights' gate: the middle of the force field on the hall's -Y side, the way out 150 m beyond it.
    field = [a['POSITION'] for a, _, n in prims if 'Forcefield' in n]
    if field:
        f = np.concatenate(field); f = f[f[:, 2] < 0]
        gx, gy, gz = float((f[:, 0].min() + f[:, 0].max()) / 2), float(top0 + 25.0), float(f[:, 2].min())
        span = [float(f[:, 1].min()), float(f[:, 1].max())]
    else:
        gx, gy, gz, span = marks['pad'][0], top0 + 25.0, -114.0, [top0, top0 + 50.0]
    marks['gate'] = [gx, gy, gz]
    marks['gate_out'] = [gx, gy, gz - 150.0]

    # The hangar's view: from the hall's middle toward the casino end, above the deck, at the player's pad.
    px, py, pz = marks['pad']
    marks['camera'] = [px - 52.0, py + 17.0, pz - 40.0]
    marks['camera_target'] = [px, py + 4.0, pz]
    marks['light'] = [px - 40.0, py + 45.0, pz - 30.0]

    # The casino (Unreal x 3..76 m at the hall's back): a trapezoid lounge floor, stairs down either side, the round fish tank
    # at its open end toward the hangar (x ~59 m), the casino's facade with its name sign behind the lounge. Placed from
    # renders of the room (es2_re/homebase/render_room.py, 'top' for the plan): the camera beside the tank, raised, looking
    # over the lounge at the facade; the visitors on the lounge floor (its height measured under each spot).
    floor = _floor_at(prims, 4300, -1000, below=-10.0, above=-30.0)   # (below the tables and the bar counter)
    vis, bar = [], None
    if floor is not None:
        bar = {'bar_camera': [71.4, floor + 11.8, -21.4], 'bar_camera_target': [42.9, floor + 3.6, 3.6],
               'bar_camera_start': [73.2, floor + 15.4, 0.0], 'bar_camera_start_target': [45.0, floor + 1.8, 0.0],
               'bar_light': [46.0, floor + 16.0, 0.0]}
        vis = _visible_spots(prims, bar['bar_camera'], bar['bar_camera_target'], floor, 60.0)
        for k, v in enumerate(vis, 1): marks[f'visitor_{k}'] = v
        if not vis: bar = None

    prims = [x for x in prims if 'Forcefield' not in x[2]]   # the openings' film: only washed the view of space out

    # The plating's vertex-colour tints (BaseColorVtxR / G / B): their switch is the parent material's, which the export's
    # resolved form doesn't carry, so they are switched on here for every material that has them.
    for n in {x[2] for x in prims}:
        m = warships.es2mat.resolve(n)
        if 'BaseColorVtxR' in m['col'] and 'UseVertexColorMasks' not in m['sw']: m['sw']['UseVertexColorMasks'] = True

    mats_used = {}
    out = split_prims('hb', prims, mats_used, layered=True)
    w = glbtool.Writer()
    root = w.node('homebase')
    w.node('homebase_mesh', mesh=w.mesh('homebase', out), parent=root)
    rel = 'warships/homebase_room.glb'
    p = os.path.join(mod, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    w.write(p)
    materials = material_entries('hb', mats_used)
    for e in materials:
        # The hall's plating is nearly all polished metal (Plating_101's metal ~0.95): ES2 lights it with its reflection
        # captures, the remake's room has none, so it came out black.
        if e.get('metallicSmoothness'): e['metallicSmoothness'] = _less_metal(mod, e['metallicSmoothness'])
        if re.search(r'_c\d+a?\.png$', e.get('diffuse', '')) and e.get('color'):
            e['diffuse'] = _structure_colour(mod, e['diffuse'], e['color']); e['color'] = [1.0, 1.0, 1.0]
        if e.get('opacity') == 0.6: e['opacity'] = 0.18   # the windows: clear, space behind them
        # the landing pads' dark colour map (a quarter grey) under a 0.35 tint: black under the room's one light
        if 'LandingPads' in e.get('diffuse', ''): e['color'] = [round(min(1.0, c * 1.8), 3) for c in e['color']]
    tris = sum(len(i) // 3 for _, i, _ in out)
    log(f'  Homebase hangar: {len(prims)} meshes, {tris} triangles, {len(materials)} materials, {len(pads)} pads, '
        f'{len(vis)} casino spots, {os.path.getsize(p) // (1 << 20)} MB')

    def scaled(v, k=SCALE): return [round(-v[0] * k, 2), round(v[1] * k, 2), round(v[2] * k, 2)]   # glTFast mirrors x
    hangar = {'id': 'homebase_hangar', 'type': 'hangar', 'model': rel, 'scale': SCALE, 'materials': materials,
              'markers': {k: scaled(v) for k, v in marks.items() if not k.startswith('visitor')},
              'fov': 50, 'far': 4000, 'ambient': [0.62, 0.64, 0.7], 'lightIntensity': 1.6,
              'cruise': round(40.0 * SCALE), 'gateSpan': [round(max(span[0], top0 + 5.0) * SCALE), round(span[1] * SCALE)]}
    rooms = [hangar]
    if bar:
        markers = {k[4:]: scaled(v, BAR_SCALE) for k, v in bar.items()}
        markers.update({k: scaled(v, BAR_SCALE) for k, v in marks.items() if k.startswith('visitor')})
        rooms.append({'id': 'homebase_casino', 'type': 'bar', 'model': rel, 'scale': BAR_SCALE, 'materials': materials,
                      'markers': markers, 'fov': 60, 'far': 10000, 'ambient': [0.26, 0.23, 0.3], 'lightIntensity': 0.7})
    return rooms
