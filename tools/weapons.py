"""EVERSPACE 2's weapons as the ES2 Ships mod's items (items.json): every player weapon of ES2 (its primaries, secondaries,
the Okkar and legendary variants) and the capital ships' turrets (warships.py), each a mod item "based on" the GoF2 weapon
that behaves most like it (its kind: laser bolt, blaster, beam, auto-cannon, scatter burst, thermo homing shot, rocket,
missile, cluster, mine), keeping what makes the ES2 weapon itself:
  - its rate of fire (FireRate) and so its reload, its projectile speed and range against the family's, its spread as a
    salvo (the coil gun's scatter, parallel and burst variants), its burst fire (salvoCount / salvoGapMs);
  - its hull / shield split (HullDamage : ShieldDamage) as the remake's "shieldDamage": the blaster and the pulse laser
    strip shields, the autocannon and the scatter gun are hull breakers;
  - its effect as the nearest GoF2 mechanic: cryo (frost) and lightning as EMP damage, shield breakers / destabilizers as
    shield damage, the flak's and the mines' blasts, the legendary homing barrages as cluster missiles;
  - its own look (the base's projectile, muzzle flash and impact recoloured in its ES2 colour), its own fire sound (its
    FireSounds / FireSound cue), its own ES2 weapon model on the ships' hardpoints (build.HARDPOINTS rules by item).
Damage is set on GoF2's own ladder by tech level (DPS), times the family's ES2 character, so they fit the game's balance.
Rarity: the base weapons tech level 5-7, the Okkar and special variants one higher, the legendaries 10 (rare in shops).

The capital turrets (TURRETS) are NPC-only (occurrence 0, never stocked): ES2's own turret models (Assets/Turrets/Meshes,
split by bone like build.turret_model into base / pivot / gun with their textures embedded) on the GoF2 turret behaviour.
"""
import json, os, re, glob, struct, io
import numpy as np
from PIL import Image
import glbtool, es2mat

SRC = MOD = None
LOG = print


def configure(src, mod, log=print):
    global SRC, MOD, LOG
    SRC, MOD, LOG = src, mod, log
    es2mat.configure(src)


# The GoF2 items the ES2 weapons are based on: their stats (items.json; the importer runs without the remake's files).
BASE = {5: {'damage': 16, 'loadingTimeMs': 900, 'range': 2200, 'projectileSpeed': 22}, 7: {'damage': 18, 'loadingTimeMs': 750, 'range': 2200, 'projectileSpeed': 23},
        9: {'damage': 27, 'loadingTimeMs': 1200, 'range': 2400, 'projectileSpeed': 20}, 10: {'damage': 34, 'loadingTimeMs': 1400, 'range': 2600, 'projectileSpeed': 20},
        11: {'damage': 51, 'loadingTimeMs': 1500, 'range': 2600, 'projectileSpeed': 20}, 19: {'damage': 12, 'loadingTimeMs': 300, 'range': 1400, 'projectileSpeed': 17},
        21: {'damage': 13, 'loadingTimeMs': 220, 'range': 1000, 'projectileSpeed': 19}, 25: {'damage': 3, 'loadingTimeMs': 120, 'range': 1400, 'projectileSpeed': 26},
        27: {'damage': 4, 'loadingTimeMs': 90, 'range': 1400, 'projectileSpeed': 30}, 29: {'damage': 4, 'loadingTimeMs': 170, 'range': 2000, 'projectileSpeed': 14},
        176: {'damage': 13, 'loadingTimeMs': 700, 'range': 2000, 'projectileSpeed': 22}, 177: {'damage': 19, 'loadingTimeMs': 750, 'range': 2100, 'projectileSpeed': 25},
        183: {'damage': 18, 'loadingTimeMs': 300, 'range': 2000, 'projectileSpeed': 28}, 193: {'damage': 5, 'loadingTimeMs': 120, 'range': 2200, 'projectileSpeed': 17},
        228: {'damage': 120, 'loadingTimeMs': 1300, 'range': 2600, 'projectileSpeed': 22}, 32: {'damage': 70, 'loadingTimeMs': 900, 'range': 1200, 'projectileSpeed': 14},
        37: {'damage': 100, 'loadingTimeMs': 3000, 'range': 8000, 'projectileSpeed': 18}, 38: {'damage': 140, 'loadingTimeMs': 3000, 'range': 8000, 'projectileSpeed': 10},
        39: {'damage': 0, 'loadingTimeMs': 3000, 'range': 10000, 'projectileSpeed': 15}, 40: {'damage': 120, 'loadingTimeMs': 3000, 'range': 10000, 'projectileSpeed': 17},
        60: {'damage': 350, 'loadingTimeMs': 1000, 'range': 40000}, 62: {'damage': 700, 'loadingTimeMs': 4000, 'range': 60000},
        214: {'damage': 60, 'loadingTimeMs': 3000, 'range': 8000, 'projectileSpeed': 8}, 216: {'damage': 90, 'loadingTimeMs': 3000, 'range': 10000, 'projectileSpeed': 10},
        48: {'damage': 10, 'loadingTimeMs': 280, 'range': 2500, 'projectileSpeed': 32}, 49: {'damage': 12, 'loadingTimeMs': 250, 'range': 3000, 'projectileSpeed': 32},
        224: {'damage': 18, 'loadingTimeMs': 200, 'range': 3000, 'projectileSpeed': 32}}


