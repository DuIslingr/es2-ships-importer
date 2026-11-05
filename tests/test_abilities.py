"""ES2's enemy abilities on the fighters' traffic (tools/fighters.py abilities_of): the blueprints' devices, each from a rank
on and for a share of the hull's NPCs (ES2's enemies are harder than GoF2's), mines from a later rank; none for the rest."""
from pathlib import Path
import sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import fighters


class AbilityTests(unittest.TestCase):
    def test_gated(self):
        for bp in fighters.ABILITIES:
            for d in fighters.abilities_of(bp):
                self.assertEqual(fighters.SHARE, d['share'], bp)
                self.assertEqual(fighters.MINES_MIN_RANK if d['type'] == 'bombSpreader' else fighters.MIN_RANK, d['minRank'], bp)

    def test_kits(self):
        self.assertEqual(['frontShield', 'bombSpreader'], [d['type'] for d in fighters.abilities_of('BP_Outlaw_Bomber_Zurilia')])
        self.assertEqual(120, fighters.abilities_of('BP_Okkar_Interceptor')[0]['notAhead'], 'tailed: the player behind it')
        self.assertEqual(25, fighters.abilities_of('BP_Outlaw_Madcap')[0]['hullBelow'], 'its last act')
        self.assertIsNone(fighters.abilities_of('BP_Outlaw_Raider'))

    def test_copies(self):
        a = fighters.abilities_of('BP_Cultist_Heavy')
        a[0]['range'] = None
        self.assertIsNotNone(fighters.ABILITIES['BP_Cultist_Heavy'][0]['range'], 'each hull its own copy')


if __name__ == '__main__':
    unittest.main()
