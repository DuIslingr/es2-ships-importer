"""EVERSPACE 2's bosses as the ES2 Ships mod's Most Wanted criminals (wanted.json: the remake's Most Wanted boards, Modding/
README.md "Most Wanted"): each flies its own boss hull (fighters.py's BOSSES), roams the sectors its faction raids in ES2
(systems.json's "raiders"), with ES2's gun on it (its blueprint's, else its parent's: the mod's weapon of that family) and its
ES2 drop as its loot.

Strength and bounty: the boards take fixed numbers, on their own scale: the game's 25 criminals have 5000-10000 hit points
on top of the criminal bonus and pay 50,000-140,000. The ES2 bosses are placed on that range by their hit points in ES2
(npc_leveling.csv: hull + armour + shield), the weakest at the bottom and the strongest at the top; they come in that order
(requiredBounties) with as many escorts as their place (0-4, as the game's boards go), fighters of their faction.

Their fight kit (KIT, wanted.json "devices", read from their blueprints with es2_re/kismet.py, 2026-11-05): GoF2's NPCs
have hull only, so ES2's "shield depleted" / "armour depleted" phases are the remake's "hullBelow" 66 / 33 %; the drones
that keep a boss's energy shield up are the remake's shield drones ("minions"), its armour drones (ES2's armour link:
three quarters of the hits) minions that stop 75 %, its proximity mines the "bombSpreader". The Claw has no kit of its own
(it docks out of its carrier and blasts when its armour goes), the Outlaw Leader's charged laser beam no remake device."""
import es2data

# ship id (fighters.py), blueprint (npc_leveling.csv), faction (systems.json raiders, its race), gun, missiles, loot (item,
# amount), escorts
BOSSES = [
    ('es2_okkarprime_claw', 'BP_OkkarPrime_Claw', 'okkar_prime', 'gausscannon_okkar', None, ('es2_resources_okkar_special', 2),
     ['es2_okkarprime_fighter', 'es2_okkarprime_interceptor']),
    ('es2_outlaw_trapper', 'BP_Outlaw_Zero_Boss', 'outlaw', 'coilgun', None, None, ['es2_outlaw_raider', 'es2_outlaw_scout']),
    ('es2_bloodstar_chief', 'BP_Outlaw_Bomber_OutlawChief', 'outlaw', 'scattergun', 'homingmissilelauncher', None,
     ['es2_outlaw_bomber', 'es2_outlaw_raider']),
    ('es2_bloodstar_overseer', 'BP_Outlaw_Ravager_Bloodstar', 'outlaw', 'autocannon_bloodstar', None, ('scattergun_bloodstar', 1),
     ['es2_outlaw_ravager', 'es2_outlaw_raider']),
    ('es2_outlaw_leader', 'BP_Outlaw_Ravager_Boss', 'outlaw', 'blaster', None, None, ['es2_outlaw_ravager', 'es2_outlaw_tormentor']),
]
FACTION = {'outlaw': 'Outlaw', 'okkar_prime': 'Okkar Prime'}
LONG = 600000   # (ms: a phase that lasts the fight, the remake's longest run)
KIT = {
    # BP_Outlaw_Zero_Boss: OnShieldDepleted -> its BP_FrontShield ActivateShield and BP_Okkar_ShieldChargeDrones over a
    # timeline; OnArmorDepleted -> DeactivateShield and BP_Outlaw_ArmorDrones (the armour link); CanDoBarrelRoll false
    'es2_outlaw_trapper': [
        {'type': 'frontShield', 'hullBelow': 66, 'durationMs': 20000, 'cooldownMs': 5000},
        {'type': 'minions', 'hullBelow': 66, 'count': 3, 'durationMs': LONG, 'cooldownMs': LONG},
        {'type': 'minions', 'hullBelow': 33, 'count': 3, 'blockPercent': 75, 'durationMs': LONG, 'cooldownMs': LONG}],
    # BP_Outlaw_Bomber_OutlawChief: SpawnChiefDrones (OutlawDroneMin..Max 1-2) holding BP_Condition_Buff_EnergyShield on it,
    # spawned again 20 s after they are gone; Phase2Percentage 0.4 brings more
    'es2_bloodstar_chief': [
        {'type': 'minions', 'count': 2, 'durationMs': 40000, 'cooldownMs': 20000},
        {'type': 'minions', 'hullBelow': 40, 'count': 2, 'durationMs': 40000, 'cooldownMs': 20000}],
    # BP_Outlaw_Ravager_Bloodstar: a BP_ProximityMine_Base (Radius 10000, armed after 1 s, MineLifeSpan 9-11 s) every 1-4 s
    # while it boosts
    'es2_bloodstar_overseer': [
        {'type': 'bombSpreader', 'bombEveryMs': 2500, 'durationMs': 10000, 'cooldownMs': 8000}],
    # BP_Outlaw_Ravager_Boss: ActivatePhase2 spawns drones 3-3.5 s apart that give it BP_Condition_Buff_EnergyShield
    'es2_outlaw_leader': [
        {'type': 'minions', 'hullBelow': 50, 'count': 3, 'durationMs': LONG, 'cooldownMs': 30000}],
}
# the board's face of a race (portraitParts' first): the Outlaws are human (terran), the Okkar the Vossk's look (no GoF2 face
# is theirs)
FACE = {'outlaw': 0, 'okkar_prime': 1}
HULL = (5000, 10000)       # the game's criminals' hit points ...
REWARD = (50000, 140000)   # ... and bounties