# GoF2's DPS ladder by tech level (items.json: Berger Retribution 24 at 7, Gram 40 at 7, Tyrfing 59 at 9, the TL9 specials
# 60-90): the ES2 weapons sit on it.
DPS = {4: 18, 5: 22, 6: 27, 7: 33, 8: 42, 9: 55, 10: 68}
# A secondary's damage per hit by tech level (Intelli Jet 100 at 5, Dephase 120 at 8, Patala 90 x cluster at 9).
HIT = {4: 80, 5: 95, 6: 110, 7: 125, 8: 145, 9: 170, 10: 210}

# family -> (GoF2 base item, kind, colour, tech level, DPS factor, ES2 weapon model number (build.W) or None)
PRIMARY = {
    'Autocannon':   (27, 'cannon',  '#ffb347', 5, 0.95, None),
    'Blaster':      (19, 'blaster', '#5aa0ff', 5, 1.00, 4),
    'BeamLaser':    (9,  'beam',    '#ff4a3a', 6, 1.10, 3),
    'ThermalBeam':  (10, 'beam',    '#ff8a1c', 7, 1.10, 3),
    'CryoBeam':     (10, 'beam',    '#8fe4ff', 7, 1.00, 3),
    'LightningGun': (11, 'beam',    '#b48cff', 7, 0.95, 3),
    'PulseLaser':   (7,  'laser',   '#ff5a3c', 5, 1.00, 5),
    'ThermalPulse': (7,  'laser',   '#ff9a2a', 6, 1.05, 5),
    'CryoLance':    (7,  'laser',   '#9fe8ff', 6, 0.95, 5),
    'CoilGun':      (25, 'cannon',  '#d8e8ff', 6, 1.05, 7),
    'GaussCannon':  (5,  'laser',   '#c070ff', 6, 1.05, 6),
    'RailGun':      (228, 'beam',   '#7fb8ff', 7, 1.15, 9),
    'Flak':         (177, 'scatter', '#ff9040', 6, 1.00, 10),
    'ScatterGun':   (176, 'scatter', '#ffe070', 5, 1.10, 11),
    'ThermoGun':    (29, 'thermo',  '#ff6a20', 6, 0.90, 8),
    'ChargeOrb':    (183, 'laser',  '#55e0ff', 7, 1.00, 4),
    'GooGun':       (21, 'blaster', '#8cff4a', 9, 1.00, 12),
    'PlasmaThrower': (193, 'thermo', '#ff58d0', 9, 1.05, 12),
}
# family -> (GoF2 base item, kind, colour, tech level, damage factor, extra stats)
SECONDARY = {
    'HomingMissileLauncher':       (37, 'missile', '#ffd0a0', 5, 1.00, {}),
    'RocketLauncher':              (32, 'rocket',  '#ffb070', 4, 1.00, {}),
    'CruiseMissileLauncher':       (38, 'missile', '#ffa060', 7, 2.20, {'reloadMs': 4000}),
    'EMPMissileLauncher':          (39, 'missile', '#7fc8ff', 6, 0.20, {'empDamage': 110}),
    'CryoMissileLauncher':         (40, 'missile', '#a8ecff', 7, 0.70, {'empDamage': 70}),
    'CorrosionMissileLauncher':    (37, 'missile', '#9cff5a', 6, 1.30, {'shieldDamage': 40}),
    'ShieldBreakerMissileLauncher': (37, 'missile', '#5ad8ff', 6, 0.90, {'shieldDamage': 400}),
    'ArmorBreakerMissileLauncher': (37, 'missile', '#ff7a4a', 6, 1.40, {'shieldDamage': 25}),
    'DestabilizerMissileLauncher': (37, 'missile', '#d070ff', 7, 0.90, {'shieldDamage': 220, 'empDamage': 30}),
    'ExorciserMissileLauncher':    (37, 'missile', '#fff09a', 8, 1.25, {}),
    'ParasiticMissileLauncher':    (37, 'missile', '#c0ff60', 8, 1.10, {'empDamage': 30}),
    'SporeMissileLauncher':        (214, 'cluster', '#a0ff80', 8, 0.80, {}),
    'WebMissileLauncher':          (39, 'missile', '#e0e0ff', 7, 0.30, {'empDamage': 140}),
    'ThermalMissileLauncher':      (37, 'missile', '#ff8030', 7, 0.55, {'salvoShots': 3}),
    'TetherMissileLauncher':       (40, 'missile', '#ff60a0', 10, 1.60, {'empDamage': 60}),
    'SwarmMissileLauncher':        (216, 'cluster', '#ffc060', 10, 1.20, {}),
    'MineLauncher':                (60, 'mine',    '#ffa040', 5, 1.00, {}),
    'AutocannonMineLauncher':      (62, 'mine',    '#ffb347', 10, 1.20, {}),
}
# Variant suffixes: (name, tech level +, DPS factor, stat changes, colour or None, legendary)
VARIANT = {
    'Okkar': ('Okkar {}', 1, 1.0, {}, '#5cff9a', False),
    'Cryo': ('Cryo {}', 1, 0.9, {'empDamage': 2}, '#9fe8ff', False),
    'Bloodstar': ('{} "Bloodstar"', 4, 1.0, {}, '#ff2040', True),
    'Eclipse': ('{} "Eclipse"', 4, 1.0, {}, '#ffd040', True),
    'Charged': ('Charged {}', 1, 1.15, {'reloadx': 1.3}, None, False),
    'Heavy': ('Heavy {}', 1, 1.0, {'reloadx': 1.6}, None, False),
    'Highfirerate': ('Rapid {}', 1, 1.0, {'reloadx': 0.6}, None, False),
    'Parallel': ('Parallel {}', 1, 1.0, {'salvoShots': 2, 'dmgx': 0.5}, None, False),
    'Scatter': ('Scatter {}', 1, 1.0, {'salvoShots': 5, 'dmgx': 0.2}, None, False),
    'Judge': ('{} "Judge"', 3, 1.0, {'salvoCount': 3, 'salvoGapMs': 100, 'reloadx': 2.4}, '#ffe0a0', True),
    'Redemption': ('{} "Redemption"', 4, 1.0, {}, '#ffffff', True),
    'Dragon': ('{} "Dragon"', 4, 1.0, {'salvoShots': 3, 'dmgx': 0.34}, '#ff3010', True),
    'Freeze': ('{} "Freeze"', 4, 1.0, {'empDamage': 4}, '#c0f4ff', True),
    'Slime': ('{} "Slime"', 4, 1.0, {}, '#90ff40', True),
    'EMP': ('EMP {}', 1, 1.0, {'empDamage': 300, 'dmgx': 0.15}, '#7fc8ff', False),
    'Web': ('Web {}', 1, 1.0, {'empDamage': 220, 'dmgx': 0.2}, '#e0e0ff', False),
    'Cluster': ('Cluster {}', 1, 1.0, {'dmgx': 1.35}, None, False),
}


