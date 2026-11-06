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

    def test_cratered(self):
        s = self.sphere('MI_Planet_Cratered_A')
        self.assertEqual('es2Cratered', s['look'])
        self.assertIn('surface2', s['maps'], 'the rock beside the craters')
        self.assertNotIn('colors', s, 'grey')

    def test_volcanic(self):
        s = self.sphere('MI_Planet_Volcanic_A', variation=0.1)
        self.assertEqual('es2Volcanic', s['look'])
        self.assertEqual([1.0, 0.25, 0.1], s['colors'][1], "M_Planet_Volcanic's LavaColor")
        self.assertIn('noise2', s['maps'])

    def test_ice_and_water_have_clouds(self):
        for m, look in (('MI_Planet_Ice_A', 'es2Ice'), ('MI_Planet_Water_A', 'es2Water')):
            s = self.sphere(m)
            self.assertEqual(look, s['look'])
            self.assertIn('clouds', s['maps']); self.assertIn('cloudsNormal', s['maps'])
        self.assertEqual([0.08, 0.156, 0.2], self.sphere('MI_Planet_Water_A')['colors'][0], "M_Planet_Water's Color")

    def test_earthlike(self):
        s = self.sphere('MI_Planet_Earthlike_A')
        self.assertEqual('es2Earthlike', s['look'])
        self.assertNotIn('colors', s, "its colours are the shader's own")
        self.assertIn('clouds', s['maps'])

    def test_okkar_desert_is_the_desert(self):
        self.assertEqual('es2Desert', self.sphere('MI_Planet_Desert_Okkar')['look'])

    def test_desert_has_no_colours(self):
        s = self.sphere('MI_Planet_Desert_A')
        self.assertNotIn('colors', s)

    def test_unknown_master(self):
        self.assertIsNone(sectors.planet_sphere({'material': 'MI_Planet_Lava_X'}))


if __name__ == '__main__':
    unittest.main()
