"""EVERSPACE 2's ship components (tools/components.py) on GoF2's ranges: the tech level from the rarity, the stats GoF2's
own at that tech level nudged by the item's standing in its kind and rarity, never past GoF2's best; the items without
their key stat and the energy cores left out. Small tables in ES2's own form stand in for the export's (as
test_es2data's)."""
from pathlib import Path
import os, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import es2data, icons, components

ATTRS = ['shield_capacity', 'shield_recharge_speed', 'armor', 'boost_speed', 'boost_energy_capacity',
         'boost_energy_consumption', 'boost_recharge_speed', 'sensor_range_ships', 'sensor_range_resources', 'cargo_slots_buff']


def row(cat, iid, name, rarity, values):
    cells = [cat, '', '', '', iid, name, 'BP_X', 'icon_' + iid, 'Its text.', '', '', rarity, 'Ascendant']
    for a in ATTRS:
        v = values.get(a, '')
        cells += [v, '!' if v else '', v]
    return '|~'.join(cells)


def header(cat): return '|~'.join([cat, 'X', '', '', cat[4:], 'X'] + [''] * (7 + 3 * len(ATTRS)))


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = os.path.join(self.dir.name, 'DataFiles')
        os.makedirs(d)
        head = []
        for a in ATTRS: head += [a, '', '']
        open(os.path.join(d, 'attributes.CSV'), 'wb').write(('|~'.join(head) + '\r\n').encode('cp1252'))
        rows = [
            header('cat_energy_core'),
            row('', 'energy_core_weapons', 'Energy Core', 'Common', {'shield_capacity': '10'}),
            header('cat_shield'),
            row('', 'shield_a', 'Shield A', 'Uncommon', {'shield_capacity': '40', 'shield_recharge_speed': '1.0'}),
            row('', 'shield_b', 'Shield B', 'Uncommon', {'shield_capacity': '80', 'shield_recharge_speed': '1.0'}),
            row('', 'shield_none', 'Shield None', 'Legendary', {'shield_capacity': '0'}),
            header('cat_thrusters'),
            row('', 'boost_x', 'Boost X', 'Legendary', {'boost_speed': '9', 'boost_energy_capacity': '300', 'boost_energy_consumption': '1',
                                                        'boost_recharge_speed': '9'}),
            header('cat_sensor'),
            row('', 'sensor_res', 'Peruser', 'Uncommon', {'sensor_range_ships': '300000', 'sensor_range_resources': '140000'}),
            header('cat_cargo_unit'),
            row('', 'cargo_x', 'Cargo X', 'Rare', {'cargo_slots_buff': '4'}),
        ]
        open(os.path.join(d, 'items.CSV'), 'wb').write(('\r\n'.join(rows) + '\r\n').encode('cp1252'))
        es2data.configure(self.dir.name)
        self.apply = icons.apply
        icons.apply = lambda items, mod, folder='icons/items': 0
        components.LOG = lambda *a: None
        self.items = {it['id']: it for it in components.build(self.dir.name)}

    def tearDown(self):
        icons.apply = self.apply
        es2data.configure(None)
        self.dir.cleanup()

    def test_left_out(self):
        self.assertNotIn('energy_core_weapons', self.items, 'no GoF2 energy')
        self.assertNotIn('shield_none', self.items, 'no key stat: a legendary effect only')

    def test_on_gof2s_ranges(self):
        a, b = self.items['shield_a'], self.items['shield_b']
        self.assertEqual(5, a['techLevel'], 'Uncommon: tech 5')
        mid = components._at(components.SHIELD, 5)
        self.assertEqual(round(mid * (1 - components.NUDGE)), a['stats']['shieldCapacity'], 'half the average: nudged down at most')
        self.assertEqual(round(mid * (1 + components.NUDGE)), b['stats']['shieldCapacity'])
        self.assertEqual(51, a['base'], 'on the GoF2 shield of its tech level (Riot Shield, tech 4)')
        self.assertEqual('Shield A', a['name'])
        self.assertEqual('Its text.', a['description'])

    def test_never_past_gof2s_best(self):
        s = self.items['boost_x']['stats']
        self.assertEqual(max(components.BOOST_SPEED.values()), s['boostSpeed'])
        self.assertEqual(max(components.BOOST_DURATION.values()), s['boostDurationMs'])
        self.assertGreaterEqual(s['boostRechargeMs'], min(components.BOOST_RECHARGE.values()))

    def test_sensor_and_cargo(self):
        s = self.items['sensor_res']['stats']
        self.assertEqual(1, s['showClassAAsteroids'], 'a resource sensor marks class-A asteroids')
        self.assertEqual(1, s['radarShowsCargo'])
        self.assertGreaterEqual(s['lockTimeMs'], min(components.LOCK.values()))
        self.assertEqual(round(components._at(components.CARGO, 7)), self.items['cargo_x']['stats']['cargoBonus'])


if __name__ == '__main__':
    unittest.main()
