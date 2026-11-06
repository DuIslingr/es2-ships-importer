"""ES2's wreck fields' hulls (tools/sectors.py wreck_models): the orbit "wrecks" "models" from SM_Wrecks_*, none (containers
only, logged) when the export lacks the meshes."""
from pathlib import Path
import sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sectors, warships


class WreckHullTests(unittest.TestCase):
    def test_without_meshes(self):
        lines = []
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as mod:
            saved = (sectors.SRC, sectors.MOD, sectors.LOG, list(sectors._wreck_models), warships.SRC)
            try:
                sectors.SRC, sectors.MOD, sectors.LOG = src, mod, lines.append
                sectors._wreck_models.clear(); warships.SRC = None
                self.assertIsNone(sectors.wreck_models())
            finally:
                sectors.SRC, sectors.MOD, sectors.LOG = saved[:3]
                sectors._wreck_models[:] = saved[3]; warships.SRC = saved[4]
        self.assertTrue(any('containers only' in l for l in lines), lines)

    def test_largest_is_the_size(self):
        self.assertIn('SM_Wrecks_010', sectors.WRECK_MESHES, 'the 400 m hull WRECK_SIZE stands for')
        self.assertFalse(set(sectors.WRECK_DEBRIS) & set(sectors.WRECK_MESHES), 'the debris apart from the hulls')
        self.assertLessEqual(sectors.WRECK_HULKS, 30, "the remake's most")
        assets = open(sectors.os.path.join(sectors.os.path.dirname(sectors.__file__), 'wreck_assets.txt')).read()
        for m in sectors.WRECK_MESHES + sectors.WRECK_DEBRIS: self.assertIn(m, assets, 'exported by wreck_assets.txt')
        self.assertEqual(8000, sectors.WRECK_SIZE, '40000 cm x 0.2')


if __name__ == '__main__':
    unittest.main()
