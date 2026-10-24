"""EVERSPACE 2's warships and freighters for the ES2 Ships mod, the way the GoF3 Ships mod brings GoF3's capital ships
(Modding.ModCapitalShips): ships.json ships with "traffic": { "capital": "battleship" | "freighter" } that the remake parks in
the orbits' capital ship special (battleships) or flies among the freighters, never as fighters, never sold.

Each comes from its EVERSPACE 2 blueprint (Blueprints/Pawns/Ships/BP_*: its hull mesh(es), and the child actors and scene
components that put turrets, drone / hangar spawners, weak spots and missile launchers on it) and its mesh's sockets (the
engines). They become the remake's capital ship subsystems (ships.json "subsystems", World.CapitalSubsystems): turrets of the
mod's own ES2 turret items (weapons.py) that can be shot off the hull, hangars launching ES2 fighters (the mod's kit ships,
random builds), weak spots that pass their hits on to the hull. The Dreadnought (its stage pieces assembled, BP_Dreadnought's
whole layout) is no traffic ship: its encounter (encounter.py) brings it.

Materials: es2mat (EVERSPACE 2's material instances, resolved) -> URP Lit through the mod's "materials" entries, each glTF
material renamed "<ship>_<n>|" so the entries match one material each; materials with vertex colour masks split into one
material per tint like the kit hulls (Paint1-3).

Scale: EVERSPACE 2's metres x 3.6 like the fighters (build.SCALE), but no hull past MAX_SIZE (the Dreadnought, the carrier and
the frigate would reach 8-10 km, past the flight level's 15 km far plane at a few km's distance)."""
import json, math, os, re, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import glbtool, es2mat

SRC = MOD = None
SCALE = 3.6
MAX_SIZE = 4500.0     # Unity metres: the largest hull's longest side
LOG = print

# Turret items (weapons.py's capital turrets) by faction: the turret, its missile launcher.
T = lambda n: 'es2_ships:' + n

# (id, name, description, race, kind, blueprint, meshes (Vehicles/...), turret item, missile item, hangar fighters)
WARSHIPS = [
    ('es2_destroyer', 'Outlaw Destroyer', 'An Outlaw warship of EVERSPACE 2: four retractable coil gun turrets, missile launchers and two drone bays. Outlaw raids bring it along now and then.',
     8, 'battleship', 'BP_Outlaw_Destroyer', ['Warships/Meshes/SK_Warship_001'], T('turret_outlaw'), T('turret_outlaw_missile'), 'outlaw'),
    ('es2_gb_carrier', 'G&B Carrier', 'Grady & Brunt\'s carrier, the corporation\'s flagship design: seven heavy laser turrets along its back and keel, torpedo bays, and launch decks for a wing of fighters.',
     3, 'battleship', 'BP_GB_Carrier', ['Warships/Meshes/SM_Warship_002'], T('turret_gb'), T('turret_gb_torpedo'), 'gb'),
    ('es2_light_cruiser', 'Colonial Light Cruiser', 'The Colonial Fleet\'s light cruiser: five pulse laser turrets, two missile turrets and a mine layer.',
     0, 'battleship', 'BP_Colonial_LightCruiser', ['Warships/Meshes/SM_Warship_003'], T('turret_colonial'), T('turret_colonial_missile'), None),
    ('es2_okkar_corvette', 'Okkar Corvette', 'An Okkar corvette with its drone bays and pulse laser turrets.',
     1, 'battleship', 'BP_Okkar_Corvette', ['Warships/Meshes/SM_Warship_004'], T('turret_okkar'), T('turret_okkar_missile'), 'okkar'),
    ('es2_cultist_battleship', 'Cultist Battleship', 'A battleship of the Ancients\' cultists, its twin turrets glowing with their alien energy.',
     9, 'battleship', 'BP_Cultist_Battleship', ['Warships/Meshes/SM_Warship_005'], T('turret_cultist'), None, None),
    ('es2_okkar_frigate', 'Okkar Frigate', 'The Okkar frigate: five turrets, two hangars and an energy core under armoured covers. Eight weak spots on its hull let a determined pilot crack it.',
     1, 'battleship', 'BP_Okkar_Frigate', ['Warships/Meshes/SM_Warship_008'], T('turret_okkar_heavy'), T('turret_okkar_missile'), 'okkar'),
    ('es2_colonial_cruiser', 'Colonial Cruiser', 'The Colonial Fleet\'s heavy cruiser, three heavy pulse laser turrets on its spine and keel.',
     0, 'battleship', 'BP_Colonial_Cruiser_Infected', ['Warships/Meshes/SM_Warship_009'], T('turret_colonial_heavy'), None, None),
    ('es2_swarmer_capital', 'Ancient Swarmer', 'A capital ship of the Ancients\' swarmers: a living hull that spits out swarmer drones.',
     9, 'battleship', 'BP_AncientSwarmer_Capital', ['Warships/Meshes/SK_Warship_011'], T('turret_swarmer'), None, 'swarmer'),
    ('es2_drone_carrier', 'Outlaw Drone Carrier', 'An Outlaw transporter turned drone carrier.',
     8, 'battleship', 'BP_Outlaw_DroneCarrier', ['Transporters/Meshes/SM_Transporter_004'], T('turret_outlaw'), None, 'outlaw'),
]
FREIGHTERS = [
    ('es2_gb_freighter', 'G&B Freighter', 'A Grady & Brunt freighter with its retractable turrets.', 3, 'BP_Freighter_Base', ['Transporters/Meshes/SK_Transporter_002'], T('turret_freighter')),
    ('es2_freelancer_freighter', 'Freelancer Freighter', 'A freelance hauler of EVERSPACE 2.', 2, 'BP_Freelancer_Freighter', ['Transporters/Meshes/SK_Transporter_005'], T('turret_freighter')),
    ('es2_cargo_carrier', 'Cargo Carrier', 'A freelancer cargo carrier with its cargo pods.', 0, 'BP_Freelancer_CargoCarrier', ['Transporters/Meshes/SK_Transporter_003'], T('turret_freighter')),
    ('es2_coalition_carrier', 'Coalition Cargo Carrier', 'The Coalition\'s cargo carrier.', 0, 'BP_Coalition_CargoCarrier', ['Transporters/Meshes/SK_Transporter_003_B'], T('turret_freighter')),
    ('es2_okkar_freighter', 'Okkar Freighter', 'An Okkar freighter.', 1, 'BP_Ship_Okkar_Freighter', ['Transporters/Meshes/SM_Transporter_010_001_A'], None),
    ('es2_flying_trader', 'Flying Trader', 'A travelling trader\'s ship.', 2, None, ['Transporters/Meshes/SM_Transporter_006'], None),
    ('es2_tareen_trader', 'Tareen Trader', 'A Tareen trader with its tarps and neon signs.', 3, None, ['Transporters/Meshes/SM_Trader_001'], None),
]
# The fighters a hangar launches by faction: the mod's kit ships (random builds).
HANGAR_SHIPS = {'outlaw': ['es2_ships:striker', 'es2_ships:stinger', 'es2_ships:scout'],
                'gb': ['es2_ships:interceptor', 'es2_ships:vanguard', 'es2_ships:sentinel'],
                'okkar': ['es2_ships:wraith', 'es2_ships:interceptor'],
                'swarmer': ['es2_ships:scout', 'es2_ships:stinger'],
                'dreadnought': ['es2_ships:striker', 'es2_ships:gunship', 'es2_ships:bomber', 'es2_ships:stinger']}


