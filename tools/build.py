# Builds the es2_ships mod (the GoF2 remake's customizable ships) from the player's own FModel export of EVERSPACE 2 (the
# ship module, weapon and turret meshes as glTF, their textures as PNG, the data tables and mesh properties as JSON). Run by
# ../import.py; nothing of EVERSPACE 2 comes with this importer. The mod it writes holds ROCKFISH Games' copyrighted models,
# textures and data: it is for the player's own use, built from their own copy of the game. Don't share the built mod.
import json, os, re, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import glbtool, jobs

SRC = MOD = TEX = TABLES = WEAPONS = TURRET = None   # configure()

def configure(src, out):
    global SRC, MOD, TEX, TABLES, WEAPONS, TURRET
    SRC, MOD = src, out
    TEX = os.path.join(SRC, 'Assets/Vehicles/ShipModules/Shared/Textures')
    TABLES = os.path.join(SRC, 'Blueprints/DataTables')
    WEAPONS = os.path.join(SRC, 'Assets/Equipment/Weapons')
    TURRET = os.path.join(SRC, 'Assets/Turrets/Meshes/SK_Turret_PlayerShip_001.glb')

def has_weapons():
    return os.path.exists(os.path.join(WEAPONS, 'Meshes/SM_PrimaryWeapon_005.glb')) and os.path.isdir(os.path.join(WEAPONS, 'Textures'))

def has_turret():
    return os.path.exists(TURRET)
SCALE = 3.6          # Unity metres per ES2 metre: a ~14 m Medium ship becomes ~50 m, the size of GoF2's fighters
GAME = SCALE / 0.05  # game units per ES2 metre
CLASSES = ['Light', 'Medium', 'Heavy']
# EShip -> (the kit type id, the ship's name in game), as the debug builds' names show them.
TYPES = {'PatrolShip': ('vanguard', 'Vanguard'), 'Scout': ('scout', 'Scout'), 'SpecOps': ('stinger', 'Stinger'),
         'Interceptor': ('interceptor', 'Interceptor'), 'Sentinel': ('sentinel', 'Sentinel'), 'AssaultFighter': ('striker', 'Striker'),
         'Bomber': ('bomber', 'Bomber'), 'Defender': ('vindicator', 'Vindicator'), 'Gunship': ('gunship', 'Gunship')}
# Model names the debug builds give wings whose table name is empty (DT_DebugShipsKS: Scout_Spirit, ...).
KNOWN = {('Light', 'Wings_005'): 'Spirit', ('Light', 'Wings_011'): 'Wasp', ('Light', 'Wings_002'): 'Mercury',
         ('Heavy', 'Wings_009'): 'Liberator', ('Heavy', 'Wings_005'): 'Typhoon'}
SLOT = {'Base': 'base', 'Body': 'body', 'Rear': 'rear', 'Cockpit': 'cockpit', 'CockpitInterior': 'interior', 'Wings': 'wings'}
# GoF2-side stats per type (the ES2 items' stats are built at run time, not in the export): handling, armour, cargo, slots, price.
STATS = {'scout': (165, 260, 30, (2, 1, 0, 8), 1900000), 'stinger': (160, 280, 25, (3, 1, 0, 8), 2100000),
         'vanguard': (150, 310, 35, (2, 2, 0, 9), 2000000), 'interceptor': (155, 330, 35, (3, 1, 0, 9), 2400000),
         'sentinel': (125, 480, 55, (3, 2, 0, 10), 2900000), 'striker': (135, 400, 45, (4, 2, 0, 9), 3100000),
         'gunship': (100, 650, 70, (4, 2, 0, 10), 3800000), 'bomber': (90, 700, 80, (2, 4, 0, 10), 3900000),
         'vindicator': (95, 760, 75, (3, 2, 0, 11), 4200000)}
DESC = {'scout': 'A Light hull for speed and agility.', 'stinger': 'A Light hull built to strike hard and fast.',
        'vanguard': 'A sturdy Light hull with room for missiles.', 'interceptor': 'A Medium hull built for speed: the fastest turns of its class.',
        'sentinel': 'The balanced Medium hull: solid armour, room for equipment.', 'striker': 'A Medium hull with the most guns of its class.',
        'gunship': 'A Heavy hull carrying a battery of guns.', 'bomber': 'A Heavy hull built around its missile racks.',
        'vindicator': 'The toughest Heavy hull: thick armour, room for equipment.'}

def table(name):
    d = json.load(open(os.path.join(TABLES, name), encoding='utf-8-sig'))
    return (d[0] if isinstance(d, list) else d)['Rows']

def mesh_of(cls, asset):
    name = asset['AssetPathName'].rsplit('/', 1)[-1].split('.')[0]
    return os.path.join(SRC, f'Assets/Vehicles/ShipModules/{cls}/Meshes/{name}.glb'), name

def hull_split(g, binary, p):
    # The hull's vertex colours are pure R / G / B masks: ES2's three hull colours. Each triangle takes its vertices'
    # majority (93-98 % of the triangles are one colour) and goes to the material Paint1 / 2 / 3 (the kit's colour slots).
    name = g['materials'][p['material']].get('name', '') if 'material' in p else ''
    if 'Floaters_Emissive' in name: return glow_split(g, binary, p)
    if 'TechDetails' in name: return tech_split(g, binary, p, name)
    if 'ShipModules_Floaters' in name and 'Floaters_002' not in name: return floater_split(g, binary, p, name)
    if 'Hull' not in name or 'COLOR_0' not in p['attributes'] or 'indices' not in p: return None
    col, _ = glbtool.read(g, binary, p['attributes']['COLOR_0'])
    idx, _ = glbtool.read(g, binary, p['indices'])
    tri = idx.reshape(-1, 3).astype(np.int64)
    rgb = col[:, :3].astype(np.float32)
    k = (rgb[tri[:, 0]] + rgb[tri[:, 1]] + rgb[tri[:, 2]]).argmax(axis=1)
    return [(f'Paint{c + 1}', tri[k == c].reshape(-1)) for c in range(3)]

# The TechDetails lights: T_ShipModules_TechDetails_00N_E paints each light in its sector's ID colour (its legend: ID04
# cyan, ID05 yellow, ID06 orange, ID07 red-orange); ES2 lights each sector in one of the ship's colours. The triangles
# showing a lit texel go to "Lamp<N>_S<id>" by their sector (the most common among a grid of samples over each
# triangle's UVs; the export's V runs the other way from the image), the rest stays the unlit TechDetails.
SECTOR_IDS = np.array([[0, 115, 159], [203, 154, 0], [181, 99, 0], [192, 56, 0]], np.float32)
_sector_maps = {}

def sector_map(n):
    if n not in _sector_maps:
        f = os.path.join(TEX, f'T_ShipModules_TechDetails_00{n}_E.png')
        _sector_maps[n] = np.array(Image.open(f).convert('RGB')) if os.path.exists(f) else None
    return _sector_maps[n]

def tech_split(g, binary, p, name):
    n = 2 if '002' in name else 1
    tex = sector_map(n)
    if tex is None or 'TEXCOORD_0' not in p['attributes'] or 'indices' not in p: return None
    uv = glbtool.read(g, binary, p['attributes']['TEXCOORD_0'])[0].astype(np.float32)
    tri = glbtool.read(g, binary, p['indices'])[0].reshape(-1, 3).astype(np.int64)
    k = 6
    w = np.array([(a / k, b / k) for a in range(k + 1) for b in range(k + 1 - a)], np.float32)
    pts = (uv[tri[:, 0]][:, None] * (1 - w[:, 0] - w[:, 1])[None, :, None] + uv[tri[:, 1]][:, None] * w[None, :, 0, None]
           + uv[tri[:, 2]][:, None] * w[None, :, 1, None])
    h, wd = tex.shape[:2]
    x = (np.mod(pts[..., 0], 1) * wd).astype(int).clip(0, wd - 1)
    y = (np.mod(1 - pts[..., 1], 1) * h).astype(int).clip(0, h - 1)
    px = tex[y, x].astype(np.float32)
    peak = px.max(-1)
    unit = px / np.maximum(peak[..., None], 1)
    ref = SECTOR_IDS / SECTOR_IDS.max(1, keepdims=True)
    ids = ((unit[..., None, :] - ref) ** 2).sum(-1).argmin(-1)
    ids = np.where(peak > 40, ids, -1)
    label = np.full(len(tri), -1)
    for i, row in enumerate(ids):
        r = row[row >= 0]
        if len(r): label[i] = np.bincount(r).argmax()
    out = [(name, tri[label < 0].reshape(-1))]
    out += [(f'Lamp{n}_S{4 + s}', tri[label == s].reshape(-1)) for s in range(4)]
    return out

# M_ShipModules_Floaters_Parent, as its compiled pixel shader computes it: the colour (T_ShipModules_Floaters_001_C_A)
# x its R_MT_E's blue x "Emissive Intensity" (MI_ShipModules_Floaters_001: 30) always glows (a few vents and grilles of the
# atlas), and the cybernetic glow is R_MT_E's alpha (three strips in the atlas' top left corner, which the thin inset
# strips along the panels map onto) x EdgeLighting^3 x 80 x EdgeLightingIntensity x EdgeLightingColor. The faces that
# show a lit alpha texel go to "CyberStrip"; the rest are alpha-cut detail cards.
_floater_masks = {}

def floater_mask():
    if 'm' not in _floater_masks:
        f = os.path.join(SRC, 'Assets/Vehicles/ShipModules/Shared/Textures/T_ShipModules_Floaters_001_R_MT_E.png')
        _floater_masks['m'] = np.array(Image.open(f).convert('RGBA')) if os.path.exists(f) else None
    return _floater_masks['m']

def floater_split(g, binary, p, name):
    if 'TEXCOORD_0' not in p['attributes'] or 'indices' not in p: return None
    uv = glbtool.read(g, binary, p['attributes']['TEXCOORD_0'])[0].astype(np.float32)
    tri = glbtool.read(g, binary, p['indices'])[0].reshape(-1, 3).astype(np.int64)
    tex = floater_mask()
    if tex is None:   # (without the mask: the strip texture's corner)
        c = uv[tri].mean(axis=1)
        strip = (np.mod(c[:, 0], 1) < 0.25) & (np.mod(c[:, 1], 1) < 0.15)
    else:
        k = 4
        w = np.array([(a / k, b / k) for a in range(k + 1) for b in range(k + 1 - a)], np.float32)
        pts = (uv[tri[:, 0]][:, None] * (1 - w[:, 0] - w[:, 1])[None, :, None] + uv[tri[:, 1]][:, None] * w[None, :, 0, None]
               + uv[tri[:, 2]][:, None] * w[None, :, 1, None])
        h, wd = tex.shape[:2]
        x = (np.mod(pts[..., 0], 1) * wd).astype(int).clip(0, wd - 1)
        y = (np.mod(pts[..., 1], 1) * h).astype(int).clip(0, h - 1)
        strip = tex[y, x, 3].max(axis=1) > 40
    return [(name, tri[~strip].reshape(-1)), ('CyberStrip', tri[strip].reshape(-1))]

