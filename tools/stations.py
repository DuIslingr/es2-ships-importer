"""EVERSPACE 2's stations for the sectors (sectors.py): each station's exterior as its stations.json model, and its landing pad
as its own hangar (interiors.json, Modding/README.md "Custom hangars and bars").

ES2 builds a station in its location's level (Maps/Locations/<location>.json) from many structure pieces (Assets/Environment/
Structures and the like) around one or more BP_DockableStation actors, each with its StationID (DataFiles/dockables.csv).
Docked, ES2 shows the ship on the dockable's pad (its DockingTransformPreview) from its spring-armed CineCamera, and takes
off along its TakeOffTransformPreview.

- The exterior: the structure pieces linked to the docks (single linkage of their pivots, LINK apart, at most REACH from the
  first dock), placed as the level places them (StaticMeshComponents and instanced ones, every attach chain resolved).
- The hangar: the pieces within PAD_REACH of the main dock (the location's first trading dockable), ES2's own view of it:
  'pad' the ship's spot, 'camera' / 'camera_target' the dockable's camera on its spring arm looking at the pad, 'gate' /
  'gate_out' its take-off path, other landing pads near it as parked slots.

The level's transforms: FModel's ObjectPath ".N" of a reference is the level's export d[N]; a component's world transform is
its relative one through its AttachParent chain (an actor's place is its RootComponent's). The meshes FModel's export lacks
come from es2_re's ShaderDump export (tools/shaders) of the list asset_list() writes."""
import json, math, os
import numpy as np

SRC = MOD = None
LOG = print

LINK = 30000.0          # cm: pieces this close to a piece of the station are part of it
REACH = 120000.0        # cm: no piece farther than this from the first dock
PAD_REACH = 25000.0     # cm: the hangar's pieces round the main dock
SCALE = 2.8             # ES2 metres -> the remake's (the Homebase hangar's: ES2's ~18 m fighters to GoF2's ~47 m hulls)
# What a station is built of: ES2's structure and prop meshes (not its asteroids, landscapes, traffic, drones, HLOD stand-ins)
KEEP = ('/Environment/Structures/', '/Environments/Structures/', '/Environment/Props/', '/Environment/Stations/')
SKIP = ('HLOD', 'Asteroid', 'Landscape', '_Blockout', 'SM_Sphere', 'Ship_Wrecks', 'Background', 'Forcefield', 'Caustics',
        'Hologram', 'Billboard', 'Decal')


def configure(src, mod, log=print):
    global SRC, MOD, LOG
    SRC, MOD, LOG = src, mod, log


def _rot(p, y, r):
    """FRotationMatrix's rows (Unreal: X forward, Y right, Z up; a point v goes to v @ M)."""
    p, y, r = (math.radians(v) for v in (p, y, r))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return np.array([[cp * cy, cp * sy, sp],
                     [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
                     [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]])


def _quat(q):
    """An FQuat as the same row matrix."""
    x, y, z, w = (q.get(k, 0.0) for k in 'XYZW')
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y)],
                     [2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x)],
                     [2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)]])


_bones = {}
def _bone(comp, socket):
    """A skeletal mesh component's bone 'socket' in its reference pose, in the component's frame: (R, t), or None (no bone
    of that name; a mesh socket isn't read)."""
    if not socket or socket == 'None': return None
    pr = comp.get('Properties') or {}
    mesh = ((pr.get('SkeletalMesh') or pr.get('SkinnedAsset') or {}).get('ObjectPath') or '').split('.')[0]
    if not mesh: return None
    key = (mesh, socket)
    if key in _bones: return _bones[key]
    out = None
    try:
        sk = json.load(open(os.path.join(SRC, mesh.replace('/Game/', '') + '_Skeleton.json'), encoding='utf-8-sig'))
        rs = next(e['ReferenceSkeleton'] for e in sk if isinstance(e, dict) and e.get('ReferenceSkeleton'))
        info, pose, names = rs['FinalRefBoneInfo'], rs['FinalRefBonePose'], rs['FinalNameToIndexMap']
        i = names.get(socket)
        R, t = np.eye(3), np.zeros(3)
        while i is not None and 0 <= i < len(pose):
            b = pose[i]
            BR = _quat(b.get('Rotation') or {}); Bt = np.array([(b.get('Translation') or {}).get(a, 0.0) for a in 'XYZ'])
            R, t = R @ BR, t @ BR + Bt
            pi = info[i].get('ParentIndex', -1)
            i = pi if pi >= 0 else None
        if names.get(socket) is not None: out = (R, t)
    except (OSError, ValueError, StopIteration, KeyError):
        pass
    _bones[key] = out
    return out