def configure(src, mod, log=print):
    global SRC, MOD, LOG
    SRC, MOD, LOG = src, mod, log
    es2mat.configure(src)


# ---- geometry -----------------------------------------------------------------------------------------------------------

KEEP = ('POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0', 'COLOR_0')


def read_prims(path):
    """A GLB's primitives: [(attributes {name: array}, triangles (n, 3) int64, material name)], positions in the file's
    metres (the mesh nodes' translations applied; FModel's static meshes sit at the origin, its skinned ones in bind pose)."""
    g, b = glbtool.load(path)
    out = []
    node_of_mesh = {n['mesh']: n for n in g.get('nodes', []) if 'mesh' in n}
    for mi, m in enumerate(g['meshes']):
        node = node_of_mesh.get(mi, {})
        t = np.array(node.get('translation', [0, 0, 0]), np.float32) if 'skin' not in node else np.zeros(3, np.float32)
        for p in m['primitives']:
            A = p['attributes']
            attrs = {k: glbtool.read(g, b, A[k])[0].astype(np.float32) for k in KEEP if k in A}
            if 'POSITION' not in attrs or 'indices' not in p: continue
            attrs['POSITION'] = attrs['POSITION'] + t
            if 'COLOR_0' in attrs:
                c = attrs['COLOR_0']
                if c.max() > 1.5: c = c / 255.0   # normalized ints
                attrs['COLOR_0'] = c
            tri = glbtool.read(g, b, p['indices'])[0].reshape(-1, 3).astype(np.int64)
            name = g['materials'][p['material']].get('name', '') if 'material' in p else ''
            out.append((attrs, tri, name))
    return out


def bounds(prims):
    mn = np.min([a['POSITION'].min(0) for a, _, _ in prims], axis=0)
    mx = np.max([a['POSITION'].max(0) for a, _, _ in prims], axis=0)
    return mn, mx


# ---- materials ----------------------------------------------------------------------------------------------------------

_made = {}


def _img(tex):
    f = es2mat.texture_file(tex)
    return np.array(Image.open(f).convert('RGBA')) if f else None


