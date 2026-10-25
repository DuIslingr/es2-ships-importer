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
import json, math, os, re, sys, threading
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import glbtool, es2mat, jobs

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
# EVERSPACE 2's civilian traffic (BP_SplineTraffic*: the ships that fly its space lanes, low-poly background models) and its
# mining ships, as freighters: (id, name, description, races, weight, blueprint or None, mesh). No turrets; several races
# each where ES2's own traffic is everyone's, a low weight so they come now and then among the warships' freighters. The
# smallest (SM_Traffic_004, Okkar_003, Okkar_006_B: under 50 m in the game) are left out: shuttles, not freighters.
CIVIL, SETTLER = [0, 2], [0, 2, 3]
TRAFFIC = 'Traffic/Meshes/'
CIVILIANS = [
    ('es2_courier', 'Courier', 'A small civilian courier of EVERSPACE 2\'s space lanes.', CIVIL, 0.3, None, TRAFFIC + 'SM_Traffic_001'),
    ('es2_container_hauler', 'Container Hauler', 'A civilian hauler carrying a stack of cargo containers.', CIVIL, 0.3, None, TRAFFIC + 'SM_Traffic_002'),
    ('es2_light_transport', 'Light Transport', 'A light civilian transport.', CIVIL, 0.3, None, TRAFFIC + 'SM_Traffic_003'),
    ('es2_passenger_shuttle', 'Passenger Shuttle', 'A long-haul passenger shuttle.', CIVIL, 0.3, None, TRAFFIC + 'SM_Traffic_005'),
    ('es2_private_yacht', 'Private Yacht', 'Somebody\'s private yacht.', CIVIL, 0.2, None, TRAFFIC + 'SM_Traffic_006'),
    ('es2_cargo_tug', 'Cargo Tug', 'A twin-engined tug hauling a cargo frame.', CIVIL, 0.3, None, TRAFFIC + 'SM_Traffic_007'),
    ('es2_ore_hauler', 'Ore Hauler', 'A tug hauling a frame full of ore.', [2, 3], 0.3, None, TRAFFIC + 'SM_Traffic_008'),
    ('es2_utility_tug', 'Utility Tug', 'A small utility tug.', CIVIL, 0.2, None, TRAFFIC + 'SM_Traffic_009'),
    ('es2_settler_transport', 'Settler Transport', 'A settler family\'s transport.', SETTLER, 0.3, None, TRAFFIC + 'SM_Traffic_010'),
    ('es2_settler_skiff', 'Settler Skiff', 'A settler\'s skiff.', SETTLER, 0.2, None, TRAFFIC + 'SM_Traffic_011'),
    ('es2_tanker', 'Tanker', 'A settlers\' fuel tanker.', SETTLER, 0.3, None, TRAFFIC + 'SM_Traffic_012'),
    ('es2_supply_truck', 'Supply Truck', 'A settlers\' supply truck.', SETTLER, 0.3, None, TRAFFIC + 'SM_Traffic_013'),
    ('es2_settler_freighter', 'Settler Freighter', 'A settlers\' long freighter.', SETTLER, 0.3, None, TRAFFIC + 'SM_Traffic_014'),
    ('es2_okkar_transport', 'Okkar Transport', 'A civilian Okkar transport.', [1], 0.4, None, TRAFFIC + 'SM_Traffic_Okkar_001'),
    ('es2_okkar_engineer', 'Okkar Engineer', 'An Okkar engineering ship.', [1], 0.4, 'BP_Okkar_Engineer', TRAFFIC + 'SM_Traffic_Okkar_001_B'),
    ('es2_okkar_shuttle', 'Okkar Shuttle', 'An Okkar shuttle.', [1], 0.4, None, TRAFFIC + 'SM_Traffic_Okkar_002'),
    ('es2_okkar_bulk_carrier', 'Okkar Bulk Carrier', 'An Okkar bulk carrier with its twin cargo drums.', [1], 0.4, None, TRAFFIC + 'SM_Traffic_Okkar_004'),
    ('es2_okkar_courier', 'Okkar Courier', 'A small Okkar courier.', [1], 0.3, None, TRAFFIC + 'SM_Traffic_Okkar_005'),
    ('es2_okkar_liner', 'Okkar Liner', 'An Okkar passenger liner.', [1], 0.3, None, TRAFFIC + 'SM_Traffic_Okkar_006'),
    ('es2_okkar_yacht', 'Okkar Yacht', 'An Okkar noble\'s yacht.', [1], 0.2, None, TRAFFIC + 'SM_Traffic_Okkar_006_C'),
    ('es2_gb_mining_ship', 'G&B Mining Ship', 'A Grady & Brunt mining ship.', [3], 0.6, 'BP_GB_MiningVessel', 'Miningships/Meshes/SM_Miningship_001'),
    ('es2_gb_mining_barge', 'G&B Viridium Mining Barge', 'A Grady & Brunt barge, nearly a kilometre long, that mines Viridium.', [3], 0.3,
     'BP_GB_Viridium_MiningShip', 'Miningships/Meshes/SM_Miningship_Barge_001'),
]
# The blueprints of the ships built without one (no turrets or parts to read), for their engine effects (engine_effects).
ENGINE_BP = {'es2_flying_trader': 'BP_Ship_Traveling_Trader', 'es2_tareen_trader': 'BP_Ship_Tareen'}
# The fighters a hangar launches by faction: the mod's kit ships (random builds).
HANGAR_SHIPS = {'outlaw': ['es2_ships:striker', 'es2_ships:stinger', 'es2_ships:scout'],
                'gb': ['es2_ships:interceptor', 'es2_ships:vanguard', 'es2_ships:sentinel'],
                'okkar': ['es2_ships:wraith', 'es2_ships:interceptor'],
                'swarmer': ['es2_ships:scout', 'es2_ships:stinger'],
                'dreadnought': ['es2_ships:striker', 'es2_ships:gunship', 'es2_ships:bomber', 'es2_ships:stinger']}


