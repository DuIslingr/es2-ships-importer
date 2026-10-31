"""Exactness and avoided-I/O checks for performance improvements (stdlib only)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache as cache


class SnapshotReadTests(unittest.TestCase):
    def test_changed_recipe_does_not_hash_discarded_snapshot(self):
        with tempfile.TemporaryDirectory() as d, cache.Work(d) as work, contextlib.redirect_stdout(io.StringIO()):
            def produce(folder):
                (folder / 'payload').write_bytes(b'exact content')
                return {}
            work.run('content', {'fingerprint': 'before'}, produce)
            with patch.object(cache, 'inventory', wraps=cache.inventory) as inventory:
                work.run('content', {'fingerprint': 'after'}, produce)
                self.assertEqual(1, inventory.call_count, 'hash only the newly produced payload')
            with patch.object(cache, 'inventory', wraps=cache.inventory) as inventory:
                work.run('content', {'fingerprint': 'after'}, produce)
                self.assertEqual(1, inventory.call_count, 'a cache hit must still verify every output byte')


class MaterialTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('material_speed_test', ROOT / 'tools/es2mat.py')
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def material(self, name, parent, value=None):
        properties = {'Parent': {'ObjectPath': parent}} if parent else {}
        if value is not None:
            properties['ScalarParameterValues'] = [{'ParameterInfo': {'Name': 'Roughness'}, 'ParameterValue': value}]
        (self.root / (name + '.json')).write_text(json.dumps([{'Type': 'MaterialInstanceConstant', 'Properties': properties}]))

    def test_shared_parent_parsed_once_with_identical_resolution(self):
        self.material('Parent', None, .7)
        self.material('ChildA', 'Parent'); self.material('ChildB', 'Parent')
        self.module.configure(str(self.root))
        real = json.load
        with patch.object(self.module.json, 'load', wraps=real) as load:
            a = self.module.resolve('ChildA'); b = self.module.resolve('ChildB')
            self.assertEqual(3, load.call_count)
            self.assertEqual(.7, a['sca']['Roughness']); self.assertEqual(.7, b['sca']['Roughness'])
        self.assertEqual(['ChildA', 'Parent'], a['chain'])
        self.assertEqual(['ChildB', 'Parent'], b['chain'])

    def test_configure_clears_parsed_and_resolved_materials(self):
        self.material('Parent', None, .7); self.material('Child', 'Parent')
        self.module.configure(str(self.root))
        self.assertEqual(.7, self.module.resolve('Child')['sca']['Roughness'])
        self.material('Parent', None, .2)
        self.module.configure(str(self.root))
        self.assertEqual(.2, self.module.resolve('Child')['sca']['Roughness'])
        other = self.root / 'other'; other.mkdir()
        (other / 'Child.json').write_text('{"Scalars":{"Roughness":0.1}}')
        self.module.configure(str(other))
        self.assertEqual(.1, self.module.resolve('Child')['sca']['Roughness'])

    def test_parsed_material_cache_is_bounded(self):
        self.assertEqual(256, self.module._load_name.cache_info().maxsize)


if __name__ == '__main__': unittest.main()
