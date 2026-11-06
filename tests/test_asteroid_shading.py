"""ES2's generic asteroid masters as tools/sectors.py bakes them (M_Asteroid_Rock_Parent / M_Asteroid_Ice_Parent's compiled
base-pass pixel shaders): UE's overlay blend, the masters' contrast curve and the sRGB encoding of the baked colour."""
from pathlib import Path
import sys, unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors


class AsteroidShadingTests(unittest.TestCase):
    def test_overlay(self):
        self.assertAlmostEqual(0.32, float(sectors._overlay(np.float32(0.4), np.float32(0.4))), 5, '2 base blend below a half')
        self.assertAlmostEqual(0.68, float(sectors._overlay(np.float32(0.6), np.float32(0.6))), 5, 'the screen above it')

    def test_contrast(self):
        x = np.array([0.0, 0.25, 0.5, 0.75, 1.0], np.float32)
        np.testing.assert_allclose([0.0, 0.5 * 0.5 ** 0.5, 0.5, 1 - 0.5 * 0.5 ** 0.5, 1.0], sectors._contrast(x, 0.5), atol=1e-5)
        np.testing.assert_allclose([0.0, 0.125, 0.5, 0.875, 1.0], sectors._contrast(x, 2.0), atol=1e-5)

    def test_srgb(self):
        self.assertEqual([0, 188, 255], sectors._srgb(np.array([0.0, 0.5, 1.0])).tolist())

    def test_rock_colour_range(self):
        # (RockColor over the curvature's middle, to the power 1.5: a mid grey, as the game's rocks)
        c = sectors._overlay(np.array(sectors.ROCK_COLOR, np.float32), np.float32(0.5)) ** 1.5
        self.assertTrue(np.all(c > 0.2) and np.all(c < 0.3), c)


if __name__ == '__main__':
    unittest.main()
