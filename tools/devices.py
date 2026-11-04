"""EVERSPACE 2's devices (the ships' ULTs and the special abilities) and consumables as the ES2 Ships mod's items (items.json).

A mod can't add code, so each becomes a mod item "based on" the Galaxy on Fire 2 equipment or secondary that does most nearly
what it does in EVERSPACE 2, with numbers of its own on GoF2's scale (the base's, nudged by what the ES2 item is about: a
longer cloak, a stronger blast, a wider beam). ES2's devices run on a cooldown and its consumables are used up; GoF2 has
neither as such, so:
  - the cloaks (Shadow Strike, Vanish, the Cloak Field Generator; Spectral Form as a phase cloak) are GoF2 cloaks;
  - the blasts (Static Overload, the Magnetic and Radial Repulsors, ARC-9000, the EMP Generator, the Peacemaker) are
    secondaries with ammunition: the Shock Blast, the nuke and the EMP bomb;
  - the drones and turrets (Phalanx, the Turret, the Combat Drone, the Sticky Turret) are sentry guns;
  - the life-steal devices (Void Swarm, Siphon Pulse, the Nano Transmitter) are transfusion beams, the repair ones
    (Temporal Nano Recompensator, Nanobots) repair bots, the last-chance ones (Entropy Anchor, the Energy Shield) the
    emergency system (used up), Time Extender the time extender, Energized Boost a booster, Weapon Overdrive / the Damage
    Booster / the Energy Injector weapon mods, the Front Shield Generator a shield and the Damage Limiter armour;
  - the Missile Defense System uses the remake's "missileDefense" (its auto turrets shoot down incoming missiles), on a
    seatless cabin (any number can be mounted, nothing else changes; the game names it "Missile defense");
  - the rest has no GoF2 mechanic to stand on and is left out (SKIPPED).
Names are EVERSPACE 2's; the descriptions say what the item does here. Icons: icons.py, from ES2's own item icons.

ES2's own numbers (2026-11-04, its items.CSV through es2data.py: TABLE) replace the mod's where the item does here what it
does there: durations, cooldowns (its first level's), effect shares and reaches. A reach is ES2's metres x 3.6 (the size of
its ships here) in game units (RANGE: cm x 0.72). Damage and prices stay on GoF2's scale. Without the tables in the export
the numbers below stand."""
import es2data, icons

LOG = print

