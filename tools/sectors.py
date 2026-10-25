"""EVERSPACE 2's sectors as Galaxy on Fire 2 systems, and an "EVERSPACE 2" campaign card that plays in them (the remake's mod
systems, stations and campaigns: Modding/README.md "systems.json and stations.json", "Campaigns").

A sector comes from its travel-mode map (Maps/TravelMode/Map_TravelMode_SNN): BP_TravelMode_System (its name and colour),
BP_TravelMode_Sun at the origin (its colour), BP_TravelMode_Planet (each planet's material, atmosphere and surface colours,
ring, moon, destroyed), BP_TravelMode_Nebula (each local nebula's place, colour and size) and BP_TravelMode_Location (each
location's name, subtitle, place on the map and level, and SpaceObjects: where the sun, nebulas and planets lie from it).

A GoF2 system holds 7 stations, so each sector keeps 7 of its locations (SECTORS): those with a station to dock at, plus
landmark places as orbits without docking. Each orbit gets:
- its sun's direction and its nearest planet (yaw / pitch / size) from the location's SpaceObjects;
- its planet: the sector's planet, drawn here from ES2's planet textures (Assets/Environment/Planets/Textures: packed
  height / colour masks that ES2's planet materials colour at runtime) in the planet's own colours, as a lit disc for the
  orbit and a 2:1 map for the star map;
- its place on the star map's system view (angle and distance round the sun) from the location's place on ES2's map;
- a GoF2 station look of the location's faction (ES2's stations are levels of many pieces: assembling them is a later step).

The sky is one panorama for the system, composed here from ES2's sky textures (Assets/Environment/Skybox/Textures: the star
layer, and the nebula masks tinted with each local nebula's colour, placed where the nebulas lie as seen from the middle of
the kept locations) with a fixed rotation, so every orbit's sun direction matches it. The sun is the sector's colour.

Those textures are not in a plain FModel export: tools/shaders' export with tools/sector_assets.txt fetches them.

Coordinates: ES2 (X forward, Y right, Z up) -> GoF2 game (x left, y up, z ahead) = (-Y, Z, X); Unity = (x, y, -z)."""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import jobs

SRC = MOD = None
LOG = print

# The sectors built: the sector's travel map, its GoF2 system and its kept locations. A location: (ES2 id, GoF2 id, station
# look, interior race, tech level, planet id, asteroids). 'look': an original station number, "gof2:<model>", or None (no
# station, an empty orbit); a model with "nodock" is seen but can't be docked at. 'planet': the ES2 planet (S01P01 ..., or a
# moon by its actor name) the orbit circles. 'asteroids': None (the game's field), False (none) or a dict for the orbit.
# EVERSPACE 2's minable resources (Blueprints/Environment/Resources/BP_Minable_Resource_*: their resource id and rarity) as
# commodities (items.json, on a GoF2 ore: they mine, stack and trade like ores; no cores, those are the game's ores'). Iron
# and Titanium are the game's own. (id, ES2 name, kind, rarity, ES2 icon); prices by rarity against the game's ores
# (Iron 10-40, Titanium 150-165, Orichalzine 120-132).
RESOURCES = [
    ('copper', 'Copper', 'ore', 'common', 'item_resource_ore_copper'),
    ('insidium', 'Insidium', 'ore', 'uncommon', 'item_resource_ore_insidium'),
    ('baromite', 'Baromite', 'ore', 'rare', 'item_resource_ore_baromite'),
    ('clygon', 'Clygon', 'ore', 'rare', 'item_resource_ore_clygon'),
    ('glacit', 'Glacit', 'ore', 'superior', 'item_resource_ore_glacit'),
    ('coruscate', 'Coruscate', 'ore', 'superior', 'item_resource_ore_coruscate'),
    ('aetheum', 'Aetheum', 'crystal', 'common', 'item_resource_crystal_aetheum'),
    ('culver', 'Culver', 'crystal', 'uncommon', 'item_resource_crystal_culver'),
    ('mallemite', 'Mallemite', 'crystal', 'uncommon', 'item_resource_crystal_mallemite'),
    ('phazium', 'Phazium', 'crystal', 'rare', 'item_resource_crystal_phazium'),
]
RARITY_PRICE = {'common': 45, 'uncommon': 95, 'rare': 175, 'superior': 290}
RARITY_OCCURRENCE = {'common': 30, 'uncommon': 20, 'rare': 10, 'superior': 5}
ORE_BASE, CRYSTAL_BASE = 155, 160   # Titanium, Doxtrite: the look and kind they copy
def R(key, chance=1):
    """A resource as an orbit's ore with its whole-number weight."""
    return {'item': f'es2_ships:es2_{key}', 'chance': chance}