class Level:
    def __init__(self, location, path=None):
        """A sector location's level (Maps/Locations/<location>.json), or any map by its path under the export."""
        self.d = json.load(open(os.path.join(SRC, path or os.path.join('Maps/Locations', location + '.json')), encoding='utf-8-sig'))
        self.cache = {}

    def ref(self, r):
        if not r: return None
        try: i = int(r.get('ObjectPath', '').rsplit('.', 1)[1])
        except (IndexError, ValueError): return None
        return self.d[i] if 0 <= i < len(self.d) else None

    def world(self, e, depth=0):
        """(R, t, s): a component's world transform (a point v cm -> (v * s) @ R + t)."""
        k = id(e)
        if k in self.cache: return self.cache[k]
        p = e.get('Properties') or {}
        l = p.get('RelativeLocation') or {}; r = p.get('RelativeRotation') or {}; s = p.get('RelativeScale3D') or {}
        out = (_rot(*[r.get(a, 0.0) for a in ('Pitch', 'Yaw', 'Roll')]), np.array([l.get(a, 0.0) for a in 'XYZ']),
               np.array([s.get(a, 1.0) for a in 'XYZ']))
        par = self.ref(p.get('AttachParent'))
        if par is not None and par is not e and depth < 64:
            # attached to a skeletal mesh's socket / bone: the bone's reference pose first (the Homebase's dock rides on its
            # landing pad's "root" bone, turned 90 deg about X)
            bone = _bone(par, p.get('AttachSocketName'))
            if bone is not None:
                BR, Bt = bone
                R, t, sc = out
                out = (R @ BR, t @ BR + Bt, sc)
            PR, Pt, Ps = self.world(par, depth + 1)
            R, t, sc = out
            out = (R @ PR, (t * Ps) @ PR + Pt, sc * Ps)
        self.cache[k] = out
        return out

    def owned(self, actor, name):
        """An actor's component by name (the components of a placed blueprint are its exports with it as Outer)."""
        an = actor.get('Name')
        for e in self.d:
            o = e.get('Outer')
            on = o.get('ObjectName', '') if isinstance(o, dict) else str(o or '')
            if e.get('Name') == name and on.endswith('.' + an + "'"): return e
        return None

    def docks(self):
        """[{id, root (R, t), pad t, camera t, takeoff t}] of the level's BP_DockableStations."""
        out = []
        for e in self.d:
            if e.get('Type') != 'BP_DockableStation_C': continue
            p = e['Properties']
            root = self.ref(p.get('RootComponent'))
            if root is None: continue
            R, t, _ = self.world(root)
            pad = self.owned(e, 'DockingTransformPreview'); off = self.owned(e, 'TakeOffTransformPreview')
            pad_R, pad_t = (self.world(pad)[:2]) if pad is not None else (R, t + np.array([0, 0, 490.0]) @ R)
            off_R, off_t = (self.world(off)[:2]) if off is not None else (R, t + np.array([10000.0, 0, 700.0]) @ R)
            # the camera on its spring arm (BP_DockableStation's defaults: pitch -15, yaw 160, 35 m), at the pad; it looks at
            # the ship + CameraLookAtOffsetZ (-250 cm) in the arm's frame (CameraLookAtShip)
            arm = _rot(-15.0, 160.0, 0.0) @ R
            cam_t = t + np.array([-3500.0, 0.0, 0.0]) @ arm
            look = pad_t + np.array([0.0, 0.0, -250.0]) @ arm
            # the Interact box the ship docks from (TriggerBoxExtent 7000 x 7000 x 3000 cm, 3500 cm above the dock)
            it = self.owned(e, 'Interact0')
            ip = (it or {}).get('Properties') or {}
            loc = ip.get('RelativeLocation') or {'Z': 3500.0}
            zone_t = t + np.array([loc.get('X', 0.0), loc.get('Y', 0.0), loc.get('Z', 0.0)]) @ R
            ext = ip.get('TriggerBoxExtent') or {}
            zone = [ext.get('X', 7000.0), ext.get('Y', 7000.0), ext.get('Z', 3000.0)]
            # TakeOffHeight (500 cm unless the level sets it)
            rise = float(p.get('TakeOffHeight', 500.0))
            out.append({'id': p.get('StationID'), 'R': R, 't': t, 'pad': pad_t, 'padR': pad_R, 'camera': cam_t, 'look': look,
                        'takeoff': off_t, 'takeoffR': off_R, 'zone': zone_t, 'zoneExt': zone, 'rise': rise})
        return out

    def pieces(self):
        """[(mesh path, R, t, s, overrides)] of every structure piece placed in the level (instances one by one); 'overrides':
        the component's OverrideMaterials by slot (a material name, None where the slot keeps the mesh's), or ()."""
        out = []
        for e in self.d:
            ty = e.get('Type')
            if ty not in ('StaticMeshComponent', 'InstancedStaticMeshComponent', 'HierarchicalInstancedStaticMeshComponent'): continue
            p = e.get('Properties') or {}
            m = ((p.get('StaticMesh') or {}).get('ObjectPath') or '').split('.')[0]
            if not m or not any(k in m for k in KEEP) or any(k in m for k in SKIP): continue
            if p.get('bVisible') is False or p.get('bHiddenInGame'): continue
            R, t, s = self.world(e)
            ovr = tuple(_override(o) for o in (p.get('OverrideMaterials') or []))
            if not any(ovr): ovr = ()
            inst = p.get('PerInstanceSMData')
            if inst:
                for i in inst:
                    tm = i.get('TransformData') or {}
                    q = tm.get('Rotation') or {}; tr = tm.get('Translation') or {}; sc = tm.get('Scale3D') or {}
                    IR = _quat(q); It = np.array([tr.get(a, 0.0) for a in 'XYZ']); Is = np.array([sc.get(a, 1.0) for a in 'XYZ'])
                    out.append((m, IR @ R, (It * s) @ R + t, Is * s, ovr))
            else:
                out.append((m, R, t, s, ovr))
        return out


