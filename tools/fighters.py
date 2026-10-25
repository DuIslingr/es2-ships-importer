"""EVERSPACE 2's enemy fighters and drones for the ES2 Ships mod: NPC traffic of their faction's GoF2 race (Modding.ModTraffic:
ships.json "traffic": { "races" }), never sold, and what the warships' hangars launch.

Each comes from its EVERSPACE 2 blueprint (Blueprints/Pawns/Ships|Drones/BP_*): its mesh components (Base0, a skeletal base, the
G&B fighters' turret dummy; each at its relative place and scale, a child's own entries winning over its parent's), the screen
name its HUD marker shows, and its mesh's sockets: SKT_PW* the guns (slotType 0), SKT_Engine* the exhausts (3), SKT_Booster*
the booster points (5); a mesh without engine sockets gets them from the rear of its hull (warships.rear_engines). Its flame
cards (M_Vehicle_EngineExhaust) get the kit hulls' TEXCOORD_1 (build.flame_across: across each card, main or boost), so
GoF2/ModEngineFlame draws ES2's own exhaust, driven by the ship's speed; engineStyle "es2" adds ES2's NPC engine glow and trail
(Modding.Es2EngineVfx). Materials through es2mat like the warships'.

Factions -> GoF2 races, as the warships: Outlaws (and the Kato Cartel) pirates 8, Okkar Vossk 1, Okkar Prime, the Redeemers and
the Ancients' swarmers the Void 9, Grady & Brunt Midorian 3, the Coalition Terran 0, Freelancers Nivelian 2.

Scale: EVERSPACE 2's metres x 3.6 like the kit fighters (build.SCALE); ModTraffic takes hulls up to 150 m."""
import json, os, re
import numpy as np
import warships, es2mat, jobs, factions

SRC = MOD = None
SCALE = 3.6
LOG = print