ORE_IRON, ORE_TITANIUM = 156, 155
SECTORS = {
    'S01': {
        'id': 'es2_ceto', 'race': 2, 'security': 2, 'position': [50, 50, 50],
        'spaceMusic': 'LayeredSong_003_1Calm', 'stationMusic': 'LayeredSong_004_1Calm',
        'locations': [
            ('S01L04', 'es2_union_bridge', 0, 2, 4, 'S01P02', {'count': 40, 'ores': [{'item': ORE_IRON, 'chance': 2}, R('copper', 3)]}),
            ('S01L08', 'es2_alcyone_station', 20, 3, 6, 'BP_TravelMode_Planet8', {'count': 40, 'ores': [{'item': ORE_TITANIUM, 'chance': 2}, R('copper', 2), R('insidium', 2)]}),
            ('S01L07P', 'es2_nephtys_plains', 21, 3, 6, 'S01P01',
             {'count': 160, 'type': 'rock', 'ores': [{'item': ORE_IRON, 'chance': 3}, {'item': ORE_TITANIUM, 'chance': 3}, R('copper', 6), R('insidium', 3), R('glacit', 1)]}),
            ('S01L15', 'es2_ceto_orbit', 70, 0, 9, 'S01P05', {'count': 60, 'type': 'ice', 'ores': [R('culver', 2), R('phazium', 1)]}),
            ('S01L11', 'es2_fort_cetus', 'gof2:station_pirates nodock', 2, 5, 'S01P04', False),
            ('S01L05', 'es2_gb_mining_grounds', None, 3, 5, 'S01P06',
             {'count': 220, 'type': 'ice', 'spread': 160000, 'ores': [R('aetheum', 6), R('culver', 4), R('mallemite', 4), R('phazium', 1)]}),
            ('S01L03', 'es2_ceto_outer_rim', None, 2, 3, 'S01P03',
             {'count': 180, 'type': 'rock', 'spread': 140000, 'ores': [{'item': ORE_IRON, 'chance': 3}, R('copper', 6), R('baromite', 3), R('clygon', 3), R('coruscate', 1)]}),
        ],
    },
}
# The campaign: where it starts and what with; the traffic per race (the mod's fighters, ES2's factions as the races).
CAMPAIGN = {
    'start': 'es2_union_bridge', 'ship': 'vanguard', 'credits': 5000, 'equipment': ['autocannon'],
    'traffic': {'terran': ['es2_coalition_fighter', 'es2_coalition_guard'],
                'vossk': ['es2_okkar_fighter', 'es2_okkar_interceptor', 'es2_okkar_protector'],
                'nivelian': ['es2_freelancer', 'es2_freelancer_escort'],
                'midorian': ['es2_gb_fighter', 'es2_gb_light_fighter'],
                'pirate': ['es2_outlaw_raider', 'es2_outlaw_scout', 'es2_outlaw_madcap', 'es2_outlaw_bomber', 'es2_outlaw_ravager']},
}
SKY_W, SKY_H = 8192, 4096
PLANET_MAP = (2048, 1024)


def configure(src, mod, log=print):
    global SRC, MOD, LOG
    SRC, MOD, LOG = src, mod, log


def available():
    """Whether the export holds what the sectors need: the travel maps and the sky / planet textures (sector_assets.txt)."""
    return (os.path.exists(os.path.join(SRC, 'Maps/TravelMode/Map_TravelMode_S01.json'))
            and os.path.exists(os.path.join(SRC, 'Assets/Environment/Skybox/Textures/T_Skybox_Stars_001_M.png'))
            and os.path.exists(os.path.join(SRC, 'Assets/Environment/Planets/Textures/T_Planet_Gas_001_C_H.png')))


# ---- reading a travel map ---------------------------------------------------------------------------------------------------

def _text(v):
    return (v or {}).get('SourceString') or (v or {}).get('LocalizedString') if isinstance(v, dict) else None


def _vec(v):
    return np.array([v['X'], v['Y'], v['Z']], np.float64) if v else np.zeros(3)


def _attr(o, key):
    for a in o.get('Attributes') or []:
        if a['Key'] == key: return a['Value']
    return None


