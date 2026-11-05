"""EVERSPACE 2's ship components (items.CSV's cat_shield, cat_plating, cat_thrusters, cat_sensor, cat_cargo_unit) as the
ES2 Ships mod's equipment (items.json), each "based on" the Galaxy on Fire 2 item of its kind and tech level.

The numbers are GoF2's, so nothing outclasses GoF2's own gear: an item's tech level comes from its ES2 rarity (TECH), its
stats from what GoF2's own items of that kind have at that tech level (the tables below, from the remake's items.json,
interpolated), nudged by how the ES2 item stands against the others of its kind and rarity (its key stat over their
average, NUDGE at most each way), and never past GoF2's own best of the kind (cap()):
  shields     shieldCapacity by ES2's shield_capacity; shieldRegenMs by its shield_recharge_speed (faster: shorter)
  platings    armor by ES2's armor
  boosters    boostSpeed by boost_speed, boostDurationMs by boost_energy_capacity / boost_energy_consumption (its
              seconds of boost), boostRechargeMs by boost_recharge_speed
  sensors     lockTimeMs GoF2's by tech; radarShowsCargo from tech 3 as GoF2's scanners; showClassAAsteroids for the
              resource sensors (sensor_range_resources from 120 000: the Peruser, Pestilence, True Shepherd)
  cargo units cargoBonus by ES2's cargo_slots_buff
Left out: the energy cores (GoF2 has no energy to share between weapons, shields and boosters), items whose key stat is 0
(SH-8495, Hollow: theirs is a legendary effect), and ES2's perks, set bonuses and legendary effects (no GoF2 mechanic;
sets.csv, the legendary_* attributes). Names and texts are EVERSPACE 2's (items.CSV cells 5 and 8); icons its own
(cell 7, icons.py)."""
import es2data, icons

LOG = print

TECH = {'Common': 3, 'Uncommon': 5, 'Rare': 7, 'Superior': 8, 'Legendary': 9}
OCCURRENCE = {'Common': 60, 'Uncommon': 40, 'Rare': 25, 'Superior': 15, 'Legendary': 5}   # (GoF2's: 80 at tech 2 to 5 at 10)
NUDGE = 0.15   # (0.25 put a tech-5 shield past GoF2's tech-6 one)

# GoF2's own items by tech level: {tech: value} (the remake's items.json / item_attributes.json), and the base items.
SHIELD = {2: 50, 4: 80, 6: 120, 8: 150, 10: 220}
SHIELD_REGEN = {2: 20000, 4: 46000, 6: 58000, 8: 45000, 10: 60000}
SHIELD_PRICE = {2: 3750, 4: 11500, 6: 30750, 8: 89500, 10: 263825}
SHIELD_BASE = {2: 50, 4: 51, 6: 52, 8: 53, 10: 54}
ARMOR = {2: 40, 4: 80, 6: 110, 8: 160, 10: 250}
ARMOR_PRICE = {2: 2250, 4: 9500, 6: 41000, 8: 107500, 10: 169484}
ARMOR_BASE = {2: 55, 4: 56, 6: 57, 8: 58, 10: 59}
CARGO = {1: 15, 3: 25, 5: 40, 7: 75, 10: 100}
CARGO_PRICE = {1: 2100, 3: 4700, 5: 13000, 7: 24800, 10: 104550}
CARGO_BASE = {1: 63, 3: 64, 5: 65, 7: 66, 10: 67}
BOOST_SPEED = {4: 60, 5: 80, 7: 160, 8: 300}
BOOST_RECHARGE = {4: 8000, 5: 10000, 7: 12000, 8: 16000}
BOOST_DURATION = {4: 3000, 5: 4400, 7: 5600, 8: 6000}
BOOST_PRICE = {4: 4800, 5: 10400, 7: 20300, 8: 72500}
BOOST_BASE = {4: 71, 5: 72, 7: 73, 8: 195}
LOCK = {2: 4000, 3: 3000, 6: 1800, 7: 1800}
LOCK_PRICE = {2: 460, 3: 7900, 6: 33500, 7: 175200}
LOCK_BASE = {2: 81, 3: 82, 6: 83, 7: 84}
CLASS_A_RANGE = 120000   # sensor_range_resources (cm) from which a sensor marks class-A asteroids

KINDS = ['cat_shield', 'cat_plating', 'cat_thrusters', 'cat_sensor', 'cat_cargo_unit']