# id, ES2 icon, plate, base item, name, tech level, occurrence, price, stats, description
DEVICES = [
    ('shadow_strike', 'icon_super_light_scout_60x60_2x', 'equipment', 96, 'Shadow Strike', 9, 6, 240000,
     {'cloakDurationMs': 25000, 'cloakChargeMs': 1500, 'energyCells': 2},
     'The Scout\'s cloak from EVERSPACE 2. Hides the ship for 25 seconds after a charge of only 1.5 seconds, for 2 energy cells.'),
    ('vanish', 'icon_device_vanish_86x86_2x', 'equipment', 95, 'Vanish', 8, 8, 90000,
     {'cloakDurationMs': 10000, 'cloakChargeMs': 800, 'energyCells': 1},
     'A quick-start cloak: the ship disappears almost at once, for 10 seconds, for one energy cell.'),
    ('spectral_form', 'icon_super_spectral_form_60x60_2x', 'equipment', 96, 'Spectral Form', 10, 3, 420000,
     {'cloakDurationMs': 15000, 'cloakChargeMs': 2500, 'energyCells': 4, 'phaseCloak': 1},
     'Turns the ship into a ghostly, semi-corporeal form for 15 seconds: unseen, and passing through stations, asteroids and '
     'other ships unharmed. Four energy cells.'),
    ('time_extender', 'icon_super_light_patrol_60x60_2x', 'equipment', 184, 'Time Extender', 9, 4, 330000,
     {'timeExtenderMs': 12000, 'timeExtenderCooldownMs': 40000},
     'Bends spacetime around the ship: for 12 seconds everything else slows down. Recharges in 40 seconds.'),
    ('weapon_overdrive', 'icon_super_medium_interceptor_60x60_2x', 'equipment', 186, 'Weapon Overdrive', 9, 5, 160000,
     {'fireRateFactor': 20, 'damageFactor': 20},
     'The Interceptor\'s overdrive, made permanent: the primary weapons fire 20 % faster and hit 20 % harder.'),
    ('energized_boost', 'icon_device_energized_boost_86x86_2x', 'equipment', 195, 'Energized Boost', 8, 12, 60000,
     {'boostSpeed': 360, 'boostDurationMs': 2000, 'boostRechargeMs': 12000},
     'Catapults the ship forward: a short, very fast boost of 2 seconds, ready again after 12.'),
    ('void_swarm', 'icon_super_rogue_60x60_2x', 'equipment', 223, 'Void Swarm', 10, 3, 560000,
     {'beamRange': 25000, 'beamStrength': 120, 'beamTargets': 4},
     'A swarm of micro-bots that eats into up to four enemies at once and feeds what it takes to your shield.'),
    ('siphon_pulse', 'icon_device_siphon_pulse_86x86_2x', 'equipment', 223, 'Siphon Pulse', 9, 6, 300000,
     {'beamRange': 14000, 'beamStrength': 100, 'beamTargets': 3},
     'Drains three nearby enemies at once, repairing your shield with what it takes.'),
    ('nano_transmitter', 'icon_device_structural_nano_relocator_86x86_2x', 'equipment', 222, 'Nano Transmitter', 8, 12, 12000,
     {'beamRange': 16000, 'beamStrength': 60, 'beamTargets': 1},
     'Turns damage into repairs: drains the most damaged enemy in reach and feeds it to your shield.'),
    ('temporal_nano_recompensator', 'icon_device_temporal_nano_recompensator_86x86_2x', 'equipment', 188,
     'Temporal Nano Recompensator', 8, 10, 135000, {},
     'Nanites that rebuild the hull and armour in flight, quickly.'),
    ('frontshield_generator', 'icon_device_front_shield_generator_86x86_2x', 'equipment', 54, 'Front Shield Generator', 9, 6, 330000,
     {'shieldCapacity': 260, 'shieldRegenMs': 50000},
     'A heavy shield projector: a strong shield that recharges in 50 seconds.'),
    ('entropy_anchor', 'icon_device_entropy_anchor_86x86_2x', 'equipment', 185, 'Entropy Anchor', 9, 5, 12000,
     {'emergencyMs': 10000},
     'Anchors the ship\'s state in time: when the hull gives out it holds at its last point and the ship is untouchable for 10 '
     'seconds. Used up when it fires.'),
    ('static_overload', 'icon_super_medium_sentinel_60x60_2x', 'secondary', 226, 'Static Overload', 9, 6, 9000,
     {'damage': 120, 'empDamage': 400, 'blastRadius': 60000},
     'The Sentinel\'s discharge: arcing electricity all around the ship that damages, disables and throws back everything in '
     'reach.'),
    ('magnetic_repulsor', 'icon_device_magnetic_repulsor_86x86_2x', 'secondary', 226, 'Magnetic Repulsor', 8, 10, 4000,
     {'damage': 80, 'empDamage': 0, 'blastRadius': 40000},
     'A magnetic pulse that hurls nearby enemies away from the ship.'),
    ('arc_9000', 'icon_super_heavy_bomber_60x60_2x', 'secondary', 46, 'ARC-9000', 10, 4, 6200,
     {'damage': 950, 'blastRadius': 45000},
     'The Bomber\'s huge ball of destruction: explodes on impact and tears into everything around it.'),
    ('emp_generator', 'icon_device_emp_generator_86x86_2x', 'secondary', 43, 'EMP Generator', 8, 15, 420,
     {'empDamage': 400, 'blastRadius': 50000},
     'An electro-magnetic pulse that disables every ship caught in it.'),
    ('tactical_artillery_beam', 'icon_device_tac_artillery_beam_86x86_2x', 'secondary', 40, 'Tactical Artillery Beam', 10, 4, 1800,
     {'damage': 900, 'empDamage': 0, 'reloadMs': 8000, 'speed': 10},
     'Marks the locked target for a heavy strike that homes in on it.'),
    ('phalanx', 'icon_super_heavy_vindicator_60x60_2x', 'secondary', 213, 'Phalanx', 9, 6, 6500,
     {'damage': 12, 'reloadMs': 150, 'speed': 30},
     'The Vindicator\'s drones: deploys a drone that fires at your enemies at a furious rate.'),
    ('missile_defense_system', 'icon_device_missile_defense_system_86x86_2x', 'equipment', 91, 'Missile Defense System', 8, 10, 85000,
     {'missileDefense': 30000, 'cabinSize': 0},
     'Lets your auto turrets shoot down homing missiles flying at the ship within 1.5 km, before they turn to enemy ships. '
     'Needs an automatic turret.'),
    ('deployable_turret', 'icon_super_heavy_gunship_60x60_2x', 'secondary', 213, 'Turret', 9, 6, 5400,
     {'damage': 16, 'reloadMs': 250},
     'The Gunship\'s automated turret: deploys it beside the ship, where it fires at your enemies.'),
]

