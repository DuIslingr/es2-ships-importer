"""EVERSPACE 2's encounters as the ES2 Ships mod's cruise drive encounters (encounters.json; the remake's kinds battle, trap,
stash, depot and highrisk, made after ES2's BP_Encounter_FactionBattle, _Trap, _HiddenStash, _ResourceDepot and
_HighRiskArea). Their names are ES2's mission titles; the weights add to the game's own table (whose weights add to 100),
the riskier ones only in the less secure systems and from a rank on, as ES2 levels its encounters."""

ENCOUNTERS = [
    {'id': 'es2_battle', 'kind': 'battle', 'weight': 8, 'visible': True, 'security': [0, 1, 2], 'name': 'Battle Support'},
    {'id': 'es2_trap', 'kind': 'trap', 'weight': 6, 'visible': True, 'security': [0, 1]},
    {'id': 'es2_stash', 'kind': 'stash', 'weight': 6, 'visible': True, 'name': 'Hidden Stash'},
    {'id': 'es2_depot', 'kind': 'depot', 'weight': 8, 'visible': True, 'security': [0, 1, 2], 'name': 'Resource Depot'},
    {'id': 'es2_highrisk', 'kind': 'highrisk', 'weight': 4, 'visible': True, 'minRank': 6, 'security': [0, 1], 'name': 'High Risk Area'},
]


def build():
    """encounters.json's entries."""
    return [dict(e) for e in ENCOUNTERS]