def bp_config(name, seen=None):
    """A weapon blueprint's WeaponConfig with its parents' (the child's values winning), its ES2 model and fire cues."""
    seen = seen or set()
    p = glob.glob(os.path.join(SRC, 'Blueprints', '**', name + '.json'), recursive=True)
    if not p or name in seen: return {}, None, []
    seen.add(name)
    d = json.load(open(p[0], encoding='utf-8-sig'))
    sup = next((e.get('Super', {}).get('ObjectName') for e in d if e.get('Type') == 'BlueprintGeneratedClass'), None)
    sup = sup.split("'")[1][:-2] if sup and "'" in sup else None
    cfg, mesh, cues = bp_config(sup, seen) if sup else ({}, None, [])
    cdo = next((e for e in d if e.get('Name', '').startswith('Default__')), None)
    pr = cdo.get('Properties', {}) if cdo else {}
    for k, v in (pr.get('WeaponConfig') or {}).items():
        if isinstance(v, dict) and 'AttributeValueSimple' in v: cfg[k] = v['AttributeValueSimple'].get('BaseValue')
        elif not isinstance(v, (dict, list)): cfg[k] = v
    for e in d:
        sm = (e.get('Properties', {}) or {}).get('StaticMesh')
        if e.get('Type') == 'StaticMeshComponent' and sm: mesh = sm['ObjectName'].split("'")[1]
    own = re.findall(r"SoundCue'(S_SC_[A-Za-z0-9_]+)'", json.dumps(pr.get('FireSounds') or pr.get('FireSound') or []))
    if own: cues = own
    return cfg, mesh, cues


def humanize(s):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s).replace('_', ' ')
    return s.replace('E M P', 'EMP').replace('Coil Gun', 'Coil Gun').strip()


def parse(bp):
    """BP_Weapon_<Family>[_<Variant ...>] -> (family, variants)."""
    name = bp[len('BP_Weapon_'):]
    if name.startswith('Legendary_'): name = name[len('Legendary_'):]
    parts = name.split('_')
    fam = parts[0]
    rest = parts[1:]
    if fam.endswith('MissileLauncher') and fam not in SECONDARY and fam + '' in SECONDARY: pass
    return fam, rest