CONSUMABLES = [
    ('damage_booster', 'art_board16_Damage-Booster', 'equipment', 187, 'Damage Booster', 6, 20, 24000,
     {'fireRateFactor': 0, 'damageFactor': 25},
     'The primary weapons hit 25 % harder.'),
    ('energy_injector', 'art_board17_Energy-Injector', 'equipment', 186, 'Energy Injector', 6, 20, 24000,
     {'fireRateFactor': 25, 'damageFactor': 0},
     'More power for the weapons: the primaries fire 25 % faster.'),
    ('nanobots', 'icon_consumable_nanobot_small_86x86_2x', 'equipment', 75, 'Nanobots', 4, 40, 36000, {},
     'Nanobots that repair the hull and armour in flight.'),
    ('nanobots_large', 'icon_consumable_nanobot_large_86x86_2x', 'equipment', 188, 'Nanobots Large', 7, 15, 120000, {},
     'A larger swarm of nanobots: repairs the hull and armour faster.'),
    ('damage_limiter', 'icon_consumable_damage_limiter_86x86_2x', 'equipment', 57, 'Damage Limiter', 6, 20, 40000,
     {'armor': 120},
     'Absorbs a share of the damage before it reaches the hull.'),
    ('energy_shield', 'icon_consumable_energy_shield_86x86_2x', 'equipment', 185, 'Energy Shield', 7, 15, 9000,
     {'emergencyMs': 8000},
     'Deploys a shield bubble when the hull gives out: 8 seconds untouchable. Used up when it fires.'),
    ('cloak_field_generator', 'icon_consumable_cloak_field_generator_86x86_2x', 'equipment', 94, 'Cloak Field Generator', 6, 15, 60000,
     {'cloakDurationMs': 15000, 'cloakChargeMs': 5000, 'energyCells': 2},
     'Hides the ship from the enemies for 15 seconds.'),
    ('radial_repulsor', 'big_bang', 'secondary', 226, 'Radial Repulsor', 7, 12, 3000,
     {'damage': 20, 'empDamage': 0, 'blastRadius': 75000},
     'A shockwave that pushes every ship around you away.'),
    ('peacemaker', 'icon_consumable_peacemaker_86x86_2x', 'secondary', 42, 'Peacemaker', 6, 20, 260,
     {'empDamage': 220, 'blastRadius': 40000},
     'Silences the enemy\'s guns: a pulse that disables the ships around it.'),
    ('combat_drone', 'icon_consumable_combat_drone_86x86_2x', 'secondary', 212, 'Combat Drone', 8, 10, 1400,
     {'damage': 12, 'reloadMs': 280},
     'Constructs a combat drone that fights at your side.'),
    ('sticky_turret', 'icon_consumable_sticky_turret_86x86_2x', 'secondary', 211, 'Sticky Turret', 6, 25, 500,
     {'damage': 7, 'reloadMs': 500},
     'A small turret that you drop in space, where it fights for you.'),
    # The remake's consumable devices (2026-11-02; Flight.Device 8-12, "deviceConsumable": one use per unit, stacked like
    # missiles): what each EVERSPACE 2 consumable does in its blueprint, with numbers of the mod's own (ES2's item tables
    # aren't in the export).
    ('smoke_bomb', 'smoke_bomb', 'equipment', 91, 'Smoke Bomb', 5, 30, 400,
     {'cabinSize': 0, 'device': 8, 'deviceConsumable': 1, 'deviceRadius': 16000, 'deviceGrowMs': 2000, 'deviceDurationMs': 20000},
     'Drops a sensor cloud 800 m across that grows in two seconds and lasts 20: while you fly inside it the enemies lose you, hold '
     'their fire and their missiles lose their lock. One use.'),
    ('nano_injector', 'art_board19_Nano-Injector', 'equipment', 91, 'Nano Injector', 5, 30, 600,
     {'cabinSize': 0, 'device': 9, 'deviceConsumable': 1, 'deviceDamagePercent': 35},
     'A shot of nanites that rebuilds 35 % of the hull at once. One use.'),
    ('armor_repair', 'armor_repair', 'equipment', 91, 'Armor Repair', 5, 30, 500,
     {'cabinSize': 0, 'device': 10, 'deviceConsumable': 1, 'deviceDamagePercent': 100},
     'Restores the armour to full at once. One use.'),
    ('secondaries_restock', 'secondaries_restock', 'equipment', 91, 'Secondaries Restock', 6, 25, 900,
     {'cabinSize': 0, 'device': 11, 'deviceConsumable': 1, 'deviceAmmo': 10},
     'Ten rounds more for the selected secondary weapon, wherever you are. One use.'),
    ('device_charger', 'icon_consumable_device_charger_86x86_2x', 'equipment', 91, 'Device Charger', 7, 20, 1200,
     {'cabinSize': 0, 'device': 12, 'deviceConsumable': 1},
     'Ends the cooldown of every other device at once. One use.'),
    # The remake's cooldown devices 13-18 (2026-11-02), after the blueprints; the numbers are the mod's own.
    ('corrosion_injector', 'icon_device_corrosion_injector_86x86_2x', 'equipment', 91, 'Corrosion Injector', 7, 12, 150000,
     {'cabinSize': 0, 'device': 13, 'deviceCooldownMs': 45000, 'deviceDurationMs': 12000, 'deviceRadius': 60000, 'damage': 6},
     'Injects the locked ship with a corrosive agent: for 12 seconds it takes damage every second, straight past its shield. Recharges in 45 seconds.'),
    ('teleporter', 'icon_device_teleporter_86x86_2x', 'equipment', 91, 'Teleporter', 8, 10, 190000,
     {'cabinSize': 0, 'device': 14, 'deviceCooldownMs': 30000, 'deviceRadius': 40000},
     'A blink two kilometres straight ahead, short of anything in the way. Recharges in 30 seconds.'),
    ('spectral_shift', 'icon_device_spectral_shift_86x86_2x', 'equipment', 91, 'Spectral Shift', 9, 6, 320000,
     {'cabinSize': 0, 'device': 15, 'deviceCooldownMs': 40000, 'deviceRadius': 30000, 'deviceRange2': 6000, 'damage': 40},
     'Phases the ship 1.5 kilometres ahead, tearing through every enemy within 300 m of the way. Recharges in 40 seconds.'),
    ('fusion_hook', 'icon_device_fusion_hook_86x86_2x', 'equipment', 91, 'Fusion Hook', 7, 12, 120000,
     {'cabinSize': 0, 'device': 16, 'deviceCooldownMs': 25000, 'deviceDurationMs': 6000, 'deviceRadius': 40000},
     'Grapples the enemy in your sights within two kilometres and reels you together, up to 800 m/s, until you are 200 m apart. Recharges in 25 seconds.'),
    ('quantum_tether', 'icon_device_quantum_entangler_86x86_2x', 'equipment', 91, 'Quantum Tether', 8, 8, 240000,
     {'cabinSize': 0, 'device': 17, 'deviceCooldownMs': 50000, 'deviceDurationMs': 10000, 'deviceRadius': 16000},
     'Tethers the locked ship for 10 seconds: whatever it takes, every enemy within 800 m of it takes too; when it dies the tether jumps on. Recharges in 50 seconds.'),
    ('quantum_entangler', 'icon_device_quantum_entangler_86x86_2x', 'equipment', 91, 'Quantum Entangler', 8, 8, 260000,
     {'cabinSize': 0, 'device': 18, 'deviceCooldownMs': 50000, 'deviceDurationMs': 8000, 'deviceRadius': 40000, 'deviceDamagePercent': 150},
     'Entangles the locked ship with yours for 8 seconds: all the damage you take meanwhile hits it at the end, one and a half times over. Recharges in 50 seconds.'),
]