# (id, blueprint, race, weight, description); the name is the blueprint's screen name. A drone's weight is half a fighter's.
FIGHTERS = [
    # Outlaws
    ('es2_outlaw_raider', 'BP_Outlaw_Raider', 8, 1.0, 'The Outlaws\' workhorse: an armoured raider with twin guns.'),
    ('es2_outlaw_scout', 'BP_Outlaw_Scout', 8, 1.0, 'A light, nimble Outlaw scout.'),
    ('es2_outlaw_madcap', 'BP_Outlaw_Madcap', 8, 0.8, 'The Outlaw Madcap: fast, fragile and reckless.'),
    ('es2_outlaw_bomber', 'BP_Outlaw_Bomber', 8, 0.7, 'A slow, heavily shielded Outlaw bomber.'),
    ('es2_outlaw_ravager', 'BP_Outlaw_Ravager', 8, 0.8, 'The Outlaw Ravager, an armoured brawler.'),
    ('es2_outlaw_tormentor', 'BP_Outlaw_Tormentor', 8, 0.6, 'The Outlaw Tormentor: the fastest of their fighters.'),
    ('es2_outlaw_viper', 'BP_Outlaw_Viper', 8, 0.6, 'The Outlaw Viper.'),
    ('es2_outlaw_demolisher', 'BP_Outlaw_MineLayer', 8, 0.5, 'An Outlaw mine layer.'),
    ('es2_kato_fighter', 'BP_Kato_Escort', 8, 0.5, 'A fighter of the Kato Clan.'),
    ('es2_outlaw_drone', 'BP_Outlaw_Drone', 8, 0.5, 'An Outlaw combat drone.'),
    ('es2_outlaw_missile_drone', 'BP_Outlaw_Missile_Drone', 8, 0.4, 'An Outlaw drone with missile pods.'),
    ('es2_outlaw_sniper_drone', 'BP_Outlaw_SniperDrone', 8, 0.3, 'An Outlaw sniper drone.'),
    ('es2_outlaw_shield_drone', 'BP_Outlaw_ShieldDrone', 8, 0.3, 'An Outlaw drone that shields its wing.'),
    ('es2_outlaw_detonator_drone', 'BP_Outlaw_DetonatorDrone', 8, 0.3, 'An Outlaw drone packed with explosives.'),
    ('es2_outlaw_webber_drone', 'BP_Outlaw_WebberDrone', 8, 0.3, 'An Outlaw webber drone.'),
    # Okkar
    ('es2_okkar_fighter', 'BP_Okkar_Fighter', 1, 1.0, 'An Okkar fighter.'),
    ('es2_okkar_interceptor', 'BP_Okkar_Interceptor', 1, 0.8, 'An Okkar interceptor.'),
    ('es2_okkar_protector', 'BP_Okkar_HeavyFighter', 1, 0.7, 'The Okkar Protector, their heavy fighter.'),
    ('es2_okkar_skirmisher', 'BP_Okkar_Swarm_Fighter', 1, 0.6, 'A small, very fast Okkar skirmisher.'),
    ('es2_okkar_drone', 'BP_Okkar_Drone', 1, 0.5, 'An Okkar combat drone.'),
    ('es2_okkar_energy_drone', 'BP_Okkar_Energy_Drone', 1, 0.3, 'An Okkar energy drone.'),
    ('es2_okkar_flying_turret', 'BP_Okkar_Flying_Turret', 1, 0.3, 'An Okkar flying turret.'),
    ('es2_okkar_shield_drone', 'BP_Okkar_ShieldChargeDrone', 1, 0.3, 'An Okkar drone that recharges its wing\'s shields.'),
    # Okkar Prime
    ('es2_okkarprime_fighter', 'BP_OkkarPrime_Fighter', 9, 1.0, 'A fighter of the Okkar Prime, the radical Okkar.'),
    ('es2_okkarprime_interceptor', 'BP_OkkarPrime_Interceptor', 9, 0.8, 'An Okkar Prime interceptor.'),
    ('es2_okkarprime_protector', 'BP_OkkarPrime_HeavyFighter', 9, 0.7, 'The Okkar Prime Protector.'),
    ('es2_okkarprime_claw', 'BP_OkkarPrime_Claw', 9, 0.5, 'The Okkar Prime Claw.'),
    ('es2_okkarprime_drone', 'BP_OkkarPrime_Drone', 9, 0.5, 'An Okkar Prime combat drone.'),
    ('es2_okkarprime_stealth_drone', 'BP_OkkarPrime_Stealth_Drone', 9, 0.3, 'An Okkar Prime stealth drone.'),
    # The Redeemers (cultists) and the Ancients' swarmers
    ('es2_redeemer_disciple', 'BP_Cultist_Fighter', 9, 0.8, 'A Redeemer Disciple, the cultists\' fighter.'),
    ('es2_redeemer_crusader', 'BP_Cultist_Heavy', 9, 0.6, 'A Redeemer Crusader, the cultists\' heavy fighter.'),
    ('es2_redeemer_poacher', 'BP_Cultist_Poacher', 9, 0.5, 'A Redeemer Poacher.'),
    ('es2_redeemer_drone', 'BP_Cultist_Drone', 9, 0.3, 'A Redeemer drone.'),
    ('es2_swarmer_fighter', 'BP_AncientSwarmer_Fighter', 9, 0.5, 'A swarmer of the Ancients.'),
    # Grady & Brunt
    ('es2_gb_fighter', 'BP_GB_Fighter', 3, 1.0, 'A Grady & Brunt fighter with its dorsal turret.'),
    ('es2_gb_light_fighter', 'BP_GB_LightFighter', 3, 0.8, 'A Grady & Brunt light fighter.'),
    ('es2_gb_squad_fighter', 'BP_GB_EliteSquad_Fighter', 3, 0.5, 'A fighter of the Grady & Brunt elite squad.'),
    ('es2_gb_antimissile_drone', 'BP_GB_AntiMissileDrone', 3, 0.3, 'A Grady & Brunt anti-missile drone.'),
    # The Coalition and the Freelancers
    ('es2_coalition_fighter', 'BP_Coalition_Fighter', 0, 1.0, 'A Coalition fighter.'),
    ('es2_coalition_guard', 'BP_Freighter_Guard_Ship', 0, 0.6, 'A Coalition fighter guarding the freighters.'),
    ('es2_freelancer', 'BP_Freelancer', 2, 1.0, 'A freelance pilot\'s fighter.'),
    ('es2_freelancer_escort', 'BP_Freelancer_Escort', 2, 0.8, 'A freelance escort fighter.'),
]
# What the warships' hangars launch, by faction (warships.HANGAR_SHIPS).
HANGARS = {'outlaw': ['es2_outlaw_drone', 'es2_outlaw_missile_drone', 'es2_outlaw_raider', 'es2_outlaw_madcap'],
           'gb': ['es2_gb_fighter', 'es2_gb_light_fighter', 'es2_gb_squad_fighter'],
           'okkar': ['es2_okkar_fighter', 'es2_okkar_interceptor', 'es2_okkar_drone'],
           'swarmer': ['es2_swarmer_fighter'],
           'dreadnought': ['es2_outlaw_raider', 'es2_outlaw_ravager', 'es2_outlaw_bomber', 'es2_outlaw_tormentor', 'es2_outlaw_drone']}
