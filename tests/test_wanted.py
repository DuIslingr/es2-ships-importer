"""The ES2 bosses on the Most Wanted boards (tools/wanted.py): placed on the game's range by their ES2 hit points, in that
order, in the sectors their faction raids."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import es2data, wanted


class WantedTests(unittest.TestCase):
    def test_bosses(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'DataFiles'))
            open(os.path.join(d, 'DataFiles', 'npc_leveling.CSV'), 'w').write(
                'Factor|~0.004\nBP_OkkarPrime_Claw|~15|~15|~0|~0|~250|~150|~0|~13\n'
                'BP_Outlaw_Zero_Boss|~19|~30|~0|~0|~300|~120|~140|~40\nBP_Outlaw_Ravager_Boss|~22|~18|~0|~0|~2000|~1000|~0|~100\n')
            es2data.configure(d)
            try:
                ships = [{'id': x, 'name': x} for x in ('es2_okkarprime_claw', 'es2_outlaw_trapper', 'es2_outlaw_leader',
                                                        'es2_outlaw_raider', 'es2_outlaw_ravager')]
                systems = [{'id': 'es2_ceto', 'raiders': ['es2_ships:outlaw']}, {'id': 'es2_rhak', 'raiders': ['es2_ships:okkar_prime']}]
                w = wanted.build(ships, systems, {'gausscannon_okkar', 'coilgun', 'blaster', 'es2_resources_okkar_special'})
            finally: es2data.configure(None)
        self.assertEqual(['es2_okkarprime_claw', 'es2_outlaw_trapper', 'es2_outlaw_leader'], [e['id'] for e in w], 'weakest first')
        self.assertEqual([5000, 5500, 10000], [e['hitpoints'] for e in w], '400 / 560 / 3000 ES2 hit points on 5000-10000')
        self.assertEqual([50000, 55000, 140000], [e['reward'] for e in w])
        self.assertEqual([0, 1, 2], [e['requiredBounties'] for e in w])
        self.assertEqual(['es2_ships:es2_rhak'], w[0]['systems'])
        self.assertEqual(['es2_ships:es2_ceto'], w[2]['systems'])
        self.assertEqual(('es2_ships:es2_resources_okkar_special', 2), (w[0]['loot'], w[0]['lootAmount']))
        self.assertNotIn('escorts', w[0], 'no wingmen, no escorts')
        self.assertEqual(['es2_ships:es2_outlaw_ravager'], w[2]['escorts'], 'only the escorts the mod has')
        self.assertEqual('es2_ships:okkar_prime', w[0]['race'])


if __name__ == '__main__':
    unittest.main()