def round_price(v):
    m = 10 ** max(0, len(str(int(v))) - 2)
    return int(round(v / m) * m)


def item_price(tl, secondary, legendary):
    if secondary:
        return round_price({4: 40, 5: 120, 6: 220, 7: 340, 8: 520, 9: 900, 10: 1600}[tl] * (2 if legendary else 1))
    return round_price({4: 9000, 5: 24000, 6: 42000, 7: 70000, 8: 120000, 9: 260000, 10: 560000}[tl] * (1.6 if legendary else 1))


def make_item(bp):
    fam, rest = parse(bp)
    cfg, mesh, cues = bp_config(bp)
    secondary = fam in SECONDARY
    spec = SECONDARY.get(fam) if secondary else PRIMARY.get(fam)
    if not spec: return None
    tl = spec[3]
    colour = spec[2]
    name = humanize(fam).replace(' Launcher', ' Launcher')
    stats_extra = dict(spec[5]) if secondary else {}
    dps_f = 1.0 if secondary else spec[4]
    dmg_f = spec[4] if secondary else 1.0
    legendary = 'Legendary' in bp or any(VARIANT.get(r, (0, 0, 0, {}, 0, False))[5] for r in rest)
    known = [r for r in rest if r in VARIANT]
    extra_words = [r for r in rest if r not in VARIANT and r != 'Legendary']
    for r in known:
        vname, dtl, vdps, vstats, vcol, _ = VARIANT[r]
        name = vname.format(name)
        tl += dtl
        dps_f *= vdps
        for k, v in vstats.items():
            if k == 'dmgx': dmg_f *= v
            elif k == 'reloadx': stats_extra['reloadx'] = stats_extra.get('reloadx', 1.0) * v
            elif k == 'empDamage': stats_extra['empDamage'] = stats_extra.get('empDamage', 0) + v
            else: stats_extra[k] = v
        if vcol: colour = vcol
    if legendary:
        tl = 10
        if extra_words: name = f'{name} "{humanize(" ".join(extra_words))}"'
    elif extra_words:
        name = f'{name} {humanize(" ".join(extra_words))}'
    tl = max(4, min(10, tl))
    bs = BASE[spec[0]]
    stats = {}
    if secondary:
        reload = stats_extra.pop('reloadMs', bs.get('loadingTimeMs') or 2000)
        reload = int(reload * stats_extra.pop('reloadx', 1.0))
        dmg = HIT[tl] * dmg_f
        if spec[1] == 'cluster': dmg *= 0.6
        if spec[1] == 'mine': dmg *= 2.5
        stats['damage'] = max(1, int(round(dmg)))
        stats['reloadMs'] = reload
    else:
        fr = cfg.get('FireRate') or 0
        reload = bs.get('loadingTimeMs') or 500
        if fr and fr > 0 and spec[1] not in ('beam',) and fam not in ('GaussCannon',): reload = int(np.clip(1000.0 / fr, 90, 2500))   # (the gauss cannon's FireRate is its charge's)
        reload = int(reload * stats_extra.pop('reloadx', 1.0))
        # The DPS on the ladder (x the variant's: a parallel pair or a scatter shot fires 2 / 5 shots at 0.55 / 0.28 each);
        # the damage a shot rounded, the reload then set so the DPS stays exact (a fast gun's 1.6 a shot would round to 2).
        salvo = max(1, int(stats_extra.get('salvoShots', 1)))
        dps = DPS[tl] * dps_f * dmg_f * salvo
        dmg = max(1, int(round(dps * reload / 1000.0 / salvo)))
        stats['damage'] = dmg
        stats['reloadMs'] = int(max(60, round(1000.0 * dmg * salvo / dps)))
        sp = cfg.get('Speed')
        if sp and sp > 0 and bs.get('projectileSpeed'):
            stats['speed'] = int(round(bs['projectileSpeed'] * float(np.clip((sp / 132000.0) ** 0.5, 0.6, 1.6))))
        rg = cfg.get('Range')
        if rg and bs.get('range'):
            stats['lifetimeMs'] = int(round(bs['range'] * float(np.clip(rg / 125000.0, 0.6, 1.8))))
        hd, sd = cfg.get('HullDamage'), cfg.get('ShieldDamage')
        if hd and sd and hd > 0:
            stats['shieldDamage'] = int(np.clip(100.0 * sd / hd, 40, 300))
    for k, v in stats_extra.items():
        if k in ('empDamage', 'shieldDamage', 'salvoShots', 'salvoCount', 'salvoGapMs'): stats[k] = int(v)
    occurrence = 3 if legendary else 25 if tl <= 6 else 15 if tl <= 8 else 8
    return {
        'id': bp[len('BP_Weapon_'):].lower(), 'base': spec[0], 'name': name,
        'description': describe(fam, known, secondary, stats, legendary),
        'techLevel': tl, 'occurrence': occurrence, 'price': item_price(tl, secondary, legendary),
        'stats': stats,
        'fx': fx_parts(spec[1], colour),
        '_cues': cues, '_model': mesh, '_es2model': (None if secondary else spec[5]), '_secondary': secondary,
    }