# Meshes a blueprint sets where components() doesn't read them (its parent's template records), by blueprint.
MESHES = {'BP_Outlaw_Ravager': 'SK_Fighter_002_c', 'BP_Outlaw_WebberDrone': 'SM_Drone_004', 'BP_GB_AntiMissileDrone': 'SM_Drone_003'}
# Screen names two blueprints share: these get their own.
NAMES = {'es2_outlaw_missile_drone': 'Outlaw Missile Drone', 'es2_coalition_guard': 'Coalition Guard',
         'es2_freelancer_escort': 'Freelancer Escort'}
# Too big for a fighter: a pirate / Void boss's hull (ModTraffic.PickBoss, up to 400 m) at its own size.
BOSSES = {'es2_okkarprime_claw'}
MAX_FIGHTER = 110.0   # Unity metres: a fighter's longest side (ModTraffic takes hulls up to 150 m along the nose)
SKIP_MESHES = ('SM_Hemisphere', 'SM_ShipModule_', 'SM_Sphere', 'EditorSphere')


def configure(src, mod, log=print):
    global SRC, MOD, LOG
    SRC, MOD, LOG = src, mod, log
    warships.configure(src, mod, log)


def screen_name(bp):
    """The blueprint's (or a parent's) HUD marker screen name."""
    n, seen = bp, set()
    while n and n not in seen:
        seen.add(n)
        for e in warships._bp(n) or []:
            if e.get('Type') == 'HUDMarkerComponent':
                v = (e.get('Properties') or {}).get('ScreenName')
                if isinstance(v, dict) and (v.get('SourceString') or v.get('CultureInvariantString')):
                    return v.get('SourceString') or v.get('CultureInvariantString')
        n = warships._super(n)
    return None


def parts(bp):
    """The blueprint's meshes: [(Vehicles/... path, loc cm, rot, scale)] for the components that draw the ship."""
    if bp in MESHES:
        rel = mesh_index().get(MESHES[bp])
        return [(rel, [0, 0, 0], None, 1.0)] if rel else []
    out = []
    for cname, cls, mesh, loc, rot, sc in warships.components(bp):
        if not mesh or any(s in mesh for s in SKIP_MESHES): continue
        if 'JumpCharge' in cname or 'Cockpit' in cname: continue
        rel = mesh_index().get(mesh.split('/')[-1].split('.')[0])
        if not rel: continue
        out.append((rel, loc or [0, 0, 0], rot, sc or 1.0))
    return out


_index = None
def mesh_index():
    """Every vehicle mesh of the export by name: {name: Vehicles/... path without .glb}."""
    global _index
    if _index is None:
        _index = {}
        root = os.path.join(SRC, 'Assets/Vehicles')
        for base, _, files in os.walk(root):
            for f in files:
                if f.endswith('.glb'): _index.setdefault(f[:-4], os.path.relpath(os.path.join(base, f[:-4]), root))
    return _index


def place(prims, loc_cm, scale):
    """A component's primitives moved to its place (Unreal cm -> the export's glTF metres (X, Z, Y)) at its scale."""
    t = np.array([loc_cm[0], loc_cm[2], loc_cm[1]], np.float32) / 100.0
    return [({**a, 'POSITION': a['POSITION'] * scale + t}, i, n) for a, i, n in prims]


def flame_uv1(attrs, tri):
    """build.flame_across for a primitive read by warships.read_prims: TEXCOORD_1 = (across each flame card, 0.5 main /
    0.25 boost by its vertex colours)."""
    pos, uv = attrs['POSITION'].astype(np.float64), attrs['TEXCOORD_0'].astype(np.float64)
    parent = np.arange(len(pos))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, c in tri:
        ra, rb, rc = find(a), find(b), find(c); parent[rb] = ra; parent[find(rc)] = ra
    roots = np.array([find(i) for i in range(len(pos))])
    col = attrs.get('COLOR_0')
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
        boost = col is not None and col[c, 1].mean() > 0.5 and col[c, 0].mean() < 0.5
        out[c, 1] = 0.25 if boost else 0.5
    return out