# EVERSPACE 2's devices and consumables with no GoF2 mechanic to stand on (what they need).
SKIPPED = {
    'annihilator_virus': 'a spreading infection', 'resurgence': 'Echo Fragments',
    'nanobots_medium': 'nothing between the two repair bots', 'nano_repair_kit': 'equipment damage',
    'ult_recharge': 'ULT charge', 'system_recovery_routine': 'debuffs', 'pheromone_ejector': 'creatures',
}


RANGE = 0.72   # ES2 cm -> game units: m x 3.6 x 20


def _sec(v): return int(round(v * 1000))
def _pct(v): return int(round(v * 100))
def _units(v): return int(round(v * RANGE))
def _km(units): return f'{units / 20000:.1f}'.rstrip('0').rstrip('.')


# id -> ([(stat, ES2 attribute, conversion)], description template over the new stats, None = keep the description)
TABLE = {
    'vanish': ([('cloakDurationMs', 'device_duration', _sec)],
               'A quick-start cloak: the ship disappears almost at once, for {cloakDurationMs_s} seconds, for one energy cell.'),
    'energized_boost': ([('boostDurationMs', 'device_duration', _sec), ('boostRechargeMs', 'device_cooldown', _sec)],
                        'Catapults the ship forward: a short, very fast boost of {boostDurationMs_s} seconds, ready again after {boostRechargeMs_s}.'),
    'entropy_anchor': ([('emergencyMs', 'device_duration', _sec)], None),
    'magnetic_repulsor': ([('blastRadius', 'device_range', _units)], None),
    'emp_generator': ([('blastRadius', 'device_range', _units)], None),
    'missile_defense_system': ([('missileDefense', 'device_range', _units)],
                               'Lets your auto turrets shoot down homing missiles flying at the ship within {missileDefense_km} km, before they turn to enemy ships. '
                               'Needs an automatic turret.'),
    'damage_booster': ([('damageFactor', 'consumable_effect', _pct)], 'The primary weapons hit {damageFactor} % harder.'),
    'energy_shield': ([('emergencyMs', 'consumable_duration', _sec)],
                      'Deploys a shield bubble when the hull gives out: {emergencyMs_s} seconds untouchable. Used up when it fires.'),
    'cloak_field_generator': ([('cloakDurationMs', 'consumable_duration', _sec)], 'Hides the ship from the enemies for {cloakDurationMs_s} seconds.'),
    'peacemaker': ([('blastRadius', 'consumable_range', _units)], None),
    'smoke_bomb': ([('deviceRadius', 'consumable_range', _units), ('deviceDurationMs', 'consumable_duration', _sec)],
                   'Drops a sensor cloud {deviceRadius_km} km in radius that grows in two seconds and lasts {deviceDurationMs_s}: while you fly inside it the '
                   'enemies lose you, hold their fire and their missiles lose their lock. One use.'),
    'nano_injector': ([('deviceDamagePercent', 'consumable_effect', _pct)], 'A shot of nanites that rebuilds {deviceDamagePercent} % of the hull at once. One use.'),
    'corrosion_injector': ([('deviceCooldownMs', 'device_cooldown', _sec), ('deviceDurationMs', 'device_effect_duration', _sec), ('deviceRadius', 'device_range', _units)],
                           'Injects the locked ship with a corrosive agent: for {deviceDurationMs_s} seconds it takes damage every second, straight past its shield. '
                           'Recharges in {deviceCooldownMs_s} seconds.'),
    'teleporter': ([('deviceCooldownMs', 'device_cooldown', _sec), ('deviceRadius', 'device_range', _units)],
                   'A blink {deviceRadius_km} kilometres straight ahead, short of anything in the way. Recharges in {deviceCooldownMs_s} seconds.'),
    'spectral_shift': ([('deviceCooldownMs', 'device_cooldown', _sec), ('deviceRadius', 'device_range', _units), ('deviceRange2', 'device_range_2', _units)],
                       'Phases the ship {deviceRadius_km} kilometres ahead, tearing through every enemy within {deviceRange2_m} m of the way. Recharges in {deviceCooldownMs_s} seconds.'),
    'fusion_hook': ([('deviceCooldownMs', 'device_cooldown', _sec), ('deviceRadius', 'device_range', _units)],
                    'Grapples the enemy in your sights within {deviceRadius_km} kilometres and reels you together, up to 800 m/s, until you are 200 m apart. '
                    'Recharges in {deviceCooldownMs_s} seconds.'),
    # (its device_range is how far the target may be; the tether's own reach to the enemies around it stays the mod's)
    'quantum_tether': ([('deviceDurationMs', 'device_duration', _sec)],
                       'Tethers the locked ship for {deviceDurationMs_s} seconds: whatever it takes, every enemy within {deviceRadius_m} m of it takes too; when it dies '
                       'the tether jumps on. Recharges in {deviceCooldownMs_s} seconds.'),
    'quantum_entangler': ([('deviceCooldownMs', 'device_cooldown', _sec), ('deviceDurationMs', 'device_duration', _sec), ('deviceRadius', 'device_range', _units),
                           ('deviceDamagePercent', 'device_effect', lambda v: 100 + _pct(v))],
                          'Entangles the locked ship with yours for {deviceDurationMs_s} seconds: all the damage you take meanwhile hits it at the end, '
                          '{deviceDamagePercent} % over. Recharges in {deviceCooldownMs_s} seconds.'),
}


