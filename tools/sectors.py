"""EVERSPACE 2's sectors as Galaxy on Fire 2 systems (the remake's mod systems and stations: Modding/README.md "systems.json
and stations.json"). ES2's galaxy is a galaxy of its own: its sectors lie in a cluster past the edge of GoF2's star map, in
ES2's own layout (GALAXY), linked to each other only by ES2's own jumpgates and to GoF2's systems by none, so a Khador Drive
is the way there. They belong to ES2's factions (factions.py) and only ES2's ships fly there.

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
import re
import json, math, os
import numpy as np
from PIL import Image
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
    # (only in Okkar space: ES2's ore_okkar1 and crystal_okkar1, its loot_mining.csv)
    ('khaitium', 'Khaïtium', 'ore', 'uncommon', 'khaitium'),
    ('cymalite', 'Cymalite', 'crystal', 'uncommon', 'cymalite'),
]
# ES2's resources that its NPCs drop (its loot_npcs.csv: the Ancient Wardens' and the Redeemers' dark energy, dark matter and
# solar particles, the Okkar's nanospheres, Viridian Energy, components and Eshahar Fragments; fighters.py puts them in
# their "traffic.loot"), and biomass, which in ES2 only the Leviathans' pearls drop (left out): here a trade good the
# stations stock. (ES2 id, its icon, occurrence: 0 = only dropped)
DROPS = [('dark_energy', 'item_dark_energy_86x86_2x', 0), ('dark_matter', 'item_exotic_1_86x86_2x', 0),
         ('solar_particles', 'item_solar_particles_86x86_2x', 0), ('resources_okkar', 'item_okkar_nanospheres_86x86_2x', 0),
         ('resources_okkar_special', 'item_viridian_energy_86x86_2x', 0), ('okkar_component_1', 'TR_hyper_filament_86x86_2x', 0),
         ('okkar_component_2', 'TR_spatial_regulator_86x86_2x', 0), ('eshahar_fragments', 'eshahar_fragments_86x86_2x', 0),
         ('biomass', 'item_biomass_86x86_2x', 15)]
DROP_PRICE_FACTOR = 0.25   # ES2's item_price against the mod's (crafting.PRICE_FACTOR)
OKKAR_KEYS = {'ore_okkar1': 'khaitium', 'crystal_okkar1': 'cymalite', 'crystal_okkar': 'cymalite'}   # (Refined Cymalite too)


def drop_ref(es2_id):
    """The mod's item for an ES2 drop resource or a resource of RESOURCES ('ore_copper_common' -> its Copper), None if none."""
    if any(es2_id == d[0] for d in DROPS): return f'es2_ships:es2_{es2_id}'
    for kind in ('ore_', 'crystal_'):
        if es2_id.startswith(kind):
            key = OKKAR_KEYS.get(es2_id.rsplit('_', 1)[0], es2_id[len(kind):].rsplit('_', 1)[0])
            if any(key == r[0] for r in RESOURCES): return f'es2_ships:es2_{key}'
    return None
RARITY_PRICE = {'common': 45, 'uncommon': 95, 'rare': 175, 'superior': 290}
RARITY_OCCURRENCE = {'common': 30, 'uncommon': 20, 'rare': 10, 'superior': 5}
ORE_BASE, CRYSTAL_BASE = 155, 160   # Titanium, Doxtrite: the look and kind they copy
def R(key, chance=1):
    """A resource as an orbit's ore with its whole-number weight."""
    return {'item': f'es2_ships:es2_{key}', 'chance': chance}