def _override(o):
    """An OverrideMaterials entry's material name: None for an empty slot or one the level makes at runtime (a
    MaterialInstanceDynamic: the blueprints' lamps, the skybox)."""
    n = (o or {}).get('ObjectName', '') if isinstance(o, dict) else ''
    if not n or n.startswith('MaterialInstanceDynamic'): return None
    return n.split("'")[1].split(':')[-1].split('.')[-1] if "'" in n else n


def cluster(pieces, docks):
    """The pieces linked to the docks: single linkage of their pivots (LINK), within REACH of the first dock."""
    if not pieces or not docks: return []
    P = np.array([p[2] for p in pieces])
    near = np.linalg.norm(P - docks[0]['t'], axis=1) < REACH
    taken = np.zeros(len(pieces), bool)
    front = []
    for d in docks:
        hit = near & (np.linalg.norm(P - d['t'], axis=1) < LINK) & ~taken
        taken |= hit; front += list(np.nonzero(hit)[0])
    while front:
        i = front.pop()
        hit = near & ~taken & (np.linalg.norm(P - P[i], axis=1) < LINK)
        taken |= hit; front += list(np.nonzero(hit)[0])
    return [pieces[i] for i in np.nonzero(taken)[0]]


def station_locations():
    """The sectors' station orbits: [(sector, location, GoF2 id)]."""
    import sectors
    out = []
    for k in sectors.SECTOR_KEYS:
        for l in sectors.spec_of(k)['locations']:
            if l[2] is not None and 'nodock' not in str(l[2]) and os.path.exists(os.path.join(SRC, 'Maps/Locations', l[0] + '.json')):
                out.append((k, l[0], l[1]))
    return out


def asset_list(path):
    """Writes the meshes the stations need that the export lacks (one /Game/ path a line, for tools/shaders' export)."""
    need = set()
    for _, lid, _ in station_locations():
        lv = Level(lid)
        for m, *_ in cluster(lv.pieces(), lv.docks()):
            if not os.path.exists(os.path.join(SRC, m.replace('/Game/', '') + '.glb')): need.add(m)
    with open(path, 'w') as f:
        f.write('# What the stations need beyond a plain FModel export (tools/stations.py). tools/shaders: export <this file> <Exports> all\n')
        for m in sorted(need): f.write(m + '\n')
    return need


# ---- building ------------------------------------------------------------------------------------------------------------

_prims = {}
def _mesh(m):
    """A mesh's primitives (warships.read_prims), once."""
    import jobs, warships
    with jobs.once(('stmesh', m)):
        if m not in _prims:
            p = os.path.join(SRC, m.replace('/Game/', '') + '.glb')
            _prims[m] = warships.read_prims(p) if os.path.exists(p) else None
    return _prims[m]