def es2_hitpoints():
    """{blueprint: hull + armour + shield} from npc_leveling.csv."""
    out = {}
    for r in es2data.rows('npc_leveling.CSV'):
        if len(r) > 7 and r[0].strip():
            out[r[0].strip()] = sum(es2data.number(r[i]) or 0.0 for i in (5, 6, 7))
    return out


def build(ships, systems, items):
    """wanted.json's entries: 'ships' the mod's ships.json entries, 'systems' its systems.json, 'items' its item ids."""
    hp = es2_hitpoints()
    have = {s['id']: s for s in ships}
    rows = [b for b in BOSSES if b[0] in have and hp.get(b[1])]
    if not rows: return []
    rows.sort(key=lambda b: hp[b[1]])
    lo, hi = hp[rows[0][1]], hp[rows[-1][1]]
    out = []
    for i, (sid, bp, faction, gun, missiles, loot, escorts) in enumerate(rows):
        share = (hp[bp] - lo) / (hi - lo) if hi > lo else 0.0
        where = [f"es2_ships:{s['id']}" for s in systems if f'es2_ships:{faction}' in (s.get('raiders') or [])]
        text = f"An EVERSPACE 2 {FACTION[faction]} boss in its own ship, {int(hp[bp])} hit points in ES2 (hull, armour and shield)."
        e = {'id': sid, 'name': have[sid]['name'], 'description': text, 'race': f'es2_ships:{faction}', 'ship': f'es2_ships:{sid}',
             'portraitParts': [FACE[faction], 0, 0, 0, 0],
             'hitpoints': int(round((HULL[0] + share * (HULL[1] - HULL[0])) / 500.0) * 500),
             'reward': int(round((REWARD[0] + share * (REWARD[1] - REWARD[0])) / 5000.0) * 5000),
             'requiredBounties': i, 'wingmen': min(i, 4)}
        if gun in items: e['weapon'] = f'es2_ships:{gun}'
        if missiles in items: e['secondary'] = f'es2_ships:{missiles}'
        if loot and loot[0] in items: e['loot'], e['lootAmount'] = f'es2_ships:{loot[0]}', loot[1]
        esc = [f'es2_ships:{x}' for x in escorts if x in have]
        if esc and e['wingmen']: e['escorts'] = esc
        if where: e['systems'] = where
        if KIT.get(sid): e['devices'] = [dict(d) for d in KIT[sid]]
        out.append(e)
    return out
