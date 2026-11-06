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
        self.assertEqual([('web', 18000, 38), ('corrosion', 8640, 4)], [(x['kind'], x['radius'], x['count']) for x in m],
                         "the blueprint's 25 000 cm x 0.2 x 3.6 with 38 mines at 12 000 cm apart; the actor's own 12 000 cm holds 4; "
                         "the cryo field on the station left out")
        self.assertEqual([0, 0, 100000], m[0]['centre'], "UE's X (forward) is the game's Z, as the hazards' places")
        self.assertNotIn('minRank', m[0], "the remake's gate: its defaults")
        self.assertEqual(40, sectors.minefield_count(50000, 12000, 40), 'at most MaxMineAmount')
        self.assertEqual(3, sectors.minefield_count(1000, 12000, 40), 'at least 3')


class CloakedContainerTests(unittest.TestCase):
    def test_level_cloaked_containers(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/C9L01.{i}'}
            level = [obj(0, 'BP_Activity_InvisibleContainer_C', RootComponent=ref(1)),
                     obj(1, 'SceneComponent', RelativeLocation={'X': 500000, 'Y': 0, 'Z': 0}),
                     obj(2, 'BP_Activity_InvisibleContainer_C', RootComponent=ref(3)),
                     obj(3, 'SceneComponent', RelativeLocation={'X': 0, 'Y': 0, 'Z': 100000})]
            for name in ('C9L01', 'C9L01P'): json.dump(level, open(os.path.join(d, 'Maps', 'Locations', name + '.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: c, planet = sectors.level_cloaked_containers('C9L01'), sectors.level_cloaked_containers('C9L01P')
            finally: sectors.SRC = old
        self.assertEqual([[0, 20000, 0], [0, 0, 100000]], c, "cm x 0.2, the nearest first (UE's Z is up)")
        self.assertEqual([], planet, 'planet-side: left out')


class SecureContainerTests(unittest.TestCase):
    def test_level_secure_containers(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/K9L01.{i}'}
            loc = lambda x: {'X': x, 'Y': 0, 'Z': 0}
            level = [obj(0, 'BP_ItemContainer_Armored_C', RootComponent=ref(1), ShotTriggersRequired=[ref(2), ref(4)]),
                     obj(1, 'SceneComponent', RelativeLocation=loc(100000)),
                     obj(2, 'BP_ShotTrigger_C', RootComponent=ref(3), ShotTriggerChainPreviousOne=ref(4)),
                     obj(3, 'SceneComponent', RelativeLocation=loc(110000)),
                     obj(4, 'BP_ShotTrigger_C', RootComponent=ref(5), Retriggerable=True),
                     obj(5, 'SceneComponent', RelativeLocation=loc(120000)),
                     obj(6, 'BP_ItemContainer_Armored_C', RootComponent=ref(1), EnergyOrbsRequired=[ref(5)])]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'K9L01.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: s, plain = sectors.level_secure_containers('K9L01'), sectors.level_containers('K9L01')
            finally: sectors.SRC = old
        self.assertEqual(1, len(s), 'the orb-locked one without a dispenser stays a bulletproof container')
        self.assertEqual([0, 0, 20000], s[0]['at'])
        self.assertEqual([[0, 0, 24000], [0, 0, 22000]], s[0]['triggers'], 'in chain order: the one named as previous first')
        self.assertTrue(s[0]['ordered'])
        self.assertEqual(3.0, s[0]['retrigger'], "BP_ShotTrigger's RegtriggerDelay")
        self.assertEqual(1, plain['count'], 'the secure one not counted twice')


class SocketContainerTests(unittest.TestCase):
    def test_orb_and_coil_sockets(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/E9L01.{i}'}
            loc = lambda i, x: obj(i, 'SceneComponent', RelativeLocation={'X': x, 'Y': 0, 'Z': 0})
            level = [obj(0, 'BP_ItemContainer_Armored_C', RootComponent=ref(1), EnergyOrbsRequired=[ref(2)], EnergyCoilSocketsRequired=[ref(4)]), loc(1, 100000),
                     obj(2, 'BP_EnergyOrb_Socket_C', RootComponent=ref(3)), loc(3, 105000),
                     obj(4, 'BP_EnergyCoil_Socket_C', RootComponent=ref(5)), loc(5, 95000),
                     obj(6, 'BP_EnergyOrb_Dispenser_C', RootComponent=ref(7)), loc(7, 300000),
                     obj(8, 'BP_EnergyOrb_Dispenser_C', RootComponent=ref(9), EnergyOrbSocketsConnected=[ref(2)]), loc(9, 500000),
                     obj(10, 'BP_Portable_EnergyCoil_C', RootComponent=ref(11)), loc(11, 90000),
                     obj(12, 'BP_ItemContainer_Armored_C', RootComponent=ref(1), EnergyCoilSocketsRequired=[ref(4)])]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'E9L01.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: s, plain = sectors.level_secure_containers('E9L01'), sectors.level_containers('E9L01')
            finally: sectors.SRC = old
        self.assertEqual(1, len(s), 'the second wants the only coil, already given: a bulletproof one')
        self.assertNotIn('triggers', s[0])
        self.assertEqual([{'at': [0, 0, 21000], 'orb': [0, 0, 100000]}, {'at': [0, 0, 19000], 'coil': [0, 0, 18000]}], s[0]['sockets'],
                         'the dispenser listing the socket, not the nearer one; the nearest loose coil')
        self.assertEqual(1, plain['count'])


class ConductorContainerTests(unittest.TestCase):
    def test_conductor_locked(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/R9L01.{i}'}
            loc = lambda i, x: obj(i, 'SceneComponent', RelativeLocation={'X': x, 'Y': 0, 'Z': 0})
            L1 = 'EConductorLayer::NewEnumerator1'
            level = [obj(0, 'BP_ItemContainer_Armored_C', RootComponent=ref(1), ConductorReceiverRequired=[ref(2)]), loc(1, 100000),
                     obj(2, 'BP_Conductor_Receiver_C', RootComponent=ref(3), ConductorLayer=L1), loc(3, 110000),
                     obj(4, 'BP_Conductor_Source_C', RootComponent=ref(5), ConductorLayer=L1), loc(5, 140000),
                     obj(6, 'BP_Conductor_Portable_Okkar_C', RootComponent=ref(7), ConductorLayer=L1, **{'Conduction Sphere Radius': 15000.0}), loc(7, 130000),
                     obj(8, 'BP_Conductor_Static_C', RootComponent=ref(9), ConductorLayer='EConductorLayer::NewEnumerator2'), loc(9, 120000),
                     obj(10, 'BP_Conductor_Source_C', RootComponent=ref(11), ConductorLayer=L1), loc(11, 900000)]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'R9L01.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: s = sectors.level_secure_containers('R9L01')
            finally: sectors.SRC = old
        c = s[0]['conductors']
        self.assertEqual([[0, 0, 22000, 40]], c['receivers'], "the receiver's 200 cm")
        self.assertEqual([[0, 0, 28000, 4000]], c['sources'], 'the near source on its layer; the far one out of reach')
        self.assertEqual([[0, 0, 26000, 3000]], c['portables'], 'its own 15 000 cm')
        self.assertNotIn('statics', c, 'another layer')

    def test_conductor_solvable(self):
        src, rec = [0, 0, 0, 4000], [0, 0, 10000, 40]
        self.assertFalse(sectors.conductor_solvable({'sources': [src], 'receivers': [rec]}), '500 m apart, nothing to bridge it')
        self.assertTrue(sectors.conductor_solvable({'sources': [src], 'receivers': [rec], 'portables': [[0, 0, 0, 4000], [0, 0, 0, 4000]]}),
                        'two 200 m portables: 200 + 200 + 200 >= 500 m')
        self.assertFalse(sectors.conductor_solvable({'sources': [src], 'receivers': [rec], 'portables': [[0, 0, 0, 2000]]}))
        self.assertTrue(sectors.conductor_solvable({'sources': [src], 'statics': [[0, 0, 4000, 4000], [0, 0, 8000, 4000]], 'receivers': [rec]}), 'relays on the way')


class PuzzleSoundTests(unittest.TestCase):
    def test_puzzle_sounds_only_with_secure_containers(self):
        import audio
        old = audio.available; audio.available = lambda: False
        try: self.assertEqual(0, sectors.write_puzzle_sounds([{'orbit': {'containers': {'count': 3}}}]), 'no secure containers: nothing')
        finally: audio.available = old
        self.assertEqual({'grab', 'hold', 'drop', 'throw', 'dispenser', 'conductor', 'unlock'}, set(sectors.PUZZLE_SOUNDS),
                         "the remake's PuzzleSoundRoles")


class AcidSackTests(unittest.TestCase):
    def test_level_acid_sacks(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations'))
            def obj(i, t, **props): return {'Type': t, 'Name': f'o{i}', 'Properties': props}
            ref = lambda i: {'ObjectPath': f'/Game/Maps/Locations/A9L01.{i}'}
            level = [obj(0, 'BP_AcidSack_Base_C', RootComponent=ref(1)), obj(1, 'StaticMeshComponent', RelativeLocation={'X': 100000, 'Y': 0, 'Z': 0}),
                     obj(2, 'BP_AcidSack_Base_Anemone_C', RootComponent=ref(3)), obj(3, 'StaticMeshComponent', RelativeLocation={'X': 0, 'Y': 0, 'Z': 50000}),
                     obj(4, 'BP_AcidSack_C', RootComponent=ref(1))]
            for n in ('A9L01', 'A9L01P'): json.dump(level, open(os.path.join(d, 'Maps', 'Locations', n + '.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d
            try: a, planet = sectors.level_acid_sacks('A9L01'), sectors.level_acid_sacks('A9L01P')
            finally: sectors.SRC = old
        self.assertEqual([[0, -13000, 46000], [0, 23000, -26000]], a, 'the bases (not the pouches they grow), spread x 3.6 about their centre')
        self.assertEqual([], planet)


class UniqueRockTests(unittest.TestCase):
    def test_unity_euler(self):
        self.assertEqual([0.0, 90.0, 0.0], [abs(x) if x == 0 else x for x in sectors.unity_euler({'Yaw': 90})], "UE's yaw about up: Unity's y")
        self.assertEqual(30.0, sectors.unity_euler({'Pitch': 30})[0])
        self.assertEqual(45.0, sectors.unity_euler({'Roll': 45})[2])

    def test_level_props(self):
        import json, os, tempfile
        mesh = sectors.UNIQUE_ROCKS[0]
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'Maps', 'Locations')); os.makedirs(os.path.join(d, 'Assets/Environment/Asteroids/Meshes'))
            json.dump([{'Type': 'StaticMesh', 'Properties': {'ExtendedBounds': {'BoxExtent': {'X': 5000, 'Y': 2000, 'Z': 1000}}}}],
                      open(os.path.join(d, 'Assets/Environment/Asteroids/Meshes', mesh + '.json'), 'w'))
            sm = {'ObjectName': f"StaticMesh'{mesh}'"}
            level = [{'Type': 'StaticMeshComponent', 'Properties': {'StaticMesh': sm, 'RelativeLocation': {'X': 500000, 'Y': 0, 'Z': 0}, 'RelativeScale3D': {'X': 2, 'Y': 2, 'Z': 2}}},
                     {'Type': 'StaticMeshComponent', 'Properties': {'StaticMesh': sm, 'RelativeLocation': {'X': 1000, 'Y': 0, 'Z': 0}}},
                     {'Type': 'StaticMeshComponent', 'Properties': {'StaticMesh': sm, 'AttachParent': {}, 'RelativeLocation': {'X': 600000, 'Y': 0, 'Z': 0}}},
                     {'Type': 'StaticMeshComponent', 'Properties': {'StaticMesh': {'ObjectName': "StaticMesh'SM_Asteroid_Rock_Generic_Unique_099'"}, 'RelativeLocation': {'X': 700000, 'Y': 0, 'Z': 0}}}]
            json.dump(level, open(os.path.join(d, 'Maps', 'Locations', 'U9L01.json'), 'w'))
            old = sectors.SRC; sectors.SRC = d; sectors._rock_extents.clear()
            try: p = sectors.level_props('U9L01')
            finally: sectors.SRC = old; sectors._rock_extents.clear()
        self.assertEqual(1, len(p), 'the one on the station, the attached one and a mesh not taken left out')
        self.assertEqual([0, 0, 100000], p[0]['at'])
        self.assertEqual(4000, p[0]['size'], '10 000 cm x scale 2 x 0.2')
        self.assertTrue(p[0]['model'].startswith('rocks/'))


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
