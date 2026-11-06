"""The ES2 encounters (tools/encounters.py): only the remake's kinds, unique ids, sane weights and conditions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import encounters

KINDS = {'pirates', 'trader', 'derelict', 'distress', 'flyby', 'quest', 'battle', 'trap', 'stash', 'depot', 'highrisk', 'lootdrone', 'rift', 'minesweeper', 'challenge', 'needy'}


class EncounterTests(unittest.TestCase):
    def test_entries(self):
        enc = encounters.build()
        self.assertEqual(10, len(enc))
        self.assertEqual(len(enc), len({e['id'] for e in enc}), 'unique ids')
        for e in enc:
            self.assertIn(e['kind'], KINDS)
            if e['kind'] == 'rift':
                self.assertEqual({'id', 'kind'}, set(e) - {'bosses'}, "a mod's rift only adds bosses: its chance is the remake's")
                continue
            self.assertGreater(e['weight'], 0)
            for s in e.get('security', []): self.assertIn(s, (0, 1, 2, 3))
        self.assertNotIn('name', next(e for e in enc if e['kind'] == 'trap'), 'a trap passes for an unknown signal')


class EncounterMusicTests(unittest.TestCase):
    def test_music(self):
        enc = encounters.build({'rift': 'es2_rift', 'highrisk': 'es2_highrisk'})
        self.assertEqual('es2_rift', next(e for e in enc if e['kind'] == 'rift')['music'])
        self.assertEqual('es2_highrisk', next(e for e in enc if e['kind'] == 'highrisk')['music'])
        self.assertNotIn('music', next(e for e in enc if e['kind'] == 'battle'), 'the system\'s battle music')
        self.assertTrue(all('music' not in e for e in encounters.build()), 'none without the tracks')


class RiftBossTests(unittest.TestCase):
    def test_rift_bosses(self):
        import os, tempfile, es2data
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'DataFiles'))
            open(os.path.join(d, 'DataFiles', 'npc_leveling.CSV'), 'w').write(
                'Factor|~0.004\nBP_Okkar_Corvette|~25|~28|~0|~0|~2000|~0|~300|~80\nBP_Outlaw_DroneCarrier|~0|~0|~0|~0|~700|~0|~0|~70\n')
            es2data.configure(d)
            try: b = encounters.rift_bosses()
            finally: es2data.configure(None)
        self.assertEqual([{'ship': 'es2_ships:es2_okkar_corvette', 'raiders': 7.42, 'race': 'es2_ships:okkar'}] * 2
                         + [{'ship': 'es2_ships:es2_drone_carrier', 'raiders': 2.26, 'race': 'es2_ships:outlaw'}], b,
                         "its hull + armour + shield over the raider's 310; the corvette twice, as ES2 picks it")


if __name__ == '__main__':
    unittest.main()
