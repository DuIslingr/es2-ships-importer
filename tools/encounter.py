"""The Dreadnought's raids: an Outlaw Dreadnought of EVERSPACE 2 turns up now and then somewhere in the galaxy, raiding a
convoy for its cargo, and the player drives it off. A story mission of the mod (events/es2_dreadnought.gof2mission) behind a
gameplay setting (gameoptions.json "setting": Options > Gameplay "Dreadnought raids", only while the mod is on):
- it starts at a random moment (startsWhen: the setting on, rank 5 or more, a 1 in RANDOM_SECONDS chance each second) at a
  random station of a system on the map (randomstation()); Brent Snocom calls the player and the station is marked on the map
  (target); the raid waits there, however long it takes, until the player flies into that orbit (a checkpoint keeps the place
  through saves);
- there the Dreadnought holds a convoy of EVERSPACE 2 freighters under its guns, fought in EVERSPACE 2's encounter's stages
  (BP_Encounter_Dreadnought_*: its energy fields first, its gun decks, then its weak points) on the remake's capital ship
  subsystems (warships.build_dreadnought): the hull takes no damage while its field emitters and shield generator stand; the
  sniper and lightning turrets can't be harmed before them, the explosive weak points not before those; its hangars launch
  fighters and its flak and missile batteries fire throughout. The player can't jump or dock away during the fight (ES2's
  encounter fails a player who leaves; here the way out is the fight);
- as in EVERSPACE 2 it is never destroyed: its hull depleted (BP_Encounter_Dreadnought_Base's OnHealthDepleted), its fighters
  jump out and it jumps away (ships.json "retreat": the remake's CapitalRetreat, a Khador jump of its size), which pays
  credits and a legendary ES2 weapon's ammunition (ES2's loot drone);
- like ES2's repeatable Dreadnought Signature it comes again ("repeat": REPEAT_MINUTES of playing time later, then at a random
  moment again)."""
import json, os

REPEAT_MINUTES = 90
RANDOM_SECONDS = 300          # once the setting allows it: a 1 in this chance each second (about 5 minutes on average)
SETTING = 'dreadnought_raids'
SPEAKER = 'Brent Snocom'
CONVOY = ['es2_ships:es2_gb_freighter', 'es2_ships:es2_freelancer_freighter']


