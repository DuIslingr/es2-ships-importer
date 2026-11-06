"""ES2's planet masters as the remake's lit spheres (tools/sectors.py planet_sphere, stations.json "planetSphere"): the look,
its maps written into the mod, and for the gas giants their masters' two colours and the planet's variation."""
from pathlib import Path
import os, sys, tempfile, unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors, jobs


class PlanetSphereTests(unittest.TestCase):
    def sphere(self, material, **pl):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as mod:
            for f in sectors.SPHERES[material][1].values():
                os.makedirs(os.path.dirname(os.path.join(src, f)), exist_ok=True)
                Image.fromarray(np.zeros((8, 8, 4), np.uint8)).save(os.path.join(src, f))
            saved = (sectors.SRC, sectors.MOD)
            try:
                sectors.SRC, sectors.MOD = src, mod
                out = sectors.planet_sphere(dict(material=material, **pl))
                jobs.flush()
                for rel in out['maps'].values(): self.assertTrue(os.path.exists(os.path.join(mod, rel)), rel)
            finally:
                sectors.SRC, sectors.MOD = saved
        return out

    def test_gas_smooth(self):
        s = self.sphere('MI_Planet_GasSmooth_A', variation=1.3, atmosphere=[0.2, 0.5, 0.6])
        self.assertEqual('es2GasSmooth', s['look'])
        self.assertEqual([[0.02, 0.071433, 0.1], [0.166665, 0.487763, 0.5]], s['colors'], "M_Planet_GasSmooth's Color / Color2")
        self.assertAlmostEqual(0.3, s['variation'], 4, 'a whole turn more is the same hue')
        self.assertEqual({'surface', 'normal', 'capNormal', 'capColour', 'noise'}, set(s['maps']))

    def test_gas_bands(self):
        s = self.sphere('MI_Planet_Gas_A')
        self.assertEqual('es2Gas', s['look'])
        self.assertEqual(0.5, s['variation'], 'the PlanetData default')
        self.assertNotIn('capNormal', s['maps'], 'no poles')

    def test_desert_has_no_colours(self):
        s = self.sphere('MI_Planet_Desert_A')
        self.assertNotIn('colors', s)

    def test_unknown_master(self):
        self.assertIsNone(sectors.planet_sphere({'material': 'MI_Planet_Lava_X'}))


if __name__ == '__main__':
    unittest.main()
