"""The Mobile Homebase as one model, in space and as its hangar (the remake's stations.json model and interiors.json room,
Modding/README.md): EVERSPACE 2's carrier level POI_HomebaseCarrier_001 (Maps/POIs), the carrier SM_Warship_010 with the hall
inside it where the player lands: its interior, platform and detailing meshes, the six landing pads, the containers and
hangar props, the robots (in their bind pose). It docks EVERSPACE 2's way (World.Es2Dock): the ship flies in through the
hall's open side onto its pad (the level's BP_DockableStation, stations.dock_room) and takes off from it; the other pads hold
parked ships. No Space Lounge (the casino stays scenery).

The level's actors are read from FModel's .json of the map (its StaticMeshComponents / SkeletalMeshComponents without a
parent, their Unreal transforms applied to the meshes); the meshes the user's FModel export lacked come from the export
mode of es2_re's ShaderDump (CUE4Parse), into the same folder."""
import json, math, os, re
import numpy as np
import warships
from warships import read_prims, split_prims, material_entries
import glbtool

MAP = 'Maps/POIs/POI_HomebaseCarrier_001.json'
SCALE = 2.8                   # ES2's 36 m pads hold its ~18 m fighters; x2.8 they take a GoF2 hull (~47 m) about as full
SKIP = ('HLOD', 'SK_Homebase_Turret', 'SK_Turret_', 'SM_Warship_010_Caustics', 'SM_Sphere')
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
    import jobs
    out = rel[:-4] + '_room2.png'
    with jobs.once(('room2', out)):
        if not jobs.exists(os.path.join(mod, out)):
            jobs.wait(os.path.join(mod, rel))   # (the map itself may still be on its way: warships._save)
            a = np.array(Image.open(os.path.join(mod, rel)).convert('RGBA')).astype(np.float32)
            a[..., :3] *= k; a[..., 3] *= smooth
            jobs.write_image(os.path.join(mod, out), a.astype(np.uint8))
    return out


def build(src, mod, log=print):
    """Writes warships/homebase_room.glb, the carrier whole (its hull SM_Warship_010 around the hall): the Homebase's model in
    space and its hangar both, docked EVERSPACE 2's way (stations.dock_room: its BP_DockableStation on the player's pad);
    returns (interiors.json's hangar room, the station's model fields: model, modelSize, materials, and 'centre', the
    model's middle in glTF metres, for its engines)."""
    prims, pads = [], []
    missing = set()
    for mesh, loc, rot, scale in _actors(src):
        p = os.path.join(src, mesh + '.glb')
        if not os.path.exists(p): missing.add(mesh); continue
        prims += _placed(read_prims(p), loc, rot, scale)
        if 'Landingpad' in mesh: pads.append(loc)
    if missing: log(f'  Homebase hangar: missing {sorted(missing)} (export them with es2_re/ShaderDump export)')
    if len(pads) < 2: log('  Homebase hangar: no landing pads found'); return None, None

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

    prims = [x for x in prims if 'Forcefield' not in x[2]]   # the openings' film: only washed the view of space out

    # The plating's vertex-colour tints (BaseColorVtxR / G / B): their switch is the parent material's, which the export's
    # resolved form doesn't carry, so they are switched on here for every material that has them.
    for n in {x[2] for x in prims}:
        m = warships.es2mat.resolve(n)
        if ('BaseColorVtxR' in m['col'] and 'UseVertexColorMasks' not in m['sw']
                and any(m['cola'].get('BaseColorVtx' + c, 1.0) >= 0.5 for c in 'RGB')):
            m['sw']['UseVertexColorMasks'] = True

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
        m = warships.es2mat.resolve(mats_used[e['material']][0])
        kind = warships.es2mat.classify(m)
        # The hall's plating is nearly all polished metal (Plating_101's metal ~0.95): ES2 lights it with its reflection
        # captures, the remake's room has none, so it came out black.
        if e.get('metallicSmoothness'): e['metallicSmoothness'] = _less_metal(mod, e['metallicSmoothness'])
        elif e.get('metallic', 0.0) > 0.5: e['metallic'] = round(e['metallic'] * 0.1, 3)
        # (the structures' colour, saturate(curvature x 2 x tint), is baked by warships.material_entries)
        if kind == 'glass':
            # their compiled shaders: the windows (M_ShipModules_Glass_Parent) WindowColor at 0.1 + grunge + fresnel, the
            # casino's glass (M_Structures_Glass_Parent) Color at BaseOpacity (0) + scratches + fresnel: nearly clear, a
            # pale cyan tint, the URP glass's own reflection standing in for the fresnel
            c = m['col'].get('WindowColor') or m['col'].get('Color') or [0.8, 0.95, 1.0]
            e.update({'color': [round(v, 3) for v in c], 'metallic': 0.0, 'smoothness': 0.95,
                      'opacity': 0.12 if 'WindowColor' in m['col'] else 0.06})
        elif kind == 'decal':
            # M_Vehicles_Decals_Parent: the decal atlas' colour (over a neutral bake) cut out by its alpha
            d = warships.tex('colour', 'T_Vehicles_Decals_001_C_A', 'rgb', ('T_Vehicles_Decals_001_C_A', 3))
            if d: e.update({'diffuse': d, 'alphaClip': 0.5, 'color': [1.0, 1.0, 1.0], 'metallic': 0.0, 'smoothness': 0.3})
        # the landing pads' dark colour map (a quarter grey) under a 0.35 tint: black under the room's one light
        if 'LandingPads' in e.get('diffuse', ''): e['color'] = [round(min(1.0, c * 1.8), 3) for c in e['color']]
    tris = sum(len(i) // 3 for _, i, _ in out)
    log(f'  Homebase: {len(prims)} meshes, {tris} triangles, {len(materials)} materials, {len(pads)} pads, '
        f'{os.path.getsize(p) // (1 << 20)} MB')

    def scaled(v, k=SCALE): return [round(-v[0] * k, 2), round(v[1] * k, 2), round(v[2] * k, 2)]   # glTFast mirrors x
    import stations
    stations.configure(src, mod)
    docks = stations.Level(None, MAP).docks()
    if not docks: log('  Homebase hangar: no BP_DockableStation in the level'); return None, None
    room = {'id': 'homebase_hangar', 'type': 'hangar', 'model': rel, 'scale': SCALE, 'materials': materials,
            **stations.dock_room(docks[0], [], lambda v: np.array(_g(v)))}
    room['markers'].update({k: scaled(v) for k, v in marks.items() if k.startswith('parked')})   # the other pads
    room.update({'fov': 23, 'far': 4000})
    allp = np.concatenate([a['POSITION'] for a, _, _ in out])
    mn, mx = allp.min(0), allp.max(0)
    model = {'model': rel, 'modelSize': round(float((mx - mn).max()) * SCALE / 0.05), 'materials': materials,
             'centre': ((mn + mx) / 2).tolist()}
    return room, model