def build_one(sid, bp, race, weight, desc):
    ps = parts(bp)
    if not ps: warships.say(f'  {bp}: no mesh found'); return None
    name = NAMES.get(sid) or screen_name(bp) or sid.replace('es2_', '').replace('_', ' ').title()
    prims, socks = [], []
    for rel, loc, rot, sc in ps:
        pr = warships.read_prims(os.path.join(SRC, 'Assets/Vehicles', rel + '.glb'))
        for a, i, n in pr:
            if 'EngineExhaust' in n and 'TEXCOORD_0' in a: a['TEXCOORD_1'] = flame_uv1(a, i)
        prims += place(pr, loc, sc)
        socks += [(s, [loc[0] + l[0] * sc, loc[1] + l[1] * sc, loc[2] + l[2] * sc], k * sc) for s, l, k in warships.sockets(rel)]
    mn, mx = warships.bounds(prims)
    size = mx - mn
    boss = sid in BOSSES
    f = min(SCALE, (380.0 if boss else MAX_FIGHTER) / float(size.max()))
    mats_used = {}
    out = warships.split_prims(f'{sid}_', prims, mats_used)
    # (a primitive without flame cards has no TEXCOORD_1: give every one the same attributes, "none" for the rest)
    for a, i, n in out:
        if 'TEXCOORD_1' not in a and 'TEXCOORD_0' in a: a['TEXCOORD_1'] = np.zeros((len(a['POSITION']), 2), np.float32)
    rel_out = f'fighters/{sid}.glb'
    warships.write_glb(rel_out, out)
    mounts = []
    for s, loc, k in socks:
        if re.match(r'SKT_PW', s, re.I): mounts.append({'slotType': 0, 'position_engine': warships.ue_to_game(loc, f)})
        elif re.match(r'SKT_Engine', s, re.I): mounts.append({'slotType': 3, 'position_engine': warships.ue_to_game(loc, f), 'socketScale': round(k * f / SCALE, 3)})
        elif re.match(r'SKT_Booster', s, re.I): mounts.append({'slotType': 5, 'position_engine': warships.ue_to_game(loc, f), 'socketScale': round(k * f / SCALE, 3)})
    if not any(m['slotType'] == 3 for m in mounts):
        for pos, r in warships.rear_engines(prims, f, n=2):
            mounts.append({'slotType': 3, 'position_engine': pos, 'socketScale': round(r * f / SCALE, 3)})
    if not any(m['slotType'] == 0 for m in mounts):   # a gun on the nose
        mounts.append({'slotType': 0, 'position_engine': warships.ue_to_game([float(mx[0]) * 100, 0, 0], f)})
    drone = 'Drone' in bp or 'Turret' in bp
    fac = factions.for_ship(sid, bp, race)   # its ES2 faction (factions.py), never a GoF2 race
    length = float(size[0]) * f / 0.05
    ship = {'id': sid, 'name': name, 'description': desc + ' An EVERSPACE 2 ' + ('drone' if drone else 'fighter') + ', flown only by the NPCs.',
            'race': fac, 'armor': 120 if drone else 300, 'cargo': 0, 'handling': 120, 'price': 0,
            'slots': {'primary': 1, 'secondary': 0, 'turret': 0, 'equipment': 0},
            'model': rel_out, 'modelLength': round(length), 'modelYaw': 90, 'engineStyle': 'es2',
            'hangarHeight': round(max(0.0, -float(mn[1])) * f / 0.05 + 20),
            'mounts': mounts, 'materials': warships.material_entries(sid, mats_used),
            'traffic': {'races': [fac], 'weight': weight, **({'boss': True} if boss else {})},
            'explosionScale': round(min(3.0, max(0.6, float(size.max()) * f / 50.0)), 2)}
    effects = warships.engine_effects(bp)
    if effects: ship['es2Engine'] = effects
    tris = sum(len(i) // 3 for _, i, _ in out)
    return ship, name, round(float(size.max()) * f), tris, len(mounts)


def build(log=print):
    """ships.json entries for the enemy fighters and drones; also points the warships' hangars at them."""
    os.makedirs(os.path.join(MOD, 'fighters'), exist_ok=True)
    ships = []
    mesh_index()
    # on the workers (jobs.run), printed in the table's order
    for (r, lines) in jobs.run(lambda e: warships.logged(build_one, *e), FIGHTERS):
        for l in lines: LOG(l)
        if not r: continue
        ships.append(r[0])
        LOG(f'  {r[1]}: {r[2]} m, {r[3]} triangles, {r[4]} mounts')
    made = {s['id'] for s in ships}
    for k, ids in HANGARS.items():
        use = ['es2_ships:' + i for i in ids if i in made]
        if use: warships.HANGAR_SHIPS[k] = use
    return ships