def from_tables(it):
    """An item with ES2's own numbers (TABLE) where its items.CSV has them."""
    spec = TABLE.get(it['id'])
    if not spec or not es2data.available(): return it
    fields, template = spec
    stats = dict(it.get('stats') or {})
    changed = False
    for stat, attr, conv in fields:
        v = es2data.attr(it['id'], attr)
        if v is None or v <= 0: continue
        stats[stat] = conv(v)
        changed = True
    if not changed: return it
    it['stats'] = stats
    if template:
        words = {}
        for k, v in stats.items():
            words[k] = v
            if isinstance(v, (int, float)):
                words[k + '_s'] = f'{v / 1000:g}'
                words[k + '_km'] = _km(v)
                words[k + '_m'] = str(int(round(v / 20 / 10) * 10))
        it['description'] = template.format(**words)
    return it


def _item(row):
    iid, icon, frame, base, name, tl, occ, price, stats, desc = row
    it = {'id': iid, 'base': base, 'name': name, 'description': desc, 'techLevel': tl, 'occurrence': occ,
          'price': [price, int(round(price * 1.1))], '_icon': icon, '_frame': frame}
    if stats: it['stats'] = dict(stats)
    return it


def build(mod):
    """The devices' and consumables' items.json entries (their icons made)."""
    out = [from_tables(_item(r)) for r in DEVICES + CONSUMABLES]
    made = icons.apply(out, mod)
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    LOG(f'  devices: {len(DEVICES)} devices, {len(CONSUMABLES)} consumables ({len(SKIPPED)} left out: no GoF2 mechanic), '
        f'{made} icons')
    return out