_lines = threading.local()

def say(msg):
    """LOG, or the line kept for the caller of logged() when on a worker."""
    buf = getattr(_lines, 'buf', None)
    if buf is None: LOG(msg)
    else: buf.append(msg)


def logged(fn, *a):
    """fn(*a) with its say() lines kept: (result, lines)."""
    _lines.buf = []
    try: return fn(*a), _lines.buf
    finally: _lines.buf = None


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
    """Queues the map's write (jobs: encoded on a worker) and returns its path."""
    jobs.write_image(os.path.join(MOD, rel), arr, size)
    return rel


BAND_V0, BAND_V1 = 0.02, 0.98   # the vertex alpha's range in v (clear of the filtering across the wrap)


def band_glow(m):
    """M_Vehicles_Emissive_Parent with its Opacity switch (the Mobile Homebase's MI_Vehicles_Emissive_Warship_010): its
    compiled pixel shader takes the colour from the mask's three vertical bands by UV u (R '1) Primary', G '2) Secondary', B
    '3) Tertiary', x the mask's alpha) and multiplies the glow and the opacity (0.9 x) by the vertex colour's alpha: the big
    panels fade to nothing across them. The remake's materials read no vertex colour, so split_prims writes the alpha into v
    (the bands don't change along it) and band_maps ramp along v."""
    return (es2mat.classify(m) == 'glow' and 'PM_Emissive' in m['tex'] and bool(m['sw'].get('Opacity'))
            and es2mat.vertex_tints(m) is not None)


def band_maps(m):
    """(glow, opacity) maps for a band_glow material: the glow grey (the mask's band x its alpha x the vertex alpha x the
    opacity: UE's translucent blend multiplies the emission by it), the opacity black with alpha 0.9 x the vertex alpha;
    v = BAND_V0 + (BAND_V1 - BAND_V0) x the vertex alpha."""
    key = ('bands', m['tex']['PM_Emissive'])
    with jobs.once(key):
        if key not in _made: _made[key] = _band_maps(m)
    return _made[key]