ORE_IRON, ORE_TITANIUM = 156, 155
SECTORS = {
    'S01': {
        # 'gates': the ES2 sectors its jumpgate reaches (links(): ES2's own jumpgates and wormholes), from 'gateStation'
        # (Union Bridge, ES2's "Jump Gate & Trading Station")
        # 'race': the faction that owns it (factions.py), 'locals' its local fighters' factions, 'raiders' who raids it; only
        # ES2's ships fly there (systems.json "traffic": "mod"): ES2's galaxy has none of GoF2's races
        # (Ceto is laid out by hand; the other sectors by auto_spec from ES2's own data)
        'id': 'es2_ceto', 'race': 'gb', 'locals': ['gb', 'freelancer'], 'raiders': ['outlaw'], 'security': 2,
        'gateStation': 'es2_union_bridge',
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

# Every sector of ES2's galaxy (its travel maps: Maps/TravelMode/Map_TravelMode_SNN); those not in SECTORS are laid out by
# auto_spec from ES2's own data.
SECTOR_KEYS = ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08', 'S09', 'S14']

# What ES2 doesn't say in data, the remake's picks from its story: who owns a sector where its stations disagree (the Khaït
# Nebula's stations are freelance traders in Okkar space), and who raids it (ES2 spawns its enemies per encounter, not per
# sector): the factions met there.
OWNER = {'S04': 'okkar'}
RAIDERS = {'S02': ['outlaw'], 'S03': ['outlaw', 'retaliators'], 'S04': ['cultist', 'okkar_prime'], 'S05': ['okkar_prime'],
           'S06': ['outlaw', 'retaliators'], 'S07': ['rogueai', 'zurilia'], 'S08': ['zurilia', 'outlaw'],
           'S09': ['ancient'], 'S14': ['okkar_prime', 'ancient']}
# A faction's station looks (original stations of the GoF2 race whose hangar and bar it borrows, factions.py) and interior
# race (0 Terran, 1 Vossk, 2 Nivelian, 3 Midorian)
FACTION_LOOK = {'gb': ([20, 22, 23, 24, 21], 3), 'freelancer': ([0, 1, 3, 2, 4, 30, 47], 2),
                'coalition': ([5, 6, 8, 9, 7, 10, 37], 0), 'kato': ([42, 37], 0), 'okkar': ([16, 17, 28, 26, 18, 25, 29], 1),
                'outlaw': (['gof2:station_pirates'], 2)}
# Places whose names say the asteroids are the point of them, and places hostile factions hold (seen, not docked at)
MINING_WORDS = ('asteroid', 'belt', 'mining', 'field', 'deposit', 'ridge', 'cluster', 'fault', 'rift', 'shelf')
HOSTILE_WORDS = ('outlaw', 'stronghold', 'smugglers', 'immaculate', 'ascension')
# Places of war wrecks: the remake's orbit "wrecks" (a field of wreck containers to salvage, World.WreckField)
WRECK_WORDS = ('wreck', 'remains', 'ghost fleet', 'scrapyard', 'derelict', 'graveyard', 'torn station', 'station debris')

def is_wreck_place(L):
    """A place of war wrecks, by its name or subtitle (ES2's Wreck Field, Ghost Fleet, Warship Remains, ...)."""
    text = ((L.get('name') or '') + ' ' + (L.get('subtitle') or '')).lower()
    return any(w in text for w in WRECK_WORDS)
# The ores of a sector by its locations' ES2 level: low, middle, high
ORES = {
    'low': [{'item': ORE_IRON, 'chance': 2}, R('copper', 3), R('aetheum', 2), R('insidium', 1)],
    'mid': [{'item': ORE_TITANIUM, 'chance': 2}, R('insidium', 2), R('culver', 2), R('mallemite', 2), R('baromite', 1), R('clygon', 1)],
    'high': [R('baromite', 2), R('clygon', 2), R('glacit', 2), R('coruscate', 1), R('phazium', 2), R('mallemite', 1)],
}


def _slug(text):
    import re, unicodedata
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', t).strip('_')


_dockables = None
def dockables():
    """ES2's dockable stations (DataFiles/dockables.CSV): [{id, name, faction, system, location, trader}]."""
    global _dockables
    if _dockables is None:
        _dockables = []
        p = os.path.join(SRC, 'DataFiles', 'dockables.CSV')
        if os.path.exists(p):
            for line in open(p, encoding='cp1252', errors='replace'):   # (Windows-1252, like locations.CSV)
                c = line.rstrip('\r\n').split('|~')
                if len(c) < 13 or not c[0]: continue
                _dockables.append({'id': c[0], 'name': c[1], 'faction': c[2], 'system': c[3], 'location': c[4],
                                   'trader': c[11] == '1'})
    return _dockables


_secs = {}
def sector(key):
    with jobs.once(('sector', key)):
        if key not in _secs: _secs[key] = read(key)
    return _secs[key]


def system_id(key):
    """A sector's GoF2 system id (es2_<its name>)."""
    return SECTORS[key]['id'] if key in SECTORS else 'es2_' + _slug(sector(key)['name'])


def links():
    """ES2's galaxy as GoF2 sees it: {sector: {'gate': the location its gate is at, 'to': [sectors]}}, from every location's
    jumpgates and wormholes (a GoF2 system has one jumpgate, so all of a sector's links go through one: a security-zone
    gate first, then one named a gate, then the first); links inside a sector left out."""
    where = {}
    for k in SECTOR_KEYS:
        for lid in sector(k)['locations']: where[lid] = k
    out = {}
    for k in SECTOR_KEYS:
        cand = []
        for L in sector(k)['locations'].values():
            to = [where[t] for kind, ids in L['links'] for t in ids if t in where and where[t] != k]
            if to: cand.append((L, to))
        if not cand: continue
        def rank(c):
            L, to = c
            jump = any(kind == 'JumpGate' for kind, _ in L['links'])
            return (not L['security'], 'gate' not in (L['name'] or '').lower(), not jump, L['id'])
        cand.sort(key=rank)
        out[k] = {'gate': cand[0][0]['id'], 'to': sorted({t for _, to in cand for t in to})}
    return out


def _nearest_planet(sec, L):
    """The planet (or moon) a location circles: the nearest planet among its space objects, else by the map."""
    best = None
    for o in L['objects']:
        if o['type'] == 2 and o['id'] in sec['planets']:
            d = np.linalg.norm(o['rel'])
            if best is None or d < best[0]: best = (d, o['id'])
    if best: return best[1]
    if not sec['planets']: return None
    return min(sec['planets'].values(), key=lambda p: np.linalg.norm(p['pos'] - L['map']))['id']


def auto_spec(key):
    """A sector's spec as SECTORS writes it, from ES2's data: its dockable stations (dockables.CSV: their factions, the
    owner the most of them), its gate location (links()), landmark places to fill the 7 orbits, tech levels and ores by
    the locations' ES2 levels, its music (Audio/MusikSets/DA_MusicSet_Sector_NNN: the set's first two songs)."""
    sec = sector(key)
    sys_no = str(int(key[1:]))
    docks = [d for d in dockables() if d['system'] == sys_no and d['trader'] and d['location'] in sec['locations']]
    by_loc = {}
    for d in docks: by_loc.setdefault(d['location'], []).append(d)
    count = {}
    for d in docks:
        if d['faction'] in FACTION_LOOK: count[d['faction']] = count.get(d['faction'], 0) + 1
    owner = OWNER.get(key) or (max(count, key=count.get) if count else 'freelancer')
    locals_ = [owner] + [f for f in sorted(count, key=lambda f: -count[f]) if f != owner and f in ('gb', 'freelancer', 'coalition', 'okkar', 'kato')][:1]
    if len(locals_) == 1: locals_.append('freelancer' if owner != 'freelancer' else 'coalition')
    gate = links().get(key, {}).get('gate')

    def ok(L):
        n = L['name'] or ''
        return not (L['hidden'] or n.startswith('**') or '?' in n or 'notinuse' in n.lower())
    locs = [L for L in sec['locations'].values() if ok(L)]
    # the orbits: the gate, then the stations (the most traders first, main locations before mini ones), then landmarks
    # (mining places, then hostile holds, then the rest), at most 7, no name twice
    chosen, names = [], set()
    def take(L):
        if L['id'] in [c['id'] for c in chosen] or (L['name'] or '').lower() in names or len(chosen) >= 7: return
        chosen.append(L); names.add((L['name'] or '').lower())
    if gate: take(sec['locations'][gate])
    for L in sorted((L for L in locs if L['id'] in by_loc), key=lambda L: (-len(by_loc[L['id']]), 'ML' in L['id'], L['id'])):
        take(L)
    low = lambda L: (L['name'] or '').lower()
    for L in sorted(locs, key=lambda L: (not any(w in low(L) for w in MINING_WORDS), not any(w in low(L) for w in HOSTILE_WORDS),
                                         'ML' in L['id'], L['level'] or 0, L['id'])):
        take(L)

    levels = [c['level'] or 10 for c in chosen]
    tier = 'low' if min(levels) < 12 else 'mid' if min(levels) < 22 else 'high'
    ores = ORES[tier] + ([R('khaitium', 2), R('cymalite', 2)] if owner == 'okkar' else [])   # (Okkar space's own)
    used = {}
    locations = []
    for L in chosen:
        lev = L['level'] or 10
        tech = int(np.clip(round(1 + lev * 9 / 30), 1, 10))
        here = by_loc.get(L['id'], [])
        pid = _nearest_planet(sec, L)
        pl = sec['planets'].get(pid) if pid else None
        ice = pl is not None and 'ice' in pl['material'].lower()
        kind = 'ice' if ice or key == 'S07' else 'rock'
        if here:
            fac = max({d['faction'] for d in here if d['faction'] in FACTION_LOOK} or {owner},
                      key=lambda f: sum(d['faction'] == f for d in here))
            pool, interior = FACTION_LOOK.get(fac, FACTION_LOOK[owner])
            look = pool[used.get(fac, 0) % len(pool)]; used[fac] = used.get(fac, 0) + 1
            asteroids = {'count': 40, 'type': kind, 'ores': ores}
            tech = min(10, tech + 1)
        elif any(w in low(L) for w in HOSTILE_WORDS):
            look, interior, asteroids = 'gof2:station_pirates nodock', FACTION_LOOK[owner][1], False
        else:
            look, interior = None, FACTION_LOOK[owner][1]
            mining = any(w in low(L) for w in MINING_WORDS)
            asteroids = ({'count': 200, 'type': kind, 'spread': 150000, 'ores': ores} if mining
                         else {'count': 60, 'type': kind, 'ores': ores})
        locations.append((L['id'], 'es2_' + _slug(L['name']), look, interior, tech, pid, asteroids))

    songs = []
    p = os.path.join(SRC, f'Audio/MusikSets/DA_MusicSet_Sector_{int(key[1:]):03d}.json')
    if os.path.exists(p):
        for s in json.load(open(p, encoding='utf-8-sig'))[0]['Properties'].get('SongList', []):
            # (a song's _NoBattle variant plays the song's own waves)
            songs.append(s['AssetPathName'].rsplit('.', 1)[-1].replace('DA_', '').replace('_NoBattle', '') + '_1Calm')
    songs = songs or ['LayeredSong_003_1Calm', 'LayeredSong_004_1Calm']
    security = 3 if min(levels) < 10 else 2 if min(levels) < 18 else 1 if min(levels) < 26 else 0
    return {'id': system_id(key), 'race': owner, 'locals': locals_, 'raiders': RAIDERS.get(key, ['outlaw']),
            'security': security, 'gateStation': 'es2_' + _slug(sec['locations'][gate]['name']) if gate else None,
            'spaceMusic': songs[0], 'stationMusic': songs[1 % len(songs)], 'locations': locations}


def spec_of(key):
    s = SECTORS[key] if key in SECTORS else auto_spec(key)
    s = dict(s)
    s['gates'] = [system_id(t) for t in links().get(key, {}).get('to', [])]
    return s


# Where ES2's galaxy lies on GoF2's star map: its sectors' places on ES2's galaxy map (BP_TravelMode_System LocationOnMap:
# X -750 .. 4100, Y -1620 .. 1100) scaled into a cluster past GoF2's edge (GoF2's systems lie at x 15-94, y 2-96, z 10-90;
# x and y are the map's screen axes, z its depth): x from 104, its y centred on GoF2's middle, z GoF2's middle.
GALAXY = {'x0': 104.0, 'x_from': -750.0, 'y_mid': 50.0, 'y_from': -260.0, 'scale': 0.008, 'z': 50}


def galaxy_position(loc):
    """A sector's place on GoF2's star map ([x, y, z]) from its place on ES2's galaxy map."""
    g = GALAXY
    return [int(round(g['x0'] + (loc[0] - g['x_from']) * g['scale'])), int(round(g['y_mid'] + (loc[1] - g['y_from']) * g['scale'])), g['z']]
SKY_W, SKY_H = 8192, 4096
# The game's skies by their sun sprite's colour (reference.md "Skies"): the star map draws a system's sun from its sky
SUN_SKIES = [(0, (0.3, 1.0, 0.35)), (1, (1.0, 0.55, 0.2)), (3, (1.0, 0.3, 0.9)), (5, (1.0, 0.25, 0.15)), (7, (1.0, 0.9, 0.45)),
             (8, (0.4, 0.8, 1.0)), (9, (1.0, 1.0, 1.0)), (10, (0.3, 0.4, 1.0))]


def map_sky(sun):
    c = np.array(sun, np.float64); c = c / max(c.max(), 1e-6)
    return min(SUN_SKIES, key=lambda s: float(np.sum((np.array(s[1]) - c) ** 2)))[0]
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


_planet_types = None
def planet_types():
    """DT_PlanetData: {EPlanetTypes value: {'material', 'atmosphere', 'surface'}} (a travel map's planet that names only its
    Type takes its material and colours from here)."""
    global _planet_types
    if _planet_types is None:
        _planet_types = {}
        p = os.path.join(SRC, 'Blueprints/Environment/Planets/DT_PlanetData.json')
        if os.path.exists(p):
            for r in json.load(open(p, encoding='utf-8-sig'))[0].get('Rows', {}).values():
                g = lambda pre: next((v for k, v in r.items() if k.startswith(pre)), None)
                ty, mat, atm, sur = g('Type'), g('Material'), g('AtmosphereColor'), g('SurfaceAverageColor')
                if not ty: continue
                _planet_types[ty] = {
                    'material': mat.get('ObjectName', "''").split("'")[1] if isinstance(mat, dict) else '',
                    'atmosphere': [atm['R'], atm['G'], atm['B']] if atm else None,
                    # (white = "its texture's own colours", which the colouring code doesn't want as a tint)
                    'surface': [sur['R'], sur['G'], sur['B']] if sur and min(sur['R'], sur['G'], sur['B']) < 0.99 else None}
    return _planet_types


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
            out['galaxy'] = _vec(p['SystemData'].get('LocationOnMap'))
            c = p.get('SystemColor'); out['colour'] = [c['R'], c['G'], c['B']] if c else out['colour']
        elif t == 'BP_TravelMode_Sun_C':
            c = p.get('Color'); out['sun'] = [c['R'], c['G'], c['B']] if c else out['sun']
        elif t == 'BP_TravelMode_Planet_C':
            pd = p.get('PlanetData') or {}
            mat = next((v for k, v in pd.items() if k.startswith('Material')), None)
            atm = next((v for k, v in pd.items() if k.startswith('AtmosphereColor')), None)
            sur = next((v for k, v in pd.items() if k.startswith('SurfaceAverageColor')), None)
            key = p.get('ID') or e['Name']
            # a planet naming only its Type takes the type's material and colours (DT_PlanetData)
            ty = planet_types().get(next((v for k, v in pd.items() if k.startswith('Type')), None)) or {}
            if not mat and ty.get('material'): mat = {'ObjectName': f"MaterialInstanceConstant'{ty['material']}'"}
            if not atm and ty.get('atmosphere'): atm = dict(zip('RGB', ty['atmosphere']))
            if not sur and ty.get('surface'): sur = dict(zip('RGB', ty['surface']))
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
                'map': _vec(L.get('LocationOnMap')), 'level': L.get('StaticLevel'), 'objects': objs,
                'type': (L.get('LocationType') or '').split('::')[-1], 'security': bool(L.get('Security')),
                'hidden': bool(L.get('bNeverShowIngame')),
                # its jumpgates / wormholes: [(kind, [location ids])]
                'links': [(c.get('ConnectionType', '').split('::')[-1], list(c.get('LocationIDs') or []))
                          for c in L.get('Connections') or []]}
    # the moons have no ID: they are known by their actor name; their place in the locations' objects is by distance
    return out


# (BP_FrostField / BP_CorrosionField too: the remake's frost and corrosion kinds with ES2's own buildup, freeze and ticks;
# BP_DamageField left out: each is a child of a burning mining prop, BP_Mining_Fire_001, which the mod doesn't place)
HAZARD_CLASSES = {'BP_HeatDamageVolume_C': 'heat', 'BP_RadiationField_C': 'radiation', 'BP_FrostField_C': 'frost',
                  'BP_CorrosionField_C': 'corrosion'}
HAZARD_RADIUS = {'heat': 10000.0, 'radiation': 15000.0, 'frost': 70000.0, 'corrosion': 4000.0}   # (cm: the blueprints' spheres)
HEAT_DPS = 200.0        # BP_HeatDamageVolume's DamagePerSecondMax (an actor may set its own): GetScaledDamage by level, as
ES2_RAIDER_DPS = 55.0   # its NPCs' DPS are: the Outlaw raider's 31 + 24 (npc_leveling.csv); the remake's "raiderDps"
HAZARD_CLEAR = 10000    # game units (500 m) a volume's edge stays from the orbit's centre, where the station and arrivals are
MAX_HAZARDS = 12


_levels = {}
def _level(es2_id):
    """An ES2 location's actors (Maps/Locations/<id>.json; tens of MB: the last few kept), [] when it has none."""
    key = (SRC, es2_id)
    with jobs.once(('level',) + key):
        if key not in _levels:
            path = os.path.join(SRC, 'Maps', 'Locations', es2_id + '.json')
            if len(_levels) >= 2: _levels.pop(next(iter(_levels)))
            _levels[key] = json.load(open(path, encoding='utf-8-sig')) if os.path.exists(path) else []
    return _levels[key]


def level_hazards(es2_id):
    """An ES2 location's heat volumes, radiation, frost and corrosion fields (Maps/Locations/<id>.json) as the remake's orbit "hazards":
    their place (ES2 cm -> game units, 1 m = 20) and sphere radius x scale, the nearest MAX_HAZARDS whose edge stays
    HAZARD_CLEAR from the orbit's centre."""
    d = _level(es2_id)
    if not d: return []
    def at(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return d[i].get('Properties', {}) if 0 <= i < len(d) else {}
    out = []
    for o in d:
        kind = HAZARD_CLASSES.get(o.get('Type'))
        if not kind: continue
        p = o.get('Properties', {})
        root, sph = at(p.get('RootComponent')), at(p.get('Sphere'))
        loc = _vec(root.get('RelativeLocation'))
        sc = root.get('RelativeScale3D') or {}
        scale = max(abs(sc.get('X', 1.0)), abs(sc.get('Y', 1.0)), abs(sc.get('Z', 1.0))) if sc else 1.0
        radius = float(sph.get('SphereRadius', p.get('Radius', HAZARD_RADIUS[kind]))) * scale * 0.2
        g = to_game(loc) * 0.2
        radius = max(1000.0, radius)
        if np.linalg.norm(g) - radius < HAZARD_CLEAR: continue
        h = {'kind': kind, 'centre': [round(float(x)) for x in g], 'radius': round(radius)}
        if kind == 'heat': h['raiderDps'] = round(float(p.get('DamagePerSecondMax', HEAT_DPS)) / ES2_RAIDER_DPS, 2)
        out.append(h)
    out.sort(key=lambda h: np.linalg.norm(h['centre']))
    return out[:MAX_HAZARDS]


# ES2's minefields (BP_Minefield_*: Radius 25 000 cm, AverageMineDistance 12 000 cm, MaxMineAmount 40 over the blueprint's)
# as the remake's orbit "minefields": the actor's place, its radius (cm -> game units x the ES2 ships' 3.6, as the remake's mine
# trigger and blast: else ES2's 120 m spacing against its 100 m trigger becomes 120 m against 360 m and a field goes off at
# once), its kind by class, and as many mines
# as fit the sphere at that spacing (4/3 pi (Radius / AverageMineDistance)^3, 38 for the defaults), 3 to MaxMineAmount.
# The remake lays them only in risky or dangerous systems for a pilot of rank 4 or more, on half the visits (its defaults).
# 90 actors in 30 locations: Corrosion 48, Web 19, Thermal 13, Cryo 10.
MINEFIELD_CLASSES = {'BP_Minefield_C': 'kinetic', 'BP_Minefield_Base_C': 'kinetic', 'BP_Minefield_BiggerRadius_C': 'kinetic',
                     'BP_Minefield_Web_C': 'web', 'BP_Minefield_Cryo_C': 'cryo', 'BP_Minefield_Thermal_C': 'thermal',
                     'BP_Minefield_Corrosion_C': 'corrosion'}
MINEFIELD_DEFAULTS = {'Radius': 25000.0, 'AverageMineDistance': 12000.0, 'MaxMineAmount': 40}
MAX_MINEFIELDS = 6
ES2_SHIP_SCALE = 3.6   # the remake's ES2 numbers' scale (its mines' trigger / blast, interaction ranges)


def minefield_count(radius_cm, spacing_cm, most):
    """The mines a field holds: its sphere's volume over a cube of their spacing, 3 to 'most'."""
    n = 4.0 / 3.0 * math.pi * (radius_cm / max(1.0, spacing_cm)) ** 3
    return int(max(3, min(most, round(n))))


def level_minefields(es2_id):
    """An ES2 location's minefields as the remake's orbit "minefields", the nearest MAX_MINEFIELDS whose edge stays HAZARD_CLEAR
    from the orbit's centre ([] on a planet-side level)."""
    if re.search(r'L\d\dP', es2_id): return []
    d = _level(es2_id)
    out = []
    for o in d or []:
        kind = MINEFIELD_CLASSES.get(o.get('Type'))
        if not kind: continue
        p = dict(MINEFIELD_DEFAULTS, **{k: v for k, v in o.get('Properties', {}).items() if k in MINEFIELD_DEFAULTS})
        m = re.search(r'\.(\d+)$', (o.get('Properties', {}).get('RootComponent') or {}).get('ObjectPath', ''))
        root = d[int(m.group(1))].get('Properties', {}) if m and int(m.group(1)) < len(d) else {}
        g = to_game(_vec(root.get('RelativeLocation'))) * 0.2
        radius = max(500.0, float(p['Radius']) * 0.2 * ES2_SHIP_SCALE)
        if np.linalg.norm(g) - radius < HAZARD_CLEAR: continue
        out.append({'kind': kind, 'centre': [round(float(x)) for x in g], 'radius': round(radius),
                    'count': minefield_count(float(p['Radius']), float(p['AverageMineDistance']), int(p['MaxMineAmount']))})
    out.sort(key=lambda f: np.linalg.norm(f['centre']))
    return out[:MAX_MINEFIELDS]


# ES2's lightning storms (BP_LightningField: AttachToCamera, a storm round the camera wherever it is in the location) as the
# remake's orbit "storm" with the actor's own Frequency / Radius (cm -> game units) / HeightPercent / LightningScale /
# LightningIntensity / ThunderSoundSpawnChance over the blueprint's; its thunder S_SC_Thunder's seven waves, the mod's
# sounds es2_thunder_00N (write_thunder). 6 locations (S02L11, S03L04...); the planet-side ones left out.
STORM_DEFAULTS = {'Frequency': 1.0, 'Radius': 400000.0, 'HeightPercent': 1.0, 'LightningScale': 1.0, 'LightningIntensity': 1.0,
                  'ThunderSoundSpawnChance': 0.2}
THUNDER_WAVES = [f'S_Thunder_00{i}' for i in range(1, 8)]


def thunder_sound(wave): return 'es2_thunder_' + wave[-3:]


def level_storm(es2_id):
    """An ES2 location's lightning field as the remake's orbit "storm", None without one (or on a planet-side level)."""
    if re.search(r'L\d\dP', es2_id): return None
    for o in _level(es2_id) or []:
        if o.get('Type') != 'BP_LightningField_C': continue
        p = dict(STORM_DEFAULTS, **{k: v for k, v in o.get('Properties', {}).items() if k in STORM_DEFAULTS})
        return {'frequency': round(float(p['Frequency']), 3), 'radius': round(float(p['Radius']) * 0.2),
                'heightPercent': round(float(p['HeightPercent']), 3), 'scale': round(float(p['LightningScale']), 3),
                'intensity': round(float(p['LightningIntensity']), 3), 'thunderChance': round(float(p['ThunderSoundSpawnChance']), 3),
                'thunder': [thunder_sound(w) for w in THUNDER_WAVES]}
    return None


def write_thunder(stations):
    """The thunder waves into the mod's sounds when an orbit has a storm; the storms' thunder dropped if they can't be."""
    import audio
    storms = [st['orbit']['storm'] for st in stations if st.get('orbit', {}).get('storm')]
    if not storms: return 0
    written = set()
    if audio.available():
        waves, tmp = audio.decode(THUNDER_WAVES)
        for w in THUNDER_WAVES:
            if w in waves: audio.write(waves[w], f'sounds/{thunder_sound(w)}'); written.add(thunder_sound(w))
        import shutil; shutil.rmtree(tmp, ignore_errors=True)
    for s in storms:
        s['thunder'] = [t for t in s.get('thunder', []) if t in written]
        if not s['thunder']: s.pop('thunder', None)
    return len(written)


# The secure containers' puzzle sounds (the remake's orbit containers "sounds", World.PuzzleSounds): the waves of ES2's grab
# cues (BP_Portable_Component: S_SC_Grab_Hold / _Hold_Loop / _Leggo / _Throw), the orb dispenser's loop, the conductor beam
# and the armoured container opening, as the mod's sounds es2_puzzle_<role>, named on every orbit with secure containers.
PUZZLE_SOUNDS = {'grab': 'S_Grab_Hold_001', 'hold': 'S_Grab_Hold_Loop_001', 'drop': 'S_Grab_Leggo_002', 'throw': 'S_Grab_Throw_001',
                 'dispenser': 'S_OrbDispenser_Loop_001', 'conductor': 'S_3D_ConductorBeam_Loop', 'unlock': 'S_Container_Armored'}


def write_puzzle_sounds(stations):
    """The puzzle sounds into the mod's sounds when an orbit has secure containers, and their names on those orbits."""
    import audio
    orbits = [st['orbit']['containers'] for st in stations
              if isinstance(st.get('orbit', {}).get('containers'), dict) and st['orbit']['containers'].get('secure')]
    if not orbits or not audio.available(): return 0
    waves, tmp = audio.decode(list(PUZZLE_SOUNDS.values()))
    written = {}
    try:
        for role, wave in PUZZLE_SOUNDS.items():
            if wave in waves and audio.write(waves[wave], f'sounds/es2_puzzle_{role}'): written[role] = f'es2_puzzle_{role}'
    finally:
        import shutil; shutil.rmtree(tmp, ignore_errors=True)
    for ct in orbits:
        if written: ct['sounds'] = dict(written)
    return len(written)


# ES2's ambience zones in space (BP_MusicTrigger's OverrideAmbience, its InnerSphereRadius): the four sets its location
# levels place round stations, factories, cargo wrecks and wreck fields, as the remake's orbit "ambience" (the loops as the
# mod's music tracks, music/es2amb_<wave>: about a minute each, kept compressed; the adds its sounds, sounds/es2amb_<wave>). Their cues (Audio/SFX/Ambience/<set>/S_SC_*): the loops a SoundNodeRandom picks
# from, the adds a SoundNodeDelay (DelayMin..Max) over a SoundNodeRandom mixes in at its InputVolume. ES2's planet-side
# ambiences (deserts, snow, lava, caves) are left out: GoF2 never lands, and ES2 plays them on planets only.
AMBIENCE = {
    'S_SC_Outlaw_Station': {'loops': ['S_Outlaw_Station_001', 'S_Outlaw_Station_002', 'S_Outlaw_Station_003'], 'volume': 0.85},
    'S_SC_Ambience_Factory': {'loops': ['S_Ambience_Factory_003', 'S_Ambience_Factory_004', 'S_Ambience_Factory_005',
                                        'S_Ambience_Factory_007b'],
                              'adds': [f'S_Factory_Ambience_Add_{i:02d}' for i in range(1, 11)], 'addVolume': 0.1,
                              'addEveryMs': [4000, 10000]},
    'S_SC_Cargo_Wreck_Ambience': {'loops': ['S_Cargo_Wreck_Ambience_001'],
                                  'adds': [f'S_Cargo_Wreck_Ambience_Add_{i:03d}' for i in range(1, 9)], 'addVolume': 0.3,
                                  'addEveryMs': [8000, 15000]},
    'S_SC_WreckField_Loop': {'loops': ['S_WreckField_001'], 'volume': 1.0},   # (its cue's 1.5: the remake's at most 1)
}
AMBIENCE_GAIN = 0.6   # x the cues' volumes: ES2's beds under the remake's music and sound effects
MAX_AMBIENCE = 6


def ambience_sound(wave): return 'es2amb_' + wave[2:].lower()


def level_ambience(es2_id):
    """An ES2 location's ambience zones in space as the remake's orbit "ambience" (the nearest MAX_AMBIENCE): each its set's
    loops and adds (as the mod's sound names), volumes, its place (ES2 cm -> game units) and inner radius x scale."""
    d = _level(es2_id)
    if not d: return []
    def at(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return d[i].get('Properties', {}) if 0 <= i < len(d) else {}
    out = []
    for o in d:
        if o.get('Type') != 'BP_MusicTrigger_C': continue
        p = o.get('Properties', {})
        m = re.search(r"'(\w+)'", (p.get('OverrideAmbience') or {}).get('ObjectName', ''))
        spec = AMBIENCE.get(m.group(1)) if m else None
        if not spec: continue
        root = at(p.get('RootComponent'))
        sc = root.get('RelativeScale3D') or {}
        scale = max(abs(sc.get('X', 1.0)), abs(sc.get('Y', 1.0)), abs(sc.get('Z', 1.0))) if sc else 1.0
        z = {'loops': [ambience_sound(w) for w in spec['loops']], 'volume': round(spec.get('volume', 1.0) * AMBIENCE_GAIN, 2),
             'centre': [round(float(x)) for x in to_game(_vec(root.get('RelativeLocation'))) * 0.2],
             'radius': round(max(1000.0, float(p.get('InnerSphereRadius', 50000.0)) * scale * 0.2))}
        if spec.get('adds'):
            z['adds'] = [ambience_sound(w) for w in spec['adds']]
            z['addVolume'] = round(spec['addVolume'] * AMBIENCE_GAIN, 2)
            z['addEveryMs'] = spec['addEveryMs']
        out.append(z)
    out.sort(key=lambda z: np.linalg.norm(z['centre']))
    return out[:MAX_AMBIENCE]


def write_ambience(stations):
    """The ambience waves the orbits use, into the mod's sounds; the orbits' zones whose loops couldn't be written dropped."""
    import audio
    loops = {w for spec in AMBIENCE.values() for w in spec['loops']}
    used = sorted({w for spec in AMBIENCE.values() for w in spec['loops'] + spec.get('adds', [])
                   if any(ambience_sound(w) in z['loops'] + z.get('adds', []) for st in stations for z in st.get('orbit', {}).get('ambience', []))})
    written = set()
    if used and audio.available():
        waves, tmp = audio.decode(used)
        for w in used:
            if w in waves:
                audio.write(waves[w], f'{"music" if w in loops else "sounds"}/{ambience_sound(w)}'); written.add(ambience_sound(w))
        import shutil; shutil.rmtree(tmp, ignore_errors=True)
    zones = 0
    for st in stations:
        orbit = st.get('orbit', {})
        if 'ambience' not in orbit: continue
        keep = []
        for z in orbit['ambience']:
            z['loops'] = [s for s in z['loops'] if s in written]
            if 'adds' in z: z['adds'] = [s for s in z['adds'] if s in written]
            if z['loops']: keep.append(z)
        if keep: orbit['ambience'] = keep; zones += len(keep)
        else: del orbit['ambience']
    return zones, len(written)


# Who flies where (DataFiles/location_spawns.CSV: a location's weight for each faction's ships, besides its cargo ships,
# capital ships, creatures and resources): the factions with a weight as the orbit's own "locals" (the friendly ones,
# heaviest first) and "raiders" (the hostile ones, factions.py's flag), beating its system's there. Only who, not how many:
# GoF2's own counts and raider chances stay (ES2's spawn counts and levels would change its difficulty).
SPAWN_FACTIONS = {'gb': 'gb', 'okkar': 'okkar', 'outlaw': 'outlaw', 'outlaw_bloodstar': 'outlaw', 'zurilia': 'zurilia',
                  'retaliators': 'retaliators', 'coalition': 'coalition', 'freelancer': 'freelancer', 'cultist': 'cultist',
                  'okkar_radicals': 'okkar_prime', 'ancient_swarmers': 'ancient', 'okkar_wota_dlc': 'okkar',
                  'okkar_radicals_wota_dlc': 'okkar_prime'}
_spawns = None


def orbit_spawns(es2_id):
    """(locals, raiders) of an ES2 location from location_spawns.CSV, the mod's faction ids heaviest first; ([], []) without."""
    global _spawns
    if _spawns is None:
        import es2data, factions
        _spawns = {}
        rows = es2data.rows('location_spawns.CSV')
        head = [c.strip() for c in rows[0]] if rows else []
        hostile = {v[0]: v[3] for v in factions.FACTIONS.values()}
        for r in rows[1:]:
            if not r or not r[0].strip(): continue
            weight = {}
            for j, col in enumerate(head):
                f = SPAWN_FACTIONS.get(col)
                w = es2data.number(r[j]) if f and j < len(r) else None
                if w: weight[f] = weight.get(f, 0.0) + w
            order = sorted(weight, key=lambda f: -weight[f])
            _spawns[r[0].strip()] = ([f for f in order if not hostile.get(f)], [f for f in order if hostile.get(f)])
    return _spawns.get(es2_id, ([], []))


# ES2's unique loot (DataFiles/unique_loot.csv: a location's fixed loot, mostly a rarity of random gear, which GoF2 has no
# roll for, but also named items and resources with amounts) as the remake's orbit "containers.loot": each found once a game.
# Only the named items and resources the mod has (resolve_container_loot, once every item is made): ES2's rare resources,
# its components, devices and weapons by their ids, its crafting goods; its personal items, logbooks, augment parts and ship
# module blueprints (no GoF2 counterpart) left out.
SKIP_UNIQUE = ('personal_item', 'generic_logbook', 'augment_part', 'blueprint_ship_module', 'credits', 'device_reset_item')
_unique = None


def orbit_unique_loot(es2_id):
    """An ES2 location's named loot: [{'_ids': candidate item ids, 'amount'}] (resolve_container_loot picks the mod's)."""
    global _unique
    if _unique is None:
        import es2data
        _unique, where = {}, None
        for r in es2data.rows('unique_loot.csv'):
            r = r + [''] * 20
            if r[1].strip(): where = r[1].strip()
            for item, amount in ((r[3].strip(), 1), (r[8].strip(), es2data.number(r[10]) or 1)):
                if not item or not where or item.startswith(SKIP_UNIQUE): continue
                ids = [item, 'es2_' + item]
                ref = drop_ref(item)
                if ref: ids.insert(0, ref.split(':', 1)[1])
                _unique.setdefault(where, []).append({'_ids': ids, 'amount': max(1, int(round(amount)))})
    return [dict(e) for e in _unique.get(es2_id, [])]


def resolve_container_loot(stations, item_ids, log=print):
    """The orbits' containers.loot to the mod's item references ('item_ids' every item the mod has); unknown ones dropped."""
    kept = dropped = 0
    for st in stations:
        ct = st.get('orbit', {}).get('containers')
        if not isinstance(ct, dict) or 'loot' not in ct: continue
        out = []
        for e in ct['loot']:
            iid = next((i for i in e.get('_ids', []) if i in item_ids), None)
            if iid: out.append({'item': f'es2_ships:{iid}', 'amount': e['amount']}); kept += 1
            else: dropped += 1
        if out: ct['loot'] = out
        else: del ct['loot']
    log(f'  unique loot: {kept} items in the orbits\' containers ({dropped} the mod has no item for)')


# ES2's item containers' own models (BP_ItemContainer: SK_Container_Generic_002, the armoured BP_ItemContainer_Armored:
# SK_Container_Generic_004; tools/container_assets.txt exports them) as the orbits' containers' "model" / "bulletproofModel"
# with their ES2 materials (warships.py's, as its props are made), drawn as big as the race's container. Without the meshes
# in the export the containers keep the race's container.
CONTAINER_MESHES = {'model': 'SK_Container_Generic_002', 'bulletproofModel': 'SK_Container_Generic_004'}
_container_models = False


def container_models():
    """{"model", "bulletproofModel", "materials"} for the orbits' containers (made once), None without the meshes."""
    global _container_models
    if _container_models is not False: return _container_models
    import warships
    if warships.SRC is None: warships.configure(SRC, MOD, LOG)
    out, materials = {}, []
    for field, mesh in CONTAINER_MESHES.items():
        path = os.path.join(SRC, 'Assets/Environment/Props/Meshes', mesh + '.glb')
        if not os.path.exists(path): continue
        prims = warships.read_prims(path)
        mn, mx = warships.bounds(prims)
        used = {}
        prefix = f'es2_{field.lower()}_'
        rel = f'containers/{mesh.lower()}.glb'
        warships.write_glb(rel, warships.split_prims(prefix, prims, used), (mn + mx) / 2)
        out[field] = rel
        materials += warships.material_entries(prefix, used)
    _container_models = dict(out, materials=materials) if out else None
    if not out: LOG('  containers: their meshes aren\'t in the export (tools/container_assets.txt): the race\'s container')
    return _container_models


# ES2's own asteroids (Assets/Environment/Asteroids/Meshes; tools/asteroid_assets.txt exports them) as the orbits'
# asteroids' "models" with their materials (warships.py's, as the props are made): the rock orbits its jagged rocks
# (MI_Asteroid_Rock_Seamless_Jagged: T_Rocks_005_C on T_Quixel_Rock_017_N, es2mat reads it) and its generic rocks, the ice
# orbits its generic ices. The generic rocks' and ices' masters (M_Asteroid_Rock_Parent, M_Asteroid_Ice_Parent) have no
# colour map: their compiled base-pass pixel shaders (es2_re astmat, ShaderDump + disasm) take the colour from
# MPC_Asteroids (RockColor / IceColor, which no level changes) and shade it by the mesh's curvature map, so it is baked
# here (rock_maps, ice_maps). Mining stays GoF2's.
ASTEROID_MESHES = {'rock': ['SM_Asteroid_Rock_Jagged_001', 'SM_Asteroid_Rock_Jagged_002', 'SM_Asteroid_Rock_Jagged_003',
                            'SM_Asteroid_Rock_Jagged_004', 'SM_Asteroid_Rock_Jagged_005',
                            'SM_Asteroid_Rock_Generic_Small_001', 'SM_Asteroid_Rock_Generic_Small_002',
                            'SM_Asteroid_Rock_Generic_Small_003', 'SM_Asteroid_Rock_Generic_Medium_001',
                            'SM_Asteroid_Rock_Generic_Medium_002'],
                   'ice': ['SM_Asteroid_Ice_Generic_Small_001', 'SM_Asteroid_Ice_Generic_Small_002',
                           'SM_Asteroid_Ice_Generic_Medium_001', 'SM_Asteroid_Ice_Generic_Medium_002']}
ROCK_COLOR = [0.4, 0.394272, 0.37708]   # MPC_Asteroids RockColor / IceColor (linear)
ICE_COLOR = [0.395832, 0.762062, 1.0]
ASTEROID_MAP_SIZE = 1024
_asteroid_models = {}


def _srgb(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.round(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255).astype(np.uint8)


def _overlay(base, blend):
    """UE's BlendOverlay(base, blend), the masters' colour over their curvature."""
    return np.where(base >= 0.5, 1 - 2 * (1 - base) * (1 - blend), 2 * base * blend)


def _contrast(x, k):
    """The masters' contrast curve (their shaders' S-curve): 0.5 (2x)^k below a half, 1 - 0.5 (2 - 2x)^k above."""
    a = np.clip(2 * x, 0, 1)
    lo = 0.5 * a ** k
    hi = 1 - np.clip(1 - 2 * (x - 0.5), 0, 1) ** k
    return np.where(hi > 0, 0.5 + 0.5 * hi, lo)


def _map(name, size):
    """A map's channels as floats (0-1) at size x size, None without it."""
    import warships
    a = warships._img(name)
    if a is None: return None
    if a.shape[0] != size: a = np.array(Image.fromarray(a).resize((size, size), Image.LANCZOS))
    return a.astype(np.float32) / 255


def rock_maps(mi):
    """(colour, metallicSmoothness) maps of a generic rock (MI_Asteroid_Rock_Generic_*: M_Asteroid_Rock_Parent's base-pass
    pixel shader with its parameters, which every generic rock keeps): its AO_CRV_R map's curvature (G) overlaid by the
    Quixel cavity (T_Quixel_Rock_022_C_R_H R, at the UV x DetailTiling 2), through the contrast curve (CurvatureContrast 0.5)
    to the power CurvatureStrength 1.5; RockColor overlaid on it, to the power of the colour variation's exponent (2 - the
    world-space noise: 1.5, its middle); the roughness BaseRoughness 0.7 overlaid on the map's B (0.4 + 0.6 B). The rim
    light (view-dependent) left out."""
    import warships
    t = 'T_' + mi[3:]
    s = ASTEROID_MAP_SIZE
    m = _map(t + '_AO_CRV_R', s)
    q = _map('T_Quixel_Rock_022_C_R_H', s // 2)
    if m is None or q is None: return None
    cav = np.tile(q[..., 0], (2, 2))
    c = _contrast(_overlay(m[..., 1], cav), 0.5) ** 1.5
    col = _overlay(np.array(ROCK_COLOR, np.float32), c[..., None]) ** 1.5
    rough = 0.4 + 0.6 * m[..., 2]
    ms = np.zeros((s, s, 4), np.uint8); ms[..., 3] = np.round((1 - rough) * 255)
    return (warships._save(_srgb(col), f'asteroids/maps/{t}_c.png', s), warships._save(ms, f'asteroids/maps/{t}_ms.png', s))


def ice_maps(mi):
    """(colour, metallicSmoothness) maps of a generic ice (MI_Asteroid_Ice_Generic_*: M_Asteroid_Ice_Parent's base-pass
    pixel shader with the ices' parameters): IceColor x the per-asteroid variation (0.2-1 by ColorVariationAmount 0.8: 0.6,
    its middle), overlaid on the C_R_TH map's curvature (R ^ CurvatureExponent 1, through the contrast curve 2), times the
    noise (T_Noise_014_M at the UV x 2, its square root through the contrast curve 2, by Param_2 0.7; its parallax left
    out), times (1 - thickness B) ^ ThicknessExponent 1; the roughness the map's G. The fresnel (view-dependent, into the
    subsurface colour) left out."""
    import warships
    t = 'T_' + mi[3:]
    s = ASTEROID_MAP_SIZE
    m = _map(t + '_C_R_TH', s)
    nz = _map('T_Noise_014_M', s // 2)
    if m is None or nz is None: return None
    c = _contrast(m[..., 0], 2.0)
    n = _contrast(np.sqrt(np.tile(nz[..., 0], (2, 2))), 2.0)
    col = _overlay(np.array(ICE_COLOR, np.float32) * 0.6, c[..., None]) * ((n - 1) * 0.7 + 1)[..., None] * (1 - m[..., 2:3])
    ms = np.zeros((s, s, 4), np.uint8); ms[..., 3] = np.round((1 - m[..., 1]) * 255)
    return (warships._save(_srgb(col), f'asteroids/maps/{t}_c.png', s), warships._save(ms, f'asteroids/maps/{t}_ms.png', s))


def asteroid_models(kind):
    """{"models", "materials"} for an orbit's asteroids of 'kind' ('rock' / 'ice'; made once), None without the meshes."""
    if kind in _asteroid_models: return _asteroid_models[kind]
    import warships, es2mat
    if warships.SRC is None: warships.configure(SRC, MOD, LOG)
    plan = es2mat.plan
    baked = {'MI_Asteroid_Rock_Generic': rock_maps, 'MI_Asteroid_Ice_Generic': ice_maps}
    def baked_plan(m):   # (the generic rocks and ices: their normals; the colour and roughness baked below)
        n = (m or {}).get('name') or ''
        if any(n.startswith(k) for k in baked): return {'normal': 'T_' + n[3:] + '_N', 'tint': [1.0, 1.0, 1.0]}
        return plan(m)
    models, materials = [], []
    es2mat.plan = baked_plan
    try:
        for mesh in ASTEROID_MESHES.get(kind, []):
            path = os.path.join(SRC, 'Assets/Environment/Asteroids/Meshes', mesh + '.glb')
            if not os.path.exists(path): continue
            prims = warships.read_prims(path)
            mn, mx = warships.bounds(prims)
            used = {}
            prefix = 'es2_' + mesh.lower().replace('sm_asteroid_', '') + '_'
            rel = f'asteroids/{mesh.lower()}.glb'
            warships.write_glb(rel, warships.split_prims(prefix, prims, used), (mn + mx) / 2)
            models.append(rel)
            for e in warships.material_entries(prefix, used):
                src = es2mat._name(used[e['material']][0])
                bake = next((f for k, f in baked.items() if src.startswith(k)), None)
                maps = bake(src) if bake else None
                if maps:
                    e.update({'diffuse': maps[0], 'metallicSmoothness': maps[1], 'color': [1.0, 1.0, 1.0]})
                    e.pop('metallic', None); e.pop('smoothness', None)
                    if bake is rock_maps:   # (the Quixel detail normal at its tiling, as URP's detail normal)
                        dn = warships.tex('normal', 'T_Quixel_Rock_022_N')
                        if dn: e.update({'detailNormal': dn, 'detailTiling': 2.0})
                materials.append(e)
    finally:
        es2mat.plan = plan
    # (the asteroids' own maps at ASTEROID_MAP_SIZE: a GoF2 asteroid never fills the screen; shared maps untouched)
    from PIL import Image
    jobs.flush()   # (the maps are written in the background)
    for e in materials:
        for v in e.values():
            if not isinstance(v, str) or 'T_Asteroid_' not in v: continue
            f = os.path.join(MOD, v)
            if not os.path.exists(f): continue
            im = Image.open(f)
            if max(im.size) > ASTEROID_MAP_SIZE:
                im.thumbnail((ASTEROID_MAP_SIZE, ASTEROID_MAP_SIZE), Image.LANCZOS)
                im.save(f)
    _asteroid_models[kind] = {'models': models, 'materials': materials} if models else None
    if not models: LOG(f'  asteroids ({kind}): their meshes aren\'t in the export (tools/asteroid_assets.txt): the game\'s')
    return _asteroid_models[kind]


# ES2's wreck fields' hulls (BP_MeshField_Wrecks' SM_Wrecks_*, Assets/Environment/Structures/Meshes; tools/
# wreck_assets.txt exports them) as the orbit "wrecks" "models" with their materials (MI_ShipWrecks_RGB_004, warships.py's
# as the props are made): the field's larger hulls (113-400 m), the largest WRECK_SIZE game units (ES2 cm x 0.2) and the
# others in proportion (the remake keeps them as authored); WRECK_HULKS of them among the wreck containers. With them the
# field's smaller pieces from the same MeshEntries (WRECK_DEBRIS: SM_Wrecks_015-017, 019, 020, 20-60 m, and the
# SM_Ship_Wrecks_Detail plates and struts it lists), so a field is a few big hulls among their debris as ES2's (the remake
# picks among the models evenly).
WRECK_MESHES = ['SM_Wrecks_001', 'SM_Wrecks_003', 'SM_Wrecks_004', 'SM_Wrecks_006', 'SM_Wrecks_008', 'SM_Wrecks_009',
                'SM_Wrecks_010', 'SM_Wrecks_018']
WRECK_DEBRIS = ['SM_Wrecks_015', 'SM_Wrecks_016', 'SM_Wrecks_017', 'SM_Wrecks_019', 'SM_Wrecks_020'] + \
               [f'SM_Ship_Wrecks_Detail_{n:03d}' for n in (3, 4, 5, 7, 9, 10, 11)]
WRECK_SIZE = 9020   # (the largest, SM_Ship_Wrecks_Detail_009's 451 m: every piece at its ES2 size)
WRECK_HULKS = 20
_wreck_models = []


def wreck_models():
    """{"models", "materials"} of the wreck fields' hulls (made once), None without the meshes."""
    if _wreck_models: return _wreck_models[0]
    import warships
    if warships.SRC is None: warships.configure(SRC, MOD, LOG)
    models, materials = [], []
    for mesh in WRECK_MESHES + WRECK_DEBRIS:
        path = os.path.join(SRC, 'Assets/Environment/Structures/Meshes', mesh + '.glb')
        if not os.path.exists(path): continue
        prims = warships.read_prims(path)
        mn, mx = warships.bounds(prims)
        used = {}
        prefix = 'es2_' + mesh.lower().replace('sm_', '') + '_'
        rel = f'wrecks/{mesh.lower()}.glb'
        warships.write_glb(rel, warships.split_prims(prefix, prims, used), (mn + mx) / 2)
        models.append(rel)
        materials += warships.material_entries(prefix, used)
    _wreck_models.append({'models': models, 'materials': materials} if models else None)
    if not models: LOG('  wrecks: their meshes aren\'t in the export (tools/wreck_assets.txt): containers only')
    return _wreck_models[0]


# ES2's plasma fields (BP_PlasmaField: a cloud of plasma to harvest, Radius 20 000-500 000 cm) as the remake's orbit
# "gasClouds": GoF2's own gas clouds at their places (a spectral filter shows them, an ionizing missile bursts them, a plasma
# collector gathers the sparks), in the GoF2 plasma of the location's ES2 level (PLASMA_BY_LEVEL: Green to Red, the deeper
# the rarer). The planet-side levels' (S05L03P, S07L01P...) are left out: GoF2 never lands.
PLASMA_BY_LEVEL = [(10, 201), (18, 202), (26, 203), (99, 204)]   # (below this ES2 level, the GoF2 plasma item)
MAX_GAS_CLOUDS = 8
GAS_CLOUD_RANGE = (25000, 200000)   # game units from the station: GoF2's clouds keep 25 000 off it (Level::createGasClouds)


def level_gas_clouds(es2_id, es2_level):
    """An ES2 location's plasma fields as the remake's orbit "gasClouds" (the nearest MAX_GAS_CLOUDS within GAS_CLOUD_RANGE
    of the station); None without any or on a planet-side level."""
    if re.search(r'L\d\dP', es2_id): return None
    d = _level(es2_id)
    def at(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return d[i].get('Properties', {}) if 0 <= i < len(d) else {}
    places = [to_game(_vec(at(o.get('Properties', {}).get('RootComponent')).get('RelativeLocation'))) * 0.2
              for o in d if o.get('Type') == 'BP_PlasmaField_C']
    places = [g for g in places if GAS_CLOUD_RANGE[0] <= float(np.linalg.norm(g)) <= GAS_CLOUD_RANGE[1]]
    if not places: return None
    places.sort(key=lambda g: float(np.linalg.norm(g)))
    plasma = next(item for top, item in PLASMA_BY_LEVEL if (es2_level or 1) < top)
    return {'plasma': plasma, 'clouds': [[round(float(x)) for x in g] for g in places[:MAX_GAS_CLOUDS]]}


# ES2's item containers (Blueprints/Pickups/BP_ItemContainer*): opened by a hit, unless bulletproof (its ContainerType
# OpenOnInteract) or armoured (OpenOnUnlocked, the conductor puzzle: the remake's bulletproof, opened with the action key).
CONTAINER_CLASSES = {'BP_ItemContainer_C': False, 'BP_ItemContainer_Okkar_C': False,
                     'BP_ItemContainer_Armored_C': True, 'BP_ItemContainer_Armored_Okkar_C': True}
MAX_CONTAINERS = 40


def level_containers(es2_id):
    """An ES2 location's item containers as the remake's orbit "containers": how many (at most MAX_CONTAINERS), their
    mean place (ES2 cm -> game units), the field's spread (twice the farthest from it, 5000..400000) and the bulletproof
    share; None without any."""
    d = _level(es2_id)
    def at(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return d[i].get('Properties', {}) if 0 <= i < len(d) else {}
    places, proof = [], 0
    secure_at = None if re.search(r'L\d\dP', es2_id) else _secure_specs(d)   # (the secure ones, level_secure_containers)
    for oi, o in enumerate(d):
        armoured = CONTAINER_CLASSES.get(o.get('Type'))
        if armoured is None: continue
        p = o.get('Properties', {})
        if armoured and secure_at is not None and oi in secure_at: continue   # (a secure container of its own)
        places.append(to_game(_vec(at(p.get('RootComponent')).get('RelativeLocation'))) * 0.2)
        if armoured or p.get('ContainerType') in ('EContainerType::OpenOnInteract', 'EContainerType::OpenOnUnlocked'): proof += 1
    if not places: return None
    pts = np.array(places)
    centre = pts.mean(axis=0)
    spread = float(np.clip(2 * np.abs(pts - centre).max(), 5000, 400000))
    return {'count': min(len(places), MAX_CONTAINERS), 'centre': [round(float(x)) for x in centre], 'spread': round(spread),
            'bulletproof': round(proof / len(places), 2)}


# ES2's armoured containers (BP_ItemContainer_Armored, OpenOnUnlocked) as the remake's containers "secure": the container's
# place and what unlocks it, by its lists:
#   ShotTriggersRequired       BP_ShotTrigger: its triggers' places in chain order (at most 8), "ordered" when chained
#                              (ShotTriggerChainPreviousOne), "retrigger" when Retriggerable (RegtriggerDelay 3 s)
#   EnergyOrbsRequired         BP_EnergyOrb_Socket: a socket with its dispenser ("orb": the BP_EnergyOrb_Dispenser listing it
#                              in EnergyOrbSocketsConnected, else the nearest one)
#   EnergyCoilSocketsRequired  BP_EnergyCoil_Socket: a socket with a coil ("coil": the nearest loose BP_Portable_EnergyCoil*
#                              not yet given to another socket)
#   ConductorReceiverRequired  BP_Conductor_Receiver*: "conductors" with its receivers and the level's sources, statics
#                              and portables (BP_Conductor_Source* / _Static* / _Portable*, BP_ConductorPortable_Materializing,
#                              the Okkar pipes as statics) on the receivers' layer (ConductorLayer; any when a receiver has
#                              none) within CONDUCTOR_REACH of a receiver, each with its own Conduction Sphere Radius
#                              (cm -> game units, the blueprints' 20 000 / 200 when unset) as [x, y, z, radius]
# Sockets without a dispenser or coil, and conductors without a source in reach, leave the container a plain bulletproof
# one. Planet-side levels left out. 82 trigger-locked, 74 orb-locked, 48 coil-locked and 13 conductor-locked in the survey.
MAX_SECURE = 6
CONDUCTOR_REACH = 200000   # cm
CONDUCTOR_KINDS = (('sources', ('BP_Conductor_Source',)), ('statics', ('BP_Conductor_Static', 'BP_Conductor_Pipe')),
                   ('portables', ('BP_Conductor_Portable', 'BP_ConductorPortable_Materializing')))
SHOT_TRIGGER_CLASSES = ('BP_ShotTrigger_C', 'BP_ShotTrigger_Okkar_Toggle_C')


def conductor_solvable(net):
    """Whether the portables can join every receiver to a source: the fewest portables each gap between fixed nodes needs (a
    chain of hops each within a sphere: the ends' and the portables'), the cheapest route to each receiver within the count."""
    import heapq
    fixed = [(n, True) for n in net.get('sources', [])] + [(n, False) for n in net.get('statics', [])]
    recv = net.get('receivers', [])
    nodes = fixed + [(n, False) for n in recv]
    portables = net.get('portables', [])
    rp = max((p[3] for p in portables), default=0)
    def need(a, b):
        dist = float(np.linalg.norm(np.subtract(a[:3], b[:3])))
        if dist <= max(a[3], b[3]): return 0
        if rp <= 0: return None
        return max(1, math.ceil((dist - max(a[3], rp) - max(b[3], rp)) / rp) + 1)
    cost = [math.inf] * len(nodes)
    heap = []
    for i, (n, src) in enumerate(nodes):
        if src: cost[i] = 0; heapq.heappush(heap, (0, i))
    while heap:
        c, i = heapq.heappop(heap)
        if c > cost[i]: continue
        for j in range(len(nodes)):
            k = need(nodes[i][0], nodes[j][0])
            if k is not None and c + k < cost[j]: cost[j] = c + k; heapq.heappush(heap, (c + k, j))
    return all(cost[len(fixed) + r] <= len(portables) for r in range(len(recv)))


def _secure_specs(d):
    """The level's armoured containers' "secure" specs: {container index: spec}."""
    def idx(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return i if 0 <= i < len(d) else -1
    def obj(ref):
        i = idx(ref)
        return d[i] if i >= 0 else {}
    def place(o):
        return [round(float(x)) for x in to_game(_vec(obj(o.get('Properties', {}).get('RootComponent')).get('Properties', {}).get('RelativeLocation'))) * 0.2]
    def loose(o): return 'AttachParent' not in obj(o.get('Properties', {}).get('RootComponent')).get('Properties', {})
    dispensers = [o for o in d if o.get('Type', '').startswith('BP_EnergyOrb_Dispenser')]
    coils = [o for o in d if o.get('Type', '').startswith('BP_Portable_EnergyCoil') and loose(o)]
    used_coils = set()
    def nearest(at, pool):
        return min(pool, key=lambda o: float(np.linalg.norm(np.subtract(place(o), at))), default=None)
    out = {}
    for ci, o in enumerate(d):
        p = o.get('Properties', {})
        if not CONTAINER_CLASSES.get(o.get('Type')): continue
        spec = {'at': place(o), 'triggers': []}
        refs = [r.get('ObjectPath') for r in p.get('ShotTriggersRequired') or []]
        trig = {r: obj({'ObjectPath': r}) for r in refs}
        trig = {r: t for r, t in trig.items() if t.get('Type') in SHOT_TRIGGER_CLASSES}
        if trig:
            prev = {r: (t.get('Properties', {}).get('ShotTriggerChainPreviousOne') or {}).get('ObjectPath') for r, t in trig.items()}
            order, left = [], list(trig)
            while left:   # (each after the one it names as its previous; the rest as listed)
                nxt = next((r for r in left if prev[r] not in left), left[0])
                order.append(nxt); left.remove(nxt)
            spec['triggers'] = [place(trig[r]) for r in order][:8]
            if any(v in trig for v in prev.values()): spec['ordered'] = True
            retrig = [t.get('Properties', {}) for t in trig.values() if t.get('Properties', {}).get('Retriggerable')]
            if retrig: spec['retrigger'] = round(float(retrig[0].get('RegtriggerDelay', 3.0)), 2)
        sockets = []
        for r in p.get('EnergyOrbsRequired') or []:
            sock = obj(r)
            if not sock: continue
            linked = [x for x in dispensers if any(idx(q) == idx(r) for q in x.get('Properties', {}).get('EnergyOrbSocketsConnected') or [])]
            disp = linked[0] if linked else nearest(place(sock), dispensers)
            if disp is None: sockets = None; break
            sockets.append({'at': place(sock), 'orb': place(disp)})
        for r in (p.get('EnergyCoilSocketsRequired') or []) if sockets is not None else []:
            sock = obj(r)
            if not sock: continue
            coil = nearest(place(sock), [c for c in coils if id(c) not in used_coils])
            if coil is None: sockets = None; break
            used_coils.add(id(coil))
            sockets.append({'at': place(sock), 'coil': place(coil)})
        if sockets is None: continue   # (a socket it can't fill: a plain bulletproof container)
        if sockets: spec['sockets'] = sockets[:4]
        receivers = [obj(r) for r in p.get('ConductorReceiverRequired') or []]
        receivers = [r for r in receivers if r.get('Type', '').startswith('BP_Conductor_Receiver')]
        if receivers:
            layers = {r.get('Properties', {}).get('ConductorLayer') for r in receivers}
            def node(o, default):
                r = o.get('Properties', {}).get('Conduction Sphere Radius')
                return place(o) + [round(float(r if r is not None else default) * 0.2)]
            rx = [np.array(place(r)) for r in receivers]
            net = {'receivers': [node(r, 200.0) for r in receivers]}
            for field, prefixes in CONDUCTOR_KINDS:
                pool = [o2 for o2 in d if o2.get('Type', '').startswith(prefixes) and not o2.get('Type', '').endswith('Component_C')
                        and (None in layers or o2.get('Properties', {}).get('ConductorLayer') in layers)
                        and min(float(np.linalg.norm(np.array(place(o2)) - x)) for x in rx) <= CONDUCTOR_REACH * 0.2]
                net[field] = [node(o2, 20000.0) for o2 in pool][:12]
            if not net['sources'] or not conductor_solvable(net): continue   # (no way to energize it here: a plain bulletproof container)
            spec['conductors'] = {k: v for k, v in net.items() if v}
        if spec['triggers'] or sockets or spec.get('conductors'):
            out[ci] = spec if spec['triggers'] else {k: v for k, v in spec.items() if k != 'triggers'}
    return out


def level_secure_containers(es2_id):
    """An ES2 location's locked armoured containers as the remake's containers "secure", the nearest first."""
    if re.search(r'L\d\dP', es2_id): return []
    out = list(_secure_specs(_level(es2_id) or []).values())
    out.sort(key=lambda s: np.linalg.norm(s['at']))
    return out[:MAX_SECURE]


# ES2's acid pouches (BP_AcidSack_Base and its anemone kind: a stalk holding a BP_AcidSack that spits corrosion every 8-13 s,
# can be pulled off and thrown to burst into corrosion, and grows again) as the remake's orbit "acidSacks": their places
# (the base mesh's, cm -> game units), spread x ES2_SHIP_SCALE about their centre as the remake's corrosion field is (ES2's
# 40 m field x 3.6: at 1:1 the bases' 70 m spacing made the spits one corrosive zone), at most MAX_ACID. 26 bases in 3
# locations (S04L01, S04L04, S08ML04).
ACID_CLASSES = ('BP_AcidSack_Base_C', 'BP_AcidSack_Base_Anemone_C')
MAX_ACID = 30


def level_acid_sacks(es2_id):
    """An ES2 location's acid pouch bases as the remake's orbit "acidSacks" ([] on a planet-side level)."""
    if re.search(r'L\d\dP', es2_id): return []
    d = _level(es2_id)
    out = []
    for o in d or []:
        if o.get('Type') not in ACID_CLASSES: continue
        m = re.search(r'\.(\d+)$', (o.get('Properties', {}).get('RootComponent') or {}).get('ObjectPath', ''))
        root = d[int(m.group(1))].get('Properties', {}) if m and int(m.group(1)) < len(d) else {}
        out.append(to_game(_vec(root.get('RelativeLocation'))) * 0.2)
    if not out: return []
    c = np.mean(out, axis=0)
    return [[round(float(x)) for x in c + (p - c) * ES2_SHIP_SCALE] for p in out][:MAX_ACID]


# ES2's cloaked containers (BP_Activity_InvisibleContainer: a BP_InvisibleItemContainer under the cloak, its marker hidden
# until the ship is within its InteractRadius, a rare container's loot) as the remake's orbit containers "cloaked": their
# places (ES2 cm -> game units), at most MAX_CLOAKED. 29 in 27 locations.
MAX_CLOAKED = 10


def level_cloaked_containers(es2_id):
    """An ES2 location's cloaked containers' places as the remake's containers "cloaked", the nearest first; [] without any
    (or on a planet-side level)."""
    if re.search(r'L\d\dP', es2_id): return []
    d = _level(es2_id)
    out = []
    for o in d or []:
        if o.get('Type') != 'BP_Activity_InvisibleContainer_C': continue
        m = re.search(r'\.(\d+)$', (o.get('Properties', {}).get('RootComponent') or {}).get('ObjectPath', ''))
        root = d[int(m.group(1))].get('Properties', {}) if m and int(m.group(1)) < len(d) else {}
        out.append([round(float(x)) for x in to_game(_vec(root.get('RelativeLocation'))) * 0.2])
    out.sort(key=lambda p: np.linalg.norm(p))
    return out[:MAX_CLOAKED]


# ES2's spline traffic (Blueprints/Environment/BP_SplineTraffic*): its ships' lanes; the worker drones' small loops around
# station parts and the industrial ground vehicles are left out. Their class defaults (BP_SplineTraffic: Count 10, BaseSpeed
# 8000 cm/s, ClosedLoop, TwoLanes; the Industrial one open), an actor's own values winning.
LANE_CLASSES = {'BP_SplineTraffic_C': True, 'BP_SplineTraffic_Okkar_C': True, 'BP_SplineTraffic_Settler_C': True}
MAX_LANES = 12


def _rotator(r):
    """An Unreal FRotator (degrees) as a 3x3 matrix acting on (X, Y, Z) column vectors (FRotationMatrix)."""
    p, y, rl = (math.radians((r or {}).get(k, 0.0)) for k in ('Pitch', 'Yaw', 'Roll'))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(rl), math.cos(rl)
    x = [cp * cy, cp * sy, sp]
    yv = [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp]
    z = [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]
    return np.array([x, yv, z], np.float64).T


def level_lanes(es2_id):
    """An ES2 location's ship traffic lanes as the remake's orbit "lanes": each spline's points placed by its actor (ES2 cm
    -> game units), its unit count, speed (m/s) and loop; at most MAX_LANES, the nearest first."""
    d = _level(es2_id)
    def at(ref):
        m = re.search(r'\.(\d+)$', (ref or {}).get('ObjectPath', ''))
        i = int(m.group(1)) if m else -1
        return d[i].get('Properties', {}) if 0 <= i < len(d) else {}
    out = []
    for o in d:
        if not LANE_CLASSES.get(o.get('Type')): continue
        p = o.get('Properties', {})
        root, spl = at(p.get('RootComponent')), at(p.get('Spline'))
        pts = (((spl.get('SplineCurves') or {}).get('position') or {}).get('Points')) or []
        if len(pts) < 2: continue
        sc = root.get('RelativeScale3D') or {}
        scale = np.array([sc.get('X', 1.0), sc.get('Y', 1.0), sc.get('Z', 1.0)], np.float64)
        rot, loc = _rotator(root.get('RelativeRotation')), _vec(root.get('RelativeLocation'))
        world = [loc + rot @ (scale * _vec(q.get('OutVal'))) for q in pts]
        n = p.get('OverrideCount', -1)
        lane = {'points': [[round(float(x)) for x in to_game(w) * 0.2] for w in world],
                'count': int(max(1, min(40, n if isinstance(n, int) and n >= 0 else p.get('Count', 10)))),
                'speed': round(8000.0 * float(p.get('SpeedFactor', 1.0)) / 100.0, 1)}
        if p.get('ClosedLoop', True) is False or len(pts) < 3: lane['loop'] = False
        if p.get('TwoLanes', True) is False: lane['twoLanes'] = False
        out.append(lane)
    out.sort(key=lambda l: float(np.linalg.norm(np.mean(l['points'], axis=0))))
    return out[:MAX_LANES]


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
    elif 'volcanic' in mat:
        # dark rock (its height, blue) cracked by lava (the mask's green) in a molten orange
        t = _sample(_texture(PLANET_TEX + 'T_Planet_Volcanic_001_M.png', 2048), u, v)
        base = sur * 0.6 if pl['surface'] else np.array([0.22, 0.18, 0.16], np.float32)
        col = _ramp(t[..., 2] * 0.7 + t[..., 0] * 0.3, [(0.0, base * 0.25), (0.6, base * 0.7), (1.0, np.minimum(base * 1.2, 1.0))])
        lava = np.clip((t[..., 1] - 0.35) * 2.2, 0.0, 1.0)[..., None]
        col = col * (1 - lava) + np.array([1.0, 0.42, 0.1], np.float32) * lava
    elif 'ice' in mat:
        # pale ice in the planet's own colour, its craters and ridges shaded
        t = _sample(_texture(PLANET_TEX + 'T_Planet_Craters_001_H_C_R.png', 2048), u, v)
        base = np.minimum(np.array(pl['surface'] or pl['atmosphere'], np.float32) * 0.5 + 0.5, 1.0)
        col = _ramp(t[..., 1] * 0.5 + t[..., 0] * 0.5, [(0.0, base * 0.45), (0.55, base * 0.8), (1.0, base)])
    elif 'okkar' in mat:
        # an Okkar world: desert rock with the lights of its cities (the city mask's lines)
        t = _sample(_texture(PLANET_TEX + 'T_Planet_Rock_001_H_C_R.png', 2048), u, v)
        col = _ramp(t[..., 1] * 0.7 + t[..., 0] * 0.3, [(0.0, sur * 0.3), (0.5, sur * 0.65), (1.0, np.minimum(sur * 1.05, 1.0))])
        city = _sample(_texture(PLANET_TEX + 'T_Planet_City_Okkar_001_M.png', 2048), u * 2, v * 2)
        lit = (city[..., 2] * np.clip(city[..., 1] * 1.5, 0, 1))[..., None]
        col = col * (1 - lit * 0.6) + np.array([0.55, 1.0, 0.75], np.float32) * lit * 0.6
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


# ES2's planet masters the remake draws as lit spheres (GoF2/Es2Planet, stations.json "planetSphere"): the look and the maps
# its compiled shader samples (M_Planet_Desert: its ReferencedTextures), each written once into the mod as it is (every
# channel, linear; the normals in ES2's DirectX form, the shader reads them so).
SPHERES = {'MI_Planet_Desert_A': ('es2Desert', {
    'surface': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_H_C_R.png',
    'normal': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_N.png',
    'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
    'capColour': 'Assets/Shared/Textures/Rock/T_Rocks_004_C.png',
    'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png'}),
    # (2026-11-06) the gas giants: M_Planet_GasSmooth / M_Planet_Gas's compiled shaders (es2_re planetmat); their two colours
    # the masters' defaults (linear; the instances keep them), turned per planet by its PlanetData Variation
    'MI_Planet_GasSmooth_A': ('es2GasSmooth', {
        'surface': 'Assets/Environment/Planets/Textures/T_Planet_Gas_002_C_H.png',
        'normal': 'Assets/Environment/Planets/Textures/T_Planet_Gas_002_N.png',
        'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
        'capColour': 'Assets/Shared/Textures/Rock/T_Rocks_004_C.png',
        'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png'},
        [[0.02, 0.071433, 0.1], [0.166665, 0.487763, 0.5]]),   # Color, Color2
    'MI_Planet_Gas_A': ('es2Gas', {
        'surface': 'Assets/Environment/Planets/Textures/T_Planet_Gas_001_C_H.png',
        'normal': 'Assets/Environment/Planets/Textures/T_Planet_Gas_001_N.png',
        'noise': 'Assets/Shared/Textures/Effects/T_Noise_001_M.png'},
        [[0.5, 0.233332, 0.099999], [1.0, 0.515625, 0.354167]]),   # SecondaryColor, BaseColor
    # (2026-11-06) the grey cratered moons: M_Planet_Cratered (craters or rock by a noise, the desert's poles)
    'MI_Planet_Cratered_A': ('es2Cratered', {
        'surface': 'Assets/Environment/Planets/Textures/T_Planet_Craters_001_H_C_R.png',
        'normal': 'Assets/Environment/Planets/Textures/T_Planet_Craters_001_N.png',
        'surface2': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_H_C_R.png',
        'normal2': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_N.png',
        'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
        'capColour': 'Assets/Shared/Textures/Rock/T_Rocks_004_C.png',
        'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png'})}
# (2026-11-06) the volcanic planets: M_Planet_Volcanic's lava (its compiled emissive pass), its rock from the master's
# BaseColor; T_Quixel_Rock_024_C_R_H through tools/planet_assets.txt
SPHERES['MI_Planet_Volcanic_A'] = ('es2Volcanic', {
    'surface': 'Assets/Environment/Planets/Textures/T_Planet_Volcanic_001_M.png',
    'normal': 'Assets/Environment/Planets/Textures/T_Planet_Volcanic_001_N.png',
    'surface2': 'Assets/Shared/Textures/Quixel/T_Quixel_Rock_024_C_R_H.png',
    'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
    'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png',
    'noise2': 'Assets/Shared/Textures/Effects/T_Noise_008_M.png'},
    [[0.05, 0.048342, 0.043371], [1.0, 0.25, 0.1]])   # BaseColor, LavaColor
# (2026-11-06) the ice and water planets, with M_Planet_Ice / M_Planet_Water's drifting clouds
CLOUDS = {'clouds': 'Assets/Environment/Planets/Textures/T_Planet_Clouds_001_C_AO.png',
          'cloudsNormal': 'Assets/Environment/Planets/Textures/T_Planet_Clouds_001_N.png'}
SPHERES['MI_Planet_Ice_A'] = ('es2Ice', dict({
    'surface': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_H_C_R.png',
    'normal': 'Assets/Environment/Planets/Textures/T_Planet_Rock_002_N.png',
    'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
    'capColour': 'Assets/Shared/Textures/Rock/T_Rocks_004_C.png',
    'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png'}, **CLOUDS),
    [[0.7708, 0.9229, 1.0], [0.7708, 0.9229, 1.0]])   # BaseColor (one colour)
SPHERES['MI_Planet_Water_A'] = ('es2Water', dict({
    'surface': 'Assets/Shared/Textures/Effects/T_Noise_018_M.png',
    'normal': 'Assets/Shared/Textures/Effects/T_Noise_018_N.png',
    'noise2': 'Assets/Shared/Textures/Effects/T_Noise_009_M.png'}, **CLOUDS),
    [[0.08, 0.156, 0.2], [0.4, 0.4832, 0.5]])   # Color, IceColor
SPHERES['MI_Planet_Earthlike_A'] = ('es2Earthlike', dict({   # (land, seas and clouds: its colours are the shader's own)
    'surface': 'Assets/Environment/Planets/Textures/T_Planet_Mountains_001_H_C_R.png',
    'normal': 'Assets/Environment/Planets/Textures/T_Planet_Mountains_001_N.png',
    'surface2': 'Assets/Environment/Planets/Textures/T_Planet_Rock_001_H_C_R.png',
    'normal2': 'Assets/Environment/Planets/Textures/T_Planet_Rock_001_N.png',
    'capNormal': 'Assets/Shared/Textures/Rock/T_Rocks_004_N.png',
    'capColour': 'Assets/Shared/Textures/Rock/T_Rocks_004_C.png',
    'noise': 'Assets/Shared/Textures/Effects/T_Noise_016_M.png',
    'noise2': 'Assets/Shared/Textures/Effects/T_Noise_015_M.png'}, **CLOUDS))
SPHERES['MI_Planet_Desert_Okkar'] = SPHERES['MI_Planet_Desert_A']   # (M_Planet_Desert unchanged: the same look and maps)


def planet_sphere(pl):
    """A planet's stations.json "planetSphere" (its master's look, its maps in the mod, its atmosphere colour), or None
    when the remake has no sphere for its master or the export lacks a map."""
    look = SPHERES.get(pl.get('material'))
    if not look: return None
    maps = {}
    for role, src in look[1].items():
        rel = 'sectors/planets/' + os.path.basename(src)
        with jobs.once(('sphere', rel)):
            if not jobs.exists(os.path.join(MOD, rel)):
                p = os.path.join(SRC, src)
                if not os.path.exists(p): return None
                jobs.write_image(os.path.join(MOD, rel), np.asarray(Image.open(p).convert('RGBA')), 2048)
        maps[role] = rel
    out = {'look': look[0], 'maps': maps}
    if pl.get('atmosphere'): out['atmosphere'] = [round(float(c), 3) for c in pl['atmosphere']]
    if len(look) > 2:   # (the gas giants: their colours, the planet's variation)
        out['colors'] = look[2]
        out['variation'] = round(float(pl.get('variation', 0.5) or 0.0) % 1.0, 4)
    return out


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
    spec = spec_of(key)
    sec = sector(key)
    sid = spec['id']
    os.makedirs(os.path.join(MOD, 'sectors', sid), exist_ok=True)
    kept = [l for l in spec['locations'] if l[0] in sec['locations']]
    centre = np.mean([sec['locations'][l[0]]['map'] for l in kept], axis=0)
    # the sky and the sun
    sky_rel = f'sectors/{sid}/sky.jpg'
    sky_panorama(sec, centre, os.path.join(MOD, sky_rel))
    sun_rel = _write_png(f'sectors/{sid}/sun.png', sun_image(sec['sun']))[len(MOD) + 1:]
    sc = np.array(sec['sun'], np.float32); sc = sc / max(sc.max(), 1e-6)
    system = {'id': sid, 'name': sec['name'], 'race': f'es2_ships:{spec["race"]}', 'traffic': 'mod',
              'locals': [f'es2_ships:{f}' for f in spec['locals']], 'raiders': [f'es2_ships:{f}' for f in spec['raiders']],
              'security': spec['security'], 'visible': True,
              # 'sky': the game's sky whose sun sprite the star map shows (its own sun, sky and light replace the rest):
              # the one whose sun's colour is nearest the sector's
              'position': galaxy_position(sec.get('galaxy', np.zeros(3))), 'sky': map_sky(sec['sun']),
              'sunTexture': sun_rel.replace(os.sep, '/'), 'sunColor': [round(float(0.55 + 0.45 * v), 3) for v in sc],
              'skybox': {'nebula': sky_rel, 'stars': 'none', 'rotation': [0, 0, 0]}}
    if spec['gates'] and spec.get('gateStation'):   # ES2's own jumpgates and wormholes, to its own sectors only
        system['gates'] = [f'es2_ships:{g}' for g in spec['gates']]
        system['gateStation'] = f'es2_ships:{spec["gateStation"]}'
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
        # (GoF2 calls a station "<name> Station" itself: "Okrot Trading Station" would read "... Station Station")
        name = L['name'][:-8] if L['name'].endswith(' Station') else L['name']
        st = {'id': gid, 'system': f'es2_ships:{sid}', 'name': name, 'techLevel': tech, 'planet': 6, 'interior': interior}
        # its lore (locations.CSV): what it is under its name on the star map, the description on the map and the ticker
        lore = location_lore().get(es2_id)
        sub = (lore[1] if lore and lore[1] else L.get('subtitle')) or ''
        if sub: st['subtitle'] = sub
        if lore and lore[2]: st['description'] = lore[2]
        orbit = {}
        if look is None:
            orbit['station'] = False
        elif isinstance(look, int):
            st['looksLike'] = look
        else:
            model, *flags = look.split()
            st['model'] = model; st['modelSize'] = 30000
            if 'nodock' in flags: orbit['station'] = 'nodock'
            # an outlaw stronghold: held by pirates on every visit, outposts and guards (the remake's pirateHeld), not at the gate
            if 'nodock' in flags and model == 'gof2:station_pirates' and not (spec['gates'] and gid == spec['gateStation']):
                orbit['pirateHeld'] = True
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
            sphere = planet_sphere(pi[2])   # ES2's own planet material, drawn as a lit sphere where the remake has it
            if sphere: st['planetSphere'] = sphere
            if pi[2]['ring']: st['mapRing'] = True
        if asteroids is False: orbit['asteroids'] = False
        elif asteroids:
            orbit['asteroids'] = dict(asteroids)
            looks = asteroid_models(asteroids.get('type', 'rock'))   # ES2's own asteroid models
            if looks: orbit['asteroids'].update({'models': list(looks['models']), 'materials': list(looks['materials'])})
        if not (spec['gates'] and gid == spec['gateStation']): orbit['jumpgate'] = False   # (the gate only where ES2's is)
        if L.get('level'): orbit['level'] = int(max(1, min(30, L['level'])))   # ES2's location level: its encounters' pay
        hz = level_hazards(es2_id)   # ES2's heat volumes and radiation fields at their places
        if hz: orbit['hazards'] = hz
        amb = level_ambience(es2_id)   # ES2's ambience zones round its stations, factories and wrecks
        if amb: orbit['ambience'] = amb
        storm = level_storm(es2_id)   # ES2's lightning storm round the camera
        if storm: orbit['storm'] = storm
        mf = level_minefields(es2_id)   # ES2's minefields at their places (the remake gates them by security, rank and share)
        if mf: orbit['minefields'] = mf
        acid = level_acid_sacks(es2_id)   # ES2's acid pouches on their stalks
        if acid: orbit['acidSacks'] = acid
        gc = level_gas_clouds(es2_id, L.get('level'))   # ES2's plasma fields as GoF2's gas clouds
        if gc: orbit['gasClouds'] = gc
        loc, raid = orbit_spawns(es2_id)   # who flies here in ES2 (location_spawns.CSV)
        if loc: orbit['locals'] = [f'es2_ships:{f}' for f in loc]
        if raid: orbit['raiders'] = [f'es2_ships:{f}' for f in raid]
        if is_wreck_place(L):   # ES2's war wrecks to salvage, among its wreck hulls
            orbit['wrecks'] = {'count': 16, 'spread': 80000}
            hulls = wreck_models()
            if hulls: orbit['wrecks'].update({'models': hulls['models'], 'materials': hulls['materials'], 'hulks': WRECK_HULKS, 'size': WRECK_SIZE})
        ct = level_containers(es2_id)   # ES2's item containers there
        unique = orbit_unique_loot(es2_id)   # ... and its fixed loot in them, once a game
        cloaked = level_cloaked_containers(es2_id)   # ... and its cloaked containers (the fixed loot in them first)
        if cloaked:
            ct = ct or {'count': 0}
            ct['cloaked'] = cloaked
        secure = level_secure_containers(es2_id)   # ... and its armoured containers locked by shot triggers
        if secure:
            ct = ct or {'count': 0}
            ct['secure'] = secure
        if unique:
            ct = ct or {'count': min(len(unique), 6), 'spread': 40000, 'bulletproof': 0.5}
            ct['loot'] = unique
        if ct:
            models = container_models()   # ES2's own container models
            if models: ct.update({k: (list(v) if k == 'materials' else v) for k, v in models.items()})
            orbit['containers'] = ct
        ln = level_lanes(es2_id)   # ... and its ships' traffic lanes
        if ln: orbit['lanes'] = ln
        st['orbit'] = orbit
        m = L['map']
        st['mapPlace'] = {'angle': round(math.degrees(math.atan2(m[1], m[0])) % 360, 1),
                          'distance': round(8000 + 37000 * float(np.linalg.norm(m[:2])) / radius_max)}
        stations.append(st)
        LOG(f'  {L["name"]} ({L["subtitle"]}): ' + ('station' if 'station' not in orbit else str(orbit['station'])) +
            f', planet {sec["planets"][pid]["name"] if pid in sec["planets"] else "-"}')
    return system, stations, sec


def mining_times():
    """ES2's DT_Mining_Yield as items.json "miningTime" (percent of the game's layer time) per resource key: its Duration
    against Iron's (5 s; the crystals 10 s). Its MaxYield (8) and Difficulty (0.5) are the same for every row, so they
    change nothing between ores. A resource the table lacks takes its kind's (Mallemite and Phazium the crystals')."""
    p = os.path.join(SRC, 'Blueprints/Environment/Resources/DT_Mining_Yield.json')
    if not os.path.exists(p): return {}
    rows = json.load(open(p, encoding='utf-8-sig'))[0].get('Rows', {})
    dur = {k: next((v for kk, v in r.items() if kk.startswith('Duration')), None) for k, r in rows.items()}
    base = dur.get('ore_iron') or 5.0
    by_kind = {}
    for k, d in dur.items():
        if d: by_kind.setdefault(k.split('_')[0], d)
    out = {}
    for key, _, kind, _, _ in RESOURCES:
        d = next((v for k, v in dur.items() if k.endswith('_' + key) and v), None) or by_kind.get(kind)
        if d and round(d / base * 100) != 100: out[key] = int(round(d / base * 100))
    return out


_lore = None
def location_lore():
    """DataFiles/locations.CSV: {location id: (name, subtitle, description)} (Windows-1252; its fields "|~"-separated: id, name, subtitle,
    description, ..., the unlock flag, the build)."""
    global _lore
    if _lore is None:
        _lore = {}
        p = os.path.join(SRC, 'DataFiles', 'locations.CSV')
        if os.path.exists(p):
            for line in open(p, encoding='cp1252', errors='replace'):   # (Windows-1252: its ellipses are 0x85)
                f = [x.strip() for x in line.rstrip('\r\n').split('|~')]
                if len(f) >= 4 and f[0]: _lore[f[0]] = (f[1], f[2], '' if f[3] == '-' else f[3])
    return _lore


def resource_items(mod):
    """items.json entries of ES2's resources (their icons on the commodity plate, icons.py; their mining time from
    DT_Mining_Yield)."""
    import icons
    out = []
    times = mining_times()
    for key, name, kind, rarity, icon in RESOURCES:
        p = RARITY_PRICE[rarity]
        out.append({'id': f'es2_{key}', 'base': CRYSTAL_BASE if kind == 'crystal' else ORE_BASE, 'name': name,
                    'description': f'An EVERSPACE 2 {kind} ({rarity}), mined from the asteroids where it occurs.',
                    'techLevel': 1, 'occurrence': RARITY_OCCURRENCE[rarity], 'price': [p, int(round(p * 1.1))],
                    '_icon': icon + '_86x86_2x', '_frame': 'commodity'})
        if key in times: out[-1]['stats'] = {'miningTime': times[key]}
    import es2data
    for es2_id, icon, occ in DROPS:
        e = es2data.items().get(es2_id) or {}
        row = e.get('row') or []
        p = int(round((es2data.attr(es2_id, 'item_price') or 400) * DROP_PRICE_FACTOR))
        text = row[8].strip() if len(row) > 8 and row[8].strip() else 'An EVERSPACE 2 resource.'
        out.append({'id': f'es2_{es2_id}', 'base': ORE_BASE, 'name': e.get('name') or es2_id.replace('_', ' ').title(),
                    'description': text + (' Stations trade it.' if occ else ' Dropped by the ships that carry it in EVERSPACE 2.'),
                    'techLevel': 1, 'occurrence': occ, 'price': [p, int(round(p * 1.1))], '_icon': icon, '_frame': 'commodity'})
    icons.apply(out, mod)
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    return out


def build(log=print):
    """The sectors (systems.json, the stations to add to stations.json) and ES2's resources. Returns (systems, stations, items).
    """
    global LOG
    LOG = log
    systems, stations = [], []
    music = []
    ids = set()
    for key in SECTOR_KEYS:
        system, sts, sec = build_sector(key)
        spec = spec_of(key)
        for st in sts:   # (ES2 reuses names across sectors: a second one takes its sector's name)
            if st['id'] in ids:
                old = st['id']; st['id'] = old + '_' + system['id'][4:]
                if system.get('gateStation') == f'es2_ships:{old}': system['gateStation'] = f'es2_ships:{st["id"]}'
            ids.add(st['id'])
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
            # the fights' music: each sector's tense layer, then its battle set (battle_music.py; systems.json "battleMusic")
            import battle_music
            battle_music.SRC = SRC
            battle_music.add([(key, m[0]) for key, m in zip(SECTOR_KEYS, music)], LOG)
    except Exception as e:
        LOG(f'  no sector music: {e}')
    # the storms' thunder: ES2's waves as the mod's sounds
    try:
        n = write_thunder(stations)
        if n: LOG(f'  storms: {sum(1 for st in stations if st.get("orbit", {}).get("storm"))}, {n} thunder sounds')
    except Exception as e:
        for st in stations: st.get('orbit', {}).get('storm', {}).pop('thunder', None)
        LOG(f'  no thunder: {e}')
    # the secure containers' puzzle sounds: ES2's grab, dispenser, conductor and armoured container waves
    try:
        n = write_puzzle_sounds(stations)
        if n: LOG(f'  puzzle sounds: {n}')
    except Exception as e:
        LOG(f'  no puzzle sounds: {e}')
    # the orbits' ambience zones: their waves as the mod's sounds (the zones dropped when they can't be written)
    try:
        zones, waves = write_ambience(stations)
        LOG(f'  ambience: {zones} zones, {waves} sounds')
    except Exception as e:
        for st in stations: st.get('orbit', {}).pop('ambience', None)
        LOG(f'  no ambience: {e}')
    items = resource_items(MOD)
    LOG(f'  {len(items)} of EVERSPACE 2\'s resources as commodities ({sum(1 for i in items if i.get("icon"))} icons)')
    return systems, stations, items
