"""The drones' roles (tools/fighters.role_of): the remake's traffic "role" names from ES2's blueprint names."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import fighters

ROLES = {'sniper', 'detonator', 'webber', 'shieldCharger', 'armorLink', 'antiMissile', 'jumpSuppressor', 'lootDrone'}


class RoleTests(unittest.TestCase):
    def test_roles(self):
        self.assertEqual('lootDrone', fighters.role_of('BP_LootDrone'))
        self.assertIsNone(fighters.role_of('BP_Outlaw_LootDrone'), 'the Outlaw Cargo Drone is a plain drone')
        self.assertEqual('sniper', fighters.role_of('BP_Outlaw_SniperDrone'))
        self.assertEqual('shieldCharger', fighters.role_of('BP_Okkar_ShieldChargeDrone'))
        self.assertIsNone(fighters.role_of('BP_Retaliators_FrostShieldDrone'))
        self.assertIsNone(fighters.role_of('BP_Outlaw_Raider'))

    def test_every_role_is_the_remakes(self):
        for _, bp, *_ in fighters.FIGHTERS:
            r = fighters.role_of(bp)
            if r: self.assertIn(r, ROLES, bp)
        self.assertEqual(1, sum(1 for f in fighters.FIGHTERS if fighters.role_of(f[1]) == 'lootDrone'), 'one loot drone')


if __name__ == '__main__':
    unittest.main()
