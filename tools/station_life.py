"""EVERSPACE 2's station life for stations.py: the worker drones (BP_SplineTraffic_WorkerDrones) flying their loops round a
station's structures and stopping now and then to weld its hull, as the station's stations.json "life" (the remake's
World.StationLife, Modding/README.md "Station life").

ES2 (BP_SplineTraffic and its WorkerDrones child, decompiled): a level's spline carries Count drones (OverrideCount, else
trunc(the spline's length / 20000 cm x Density 0.5)) at BaseSpeed 2000 cm/s, the lanes LaneOffset 500 cm apart (TwoLanes),
turning at an open spline's ends (DoUTurns). Every WeldScanIntervalPerDrone 2 s / the drones not welding, one at random (not
welding, its cooldown over) sphere-traces MaxWeldPointDistance 10000 cm along a random direction within 90 degrees of its
heading; on a static hull it leaves the spline for the spot WeldPointPositionOffset 500 cm off the surface, facing it
(PhysicsApproachTransform: at most 8000 cm/s), welds there 10-20 s (P_WorkerDrone_WeldSparks), and goes back with a
cooldown of up to CooldownDurationMax 20 s.

Here: the loops and their weld spots in the station model's own frame (its glTF metres, as stations.py writes the model: the
level's place less the station's centre), so the remake flies them on the model as it is turned, scaled and centred. The
traces are made once, here, against the station's triangles: from points along each loop, both ways, rays within the 90
degree cone; the hits (spot, outward normal) spread over the loop. The drone itself (SM_Drone_022) goes into the station's
model file as its scene "life", its nose turned onto glTF +z."""
import math, os
import numpy as np

SPAN = 20000.0           # cm of spline a drone at Density 1 (BP_SplineTraffic's construction script)
DENSITY = 0.5            # BP_SplineTraffic_WorkerDrones' class defaults
SPEED = 2000.0           # cm/s
LANE_OFFSET = 500.0      # cm
WELD_REACH = 10000.0     # MaxWeldPointDistance, cm
CONE_DEG = 90.0          # RandomUnitVectorInConeInDegrees(forward, 90)
STEP = 6000.0           # cm between the trace points along a loop
RAYS = 4                 # traces a point, each way
MAX_SPOTS = 24           # weld spots kept a loop
MAX_DRONES = 40          # a loop's drones at most (the remake's limit)
DRONE = '/Game/Assets/Vehicles/Drones/Meshes/SM_Drone_022'
NEAR = 30000.0           # cm: a spline whose points come this close to the station's bounds is its own


def _spline_points(lv, actor):
    """A WorkerDrones actor's spline points in the level (cm), or None (hidden, no spline)."""
    p = actor.get('Properties') or {}
    if p.get('bHidden'): return None
    spl = lv.ref(p.get('Spline'))
    if spl is None: return None
    pts = ((((spl.get('Properties') or {}).get('SplineCurves') or {}).get('position') or {}).get('Points')) or []
    if len(pts) < 2: return None
    R, t, s = lv.world(spl)
    return np.array([(np.array([(q.get('OutVal') or {}).get(a, 0.0) for a in 'XYZ']) * s) @ R + t for q in pts], np.float64)


def _catmull(points, loop, per=16):
    """The loop's curve as the remake draws it (Flight.TrafficLane: Catmull-Rom through the points, closed when it loops)."""
    n = len(points)
    loop = loop and n > 2
    def at(i):
        if loop: return points[i % n]
        if i < 0: return points[0] + (points[0] - points[1])
        if i >= n: return points[-1] + (points[-1] - points[-2])
        return points[i]
    out = []
    for sgm in range(n if loop else n - 1):
        p0, p1, p2, p3 = at(sgm - 1), at(sgm), at(sgm + 1), at(sgm + 2)
        for k in range(per):
            t = k / per; t2 = t * t; t3 = t2 * t
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3))
    out.append(points[0] if loop else points[-1])
    return np.array(out)


def _cone(axis, rng, k):
    """'k' random unit vectors within CONE_DEG of 'axis' (uniform over the cap)."""
    axis = axis / (np.linalg.norm(axis) or 1.0)
    helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, helper); u /= np.linalg.norm(u); v = np.cross(axis, u)
    cos_max = math.cos(math.radians(CONE_DEG))
    c = rng.uniform(cos_max, 1.0, k); s = np.sqrt(1.0 - c * c); a = rng.uniform(0.0, 2 * math.pi, k)
    return c[:, None] * axis + s[:, None] * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v)


def _trace(origins, dirs, tris):
    """Nearest hits of rays (origin, unit dir) within WELD_REACH on triangles (T, 3, 3): [(point, normal toward the ray)]."""
    out = []
    if len(tris) == 0: return out
    v0 = tris[:, 0]; e1 = tris[:, 1] - v0; e2 = tris[:, 2] - v0
    for o, d in zip(origins, dirs):
        p = np.cross(d, e2)
        det = np.einsum('ij,ij->i', e1, p)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = o - v0
        u = np.einsum('ij,ij->i', tv, p) * inv
        q = np.cross(tv, e1)
        v = (q @ d) * inv
        t = np.einsum('ij,ij->i', e2, q) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1.0) & (t <= WELD_REACH)
        if not hit.any(): continue
        i = np.flatnonzero(hit)[np.argmin(t[hit])]
        n = np.cross(e1[i], e2[i]); n /= (np.linalg.norm(n) or 1.0)
        if n @ d > 0: n = -n
        out.append((o + d * t[i], n))
    return out


