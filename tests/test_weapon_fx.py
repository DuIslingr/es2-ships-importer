"""ES2's weapon looks baked into the remake's fx sprites (tools/weapon_fx.py): its glow's and beams' profiles as its compiled
shaders give them, every primary family a sprite for each part its GoF2 base has, the PNGs written into the mod."""
from pathlib import Path
import os, sys, tempfile, unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import weapon_fx, weapons


class WeaponFxTests(unittest.TestCase):
    def test_hot_profile(self):
        self.assertAlmostEqual(1.0, float(weapon_fx.hot(np.float32(1.0), 98.0)), 6, 'the centre: full')
        self.assertAlmostEqual(0.5 / (0.5 * 8 + 1), float(weapon_fx.hot(np.float32(0.5), 8.0)), 6, 'p / ((1 - p) k + 1)')

    def test_glow_falls_to_nothing_at_its_edge(self):
        g = weapon_fx.glow(64, rays=False)
        self.assertGreater(g[32, 32], 0.7, "near the centre (half a pixel off: (0.978 / 1.18)^1.5)")
        self.assertAlmostEqual(0.0, float(g[32, 0]), 3, 'max(1 - 2r, 0): none at the rim')

    def test_contrast(self):
        np.testing.assert_allclose([0.0, 0.5, 1.0], weapon_fx._contrast(np.array([0.0, 0.5, 1.0]), 8.0), atol=1e-6)

    def test_tone_keeps_the_colour_where_faint(self):
        px = weapon_fx.tone(np.array([[0.05, 50.0]], np.float32), '#5aa0ff')
        self.assertGreater(px[0, 0, 2], px[0, 0, 0], 'faint: blue')
        self.assertTrue(np.all(px[0, 1, :3] > 240), 'bright: white-hot')

    def test_every_family_bakes_its_parts(self):
        with tempfile.TemporaryDirectory() as mod:
            weapon_fx.configure(None, mod); weapon_fx._made.clear()
            try:
                for fam, spec in weapons.PRIMARY.items():
                    p = weapon_fx.parts(fam, spec[1], spec[2])
                    self.assertIsNotNone(p, fam)
                    self.assertIn('projectile', p); self.assertIn('muzzle', p)
                    self.assertEqual(spec[1] != 'scatter', 'impact' in p, f'{fam}: an impact unless its base is a scatter gun')
                    for part in p.values():
                        im = Image.open(os.path.join(mod, part['sprite']))
                        self.assertEqual('RGBA', im.mode)
                beam = weapon_fx.parts('BeamLaser', 'beam', '#ff4a3a')['projectile']
                self.assertNotIn('alongFlight', beam, 'the remake fits a beam sprite along the beam itself')
                bolt = weapon_fx.parts('PulseLaser', 'laser', '#ff5a3c')['projectile']
                self.assertTrue(bolt['alongFlight'] and bolt['stretch'] > 1, 'a bolt streaks along its flight')
            finally:
                weapon_fx.configure(None, None)
        self.assertIsNone(weapon_fx.parts('HomingMissileLauncher', 'missile', '#ffd0a0'), 'the missiles keep their models')


if __name__ == '__main__':
    unittest.main()