def fx_parts(kind, colour):
    """The base weapon's own parts recoloured: only those its kind has (a missile or a turret has no muzzle flash or impact of
    its own to recolour, a scatter gun no impact; the mod's loader warns about the rest)."""
    parts = ['projectile'] if kind in ('missile', 'rocket', 'cluster', 'mine', 'turret') else ['projectile', 'muzzle'] if kind == 'scatter' \
        else ['projectile', 'muzzle', 'impact']
    return {p: {'color': colour} for p in parts}


FAMILY_TEXT = {
    'Autocannon': 'A fast-firing auto-cannon: weak against shields, it tears into hulls.',
    'Blaster': 'Plasma bolts that burn through shields.',
    'BeamLaser': 'A continuous laser beam that hits the moment it fires.',
    'ThermalBeam': 'A beam that heats its target past what its armour can take.',
    'CryoBeam': 'A freezing beam: its frost cripples a ship\'s systems.',
    'LightningGun': 'Arcs of lightning that jump to the nearest ship and scramble its systems.',
    'PulseLaser': 'EVERSPACE 2\'s pulse laser: quick, accurate bolts, best against shields.',
    'ThermalPulse': 'A pulse laser firing superheated bolts.',
    'CryoLance': 'Frozen lances that numb a ship\'s systems.',
    'CoilGun': 'Magnetic slugs at high velocity, equally good against hull and shields.',
    'GaussCannon': 'Heavy gauss slugs: slow to fire, hard to stop.',
    'RailGun': 'A rail gun: a charged slug that crosses the battlefield in an instant.',
    'Flak': 'Flak shells that burst near their target.',
    'ScatterGun': 'A scatter gun: a cone of pellets at close range.',
    'ThermoGun': 'Thermo shots that home in on their target.',
    'ChargeOrb': 'Orbs of charged energy that overload shields.',
    'GooGun': 'Sticky goo that eats into a ship\'s hull.',
    'PlasmaThrower': 'A short-range stream of plasma.',
    'HomingMissileLauncher': 'Homing missiles that follow their locked target.',
    'RocketLauncher': 'Unguided rockets: fast and hard-hitting if you aim well.',
    'CruiseMissileLauncher': 'A slow, heavy cruise missile with a devastating warhead.',
    'EMPMissileLauncher': 'EMP missiles that knock out a ship\'s systems.',
    'CryoMissileLauncher': 'Cryo missiles that freeze their target\'s systems.',
    'CorrosionMissileLauncher': 'Corrosive warheads that eat through armour and hull.',
    'ShieldBreakerMissileLauncher': 'Shield breakers: missiles made to collapse shields.',
    'ArmorBreakerMissileLauncher': 'Armour breakers: armour-piercing warheads.',
    'DestabilizerMissileLauncher': 'Destabilizers that unsettle shields and systems.',
    'ExorciserMissileLauncher': 'Exorcisers, made against the Ancients\' creations.',
    'ParasiticMissileLauncher': 'Parasitic warheads that drain their target.',
    'SporeMissileLauncher': 'Spore missiles that split into a cloud of seekers.',
    'WebMissileLauncher': 'Web missiles that tangle a ship\'s systems.',
    'ThermalMissileLauncher': 'Thermal missiles fired three at a time.',
    'TetherMissileLauncher': 'A tether missile that chains its target.',
    'SwarmMissileLauncher': 'A swarm of missiles from one launch.',
    'MineLauncher': 'Proximity mines laid behind you.',
    'AutocannonMineLauncher': 'Mines that open fire on whatever comes close.',
}


def describe(fam, variants, secondary, stats, legendary):
    t = FAMILY_TEXT.get(fam, 'An EVERSPACE 2 weapon.')
    if legendary: t += ' A legendary EVERSPACE 2 weapon.'
    if 'Okkar' in variants: t += ' Okkar make.'
    return t


# ---- the capital ships' turrets (NPC only) -------------------------------------------------------------------------------

