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

    def test_heat_as_raiders_fire(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/H.{i}'}
            level = [obj(0, 'BP_HeatDamageVolume_C', RootComponent=ref(1), Sphere=ref(2), DamagePerSecondMax=110.0),
                     obj(1, 'SceneComponent', RelativeLocation={'X': 500000, 'Y': 0, 'Z': 0}), obj(2, 'SphereComponent', SphereRadius=10000.0),
                     obj(3, 'BP_HeatDamageVolume_C', RootComponent=ref(4), Sphere=ref(2)),
                     obj(4, 'SceneComponent', RelativeLocation={'X': 600000, 'Y': 0, 'Z': 0})]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'H.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: h = sectors.level_hazards('H')
            finally: sectors.SRC = old
        self.assertEqual([2.0, 3.64], [x['raiderDps'] for x in h], "its own 110, else ES2's 200, over the raider's 55")

    def test_frost_and_corrosion_fields(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/F.{i}'}
            level = [obj(0, 'BP_FrostField_C', RootComponent=ref(1), Sphere=ref(2), Radius=70000.0),
                     obj(1, 'SceneComponent', RelativeLocation={'X': 500000, 'Y': 0, 'Z': 0}), obj(2, 'SphereComponent', SphereRadius=70000.0),
                     obj(3, 'BP_CorrosionField_C', RootComponent=ref(4), Radius=4000.0),
                     obj(4, 'SceneComponent', RelativeLocation={'X': 0, 'Y': 600000, 'Z': 0}),
                     obj(5, 'BP_DamageField_C', RootComponent=ref(4))]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'F.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: h = sectors.level_hazards('F')
            finally: sectors.SRC = old
        self.assertEqual([('frost', 14000), ('corrosion', 1000)], [(x['kind'], x['radius']) for x in h],
                         "700 m across; the corrosion's 40 m at the remake's 1000-unit least; the mining fire's damage field left out")
        self.assertNotIn('raiderDps', h[1], "the remake's default: ES2's intensity 5")


class StormTests(unittest.TestCase):
    def test_level_storm(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            level = [{'Type': 'BP_LightningField_C', 'Name': 'L', 'Properties': {'Frequency': 2.0, 'LightningScale': 1.5}}]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'S9L01.json'), 'w'))
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'S9L01P.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: s, planet, none = sectors.level_storm('S9L01'), sectors.level_storm('S9L01P'), sectors.level_storm('S9L02')
            finally: sectors.SRC = old
        self.assertEqual(2.0, s['frequency'], "the actor's own")
        self.assertEqual(80000, s['radius'], "the blueprint's 400 000 cm x 0.2")
        self.assertEqual(1.5, s['scale'])
        self.assertEqual(0.2, s['thunderChance'])
        self.assertEqual(7, len(s['thunder']))
        self.assertIsNone(planet, 'planet-side: left out')
        self.assertIsNone(none)


class MinefieldTests(unittest.TestCase):
    def test_level_minefields(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/M9L01.{i}'}
            level = [obj(0, 'BP_Minefield_Web_C', RootComponent=ref(1)),
                     obj(1, 'SceneComponent', RelativeLocation={'X': 500000, 'Y': 0, 'Z': 0}),
                     obj(2, 'BP_Minefield_Corrosion_C', RootComponent=ref(3), Radius=12000.0),
                     obj(3, 'SceneComponent', RelativeLocation={'X': 0, 'Y': 600000, 'Z': 0}),
                     obj(4, 'BP_Minefield_Cryo_C', RootComponent=ref(5)),
                     obj(5, 'SceneComponent', RelativeLocation={'X': 1000, 'Y': 0, 'Z': 0})]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'M9L01.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: m = sectors.level_minefields('M9L01')
            finally: sectors.SRC = old
        self.assertEqual([('web', 5000, 38), ('corrosion', 2400, 4)], [(x['kind'], x['radius'], x['count']) for x in m],
                         "the blueprint's 25 000 cm x 0.2 with 38 mines at 12 000 cm apart; the actor's own 12 000 cm holds 4; "
                         "the cryo field on the station left out")
        self.assertEqual([0, 0, 100000], m[0]['centre'], "UE's X (forward) is the game's Z, as the hazards' places")
        self.assertNotIn('minRank', m[0], "the remake's gate: its defaults")
        self.assertEqual(40, sectors.minefield_count(50000, 12000, 40), 'at most MaxMineAmount')
        self.assertEqual(3, sectors.minefield_count(1000, 12000, 40), 'at least 3')


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


class LaneTests(unittest.TestCase):
    def test_rotator(self):
        import numpy as np
        r = sectors._rotator({'Yaw': 90})
        np.testing.assert_allclose(r @ np.array([1.0, 0, 0]), [0, 1, 0], atol=1e-9, err_msg='yaw 90 turns X to Y')

    def test_level_lanes(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/L.{i}'}
            pt = lambda x, y, z: {'OutVal': {'X': x, 'Y': y, 'Z': z}}
            level = [
                obj(0, 'BP_SplineTraffic_C', RootComponent=ref(1), Spline=ref(2), SpeedFactor=1.5, OverrideCount=4, ClosedLoop=False),
                obj(1, 'SceneComponent', RelativeLocation={'X': 100000, 'Y': 0, 'Z': 0}, RelativeRotation={'Yaw': 90}),
                obj(2, 'SplineComponent', SplineCurves={'position': {'Points': [pt(0, 0, 0), pt(10000, 0, 0), pt(10000, 10000, 0)]}}),
                obj(3, 'BP_SplineTraffic_WorkerDrones_C', RootComponent=ref(1), Spline=ref(2)),
            ]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'L.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: lanes = sectors.level_lanes('L')
            finally: sectors.SRC = old
        self.assertEqual(1, len(lanes), 'the worker drones left out')
        l = lanes[0]
        # 1 km ahead; the spline turned 90 deg: its +X runs along ES2's +Y (the game's -x, 1 m = 20 units)
        self.assertEqual([[0, 0, 20000], [-2000, 0, 20000], [-2000, 0, 18000]], l['points'])
        self.assertEqual((4, 120.0, False), (l['count'], l['speed'], l['loop']))


if __name__ == '__main__':
    unittest.main()
