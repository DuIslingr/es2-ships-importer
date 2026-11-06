"""Who flies where (tools/sectors.py orbit_spawns): location_spawns.CSV's faction weights as an orbit's "locals" (the
friendly factions, heaviest first) and "raiders" (the hostile ones), the cargo, capital, creature and resource columns
left out, the Bloodstar counted as Outlaws. A small table in ES2's form stands in for the export's."""
from pathlib import Path
import os, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import es2data, sectors


class SpawnTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = os.path.join(self.dir.name, 'DataFiles')
        os.makedirs(d)
        open(os.path.join(d, 'location_spawns.CSV'), 'w').write(
            '|~busyness|~gb|~gb_capital|~okkar|~outlaw|~outlaw_bloodstar|~freelancer|~asteroid_crawler\n'
            'S01L01|~1|~0|~0|~0|~0|~0|~0|~3\n'
            'S02L05|~2|~1|~5|~4|~1|~2|~2|~0\n')
        es2data.configure(self.dir.name)
        sectors._spawns = None

    def tearDown(self):
        sectors._spawns = None
        es2data.configure(None)
        self.dir.cleanup()

    def test_spawns(self):
        self.assertEqual((['okkar', 'freelancer', 'gb'], ['outlaw']), sectors.orbit_spawns('S02L05'))
        self.assertEqual(([], []), sectors.orbit_spawns('S01L01'), 'creatures only: the system decides')
        self.assertEqual(([], []), sectors.orbit_spawns('S09L99'), 'not in the table')


if __name__ == '__main__':
    unittest.main()
