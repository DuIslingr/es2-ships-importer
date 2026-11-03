"""The parts' mesh sockets as remake mounts (tools/build.py part_mounts): the contrail points (slotType 6, the socket's scale)
and the headlight fixtures (slotType 7, the way they shine) beside the guns and exhausts. Stdlib only: a synthetic socket
JSON beside a fake .glb path, no game files."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build


def socket(name, x, y, z, pitch=0.0, yaw=0.0, roll=0.0, scale=None):
    p = {'SocketName': name, 'RelativeLocation': {'X': x, 'Y': y, 'Z': z}, 'RelativeRotation': {'Pitch': pitch, 'Yaw': yaw, 'Roll': roll}}
    if scale is not None: p['RelativeScale'] = {'X': scale, 'Y': scale, 'Z': scale}
    return {'Type': 'StaticMeshSocket', 'Properties': p}


class PartMountTests(unittest.TestCase):
    def mounts(self, sockets):
        with tempfile.TemporaryDirectory() as d:
            glb = os.path.join(d, 'part.glb')
            with open(glb[:-4] + '.json', 'w', encoding='utf-8') as f: json.dump(sockets, f)
            return build.part_mounts(glb)

    def test_contrail_sockets_become_slot_6_with_their_scale(self):
        out = self.mounts([socket('SKT_Contrail_022', -724.9, -736.5, -296.9, pitch=-90.0, roll=180.0, scale=0.5),
                           socket('SKT_Contrail_023', -743.2, 727.5, 133.9, pitch=-90.0, roll=180.0)])
        contrails = [m for m in out if m['slotType'] == 6]
        self.assertEqual(2, len(contrails))
        self.assertEqual(0.5, contrails[0]['socketScale'], 'the socket\'s largest axis sizes the ribbon')
        self.assertNotIn('socketScale', contrails[1], 'scale 1 is the default')
        # Unreal (X fwd, Y side, Z up) cm -> position_engine game units: (-Y, Z, X) / 100 x GAME
        self.assertEqual([round(736.5 / 100 * build.GAME, 1), round(-296.9 / 100 * build.GAME, 1), round(-724.9 / 100 * build.GAME, 1)], contrails[0]['position_engine'])

    def test_headlight_sockets_become_slot_7_shining_along_their_forward(self):
        out = self.mounts([socket('SKT_HeadLight_033', 502.9, 304.0, 85.5, pitch=0.32, yaw=0.05),
                           socket('SKT_HeadLight_01', 162.7, -44.0, 6.0, roll=-90.0)])
        lights = [m for m in out if m['slotType'] == 7]
        self.assertEqual(2, len(lights))
        for m in lights:
            self.assertNotIn('socketScale', m)
            d = m['direction']
            self.assertAlmostEqual(1.0, sum(c * c for c in d) ** 0.5, places=2, msg='a unit vector')
            self.assertGreater(d[2], 0.99, 'the fixtures face forward (position_engine z)')

    def test_the_counts_include_the_new_sockets(self):
        with tempfile.TemporaryDirectory() as d:
            glb = os.path.join(d, 'part.glb')
            with open(glb[:-4] + '.json', 'w', encoding='utf-8') as f:
                json.dump([socket('SKT_Contrail_1', 0, 0, 0), socket('SKT_HeadLight_1', 0, 0, 0), socket('SKT_Engine_1', 0, 0, 0)], f)
            c = build.socket_counts(glb)
        self.assertEqual({0: 0, 1: 0, 2: 0, 3: 1, 5: 0, 6: 1, 7: 1}, c)


if __name__ == '__main__':
    unittest.main()