def read(sector):
    """The sector's system, sun, planets, nebulas and locations from its travel map."""
    d = json.load(open(os.path.join(SRC, f'Maps/TravelMode/Map_TravelMode_{sector}.json'), encoding='utf-8-sig'))
    byname = {}
    for e in d: byname.setdefault(e.get('Name'), []).append(e)

    def place(actor):
        rc = ((actor.get('Properties') or {}).get('RootComponent') or {}).get('ObjectName', '')
        cname = rc.split('.')[-1].rstrip("'")
        for c in byname.get(cname, []):
            outer = c.get('Outer'); outer = outer.get('ObjectName') if isinstance(outer, dict) else outer
            if outer and actor['Name'] in str(outer): return _vec((c.get('Properties') or {}).get('RelativeLocation'))
        return np.zeros(3)

    out = {'planets': {}, 'nebulas': [], 'locations': {}, 'sun': [0.3, 0.65, 1.0], 'name': sector, 'colour': [0.1, 0.55, 1.0]}
    for e in d:
        t, p = e.get('Type'), e.get('Properties') or {}
        if t == 'BP_TravelMode_System_C':
            out['name'] = _text(p['SystemData'].get('Name')) or sector
            c = p.get('SystemColor'); out['colour'] = [c['R'], c['G'], c['B']] if c else out['colour']
        elif t == 'BP_TravelMode_Sun_C':
            c = p.get('Color'); out['sun'] = [c['R'], c['G'], c['B']] if c else out['sun']
        elif t == 'BP_TravelMode_Planet_C':
            pd = p.get('PlanetData') or {}
            mat = next((v for k, v in pd.items() if k.startswith('Material')), None)
            atm = next((v for k, v in pd.items() if k.startswith('AtmosphereColor')), None)
            sur = next((v for k, v in pd.items() if k.startswith('SurfaceAverageColor')), None)
            key = p.get('ID') or e['Name']
            out['planets'][key] = {
                'id': key, 'name': _text(p.get('Name')) or 'Moon',
                'material': (mat or {}).get('ObjectName', "''").split("'")[1] if mat else '',
                'atmosphere': [atm['R'], atm['G'], atm['B']] if atm else [0.6, 0.6, 0.6],
                'surface': [sur['R'], sur['G'], sur['B']] if sur else None,
                'ring': bool(p.get('Ring')), 'moon': bool(p.get('Moon')), 'destroyed': bool(p.get('Destroyed')),
                'variation': p.get('Variation', 0.5), 'pos': place(e)}
        elif t == 'BP_TravelMode_Nebula_C':
            c = p.get('Color'); sc = _attr(p, 'Scale')
            size = (sc['VectorValue']['X'] if sc else 1.0) or 1.0
            out['nebulas'].append({'colour': [c['R'], c['G'], c['B']], 'pos': place(e), 'radius': 2.0e6 * size, 'seed': p.get('Seed', 0)})
        elif t == 'BP_TravelMode_Location_C':
            L = p['LocationData']
            objs = []
            for o in L.get('SpaceObjects') or []:
                ty = _attr(o, 'Type')
                objs.append({'type': ty['IntValue'] if ty else 0, 'id': o.get('ID'), 'rel': _vec(o['RelativeTransform']['Translation'])})
            out['locations'][L['LocationID']] = {
                'id': L['LocationID'], 'name': _text(L.get('Name')), 'subtitle': _text(L.get('Subtitle')),
                'map': _vec(L.get('LocationOnMap')), 'level': L.get('StaticLevel'), 'objects': objs}
    # the moons have no ID: they are known by their actor name; their place in the locations' objects is by distance
    return out


def to_game(v):
    """ES2 (X forward, Y right, Z up) -> GoF2's game frame (x left, y up, z ahead)."""
    return np.array([-v[1], v[2], v[0]], np.float64)


def yaw_pitch(g):
    """An orbit's direction (yaw 0 behind a launching ship, 90 to its right; pitch up) of a game-frame vector."""
    g = g / (np.linalg.norm(g) or 1.0)
    return round(math.degrees(math.atan2(-g[0], -g[2])), 1), round(math.degrees(math.asin(max(-1.0, min(1.0, g[1])))), 1)


# ---- images ---------------------------------------------------------------------------------------------------------------

