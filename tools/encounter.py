"""The Dreadnought's encounter at Herjaza (station 101), the Valkyrie's anchorage: once the Valkyrie add-on's story is over
(the battlestation gone from the orbit, OrbitLayout.IsEmptyOrbit from step 0x54), an Outlaw Dreadnought of EVERSPACE 2 jumps
in when the player comes there. A story mission of the mod (events/es2_dreadnought.gof2mission), in EVERSPACE 2's encounter's
stages (BP_Encounter_Dreadnought_*: its energy fields first, its gun decks, then its weak points), on the remake's capital ship
subsystems (warships.build_dreadnought): the hull takes no damage while its field emitters and shield generator stand; the
sniper and lightning turrets can't be harmed before them, the explosive weak points not before those; its hangars launch
fighters and its flak and missile batteries fire throughout. The player can't jump or dock away during the fight (ES2's
encounter fails a player who leaves; here the way out is the fight). Its destruction pays credits and a legendary ES2 weapon."""
import json, os

HERJAZA = 101
SPEAKER = 'terran male Wing Commander Hale'


def build(mod):
    mission = {
        'format': 'gof2mission', 'title': 'The Dreadnought', 'kind': 'quest',
        'startsWhen': f'(campaign >= 84 or won(valkyrie)) and inorbit({HERJAZA})',
        'steps': [
            {'type': 'wait', 'seconds': 6},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'All pilots near Herjaza: a jump signature where the Valkyrie used to anchor. '
                                                          'Big. Outlaw make. It\'s a Dreadnought.'},
            {'type': 'spawn', 'ship': 'es2_ships:es2_dreadnought', 'count': 1, 'race': 'pirate', 'behaviour': 'enemy',
             'name': 'Dreadnought', 'at': '0 25000 150000'},
            {'type': 'restrict', 'what': 'all'},
            {'type': 'music', 'track': 'boss'},
            {'type': 'title', 'title': 'Dreadnought', 'subtitle': 'An Outlaw fortress at the Valkyrie\'s anchorage', 'seconds': 5},
            {'type': 'wait', 'seconds': 4},
            {'type': 'dialog', 'pages': [
                {'speaker': SPEAKER, 'text': 'Nothing gets through those energy fields. Its field emitters are on the bow, the shield '
                                              'generator on its flank: take them out and the hull is open.'},
                {'speaker': SPEAKER, 'text': 'Watch its hangars. And keep moving: those flak batteries don\'t miss a sitting target.'},
            ]},
            {'type': 'objective', 'text': 'Destroy the Dreadnought\'s field emitters and its shield generator', 'station': HERJAZA},
            {'type': 'waituntil', 'condition': 'alive("Field emitter") + alive("Shield generator") == 0'},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'The fields are down! Now its gun decks: the torpedo launchers, the snipers and '
                                                          'the lightning turrets.'},
            {'type': 'objective', 'text': 'Destroy the torpedo launchers, the sniper turrets and the lightning turrets', 'station': HERJAZA},
            {'type': 'waituntil', 'condition': 'alive("Torpedo launcher") + alive("Sniper turret") + alive("Lightning turret") == 0'},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'Its reactor lines are exposed. Hit the explosive weak points under the hull, '
                                                          'every one of them takes a bite out of it!'},
            {'type': 'objective', 'text': 'Hit the weak points and destroy the Dreadnought', 'station': HERJAZA},
            {'type': 'waituntil', 'condition': 'alive("Dreadnought") == 0'},
            {'type': 'restrict', 'what': 'off'},
            {'type': 'music', 'track': 'stop'},
            {'type': 'wait', 'seconds': 4},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'Confirmed: the Dreadnought is gone. Herjaza owes you one, pilot. '
                                                          'We pulled something out of its wreck for you.'},
            {'type': 'reward', 'credits': 250000,
             'items': [{'item': 'es2_ships:railgun_legendary_damageboost', 'amount': 1},
                       {'item': 'es2_ships:legendary_swarmmissilelauncher', 'amount': 20}],
             'title': 'Dreadnought destroyed'},
            {'type': 'complete'},
        ],
    }
    os.makedirs(os.path.join(mod, 'events'), exist_ok=True)
    json.dump(mission, open(os.path.join(mod, 'events', 'es2_dreadnought.gof2mission'), 'w', encoding='utf-8'), indent=1)
    return 'events/es2_dreadnought.gof2mission'