def glow_split(g, binary, p):
    # M_Vehicles_Floaters_Emissive, as its compiled pixel shader computes it (research/floater_emissive.md):
    #   the UV quadrant picks the slot: u < 0.5, v < 0.5 Emissive 1 (EmissiveIntensityHigh 20 x EmissiveColor1, always on),
    #   u >= 0.5, v < 0.5 Emissive 2 (EmissiveIntensityLow 2 x EmissiveColor2, always on), u < 0.5, v >= 0.5 the engine
    #   (EngineGlowIntensity x EngineColor x the thrust), u >= 0.5, v >= 0.5 the booster (BoosterGlowIntensity x
    #   BoostColor x the boost, or CruiseMode);
    #   the mask is T_Vehicles_Floaters_Emissive_M's red x green at twice the UV (each quadrant shows the whole atlas:
    #   floater_e.png, a 2 x 2 tiling of it);
    #   x the vertex colour's red channel: black, green and cyan faces (red 0) stay dark (NozzleOff); a dimmer red dims it
    #   (the "_R33" / "_R67" materials, their masks at a third / two thirds).
    # The rules matched by eye before (vertex colours and atlas rows) mostly fell out of the quadrants; where they didn't
    # (black faces in Emissive 2, green "hot discs", white nozzle faces in the engine colour) the shader wins.
    if 'COLOR_0' not in p['attributes'] or 'indices' not in p or 'TEXCOORD_0' not in p['attributes']: return None
    col, _ = glbtool.read(g, binary, p['attributes']['COLOR_0'])
    col = col[:, :3].astype(np.float32)
    if col.max() > 1.5: col /= 255.0
    tri = glbtool.read(g, binary, p['indices'])[0].reshape(-1, 3).astype(np.int64)
    red = col[tri, 0].mean(axis=1)
    uv = glbtool.read(g, binary, p['attributes']['TEXCOORD_0'])[0].astype(np.float32)
    u = np.mod(uv[tri, 0].mean(axis=1), 1.0); v = np.mod(uv[tri, 1].mean(axis=1), 1.0)
    quad = np.where(v < 0.5, np.where(u < 0.5, 0, 1), np.where(u < 0.5, 2, 3))
    level = np.where(red < 0.1, -1, np.where(red < 0.5, 1, np.where(red < 0.85, 2, 3)))   # off, 1/3, 2/3, full
    out = [('NozzleOff', tri[level < 0].reshape(-1))]
    for q, name in enumerate(('Ring1', 'Ring2', 'NozzleGlow', 'BoostVent')):
        for lv, suffix in ((3, ''), (2, '_R67'), (1, '_R33')):
            m = (quad == q) & (level == lv)
            if m.any(): out.append((name + suffix, tri[m].reshape(-1)))
    if SHIMMER:   # (the engine glow's faces again: the additive shimmer over them)
        out.append(('NozzleShimmer', tri[(quad == 2) & (level > 0)].reshape(-1)))
    return out

def holo_rings(g, binary, p):
    # The hologram's stacked rings carry their animation in their vertex colours (M_ShipModules_Holograms): red the spin
    # (0 / 0.5 / 1 = one way / still / the other way), blue the share of the hover. TEXCOORD_1 for GoF2/ModHologram: x the
    # spin -1..1, y 1 - the hover share (glTFast flips V, so the shader reads the share).
    if 'COLOR_0' not in p['attributes']: return None
    col = glbtool.read(g, binary, p['attributes']['COLOR_0'])[0][:, :3].astype(np.float32)
    if col.max() > 1.5: col /= 255.0
    return {'TEXCOORD_1': np.stack([col[:, 0] * 2 - 1, 1 - col[:, 2]], axis=1)}

def flame_across(g, binary, p):
    # The engine flames (M_Vehicle_EngineExhaust) are crossed flat cards, UV u from the nozzle to the tip. TEXCOORD_1 gets
    # each card's coordinate across it (x 0..1) and its kind in y, read as |y - 0.5| so a V flip by the loader changes
    # nothing: 0.5 a main flame card (red), 0.25 a boost card (green); so GoF2/ModEngineFlame can fade its long edges
    # and show the boost cards only while boosting (only some
    # cards' normals are bent for ES2's own edge fade). A card = the triangles sharing vertex indices.
    name = g['materials'][p['material']].get('name', '') if 'material' in p else ''
    if 'Holograms' in name: return holo_rings(g, binary, p)
    if 'EngineExhaust' not in name or 'indices' not in p or 'TEXCOORD_0' not in p['attributes']: return None
    pos = glbtool.read(g, binary, p['attributes']['POSITION'])[0].astype(np.float64)
    uv = glbtool.read(g, binary, p['attributes']['TEXCOORD_0'])[0].astype(np.float64)
    tri = glbtool.read(g, binary, p['indices'])[0].reshape(-1, 3).astype(np.int64)
    parent = np.arange(len(pos))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, c in tri:
        ra, rb, rc = find(a), find(b), find(c); parent[rb] = ra; parent[find(rc)] = ra
    roots = np.array([find(i) for i in range(len(pos))])
    col = None
    if 'COLOR_0' in p['attributes']:
        col = glbtool.read(g, binary, p['attributes']['COLOR_0'])[0][:, :3].astype(np.float32)
        if col.max() > 1.5: col /= 255.0
    out = np.zeros((len(pos), 2), np.float32)
    for r in np.unique(roots):
        c = np.where(roots == r)[0]
        q, u = pos[c], uv[c, 0]
        d = np.linalg.lstsq(np.c_[u, np.ones(len(u))], q, rcond=None)[0][0] if np.ptp(u) > 1e-4 else np.array([-1.0, 0, 0])
        d = d / (np.linalg.norm(d) or 1.0)
        rest = q - np.outer(q @ d, d); rest -= rest.mean(axis=0)
        e = np.linalg.eigh(rest.T @ rest)[1][:, -1]
        t = rest @ e
        out[c, 0] = (t - t.min()) / np.ptp(t) if np.ptp(t) > 1e-5 else 0.5
        # ES2's vertex colours: red cards burn with the thrust, green ones only while boosting (the boost jets).
        boost = col is not None and col[c, 1].mean() > 0.5 and col[c, 0].mean() < 0.5
        out[c, 1] = 0.25 if boost else 0.5
    return {'TEXCOORD_1': out}

bounds = {}   # out file -> (min, max) in ES2 metres, glTF axes (+X nose, +Y up, Z side)

# ES2's mesh sockets (the meshes' property JSON): SKT_PWSlot primary weapons, SKT_SWSlot secondaries, SKT_Turret turrets,
# SKT_Engine exhausts, SKT_Booster booster points (the remake's slotType 5: where EVERSPACE 2 puts a booster's engine trail and
# light, Modding.Es2EngineVfx). Unreal centimetres, X forward, Y side, Z up -> the export's glTF metres (X, Z, Y).
SOCKETS = [(re.compile(r'^SKT_PWSlot'), 0), (re.compile(r'^SKT_SWSlot'), 1), (re.compile(r'^SKT_Turret'), 2), (re.compile(r'^SKT_Engine'), 3),
           (re.compile(r'^SKT_Booster'), 5)]
MAX_EXHAUSTS = 4   # per part: some rears have a dozen nozzles, and each exhaust is a particle system (phones)

def socket_counts(glb_path):
    """How many sockets of each mount type a part's mesh has (before the exhaust cap)."""
    jpath = glb_path[:-4] + '.json'
    c = {0: 0, 1: 0, 2: 0, 3: 0, 5: 0}
    if not os.path.exists(jpath): return c
    for o in json.load(open(jpath, encoding='utf-8-sig')):
        if o.get('Type') == 'StaticMeshSocket':
            name = o['Properties'].get('SocketName', '')
            t = next((t for rx, t in SOCKETS if rx.match(name)), None)
            if t is not None: c[t] += 1
    return c

def unreal_forward(rot):
    # An Unreal rotator's forward axis (X forward, Y right, Z up; roll doesn't move it).
    pitch, yaw = np.radians(rot.get('Pitch', 0.0)), np.radians(rot.get('Yaw', 0.0))
    return np.array([np.cos(pitch) * np.cos(yaw), np.cos(pitch) * np.sin(yaw), np.sin(pitch)])

def thruster_mounts(glb_path):
    # SKT_LateralThruster sockets: ES2's small manoeuvring jets (P_Vehicle_LateralThruster), each blowing along its
    # socket's forward axis whenever the ship strafes, rises, sinks or reverses against it (checked in the game). Mount
    # slotType 4 with 'direction' in position_engine's convention.
    jpath = glb_path[:-4] + '.json'
    if not os.path.exists(jpath): return []
    out = []
    for o in json.load(open(jpath, encoding='utf-8-sig')):
        if o.get('Type') != 'StaticMeshSocket': continue
        pr = o['Properties']
        if not pr.get('SocketName', '').startswith('SKT_LateralThruster'): continue
        l = pr.get('RelativeLocation') or {}
        f = unreal_forward(pr.get('RelativeRotation') or {})
        # Unreal (X, Y, Z) -> glTF (X, Z, Y) -> position_engine (-gz, gy, gx) = (-Y, Z, X)
        m = mount(l.get('X', 0) / 100, l.get('Z', 0) / 100, l.get('Y', 0) / 100, 4)
        m['direction'] = [round(float(-f[1]), 3), round(float(f[2]), 3), round(float(f[0]), 3)]
        out.append(m)
    return out

def part_mounts(glb_path):
    jpath = glb_path[:-4] + '.json'
    if not os.path.exists(jpath): return []
    found = []
    for o in json.load(open(jpath, encoding='utf-8-sig')):
        if o.get('Type') != 'StaticMeshSocket': continue
        pr = o['Properties']; name = pr.get('SocketName', '')
        slot = next((t for rx, t in SOCKETS if rx.match(name)), None)
        if slot is None: continue
        l = pr.get('RelativeLocation') or {}
        num = int(re.sub(r'\D', '', name) or 0)
        roll = abs((pr.get('RelativeRotation') or {}).get('Roll', 0.0))
        # the socket's scale (its largest axis): EVERSPACE 2 sizes the engine lights, trails and glow there by it
        sc = pr.get('RelativeScale') or {}
        scale = max(abs(sc.get('X', 1.0)), abs(sc.get('Y', 1.0)), abs(sc.get('Z', 1.0))) if sc else 1.0
        found.append((slot, num, l.get('X', 0) / 100, l.get('Z', 0) / 100, l.get('Y', 0) / 100, roll, scale))
    out = []
    for slot in (0, 1, 2, 3, 5):
        group = sorted((f for f in found if f[0] == slot), key=lambda f: f[1])
        if slot == 3 and len(group) > MAX_EXHAUSTS:   # keep an even spread across the side
            group = sorted(group, key=lambda f: f[4])
            group = [group[round(i * (len(group) - 1) / (MAX_EXHAUSTS - 1))] for i in range(MAX_EXHAUSTS)]
        for f in group:
            extra = None
            if slot == 2:   # the ship's own turret socket: the turret item fires from here, no GoF2 turret model on it
                extra = {'builtIn': True}
                if f[5] > 90: extra['upsideDown'] = True
            if slot == 3:
                size = 40 if len(group) <= 2 else 28
                extra = {'turretAngles': [0.6, 0.6, 0.6], 'glowSize': [size, size, size * 2.2]}
            if slot in (3, 5) and abs(f[6] - 1.0) > 1e-3:
                extra = dict(extra or {}, socketScale=round(f[6], 3))
            out.append(mount(f[2], f[3], f[4], slot, extra))
    return out + thruster_mounts(glb_path)