def build(mod):
    here = '{stationname(st)} in the {systemname(st)} system'
    mission = {
        'format': 'gof2mission', 'title': 'Dreadnought Raid', 'kind': 'quest',
        'startsWhen': f'option(es2_ships:{SETTING}) and rank >= 5 and random(1, {RANDOM_SECONDS}) == 1',
        'repeat': REPEAT_MINUTES,
        'variables': [{'name': 'st', 'value': -1}],
        'steps': [
            {'type': 'set', 'variable': 'st', 'value': 'randomstation()'},
            {'type': 'if', 'condition': 'st < 0', 'then': [{'type': 'stop'}]},
            {'type': 'dialog', 'pages': [
                {'speaker': SPEAKER, 'text': f'Keith, this is Brent! An Outlaw Dreadnought just jumped in at {here}. They\'re attacking '
                                              'a convoy and taking the whole shipment.'},
                {'speaker': SPEAKER, 'text': 'I\'ve marked the position on your star map. That fortress isn\'t going anywhere until '
                                              'somebody makes it leave. Get over there as fast as you can!'},
            ]},
            {'type': 'objective', 'text': f'Drive the Outlaw Dreadnought away from the convoy at {here}', 'station': '{st}'},
            {'type': 'checkpoint', 'name': 'called'},
            {'type': 'waituntil', 'condition': 'inorbit({st}) > 0'},
            {'type': 'wait', 'seconds': 3},
            # the convoy holds 4-5 km short of the Dreadnought, out of its turrets' reach (its fighters harry them)
            {'type': 'spawn', 'ship': CONVOY[0], 'count': 1, 'race': 'es2_ships:gb', 'behaviour': 'friendly', 'name': 'Convoy', 'at': '9000 20000 80000'},
            {'type': 'spawn', 'ship': CONVOY[1], 'count': 1, 'race': 'es2_ships:gb', 'behaviour': 'friendly', 'name': 'Convoy', 'at': '-9000 24000 75000'},
            {'type': 'shipaction', 'ship': 'Convoy', 'action': 'hold'},
            {'type': 'spawn', 'ship': 'es2_ships:es2_dreadnought', 'count': 1, 'race': 'es2_ships:outlaw', 'behaviour': 'enemy',
             'name': 'Dreadnought', 'at': '0 25000 165000'},
            # (a Dreadnought that didn't come: nothing to fight, so nothing won; the raid comes again later)
            {'type': 'waituntil', 'condition': 'alive("Dreadnought") > 0', 'timeout': 30},
            {'type': 'if', 'condition': 'alive("Dreadnought") == 0', 'then': [{'type': 'target', 'station': 'off'}, {'type': 'stop'}]},
            {'type': 'restrict', 'what': 'all'},
            {'type': 'music', 'track': 'boss'},
            {'type': 'title', 'title': 'Dreadnought', 'subtitle': 'An Outlaw raid on a convoy', 'seconds': 5},
            {'type': 'wait', 'seconds': 4},
            {'type': 'dialog', 'pages': [
                {'speaker': SPEAKER, 'text': 'There it is. Nothing gets through those energy fields, Keith. Take out the field emitters '
                                              'on the bow and the shield generator on its flank, then the hull is open.'},
                {'speaker': SPEAKER, 'text': 'Watch out for its hangars. And keep moving! Those flak batteries don\'t miss a sitting target.'},
            ]},
            {'type': 'objective', 'text': 'Destroy the Dreadnought\'s field emitters and its shield generator', 'station': '{st}'},
            {'type': 'waituntil', 'condition': 'alive("Field emitter") + alive("Shield generator") == 0'},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'The fields are down! Now hit its gun decks: the torpedo launchers, the snipers and '
                                                          'the lightning turrets!'},
            {'type': 'objective', 'text': 'Destroy the torpedo launchers, the sniper turrets and the lightning turrets', 'station': '{st}'},
            {'type': 'waituntil', 'condition': 'alive("Torpedo launcher") + alive("Sniper turret") + alive("Lightning turret") == 0'},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'Its reactor lines are exposed! Hit the weak points under the hull. Every one of them '
                                                          'takes a bite out of it!'},
            {'type': 'objective', 'text': 'Hit the weak points until the Dreadnought breaks off', 'station': '{st}'},
            {'type': 'waituntil', 'condition': 'alive("Dreadnought") == 0'},
            {'type': 'restrict', 'what': 'off'},
            {'type': 'music', 'track': 'stop'},
            {'type': 'target', 'station': 'off'},
            {'type': 'wait', 'seconds': 4},
            {'type': 'radio', 'speaker': SPEAKER, 'text': 'Dammit, it jumped out! But that thing won\'t be raiding anybody for a while. Well '
                                                          'done, Keith. I transferred 150,000 Credits to your account.'},
            {'type': 'reward', 'credits': 150000,
             'items': [{'item': 'es2_ships:legendary_swarmmissilelauncher', 'amount': 10}],
             'title': 'Dreadnought driven off'},
            {'type': 'complete'},
        ],
    }
    os.makedirs(os.path.join(mod, 'events'), exist_ok=True)
    json.dump(mission, open(os.path.join(mod, 'events', 'es2_dreadnought.gof2mission'), 'w', encoding='utf-8'), indent=1)
    options = [{'id': SETTING, 'setting': True, 'default': True, 'name': 'Dreadnought raids',
                'description': 'Now and then an Outlaw Dreadnought of EVERSPACE 2 raids a convoy somewhere in the galaxy: Brent '
                               'Snocom calls you and marks it on the map, and it waits there until you drive it off.'}]
    json.dump(options, open(os.path.join(mod, 'gameoptions.json'), 'w', encoding='utf-8'), indent=1)
    return 'events/es2_dreadnought.gof2mission, gameoptions.json'
