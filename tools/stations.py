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


class Level:
    def __init__(self, location):
        self.d = json.load(open(os.path.join(SRC, 'Maps/Locations', location + '.json'), encoding='utf-8-sig'))
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
            pad_t = self.world(pad)[1] if pad is not None else t + np.array([0, 0, 490.0]) @ R
            off_t = self.world(off)[1] if off is not None else t + np.array([10000.0, 0, 700.0]) @ R
            # the camera on its spring arm (BP_DockableStation's defaults: pitch -15, yaw 160, 35 m), at the pad
            arm = _rot(-15.0, 160.0, 0.0) @ R
            cam_t = t + np.array([-3500.0, 0.0, 0.0]) @ arm
            out.append({'id': p.get('StationID'), 'R': R, 't': t, 'pad': pad_t, 'camera': cam_t, 'takeoff': off_t})
        return out

    def pieces(self):
        """[(mesh path, R, t, s)] of every structure piece placed in the level (instances one by one)."""
        out = []
        for e in self.d:
            ty = e.get('Type')
            if ty not in ('StaticMeshComponent', 'InstancedStaticMeshComponent', 'HierarchicalInstancedStaticMeshComponent'): continue
            p = e.get('Properties') or {}
            m = ((p.get('StaticMesh') or {}).get('ObjectPath') or '').split('.')[0]
            if not m or not any(k in m for k in KEEP) or any(k in m for k in SKIP): continue
            if p.get('bVisible') is False or p.get('bHiddenInGame'): continue
            R, t, s = self.world(e)
            inst = p.get('PerInstanceSMData')
            if inst:
                for i in inst:
                    tm = i.get('TransformData') or {}
                    q = tm.get('Rotation') or {}; tr = tm.get('Translation') or {}; sc = tm.get('Scale3D') or {}
                    IR = _quat(q); It = np.array([tr.get(a, 0.0) for a in 'XYZ']); Is = np.array([sc.get(a, 1.0) for a in 'XYZ'])
                    out.append((m, IR @ R, (It * s) @ R + t, Is * s))
            else:
                out.append((m, R, t, s))
        return out


def cluster(pieces, docks):
    """The pieces linked to the docks: single linkage of their pivots (LINK), within REACH of the first dock."""
    if not pieces or not docks: return []
    P = np.array([t for _, _, t, _ in pieces])
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
    for m, R, t, s in pieces:
        if _mesh(m) is None: missing.add(m); continue
        placed.append((m, R, t, s))
    if missing: log(f'  {gid}: {len(missing)} meshes missing (tools/station_assets.txt)')
    if not placed: return None
    # the centre: the middle of the pieces' bounds (each piece's bounds through its transform)
    lo, hi = np.full(3, 1e12), np.full(3, -1e12)
    for m, R, t, s in placed:
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
    for m, R, t, s in placed:
        if m not in mesh_index:
            mesh_index[m] = w.mesh(m.rsplit('/', 1)[-1], _merge(split_prims(f'st_{gid}_', _mesh(m), mats_used, layered=True, names=names)))
        # the piece's transform in glTF metres: v' = v @ (P diag(s) R P) + (t - centre) @ P / 100 (rows); glTF's matrix is
        # column-major, so its 16 numbers are those rows in turn
        M = P @ np.diag(s) @ R @ P
        b = (t - centre) @ P / 100.0
        w.g['nodes'].append({'name': m.rsplit('/', 1)[-1], 'mesh': mesh_index[m],
                             'matrix': [float(v) for v in (*M[0], 0.0, *M[1], 0.0, *M[2], 0.0, *b, 1.0)]})
        w.g['nodes'][root].setdefault('children', []).append(len(w.g['nodes']) - 1)
        tris += sum(len(tri) for _, tri, _ in _mesh(m))
    rel = f'stations/{gid}.glb'
    path = os.path.join(MOD, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w.write(path)
    materials = material_entries(f'st_{gid}_', mats_used)
    extent = float((hi - lo).max()) / 100.0                   # ES2 metres
    station = {'model': rel, 'modelSize': round(extent * SCALE / 0.05), 'materials': materials, 'hangar': f'es2_ships:{gid}_hangar'}

    # The hangar: the same model, ES2's own docked view of the main dock
    d = _main_dock(location, docks)
    g = lambda v: _gltf(np.asarray(v) - centre)
    pad = g(d['t']); ship = g(d['pad']); cam = g(d['camera']); off = g(d['takeoff'])
    up = np.array([0.0, 1.0, 0.0])
    marks = {'pad': pad, 'camera': cam, 'camera_target': ship, 'light': cam + (cam - ship) * 0.3 + up * 40.0,
             'gate': off, 'gate_out': ship + (off - ship) * 3.0}
    for k, o in enumerate([o for o in docks if o is not d and np.linalg.norm(o['t'] - d['t']) < PAD_REACH][:6], 1):
        marks[f'parked_{k}'] = g(o['t'])
    fwd = d['R'][0]                                           # the dock's forward (Unreal) -> Unity (mirrored x)
    fu = np.array([-fwd[0], fwd[2], fwd[1]])
    def scaled(v): return [round(-float(v[0]) * SCALE, 2), round(float(v[1]) * SCALE, 2), round(float(v[2]) * SCALE, 2)]
    room = {'id': f'{gid}_hangar', 'type': 'hangar', 'model': rel, 'scale': SCALE, 'materials': materials,
            'markers': {k: scaled(v) for k, v in marks.items()},
            # ES2's CineCamera: a 1400 mm lens on a 1000 mm square filmback, 39 deg across: 23 deg up a 16:9 screen
            'fov': 23, 'near': 1, 'far': 20000, 'ambient': [0.34, 0.36, 0.42], 'lightIntensity': 1.4,
            'startYaw': round(math.degrees(math.atan2(fu[0], fu[2])), 1), 'flights': True,
            'cruise': round(30.0 * SCALE), 'gateSpan': [round((off[1] - 30.0) * SCALE), round((off[1] + 30.0) * SCALE)]}
    log(f'  {gid}: {len(placed)} pieces of {len(mesh_index)} meshes, {tris} triangles, {len(materials)} materials, {extent:.0f} m, '
        f'{len(marks) - 6} parked pads, {os.path.getsize(path) >> 20} MB')
    return station, room


def build(stations_json, log=print):
    """Gives the sectors' stations (stations.json entries) ES2's own models and hangars; returns the interiors.json rooms."""
    import jobs, warships
    warships.configure(SRC, MOD)
    by = {s['id']: s for s in stations_json}
    rooms = []
    todo = [(lid, gid) for _, lid, gid in station_locations() if gid in by]
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
