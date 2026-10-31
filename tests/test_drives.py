"""The drives part's numbers (stdlib + pillow): the recipe costs more than a Khador Drive in both of the remake's economies,
uses only ES2's real resources, and the part pulls in the sectors that hold them."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import drives
import sectors

REMAKE = Path(os.environ.get('GOF2_REMAKE', Path.home() / 'Github/Galaxy-on-Fire-2-Unity-Remake'))
DATA = REMAKE / 'Assets/Resources/GoF2Data'


def prices():
    """{'classic': (item -> max price, item -> recipe), 'default': ...}, the second the Default Economy's overlay."""
    base = {i['index']: i for i in json.load(open(DATA / 'items.json', encoding='utf-8'))}
    over = {i['index']: i for i in json.load(open(DATA / 'economy_default.json', encoding='utf-8'))['items']}
    classic = {k: v['maxPrice'] for k, v in base.items()}
    default = {k: over.get(k, {}).get('maxPrice', v) for k, v in classic.items()}
    return {'classic': (classic, {k: v.get('blueprint') for k, v in base.items()}),
            'default': (default, {k: over.get(k, {}).get('blueprint') or v.get('blueprint') for k, v in base.items()})}


def ore_price(key):
    rarity = next(r[3] for r in sectors.RESOURCES if r[0] == key)
    return int(round(sectors.RARITY_PRICE[rarity] * 1.1))


class Drives(unittest.TestCase):
    def test_the_recipe_names_real_resources(self):
        known = {r[0] for r in sectors.RESOURCES}
        for key, n in drives.ORES:
            self.assertIn(key, known)
            self.assertGreater(n, 0)
        rarities = {next(r[3] for r in sectors.RESOURCES if r[0] == k) for k, _ in drives.ORES}
        self.assertIn('superior', rarities)

    def test_the_blueprint_is_the_only_way_to_the_second_drive(self):
        bp = drives.blueprints()[0]
        self.assertEqual(bp['item'], f'es2_ships:{drives.SECOND}')
        self.assertIs(bp['autocomplete'], False)
        self.assertIn({'item': f'es2_ships:{drives.FIRST}', 'amount': 1}, bp['ingredients'])
        self.assertEqual(sum(1 for i in bp['ingredients'] if str(i['item']).startswith('es2_ships:es2_') and i['item'] != f'es2_ships:{drives.FIRST}'), len(drives.ORES))

    @unittest.skipUnless((DATA / 'items.json').exists(), 'no remake checkout (GOF2_REMAKE)')
    def test_it_costs_more_to_make_than_a_khador_drive_in_both_economies(self):
        ores = sum(ore_price(k) * n for k, n in drives.ORES)
        for name, (price, recipes) in prices().items():
            khador = sum(b['amount'] * price[b['item']] for b in recipes[drives.KHADOR])
            mine = ores + sum(price[i] * n for i, n in drives.GOODS) + 162800
            self.assertGreater(mine, khador, name)
            self.assertGreater(mine, price[drives.KHADOR], name + ': more than buying one, too')

    def test_the_part_pulls_in_the_sectors(self):
        import build
        parts, pulled = build.resolve_parts('drives')
        self.assertIn('sectors', parts)
        self.assertIn('sectors', pulled)
        self.assertIn('drives', build.resolve_parts('all')[0])
        self.assertIn('warp/', build.MULTIPLAYER_IGNORE)


class Warp(unittest.TestCase):
    def test_layers_become_one_channel_and_missing_ones_are_left_out(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            src, mod = os.path.join(d, 'src'), os.path.join(d, 'mod')
            folder = os.path.join(src, drives.TEXTURES)
            os.makedirs(folder)
            Image.new('RGBA', (2048, 2048), (200, 0, 0, 255)).save(os.path.join(folder, drives.LAYERS[0][1] + '.png'))
            drives.configure(src, mod)
            look = drives.warp()
            self.assertEqual(look['tunnel'], 'warp/tunnel.png')
            self.assertNotIn('detail', look)
            with Image.open(os.path.join(mod, 'warp/tunnel.png')) as img:
                self.assertEqual((img.mode, img.size), ('L', (drives.LAYER_SIZE, drives.LAYER_SIZE)))
                self.assertEqual(img.getpixel((5, 5)), 200)


if __name__ == '__main__':
    unittest.main()