_tex = {}
def _texture(rel, size=None):
    """An ES2 texture as float32 0..1 (RGBA), shrunk to 'size' (square)."""
    key = (rel, size)
    with jobs.once(('sectex',) + key):
        if key not in _tex:
            im = Image.open(os.path.join(SRC, rel)).convert('RGBA')
            if size and im.size[0] > size: im = im.resize((size, size), Image.LANCZOS)
            _tex[key] = np.asarray(im, np.float32) / 255.0
    return _tex[key]


PLANET_TEX = 'Assets/Environment/Planets/Textures/'
SKY_TEX = 'Assets/Environment/Skybox/Textures/'


def _sample(tex, u, v):
    """Bilinear sample of a tiling texture at u, v (0..1, any range)."""
    h, w = tex.shape[:2]
    x = (u % 1.0) * w - 0.5; y = (v % 1.0) * h - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x0 %= w; y0 %= h; x1 = (x0 + 1) % w; y1 = (y0 + 1) % h
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) + tex[y1, x0] * (1 - fx) * fy + tex[y1, x1] * fx * fy)


def _ramp(t, stops):
    """A colour ramp: t 0..1 through [(at, [r, g, b]), ...]."""
    t = np.clip(t, 0.0, 1.0)
    out = np.zeros(t.shape + (3,), np.float32)
    for (a0, c0), (a1, c1) in zip(stops, stops[1:]):
        k = np.clip((t - a0) / max(a1 - a0, 1e-6), 0.0, 1.0)[..., None]
        sel = ((t >= a0) & (t <= a1))[..., None]
        out = np.where(sel, np.array(c0, np.float32) * (1 - k) + np.array(c1, np.float32) * k, out)
    return out


def _hue(c, deg):
    """A colour with its hue turned by 'deg' degrees."""
    import colorsys
    h, l, sat = colorsys.rgb_to_hls(*[float(x) for x in c])
    return np.array(colorsys.hls_to_rgb((h + deg / 360.0) % 1.0, l, sat), np.float32)


def planet_map(pl):
    """The planet's surface as a 2:1 map (float RGB), from ES2's packed planet textures in its own colours (ES2 colours them
    in its planet materials at runtime: the masks' colour channel through a ramp of the planet's colours)."""
    w, h = PLANET_MAP
    lon = (np.arange(w) + 0.5) / w; lat = (np.arange(h) + 0.5) / h
    u = np.repeat(lon[None, :], h, 0) * 2.0      # (the square texture twice round the planet)
    v = np.repeat(lat[:, None], w, 1)
    atm = np.array(pl['atmosphere'], np.float32); sur = np.array(pl['surface'] or pl['atmosphere'], np.float32)
    mat = pl['material'].lower(); shift = pl['variation']
    if 'gas' in mat:
        # ES2 sets one gas material on several planets and varies them by 'Variation': here the banding's scale and
        # turbulence, the texture, and a small turn of the colour's hue
        turbulent = 'smooth' in mat or shift > 0.6
        t = _texture(PLANET_TEX + ('T_Planet_Gas_002_C_H.png' if turbulent else 'T_Planet_Gas_001_C_H.png'), 2048)
        s = _sample(t, u + shift * 3.1, v * (0.3 + shift * 0.6) + shift * 0.7)
        c, hgt = s[..., 0], s[..., 1]
        atm = _hue(atm, (shift - 0.5) * 50.0)
        dark = _hue(atm, -25.0) * 0.22
        col = _ramp(c * 0.7 + hgt * 0.3, [(0.0, dark), (0.45, atm * 0.7), (0.75, atm), (1.0, np.minimum(atm * 0.6 + 0.45, 1.0))])
    elif 'earthlike' in mat or 'water' in mat:
        land = _sample(_texture(PLANET_TEX + 'T_Planet_GlobalMask_M.png', 2048)[..., :1].repeat(4, -1), u + shift, v)[..., 0]
        m = _sample(_texture(PLANET_TEX + 'T_Planet_Mountains_001_H_C_R.png', 2048), u * 2, v * 2)
        clouds = _sample(_texture(PLANET_TEX + 'T_Planet_Clouds_001_C_AO.png', 2048), u + 0.3, v)[..., 0]
        sea = _ramp(m[..., 0], [(0.0, atm * 0.12), (1.0, atm * 0.35)])
        ground = _ramp(m[..., 1], [(0.0, [0.16, 0.22, 0.10]), (0.5, [0.32, 0.36, 0.18]), (0.8, [0.55, 0.45, 0.30]), (1.0, [0.85, 0.82, 0.78])])
        k = np.clip((land - 0.45) * 8.0, 0.0, 1.0)[..., None]
        col = sea * (1 - k) + ground * k
        col = col * (1 - clouds[..., None] * 0.8) + clouds[..., None] * 0.9
        pole = np.abs(v - 0.5) * 2
        col = np.where((pole > 0.88)[..., None], np.minimum(col + 0.6, 0.95), col)
    elif pl['destroyed'] or 'cratered' in mat or not mat:
        t = _sample(_texture(PLANET_TEX + 'T_Planet_Craters_001_H_C_R.png', 2048), u, v)
        base = sur if pl['surface'] else np.array([0.5, 0.5, 0.5], np.float32)
        col = _ramp(t[..., 1] * 0.6 + t[..., 0] * 0.4, [(0.0, base * 0.25), (0.6, base * 0.7), (1.0, np.minimum(base * 1.1, 1.0))])
        if pl['destroyed']:   # its broken crust: glowing fissures along the mask's edges
            m = _sample(_texture(PLANET_TEX + 'T_Planet_GlobalMask_M.png', 2048)[..., :1].repeat(4, -1), u * 1.5, v * 1.5)[..., 0]
            crack = np.exp(-((m - 0.5) * 18.0) ** 2)[..., None]
            col = col * (1 - crack) + np.array([1.0, 0.45, 0.12], np.float32) * crack
    else:   # desert / rock
        t = _sample(_texture(PLANET_TEX + 'T_Planet_Rock_001_H_C_R.png', 2048), u, v)
        col = _ramp(t[..., 1] * 0.7 + t[..., 0] * 0.3, [(0.0, sur * 0.35), (0.5, sur * 0.75), (0.85, sur), (1.0, np.minimum(sur * 1.15, 1.0))])
    return np.clip(col, 0.0, 1.0)