def _band_maps(m):
    a = _img(m['tex']['PM_Emissive'])
    out = None
    if a is not None:
        a = a.astype(np.float32) / 255
        prof = a[..., :3].max(axis=2).mean(axis=0) * a[..., 3].mean(axis=0)   # across u: the bands are vertical
        v = (np.arange(64) + 0.5) / 64
        al = np.clip((v - BAND_V0) / (BAND_V1 - BAND_V0), 0, 1)
        op = np.minimum(1.0, 0.9 * al)
        glow = np.round(np.outer(al * op, prof) ** (1 / 2.2) * 255).astype(np.uint8)   # sRGB: the emission map is colour
        opa = np.zeros((64, len(prof), 4), np.uint8); opa[..., 3] = np.round(op * 255)[:, None]
        n = es2mat._name(m['tex']['PM_Emissive'])
        out = (_save(np.ascontiguousarray(np.repeat(glow[..., None], 3, axis=2)), f'warships/maps/{n}_bands_glow.png'),
               _save(opa, f'warships/maps/{n}_bands_alpha.png'))
    return out


def tex(kind, src, ch=None, extra=None):
    """A texture made for a role, once per (role, texture, channel): 'colour' (RGB, or one channel as grey; alpha from 'extra'
    = (texture, channel) when masked), 'ms' (src = (metal, rough) each (texture, channel) or None), 'emit' (one channel),
    'normal' (DirectX -> Unity)."""
    key = (kind, str(src), ch, str(extra))
    if key in _made: return _made[key]
    with jobs.once(('tex',) + key):   # (the ships are built on several threads: each map made once)
        if key in _made: return _made[key]
        return _tex(key, kind, src, ch, extra)


def _tex(key, kind, src, ch, extra):
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
        say(f'    texture {src}: {e}')
    _made[key] = rel
    return rel


def structure_colour(rel, tint):
    """ES2's structure base colour as its shader computes it (M_Structures_Parent's base-pass pixel shader, read with
    tools/shaders' ShaderDump): saturate(C x 2 x tint) in linear light, C the masks texture's curvature channel (linear data),
    tint the vertex-colour-chosen BaseColor (an sRGB parameter). Baked per tint into a colour map: Unity would read the
    channel as sRGB and has no saturate for a colour above 1, so a material colour can't do it."""
    key = '%02x%02x%02x' % tuple(int(round(c * 255)) for c in tint[:3])
    out = re.sub(r'\.png$', f'_x2_{key}.jpg', rel)
    p = os.path.join(MOD, out)
    with jobs.once(('structure', out)):
        if not jobs.exists(p) and not jobs.exists(p[:-4] + '.png'):
            jobs.wait(os.path.join(MOD, rel))
            out = _structure_colour(rel, tint, out)
        elif not jobs.exists(p):
            out = out[:-4] + '.png'
    return out


def _structure_colour(rel, tint, out):
    im = Image.open(os.path.join(MOD, rel))
    a = np.asarray(im.convert('RGBA' if im.mode in ('RGBA', 'LA') else 'RGB')).astype(np.float32) / 255.0
    lin = np.clip(a[..., :1] * 2.0 * (np.array(tint[:3], np.float32) ** 2.2), 0.0, 1.0)
    rgb = (lin ** (1 / 2.2) * 255.0 + 0.5).astype(np.uint8)
    if a.shape[2] == 4:
        out = out[:-4] + '.png'
        jobs.write_image(os.path.join(MOD, out), np.dstack([rgb, (a[..., 3:] * 255).astype(np.uint8)]))
    else:
        jobs.write_image(os.path.join(MOD, out), rgb, quality=92)
    return out


def strips_map(m):
    """M_StructuresStrips_Parent's markings (its compiled shader): painted, lit stripes and signs, not lights. The mask
    T_Structures_Strips_M's R (the stripes) takes Color_1 and its G (the signs, letters) Color_2, mixed in linear; the
    opacity is R + G (the surface between them see-through). Baked into one colour + alpha map per pair of colours."""
    c1 = m['col'].get('Color_1') or [1.0, 1.0, 1.0]
    c2 = m['col'].get('Color_2') or [1.0, 1.0, 1.0]
    src = next((t for t in m['tex'].values() if t.startswith('T_Structures_Strips_M')), 'T_Structures_Strips_M')
    key = ('strips', src, tuple(c1), tuple(c2))
    if key in _made: return _made[key]
    rel = None
    a = _img(src)
    if a is not None:
        a = a.astype(np.float32) / 255
        lin1 = np.array(c1, np.float32) ** 2.2; lin2 = np.array(c2, np.float32) ** 2.2
        rgb = np.clip(a[..., 0:1] * lin1 + a[..., 1:2] * lin2, 0, 1) ** (1 / 2.2)
        al = np.clip(a[..., 0] + a[..., 1], 0, 1)
        img = np.dstack([np.round(rgb * 255), np.round(al * 255)]).astype(np.uint8)
        h = ''.join('%02x' % int(round(v * 255)) for v in list(c1) + list(c2))
        rel = _save(img, f'warships/maps/{src}_{h}.png', 1024)
    _made[key] = rel
    return rel


