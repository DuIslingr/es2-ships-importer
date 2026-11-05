"""ES2's ambience zones in space (tools/sectors.py level_ambience): a location's BP_MusicTrigger zones of the four space
sets as the remake's orbit "ambience" (the mod's sound names, ES2 cm -> game units, its inner radius x scale), the
planet-side ones left out. A small level in FModel's form stands in for the export's."""
from pathlib import Path
import sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors


def trigger(name, cue, root_index, radius):
    return {'Type': 'BP_MusicTrigger_C', 'Name': name, 'Properties': {
        'OverrideAmbience': {'ObjectName': f"SoundCue'{cue}'", 'ObjectPath': f'/Game/Audio/SFX/Ambience/X/{cue}.0'},
        'RootComponent': {'ObjectName': "SceneComponent'L:PersistentLevel.T.DefaultSceneRoot'", 'ObjectPath': f'/Game/Maps/L.{root_index}'},
        'InnerSphereRadius': radius}}


class AmbienceTests(unittest.TestCase):
    def setUp(self):
        level = [
            {'Type': 'SceneComponent', 'Properties': {'RelativeLocation': {'X': 100000.0, 'Y': 0.0, 'Z': 0.0}}},
            {'Type': 'SceneComponent', 'Properties': {'RelativeLocation': {'X': 0.0, 'Y': 0.0, 'Z': 0.0}, 'RelativeScale3D': {'X': 2.0, 'Y': 2.0, 'Z': 2.0}}},
            trigger('T1', 'S_SC_Ambience_Factory', 0, 50000.0),
            trigger('T2', 'S_SC_Outlaw_Station', 1, 20000.0),
            trigger('T3', 'S_SC_DesertPlanet_Underground', 1, 20000.0),
        ]
        self.level = sectors._level
        sectors._level = lambda es2_id: level
        self.zones = sectors.level_ambience('S01L99')

    def tearDown(self):
        sectors._level = self.level

    def test_space_sets_only(self):
        self.assertEqual(2, len(self.zones), 'the planet-side one left out')

    def test_zones(self):
        outlaw, factory = self.zones   # (nearest first)
        self.assertEqual(['es2amb_outlaw_station_001', 'es2amb_outlaw_station_002', 'es2amb_outlaw_station_003'], outlaw['loops'])
        self.assertEqual(8000, outlaw['radius'], '20000 cm x its scale 2 x 0.2')
        self.assertEqual([0, 0, 0], outlaw['centre'])
        self.assertNotIn('adds', outlaw)
        self.assertEqual(10, len(factory['adds']))
        self.assertEqual([4000, 10000], factory['addEveryMs'], "the cue's SoundNodeDelay")
        self.assertEqual(round(0.1 * sectors.AMBIENCE_GAIN, 2), factory['addVolume'])
        self.assertEqual(20000.0, abs(factory['centre'][0]) + abs(factory['centre'][1]) + abs(factory['centre'][2]), '100000 cm x 0.2')


if __name__ == '__main__':
    unittest.main()
