"""The sectors' places (tools/sectors.py): which ES2 places get a wreck field (by name or subtitle)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors


class WreckPlaceTests(unittest.TestCase):
    def test_wreck_places(self):
        self.assertTrue(sectors.is_wreck_place({'name': 'Ghost Fleet', 'subtitle': 'Wreck Field'}))
        self.assertTrue(sectors.is_wreck_place({'name': 'Warship Remains', 'subtitle': None}))
        self.assertTrue(sectors.is_wreck_place({'name': 'Charybdis Bowl', 'subtitle': 'Scrapyard'}))
        self.assertFalse(sectors.is_wreck_place({'name': 'Ceto Outer Rim', 'subtitle': 'Planetary Debris'}), 'rock debris, not wrecks')
        self.assertFalse(sectors.is_wreck_place({'name': 'Rhodia II', 'subtitle': 'Homebase'}))



class HazardTests(unittest.TestCase):
    def test_level_hazards(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/T.{i}'}
            level = [
                obj(0, 'BP_RadiationField_C', RootComponent=ref(1), Sphere=ref(2)),
                obj(1, 'SceneComponent', RelativeLocation={'X': 500000, 'Y': 0, 'Z': 0}),
                obj(2, 'SphereComponent', SphereRadius=15000.0),
                obj(3, 'BP_HeatDamageVolume_C', RootComponent=ref(4), Sphere=ref(5)),
                obj(4, 'SceneComponent', RelativeLocation={'X': 1000, 'Y': 0, 'Z': 0}),   # (at the station: left out)
                obj(5, 'SphereComponent', SphereRadius=10000.0),
            ]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'T.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: h = sectors.level_hazards('T')
            finally: sectors.SRC = old
        self.assertEqual([{'kind': 'radiation', 'centre': [0, 0, 100000], 'radius': 3000}], h, '5 km ahead, 150 m across; the one at the station left out')


if __name__ == '__main__':
    unittest.main()