def planet_disc(surface, atm, size=512, light=(-0.55, 0.45, 0.70)):
    """The planet as GoF2 draws an orbit's planet: a lit sphere on transparency, its atmosphere's rim in its colour."""
    r = size / 2 - 6
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    nx = (x + 0.5 - size / 2) / r; ny = (size / 2 - y - 0.5) / r
    d2 = nx * nx + ny * ny
    inside = d2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - d2, 0.0, 1.0))
    lon = np.arctan2(nx, nz) / (2 * math.pi) + 0.5; lat = 0.5 - np.arcsin(np.clip(ny, -1, 1)) / math.pi
    h, w = surface.shape[:2]
    col = surface[np.clip((lat * h).astype(int), 0, h - 1), np.clip((lon * w).astype(int), 0, w - 1)]
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0.0, 1.0)
    shade = 0.04 + 0.96 * lam ** 0.8
    atm = np.array(atm, np.float32)
    rim = (1.0 - nz) ** 2.5 * np.clip(lam * 1.4 + 0.1, 0.0, 1.0)
    rgb = col * shade[..., None] + atm * rim[..., None] * 0.9
    # a thin glow just outside the edge
    d = np.sqrt(d2)
    halo = np.clip(1.0 - (d - 1.0) * r / 6.0, 0.0, 1.0) * (d > 1.0) * np.clip(lam * 1.2 + 0.15, 0, 1)
    a = np.where(inside, 1.0, halo * 0.6)
    rgb = np.where(inside[..., None], rgb, atm * 0.9)
    out = np.dstack([np.clip(rgb, 0, 1), a]) * 255
    return out.astype(np.uint8)


