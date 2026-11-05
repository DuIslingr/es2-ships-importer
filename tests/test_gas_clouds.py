"""ES2's plasma fields as GoF2's gas clouds (tools/sectors.py level_gas_clouds): their places (ES2 cm -> game units) within
GAS_CLOUD_RANGE of the station, the plasma by the location's ES2 level, none on a planet-side level. A small level in
FModel's form stands in for the export's."""
from pathlib import Path
import sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors


def field(root_index):
    return {'Type': 'BP_PlasmaField_C', 'Properties': {'RootComponent': {'ObjectPath': f'/Game/Maps/L.{root_index}'}}}


def place(x): return {'Type': 'SceneComponent', 'Properties': {'RelativeLocation': {'X': x, 'Y': 0.0, 'Z': 0.0}}}


class GasCloudTests(unittest.TestCase):
    def setUp(self):
        level = [place(500000.0), place(0.0), place(5000000.0), field(0), field(1), field(2)]
        self.level = sectors._level
        sectors._level = lambda es2_id: level

    def tearDown(self):
        sectors._level = self.level

    def test_places_and_plasma(self):
        g = sectors.level_gas_clouds('S01L99', 5)
        self.assertEqual(1, len(g['clouds']), 'the one on the station and the one past the orbit left out')
        self.assertEqual(100000, abs(g['clouds'][0][0]) + abs(g['clouds'][0][1]) + abs(g['clouds'][0][2]), '500000 cm x 0.2')
        self.assertEqual(201, g['plasma'], 'a low level: Green')
        self.assertEqual(204, sectors.level_gas_clouds('S01L99', 28)['plasma'], 'the deepest: Red')

    def test_planet_side(self):
        self.assertIsNone(sectors.level_gas_clouds('S05L03P', 5), 'GoF2 never lands')
        self.assertIsNone(sectors.level_gas_clouds('S05L03P_Cave', 5))


if __name__ == '__main__':
    unittest.main()
