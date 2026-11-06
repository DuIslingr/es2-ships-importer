"""ES2's unique loot (tools/sectors.py orbit_unique_loot, resolve_container_loot): a location's named items and resources
with their amounts as the orbit's fixed container loot, to the mod's items once they are made; ES2's rarity rolls,
personal items and augment parts left out, items the mod lacks dropped. A small table in ES2's form stands in."""
from pathlib import Path
import os, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import es2data, sectors


class UniqueLootTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = os.path.join(self.dir.name, 'DataFiles')
        os.makedirs(d)
        cells = lambda *c: '|~'.join(list(c) + [''] * (18 - len(c)))
        rows = [cells('1', 'S04L01', 'a', 'sensor_okkar', '', '', 'Rare'),
                cells('', '', 'b', '', 'cat_equipment', '', 'Common', '', 'solar_particles', '', '12'),
                cells('', '', 'c', 'personal_item_dax'),
                cells('', '', 'd', '', '', '', '', '', 'augment_part', '', '3'),
                cells('', 'S09L01', 'e', 'unknown_thing')]
        open(os.path.join(d, 'unique_loot.csv'), 'w').write('\n'.join(rows) + '\n')
        es2data.configure(self.dir.name)
        sectors._unique = None

    def tearDown(self):
        sectors._unique = None
        es2data.configure(None)
        self.dir.cleanup()

    def test_named_only(self):
        loot = sectors.orbit_unique_loot('S04L01')
        self.assertEqual(2, len(loot), 'the rarity roll, the personal item and the augment parts left out')
        self.assertEqual(12, loot[1]['amount'])

    def test_resolved(self):
        st = [{'orbit': {'containers': {'count': 2, 'loot': sectors.orbit_unique_loot('S04L01')}}},
              {'orbit': {'containers': {'count': 1, 'loot': sectors.orbit_unique_loot('S09L01')}}}]
        sectors.resolve_container_loot(st, {'sensor_okkar', 'es2_solar_particles'}, log=lambda *a: None)
        self.assertEqual([{'item': 'es2_ships:sensor_okkar', 'amount': 1}, {'item': 'es2_ships:es2_solar_particles', 'amount': 12}],
                         st[0]['orbit']['containers']['loot'])
        self.assertNotIn('loot', st[1]['orbit']['containers'], 'nothing the mod has: no loot field')


if __name__ == '__main__':
    unittest.main()