def material_entries(prefix, mats_used):
    """ships.json "materials" for the renamed glTF materials: {new name: (es2 material, tint index or None)}."""
    out = []
    for new, (src, ti) in mats_used.items():
        m = es2mat.resolve(src)
        kind = es2mat.classify(m)
        e = {'material': new}
        if isinstance(ti, tuple) and ti[0] == 'light':
            # M_Fx_Lights_Parent (its compiled shader): unlit, additive, the light atlas x the card's vertex colour (x (N.V)^2,
            # fading edge-on, left out). Drawn additively: no base colour (alpha 0), the atlas as the emission.
            em = tex('emit', LIGHT_ATLAS, 0)
            e.update({'diffuse': 'warships/maps/clear.png', 'opacity': 0.999, 'color': [0.0, 0.0, 0.0], 'metallic': 0.0,
                      'smoothness': 0.0, 'doubleSided': True, 'emissionColor': list(ti[1:]), 'emissionIntensity': 2.0})
            if em: e['emission'] = em
            out.append(e)
            continue
        if 'StructuresStrips' in m['root'] or 'StructuresStrips' in m['name']:
            d = strips_map(m)
            if d:
                e.update({'diffuse': d, 'alphaClip': 0.4, 'color': [1.0, 1.0, 1.0], 'metallic': 0.0, 'smoothness': 0.35})
                n = tex('normal', 'T_Structures_Strips_N')
                if n: e['normal'] = n
            else:
                e.update({'diffuse': 'warships/maps/clear.png', 'alphaClip': 0.5})
            out.append(e)
            continue
        if kind == 'decal':
            e.update({'diffuse': 'warships/maps/clear.png', 'alphaClip': 0.5})
        elif kind == 'field':
            c = m['col'].get('Color') or m['col'].get('FieldColor') or m['col'].get('Colour') or [0.35, 0.75, 1.0]
            e.update({'color': [round(v * 0.2, 3) for v in c], 'emissionColor': [round(v, 3) for v in c], 'emissionIntensity': 1.6,
                      'opacity': 0.22, 'doubleSided': True})
        elif kind == 'glow':
            tints = es2mat.vertex_tints(m)
            c, i = es2mat.glow_colour(m)
            if ti is not None and ti >= 10 and tints:
                # a band_glow material: see-through, its glow and opacity from the maps (split_prims' v = the vertex alpha)
                maps = band_maps(m)
                e.update({'color': [0.0, 0.0, 0.0], 'emissionColor': [round(v, 3) for v in tints[ti - 10]], 'emissionIntensity': i,
                          'metallic': 0.0, 'smoothness': 0.0})
                if maps: e.update({'emission': maps[0], 'diffuse': maps[1], 'opacity': 0.999})
                out.append(e)
                continue
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
            if es2mat.structure(m) and re.search(r'_c\d+a?\.png$', e.get('diffuse', '')) and e.get('color'):
                e['diffuse'] = structure_colour(e['diffuse'], e['color']); e['color'] = [1.0, 1.0, 1.0]
        out.append(e)
    return out


LIGHT_ATLAS = 'T_Structures_FX_Lights_001'


def is_light(m):
    """ES2's light cards (M_Fx_Lights_Parent): the traffic ships', some fighters' and drones' running lights."""
    return any('fx_lights' in n.lower() for n in m['chain'])