def convert(src, out):
    if not os.path.exists(src): print('  missing', os.path.basename(src)); return None
    glbtool.rewrite(src, os.path.join(MOD, out), split=hull_split, extra=flame_across)
    g, b = glbtool.load(src)
    mn, mx = np.full(3, 1e9), np.full(3, -1e9)
    for m in g.get('meshes', []):
        for p in m['primitives']:
            a = g['accessors'][p['attributes']['POSITION']]
            if 'min' in a: mn = np.minimum(mn, a['min']); mx = np.maximum(mx, a['max'])
    bounds[out] = (mn, mx)
    return out

def build_kit(cls):
    rows = table(f'DT_ShipModules_{cls}.json')
    parts, counts, exhaust = [], {}, []
    for rid, r in rows.items():
        kind = r['Type'].split('::')[1]
        if kind not in SLOT: continue   # Invalid: cut or unreleased
        src, mesh = mesh_of(cls, r['Asset'])
        out = convert(src, f'parts/{mesh.lower()}.glb')
        if out is None: continue
        slot = SLOT[kind]
        counts[slot] = counts.get(slot, 0) + 1
        types = [TYPES[t.split('::')[1]][0] for t in r.get('ShipsWhiteList') or [] if t.split('::')[1] in TYPES]
        mn = r['ModuleName']
        name = mn.get('SourceString') if isinstance(mn, dict) else None
        if not name:
            name = KNOWN.get((cls, rid))
        if not name:
            name = {'base': 'Base', 'interior': f'Interior {counts[slot]}', 'cockpit': f'Canopy {counts[slot]}',
                    'body': f'Body {counts[slot]}', 'rear': f'Rear {counts[slot]}'}.get(slot)
        if not name:   # an unnamed wing set: its type and a letter
            n = sum(1 for p in parts if p['slot'] == 'wings' and p.get('types') == types) + 1
            name = f"{TYPES_BY_ID[types[0]]} {chr(64 + n)}" if types else f'Wings {counts[slot]}'
        p = {'id': re.sub(r'[^a-z0-9_]', '_', (name if slot in ('wings', 'body', 'rear') else rid).lower()), 'slot': slot, 'name': name, 'model': out, 'table': rid}
        if types: p['types'] = types
        # The canopy and the cockpit interior sit on the body's SKT_Cockpit socket (each body has its own), modelled at their
        # own origin.
        if slot == 'body':
            skt = socket_pos(src[:-4] + '.json', r'^SKT_Cockpit') if os.path.exists(src[:-4] + '.json') else None
            if skt: p['anchors'] = {'cockpit': [round(v, 4) for v in skt]}
        elif slot in ('cockpit', 'interior'):
            p['anchor'] = 'cockpit'
        tiers = [convert(mesh_of(cls, e['Asset'])[0], f"parts/{mesh_of(cls, e['Asset'])[1].lower()}.glb")
                 for e in r.get('Extensions') or [] if not e.get('bExludeFromGame')]
        tiers = [t for t in tiers if t]
        if tiers: p['tiers'] = tiers
        mounts = part_mounts(src)
        if mounts: p['mounts'] = mounts
        tier_mounts = [part_mounts(mesh_of(cls, e['Asset'])[0]) for e in r.get('Extensions') or [] if not e.get('bExludeFromGame')]
        if any(tier_mounts): p['tierMounts'] = tier_mounts
        if slot == 'rear': exhaust.extend(exhaust_points(src))
        p['_sockets'] = socket_counts(src)
        parts.append(p)
    # Unique part ids in the kit (a name used twice gets its table row's number).
    seen = {}
    for p in parts:
        if p['id'] in seen: p['id'] = p['id'] + '_' + p['table'].lower()
        seen[p['id']] = True
    return parts, (np.mean(exhaust, axis=0) if exhaust else np.array([-4.8, 0.0, 0.0]))

TYPES_BY_ID = {v[0]: v[1] for v in TYPES.values()}

def exhaust_points(src):
    g, b = glbtool.load(src)
    pts = []
    for m in g['meshes']:
        for p in m['primitives']:
            if 'EngineExhaust' in g['materials'][p['material']]['name']:
                pos, _ = glbtool.read(g, b, p['attributes']['POSITION']); pts.append(pos.mean(axis=0))
    return pts

def save(arr, name, size=None):
    jobs.write_image(os.path.join(MOD, 'maps', name), arr, size, square=True)   # (on a worker)

