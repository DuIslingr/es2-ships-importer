"""ES2's game tables (tools/es2data.py) and what reads them: devices.py's numbers, weapons.py's debuffs, crafting.py's
recipes. Small tables in ES2's own form ('|~' cells, items.CSV's 13 leading cells, three cells an attribute) stand in for
the export's."""
from pathlib import Path
import os, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import es2data, devices, weapons, crafting

ATTRS = ['device_cooldown', 'device_duration', 'device_effect_duration', 'device_range', 'device_effect',
         'consumable_effect', 'consumable_duration', 'consumable_range', 'item_price',
         'destabilizer_effect', 'weapon_effect_duration_scaling', 'weapon_effect_duration', 'no_damage']


def item_row(iid, name, values, icon='icon_x', text='Its text.'):
    cells = ['cat_x', 'X', '', '', iid, name, 'BP_X', icon, text, '', '', 'Common', 'Common']
    for a in ATTRS:
        v = values.get(a, '')
        cells += [v, '!' if v else '', v]
    return '|~'.join(cells)


class TableTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = os.path.join(self.dir.name, 'DataFiles')
        os.makedirs(d)
        head = []
        for a in ATTRS: head += [a, '', '']
        open(os.path.join(d, 'attributes.CSV'), 'wb').write(('|~'.join(head) + '\r\n').encode('cp1252'))
        rows = [
            item_row('teleporter', 'Teleporter', {'device_cooldown': '20|19|18', 'device_range': '60000'}),
            item_row('damage_booster', 'Damage Booster', {'consumable_effect': '0.40', 'consumable_duration': '20.00'}),
            item_row('quantum_entangler', 'Quantum Entangler', {'device_cooldown': '20|19', 'device_duration': '14', 'device_effect': '0.4', 'device_range': '80000'}),
            item_row('destabilizer_missile', 'Destabilizer Missiles', {'destabilizer_effect': '0.30', 'weapon_effect_duration_scaling': '6.00', 'no_damage': '1.00'}),
            item_row('corrosion_missile', 'Corrosion Missiles', {'weapon_effect_duration': '8.00', 'no_damage': '1.00'}),
            item_row('supra_gel', 'Supra Gel', {'item_price': '160.00'}, 'item_component_supra_gel_86x86_2x', 'An indispensable component.'),
            item_row('crafting_resource_basic', 'Spare Parts', {}),
        ]
        open(os.path.join(d, 'items.CSV'), 'wb').write(('\r\n'.join(rows) + '\r\n').encode('cp1252'))
        open(os.path.join(d, 'crafting_tech.csv'), 'w').write(
            '|~ore_copper_common|~plasma|~scrap_metal|~biomass\nsupra_gel|~3|~3|~4|~\nbio_processor|~|~2|~|~2\n')
        open(os.path.join(d, 'crafting_consumables.csv'), 'w').write(
            '|~crafting_resource_basic|~supra_gel\ndamage_booster|~4|~1\nnanobots_small|~2|~\nult_recharge|~1|~1\n')
        es2data.configure(self.dir.name)

    def tearDown(self):
        es2data.configure(None)
        self.dir.cleanup()

    def test_items(self):
        self.assertEqual(20.0, es2data.attr('teleporter', 'device_cooldown'), 'the first level of "20|19|18"')
        self.assertEqual(18.0, es2data.attr('teleporter', 'device_cooldown', level=5), 'past the list: its last')
        self.assertEqual(0.4, es2data.attr('damage_booster', 'consumable_effect'))
        self.assertIsNone(es2data.attr('damage_booster', 'device_range'))
        self.assertEqual('Supra Gel', es2data.items()['supra_gel']['name'])

    def test_recipes(self):
        r = es2data.recipes('crafting_tech.csv')
        self.assertEqual({'ore_copper_common': 3, 'plasma': 3, 'scrap_metal': 4}, r['supra_gel'])

    def test_devices_take_es2s_numbers(self):
        row = next(r for r in devices.CONSUMABLES if r[0] == 'teleporter')
        it = devices.from_tables(devices._item(row))
        self.assertEqual(20000, it['stats']['deviceCooldownMs'])
        self.assertEqual(43200, it['stats']['deviceRadius'], "600 m x 3.6 in game units")
        self.assertIn('2.2 kilometres', it['description'])
        row = next(r for r in devices.CONSUMABLES if r[0] == 'damage_booster')
        self.assertEqual(40, devices.from_tables(devices._item(row))['stats']['damageFactor'])
        row = next(r for r in devices.CONSUMABLES if r[0] == 'quantum_entangler')
        st = devices.from_tables(devices._item(row))['stats']
        self.assertEqual((20000, 14000, 140), (st['deviceCooldownMs'], st['deviceDurationMs'], st['deviceDamagePercent']))

    def test_without_tables_the_mods_numbers_stand(self):
        es2data.configure(None)
        row = next(r for r in devices.CONSUMABLES if r[0] == 'teleporter')
        self.assertEqual(30000, devices.from_tables(devices._item(row))['stats']['deviceCooldownMs'])

    def test_debuff_missiles(self):
        self.assertEqual({'vulnerablePercent': 30, 'vulnerableMs': 6000},
                         weapons.table_debuffs('DestabilizerMissileLauncher', weapons.SECONDARY['DestabilizerMissileLauncher'][5]))
        c = weapons.table_debuffs('CorrosionMissileLauncher', weapons.SECONDARY['CorrosionMissileLauncher'][5])
        self.assertEqual((1.0, 8000), (c['dotShare'], c['dotMs']), "ES2's no_damage: the whole hit over time")

    def test_crafting(self):
        import icons
        old = icons.available; icons.available = lambda: False
        try: items, bps = crafting.build(self.dir.name, {'copper'}, {'damage_booster', 'nanobots'})
        finally: icons.available = old
        ids = {b['id']: b for b in bps}
        self.assertEqual([{'item': 'es2_ships:es2_copper', 'amount': 3}, {'item': 201, 'amount': 3}, {'item': 99, 'amount': 4}],
                         ids['es2_craft_supra_gel']['ingredients'], 'copper the mod\'s, plasma and scrap GoF2\'s')
        self.assertNotIn('es2_craft_bio_processor', ids, 'biomass: no stand-in')
        self.assertEqual('es2_ships:damage_booster', ids['es2_craft_damage_booster']['item'])
        self.assertEqual('es2_ships:nanobots', ids['es2_craft_nanobots_small']['item'], 'ES2\'s small nanobots: the mod\'s nanobots')
        self.assertNotIn('es2_craft_ult_recharge', ids, 'a product the mod lacks')
        self.assertTrue(all(b['unlocked'] for b in bps))
        gel = next(i for i in items if i['id'] == 'es2_supra_gel')
        self.assertEqual(40, gel['price'][0], "ES2's 160 x 0.25")
        self.assertEqual(0, gel['occurrence'], 'only crafted')
        parts = next(i for i in items if i['id'] == 'es2_crafting_resource_basic')
        self.assertGreater(parts['occurrence'], 0, 'the NPCs carry it, the shops stock it')

    def test_write_merges(self):
        import json
        p = os.path.join(self.dir.name, 'blueprints.json')
        json.dump([{'id': 'other'}, {'id': 'es2_craft_old'}], open(p, 'w'))
        crafting.write(self.dir.name, [{'id': 'es2_craft_new'}])
        self.assertEqual(['other', 'es2_craft_new'], [b['id'] for b in json.load(open(p))])


if __name__ == '__main__':
    unittest.main()