def split_prims(prefix, prims, mats_used, layered=False):
    """Renames every primitive's material "<prefix><n>|" (a vertex-colour-masked one into a material per tint) and returns
    the Writer's primitives."""
    names = {}
    out = []
    for attrs, tri, mname in prims:
        m = es2mat.resolve(mname)
        kind = es2mat.classify(m)
        vt = (kind == 'pbr' and es2mat.plan(m).get('tints')) or (kind == 'glow' and es2mat.vertex_tints(m))
        if is_light(m) and 'COLOR_0' in attrs:
            # a material per light colour (the cards' vertex colour, material_entries' 'light')
            col = attrs['COLOR_0'][:, :3]
            c = np.round((col[tri[:, 0]] + col[tri[:, 1]] + col[tri[:, 2]]) / 3 * 20) / 20
            keys = [tuple(round(float(v), 2) for v in k) for k in c]
            groups = [(('light',) + k, tri[[j for j, x in enumerate(keys) if x == k]]) for k in sorted(set(keys))]
        elif band_glow(m) and 'COLOR_0' in attrs and 'TEXCOORD_0' in attrs:
            # the colour by the mask's band under the face (u), the vertex alpha into v (material_entries: ti 10 + band)
            uv = np.array(attrs['TEXCOORD_0'], np.float32)
            al = np.clip(attrs['COLOR_0'][:, 3], 0.0, 1.0)
            uv[:, 1] = BAND_V0 + (BAND_V1 - BAND_V0) * al
            attrs = {**attrs, 'TEXCOORD_0': uv}
            u = (uv[tri[:, 0], 0] + uv[tri[:, 1], 0] + uv[tri[:, 2], 0]) / 3
            band = np.clip(np.floor(np.mod(u, 1.0) * 3).astype(int), 0, 2)
            seen = np.maximum(np.maximum(al[tri[:, 0]], al[tri[:, 1]]), al[tri[:, 2]]) > 0.01   # (all clear: nothing to draw)
            groups = [(10 + k, tri[(band == k) & seen]) for k in range(3)]
        elif vt and 'COLOR_0' in attrs:
            col = attrs['COLOR_0'][:, :3]
            c = (col[tri[:, 0]] + col[tri[:, 1]] + col[tri[:, 2]]) / 3
            if layered:
                # ES2's structures lerp BaseColor -> VtxR -> VtxG -> VtxB by the channels in turn: the last channel set wins
                # (white is VtxB), none set is BaseColor
                which = np.full(len(c), -1)
                w = (kind == 'pbr' and es2mat.plan(m).get('tintw')) or [1.0, 1.0, 1.0]
                for k in range(3):
                    if w[k] >= 0.5: which[c[:, k] >= 0.5] = k   # (a tint of alpha 0 lerps nowhere)
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


def engine_effects(bp):
    """ships.json "es2Engine" from a ship blueprint (and its parents, the child's values winning): its SpawnEngineGlow /
    SpawnEngineTrails, both off with EngineVFXEnabled false (BP_ShipBase's InitializeEngineVFX), None = both on. EVERSPACE 2's
    warships and freighters have them off (all but the Ancient Swarmer): their engines are their nozzles' glow. A blueprint
    that isn't a ship's (the Dreadnought, an actor of its own) has no engine effects at all."""
    found, n, seen, ship = {}, bp, set(), False
    while n and n not in seen:
        seen.add(n)
        d = _bp(n)
        if not d: break
        for e in d:
            if e.get('Name', '').startswith('Default__'):
                for k, v in (e.get('Properties') or {}).items():
                    if k in ('EngineVFXEnabled', 'SpawnEngineGlow', 'SpawnEngineTrails') and k not in found: found[k] = bool(v)
        if n == 'BP_ShipBase': ship = True
        n = _super(n)
    if not ship: return {'glow': False, 'trails': False}
    on = found.get('EngineVFXEnabled', True)
    glow, trails = on and found.get('SpawnEngineGlow', True), on and found.get('SpawnEngineTrails', True)
    return None if glow and trails else {'glow': glow, 'trails': trails}


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