_boxes = {}
def _corners(m):
    """A mesh's bounding box corners in Unreal cm (a piece's bounds are its mesh's corners through its transform: every
    vertex through every piece's transform took most of a big station's time)."""
    if m not in _boxes:
        p = np.concatenate([a['POSITION'] for a, _, _ in _mesh(m)]).astype(np.float64)[:, [0, 2, 1]] * 100.0
        lo, hi = p.min(0), p.max(0)
        _boxes[m] = np.array([[(lo, hi)[i >> k & 1][k] for k in range(3)] for i in range(8)])
    return _boxes[m]


_slot_names = {}
def _slots(m):
    """A mesh's material slots: their default materials' names (the mesh's .json StaticMaterials), in slot order."""
    if m not in _slot_names:
        out = []
        try:
            for e in json.load(open(os.path.join(SRC, m.replace('/Game/', '') + '.json'), encoding='utf-8-sig')):
                for sm in (e.get('Properties') or {}).get('StaticMaterials') or []:
                    n = (sm.get('MaterialInterface') or {}).get('ObjectName', '')
                    out.append(n.split("'")[1] if "'" in n else n)
                if out: break
        except (OSError, ValueError): pass
        _slot_names[m] = out
    return _slot_names[m]


def _variant(m, ovr):
    """A mesh's primitives with a piece's OverrideMaterials put in (a slot's default material renamed to the override; one
    the export lacks is left as it was)."""
    import es2mat
    prims = _mesh(m)
    if not ovr: return prims
    slots = _slots(m)
    swap = {slots[k]: o for k, o in enumerate(ovr) if o and k < len(slots) and es2mat._load(o) is not None}
    return [(a, tri, swap.get(name, name)) for a, tri, name in prims]


def _gltf(v):
    """Unreal cm -> glTF metres (x, z, y)."""
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1) / 100.0


def _place(prims, R, t, s, centre):
    """A piece's primitives into the station's frame: the export's glTF metres -> Unreal cm, the piece's transform, less the
    station's centre, back to glTF metres."""
    out = []
    for a, tri, name in prims:
        a = dict(a)
        p = a['POSITION'].astype(np.float64)[:, [0, 2, 1]] * 100.0
        a['POSITION'] = _gltf((p * s) @ R + t - centre).astype(np.float32)
        for k in ('NORMAL', 'TANGENT'):
            if k not in a: continue
            v = a[k][:, :3].astype(np.float64)[:, [0, 2, 1]]
            v = (v / s) @ R
            v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-8)
            v = v[:, [0, 2, 1]].astype(np.float32)
            a[k] = np.hstack([v, a[k][:, 3:]]).astype(np.float32) if k == 'TANGENT' else v
        if np.linalg.det(R * s[:, None]) < 0: tri = tri[:, ::-1]   # a mirrored piece keeps its faces outward
        out.append((a, tri, name))
    return out


def _merge(prims):
    """One primitive per material (the pieces share their materials: hundreds of draw calls otherwise)."""
    by = {}
    for a, tri, name in prims:
        by.setdefault((name, tuple(sorted(a))), []).append((a, tri))
    out = []
    for (name, keys), parts in by.items():
        attrs = {k: np.concatenate([a[k] for a, _ in parts]) for k in keys}
        off, tris = 0, []
        for a, tri in parts:
            tris.append(tri + off); off += len(a['POSITION'])
        out.append((attrs, np.concatenate(tris), name))
    return out


def _main_dock(location, docks):
    """The dock the hangar shows: the location's first trading dockable (dockables.csv's order), else its first."""
    import sectors
    order = [d['id'] for d in sectors.dockables() if d['location'] == location and d['trader']]
    for i in order:
        for d in docks:
            if d['id'] == i: return d
    return docks[0]


_dock_sounds = None
def dock_sounds():
    """BP_DockableStation's DockSound / UndockSound (S_SC_Docking: S_Docking_003, S_SC_Undocking: S_Undocking_005) as the
    mod's sounds (sounds/es2_docking, es2_undocking: ModSounds.Named): {field: name}, empty without the export's audio."""
    global _dock_sounds
    if _dock_sounds is not None: return _dock_sounds
    import audio, shutil
    _dock_sounds = {}
    try:
        if not audio.available(): return _dock_sounds
        cues = {'dockSound': ('S_SC_Docking', 'es2_docking'), 'undockSound': ('S_SC_Undocking', 'es2_undocking')}
        waves = {k: (audio.cue(c) or {}).get('waves') for k, (c, _) in cues.items()}
        files, tmp = audio.decode([w[0][0] for w in waves.values() if w])
        for k, (_, name) in cues.items():
            if waves[k] and waves[k][0][0] in files:
                audio.write(files[waves[k][0][0]], f'sounds/{name}')
                _dock_sounds[k] = name
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        print(f'  dock sounds: {e}')
    return _dock_sounds


