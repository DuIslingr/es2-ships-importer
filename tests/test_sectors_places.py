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


if __name__ == '__main__':
    unittest.main()