def sun_image(colour, size=512):
    """The sector's sun: a small white-hot core and a glow in its colour fading to black well inside the edge (the guide)."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((x + 0.5 - size / 2) ** 2 + (y + 0.5 - size / 2) ** 2) / (size / 2)
    c = np.array(colour, np.float32); c = c / max(c.max(), 1e-6)
    core = np.clip(1.0 - r / 0.09, 0.0, 1.0) ** 0.6
    glow = np.exp(-(r / 0.22) ** 2) * 0.8 + np.exp(-(r / 0.5) ** 2) * 0.25
    glow *= np.clip(1.0 - (r - 0.75) / 0.2, 0.0, 1.0)
    rgb = core[..., None] + (glow[..., None] * c) * (1 - core[..., None])
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def sky_panorama(sec, centre, out_path):
    """The system's sky (2:1): ES2's star layer and its nebula masks in each local nebula's colour, where the nebulas lie from
    'centre' (ES2 map units), and a faint haze of the system colour; written in bands of rows on the workers."""
    stars = _texture(SKY_TEX + 'T_Skybox_Stars_001_M.png')
    neb_a = _texture(SKY_TEX + 'T_Skybox_Nebula_Global_001_M.png', 2048)
    neb_b = _texture(SKY_TEX + 'T_Skybox_Nebula_005_M.png', 2048)
    nebs = []
    for n in sec['nebulas']:
        g = to_game(n['pos'] - centre); dist = np.linalg.norm(g) or 1.0
        u = np.array([g[0], g[1], -g[2]]) / dist            # Unity frame
        ang = max(0.45, math.atan2(n['radius'], dist)) * 2.4
        nebs.append((u, ang, np.array(n['colour'], np.float32), n['seed']))
    sysc = np.array(sec['colour'], np.float32)
    img = np.zeros((SKY_H, SKY_W, 3), np.uint8)

    def band(r0):
        r1 = min(SKY_H, r0 + 256)
        v = 1.0 - (np.arange(r0, r1) + 0.5) / SKY_H                # 1 top
        uu = (np.arange(SKY_W) + 0.5) / SKY_W
        lat = (v - 0.5) * math.pi; lon = (uu - 0.5) * 2 * math.pi
        LAT, LON = np.meshgrid(lat, lon, indexing='ij')
        dx = np.cos(LAT) * np.sin(LON); dy = np.sin(LAT); dz = np.cos(LAT) * np.cos(LON)
        V = np.repeat(v[:, None], SKY_W, 1); U = np.repeat(uu[None, :], SKY_W, 0)[:len(v)]
        # stars: the 4096 layer twice round, once top to bottom (2 x 1 tiles of the 8192 x 4096 sky)
        sx = (np.arange(SKY_W) % 4096); sy = np.arange(r0, r1) % 4096
        col = stars[sy[:, None], sx[None, :], :3] * 1.6
        haze = _sample(neb_a, U * 2.0, V * 1.0)
        band_w = np.exp(-(dy / 0.35) ** 2)          # a faint band of the system's colour round the sky (the galaxy's plane)
        col = col + sysc * ((haze[..., 1] * 0.10 + 0.012) * (0.35 + band_w))[..., None]
        for i, (n, ang, c, seed) in enumerate(nebs):
            cosang = np.clip(dx * n[0] + dy * n[1] + dz * n[2], -1.0, 1.0)
            a = np.arccos(cosang)
            w = np.exp(-(a / ang) ** 2)
            t = neb_a if i % 2 == 0 else neb_b
            s = _sample(t, U * 3.0 + (seed % 97) / 97.0, V * 1.5 + (seed % 31) / 31.0)
            dens = (s[..., 0] * 0.65 + s[..., 1] * 0.35) * w
            col = col + c * (dens ** 1.25 * 1.1)[..., None] + c * (w * 0.06)[..., None]
        img[r0:r1] = (np.clip(col, 0, 1) ** (1 / 1.05) * 255).astype(np.uint8)

    jobs.run(band, range(0, SKY_H, 256))
    Image.fromarray(img).save(out_path, quality=92)


# ---- the system --------------------------------------------------------------------------------------------------------------

def _write_png(rel, arr):
    return jobs.write_image(os.path.join(MOD, rel), arr)


def build_sector(key):
    """systems.json / stations.json entries of one sector, its images and music; returns (system, stations, music files)."""
    spec = SECTORS[key]
    sec = read(key)
    sid = spec['id']
    os.makedirs(os.path.join(MOD, 'sectors', sid), exist_ok=True)
    kept = [l for l in spec['locations'] if l[0] in sec['locations']]
    centre = np.mean([sec['locations'][l[0]]['map'] for l in kept], axis=0)
    # the sky and the sun
    sky_rel = f'sectors/{sid}/sky.jpg'
    sky_panorama(sec, centre, os.path.join(MOD, sky_rel))
    sun_rel = _write_png(f'sectors/{sid}/sun.png', sun_image(sec['sun']))[len(MOD) + 1:]
    sc = np.array(sec['sun'], np.float32); sc = sc / max(sc.max(), 1e-6)
    system = {'id': sid, 'name': sec['name'], 'race': spec['race'], 'security': spec['security'], 'visible': True,
              'position': spec['position'], 'sky': 3,
              'sunTexture': sun_rel.replace(os.sep, '/'), 'sunColor': [round(float(0.55 + 0.45 * v), 3) for v in sc],
              'skybox': {'nebula': sky_rel, 'stars': 'none', 'rotation': [0, 0, 0]}}
    # the planets the kept orbits circle
    made = {}
    def planet_images(pid):
        if pid in made: return made[pid]
        pl = sec['planets'].get(pid)
        if not pl: made[pid] = None; return None
        surf = planet_map(pl)
        name = pl['name'].lower().replace(' ', '_') + ('' if pl['name'] != 'Moon' else '_' + pid[-1])
        disc = _write_png(f'sectors/{sid}/planet_{name}.png', planet_disc(surf, pl['atmosphere']))[len(MOD) + 1:]
        mp = _write_png(f'sectors/{sid}/map_{name}.png', (surf * 255).astype(np.uint8))[len(MOD) + 1:]
        made[pid] = (disc.replace(os.sep, '/'), mp.replace(os.sep, '/'), pl)
        return made[pid]
    stations = []
    radius_max = max(np.linalg.norm(sec['locations'][l[0]]['map'][:2]) for l in kept) or 1.0
    for es2_id, gid, look, interior, tech, pid, asteroids in kept:
        L = sec['locations'][es2_id]
        st = {'id': gid, 'system': f'es2_ships:{sid}', 'name': L['name'], 'techLevel': tech, 'planet': 6, 'interior': interior}
        orbit = {}
        if look is None:
            orbit['station'] = False
        elif isinstance(look, int):
            st['looksLike'] = look
        else:
            model, *flags = look.split()
            st['model'] = model; st['modelSize'] = 30000
            if 'nodock' in flags: orbit['station'] = 'nodock'
        sun = next((o for o in L['objects'] if o['type'] == 1), None)
        if sun is not None: orbit['sun'] = list(yaw_pitch(to_game(sun['rel'])))
        # the orbit's planet: its own; its direction and size by how near it is
        pi = planet_images(pid)
        target = None
        if pi:
            pos = sec['planets'][pid]['pos']; loc = L['map']
            target = next((o for o in L['objects'] if o['id'] == pid), None)
            rel = target['rel'] if target is not None else pos - loc
            dist = np.linalg.norm(rel) / 1e6
            yw, pt = yaw_pitch(to_game(rel))
            orbit['planet'] = {'size': round(float(np.clip(2.2 - dist * 0.35, 0.8, 2.2)), 2), 'yaw': yw, 'pitch': pt}
            st['planetTexture'] = pi[0]; st['mapTexture'] = pi[1]
            if pi[2]['ring']: st['mapRing'] = True
        if asteroids is False: orbit['asteroids'] = False
        elif asteroids: orbit['asteroids'] = dict(asteroids)
        orbit['jumpgate'] = False
        st['orbit'] = orbit
        m = L['map']
        st['mapPlace'] = {'angle': round(math.degrees(math.atan2(m[1], m[0])) % 360, 1),
                          'distance': round(8000 + 37000 * float(np.linalg.norm(m[:2])) / radius_max)}
        stations.append(st)
        LOG(f'  {L["name"]} ({L["subtitle"]}): ' + ('station' if 'station' not in orbit else str(orbit['station'])) +
            f', planet {sec["planets"][pid]["name"] if pid in sec["planets"] else "-"}')
    return system, stations, sec


def card(sky_path, planet_path, title, subtitle, out):
    """The campaign card (580 x 896): a crop of the sector's sky, its planet, the title."""
    W, H = 580, 896
    sky = Image.open(sky_path).convert('RGB')
    # the brightest part of the sky (its nebulas) in a card-shaped crop
    small = np.asarray(sky.resize((256, 128)), np.float32).sum(-1)
    cx = int(np.argmax(small.sum(0)) / 256 * sky.size[0]); cy = int(np.argmax(small.sum(1)) / 128 * sky.size[1])
    ch = int(sky.size[1] * 0.42); cw = int(ch * W / H)
    x0 = min(max(0, cx - cw // 2), sky.size[0] - cw); y0 = min(max(0, cy - ch // 2), sky.size[1] - ch)
    im = sky.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS).convert('RGBA')
    pl = Image.open(planet_path).convert('RGBA').resize((520, 520), Image.LANCZOS)
    im.alpha_composite(pl, (W - 330, H - 470))
    shade = Image.new('RGBA', (W, 240), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    for y in range(240): sd.line([(0, y), (W, y)], fill=(4, 6, 12, int(210 * (y / 240) ** 1.2)))
    im.alpha_composite(shade, (0, H - 240))
    d = ImageDraw.Draw(im)
    def font(size, bold=True):
        for n in (("DejaVuSans-Bold.ttf", "arialbd.ttf") if bold else ("DejaVuSans.ttf", "arial.ttf")):
            try: return ImageFont.truetype(n, size)
            except OSError: pass
        return ImageFont.load_default()
    d.text((30, H - 150), title, font=font(46), fill=(245, 246, 250))
    d.text((32, H - 92), subtitle, font=font(24, False), fill=(200, 215, 235))
    im.convert('RGB').save(out, quality=92)


def resource_items(mod):
    """items.json entries of ES2's resources (their icons on the commodity plate, icons.py)."""
    import icons
    out = []
    for key, name, kind, rarity, icon in RESOURCES:
        p = RARITY_PRICE[rarity]
        out.append({'id': f'es2_{key}', 'base': CRYSTAL_BASE if kind == 'crystal' else ORE_BASE, 'name': name,
                    'description': f'An EVERSPACE 2 {kind} ({rarity}), mined from the asteroids where it occurs.',
                    'techLevel': 1, 'occurrence': RARITY_OCCURRENCE[rarity], 'price': [p, int(round(p * 1.1))],
                    '_icon': icon + '_86x86_2x', '_frame': 'commodity'})
    icons.apply(out, mod)
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    return out


def build(log=print):
    """The sectors (systems.json, the stations to add to stations.json), the campaign (campaign.json) and its card. Returns
    (systems, stations, items: ES2's resources)."""
    global LOG
    LOG = log
    systems, stations = [], []
    music = []
    for key in SECTORS:
        system, sts, sec = build_sector(key)
        spec = SECTORS[key]
        systems.append(system); stations += sts
        music.append((system, sts, spec))
    jobs.flush()
    # the music: each sector's calm layers (its space and docked tracks)
    try:
        import audio
        if audio.available():
            for system, sts, spec in music:
                waves, tmp = audio.decode([spec['spaceMusic'].replace('LayeredSong', 'S_LayeredSong'), spec['stationMusic'].replace('LayeredSong', 'S_LayeredSong')])
                sp = waves.get('S_' + spec['spaceMusic']); stm = waves.get('S_' + spec['stationMusic'])
                if sp:
                    audio.write(sp, f'music/{system["id"]}_space'); system['spaceMusic'] = f'{system["id"]}_space'
                if stm:
                    audio.write(stm, f'music/{system["id"]}_station')
                    for s in sts:
                        if s.get('orbit', {}).get('station', True) is True: s['music'] = f'{system["id"]}_station'
                import shutil; shutil.rmtree(tmp, ignore_errors=True)
                LOG(f'  music: {"space" if sp else "-"}, {"docked" if stm else "-"}')
    except Exception as e:
        LOG(f'  no sector music: {e}')
    # the campaign
    start = next(s for s in stations if s['id'] == CAMPAIGN['start'])
    first = systems[0]
    card(os.path.join(MOD, first['skybox']['nebula']), os.path.join(MOD, start['planetTexture']),
         'EVERSPACE 2', f'{first["name"]} sector', os.path.join(MOD, 'campaign.jpg'))
    traffic = {race: [f'es2_ships:{s}' for s in ships] for race, ships in CAMPAIGN['traffic'].items()}
    campaign = {
        'name': 'EVERSPACE 2',
        'description': f'Start over in EVERSPACE 2\'s {first["name"]} sector: {len(stations)} of its places, its planets and '
                       'sky, ES2\'s factions and ships. A prototype: one sector so far.',
        'image': 'campaign.jpg', 'showTitle': False,
        'startStation': f'es2_ships:{CAMPAIGN["start"]}', 'startShip': f'es2_ships:{CAMPAIGN["ship"]}',
        'credits': CAMPAIGN['credits'], 'equipment': [f'es2_ships:{i}' for i in CAMPAIGN['equipment']],
        'galaxy': 'mod', 'ships': 'mod', 'trafficShips': traffic}
    json.dump(campaign, open(os.path.join(MOD, 'campaign.json'), 'w', encoding='utf-8'), indent=1)
    LOG(f'  campaign: "EVERSPACE 2", starting at {start["name"]}')
    items = resource_items(MOD)
    LOG(f'  {len(items)} of EVERSPACE 2\'s resources as commodities ({sum(1 for i in items if i.get("icon"))} icons)')
    return systems, stations, items