def _save(arr, rel, size=2048):
    p = os.path.join(MOD, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im = Image.fromarray(arr)
    if max(im.size) > size:
        s = size / max(im.size); im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
    im.save(p, optimize=True)
    return rel


def tex(kind, src, ch=None, extra=None):
    """A texture made for a role, once per (role, texture, channel): 'colour' (RGB, or one channel as grey; alpha from 'extra'
    = (texture, channel) when masked), 'ms' (src = (metal, rough) each (texture, channel) or None), 'emit' (one channel),
    'normal' (DirectX -> Unity)."""
    key = (kind, str(src), ch, str(extra))
    if key in _made: return _made[key]
    rel = None
    try:
        if kind == 'normal':
            a = _img(src)
            if a is not None:
                a[..., 1] = 255 - a[..., 1]
                rel = _save(a[..., :3].copy(), f'warships/maps/{es2mat._name(src)}_n.png')
        elif kind == 'colour':
            a = _img(src)
            if a is not None:
                rgb = a[..., :3] if ch == 'rgb' else np.repeat(a[..., ch:ch + 1], 3, axis=2)
                al = None
                if extra:
                    m = _img(extra[0])
                    if m is not None:
                        al = m[..., extra[1]] if m.shape[:2] == a.shape[:2] else np.array(Image.fromarray(m[..., extra[1]]).resize(a.shape[1::-1]))
                out = np.dstack([rgb, al]) if al is not None else rgb
                tag = 'rgb' if ch == 'rgb' else 'c%d' % ch
                rel = _save(np.ascontiguousarray(out), f'warships/maps/{es2mat._name(src)}_{tag}{"a" if al is not None else ""}.png')
        elif kind == 'ms':
            metal, rough = src
            base = _img((rough or metal)[0])
            if base is not None:
                h, w = base.shape[:2]
                def chan(spec, default):
                    if not spec: return np.full((h, w), default, np.uint8)
                    a = _img(spec[0])
                    c = a[..., spec[1]]
                    return c if c.shape == (h, w) else np.array(Image.fromarray(c).resize((w, h)))
                mt = chan(metal, 0); rg = chan(rough, 128)
                out = np.zeros((h, w, 4), np.uint8); out[..., 0] = out[..., 1] = out[..., 2] = mt; out[..., 3] = 255 - rg
                rel = _save(out, f'warships/maps/{es2mat._name((rough or metal)[0])}_ms{metal[1] if metal else "x"}{rough[1] if rough else "x"}.png')
        elif kind == 'emit':
            a = _img(src)
            if a is not None and a[..., ch].max() > 8:
                rel = _save(np.repeat(a[..., ch:ch + 1], 3, axis=2).copy(), f'warships/maps/{es2mat._name(src)}_e{ch}.png', 1024)
    except Exception as e:
        LOG(f'    texture {src}: {e}')
    _made[key] = rel
    return rel


def material_entries(prefix, mats_used):
    """ships.json "materials" for the renamed glTF materials: {new name: (es2 material, tint index or None)}."""
    out = []
    for new, (src, ti) in mats_used.items():
        m = es2mat.resolve(src)
        kind = es2mat.classify(m)
        e = {'material': new}
        if kind == 'decal':
            e.update({'diffuse': 'warships/maps/clear.png', 'alphaClip': 0.5})
        elif kind == 'field':
            c = m['col'].get('Color') or m['col'].get('FieldColor') or m['col'].get('Colour') or [0.35, 0.75, 1.0]
            e.update({'color': [round(v * 0.2, 3) for v in c], 'emissionColor': [round(v, 3) for v in c], 'emissionIntensity': 1.6,
                      'opacity': 0.22, 'doubleSided': True})
        elif kind == 'glow':
            tints = es2mat.vertex_tints(m)
            c, i = es2mat.glow_colour(m)
            if tints and ti is not None: c = tints[min(ti, 2)]
            e.update({'color': [0.04, 0.04, 0.045], 'emissionColor': [round(v, 3) for v in c], 'emissionIntensity': i})
        elif kind == 'glass':
            e.update({'color': [0.06, 0.09, 0.12], 'smoothness': 0.95, 'metallic': 0.3, 'opacity': 0.6})
        elif kind == 'dark':
            e.update({'color': [0.0, 0.0, 0.0], 'smoothness': 0.0})
        elif kind == 'flame':
            e.update({'flame': True, 'flameLength': 5.0, 'emissionColor': [1.0, 0.45, 0.15], 'boostColor': [0.05, 0.525, 1.0], 'emissionIntensity': 4})
            if os.path.exists(os.path.join(MOD, 'maps', 'flame_noise.png')): e['flameNoise'] = 'maps/flame_noise.png'
        else:
            p = es2mat.plan(m)
            tint = p['tints'][ti] if ti is not None and p.get('tints') else p['tint']
            if 'colour' in p:
                ctex, cch = p['colour']
                alpha = p.get('alpha') if m['blend'] == 1 else None
                d = tex('colour', ctex, cch, alpha)
                if d: e['diffuse'] = d
                if alpha: e['alphaClip'] = 0.4
            e['color'] = [round(v, 3) for v in tint]
            if 'normal' in p:
                n = tex('normal', p['normal'])
                if n: e['normal'] = n
            if 'rough' in p or 'metal' in p:
                ms = tex('ms', (p.get('metal'), p.get('rough')))
                if ms: e['metallicSmoothness'] = ms
            else:
                e['metallic'] = round(p.get('metallic', 0.2), 2)
                e['smoothness'] = round(p.get('smoothness', 0.45), 2)
            if 'emit' in p and p.get('emission'):
                em = tex('emit', p['emit'][0], p['emit'][1])
                if em:
                    e.update({'emission': em, 'emissionColor': [round(v, 3) for v in p['emissionColor']], 'emissionIntensity': p['emission']})
            if p.get('tiling'): e['tiling'] = p['tiling']
        out.append(e)
    return out


def split_prims(prefix, prims, mats_used, layered=False):
    """Renames every primitive's material "<prefix><n>|" (a vertex-colour-masked one into a material per tint) and returns
    the Writer's primitives."""
    names = {}
    out = []
    for attrs, tri, mname in prims:
        m = es2mat.resolve(mname)
        kind = es2mat.classify(m)
        vt = (kind == 'pbr' and es2mat.plan(m).get('tints')) or (kind == 'glow' and es2mat.vertex_tints(m))
        if vt and 'COLOR_0' in attrs:
            col = attrs['COLOR_0'][:, :3]
            c = (col[tri[:, 0]] + col[tri[:, 1]] + col[tri[:, 2]]) / 3
            if layered:
                # ES2's structures lerp BaseColor -> VtxR -> VtxG -> VtxB by the channels in turn: the last channel set wins
                # (white is VtxB), none set is BaseColor
                which = np.full(len(c), -1)
                for k in range(3): which[c[:, k] >= 0.5] = k
                groups = [(None, tri[which == -1])] + [(k, tri[which == k]) for k in range(3)]
            else:
                which = c.argmax(axis=1)
                which[c.max(axis=1) < 0.25] = 0
                groups = [(k, tri[which == k]) for k in range(3)]
        else:
            groups = [(None, tri)]
        for ti, sel in groups:
            if len(sel) == 0: continue
            key = (mname, ti)
            if key not in names:
                names[key] = f'{prefix}{len(names):02d}|'
                mats_used[names[key]] = key
            used, inv = np.unique(sel.reshape(-1), return_inverse=True)
            a = {k: v[used] for k, v in attrs.items() if k != 'COLOR_0'}
            out.append((a, inv.astype(np.uint32), names[key]))
    return out


def write_glb(rel, prims, centre=None):
    w = glbtool.Writer()
    if centre is not None:
        prims = [({**a, 'POSITION': a['POSITION'] - centre}, i, n) for a, i, n in prims]
    root = w.node('hull')
    w.node('hull_mesh', mesh=w.mesh('hull', prims), parent=root)
    p = os.path.join(MOD, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    w.write(p)


# ---- blueprint layout ---------------------------------------------------------------------------------------------------

def _bp(name):
    import glob
    p = glob.glob(os.path.join(SRC, 'Blueprints', '**', name + '.json'), recursive=True)
    return json.load(open(p[0], encoding='utf-8-sig')) if p else None


def _super(name):
    d = _bp(name)
    if not d: return None
    for e in d:
        if e.get('Type') == 'BlueprintGeneratedClass':
            s = (e.get('Super') or {}).get('ObjectName')
            return s.split("'")[1][:-2] if s and "'" in s else None
    return None


def components(name):
    """The blueprint's (and its parents') child actors and scene components: [(component name, class or None, mesh or None,
    loc (cm) or None, rot (p, y, r) or None, scale)], the child's own entries winning."""
    out, seen = [], set()
    n = name
    while n and n not in seen:
        seen.add(n)
        d = _bp(n)
        if not d: break
        for e in d:
            pr = e.get('Properties', {})
            cname = e.get('Name', '').replace('_GEN_VARIABLE', '')
            t = e.get('Type')
            if t not in ('ChildActorComponent', 'SceneComponent', 'ArrowComponent', 'StaticMeshComponent', 'SkeletalMeshComponent'): continue
            if any(c[0] == cname for c in out): continue
            cls = (pr.get('ChildActorClass') or {}).get('ObjectName')
            cls = cls.split("'")[1][:-2] if cls and "'" in cls else None
            mesh = (pr.get('StaticMesh') or pr.get('SkeletalMesh') or pr.get('SkinnedAsset') or {}).get('ObjectName')
            mesh = mesh.split("'")[1] if mesh and "'" in mesh else None
            loc = pr.get('RelativeLocation'); rot = pr.get('RelativeRotation'); sc = pr.get('RelativeScale3D')
            out.append((cname, cls, mesh, [loc.get(k, 0) for k in 'XYZ'] if loc else None,
                        [rot.get(k, 0) for k in ('Pitch', 'Yaw', 'Roll')] if rot else None, (sc or {}).get('X', 1.0)))
        n = _super(n)
    return out


def isa(cls, word):
    """A child actor class is 'word' (by its own or a parent's name)."""
    n, seen = cls, set()
    while n and n not in seen:
        seen.add(n)
        if word.lower() in n.lower(): return True
        n = _super(n)
    return False


def ue_to_game(loc_cm, f):
    """Unreal cm (X forward, Y right, Z up) -> the export's glTF metres (X, Z, Y) -> position_engine (-gz, gy, gx) x f / 0.05."""
    gx, gy, gz = loc_cm[0] / 100.0, loc_cm[2] / 100.0, loc_cm[1] / 100.0
    k = f / 0.05
    return [round(-gz * k, 1), round(gy * k, 1), round(gx * k, 1)]


def ue_up(rot):
    """A component's up (Unreal (0, 0, 1) turned by its rotator) in the mounts' game frame."""
    if not rot: return [0.0, 1.0, 0.0]
    p, y, r = (math.radians(v) for v in rot)
    v = np.array([0.0, math.sin(r), math.cos(r)])                     # roll about X
    v = np.array([v[0] * math.cos(p) - v[2] * math.sin(p), v[1], v[0] * math.sin(p) + v[2] * math.cos(p)])   # pitch
    v = np.array([v[0] * math.cos(y) - v[1] * math.sin(y), v[0] * math.sin(y) + v[1] * math.cos(y), v[2]])   # yaw
    g = [-v[1], v[2], v[0]]   # (X, Y, Z) -> glTF (X, Z, Y) -> game (-gz, gy, gx)
    n = math.sqrt(sum(c * c for c in g)) or 1.0
    return [round(c / n, 3) for c in g]


def sockets(mesh_rel):
    """A mesh's sockets: [(name, loc cm, scale)] from its .json (static) or _Skeleton.json (skinned: relative to their
    bone, taken as at the root)."""
    out = []
    for f in (mesh_rel + '.json', mesh_rel + '_Skeleton.json'):
        p = os.path.join(SRC, 'Assets/Vehicles', f)
        if not os.path.exists(p): continue
        for o in json.load(open(p, encoding='utf-8-sig')):
            if o.get('Type') in ('StaticMeshSocket', 'SkeletalMeshSocket'):
                pr = o['Properties']; l = pr.get('RelativeLocation') or {}; s = pr.get('RelativeScale') or {}
                out.append((pr.get('SocketName', ''), [l.get('X', 0), l.get('Y', 0), l.get('Z', 0)], s.get('X', 1.0)))
    return out


def rear_engines(prims, f, n=4):
    """Engine points for a hull without engine sockets: its rear-most vertices (the last 2 % of its length) clustered across
    (y, z) into up to 'n' points, each sized by its cluster."""
    P = np.concatenate([a['POSITION'] for a, _, _ in prims])
    xmin, xmax = P[:, 0].min(), P[:, 0].max()
    rear = P[P[:, 0] < xmin + (xmax - xmin) * 0.02]
    if len(rear) < 8: return []
    pts = rear[:, 1:]
    k = min(n, max(1, len(pts) // 200))
    rng = np.random.default_rng(1)
    c = pts[rng.choice(len(pts), k, replace=False)]
    for _ in range(20):
        lab = np.argmin(((pts[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
        c = np.array([pts[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
    out = []
    for i in range(k):
        sel = rear[lab == i]
        if len(sel) == 0: continue
        r = float(np.sqrt(((sel[:, 1:] - c[i]) ** 2).sum(-1)).mean())
        loc = [float(sel[:, 0].min()) * 100, float(c[i][1]) * 100, float(c[i][0]) * 100]   # back to Unreal cm (X, Y=gz, Z=gy)
        out.append((ue_to_game(loc, f), max(1.0, r / 3.0)))
    return out


# ---- one ship -----------------------------------------------------------------------------------------------------------

def build_ship(sid, name, desc, race, kind, bp, meshes, turret, missile, hangar, extra_parts=None, traffic=True):
    prims = []
    for m in meshes:
        p = os.path.join(SRC, 'Assets/Vehicles', m + '.glb')
        if not os.path.exists(p): LOG(f'  {name}: missing {m}'); return None
        prims += read_prims(p)
    mn, mx = bounds(prims)
    size = mx - mn
    f = min(SCALE, MAX_SIZE / float(size.max()))
    mats_used = {}
    out = split_prims(f'{sid}_', prims, mats_used)
    rel = f'warships/{sid}.glb'
    write_glb(rel, out)
    length = float(size[0]) * f / 0.05   # game units, nose to tail (glTF x)
    mounts, subs = [], []
    # Engines: the mesh sockets SKT_Engine* (boosters as slotType 5), else from the rear of the hull.
    socks = [s for m in meshes for s in sockets(m)]
    eng = [s for s in socks if re.match(r'SKT_(Engine|Booster)', s[0], re.I)]
    for sname, loc, sc in eng:
        boost = 'booster' in sname.lower()
        mounts.append({'slotType': 5 if boost else 3, 'position_engine': ue_to_game(loc, f), 'socketScale': round(sc * f / SCALE, 3)})
    if not eng:
        for pos, r in rear_engines(prims, f):
            mounts.append({'slotType': 3, 'position_engine': pos, 'socketScale': round(r * f / SCALE, 3)})
    # The blueprint's child actors: turrets, drone / hangar spawners, missile turrets, weak spots.
    comps = components(bp) if bp else []
    n_turret = 0
    for cname, cls, mesh, loc, rot, sc in comps:
        if loc is None: continue
        low = (cname + ' ' + (cls or '')).lower()
        up = ue_up(rot)
        pos = ue_to_game(loc, f)
        if ((cls and isa(cls, 'Turret')) or (cname.startswith('Turret_') and 'Dummy' not in cname and not mesh)) and turret:
            n_turret += 1
            subs.append({'kind': 'turret', 'name': 'Turret', 'position_engine': pos, 'turretUp': up, 'item': turret, 'scale': round(f * (sc or 1.0), 3)})
        elif ('missileturretspawn' in low or 'missile' in low and 'spawn' in low) and missile:
            subs.append({'kind': 'turret', 'name': 'Missile launcher', 'position_engine': pos, 'turretUp': up, 'item': missile, 'scale': round(f * 0.4, 3)})
        elif cls and (isa(cls, 'DroneSpawner') or isa(cls, 'HangarSpawner')) and hangar:
            subs.append({'kind': 'hangar', 'model': 'none', 'name': 'Hangar', 'position_engine': pos, 'turretUp': up, 'ships': HANGAR_SHIPS[hangar],
                         'every': 30, 'perWave': 2, 'maxAlive': 4})
    # The carrier's launch arrows: one hangar per side.
    arrows = [(c, l) for c, cls, _, l, _, _ in comps if c.startswith('HangarLaunch') and l]
    if arrows and hangar:
        for side in ('Left', 'Right'):
            pts = [l for c, l in arrows if side in c]
            if pts:
                loc = np.mean(pts, axis=0).tolist()
                subs.append({'kind': 'hangar', 'model': 'none', 'name': 'Launch deck', 'position_engine': ue_to_game(loc, f),
                             'turretUp': [1.0 if side == 'Left' else -1.0, 0.0, 0.0], 'ships': HANGAR_SHIPS[hangar], 'every': 25, 'perWave': 2, 'maxAlive': 6})
    # Turret sockets on the mesh when the blueprint names none (the corvette, the battleship, the cruiser).
    if n_turret == 0 and turret:
        for sname, loc, sc in socks:
            if re.match(r'SKT_(Turret|SW|PW)', sname, re.I) and 'Engine' not in sname:
                subs.append({'kind': 'turret', 'name': 'Turret', 'position_engine': ue_to_game(loc, f), 'item': turret, 'scale': round(f * 0.6, 3)})
                n_turret += 1
    if extra_parts: subs += extra_parts
    materials = material_entries(sid, mats_used)
    ship = {'id': sid, 'name': name, 'description': desc, 'race': race,
            'armor': 20000 if kind == 'battleship' else 4000, 'cargo': 0, 'handling': 10, 'price': 0,
            'slots': {'primary': 0, 'secondary': 0, 'turret': 0, 'equipment': 0},
            'model': rel, 'modelLength': round(length), 'modelYaw': 90, 'engineStyle': 'es2',
            'mounts': mounts, 'materials': materials, 'subsystems': subs,
            'traffic': {'capital': kind, **({} if traffic else {'weight': 0})},
            'explosionScale': round(min(20.0, max(4.0, float(size.max()) * f / 250.0)), 1)}
    tris = sum(len(i) // 3 for _, i, _ in out)
    LOG(f'  {name}: {round(float(size.max()) * f)} m, {tris} triangles, {len(eng) or len([m for m in mounts if m["slotType"] == 3])} engines, '
        f'{sum(1 for s in subs if s["kind"] == "turret")} turrets, {sum(1 for s in subs if s["kind"] == "hangar")} hangars, '
        f'{sum(1 for s in subs if s.get("weakspot"))} weak spots, {len(materials)} materials')
    return ship, f, prims, mats_used


def build(log=print):
    """ships.json entries for the warships, freighters, the Dreadnought and their props."""
    os.makedirs(os.path.join(MOD, 'warships', 'maps'), exist_ok=True)
    Image.fromarray(np.zeros((4, 4, 4), np.uint8)).save(os.path.join(MOD, 'warships', 'maps', 'clear.png'))
    ships, props = [], []
    for sid, name, desc, race, kind, bp, meshes, turret, missile, hangar in WARSHIPS:
        r = build_ship(sid, name, desc, race, kind, bp, meshes, turret, missile, hangar)
        if not r: continue
        if sid == 'es2_okkar_frigate':   # its weak spots on ES2's weak point mesh
            subs, pr = frigate_weakpoints(r[1])
            r[0]['subsystems'] += subs; props += pr
        ships.append(r[0])
    for sid, name, desc, race, bp, meshes, turret in FREIGHTERS:
        r = build_ship(sid, name, desc, race, 'freighter', bp, meshes, turret, None, None)
        if r: ships.append(r[0])
    ships += build_dreadnought()
    return ships + props


# ---- the Mobile Homebase: a station that roams the galaxy (Modding.MobileStations), like the GoF3 Ships mod's Manticore ---

HOMEBASE_SYSTEM = 2            # its home (where its route starts; it roams every system)
HOMEBASE_STAY = 30             # minutes in each orbit ...
HOMEBASE_SYSTEM_MINUTES = 120  # ... and in each system


def build_homebase():
    """EVERSPACE 2's Mobile Homebase (SM_Warship_010, BP_Ship_Mobile_Homebase: the pilots' carrier with its hangar and casino)
    as stations.json's mobile station: no planet, it cruises through every system (two hours in each, half an hour per orbit)
    and is docked at wherever it is, into the game's Terran hangar and bar. Its model is centred on its bounds (as the remake
    centres a station's), its engine points the hull's rear's (it has no engine sockets), glowing in its cyan."""
    r = build_ship('es2_homebase', 'Mobile Homebase', '', 0, 'battleship', 'BP_Ship_Mobile_Homebase', ['Warships/Meshes/SM_Warship_010'], None, None, None)
    if not r: return []
    ship, f, prims, _ = r
    mn, mx = bounds(prims)
    centre = glb_to_game((mn + mx) / 2, f)
    engines = []
    for m in ship['mounts']:
        if m['slotType'] != 3: continue
        p = [round(m['position_engine'][i] - centre[i], 1) for i in range(3)]
        rad = max(250, round(m.get('socketScale', 1.0) * 450))
        engines.append({'position_engine': p, 'glowSize': [rad, rad, rad * 3]})
    return [{
        'id': 'es2_homebase', 'system': HOMEBASE_SYSTEM, 'name': 'Mobile Homebase', 'techLevel': 9, 'planet': 0, 'looksLike': 70,
        'model': ship['model'], 'modelSize': round(float((mx - mn).max()) * f / 0.05), 'modelYaw': 90, 'materials': ship['materials'],
        'interior': 'terran', 'hangar': 'es2_ships:homebase_hangar', 'bar': 'es2_ships:homebase_casino',
        'mobile': {'route': 'any', 'stayMinutes': HOMEBASE_STAY, 'systemMinutes': HOMEBASE_SYSTEM_MINUTES, 'speed': 0.12,
                   'race': 'terran', 'engines': engines, 'engineColor': [0.07, 0.89, 0.89]},
    }]


# ---- props: a subsystem's own model (a fixed object of the remake), as a ship that never flies -------------------------

def build_prop(pid, name, meshes, f, offsets=None):
    """A model for subsystems: the meshes (Vehicles/...; 'offsets' Unreal cm per mesh) centred on their bounds, at the
    hull's scale 'f'. Returns (ships.json entry, centre in the export's glTF metres)."""
    prims = []
    for k, m in enumerate(meshes):
        p = os.path.join(SRC, 'Assets/Vehicles', m + '.glb')
        if not os.path.exists(p): LOG(f'  prop {name}: missing {m}'); return None, None
        ps = read_prims(p)
        if offsets and offsets[k]:
            o = offsets[k]; d = np.array([o[0], o[2], o[1]], np.float32) / 100.0
            ps = [({**a, 'POSITION': a['POSITION'] + d}, t, n) for a, t, n in ps]
        prims += ps
    mn, mx = bounds(prims)
    centre = (mn + mx) / 2
    mats_used = {}
    out = split_prims(f'{pid}_', prims, mats_used)
    rel = f'warships/props/{pid}.glb'
    write_glb(rel, out, centre)
    size = mx - mn
    entry = {'id': pid, 'name': name, 'description': 'A part of an EVERSPACE 2 warship.', 'race': -1,
             'armor': 1000, 'cargo': 0, 'handling': 10, 'price': 0, 'slots': {'primary': 0, 'secondary': 0, 'turret': 0, 'equipment': 0},
             'model': rel, 'modelLength': max(1, round(float(size[0]) * f / 0.05)), 'modelYaw': 90,
             'materials': material_entries(pid, mats_used), 'traffic': {'weight': 0}, 'explosionScale': 2.0}
    return entry, centre


def glb_to_game(p, f):
    """The export's glTF metres -> position_engine."""
    k = f / 0.05
    return [round(-float(p[2]) * k, 1), round(float(p[1]) * k, 1), round(float(p[0]) * k, 1)]


# ---- the Dreadnought (its encounter: encounter.py) ----------------------------------------------------------------------

DREAD_SUBSYSTEM_PIECES = {   # stage pieces that become destroyable parts instead of hull
    'SM_Warship_006_Stage01_007_A', 'SM_Warship_006_Stage01_007_B', 'SM_Warship_006_Stage01_007_C', 'SM_Warship_006_Stage01_007_D',
    'SM_Warship_006_Stage01_011',
}
DREAD_SKIP = {'SK_Warship_006_Stage04_001', 'SK_Warship_006_Stage01_003'}   # the retractable sniper's duplicate, the lightning turret


def build_dreadnought():
    """The Dreadnought: BP_Dreadnought's stage pieces as one hull (its energy absorbing fields kept as "shieldMaterial"
    surfaces), its field emitters and shield generator as shield parts (stage 1, with the torpedo launchers), the sniper and
    lightning turrets (stage 2), the explosive weak points (stage 3), the flak and missile turrets and the hangars any time.
    Returns [the Dreadnought, its props]."""
    comps = components('BP_Dreadnought')
    pieces, offsets = [], []
    for cname, cls, mesh, loc, rot, sc in comps:
        if not mesh or not re.match(r'S[KM]_Warship_006', mesh) or mesh in DREAD_SKIP or mesh in DREAD_SUBSYSTEM_PIECES: continue
        if mesh in pieces: continue
        pieces.append('Warships/Meshes/' + mesh); offsets.append(loc)
    prims = []
    for m, o in zip(pieces, offsets):
        p = os.path.join(SRC, 'Assets/Vehicles', m + '.glb')
        if not os.path.exists(p): continue
        ps = read_prims(p)
        if o:
            d = np.array([o[0], o[2], o[1]], np.float32) / 100.0
            ps = [({**a, 'POSITION': a['POSITION'] + d}, t, n) for a, t, n in ps]
        prims += ps
    mn, mx = bounds(prims)
    size = mx - mn
    f = min(SCALE, MAX_SIZE / float(size.max()))
    mats_used = {}
    out = split_prims('es2_dreadnought_', prims, mats_used)
    # The energy absorbing fields: named so the ship's "shieldMaterial" finds them.
    renamed = {}
    for new, (src, ti) in list(mats_used.items()):
        if 'energyabsorbing' in src.lower():
            nn = new.replace('|', 'energyfield|'); renamed[new] = nn; mats_used[nn] = mats_used.pop(new)
    out = [(a, i, renamed.get(n, n)) for a, i, n in out]
    rel = 'warships/es2_dreadnought.glb'
    write_glb(rel, out)
    length = float(size[0]) * f / 0.05
    props = []
    subs = []
    def prop(pid, name, meshes, offs=None):
        e, c = build_prop(pid, name, meshes, f, offs)
        if e: props.append(e)
        return c
    # Stage 1: the field emitters and the shield generator (shields), the torpedo launchers.
    for k, letter in enumerate('ABCD'):
        c = prop(f'es2_prop_field_emitter_{letter.lower()}', 'Field emitter', [f'Warships/Meshes/SM_Warship_006_Stage01_007_{letter}'])
        if c is not None:
            subs.append({'kind': 'object', 'name': 'Field emitter', 'model': f'es2_ships:es2_prop_field_emitter_{letter.lower()}',
                         'position_engine': glb_to_game(c, f), 'shields': True, 'stage': 1, 'hull': 2600})
    c = prop('es2_prop_shield_generator', 'Shield generator', ['Warships/Meshes/SM_Warship_006_Stage01_011'])
    if c is not None:
        subs.append({'kind': 'object', 'name': 'Shield generator', 'model': 'es2_ships:es2_prop_shield_generator',
                     'position_engine': glb_to_game(c, f), 'shields': True, 'stage': 1, 'hull': 4000})
    wp = prop('es2_prop_weak_point', 'Weak point', ['Warships/Meshes/SM_Warship_008_Weakpoint'])
    for cname, cls, mesh, loc, rot, sc in comps:
        if loc is None: continue
        pos = ue_to_game(loc, f); up = ue_up(rot)
        if cls and 'TorpedoLauncher' in cname and 'Socket' not in cname:
            subs.append({'kind': 'turret', 'name': 'Torpedo launcher', 'position_engine': pos, 'turretUp': up, 'item': T('turret_dread_torpedo'),
                         'scale': round(f * 1.4, 3), 'stage': 1, 'hull': 2200})
        elif cls and 'SniperTurret' in cname:
            subs.append({'kind': 'turret', 'name': 'Sniper turret', 'position_engine': pos, 'turretUp': up, 'item': T('turret_dread_sniper'),
                         'scale': round(f * 2.5, 3), 'stage': 2, 'hull': 2400})
        elif cls and 'LightningTurret' in cname:
            subs.append({'kind': 'turret', 'name': 'Lightning turret', 'position_engine': pos, 'turretUp': up, 'item': T('turret_dread_lightning'),
                         'scale': round(f * 3.0, 3), 'stage': 2, 'hull': 3000})
        elif cls and 'Homebase_Turret' in cname:
            subs.append({'kind': 'turret', 'name': 'Flak turret', 'position_engine': pos, 'turretUp': up, 'item': T('turret_dread_flak'),
                         'scale': round(f * 1.0, 3), 'hull': 1800})
        elif cls and 'HomingMissile_Turret' in cname:
            subs.append({'kind': 'turret', 'name': 'Missile turret', 'position_engine': pos, 'turretUp': up, 'item': T('turret_dread_missile'),
                         'scale': round(f * 1.2, 3), 'hull': 1800})
        elif cls and 'Hangar' in cname and isa(cls, 'HangarSpawner'):
            subs.append({'kind': 'hangar', 'model': 'none', 'name': 'Hangar', 'position_engine': pos, 'turretUp': [0.0, 0.0, 1.0],
                         'ships': HANGAR_SHIPS['dreadnought'], 'every': 35, 'perWave': 2, 'maxAlive': 3, 'total': 8})
        elif cname.startswith('ExplosiveWeakPointLocation') and wp is not None:
            subs.append({'kind': 'object', 'name': 'Weak point', 'model': 'es2_ships:es2_prop_weak_point', 'position_engine': pos,
                         'turretUp': up, 'scale': round(3.0 * (sc or 1.0), 3), 'stage': 3, 'weakspot': 2.5, 'bonus': 0.08, 'hull': 1500})
    # The four thrusters (its heat volumes behind them).
    mounts = []
    for cname, cls, mesh, loc, rot, sc in comps:
        if 'Thruster_HeatVolume' in cname and loc:
            mounts.append({'slotType': 3, 'position_engine': ue_to_game([loc[0] + 2000, loc[1], loc[2]], f), 'socketScale': round(28 * f / SCALE, 3)})
    materials = material_entries('es2_dreadnought', mats_used)
    ship = {'id': 'es2_dreadnought', 'name': 'Dreadnought', 'race': 8,
            'description': 'The Outlaws\' Dreadnought: a flying fortress of EVERSPACE 2, its hull shielded by energy absorbing fields, '
                           'armed with torpedo launchers, sniper and lightning turrets, flak and missile batteries, and five hangars of fighters.',
            'armor': 60000, 'cargo': 0, 'handling': 5, 'price': 0, 'slots': {'primary': 0, 'secondary': 0, 'turret': 0, 'equipment': 0},
            'model': rel, 'modelLength': round(length), 'modelYaw': 90, 'engineStyle': 'es2', 'mounts': mounts, 'materials': materials,
            'subsystems': subs, 'shieldMaterial': 'energyfield|', 'shieldedDamage': 0.0, 'hullFactor': 6.0,
            'traffic': {'capital': 'battleship', 'weight': 0}, 'explosionScale': 20.0}
    tris = sum(len(i) // 3 for _, i, _ in out)
    LOG(f'  Dreadnought: {round(float(size.max()) * f)} m, {tris} triangles, {len(pieces)} pieces, {len(subs)} subsystems '
        f'({sum(1 for s in subs if s.get("shields"))} shield, {sum(1 for s in subs if s["kind"] == "turret")} turrets, '
        f'{sum(1 for s in subs if s["kind"] == "hangar")} hangars, {sum(1 for s in subs if s.get("weakspot"))} weak points), {len(props)} props')
    return [ship] + props


def frigate_weakpoints(f):
    """The Okkar frigate's eight weak spots (BP_Okkar_Frigate's Weakspot_* child actors) on ES2's weak point mesh."""
    e, c = build_prop('es2_prop_okkar_weakpoint', 'Weak spot', ['Warships/Meshes/SM_Warship_008_Weakpoint'], f)
    if not e: return [], []
    subs = []
    for cname, cls, mesh, loc, rot, sc in components('BP_Okkar_Frigate'):
        if cls and isa(cls, 'Weakspot') and loc:
            subs.append({'kind': 'object', 'name': 'Weak spot', 'model': 'es2_ships:es2_prop_okkar_weakpoint', 'position_engine': ue_to_game(loc, f),
                         'turretUp': ue_up(rot), 'weakspot': 3.0, 'bonus': 0.06, 'hull': 1200})
    return subs, [e]
