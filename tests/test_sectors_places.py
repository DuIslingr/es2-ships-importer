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


class ContainerTests(unittest.TestCase):
    def test_level_containers(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/C.{i}'}
            level = [
                obj(0, 'BP_ItemContainer_C', RootComponent=ref(1)),
                obj(1, 'MovementRootComponent', RelativeLocation={'X': 100000, 'Y': 0, 'Z': 0}),
                obj(2, 'BP_ItemContainer_C', RootComponent=ref(3), ContainerType='EContainerType::OpenOnInteract'),
                obj(3, 'MovementRootComponent', RelativeLocation={'X': 300000, 'Y': 0, 'Z': 0}),
                obj(4, 'BP_ItemContainer_Armored_C', RootComponent=ref(5)),
                obj(5, 'MovementRootComponent', RelativeLocation={'X': 200000, 'Y': 0, 'Z': 0}),
                obj(6, 'BP_ItemContainer_C', RootComponent=ref(7)),
                obj(7, 'MovementRootComponent', RelativeLocation={'X': 200000, 'Y': 0, 'Z': 0}),
            ]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'C.json'), 'w'))
            json.dump([obj(0, 'BP_HeatDamageVolume_C')], open(os.path.join(d, 'Maps', 'Locations', 'E.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: c, none = sectors.level_containers('C'), sectors.level_containers('E')
            finally: sectors.SRC = old
        # 1, 3, 2, 2 km ahead (x 20 units a metre): centred 2 km ahead, 1 km either way -> 40000 across
        self.assertEqual({'count': 4, 'centre': [0, 0, 40000], 'spread': 40000, 'bulletproof': 0.5}, c, 'the bulletproof one and the armoured one')
        self.assertIsNone(none)


if __name__ == '__main__':
    unittest.main()
