"""An older build's drives part goes on a rebuild: the Khador Slipstream is the remake's own now."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build


class OldDrives(unittest.TestCase):
    def test_what_it_left_goes_and_the_rest_stays(self):
        with tempfile.TemporaryDirectory() as mod:
            os.makedirs(os.path.join(mod, 'warp'))
            os.makedirs(os.path.join(mod, 'icons/items'))
            for name in ('warp.json', 'warp/tunnel.png', 'blueprints.json', 'icons/items/es2_slipstream_ii.png', 'icons/items/es2_glacit.png'):
                open(os.path.join(mod, name), 'w').close()
            build.clear_old_drives(mod)
            self.assertEqual(sorted(os.listdir(mod)), ['icons'])
            self.assertEqual(os.listdir(os.path.join(mod, 'icons/items')), ['es2_glacit.png'])

    def test_there_is_no_drives_part(self):
        self.assertNotIn('drives', build.PARTS)
        self.assertNotIn('drives', build.resolve_parts('all')[0])


if __name__ == '__main__':
    unittest.main()