def _at(table, tech):
    """'table' at 'tech', linear between its tech levels, its ends beyond them."""
    ks = sorted(table)
    if tech <= ks[0]: return table[ks[0]]
    if tech >= ks[-1]: return table[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= tech <= b: return table[a] + (table[b] - table[a]) * (tech - a) / (b - a)


def _base(table, tech):
    """The base item: the one at the nearest tech level at or below (the lowest above when none is)."""
    below = [k for k in table if k <= tech]
    return table[max(below)] if below else table[min(table)]


def _nudge(value, mean):
    if not value or not mean: return 1.0
    return max(1.0 - NUDGE, min(1.0 + NUDGE, value / mean))


def _a(it, name):
    lo, _ = it['attr'].get(name, ('', ''))
    return es2data.number(lo)


def _price(v): return int(round(v / 50.0)) * 50


# GoF2's best of each stat (its tables' ends; the lock time and recharges the shortest): nothing here goes past them
CAPS = {'shieldCapacity': (None, max(SHIELD.values())), 'shieldRegenMs': (min(SHIELD_REGEN.values()), max(SHIELD_REGEN.values())),
        'armor': (None, max(ARMOR.values())), 'cargoBonus': (None, max(CARGO.values())),
        'boostSpeed': (None, max(BOOST_SPEED.values())), 'boostDurationMs': (None, max(BOOST_DURATION.values())),
        'boostRechargeMs': (min(BOOST_RECHARGE.values()), None), 'lockTimeMs': (min(LOCK.values()), None)}


def cap(stats):
    for k, (lo, hi) in CAPS.items():
        if k not in stats: continue
        if lo is not None: stats[k] = max(lo, stats[k])
        if hi is not None: stats[k] = min(hi, stats[k])
    return stats


def _components():
    """[(kind, item id, item)] in items.CSV's order (a category row, then its items)."""
    out, cat = [], None
    for iid, it in es2data.items().items():
        if it['category']: cat = it['category']; continue
        if cat in KINDS: out.append((cat, iid, it))
    return out


def build(mod):
    """The components' items.json entries (their icons made)."""
    if not es2data.available(): return []
    comps = _components()
    rarity = lambda it: it['row'][11].strip() if len(it['row']) > 11 else 'Common'
    key = {'cat_shield': 'shield_capacity', 'cat_plating': 'armor', 'cat_thrusters': 'boost_speed',
           'cat_sensor': 'sensor_range_ships', 'cat_cargo_unit': 'cargo_slots_buff'}
    # the averages each item is measured against: its kind's items of its rarity (with that stat above 0)
    def mean(kind, rar, f):
        vs = [f(it) for k, _, it in comps if k == kind and rarity(it) == rar and (f(it) or 0) > 0]
        return sum(vs) / len(vs) if vs else None
    secs = lambda it: (_a(it, 'boost_energy_capacity') or 0) / max(1e-6, _a(it, 'boost_energy_consumption') or 0) or None
    out, skipped = [], 0
    for kind, iid, it in comps:
        rar = rarity(it)
        tech = TECH.get(rar, 5)
        v = _a(it, key[kind])
        if not v or v <= 0: skipped += 1; continue
        n = _nudge(v, mean(kind, rar, lambda x: _a(x, key[kind])))
        if kind == 'cat_shield':
            sp = _a(it, 'shield_recharge_speed')
            regen = _at(SHIELD_REGEN, tech) / _nudge(sp, mean(kind, rar, lambda x: _a(x, 'shield_recharge_speed'))) if sp else _at(SHIELD_REGEN, tech)
            stats = {'shieldCapacity': int(round(_at(SHIELD, tech) * n)), 'shieldRegenMs': int(round(regen / 500.0)) * 500}
            base, price = _base(SHIELD_BASE, tech), _at(SHIELD_PRICE, tech) * n
        elif kind == 'cat_plating':
            stats = {'armor': int(round(_at(ARMOR, tech) * n))}
            base, price = _base(ARMOR_BASE, tech), _at(ARMOR_PRICE, tech) * n
        elif kind == 'cat_thrusters':
            rs = _a(it, 'boost_recharge_speed')
            stats = {'boostSpeed': int(round(_at(BOOST_SPEED, tech) * n)),
                     'boostDurationMs': int(round(_at(BOOST_DURATION, tech) * _nudge(secs(it), mean(kind, rar, secs)) / 100.0)) * 100,
                     'boostRechargeMs': int(round(_at(BOOST_RECHARGE, tech) / _nudge(rs, mean(kind, rar, lambda x: _a(x, 'boost_recharge_speed'))) / 100.0)) * 100}
            base, price = _base(BOOST_BASE, tech), _at(BOOST_PRICE, tech) * n
        elif kind == 'cat_sensor':
            t = min(tech, max(LOCK))
            stats = {'lockTimeMs': int(round(_at(LOCK, t) / n / 100.0)) * 100, 'radarShowsCargo': 1 if t >= 3 else 0,
                     'showClassAAsteroids': 1 if (_a(it, 'sensor_range_resources') or 0) >= CLASS_A_RANGE else 0}
            base, price = _base(LOCK_BASE, t), _at(LOCK_PRICE, t) * n
        else:
            stats = {'cargoBonus': int(round(_at(CARGO, tech) * n))}
            base, price = _base(CARGO_BASE, tech), _at(CARGO_PRICE, tech) * n
        cap(stats)
        if rar == 'Legendary': price *= 1.3
        row = it['row']
        desc = (row[8] if len(row) > 8 else '').strip()
        out.append({'id': iid, 'base': base, 'name': it['name'], 'description': desc, 'techLevel': tech,
                    'occurrence': OCCURRENCE.get(rar, 20), 'price': [_price(price), _price(price * 1.1)], 'stats': stats,
                    '_icon': (row[7] if len(row) > 7 else '').strip(), '_frame': 'equipment'})
    made = icons.apply(out, mod)
    for it in out:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    LOG(f'  components: {len(out)} ({", ".join(f"{sum(1 for k, _, i in comps if k == c and _a(i, key[c]))} {c[4:]}" for c in KINDS)}), '
        f'{skipped} left out (a legendary effect only), the energy cores too (no GoF2 energy); {made} icons')
    return out
