"""The ES2 encounters (tools/encounters.py): only the remake's kinds, unique ids, sane weights and conditions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import encounters

KINDS = {'pirates', 'trader', 'derelict', 'distress', 'flyby', 'quest', 'battle', 'trap', 'stash', 'depot', 'highrisk'}


class EncounterTests(unittest.TestCase):
    def test_entries(self):
        enc = encounters.build()
        self.assertEqual(5, len(enc))
        self.assertEqual(len(enc), len({e['id'] for e in enc}), 'unique ids')
        for e in enc:
            self.assertIn(e['kind'], KINDS)
            self.assertGreater(e['weight'], 0)
            for s in e.get('security', []): self.assertIn(s, (0, 1, 2, 3))
        self.assertNotIn('name', next(e for e in enc if e['kind'] == 'trap'), 'a trap passes for an unknown signal')


if __name__ == '__main__':
    unittest.main()