def textures():
    def load(n): return np.array(Image.open(os.path.join(TEX, n)).convert('RGBA'))
    for src, dst, size in [('T_ShipModules_Hull_001', 'hull', 1024), ('T_ShipModules_TechDetails_001', 'tech1', 2048),
                           ('T_ShipModules_TechDetails_002', 'tech2', 2048), ('T_ShipModules_Floaters_001', 'floaters1', 1024)]:
        c = load(src + ('_C_A.png' if 'Floaters' in src else '_C_AO.png'))
        if 'Floaters' in src:
            save(c.copy(), dst + '_ca.png', size)   # (with the detail cards' cut-out alpha)
            # The cybernetic glow's mask (R_MT_E's alpha) and the always-on glow (the colour x R_MT_E's blue), as
            # M_ShipModules_Floaters_Parent computes them.
            rmte = load(src + '_R_MT_E.png')
            save(np.repeat(rmte[..., 3:4], 3, axis=2).copy(), 'cyberstrip_e.png', size)
            glow = (c[..., :3].astype(np.float32) * (rmte[..., 2:3].astype(np.float32) / 255.0)).round().astype(np.uint8)
            save(glow, 'floaters1_glow_e.png', size)
        if dst == 'hull':
            # The hull's colour map is a flat grey (0.686, linear 0.43) with a few percent of variation: ES2 paints the hull
            # in its colour set's colours as they are (its white burns white), so the map is scaled to average white, or
            # every paint colour came out at 43 % (white a mid grey, the dark colours near black).
            lin = (c[..., :3].astype(np.float64) / 255.0) ** 2.2
            lin = np.clip(lin / lin.mean(), 0, 1)
            c = c.copy(); c[..., :3] = (lin ** (1 / 2.2) * 255).round().astype(np.uint8)
        save(c[..., :3].copy(), dst + '_c.png', size)
        n = load(src + '_N.png'); n[..., 1] = 255 - n[..., 1]   # Unreal's DirectX normal map -> Unity's (green up)
        save(n[..., :3].copy(), dst + '_n.png', size)
        r = load(src + '_R_MT_E.png')
        ms = np.zeros_like(r); ms[..., 0] = ms[..., 1] = ms[..., 2] = r[..., 1]; ms[..., 3] = 255 - r[..., 0]
        save(ms, dst + '_ms.png', size)   # URP: metallic in R, smoothness in A
        e_file = os.path.join(TEX, src + '_E.png')
        if os.path.exists(e_file):
            e = load(src + '_E.png')[..., :3].max(axis=2, keepdims=True)   # the sectors' ID colours -> brightness
            e = np.repeat(e, 3, axis=2).copy()
        else:
            e = np.repeat(r[..., 2:3], 3, axis=2)
        save(e, dst + '_e.png', size)
    save(np.zeros((4, 4, 4), np.uint8), 'clear.png')   # the decals, cut away (they need ES2's decal atlas and projections)
    # The engine flames' noise (M_Vehicle_EngineExhaust's T_Noise_018_M, tiling grey noise; optional: flat flames without it).
    # The floater glow's mask (M_Vehicles_Floaters_Emissive's T_Vehicles_Floaters_Emissive_M; optional: the whole faces
    # glow without it).
    global FLAME_NOISE, NOZZLE_MASK, HOLO_MASK
    holo = os.path.join(SRC, 'Assets/Vehicles/Shared/Textures/T_ShipModules_FX_001_M_A.png')
    HOLO_MASK = os.path.exists(holo)
    if HOLO_MASK:
        r = np.array(Image.open(holo).convert('RGBA'))[..., 0]
        save(np.repeat(r[..., None], 3, axis=2).copy(), 'holo_e.png', 512)
    mask = os.path.join(SRC, 'Assets/Vehicles/Shared/Textures/T_Vehicles_Floaters_Emissive_M.png')
    NOZZLE_MASK = os.path.exists(mask)
    if NOZZLE_MASK:
        # As M_Vehicles_Floaters_Emissive samples it: red x green at twice the UV, so each UV quadrant (glow_split's
        # slots) shows the whole atlas; floater_e.png tiles it 2 x 2 for the plain UV. The lights' quadrants (top) light
        # wherever red x green > 0 (the shader divides by zero there: no gradient); the engine and boost quadrants
        # (bottom) reveal the gradient with the thrust, smoothstep((m - (1 - 2a)) / ...): baked at 3/4 thrust, 2m
        # (the remake's engine glow fades the whole of it with the thrust). Red's slow horizontal scroll (the band rows,
        # ScrollSpeed) is left out: its bands run along the scroll. Also at 2/3 and 1/3 for the dimmer vertex reds.
        m = np.array(Image.open(mask).convert('RGBA')).astype(np.float32) / 255.0
        rg = m[..., 0] * m[..., 1]
        lit = (rg > 0).astype(np.float32)
        t = np.clip(2 * rg, 0, 1); t = t * t * (3 - 2 * t)
        tiles = np.vstack([np.hstack([lit, lit]), np.hstack([t, t])])
        for scale, name, size in ((1.0, 'floater_e.png', 2048), (2 / 3, 'floater_e67.png', 1024), (1 / 3, 'floater_e33.png', 1024)):
            v = (tiles * scale * 255).round().astype(np.uint8)
            save(np.repeat(v[..., None], 3, axis=2).copy(), name, size)
    # Battle damage embers (the hull materials' DamageAmount / Ember* in ES2): burn patches from T_Vehicles_Damage_C_R_M_H's
    # height (A, blurred: the hearts of the burn blobs) with glowing cracks from its colour (R); optional.
    global EMBERS
    dmg = os.path.join(SRC, 'Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_C_R_M_H.png')
    EMBERS = os.path.exists(dmg)
    if EMBERS:
        from PIL import ImageFilter
        a = np.asarray(Image.open(dmg).convert('RGBA').resize((1024, 1024), Image.LANCZOS)).astype(np.float32) / 255.0
        hb = np.asarray(Image.fromarray((a[..., 3] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12))).astype(np.float32) / 255.0
        core = np.clip((0.26 - hb) / 0.1, 0, 1)
        crack = np.clip((a[..., 0] - 0.2) / 0.3, 0, 1)
        m = np.clip(core * (0.04 + crack ** 1.5 * 1.8), 0, 1)   # (mostly the cracks: a faint glow between them)
        save(np.repeat((m * 255).astype(np.uint8)[..., None], 3, axis=2).copy(), 'embers_e.png')
        # The charring under them (the damage's colour and normals, ES2's DamageColorExp / FuzzyBorderExp): a URP detail
        # colour (sRGB, 0.5 = unchanged: the burnt colour darker) whose alpha is the burn mask (the blurred height, a soft
        # border), and the damage normal map (DirectX -> Unity: green flipped).
        hc = np.asarray(Image.fromarray((a[..., 3] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255.0
        mask = np.clip((0.34 - hc) / 0.12, 0, 1)
        burnt = np.clip(a[..., 0] * 0.8, 0.03, 0.5)
        char = np.zeros((1024, 1024, 4), np.uint8)
        char[..., 0] = char[..., 1] = char[..., 2] = (burnt * 255).astype(np.uint8)
        char[..., 3] = (mask * 255).astype(np.uint8)
        save(char, 'char_c.png')
        dn = os.path.join(SRC, 'Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_N.png')
        if os.path.exists(dn):
            n = np.array(Image.open(dn).convert('RGB').resize((1024, 1024), Image.LANCZOS)); n[..., 1] = 255 - n[..., 1]
            save(n, 'char_n.png')
    # The nozzle shimmer's noise (M_Vehicles_Floaters_Emissive scrolls T_Noise_001_M over the glow; optional).
    global SHIMMER
    snoise = os.path.join(SRC, 'Assets/Shared/Textures/Effects/T_Noise_001_M.png')
    SHIMMER = NOZZLE_MASK and os.path.exists(snoise)
    if SHIMMER:
        Image.open(snoise).convert('L').resize((512, 512), Image.LANCZOS).save(os.path.join(MOD, 'maps', 'shimmer_noise.png'), optimize=True)
    noise = os.path.join(SRC, 'Assets/Shared/Textures/Effects/T_Noise_018_M.png')
    FLAME_NOISE = os.path.exists(noise)
    if FLAME_NOISE:
        im = Image.open(noise).convert('L').resize((512, 512), Image.LANCZOS)
        im.save(os.path.join(MOD, 'maps', 'flame_noise.png'), optimize=True)

FLAME_NOISE = False
NOZZLE_MASK = False
EMBERS = False
SHIMMER = False
HOLO_MASK = False

def holograms():
    # M_ShipModules_Holograms (the projector discs on the wings' tier extensions): additive and unlit in ES2, its own fixed
    # blue (3FC0FF, linear 0.05 / 0.525 / 1), through the pattern of T_ShipModules_FX_001_M_A's red channel; not the colour
    # set's accent colour (as an accent target the discs burned in Set100's yellow). Without the mask: a faint blue disc.
    # Animated by GoF2/ModHologram ("hologram"): its rings turn and bob (ES2: Rotation speed 2, Hover height 10 cm, Hover
    # speed 0.5; the rings' spin and hover from holo_rings).
    h = {'material': 'Holograms', 'hologram': True, 'emissionColor': [0.05, 0.525, 1.0]}
    if HOLO_MASK: h.update({'emission': 'maps/holo_e.png', 'emissionIntensity': 3})
    else: h['emissionIntensity'] = 0.6
    return h

def nozzles():
    # M_Vehicles_Floaters_Emissive's four slots, split by glow_split: the lights (Ring1 / Ring2) always on, the engine
    # glow (NozzleGlow) dark while the engines are off (parked in a hangar), the booster's (BoostVent) only while boosting;
    # each through floater_e.png (its "_R67" / "_R33" copies through the dimmer masks); the faces without vertex red dark.
    # The dimmer copies come first: the remake takes the first material whose name the model's contains.
    dark = [0.03, 0.03, 0.035]
    def slot(name, extra, intensity):
        out = []
        for suffix, mask in (('_R33', 'floater_e33'), ('_R67', 'floater_e67'), ('', 'floater_e')):
            e = {'material': name + suffix, 'color': dark, **extra}
            if NOZZLE_MASK: e.update({'emission': f'maps/{mask}.png', 'emissionIntensity': intensity})
            else: e['emissionIntensity'] = intensity * {'_R33': 1 / 3, '_R67': 2 / 3, '': 1}[suffix] / 2
            out.append(e)
        return out
    out = [*slot('NozzleGlow', {'emissionColor': [1.0, 0.2875, 0.05], 'engine': True}, glow_intensity()),
           *slot('Ring1', {'emissionColor': [1, 1, 1]}, 1), *slot('Ring2', {'emissionColor': [1, 1, 1]}, 1),
           *slot('BoostVent', {'emissionColor': [0.05, 0.525, 1.0], 'boost': True}, FLAME_INTENSITY),
           {'material': 'NozzleOff', 'color': dark}]
    if SHIMMER:   # the shimmer: noise scrolling over the engine glow (ES2's ScrollSpeed 0.3), in the engine colour
        out.append({'material': 'NozzleShimmer', 'shimmer': True, 'engine': True, 'emission': 'maps/floater_e.png',
                    'flameNoise': 'maps/shimmer_noise.png', 'emissionColor': [1.0, 0.2875, 0.05], 'emissionIntensity': SHIMMER_INTENSITY})
    return out

def glow_intensity():
    # (with the shimmer, the steady glow gives part of its brightness to the moving layer)
    return NOZZLE_INTENSITY * (0.6 if SHIMMER else 1.0)

LIGHT_INTENSITY = 5   # ES2's lights (Emissive 1 / 2) burn vividly even in dark colours (its EmissiveIntensityHigh 20)
NOZZLE_INTENSITY = 1.6
SHIMMER_INTENSITY = 1.3

def flame():
    # ES2's engine flames: each rear / wing part's M_Vehicle_EngineExhaust section is a short stub behind its nozzles (UV u
    # from the nozzle to the tip) that the material stretches backward by u x its Length, 500 cm (research/engine_exhaust.md:
    # its shaders decompiled; the thrust shows only in the opacity). The remake's GoF2/ModEngineFlame draws it with that
    # formula; the colours: the exhaust colours (TE_Default) and the boost colour (TB_Default) of DT_ShipColors, linear.
    f = {'material': 'EngineExhaust', 'flame': True, 'flameLength': 5.0, 'flameIdle': 0.15,
         'emissionColor': [1.0, 0.2875, 0.05], 'boostColor': [0.05, 0.525, 1.0], 'emissionIntensity': FLAME_INTENSITY}
    if FLAME_NOISE: f['flameNoise'] = 'maps/flame_noise.png'
    return f

FLAME_INTENSITY = 4

def materials():
    unlit = lambda t: {'diffuse': f'maps/{t}_c.png', 'normal': f'maps/{t}_n.png', 'metallicSmoothness': f'maps/{t}_ms.png', **embers}
    tech = lambda t: {'diffuse': f'maps/{t}_c.png', 'normal': f'maps/{t}_n.png', 'metallicSmoothness': f'maps/{t}_ms.png',
                      'emission': f'maps/{t}_e.png', 'emissionColor': [1, 1, 1], 'emissionIntensity': 2}
    embers = {'damageEmission': 'maps/embers_e.png', 'damageDetail': 'maps/char_c.png',
              **({'damageNormal': 'maps/char_n.png'} if jobs.exists(os.path.join(MOD, 'maps', 'char_n.png')) else {})} if EMBERS else {}
    paint = lambda n: {'material': f'Paint{n}', 'diffuse': 'maps/hull_c.png', 'normal': 'maps/hull_n.png', 'metallic': 0.1, 'smoothness': 0.5, **embers}
    return [
        *nozzles(),
        paint(1), paint(2), paint(3),
        *[{'material': f'Lamp{n}_S{k}', **tech(f'tech{n}')} for n in (2, 1) for k in (4, 5, 6, 7)],
        {'material': 'TechDetails_002', **unlit('tech2')},
        {'material': 'TechDetails', **unlit('tech1')},
        # (the floaters: alpha-cut detail cards with a few always-glowing vents; their strips, CyberStrip, glow in the
        # cybernetic glow's colour)
        {'material': 'ShipModules_Floaters', **unlit('floaters1'), 'diffuse': 'maps/floaters1_ca.png', 'alphaClip': 0.5,
         'emission': 'maps/floaters1_glow_e.png', 'emissionColor': [1, 1, 1], 'emissionIntensity': 30 * LIGHT_INTENSITY / 20},
        {'material': 'CyberStrip', **unlit('floaters1'), 'diffuse': 'maps/floaters1_ca.png', 'alphaClip': 0.5, 'color': [0.15, 0.15, 0.15],
         'emission': 'maps/cyberstrip_e.png', 'emissionColor': [0, 0, 0], 'emissionIntensity': 1},
        {'material': 'Glass_Lines', 'color': [0.1, 0.2, 0.25], 'emissionColor': [0.4, 0.85, 1.0], 'emissionIntensity': 1.5},
        {'material': 'Glass_Interior', 'color': [0.03, 0.04, 0.06]},
        {'material': 'Glass', 'color': [0.08, 0.12, 0.16], 'smoothness': 0.95, 'metallic': 0.3, 'opacity': 0.6},
        {'material': 'Decals', 'diffuse': 'maps/clear.png', 'alphaClip': 0.5},
        flame(),
        {'material': 'Headlight', 'color': [0.9, 0.9, 0.9], 'emissionColor': [1, 1, 1], 'emissionIntensity': 5},
        holograms(),
        {'material': 'HUD', 'color': [0.02, 0.03, 0.04], 'emissionColor': [0.1, 0.3, 0.5], 'emissionIntensity': 1},
        {'material': 'CockpitWidget', 'color': [0.02, 0.03, 0.04], 'emissionColor': [0.1, 0.3, 0.5], 'emissionIntensity': 1},
        {'material': 'CarbonFibre', 'color': [0.08, 0.08, 0.09], 'smoothness': 0.6, 'metallic': 0.1},
        {'material': 'Blockout', 'color': [0.18, 0.19, 0.21], 'smoothness': 0.4, 'metallic': 0.6},
        {'material': 'WorldGrid', 'color': [0.18, 0.19, 0.21], 'smoothness': 0.4, 'metallic': 0.6},
    ]

def colors():
    pal = {'main': [], 'emissive': [], 'window': [], 'exhaust': []}
    kinds = {'EShipColor::Main': 'main', 'EShipColor::Emissive': 'emissive', 'EShipColor::Window': 'window', 'EShipColor::Exhaust': 'exhaust'}
    for rid, r in table('DT_ShipColors.json').items():
        kind = kinds.get(r.get('ColorType'))
        if kind: pal[kind].append({'id': rid, 'name': r['ColorName']['SourceString'], 'color': '#' + r['Color']['Hex'][:6]})
    slots = [
        {'id': 'hull1', 'name': 'Main colour', 'palette': 'main', 'default': 'DefaultWhite', 'targets': [{'material': 'Paint1'}]},
        {'id': 'hull2', 'name': 'Second colour', 'palette': 'main', 'default': 'Grey2', 'targets': [{'material': 'Paint2'}]},
        {'id': 'hull3', 'name': 'Third colour', 'palette': 'main', 'default': 'Grey1', 'targets': [{'material': 'Paint3'}]},
        {'id': 'lights', 'name': 'Lights', 'palette': 'emissive', 'default': 'E_DefaultYellow',
         'targets': [{'material': '_S4', 'property': 'emission', 'intensity': LIGHT_INTENSITY}, {'material': 'Ring1', 'property': 'emission', 'intensity': LIGHT_INTENSITY}]},
        {'id': 'accents', 'name': 'Accent lights', 'palette': 'emissive', 'default': 'E_White1',
         'targets': [{'material': '_S5', 'property': 'emission', 'intensity': LIGHT_INTENSITY}, {'material': '_S6', 'property': 'emission', 'intensity': LIGHT_INTENSITY},
                     {'material': '_S7', 'property': 'emission', 'intensity': LIGHT_INTENSITY}, {'material': 'Ring2', 'property': 'emission', 'intensity': LIGHT_INTENSITY}, {'material': 'Glass_Lines', 'property': 'emission', 'intensity': 1.5}]},
        # ES2's Emissive 3, the "cybernetic glow", with its intensity slider (EmissiveColor3 / EmissiveColor3Intensity; every
        # ES2 scheme leaves it off): the floater strips glow in it (CyberStrip, see floater_split: the inset strips along
        # the panels, its circuit pattern, matched against the game's customization screen).
        {'id': 'cyber', 'name': 'Cybernetic glow', 'palette': 'emissive', 'default': 'E_None',
         'targets': [{'material': 'CyberStrip', 'property': 'emission', 'intensity': 3}]},   # (brighter clips lime to pale yellow)
        {'id': 'cyber_strength', 'name': 'Glow intensity', 'steps': [round(i / 10, 1) for i in range(11)], 'default': '0.5', 'scales': 'cyber'},
        {'id': 'windows', 'name': 'Windows', 'palette': 'window', 'default': 'W_Default', 'targets': [{'material': 'Glass', 'intensity': 0.35}]},
        {'id': 'engines', 'name': 'Main thrusters', 'palette': 'exhaust', 'default': 'TE_Default',
         'targets': [{'material': 'EngineExhaust', 'property': 'emission', 'intensity': FLAME_INTENSITY},
                     {'material': 'NozzleGlow', 'property': 'emission', 'intensity': glow_intensity() if NOZZLE_MASK else NOZZLE_INTENSITY / 2},
                     *([{'material': 'NozzleShimmer', 'property': 'emission', 'intensity': SHIMMER_INTENSITY}] if SHIMMER else []),
                     {'property': 'engine'}]},
        # ES2's booster and lateral thruster colours (TrailColorBoost / TrailColorLateral): the flames' boost cards and the
        # manoeuvring jets (LateralThrusters' "lateral thruster" material).
        {'id': 'boost', 'name': 'Booster', 'palette': 'exhaust', 'default': 'TB_Default',
         'targets': [{'material': 'EngineExhaust', 'property': 'boost', 'intensity': FLAME_INTENSITY},
                     {'material': 'BoostVent', 'property': 'emission', 'intensity': FLAME_INTENSITY}]},
        {'id': 'lateral', 'name': 'Side thrusters', 'palette': 'exhaust', 'default': 'TB_Default',
         'targets': [{'material': 'lateral thruster', 'property': 'boost', 'intensity': 8}]},
    ]
    def hull(c, n):
        return '#%s/%d/%.2f' % (c[f'HullColor{n}']['Hex'][:6], 1 if c[f'bHullColor{n}Metal'] else 0, 1.0 - c[f'HullColor{n}Roughness'])
    presets = []
    for rid, r in sorted(table('DT_ShipColorSets.json').items()):
        if rid == 'Set000': continue   # the debug scheme (pure red / green / blue)
        c = r['Colors']
        presets.append({'id': rid.lower(), 'name': 'Scheme ' + str(int(rid[3:])),
                        'colors': {'hull1': hull(c, 1), 'hull2': hull(c, 2), 'hull3': hull(c, 3),
                                   'lights': '#' + c['EmissiveColor1']['Hex'][:6], 'accents': '#' + c['EmissiveColor2']['Hex'][:6],
                                   'cyber': '#' + c['EmissiveColor3']['Hex'][:6], 'cyber_strength': '%g' % round(c['EmissiveColor3Intensity'], 2),
                                   'windows': '#' + c['WindowColor']['Hex'][:6], 'engines': '#' + c['TrailColorEngine']['Hex'][:6],
                                   'boost': '#' + c['TrailColorBoost']['Hex'][:6], 'lateral': '#' + c['TrailColorLateral']['Hex'][:6]}})
    return pal, slots, presets

def clampr(v, lo, hi): return int(max(lo, min(hi, round(v))))

def part_stats(parts):
    """The parts' stats and slots (a design of this mod: ES2's data has none; ES2's modules are cosmetic). Each part shifts
    the ship type's own numbers relative to its siblings, so every build stays near the type: see the mod's notes."""
    def size(p):
        mn, mx = bounds[p['model']]; d = np.maximum(mx - mn, 0.01); return float(d[0] * d[1] * d[2])
    def span(p):
        mn, mx = bounds[p['model']]; return float(mx[2] - mn[2])
    def rel(v, vs): m = float(np.mean(vs)) if vs else v; return (v - m) / m if m > 0 else 0.0
    by = lambda slot: [p for p in parts if p['slot'] == slot]
    for p in by('body'):
        r = rel(size(p), [size(q) for q in by('body')])
        p['stats'] = {'armor': clampr(r * 20, -12, 12), 'cargo': clampr(r * 30, -20, 20), 'handling': clampr(-r * 8, -6, 6),
                      'equipment': 1 if r > 0.3 else -1 if r < -0.3 else 0}
    for p in by('rear'):
        n = p['_sockets'][3]; ns = [q['_sockets'][3] for q in by('rear')]
        rn = rel(n, ns); r = rel(size(p), [size(q) for q in by('rear')])
        p['stats'] = {'topSpeed': clampr(rn * 6, -6, 6), 'acceleration': clampr(rn * 12, -12, 12), 'armor': clampr(r * 8, -5, 5)}
    for p in by('cockpit'):
        r = rel(size(p), [size(q) for q in by('cockpit')])
        p['stats'] = {'handling': clampr(-r * 3, -3, 3)}
    for t in sorted({ty for p in by('wings') for ty in p.get('types', [])}):
        wings = [p for p in by('wings') if t in p.get('types', [])]
        base = STATS[t][3]
        for p in wings:
            r = rel(span(p), [span(q) for q in wings])
            p['stats'] = {'turnRate': clampr(-r * 12, -10, 10), 'handling': clampr(-r * 6, -5, 5), 'armor': clampr(r * 10, -8, 8)}
            slots = {}
            for key, st, b in (('primary', 0, base[0]), ('secondary', 1, base[1])):
                counts = [q['_sockets'][st] for q in wings]
                if max(counts) > min(counts):
                    d = 1 if p['_sockets'][st] == max(counts) else -1 if p['_sockets'][st] == min(counts) else 0
                    slots[key] = max(1, b + d)
                else:
                    slots[key] = b
            if any(q['_sockets'][2] for q in wings): slots['turret'] = min(2, p['_sockets'][2])
            p['slots'] = slots
    for p in parts:
        if 'stats' in p: p['stats'] = {k: v for k, v in p['stats'].items() if v != 0}

# ---- weapons and the player turret (ModHardpoints) ----------------------------------------------------------------------

def socket_pos(json_path, pattern):
    # A mesh socket's position in the export's glTF metres (Unreal cm X forward, Y side, Z up -> (X, Z, Y) / 100).
    for o in json.load(open(json_path, encoding='utf-8-sig')):
        if o.get('Type') == 'StaticMeshSocket' and re.search(pattern, o['Properties'].get('SocketName', '')):
            l = o['Properties'].get('RelativeLocation') or {}
            return [l.get('X', 0) / 100, l.get('Z', 0) / 100, l.get('Y', 0) / 100]
    return None

def weapon_models():
    # ES2's ship weapons (SM_PrimaryWeapon_001..012, the missile pod), each with a "muzzle" node at its muzzle socket (the
    # pod's: where its missiles leave). ES2's own users: 003 beam laser, 004 blaster, 005 pulse laser, 006 gauss cannon,
    # 007 coil gun, 008 thermo gun, 009 rail gun, 010 flak, 011 scatter gun, 012 the legendary goo / plasma guns, 001 the
    # player turret's coil gun, the pod every missile launcher; 002 has none.
    os.makedirs(os.path.join(MOD, 'equipment'), exist_ok=True)
    for i in range(1, 13):
        if i == 2: continue   # no user in ES2 (and 8 MB)
        src = os.path.join(WEAPONS, f'Meshes/SM_PrimaryWeapon_{i:03d}.glb')
        if not os.path.exists(src): print('  missing', src); continue
        dst = os.path.join(MOD, f'equipment/weapon_{i:03d}.glb')
        glbtool.rewrite(src, dst, split=hull_split, extra=flame_across)
        m = socket_pos(src[:-4] + '.json', r'Muzzle')
        if m: glbtool.add_node(dst, 'muzzle', m)
    src = os.path.join(WEAPONS, 'Meshes/SM_SecondaryWeapon_Pod_001.glb')
    dst = os.path.join(MOD, 'equipment/pod.glb')
    glbtool.rewrite(src, dst, split=hull_split, extra=flame_across)
    m = socket_pos(src[:-4] + '.json', r'SWSlot_Missile')
    if m: glbtool.add_node(dst, 'muzzle', m)

def turret_model():
    # SK_Turret_PlayerShip_001 is skinned (b_Root, b_Lafette_Rotate the base turning sideways, b_Gun_Rotate the barrel tilting,
    # b_Muzzleflash_Center): each triangle goes to its vertices' main bone, into rigid meshes under the nodes ModHardpoints
    # turns: turret -> base, pivot -> turret_gun -> muzzle (the bones' bind rotations are identity, so only their positions).
    g, b = glbtool.load(TURRET)
    parent = {c: i for i, n in enumerate(g['nodes']) for c in n.get('children', [])}
    def world(i):
        t = np.zeros(3)
        while i is not None:
            t += np.array(g['nodes'][i].get('translation', [0, 0, 0])); i = parent.get(i)
        return t
    bone = {g['nodes'][j]['name']: j for j in g['skins'][0]['joints']}
    joints = g['skins'][0]['joints']
    group_of = {'b_Root': 0, 'b_Lafette_Rotate': 1, 'b_Gun_Rotate': 2, 'b_Muzzleflash_Center': 2}
    jgroup = np.array([group_of.get(g['nodes'][j]['name'], 0) for j in joints])
    pivot, gun, muzzle = world(bone['b_Lafette_Rotate']), world(bone['b_Gun_Rotate']), world(bone['b_Muzzleflash_Center'])
    offset = [np.zeros(3), pivot, gun]
    groups = [[], [], []]
    for m in g['meshes']:
        for p in m['primitives']:
            A = p['attributes']
            arr = {k: glbtool.read(g, b, A[k])[0] for k in ('POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0') if k in A}
            jo, _ = glbtool.read(g, b, A['JOINTS_0']); we, _ = glbtool.read(g, b, A['WEIGHTS_0'])
            vg = jgroup[jo[np.arange(len(jo)), we.argmax(axis=1)].astype(np.int64)]
            tri = glbtool.read(g, b, p['indices'])[0].reshape(-1, 3).astype(np.int64)
            tg = np.where(vg[tri[:, 1]] == vg[tri[:, 2]], vg[tri[:, 1]], vg[tri[:, 0]])   # the majority of the three
            name = g['materials'][p['material']].get('name', '')
            colours = None
            if 'Hull' in name and 'COLOR_0' in A:   # the hull's colour masks -> Paint1-3, like the parts
                col = glbtool.read(g, b, A['COLOR_0'])[0][:, :3].astype(np.float32)
                colours = (col[tri[:, 0]] + col[tri[:, 1]] + col[tri[:, 2]]).argmax(axis=1)
            for k in range(3):
                for c in (range(3) if colours is not None else [None]):
                    sel = tri[(tg == k) & ((colours == c) if c is not None else True)]
                    if sel.size == 0: continue
                    used, inv = np.unique(sel.reshape(-1), return_inverse=True)
                    attrs = {a: v[used].astype(np.float32) for a, v in arr.items()}
                    attrs['POSITION'] = attrs['POSITION'] - offset[k]
                    groups[k].append((attrs, inv.astype(np.uint32), f'Paint{c + 1}' if c is not None else name))
    w = glbtool.Writer()
    root = w.node('turret')
    w.node('base', mesh=w.mesh('turret_base', groups[0]), parent=root)
    pv = w.node('pivot', pivot, w.mesh('turret_pivot', groups[1]), root)
    gn = w.node('turret_gun', gun - pivot, w.mesh('turret_gun', groups[2]), pv)
    w.node('muzzle', muzzle - gun, parent=gn)
    w.write(os.path.join(MOD, 'equipment/turret.glb'))
    print('  turret:', [sum(len(x[1]) // 3 for x in grp) for grp in groups], 'triangles (base, pivot, gun)')

def weapon_textures():
    T = os.path.join(WEAPONS, 'Textures')
    def load(n): return np.array(Image.open(os.path.join(T, n + '.png')).convert('RGBA'))
    def normal(n, dst):
        a = load(n); a[..., 1] = 255 - a[..., 1]; save(a[..., :3].copy(), dst, 1024)
    def ms(metal, rough, dst):
        out = np.zeros(metal.shape + (4,), np.uint8); out[..., 0] = out[..., 1] = out[..., 2] = metal; out[..., 3] = 255 - rough
        save(out, dst, 1024)
    # Metal 001: colour + AO, normal, R roughness / G metal / B emissive mask (its emission is off in ES2).
    save(load('T_Weapons_001_C_AO')[..., :3].copy(), 'weapons1_c.png', 1024); normal('T_Weapons_001_N', 'weapons1_n.png')
    r = load('T_Weapons_001_R_MT_E_A'); ms(r[..., 1], r[..., 0], 'weapons1_ms.png')
    # Metal 002: the same, fully metallic, with an orange emissive texture.
    save(load('T_Weapons_002_C_AO')[..., :3].copy(), 'weapons2_c.png', 1024); normal('T_Weapons_002_N', 'weapons2_n.png')
    r = load('T_Weapons_002_R_MT_M'); ms(r[..., 1], r[..., 0], 'weapons2_ms.png')
    save(load('T_Weapons_002_E')[..., :3].copy(), 'weapons2_e.png', 1024)
    # Floaters: R grey colour, G roughness, B metal in one map.
    f = load('T_Weapons__Floaters_001_C_R_MT_A')
    save(np.repeat(f[..., 0:1], 3, axis=2).copy(), 'wfloaters_c.png', 1024); normal('T_Weapons__Floaters_001_N', 'wfloaters_n.png')
    ms(f[..., 2], f[..., 1], 'wfloaters_ms.png')

def weapon_materials():
    # Before the hull's entries: "Floaters" would take MI_Weapons_Floaters_001, "Blockout" the green glow.
    return [
        {'material': 'Weapons_Floaters', 'diffuse': 'maps/wfloaters_c.png', 'normal': 'maps/wfloaters_n.png', 'metallicSmoothness': 'maps/wfloaters_ms.png'},
        {'material': 'Weapons_Metal_002', 'diffuse': 'maps/weapons2_c.png', 'normal': 'maps/weapons2_n.png', 'metallicSmoothness': 'maps/weapons2_ms.png',
         'emission': 'maps/weapons2_e.png', 'emissionColor': [0.44, 0.054, 0.0], 'emissionIntensity': 3},
        {'material': 'Weapons_Metal_001', 'diffuse': 'maps/weapons1_c.png', 'normal': 'maps/weapons1_n.png', 'metallicSmoothness': 'maps/weapons1_ms.png'},
        {'material': 'Glow_Green', 'color': [0.05, 0.2, 0.05], 'emissionColor': [0.3, 1.0, 0.25], 'emissionIntensity': 4},
    ]

def W(n): return f'equipment/weapon_{n:03d}.glb'

# GoF2's weapons on ES2's models (item numbers / categories of the remake's items.json): the first matching rule wins.
HARDPOINTS = {
    'turret': 'equipment/turret.glb',
    'weapons': [
        {'slot': 'primary', 'model': W(3), 'items': [9, 10, 11, 228]},   # the M6 beam lasers -> beam laser
        {'slot': 'primary', 'model': W(12), 'items': [16, 17, 18]},      # the EMP blasters -> the green-glowing plasma gun
        {'slot': 'primary', 'model': W(10), 'items': [177]},             # Berger FlaK -> flak
        {'slot': 'primary', 'model': W(11), 'categories': [25]},         # scatter guns
        {'slot': 'primary', 'model': W(4), 'categories': [1]},           # blasters
        {'slot': 'primary', 'model': W(9), 'items': [24, 25]},           # railguns
        {'slot': 'primary', 'model': W(7), 'items': [22, 23]},           # micro guns -> coil gun
        {'slot': 'primary', 'model': W(6), 'categories': [2]},           # Scram Cannon, Mass Drivers -> gauss cannon
        {'slot': 'primary', 'model': W(8), 'categories': [3]},           # thermo guns
        {'slot': 'primary', 'model': W(5)},                              # lasers and the rest -> pulse laser
        {'slot': 'secondary', 'model': 'equipment/pod.glb', 'categories': [4, 40]},   # every launcher (by kind for the sounds,
        {'slot': 'secondary', 'model': 'equipment/pod.glb', 'categories': [11]},      # audio.py): rockets, mines, EMP bombs,
        {'slot': 'secondary', 'model': 'equipment/pod.glb', 'categories': [6]},       # the rest
        {'slot': 'secondary', 'model': 'equipment/pod.glb'},
        {'slot': 'turret', 'model': '', 'categories': [35]},             # plasma collectors: the turret alone (the stream)
        {'slot': 'turret', 'model': W(6), 'items': [182]},               # Archimedes
        {'slot': 'turret', 'model': W(9), 'items': [181]},               # Skuld AT XR
        {'slot': 'turret', 'model': W(10), 'items': [224]},              # Matador TS
        {'slot': 'turret', 'model': W(5), 'items': [49]},                # L'ksaar (laser)
        {'slot': 'turret', 'model': W(1)},                               # the rest -> ES2's turret coil gun
    ],
}

def mount(gx, gy, gz, slot, extra=None):
    # glTF (x nose, y up, z side) -> glTFast's Unity (-x, y, z) -> the kit's yaw 90 -> Unity (z, y, x) -> a ship-relative
    # position_engine (Unity = (-px, py, pz) * 0.05).
    m = {'slotType': slot, 'position_engine': [round(-gz * GAME, 1), round(gy * GAME, 1), round(gx * GAME, 1)]}
    if extra: m.update(extra)
    return m

# ---- the Wraith (the Okkar ship of EVERSPACE 2's Wrath of the Ancients; optional) ----------------------------------------
# Not a module ship: one skeletal hull SK_ShipOkkar_C_001 (its bones only fold the wings; its rest pose is its bind pose) and
# the cockpit interior (canopy glass, seat, displays) on its SKT_Cockpit socket at the origin. Its sockets are glTF nodes under
# the bones. Built as its own kit "okkar", one part per slot, so it keeps the ES2 kits' colours, weapons and flames.
def okkar_dir(): return os.path.join(SRC, 'Assets/Vehicles/ShipModules/Okkar/Meshes')
def okkar_tex(): return os.path.join(SRC, 'Assets/Vehicles/Shared/Textures')

def has_okkar():
    return (os.path.exists(os.path.join(okkar_dir(), 'SK_ShipOkkar_C_001.glb'))
            and os.path.exists(os.path.join(okkar_tex(), 'T_Vehicles_Okkar_Techdetail_001_C_R_E_AO.png'))
            and os.path.exists(os.path.join(okkar_tex(), 'T_Vehicles_Okkar_Techdetail_001_N.png')))

# MI_Vehicles_Okkar_TechDetail_PlayerShip (M_Vehicles_Parent, UseVertexColorMasks): its vertex colours pick BaseColor (black),
# BaseColor1 (red / yellow), BaseColor2 (green) or BaseColor3 (white / blue); the material's sRGB values.
OKKAR_PLATES = ['#827E75', '#AAA492', '#808182', '#FFECE2']
OKKAR_RESIDUE = (0x7B / 255, 0x5F / 255, 0x3F / 255)   # CavityResidueColor, in the crevices (the Masks' alpha)

def okkar_split(g, binary, p):
    name = g['materials'][p['material']].get('name', '') if 'material' in p else ''
    if 'Floaters_Emissive' in name:
        # (the Okkar hull's glow faces by the floater shader's rules like every module's: the lights that looked like
        # Emissive 1 on the blades and wing tips are in its boost quadrant, lit in the boost colour while boosting, which
        # ES2's Engine Colors page does; the boost and Emissive 1 defaults are both light blue)
        return glow_split(g, binary, p)
    if 'Okkar_TechDetail' not in name: return hull_split(g, binary, p)
    if 'COLOR_0' not in p['attributes'] or 'indices' not in p: return None
    col = glbtool.read(g, binary, p['attributes']['COLOR_0'])[0][:, :3].astype(np.float32)
    if col.max() > 1.5: col /= 255.0
    tri = glbtool.read(g, binary, p['indices'])[0].reshape(-1, 3).astype(np.int64)
    c = col[tri].mean(axis=1) > 0.5
    r, gr, b = c[:, 0], c[:, 1], c[:, 2]
    k = np.where(b, 3, np.where(r, 1, np.where(gr, 2, 0)))
    return [(f'OkkarPlate{i}', tri[k == i].reshape(-1)) for i in range(4)]

def okkar_textures():
    def load(n): return np.array(Image.open(os.path.join(okkar_tex(), n + '.png')).convert('RGBA'))
    m = load('T_Vehicles_Okkar_Techdetail_001_C_R_E_AO')   # R grey detail, G roughness, B emissive (unused), A cavity
    lin = (m[..., 0].astype(np.float64) / 255.0) ** 2.2
    lin = np.clip(lin / lin.mean(), 0, 1.6)   # (scaled to average white like the hull map: the plates' colours as they are)
    cav = (m[..., 3].astype(np.float64) / 255.0) ** 1.788775 * 0.7   # CavityResidueExponent / TextureIntensity
    residue = np.array([v ** 2.2 for v in OKKAR_RESIDUE]) / 0.25    # (against the plates' average linear colour)
    rgb = lin[..., None] * ((1 - cav)[..., None] + cav[..., None] * residue)
    save((np.clip(rgb, 0, 1) ** (1 / 2.2) * 255).round().astype(np.uint8), 'okkar_c.png', 2048)
    n = load('T_Vehicles_Okkar_Techdetail_001_N'); n[..., 1] = 255 - n[..., 1]
    save(n[..., :3].copy(), 'okkar_n.png', 2048)
    ms = np.zeros_like(m); ms[..., 0] = ms[..., 1] = ms[..., 2] = 255; ms[..., 3] = 255 - m[..., 1]   # MetalOverride 1
    save(ms, 'okkar_ms.png', 2048)

def hex_rgb(h): return [round(int(h[i:i + 2], 16) / 255, 4) for i in (1, 3, 5)]

def okkar_materials():
    # (no glow: MI_Vehicles_Okkar_TechDetail_PlayerShip's EmissiveColor is #100801, as good as black; the plates' emissive
    # channel isn't one of the ship's lights)
    plate = lambda i: {'material': f'OkkarPlate{i}', 'diffuse': 'maps/okkar_c.png', 'normal': 'maps/okkar_n.png',
                       'metallicSmoothness': 'maps/okkar_ms.png', 'color': hex_rgb(OKKAR_PLATES[i])}
    return [plate(i) for i in range(4)] + [
        {'material': 'Okkar_Playership_Display', 'color': [0.02, 0.03, 0.04], 'emissionColor': [0.2, 0.75, 1.0], 'emissionIntensity': 2}]

def skeleton_world(g):
    """A function giving a node's world matrix (glTF translation / rotation / scale, no 'matrix' in these exports)."""
    nodes = g['nodes']; parent = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
    def local(n):
        M = np.eye(4); x, y, z, w = n.get('rotation', [0, 0, 0, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M[:3, :3] = R * np.array(n.get('scale', [1, 1, 1])); M[:3, 3] = n.get('translation', [0, 0, 0]); return M
    def world(i):
        M = np.eye(4)
        while i is not None: M = local(nodes[i]) @ M; i = parent.get(i)
        return M
    return world

def convert_rigid(src, out):
    """A skeletal mesh as a rigid one in its rest pose (= its bind pose): the skin, the bones and the sockets dropped."""
    dst = os.path.join(MOD, out)
    glbtool.rewrite(src, dst, split=okkar_split, extra=flame_across)
    g, b = glbtool.load(dst)
    mesh = next(n['mesh'] for n in g['nodes'] if 'mesh' in n)
    g['nodes'] = [{'name': os.path.basename(out)[:-4], 'mesh': mesh}]
    g['scenes'] = [{'nodes': [0]}]; g['scene'] = 0
    for k in ('skins', 'animations'): g.pop(k, None)
    glbtool.save(dst, g, b)
    mn, mx = np.full(3, 1e9), np.full(3, -1e9)
    for m in g['meshes']:
        for p in m['primitives']:
            a = g['accessors'][p['attributes']['POSITION']]
            if 'min' in a: mn = np.minimum(mn, a['min']); mx = np.maximum(mx, a['max'])
    bounds[out] = (mn, mx)
    return out

def okkar_mounts(src):
    # The hull's sockets: SKT_PWSlot_left / right the guns, SKT_SWSlot_center the launcher, SKT_Engine_001 the exhaust, any
    # SKT_Booster the booster points,
    # SKT_LateralThruster_* the manoeuvring jets, each blowing along its socket's local +X (top ones up, front ones forward).
    g, _ = glbtool.load(src)
    world = skeleton_world(g)
    out = []
    for i, n in enumerate(g['nodes']):
        name = n.get('name', '')
        if not name.startswith('SOCKET_SKT_'): continue
        W = world(i); x, y, z = W[:3, 3]
        # (the socket's own scale: EVERSPACE 2 sizes the engine lights and trails by it)
        sc = max(abs(v) for v in n.get('scale', [1.0, 1.0, 1.0]))
        scale = {'socketScale': round(sc, 3)} if abs(sc - 1.0) > 1e-3 else {}
        if 'PWSlot' in name: out.append(mount(x, y, z, 0))
        elif 'SWSlot' in name: out.append(mount(x, y, z, 1))
        elif 'Engine' in name: out.append(mount(x, y, z, 3, dict({'turretAngles': [0.7, 0.7, 0.7], 'glowSize': [40, 40, 90]}, **scale)))
        elif 'Booster' in name: out.append(mount(x, y, z, 5, scale or None))
        elif 'LateralThruster' in name:
            f = W[:3, 0] / (np.linalg.norm(W[:3, 0]) or 1)
            m = mount(x, y, z, 4); m['direction'] = [round(float(-f[2]), 3), round(float(f[1]), 3), round(float(f[0]), 3)]
            out.append(m)
    return sorted(out, key=lambda m: m['slotType'])


# NPC fighters of every race fly the ES2 ships (the game's "Mod ships in traffic" option; 0 Terran, 1 Vossk, 2 Nivelian,
# 3 Midorian, 8 pirates and the minor races, 9 Void), each in a random build of its kit (parts, tier, colour scheme, skin).
TRAFFIC = {'races': [0, 1, 2, 3, 8, 9], 'randomBuild': True}

def build_okkar(palettes, slots, presets, hardpoints):
    okkar_textures()
    hull = convert_rigid(os.path.join(okkar_dir(), 'SK_ShipOkkar_C_001.glb'), 'parts/sk_shipokkar_c_001.glb')
    mounts = okkar_mounts(os.path.join(okkar_dir(), 'SK_ShipOkkar_C_001.glb'))
    parts = [{'id': 'wraith', 'slot': 'body', 'name': 'Wraith', 'model': hull, 'types': ['wraith'],
              'anchors': {'cockpit': [0.0, 0.0, 0.0]}, 'mounts': mounts}]
    cockpit = convert(os.path.join(okkar_dir(), 'SM_ShipOkkar_C_Cockpit_Interior_001.glb'), 'parts/sm_shipokkar_c_cockpit_interior_001.glb')
    if cockpit:
        parts.append({'id': 'wraith_cockpit', 'slot': 'interior', 'name': 'Okkar cockpit', 'model': cockpit, 'types': ['wraith'], 'anchor': 'cockpit'})
    kslots = json.loads(json.dumps(slots))
    kit = {'id': 'okkar', 'name': 'EVERSPACE 2 Okkar hull', 'slots': ['body', 'interior'], 'scale': SCALE, 'yaw': 90,
           'materials': okkar_materials() + weapon_materials() + materials(), 'palettes': palettes, 'colorSlots': kslots,
           'presets': presets, 'parts': parts}
    if hardpoints: kit['hardpoints'] = hardpoints
    pr = next((x for x in presets if x['id'] == 'set033'), presets[0])   # dark with bronze, beside the bronze plates
    build = {'body': 'wraith', 'colors': dict(pr['colors'])}
    if cockpit: build['interior'] = 'wraith_cockpit'
    mn, mx = bounds[hull]
    ship = {'id': 'wraith', 'name': 'Wraith',
            'description': 'An Okkar hull of ancient make: fast, agile and tough for its size. Customize its colours in the hangar.',
            'race': 0, 'armor': 540, 'cargo': 45, 'handling': 160, 'price': 4600000,
            'slots': {'primary': 2, 'secondary': 2, 'turret': 0, 'equipment': 11},
            'kit': 'okkar', 'kitType': 'wraith', 'build': build, 'hangarHeight': int(round(-mn[1] * GAME + 20)),
            'engineGlowColor': [0.45, 0.8, 1.0], 'mounts': [dict(m) for m in mounts],
            'dealer': {'chance': 2, 'systemRace': -1, 'minTechLevel': 6}, 'traffic': dict(TRAFFIC)}
    print(f"Okkar: Wraith, {len(mounts)} mounts, {np.round(mx - mn, 1).tolist()} m (ES2)")
    return kit, ship

# ES2's thrusters as exhaust styles any ship can wear (exhausts.json: the remake's Customize screen, ModExhausts): the flame
# cards (main and boost) of a one-nozzle rear part, cut out with the nozzle at the origin and the nose along +Z, drawn by
# the same flame material and coloured from ES2's exhaust palette (the main thrusters and the booster).
EXHAUST_MODULES = [('thruster', 'EVERSPACE 2 thruster', 'sm_shipmodule_medium_rear_004'),
                   ('thruster_heavy', 'EVERSPACE 2 heavy thruster', 'sm_shipmodule_medium_rear_006'),
                   ('thruster_ring', 'EVERSPACE 2 ring thruster', 'sm_shipmodule_medium_rear_009')]

def exhaust_module(src, dst):
    """One rear part's flame cards as their own GLB (positions moved so the main cards' nozzle ring is at the origin,
    ES2's +X nose turned to +Z); returns the nozzle's radius (ES2 metres), None without flames."""
    g, b = glbtool.load(src)
    attrs = {k: [] for k in ('POSITION', 'NORMAL', 'TEXCOORD_0', 'TEXCOORD_1')}
    idx, base = [], 0
    for m in g['meshes']:
        for p in m['primitives']:
            if 'EngineExhaust' not in g['materials'][p['material']].get('name', '') or 'TEXCOORD_1' not in p['attributes']: continue
            for k in attrs: attrs[k].append(glbtool.read(g, b, p['attributes'][k])[0].astype(np.float32))
            idx.append(glbtool.read(g, b, p['indices'])[0].reshape(-1).astype(np.uint32) + base)
            base += len(attrs['POSITION'][-1])
    if not idx: return None
    a = {k: np.concatenate(v) for k, v in attrs.items()}
    pos, uv, kind = a['POSITION'], a['TEXCOORD_0'], np.abs(a['TEXCOORD_1'][:, 1] - 0.5)
    ring = pos[(uv[:, 0] < 0.05) & (kind < 0.1)]
    if len(ring) == 0: ring = pos[uv[:, 0] < 0.05]
    origin = ring.mean(axis=0)
    radius = float(np.max(np.linalg.norm(ring[:, 1:] - origin[1:], axis=1)))
    turn = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], np.float32)   # glTF: ES2's +X nose -> +Z (a rotation)
    a['POSITION'] = (pos - origin) @ turn.T
    a['NORMAL'] = a['NORMAL'] @ turn.T
    w = glbtool.Writer()
    w.node('exhaust', mesh=w.mesh('exhaust', [(a, np.concatenate(idx), 'M_Vehicle_EngineExhaust')]))
    w.write(dst)
    return radius

def exhaust_styles(palettes):
    os.makedirs(os.path.join(MOD, 'exhausts'), exist_ok=True)
    out = []
    for sid, name, part in EXHAUST_MODULES:
        src = os.path.join(MOD, 'parts', part + '.glb')
        if not os.path.exists(src): continue
        r = exhaust_module(src, os.path.join(MOD, 'exhausts', sid + '.glb'))
        if not r: continue
        mat = flame()
        if 'flameNoise' not in mat and os.path.exists(os.path.join(MOD, 'maps', 'flame_noise.png')): mat['flameNoise'] = 'maps/flame_noise.png'
        # One choice in the remake's Customize screen ("group"): each nozzle wears the thruster made for the nearest nozzle
        # size (the three are round ES2 nozzles of 0.38, 0.42 and 0.61 m, x SCALE as the ES2 ships show them: "scale").
        out.append({'id': sid, 'name': name, 'model': f'exhausts/{sid}.glb', 'nozzle': round(r, 4), 'materials': [mat],
                    'palette': palettes.get('exhaust', []), 'mainName': 'Main thrusters', 'secondName': 'Booster',
                    'group': 'thruster', 'groupName': 'EVERSPACE 2 thruster', 'scale': SCALE})
        print(f'  exhaust style {name}: nozzle radius {r:.2f} m')
    return out

# (audio/: the sounds are encoded by whatever this computer has, ffmpeg's version or none, so the files differ between
# players' builds; the names ships.json gives them don't.)
MULTIPLAYER_IGNORE = ['parts/', 'maps/', 'icons/', 'preview.png', 'audio/', 'warships/', 'fighters/', 'sectors/']

def main(version):
    os.makedirs(os.path.join(MOD, 'parts'), exist_ok=True)
    os.makedirs(os.path.join(MOD, 'maps'), exist_ok=True)
    textures()
    # The weapons and the player turret are optional (an export without them: no weapon models, the turret sockets fire
    # the turret items without a model).
    hardpoints = None
    if has_weapons():
        weapon_textures()
        weapon_models()
        hardpoints = {'weapons': HARDPOINTS['weapons']}
        if has_turret():
            turret_model()
            hardpoints['turret'] = HARDPOINTS['turret']
    else:
        print('  no weapons in the export (Assets/Equipment/Weapons): the ships come without weapon and turret models')
    palettes, slots, presets = colors()
    debug = table('DT_DebugShipsKS.json')
    kits, ships = [], []
    for cls in CLASSES:
        parts, ex = build_kit(cls)
        part_stats(parts)
        print(f'{cls}: {len(parts)} parts')
        kid = cls.lower()
        kits.append({'id': kid, 'name': f'EVERSPACE 2 {cls} hulls', 'slots': ['base', 'body', 'rear', 'cockpit', 'interior', 'wings'],
                     'scale': SCALE, 'yaw': 90, 'materials': weapon_materials() + materials(), 'palettes': palettes, 'colorSlots': slots, 'presets': presets,
                     'hardpoints': HARDPOINTS,
                     'parts': [{k: v for k, v in p.items() if not k.startswith('_') and k != 'table'} for p in parts]})
        by_table = {p['table']: p for p in parts}
        for eship, (tid, tname) in TYPES.items():
            wings = [p for p in parts if p['slot'] == 'wings' and tid in p.get('types', [])]
            if not wings: continue
            row = next((r for k, r in debug.items() if k.lower().startswith(tname.lower() + '_')), None)
            build = {'tier': 1}
            if row and row.get('ShipClass') == f'EShipClass::{cls}':
                for slot, key in (('body', 'BodyID'), ('rear', 'RearID'), ('cockpit', 'CockpitID'), ('interior', 'CockpitInteriorID'), ('wings', 'WingsID')):
                    p = by_table.get(row.get(key))
                    if p and (slot != 'wings' or tid in p.get('types', [])): build[slot] = p['id']
                m = re.search(r'_Ext_T(\d)_', row.get('ExtensionID') or '')
                if m: build['tier'] = int(m.group(1))
                pr = next((x for x in presets if x['id'] == (row.get('ColorsID') or '').lower()), None)
                if pr: build['colors'] = dict(pr['colors'])
            build.setdefault('wings', wings[0]['id'])
            # Mounts from the default build's size: guns at the nose's sides, the exhaust at the rears' average.
            used = [p for p in parts if p['id'] in build.values() or (p['slot'] == 'body' and 'body' not in build)]
            mn = np.min([bounds[p['model']][0] for p in used], axis=0); mx = np.max([bounds[p['model']][1] for p in used], axis=0)
            body = next((p for p in parts if p['id'] == build.get('body')), next(p for p in parts if p['slot'] == 'body'))
            bmn, bmx = bounds[body['model']]
            gx, gy, gz = bmx[0] * 0.45, bmn[1] * 0.3, max(0.6, (mx[2] - mn[2]) * 0.08)
            mounts = [mount(gx, gy, -gz, 0), mount(gx, gy, gz, 0), mount(gx * 0.9, gy * 1.6, -gz * 0.5, 0), mount(gx * 0.9, gy * 1.6, gz * 0.5, 0),
                      mount(gx * 0.6, bmn[1] * 0.7, 0.0, 1), mount(gx * 0.5, bmn[1] * 0.7, -0.4, 1), mount(gx * 0.5, bmn[1] * 0.7, 0.4, 1),
                      mount(gx * 0.4, bmn[1] * 0.7, 0.0, 1),
                      mount(float(ex[0]), float(ex[1]), float(ex[2]), 3, {'turretAngles': [0.7, 0.7, 0.7], 'glowSize': [40, 40, 90]})]
            h, armor, cargo, sl, price = STATS[tid]
            # Turret slots: as many as the default build's parts have turret sockets; their first is also the ship's own turret
            # mount, for a build whose parts have none.
            turrets = [m for p in parts if p['id'] in build.values() for m in p.get('mounts', []) if m['slotType'] == 2]
            if turrets:
                mounts.append(dict(turrets[0]))   # the ship's own turret mount, for a build whose parts have none
            ships.append({'id': tid, 'name': tname, 'description': DESC[tid] + ' Customize it in the hangar.', 'race': 0,
                          'armor': armor, 'cargo': cargo, 'handling': h, 'price': price,
                          'slots': {'primary': sl[0], 'secondary': sl[1], 'turret': sl[2], 'equipment': sl[3]},
                          'kit': kid, 'kitType': tid, 'build': build, 'hangarHeight': int(round(-mn[1] * GAME + 20)),
                          'engineGlowColor': [0.45, 0.8, 1.0], 'mounts': mounts, 'dealer': {'chance': 3, 'systemRace': -1, 'minTechLevel': 5},
                          'traffic': dict(TRAFFIC)})
            print(f"  {tname}: {build.get('wings')} / {build.get('body')} / tier {build['tier']}, hangar height {ships[-1]['hangarHeight']}")
    if has_okkar():
        kit, ship = build_okkar(palettes, slots, presets, HARDPOINTS)
        kits.append(kit); ships.append(ship)
    else:
        print('  no Okkar hull in the export (Assets/Vehicles/ShipModules/Okkar): no Wraith')
    # The sounds (audio.py: EVERSPACE 2's engines, boosts and weapons, when the export has its Audio folder, converted by
    # FModel or decoded by vgmstream); into the ships' entries and the hardpoint rules every kit shares.
    import audio
    audio.configure(SRC, MOD)
    if audio.available():
        print('Adding the sounds ...')
        print('  sounds: ' + audio.build(ships, HARDPOINTS))
    else:
        print('  no sounds: ' + audio.unavailable_reason())
    # EVERSPACE 2's weapons (items.json), warships and freighters (ships.json: "traffic": { "capital" }, their subsystems), the
    # Dreadnought and its raids (events/).
    import weapons, warships, encounter, homebase_hangar, devices, fighters, sectors, factions
    # EVERSPACE 2's factions (factions.py): its ships fly for them and its sectors belong to them, never GoF2's races
    print('Adding the factions ...')
    json.dump(factions.build(SRC, MOD), open(os.path.join(MOD, 'factions.json'), 'w', encoding='utf-8'), indent=1)
    items, world_stations = [], []
    if os.path.isdir(os.path.join(SRC, 'Blueprints/Equipment/Weapons')):
        print('Adding the weapons ...')
        weapons.configure(SRC, MOD)
        items, rules = weapons.build()
        # (every kit shares the rules; the hull's own weapon rules stay behind them)
        seen = set()
        for k in kits:
            hp = k.get('hardpoints')
            if hp and id(hp) not in seen:
                seen.add(id(hp)); hp['weapons'] = rules + hp['weapons']
    if os.path.isdir(os.path.join(SRC, 'Assets/Vehicles/Fighters')):
        # (before the warships: their hangars launch these)
        print('Adding the enemy fighters and drones ...')
        fighters.configure(SRC, MOD)
        enemies = fighters.build()
        ships += enemies
        print(f'  {len(enemies)} fighters and drones as traffic of their faction\'s race')
    if os.path.isdir(os.path.join(SRC, 'Assets/Vehicles/Warships')):
        print('Adding the warships and freighters ...')
        warships.configure(SRC, MOD)
        ships += warships.build()
        stations = warships.build_homebase()
        if stations:
            world_stations += stations
            print('  the Mobile Homebase: a station roaming every system')
            rooms = homebase_hangar.build(SRC, MOD)
            if rooms:
                json.dump(rooms, open(os.path.join(MOD, 'interiors.json'), 'w', encoding='utf-8'), indent=1)
                print('  its own hangar and casino (interiors.json)')
        print('  encounter: ' + encounter.build(MOD))
    else:
        print('  no warships in the export (Assets/Vehicles/Warships): no capital ships, no Dreadnought')
    # EVERSPACE 2's devices and consumables (devices.py: on the nearest GoF2 equipment / secondary).
    print('Adding the devices and consumables ...')
    items += devices.build(MOD)
    # EVERSPACE 2's sectors as systems past the edge of the star map, and ES2's resources (sectors.py).
    sectors.configure(SRC, MOD)
    if sectors.available():
        print('Adding the EVERSPACE 2 sectors ...')
        systems, sector_stations, resources = sectors.build()
        world_stations += sector_stations; items += resources
        json.dump(systems, open(os.path.join(MOD, 'systems.json'), 'w', encoding='utf-8'), indent=1)
    else:
        print('  no sectors: the travel maps (Maps/TravelMode) or the sky and planet textures (tools/sector_assets.txt) are missing')
    if world_stations:
        json.dump(world_stations, open(os.path.join(MOD, 'stations.json'), 'w', encoding='utf-8'), indent=1)
    if items: json.dump(items, open(os.path.join(MOD, 'items.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(kits, open(os.path.join(MOD, 'shipkits.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(exhaust_styles(palettes), open(os.path.join(MOD, 'exhausts.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(ships, open(os.path.join(MOD, 'ships.json'), 'w', encoding='utf-8'), indent=1)
    jobs.flush()   # every map written (the encodes queued on the workers)
    json.dump({'id': 'es2_ships', 'name': 'EVERSPACE 2 ships', 'version': version, 'author': 'built by es2_ships_importer',
               'description': 'Nine customizable EVERSPACE 2 ships (Light / Medium / Heavy) with their parts, colour schemes, weapons '
                              'and turret' + (', and the Okkar Wraith' if has_okkar() else '') +
                              '; EVERSPACE 2\'s devices and consumables in the shops' +
                              ('; EVERSPACE 2\'s weapons in the shops; its warships and freighters in the orbits\' traffic; the Outlaw '
                               'Dreadnought raiding convoys now and then' if os.path.isdir(os.path.join(SRC, 'Assets/Vehicles/Warships')) else '') +
                              ('; EVERSPACE 2\'s Ceto sector past the edge of the star map (a Khador Drive away), with ES2\'s resources to mine' if sectors.available() else '') +
                              '. Built on this device from your own EVERSPACE 2 files. Customize the ships in the hangar.',
               'credits': 'Models, textures and colours: EVERSPACE 2 (c) ROCKFISH Games, from the player\'s own copy of the game. '
                          'For personal use: don\'t share the built mod.',
               'preview': 'preview.png',
               # What multiplayer doesn't compare: the phone version's lighter models and textures (and the icons / preview
               # made from them) differ from the PC version's, everything else is the same, so the two play together.
               'multiplayerIgnore': MULTIPLAYER_IGNORE},
              open(os.path.join(MOD, 'mod.json'), 'w', encoding='utf-8'), indent=1)

if __name__ == '__main__':
    configure(sys.argv[1], sys.argv[2])
    main(sys.argv[3] if len(sys.argv) > 3 else '1.0')
