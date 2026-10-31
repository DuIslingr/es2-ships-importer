"""Cache orchestration tests with tiny deterministic converters; no ES2 files or Blender needed."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache as cache
import import_pipeline as pipeline


class SnapshotTests(unittest.TestCase):
    def test_same_size_edits_additions_and_removals_change_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'input'
            p.write_bytes(b'AAAA'); first = cache.inventory(d)
            p.write_bytes(b'BBBB'); second = cache.inventory(d)
            self.assertNotEqual(first, second)
            (Path(d) / 'empty').mkdir()
            self.assertNotEqual(second, cache.inventory(d))
            p.unlink()
            self.assertNotEqual(first, cache.inventory(d))

    def test_failed_snapshot_is_not_reused_and_lock_is_released(self):
        with tempfile.TemporaryDirectory() as d:
            def failing(folder):
                (folder / 'partial').write_text('partial')
                raise RuntimeError('conversion failed')
            with self.assertRaises(RuntimeError), cache.Work(Path(d) / 'work') as work:
                work.run('content', {'fingerprint': 'a'}, failing)
            with cache.Work(Path(d) / 'work'): pass
            self.assertFalse((Path(d) / 'work/stages/content').exists())

    def test_rejects_unowned_work_directory(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'keep').write_text('user data')
            with self.assertRaises(ValueError), cache.Work(d, fresh=True): pass
            self.assertEqual('user data', (Path(d) / 'keep').read_text())

    def test_rejects_concurrent_importer(self):
        with tempfile.TemporaryDirectory() as d, cache.Work(d):
            with self.assertRaises(ValueError), cache.Work(d): pass

    def test_recipe_follows_content_helpers_without_affecting_preview(self):
        content = cache.recipe(ROOT, ['build.py', 'import_pipeline.py'])
        self.assertIn('tools/es2mat.py', content)
        self.assertIn('tools/trails.py', content)
        preview = cache.recipe(ROOT, ['preview_card.py', 'import_pipeline.py'])
        self.assertNotIn('tools/build.py', preview)
        self.assertNotIn('tools/decimate_blender.py', preview)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'importer'
        self.repo.mkdir()
        shutil.copy2(ROOT / 'import.py', self.repo / 'import.py')
        shutil.copytree(ROOT / 'tools', self.repo / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
        spec = importlib.util.spec_from_file_location('es2_cli_test', self.repo / 'import.py')
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)
        self.out = self.root / 'es2_ships'
        self.export = self.root / 'export'
        self.export.mkdir()
        (self.export / 'source.glb').write_bytes(b'AAAA')
        self.remake = self.root / 'remake'
        atlas = self.remake / 'atlas.png'
        atlas.parent.mkdir()
        atlas.write_bytes(b'atlas')
        self.sky = self.remake / 'Assets/Resources/GoF2Sky/nebula.png'
        self.sky.parent.mkdir(parents=True)
        self.sky.write_bytes(b'sky')
        self.a = types.SimpleNamespace(work=None, fresh=False, item_icons=None, remake=str(self.remake), jobs=1,
                                      vgmstream=None, blender=None, mobile=False, no_preview=False, no_icons=False, ratio=.25, zip=False)
        self.calls = []
        self.available = True
        self.partial = False
        self.fail_content = False
        self.fail_icons = False
        self.fail_preview = False
        self.fail_mobile = False
        self.version = 'Blender 4.5.3'
        self.build = types.SimpleNamespace(configure=self.configure, main=self.convert)
        self.jobs = types.SimpleNamespace(JOBS=None, lower_priority=lambda: None, workers=lambda: 1)
        self.audio = types.SimpleNamespace(options=lambda **_: None, configure=lambda *_: None, vgmstream=lambda: None)
        self.icons = types.SimpleNamespace(configure=lambda *_: None, REMAKE_ATLAS=str(atlas))

    def configure(self, content, folder): self.folder = Path(folder)

    def convert(self, version, parts):
        self.calls.append('content')
        (self.folder / 'mod.json').write_text('{"id":"es2_ships", "name":"ES2"}')
        (self.folder / 'ships.json').write_text('[{"id":"hull","kit":"kit"}]')
        (self.folder / 'model.glb').write_bytes((self.export / 'source.glb').read_bytes())
        if self.fail_content: raise RuntimeError('content failed')
        if self.partial: print('  skipped optional asset: missing export')
        return [] if self.partial else parts

    def render_icons(self, mod, blender):
        self.calls.append('icons')
        if self.fail_icons: return 'none (renders failed)'
        (Path(mod) / 'icons').mkdir(exist_ok=True)
        (Path(mod) / 'icons/hull.png').write_bytes(b'icon')
        (Path(mod) / 'ships.json').write_text('[{"id":"hull","kit":"kit","icon":"icons/hull.png"}]')
        return '1 of 1'

    def preview(self, mod, blender, remake):
        self.calls.append('preview')
        (Path(mod) / 'preview.png').write_bytes(b'preview')
        if self.fail_preview: print('the preview renders failed: a plain card instead')
        return 'a plain card' if self.fail_preview else 'rendered'

    def mobile(self, mod, out, ratio, blender):
        self.calls.append('mobile')
        shutil.rmtree(out)
        shutil.copytree(mod, out)
        if self.fail_mobile: raise RuntimeError('mobile failed')
        (Path(out) / 'model.glb').write_bytes(str(ratio).encode())
        return out

    def run_build(self, parts=None):
        self.calls = []
        fake_modules = {'build': self.build, 'jobs': self.jobs, 'audio': self.audio, 'icons': self.icons}
        real_import = pipeline.importlib.import_module
        real_run = self.cli.subprocess.run
        def module(name): return fake_modules[name] if name in fake_modules else real_import(name)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(pipeline.importlib, 'import_module', module))
            stack.enter_context(patch.object(self.cli, 'make_icons', self.render_icons))
            stack.enter_context(patch.object(self.cli, 'make_preview', self.preview))
            stack.enter_context(patch.object(self.cli, 'make_mobile', self.mobile))
            stack.enter_context(patch.object(self.cli, 'find_blender', lambda *_, **__: 'blender' if self.available else None))
            stack.enter_context(patch.object(self.cli.subprocess, 'run', lambda cmd, **kw: types.SimpleNamespace(stdout=self.version) if cmd[0] == 'blender' else real_run(cmd, **kw)))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            pipeline.main(self.cli, self.a, parts or ['ships'], str(self.export), str(self.out), None)
        return json.loads(Path(str(self.out) + '.build-manifest.json').read_text())

    def edit(self, relative):
        with (self.repo / relative).open('a') as f: f.write('\n# modified converter\n')

    def payload(self):
        return {p.relative_to(self.out).as_posix(): p.read_bytes() for p in self.out.rglob('*') if p.is_file()}

    def test_clean_and_resumed_payloads_match(self):
        first = self.run_build(); payload = self.payload()
        second = self.run_build()
        self.assertEqual([], self.calls)
        self.assertTrue(all(v['reused'] for v in second['stages'].values()))
        self.assertEqual(payload, self.payload())
        self.a.fresh = True
        third = self.run_build()
        self.assertEqual(['content', 'icons', 'preview'], self.calls)
        self.assertEqual(payload, self.payload())
        self.assertEqual(first['made'], third['made'])

    def test_same_size_source_edit_rebuilds_content_and_downstream(self):
        first = self.run_build()
        (self.export / 'source.glb').write_bytes(b'BBBB')
        second = self.run_build()
        self.assertEqual(['content', 'icons', 'preview'], self.calls)
        self.assertNotEqual(first['source'], second['source'])

    def test_converter_helper_change_rebuilds_content(self):
        self.run_build(); self.edit('tools/es2mat.py'); self.run_build()
        self.assertIn('content', self.calls)

    def test_preview_change_preserves_content_and_icons(self):
        self.run_build(); self.edit('tools/preview_card.py'); self.run_build()
        self.assertEqual(['preview'], self.calls)

    def test_icon_helper_change_preserves_content(self):
        # preview_blender is a render helper, rather than the shared item-icon converter.
        self.run_build(); self.edit('tools/preview_blender.py'); self.run_build()
        self.assertNotIn('content', self.calls)
        self.assertIn('icons', self.calls)
        self.assertIn('preview', self.calls)

    def test_mobile_ratio_change_preserves_desktop(self):
        self.a.mobile = True; self.run_build()
        self.a.ratio = .5; self.run_build()
        self.assertEqual(['mobile'], self.calls)

    def test_mobile_helper_change_preserves_desktop(self):
        self.a.mobile = True; self.run_build()
        self.edit('tools/decimate_blender.py'); self.run_build()
        self.assertEqual(['mobile'], self.calls)

    def test_blender_patch_change_preserves_content(self):
        self.a.mobile = True; self.run_build()
        self.version = 'Blender 4.5.4'; self.run_build()
        self.assertNotIn('content', self.calls)
        self.assertIn('icons', self.calls)
        self.assertIn('preview', self.calls)
        self.assertIn('mobile', self.calls)

    def test_parts_change_drops_previous_optional_output(self):
        self.run_build(); self.run_build(['devices'])
        self.assertEqual(['content', 'preview'], self.calls)
        self.assertFalse((self.out / 'icons/hull.png').exists())
        self.assertNotIn('icon', json.loads((self.out / 'ships.json').read_text())[0])

    def test_preview_option_does_not_invalidate_content_or_icons(self):
        self.run_build(); self.a.no_preview = True; self.run_build()
        self.assertEqual(['preview'], self.calls)

    def test_disabling_icons_restores_unmodified_ship_table(self):
        self.run_build(); self.a.no_icons = True; self.run_build()
        self.assertFalse((self.out / 'icons/hull.png').exists())
        self.assertNotIn('icon', json.loads((self.out / 'ships.json').read_text())[0])

    def test_failed_content_does_not_leave_reusable_snapshot_or_provenance(self):
        self.run_build(); self.edit('tools/build.py'); self.fail_content = True
        with self.assertRaises(RuntimeError): self.run_build()
        self.assertFalse(Path(str(self.out) + '.build-manifest.json').exists())
        self.assertFalse(Path(str(self.out) + '_work/stages/content/record.json').exists())
        self.fail_content = False; self.run_build()
        self.assertIn('content', self.calls)

    def test_partial_content_retries_and_records_missing_parts(self):
        self.partial = True
        first = self.run_build()
        self.assertEqual(['ships'], first['missing_parts'])
        self.assertTrue(first['diagnostics']['content'])
        self.partial = False; self.run_build()
        self.assertIn('content', self.calls)
        self.assertIn('icons', self.calls)

    def test_failed_icon_render_is_retried(self):
        self.fail_icons = True; self.run_build()
        self.fail_icons = False; self.run_build()
        self.assertNotIn('content', self.calls)
        self.assertIn('icons', self.calls)

    def test_failed_preview_fallback_is_retried(self):
        self.fail_preview = True; self.run_build()
        self.fail_preview = False; self.run_build()
        self.assertEqual(['preview'], self.calls)

    def test_failed_mobile_is_retried(self):
        self.a.mobile = True; self.fail_mobile = True
        with self.assertRaises(RuntimeError): self.run_build()
        self.fail_mobile = False; self.run_build()
        self.assertEqual(['mobile'], self.calls)

    def test_corrupt_snapshot_is_rebuilt(self):
        self.run_build()
        p = Path(str(self.out) + '_work/stages/content/files/model.glb')
        p.write_bytes(b'XXXX')
        self.run_build()
        self.assertIn('content', self.calls)
        self.assertEqual(b'AAAA', (self.out / 'model.glb').read_bytes())

    def test_output_edits_cannot_poison_snapshot(self):
        self.run_build()
        (self.out / 'model.glb').write_bytes(b'XXXX')
        self.run_build()
        self.assertEqual([], self.calls)
        self.assertEqual(b'AAAA', (self.out / 'model.glb').read_bytes())

    def test_sky_edit_only_rebuilds_preview(self):
        self.run_build(); self.sky.write_bytes(b'new'); self.run_build()
        self.assertEqual(['preview'], self.calls)

    def test_external_atlas_edit_rebuilds_content_and_icons(self):
        self.run_build()
        Path(self.icons.REMAKE_ATLAS).write_bytes(b'new atlas')
        self.run_build()
        self.assertIn('content', self.calls)
        self.assertIn('icons', self.calls)

    def test_new_export_file_invalidates_content(self):
        self.run_build()
        (self.export / 'new.json').write_text('{}')
        self.run_build()
        self.assertIn('content', self.calls)

    def test_corrupt_record_rebuilds_instead_of_trusting_snapshot(self):
        self.run_build()
        record = Path(str(self.out) + '_work/stages/content/record.json')
        data = json.loads(record.read_text())
        del data['result']
        record.write_text(json.dumps(data))
        self.run_build()
        self.assertIn('content', self.calls)

    def test_zip_is_repeatable_and_contains_no_provenance(self):
        self.a.zip = True; self.a.mobile = True; self.run_build()
        archive = Path(str(self.out) + '.zip').read_bytes()
        self.a.fresh = True; self.run_build()
        self.assertEqual(archive, Path(str(self.out) + '.zip').read_bytes())
        with zipfile.ZipFile(str(self.out) + '.zip') as z:
            self.assertNotIn('build-manifest.json', z.namelist())
        self.assertFalse((self.out / 'build-manifest.json').exists())
        self.assertTrue(Path(str(self.out) + '_phone.build-manifest.json').exists())

    def test_output_work_input_overlap_rejected(self):
        self.a.work = str(self.export / 'work')
        with self.assertRaises(ValueError): self.run_build()
        self.assertFalse(self.out.exists())

    def test_existing_unrelated_output_is_preserved(self):
        self.out.mkdir(); (self.out / 'user.txt').write_text('keep')
        with self.assertRaises(SystemExit): self.run_build()
        self.assertEqual('keep', (self.out / 'user.txt').read_text())


if __name__ == '__main__': unittest.main()
