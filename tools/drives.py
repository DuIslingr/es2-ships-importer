"""The cruise drives (items.json), the Slipstream II's blueprint (blueprints.json) and the warp flight's look and sound
(warp.json, warp/): the remake's rules ("Cruise drives" in its Modding/README.md) on EVERSPACE 2's travel mode.

The Khador Slipstream cruises inside an orbit and is sold in shops. Its successor, the Slipstream II, is only made from a
blueprint (never stocked, like the Khador Drive): mounted, it also flies the space between the systems. Its recipe takes
the first drive and ES2's rarest resources (sectors.RESOURCES: mined in the sectors, so the part needs them) with the
Khador Drive's goods, and costs more than a Khador Drive to make in both of the remake's economies (tests/test_drives.py).
Energy cells stay the game's own: a leg is one cell, and between the systems a leg is the average gate hop, a Khador jump's
price; nothing here touches the economy.
research/warp_effects.md lists what each effect is made of: M_TravelMode_WarpTunnel's noise and sparks are the tunnel's three
layers, S_Hyperspeed_Loop_002 its loop, S_Transition_To_Hyperspeed_Init_001 the moment it engages."""
import json
import os
import shutil

from PIL import Image

import icons
import sectors

SRC = MOD = None
LOG = print

# The tunnel's layers (warp.json key, the effect's texture); the remake's GoF2/WarpTunnel reads their red channel.
LAYERS = [('tunnel', 'T_Noise_001_M'), ('detail', 'T_Noise_013_M'), ('streaks', 'T_Pattern_MotionBlurSparks_001')]
LAYER_SIZE = 1024
TEXTURES = 'Assets/Shared/Textures/Effects'
SOUNDS = [('loop', 'S_Hyperspeed_Loop_002'), ('enter', 'S_Transition_To_Hyperspeed_Init_001')]
TINT = '#8cd0ff'

KHADOR, ENERGY_CELLS, VOID_CRYSTALS, HYPANIUM, ELECTRONICS, MICROCHIPS, OPTICS = 85, 122, 164, 163, 118, 127, 129
FIRST, SECOND = 'es2_slipstream', 'es2_slipstream_ii'
ICON, SECOND_ICON = 'icon_perk_engineer_mentor_cruisedrive_62x62_2x', 'icon_device_energized_boost_86x86_2x'

# (ES2 resource, amount): the superior and rare ores and crystals, sectors.RESOURCES' ids
ORES = [('glacit', 60), ('coruscate', 60), ('baromite', 120), ('clygon', 120), ('phazium', 100), ('mallemite', 150)]
# (the game's item, amount): the Khador Drive's goods
GOODS = [(VOID_CRYSTALS, 80), (HYPANIUM, 40), (ELECTRONICS, 150), (MICROCHIPS, 200), (OPTICS, 160), (ENERGY_CELLS, 200)]

# Where its blueprint is found: a wreck in ES2's mining grounds, where the recipe's ores are; a bar anywhere sells it now and
# then. Past the point the story gives the Khador Drive's own blueprint (34), or at once in free play (-1).
AVAILABLE = 'campaign >= 34 or campaign < 0'
WRECK_ORBIT = 'es2_ships:es2_gb_mining_grounds'
LOUNGE = {'chance': 4, 'price': 400000}


def configure(src, mod):
    global SRC, MOD
    SRC, MOD = src, mod


def items():
    """items.json's two drives (their icons made), each based on the Khador Drive."""
    out = [
        {'id': FIRST, 'base': KHADOR, 'name': 'Khador Slipstream',
         'description': 'A cut-down Void crystal array on the Khador Drive\'s pattern. Too weak to fold space between the '
                        'stars, it folds it a little: the ship slips through the orbit at several times its speed as long '
                        'as the pilot holds the charge, paying in energy cells. Anything solid ahead, a locked destination '
                        'close by or a fight breaks the slipstream.',
         'techLevel': 7, 'occurrence': 25, 'price': [148000, 162800],
         'stats': {'cruiseSpeed': 400, 'cruiseRange': 60000, 'cruiseChargeMs': 2000, 'energyCells': 1},
         '_icon': ICON, '_frame': 'equipment'},
        {'id': SECOND, 'base': KHADOR, 'name': 'Slipstream II',
         'description': 'The Slipstream rebuilt around crystals no shop sells. It holds the fold open: the charge carries the '
                        'ship out of the system into the dark between the stars, where every system on the map can be flown '
                        'to, an energy cell for each gate hop of the way. Inside an orbit it is simply a faster Slipstream.',
         'techLevel': 10, 'occurrence': 0, 'price': [1150000, 1265000],
         'stats': {'cruiseSpeed': 800, 'cruiseRange': 90000, 'cruiseChargeMs': 1500, 'energyCells': 1, 'interstellar': 1},
         '_icon': SECOND_ICON, '_frame': 'equipment'},
    ]
    icons.apply(out, MOD)
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    return out


def blueprints():
    """blueprints.json: the Slipstream II's. No autocomplete: the ores have to be fetched."""
    ingredients = [{'item': f'es2_ships:{FIRST}', 'amount': 1}]
    ingredients += [{'item': f'es2_ships:es2_{key}', 'amount': n} for key, n in ORES]
    ingredients += [{'item': item, 'amount': n} for item, n in GOODS]
    return [{'id': SECOND, 'item': f'es2_ships:{SECOND}', 'ingredients': ingredients, 'autocomplete': False, 'available': AVAILABLE,
             'lounge': dict(LOUNGE), 'derelict': {'stations': [WRECK_ORBIT]}}]


def warp():
    """warp/ and warp.json's entries: the layers that are in the export, then the sounds when they can be decoded."""
    out = {'tint': TINT}
    os.makedirs(os.path.join(MOD, 'warp'), exist_ok=True)
    for key, name in LAYERS:
        src = os.path.join(SRC, TEXTURES, name + '.png')
        if not os.path.exists(src):
            LOG(f'  no {name} in the export (tools/warp_assets.txt): the game makes that layer itself')
            continue
        img = Image.open(src).convert('RGBA').getchannel('R')
        if max(img.size) > LAYER_SIZE: img = img.resize((LAYER_SIZE, LAYER_SIZE), Image.LANCZOS)
        img.save(os.path.join(MOD, 'warp', key + '.png'), optimize=True)
        out[key] = f'warp/{key}.png'
    import audio
    if audio.available():
        waves, tmp = audio.decode([name for _, name in SOUNDS])
        for key, name in SOUNDS:
            if name in waves: out[key] = audio.write(waves[name], f'warp/{key}')
            else: LOG(f'  no {name}: the warp flight goes without that sound')
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def build(log=print):
    """Writes blueprints.json and warp.json and the warp folder. Returns the items for items.json."""
    global LOG
    LOG = log
    out = items()
    json.dump(blueprints(), open(os.path.join(MOD, 'blueprints.json'), 'w', encoding='utf-8'), indent=1)
    look = warp()
    json.dump(look, open(os.path.join(MOD, 'warp.json'), 'w', encoding='utf-8'), indent=1)
    known = {key for key, *_ in sectors.RESOURCES}
    for key, _ in ORES:
        if key not in known: raise ValueError(f'the recipe names {key}, not one of sectors.RESOURCES')
    LOG(f'  drives: {len(out)} items, the Slipstream II\'s blueprint, warp: {", ".join(k for k in look if k != "tint") or "no art"}')
    return out
