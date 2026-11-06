"""EVERSPACE 2's encounters as the ES2 Ships mod's cruise drive encounters (encounters.json; the remake's kinds battle, trap,
stash, depot and highrisk, made after ES2's BP_Encounter_FactionBattle, _Trap, _HiddenStash, _ResourceDepot and
_HighRiskArea; lootdrone after the Cargo Drone, BP_LootDrone, met at ES2's locations; rift after BP_Encounter_Rift, ES2's
Ancient Rifts: the remake's own rift, from rank 5 like ES2's rifts after the story's start, to whose pool of bosses the mod
adds ES2's). Their names are ES2's mission titles
(the loot drone's its HUD name); the weights add to the game's own table (whose weights add to 100),
the riskier ones only in the less secure systems and from a rank on, as ES2 levels its encounters."""

ENCOUNTERS = [
    {'id': 'es2_battle', 'kind': 'battle', 'weight': 8, 'visible': True, 'security': [0, 1, 2], 'name': 'Battle Support'},
    {'id': 'es2_trap', 'kind': 'trap', 'weight': 6, 'visible': True, 'security': [0, 1]},
    {'id': 'es2_stash', 'kind': 'stash', 'weight': 6, 'visible': True, 'name': 'Hidden Stash'},
    {'id': 'es2_depot', 'kind': 'depot', 'weight': 8, 'visible': True, 'security': [0, 1, 2], 'name': 'Resource Depot'},
    {'id': 'es2_highrisk', 'kind': 'highrisk', 'weight': 4, 'visible': True, 'minRank': 6, 'security': [0, 1], 'name': 'High Risk Area'},
    {'id': 'es2_lootdrone', 'kind': 'lootdrone', 'weight': 6, 'visible': True, 'name': 'Cargo Drone'},
    # BP_Encounter_Minesweeper (RegardAsDistressCall, its stuck-freighter task): the remake's minesweeper, mines being a danger
    # only from a rank on and where security is low, as the orbit minefields
    {'id': 'es2_minesweeper', 'kind': 'minesweeper', 'weight': 5, 'visible': True, 'minRank': 4, 'security': [0, 1], 'name': 'Minesweeper'},
    {'id': 'es2_rift', 'kind': 'rift'},   # (the rift's chance and stages are the remake's: the mod only adds its bosses)
]


# ES2's rift bosses (BP_Encounter_Rift's GetBossClassAndLevel: RandomIntegerInRange(0, 7) over this list, so the doubled ones
# twice as often) as the mod's warships (warships.py), each flying for its blueprint's faction (the boss's stage is then
# that race's, its guards too)
RIFT_BOSSES = [('BP_Cultist_Battleship', 'es2_cultist_battleship', 'cultist'), ('BP_Cultist_Battleship', 'es2_cultist_battleship', 'cultist'),
               ('BP_Okkar_Corvette', 'es2_okkar_corvette', 'okkar'), ('BP_Okkar_Corvette', 'es2_okkar_corvette', 'okkar'),
               ('BP_Outlaw_DroneCarrier_Retaliators', 'es2_retaliator_drone_carrier', 'retaliators'),
               ('BP_Outlaw_DroneCarrier', 'es2_drone_carrier', 'outlaw'),
               ('BP_Outlaw_Destroyer_Zurilia', 'es2_zurilia_destroyer', 'zurilia'), ('BP_Outlaw_Destroyer_Zurilia', 'es2_zurilia_destroyer', 'zurilia')]
ES2_RAIDER_HP = 310.0   # the Outlaw raider's hull 200 + armour 50 + shield 60 (npc_leveling.csv): the remake's "raiders"


def rift_bosses():
    """The rift's "bosses": each ES2 boss's hull + armour + shield (npc_leveling.csv) over the raider's; [] without the table."""
    import es2data
    hp = {}
    for r in es2data.rows('npc_leveling.CSV'):
        if len(r) > 7 and r[0].strip():
            vals = [es2data.number(r[i]) or 0.0 for i in (5, 6, 7)]
            hp[r[0].strip()] = sum(vals)
    return [{'ship': f'es2_ships:{sid}', 'raiders': round(hp[bp] / ES2_RAIDER_HP, 2), 'race': f'es2_ships:{race}'}
            for bp, sid, race in RIFT_BOSSES if hp.get(bp)]


def build():
    """encounters.json's entries."""
    out = [dict(e) for e in ENCOUNTERS]
    bosses = rift_bosses()
    for e in out:
        if e['kind'] == 'rift' and bosses: e['bosses'] = bosses
    return out