def _spread(spots, k):
    """At most 'k' of the spots, spread out (farthest first)."""
    if len(spots) <= k: return spots
    pts = np.array([s[0] for s in spots])
    keep = [0]; dist = np.linalg.norm(pts - pts[0], axis=1)
    while len(keep) < k:
        i = int(np.argmax(dist)); keep.append(i)
        dist = np.minimum(dist, np.linalg.norm(pts - pts[i], axis=1))
    return [spots[i] for i in keep]


def _triangles(placed, centre, box_lo, box_hi):
    """The triangles (T, 3, 3), level cm less 'centre', of the placed pieces (stations.py's (mesh, R, t, s, overrides))
    whose bounds reach into the box."""
    from stations import _corners, _mesh
    out = []
    for m, R, t, s, _ in placed:
        c = (_corners(m) * s) @ R + t - centre
        if (c.max(0) < box_lo).any() or (c.min(0) > box_hi).any(): continue
        for a, tri, _ in _mesh(m):
            v = (a['POSITION'].astype(np.float64)[:, [0, 2, 1]] * 100.0 * s) @ R + t - centre
            out.append(v[tri])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def loops(lv, placed, centre, lo, hi, seed=0):
    """The station's worker-drone loops: [{points, count, speed, loop, twoLanes, laneOffset, spots}] in glTF metres of the
    model ('placed' its pieces, 'centre' and its bounds 'lo' / 'hi' in level cm)."""
    from stations import _gltf
    rng = np.random.default_rng(seed)
    out = []
    for e in lv.d:
        if e.get('Type') != 'BP_SplineTraffic_WorkerDrones_C': continue
        pts = _spline_points(lv, e)
        if pts is None: continue
        if ((pts < lo - NEAR) | (pts > hi + NEAR)).any(axis=1).all(): continue
        p = e.get('Properties') or {}
        closed = bool(p.get('ClosedLoop', False))
        curve = _catmull(pts, closed)
        length = float(np.linalg.norm(np.diff(curve, axis=0), axis=1).sum())
        n = p.get('OverrideCount', -1)
        count = n if isinstance(n, int) and n >= 0 else int(length / SPAN * float(p.get('Density', DENSITY)))
        if count <= 0: continue
        two = p.get('TwoLanes', True) is not False
        # the traces: points every STEP along the curve, rays both ways (the drones run either way on two lanes or an open
        # loop's turns), against the triangles near the loop
        rel = curve - centre
        box_lo, box_hi = rel.min(0) - WELD_REACH, rel.max(0) + WELD_REACH
        tris = _triangles(placed, centre, box_lo, box_hi)
        near = tris[((tris >= box_lo) & (tris <= box_hi)).all(axis=2).any(axis=1)]
        seg = np.linalg.norm(np.diff(rel, axis=0), axis=1); along = np.concatenate([[0.0], np.cumsum(seg)])
        origins, dirs = [], []
        for d in np.arange(0.0, length, STEP):
            i = min(int(np.searchsorted(along, d, 'right')) - 1, len(rel) - 2)
            tangent = rel[i + 1] - rel[i]
            if not np.linalg.norm(tangent): continue
            for sign in ((1.0, -1.0) if two or not closed else (1.0,)):
                for v in _cone(tangent * sign, rng, RAYS): origins.append(rel[i]); dirs.append(v)
        spots = _spread(_trace(origins, dirs, near), MAX_SPOTS)
        # glTF metres; ES2 cm/s -> the model's metres a second
        loop = {'points': [[round(float(x), 2) for x in _gltf(q)] for q in pts - centre],
                'count': min(count, MAX_DRONES),
                'speed': round(float(p.get('BaseSpeed', SPEED)) * float(p.get('SpeedFactor', 1.0)) / 100.0, 2)}
        if not closed or len(pts) < 3: loop['loop'] = False
        if not two: loop['twoLanes'] = False
        lane = float(p.get('LaneOffset', LANE_OFFSET))
        if lane != LANE_OFFSET: loop['laneOffset'] = round(lane / 100.0, 2)
        if spots:
            loop['spots'] = [[round(float(x), 2) for x in _gltf(at)] + [round(float(x), 3) for x in _gltf(nrm) * 100.0] for at, nrm in spots]
        out.append(loop)
    return out


def add_drone(w, gid, mats_used, names):
    """The drone into the station's glTF writer 'w' as the scene "life": its mesh under a node turning its nose (Unreal +X,
    glTF +x) onto glTF +z (Unity's forward); returns False when the export lacks it."""
    from stations import _mesh, _merge, _variant
    from warships import split_prims
    if _mesh(DRONE) is None: return False
    mesh = w.mesh('SM_Drone_022', _merge(split_prims(f'st_{gid}_', _variant(DRONE, ()), mats_used, layered=True, names=names)))
    if mesh is None: return False
    w.g['nodes'].append({'name': 'es2_worker_drone', 'mesh': mesh, 'rotation': [0.0, -math.sqrt(0.5), 0.0, math.sqrt(0.5)]})
    w.g['scenes'].append({'name': 'life', 'nodes': [len(w.g['nodes']) - 1]})
    return True