# id -> (name, GoF2 base turret, ES2 turret mesh (Assets/Turrets/Meshes), colour, damage x, stats)
TURRETS = {
    'turret_outlaw':          ('Outlaw Coil Turret', 48, 'SK_Turret_Outlaw_001', '#d8e8ff', 1.0, {}),
    'turret_outlaw_missile':  ('Outlaw Missile Turret', 48, 'SK_Turret_GB_Rocket_001', '#ffb070', 1.3, {'missiles': 1, 'salvoCount': 2, 'salvoGapMs': 300, 'reloadMs': 2600}),
    'turret_gb':              ('G&B Heavy Laser Turret', 49, 'SK_Turret_GB_Warship_001', '#ff5a3c', 1.2, {}),
    'turret_gb_torpedo':      ('G&B Torpedo Turret', 48, 'SK_Turret_GB_Rocket_001', '#ffa060', 2.4, {'missiles': 1, 'reloadMs': 4200}),
    'turret_colonial':        ('Colonial Pulse Turret', 48, 'SK_Turret_Colonial_001', '#ff4a3a', 1.0, {}),
    'turret_colonial_heavy':  ('Colonial Heavy Turret', 49, 'SK_Turret_Colonial_001', '#ff3a2a', 1.3, {}),
    'turret_colonial_missile': ('Colonial Missile Turret', 48, 'SK_Turret_Medium_001', '#ffd0a0', 1.3, {'missiles': 1, 'salvoCount': 2, 'salvoGapMs': 250, 'reloadMs': 2800}),
    'turret_okkar':           ('Okkar Pulse Turret', 49, 'SK_Turret_Okkar_Medium_001', '#5cff9a', 1.0, {}),
    'turret_okkar_heavy':     ('Okkar Heavy Turret', 49, 'SK_Turret_Okkar_001', '#5cff9a', 1.3, {}),
    'turret_okkar_missile':   ('Okkar Missile Turret', 48, 'SK_Turret_Okkar_Medium_001', '#80ffb0', 1.3, {'missiles': 1, 'salvoCount': 3, 'salvoGapMs': 200, 'reloadMs': 3000}),
    'turret_cultist':         ('Cultist Turret', 224, 'SK_Turret_Medium_003', '#ff60e0', 1.2, {}),
    'turret_swarmer':         ('Swarmer Spitter', 224, 'SK_Turret_Medium_002', '#c0ff40', 1.1, {}),
    'turret_homebase':        ('Homebase Flak Turret', 224, 'SK_Turret_Homebase_001', '#ffa040', 1.2, {'salvoCount': 4, 'salvoGapMs': 90, 'reloadMs': 1400}),
    'turret_freighter':       ('Retractable Turret', 48, 'SK_Turret_Retractable_Medium_001', '#ffd080', 0.8, {}),
    # The Dreadnought's (encounter.py)
    'turret_dread_flak':      ('Dreadnought Flak Turret', 224, 'SK_Turret_Homebase_001', '#ff8030', 1.4, {'salvoCount': 5, 'salvoGapMs': 80, 'reloadMs': 1600}),
    'turret_dread_missile':   ('Dreadnought Missile Turret', 48, 'SK_Turret_GB_Rocket_001', '#ffb070', 1.5, {'missiles': 1, 'salvoCount': 4, 'salvoGapMs': 200, 'reloadMs': 3200}),
    'turret_dread_torpedo':   ('Dreadnought Torpedo Launcher', 48, 'SK_Turret_GB_Rocket_001', '#ff6a30', 3.2, {'missiles': 1, 'reloadMs': 5200}),
    'turret_dread_sniper':    ('Dreadnought Sniper Turret', 49, 'SK_Turret_Retractable_Medium_001', '#7fb8ff', 3.0, {'reloadMs': 2600, 'turretRange': 90000}),
    'turret_dread_lightning': ('Dreadnought Lightning Turret', 49, 'SK_Okkar_Charge_Orb_Turret_001', '#b48cff', 1.0, {'empDamage': 6, 'reloadMs': 700}),
}


def make_turret(tid, turret_models):
    name, base, mesh, colour, dmgx, extra = TURRETS[tid]
    bs = BASE[base]
    stats = {'damage': max(1, int(round((bs.get('damage') or 10) * dmgx * (1.6 if extra.get('missiles') else 1.0))))}
    for k, v in extra.items(): stats[k] = v
    fx = fx_parts('turret', colour)
    if mesh in turret_models: fx['turret'] = {'model': turret_models[mesh]}
    return {'id': tid, 'base': base, 'name': name, 'description': 'An EVERSPACE 2 capital ship turret.', 'techLevel': 8,
            'occurrence': 0, 'price': 0, 'stats': stats, 'fx': fx}


# ---- ES2 turret models: split by bone, textures embedded ------------------------------------------------------------------

def _png(arr):
    b = io.BytesIO(); Image.fromarray(np.ascontiguousarray(arr)).save(b, 'PNG', optimize=True); return b.getvalue()


def _resize(a, size=1024):
    if max(a.shape[:2]) <= size: return a
    s = size / max(a.shape[:2])
    return np.array(Image.fromarray(a).resize((int(a.shape[1] * s), int(a.shape[0] * s)), Image.LANCZOS))