_dock_dust = None


def dock_dust():
    """P_Vehicle_LandingDust's flipbook (M_Smoke_NonDirectional_001's T_Smoke_001_M: 6 x 6 frames, its green the opacity) as
    the mod's textures/es2_landing_dust.png (greyscale, 2048 px): {'dust': path}, empty when the export lacks it (export it
    with tools/shaders: export of /Game/Assets/Effects/Textures/T_Smoke_001_M)."""
    global _dock_dust
    if _dock_dust is not None: return _dock_dust
    _dock_dust = {}
    try:
        from PIL import Image
        src = os.path.join(SRC, 'Assets/Effects/Textures/T_Smoke_001_M.png')
        if not os.path.exists(src):
            print('  landing dust: T_Smoke_001_M.png not in the export (tools/shaders export), no dust')
            return _dock_dust
        rel = 'textures/es2_landing_dust.png'
        out = os.path.join(MOD, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        g = Image.open(src).convert('RGBA').split()[1]
        g.resize((2048, 2048), Image.LANCZOS).save(out, optimize=True)
        _dock_dust = {'dust': rel}
    except Exception as e:
        print(f'  landing dust: {e}')
    return _dock_dust


def dock_room(d, others, g):
    """interiors.json's fields for docking EVERSPACE 2's way at dock 'd' (World.Es2Dock; docks() gives it): its markers (room
    metres, Unity's frame; 'g' turns Unreal cm into the model's glTF metres) and settings; 'others' the docks close by, as
    parked pads."""
    pad = g(d['t']); ship = g(d['pad']); cam = g(d['camera']); off = g(d['takeoff'])
    up = np.array([0.0, 1.0, 0.0])
    # the docked ship's centre (DockingTransform) and its nose, the take-off's end and its nose, the camera's look point (the
    # ship + CameraLookAtOffsetZ), the Interact box's centre
    marks = {'pad': pad, 'camera': cam, 'camera_target': g(d['look']), 'light': cam + (cam - ship) * 0.3 + up * 40.0,
             'gate': off, 'gate_out': ship + (off - ship) * 3.0,
             'ship': ship, 'ship_ahead': g(d['pad'] + 10000.0 * d['padR'][0]),
             'takeoff': off, 'takeoff_ahead': g(d['takeoff'] + 10000.0 * d['takeoffR'][0]), 'dock_zone': g(d['zone'])}
    for k, o in enumerate(others[:6], 1):
        marks[f'parked_{k}'] = g(o['t'])
    fwd = d['R'][0]                                           # the dock's forward (Unreal) -> Unity (mirrored x)
    fu = np.array([-fwd[0], fwd[2], fwd[1]])
    def scaled(v): return [round(-float(v[0]) * SCALE, 2), round(float(v[1]) * SCALE, 2), round(float(v[2]) * SCALE, 2)]
    return {'markers': {k: scaled(v) for k, v in marks.items()},
            # ES2's CineCamera: a 1400 mm lens on a 1000 mm square filmback, 39 deg across: 23 deg up a 16:9 screen
            'fov': 23, 'near': 1, 'far': 20000, 'ambient': [0.34, 0.36, 0.42], 'lightIntensity': 1.4,
            'startYaw': round(math.degrees(math.atan2(fu[0], fu[2])), 1), 'flights': False, 'dock': 'es2',
            'rise': round(d['rise'] / 100.0 * SCALE, 2), **dock_sounds(), **dock_dust(),
            # (the box's half extents: ES2's X forward, Y right, Z up -> the dock's right, up, forward)
            'dockZone': [round(d['zoneExt'][1] / 100.0 * SCALE, 1), round(d['zoneExt'][2] / 100.0 * SCALE, 1),
                         round(d['zoneExt'][0] / 100.0 * SCALE, 1)]}


def build_station(location, gid, log=print):
    """One station's model (models/stations/<gid>.glb) and its hangar room; returns (stations.json fields, interiors.json
    room) or None without a dock or its meshes."""
    import glbtool, warships
    from warships import split_prims, material_entries
    lv = Level(location)
    docks = lv.docks()
    if not docks: return None
    pieces = cluster(lv.pieces(), docks)
    placed, missing = [], set()
    for m, R, t, s, ovr in pieces:
        if _mesh(m) is None: missing.add(m); continue
        placed.append((m, R, t, s, ovr))
    if missing: log(f'  {gid}: {len(missing)} meshes missing (tools/station_assets.txt)')
    if not placed: return None
    # the centre: the middle of the pieces' bounds (each piece's bounds through its transform)
    lo, hi = np.full(3, 1e12), np.full(3, -1e12)
    for m, R, t, s, _ in placed:
        p = (_corners(m) * s) @ R + t
        lo = np.minimum(lo, p.min(0)); hi = np.maximum(hi, p.max(0))
    centre = (lo + hi) / 2
    # each distinct mesh once, placed by a node per piece (glTF instancing: the pieces repeat, a station's ~100 pieces are
    # some 40 meshes)
    mats_used, names = {}, {}
    w = glbtool.Writer()
    root = w.node(gid)
    mesh_index, tris = {}, 0
    P = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], np.float64)   # glTF <-> Unreal axes (x, z, y)
    for m, R, t, s, ovr in placed:
        if (m, ovr) not in mesh_index:
            mesh_index[(m, ovr)] = w.mesh(m.rsplit('/', 1)[-1], _merge(split_prims(f'st_{gid}_', _variant(m, ovr), mats_used, layered=True, names=names)))
        # the piece's transform in glTF metres: v' = v @ (P diag(s) R P) + (t - centre) @ P / 100 (rows); glTF's matrix is
        # column-major, so its 16 numbers are those rows in turn
        M = P @ np.diag(s) @ R @ P
        b = (t - centre) @ P / 100.0
        w.g['nodes'].append({'name': m.rsplit('/', 1)[-1], 'mesh': mesh_index[(m, ovr)],
                             'matrix': [float(v) for v in (*M[0], 0.0, *M[1], 0.0, *M[2], 0.0, *b, 1.0)]})
        w.g['nodes'][root].setdefault('children', []).append(len(w.g['nodes']) - 1)
        tris += sum(len(tri) for _, tri, _ in _mesh(m))
    rel = f'stations/{gid}.glb'
    path = os.path.join(MOD, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w.write(path)
    materials = material_entries(f'st_{gid}_', mats_used)
    extent = float((hi - lo).max()) / 100.0                   # ES2 metres
    # (no Space Lounge: ES2's stations have none)
    station = {'model': rel, 'modelSize': round(extent * SCALE / 0.05), 'materials': materials, 'hangar': f'es2_ships:{gid}_hangar',
               'bar': 'none'}

    # The hangar: the same model, ES2's own docked view of the main dock
    d = _main_dock(location, docks)
    g = lambda v: _gltf(np.asarray(v) - centre)
    room = {'id': f'{gid}_hangar', 'type': 'hangar', 'model': rel, 'scale': SCALE, 'materials': materials,
            **dock_room(d, [o for o in docks if o is not d and np.linalg.norm(o['t'] - d['t']) < PAD_REACH], g)}
    log(f'  {gid}: {len(placed)} pieces of {len(mesh_index)} meshes, {tris} triangles, {len(materials)} materials, {extent:.0f} m, '
        f'{len([k for k in room["markers"] if k.startswith("parked")])} parked pads, {os.path.getsize(path) >> 20} MB')
    return station, room


def build(stations_json, log=print):
    """Gives the sectors' stations (stations.json entries) ES2's own models and hangars; returns the interiors.json rooms."""
    import jobs, warships
    warships.configure(SRC, MOD)
    by = {s['id']: s for s in stations_json}
    rooms = []
    todo = [(lid, gid) for _, lid, gid in station_locations() if gid in by]
    dock_sounds()   # (once, before the workers: each room names them)
    dock_dust()
    # on the step workers (jobs.run, warships.logged), their lines in the table's order: not jobs.pool(), whose workers are
    # the texture writes the builds wait for (all of them taken by builds, the batch ran nearly one station at a time)
    for (lid, gid), (r, lines) in zip(todo, jobs.run(lambda x: warships.logged(build_station, *x, warships.say), todo)):
        for l in lines: log(l)
        if not r: continue
        st, room = r
        s = by[gid]
        for k in ('looksLike', 'model', 'modelSize', 'materials'): s.pop(k, None)
        s.update(st)
        s.setdefault('orbit', {}).pop('station', None)
        rooms.append(room)
    jobs.flush()
    return rooms