def build_ship(sid, name, desc, race, kind, bp, meshes, turret, missile, hangar, extra_parts=None, traffic=True, traffic_extra=None):
    prims = []
    for m in meshes:
        p = os.path.join(SRC, 'Assets/Vehicles', m + '.glb')
        if not os.path.exists(p): say(f'  {name}: missing {m}'); return None
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
    import factions
    fac = factions.for_ship(sid, bp or ENGINE_BP.get(sid), race)   # its ES2 faction, never a GoF2 race (factions.py)
    if traffic_extra and traffic_extra.get('races'):
        traffic_extra = {**traffic_extra, 'races': factions.races(traffic_extra['races'])}
    ship = {'id': sid, 'name': name, 'description': desc, 'race': fac if fac else race,
            'armor': 20000 if kind == 'battleship' else 4000, 'cargo': 0, 'handling': 10, 'price': 0,
            'slots': {'primary': 0, 'secondary': 0, 'turret': 0, 'equipment': 0},
            'model': rel, 'modelLength': round(length), 'modelYaw': 90, 'engineStyle': 'es2',
            'mounts': mounts, 'materials': materials, 'subsystems': subs,
            'traffic': {'capital': kind, **({} if traffic else {'weight': 0}), **(traffic_extra or {})},
            'explosionScale': round(min(20.0, max(4.0, float(size.max()) * f / 250.0)), 1)}
    ebp = bp or ENGINE_BP.get(sid)
    effects = engine_effects(ebp) if ebp else None
    if effects: ship['es2Engine'] = effects
    tris = sum(len(i) // 3 for _, i, _ in out)
    say(f'  {name}: {round(float(size.max()) * f)} m, {tris} triangles, {len(eng) or len([m for m in mounts if m["slotType"] == 3])} engines, '
        f'{sum(1 for s in subs if s["kind"] == "turret")} turrets, {sum(1 for s in subs if s["kind"] == "hangar")} hangars, '
        f'{sum(1 for s in subs if s.get("weakspot"))} weak spots, {len(materials)} materials')
    return ship, f, prims, mats_used


def build(log=print):
    """ships.json entries for the warships, freighters, the Dreadnought and their props."""
    os.makedirs(os.path.join(MOD, 'warships', 'maps'), exist_ok=True)
    Image.fromarray(np.zeros((4, 4, 4), np.uint8)).save(os.path.join(MOD, 'warships', 'maps', 'clear.png'))
    ships, props = [], []
    # every warship and freighter on the workers (jobs.run), their lines printed in the table's order
    todo = list(WARSHIPS) + [(sid, name, desc, race, 'freighter', bp, meshes, turret, None, None)
                                              for sid, name, desc, race, bp, meshes, turret in FREIGHTERS]
    todo += [(sid, name, desc + ' EVERSPACE 2\'s civilian traffic.', races[0], 'freighter', bp, [mesh], None, None, None, None, True,
              {'races': races, 'weight': w}) for sid, name, desc, races, w, bp, mesh in CIVILIANS]
    for (sid, *_), (r, lines) in zip(todo, jobs.run(lambda w: logged(build_ship, *w), todo)):
        for l in lines: LOG(l)
        if not r: continue
        if sid == 'es2_okkar_frigate':   # its weak spots on ES2's weak point mesh
            subs, pr = frigate_weakpoints(r[1])
            r[0]['subsystems'] += subs; props += pr
        ships.append(r[0])
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
    ship = {'id': 'es2_dreadnought', 'name': 'Dreadnought', 'race': 'es2_ships:outlaw',
            'description': 'The Outlaws\' Dreadnought: a flying fortress of EVERSPACE 2, its hull shielded by energy absorbing fields, '
                           'armed with torpedo launchers, sniper and lightning turrets, flak and missile batteries, and five hangars of fighters.',
            'armor': 60000, 'cargo': 0, 'handling': 5, 'price': 0, 'slots': {'primary': 0, 'secondary': 0, 'turret': 0, 'equipment': 0},
            'model': rel, 'modelLength': round(length), 'modelYaw': 90, 'engineStyle': 'es2', 'mounts': mounts, 'materials': materials,
            'subsystems': subs, 'shieldMaterial': 'energyfield|', 'shieldedDamage': 0.0, 'hullFactor': 6.0,
            'traffic': {'capital': 'battleship', 'weight': 0}, 'explosionScale': 20.0,
            'es2Engine': engine_effects('BP_Dreadnought'),
            # never destroyed: it jumps away at an empty hull (BP_Encounter_Dreadnought_Base's OnHealthDepleted), so it can come again
            'retreat': True}
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