def turret_glb(mesh_name, out_rel):
    """An ES2 turret (SK_Turret_*) as the remake's turret model: base / "pivot" / "turret_gun" / "muzzle" nodes by its bones
    (b_Lafette_Rotate the base turning sideways, b_Gun_Rotate* the barrel tilting, the muzzle sockets / flash bones), each
    triangle with its vertices' main bone; its materials embedded (glTF metallic-roughness, ES2's maps converted)."""
    path = os.path.join(SRC, 'Assets/Turrets/Meshes', mesh_name + '.glb')
    if not os.path.exists(path): return None
    g, b = glbtool.load(path)
    nodes = g['nodes']
    parent = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
    def world(i):
        t = np.zeros(3)
        while i is not None:
            t += np.array(nodes[i].get('translation', [0, 0, 0])); i = parent.get(i)
        return t
    joints = g['skins'][0]['joints'] if g.get('skins') else []
    def group(name):
        n = name.lower()
        if 'lafette' in n: return 1
        if 'gun' in n or 'barrel' in n or 'muzzle' in n or 'socket' in n or 'skt' in n: return 2
        return 0
    jg = np.array([group(nodes[j]['name']) for j in joints]) if joints else np.zeros(1, int)
    # ancestors: a bone under the gun is the gun's
    for k, j in enumerate(joints):
        i = parent.get(j)
        while i is not None:
            if i in joints and group(nodes[i]['name']) == 2: jg[k] = 2; break
            i = parent.get(i)
    piv = next((j for j in joints if 'lafette' in nodes[j]['name'].lower()), None)
    gun = next((j for j in joints if 'gun_rotate' in nodes[j]['name'].lower() or nodes[j]['name'].lower() == 'b_gun'), None)
    muz = [j for j in joints if 'muzzle' in nodes[j]['name'].lower() or 'skt_pw' in nodes[j]['name'].lower()]
    pivot = world(piv) if piv is not None else np.zeros(3)
    gunp = world(gun) if gun is not None else pivot
    muzzle = np.mean([world(j) for j in muz], axis=0) if muz else gunp + np.array([3.0, 0, 0])
    offset = [np.zeros(3), pivot, gunp]
    groups = [[], [], []]
    mats = {}
    for m in g['meshes']:
        for p in m['primitives']:
            A = p['attributes']
            arr = {k: glbtool.read(g, b, A[k])[0].astype(np.float32) for k in ('POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0') if k in A}
            tri = glbtool.read(g, b, p['indices'])[0].reshape(-1, 3).astype(np.int64)
            if joints and 'JOINTS_0' in A:
                jo, _ = glbtool.read(g, b, A['JOINTS_0']); we, _ = glbtool.read(g, b, A['WEIGHTS_0'])
                vg = jg[jo[np.arange(len(jo)), we.argmax(axis=1)].astype(np.int64)]
                tg = np.where(vg[tri[:, 1]] == vg[tri[:, 2]], vg[tri[:, 1]], vg[tri[:, 0]])
            else:
                tg = np.zeros(len(tri), int)
            mname = g['materials'][p['material']].get('name', '') if 'material' in p else ''
            mats[mname] = True
            for k in range(3):
                sel = tri[tg == k]
                if sel.size == 0: continue
                used, inv = np.unique(sel.reshape(-1), return_inverse=True)
                attrs = {a: v[used] for a, v in arr.items()}
                attrs['POSITION'] = attrs['POSITION'] - offset[k]
                groups[k].append((attrs, inv.astype(np.uint32), mname))
    w = glbtool.Writer()
    for mname in mats: embed_material(w, mname)
    root = w.node('turret')
    w.node('base', mesh=w.mesh('turret_base', groups[0]), parent=root)
    pv = w.node('pivot', pivot, w.mesh('turret_pivot', groups[1]), root)
    gn = w.node('turret_gun', gunp - pivot, w.mesh('turret_gun', groups[2]), pv)
    w.node('muzzle', muzzle - gunp, parent=gn)
    p = os.path.join(MOD, out_rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    w.write(p)
    return out_rel


def embed_material(w, name):
    """An ES2 material as a glTF material with its textures embedded in the GLB (the remake reads the GLB's own materials for
    an item's turret model)."""
    m = es2mat.resolve(name)
    kind = es2mat.classify(m)
    i = w.material(name)
    mat = w.g['materials'][i]
    pbr = mat['pbrMetallicRoughness']
    def image(arr):
        data = _png(_resize(arr))
        while len(w.bin) % 4: w.bin.append(0)
        w.g['bufferViews'].append({'buffer': 0, 'byteOffset': len(w.bin), 'byteLength': len(data)})
        w.bin.extend(data)
        w.g.setdefault('images', []).append({'bufferView': len(w.g['bufferViews']) - 1, 'mimeType': 'image/png'})
        w.g.setdefault('textures', []).append({'source': len(w.g['images']) - 1})
        return {'index': len(w.g['textures']) - 1}
    def img(t):
        f = es2mat.texture_file(t)
        return np.array(Image.open(f).convert('RGBA')) if f else None
    if kind in ('glow', 'field'):
        c, it = es2mat.glow_colour(m)
        pbr['baseColorFactor'] = [0.03, 0.03, 0.03, 1]
        mat['emissiveFactor'] = [min(1.0, v) for v in c]
        mat.setdefault('extensions', {})['KHR_materials_emissive_strength'] = {'emissiveStrength': it}
        w.g.setdefault('extensionsUsed', []).append('KHR_materials_emissive_strength') if 'KHR_materials_emissive_strength' not in w.g.get('extensionsUsed', []) else None
        return
    if kind in ('decal',):
        pbr['baseColorFactor'] = [0, 0, 0, 0]; mat['alphaMode'] = 'MASK'; return
    if kind != 'pbr':
        pbr['baseColorFactor'] = [0.1, 0.1, 0.11, 1]; return
    p = es2mat.plan(m)
    tint = p['tint']
    pbr['baseColorFactor'] = [tint[0] ** 2.2, tint[1] ** 2.2, tint[2] ** 2.2, 1]
    if 'colour' in p:
        a = img(p['colour'][0])
        if a is not None:
            ch = p['colour'][1]
            rgb = a[..., :3] if ch == 'rgb' else np.repeat(a[..., ch:ch + 1], 3, axis=2)
            pbr['baseColorTexture'] = image(rgb)
    if 'normal' in p:
        a = img(p['normal'])
        if a is not None:
            a = a.copy(); a[..., 1] = 255 - a[..., 1]
            mat['normalTexture'] = image(a[..., :3])
    if 'rough' in p or 'metal' in p:
        src = img((p.get('rough') or p.get('metal'))[0])
        if src is not None:
            h, wd = src.shape[:2]
            mr = np.zeros((h, wd, 3), np.uint8)
            if 'rough' in p: mr[..., 1] = img(p['rough'][0])[..., p['rough'][1]]
            else: mr[..., 1] = 128
            if 'metal' in p: mr[..., 2] = img(p['metal'][0])[..., p['metal'][1]]
            pbr['metallicRoughnessTexture'] = image(mr)
            pbr['metallicFactor'] = 1.0; pbr['roughnessFactor'] = 1.0
    else:
        pbr['metallicFactor'] = p.get('metallic', 0.3); pbr['roughnessFactor'] = 1 - p.get('smoothness', 0.5)


# ---- the sounds ---------------------------------------------------------------------------------------------------------

def add_sounds(items):
    """Each item's own fire sound (its ES2 FireSounds / FireSound cue) as fx "shot"."""
    import audio
    if not audio.available(): return 'no sounds (' + audio.unavailable_reason() + ')'
    cues = {}
    for it in items:
        for c in it.get('_cues') or []:
            if c not in cues: cues[c] = audio.cue(c)
    cues = {k: v for k, v in cues.items() if v and v['waves']}
    decoded, tmp = audio.decode({w for c in cues.values() for w, _ in c['waves']})
    made = 0
    try:
        written = {}
        for it in items:
            c = next((cues[x] for x in it.get('_cues') or [] if x in cues), None)
            if not c: continue
            files = []
            for wname, loop in c['waves']:
                if loop or wname not in decoded: continue
                if wname not in written: written[wname] = audio.write(decoded[wname], 'audio/weapons/' + wname)
                files.append(written[wname])
            if files:
                it['fx']['shot'] = files if len(files) > 1 else files[0]
                made += 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return f'{made} weapon sounds'


# ---- everything ---------------------------------------------------------------------------------------------------------

SKIP = re.compile(r'(Base|InstantHit_Base|EmptyLauncher|Dreadnought|Homebase|Turret)$|_Turret_|Dreadnought')


def build():
    """items.json entries (and the hardpoint rules for the ES2 weapon models): [items], [rules]."""
    out = []
    for f in sorted(glob.glob(os.path.join(SRC, 'Blueprints/Equipment/Weapons/BP_Weapon_*.json'))):
        bp = os.path.basename(f)[:-5]
        if SKIP.search(bp): continue
        it = make_item(bp)
        if it: out.append(it)
    # Turret models (one GLB per ES2 mesh) and the turret items.
    models = {}
    for tid, (_, _, mesh, *_r) in TURRETS.items():
        if mesh not in models:
            rel = turret_glb(mesh, f'warships/turrets/{mesh.lower()}.glb')
            if rel: models[mesh] = rel
    turrets = [make_turret(t, models) for t in TURRETS]
    LOG(f'  weapons: {len(out)} ES2 weapons ({sum(1 for i in out if not i["_secondary"])} primaries), {len(turrets)} capital turrets, '
        f'{len(models)} turret models')
    snd = add_sounds(out)
    LOG(f'  {snd}')
    # The hardpoint rules: each primary on its own ES2 weapon model.
    rules = []
    for it in out:
        if not it['_secondary'] and it['_es2model']:
            rules.append({'slot': 'primary', 'model': f'equipment/weapon_{it["_es2model"]:03d}.glb', 'items': ['es2_ships:' + it['id']]})
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    return out + turrets, rules
