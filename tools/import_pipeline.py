"""Persistent stage orchestration for import.py; metadata stays outside the installed mod."""
import contextlib
import importlib
import importlib.metadata
import io
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import build_cache as cache


class Tee:
    def __init__(self, original, capture):
        self.original, self.capture = original, capture
    def write(self, text):
        self.original.write(text)
        return self.capture.write(text)
    def flush(self):
        self.original.flush()


def capture(fn):
    output = io.StringIO()
    with contextlib.redirect_stdout(Tee(sys.stdout, output)):
        value = fn()
    notes = [line.strip() for line in output.getvalue().splitlines()
             if any(word in line.lower() for word in ('failed', 'missing', 'skipped', 'no ', 'left out', 'not found', 'unknown'))]
    return value, notes


def runtime():
    packages = {}
    for name in ('numpy', 'Pillow', 'soundfile'):
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = None
    return {'python': platform.python_version(), 'platform': platform.platform(), 'packages': packages}


def validate_paths(work, out, content, item_icons, remake, root):
    writes = {'work': work, 'output': out, 'phone output': out + '_phone'}
    cache.disjoint(writes)
    for name, path in writes.items():
        for label, source in (('export', content), ('item icons', item_icons), ('remake', remake)):
            if source: cache.disjoint({name: path, label: source})
        if Path(path).resolve() == Path(root).resolve() or Path(path).resolve() in Path(root).resolve().parents:
            raise ValueError(f'{name} must not replace the importer source folder')


def main(cli, a, parts, content, out, blender):
    root = Path(cli.HERE)
    work = os.path.abspath(os.path.expanduser(a.work)) if a.work else out + '_work'
    item_icons = os.path.abspath(os.path.expanduser(a.item_icons)) if a.item_icons else os.path.join(content, 'UI/Images/Items')
    remake = os.path.abspath(os.path.expanduser(a.remake)) if a.remake else None
    validate_paths(work, out, content, item_icons, remake, root)
    env = runtime()
    wants_blender = a.mobile or not a.no_preview or ('ships' in parts and not a.no_icons)
    render_blender = blender or (cli.find_blender(a.blender, required=False) if wants_blender else None)
    blender_info = cache.executable(render_blender)
    if render_blender:
        r = cli.subprocess.run([render_blender, '--version'], capture_output=True, text=True, check=True)
        blender_info['version'] = next((line for line in r.stdout.splitlines() if line.startswith('Blender ')), r.stdout.strip())
    jobs = importlib.import_module('jobs')
    jobs.JOBS = a.jobs
    jobs.lower_priority()
    print(f'  {jobs.workers()} workers')
    audio = importlib.import_module('audio')
    audio.options(vgmstream=a.vgmstream, enabled='sounds' in parts)
    audio.configure(content, out)
    audio_tools = ({'vgmstream': [cache.executable(x) for x in (audio.vgmstream() or [])],
                    'ffmpeg': cache.executable('ffmpeg')} if 'sounds' in parts else None)
    icons = importlib.import_module('icons')
    icons.configure(item_icons, remake)
    atlas = cache.inventory(icons.REMAKE_ATLAS) if icons.REMAKE_ATLAS else {'kind': 'missing'}
    print('Hashing the export and external inputs (SHA-256) ...')
    inputs = {'export': cache.inventory(content), 'item_icons': cache.inventory(item_icons), 'atlas': atlas}
    if remake and Path(remake).is_dir():
        sky = cache.inventory(Path(remake) / 'Assets/Resources/GoF2Sky')
    else:
        sky = {'kind': 'missing'}
    build = importlib.import_module('build')
    options = {'parts': parts, 'icons': not a.no_icons, 'preview_renders': not a.no_preview,
               'sounds': 'sounds' in parts, 'mobile': a.mobile, 'ratio': a.ratio,
               'zip': a.zip, 'jobs': a.jobs, 'remake': remake, 'item_icons': item_icons}
    provenance = out + '.build-manifest.json'
    phone_provenance = out + '_phone.build-manifest.json'
    with cache.Work(work, fresh=a.fresh) as stages:
        # Validate ownership of the old output before replacing it. Never seed caches from it.
        cli.prepare_out(out)
        for previous in (provenance, phone_provenance, str(Path(work) / 'build-manifest.json')):
            if os.path.isfile(previous): os.remove(previous)

        def convert(folder):
            build.configure(content, str(folder))
            made, notes = capture(lambda: build.main(cli.VERSION, parts))
            missing = [p for p in parts if p not in made]
            return {'made': made, 'missing_parts': missing, 'diagnostics': notes,
                    'reusable': not missing and not any('failed' in n.lower() for n in notes)}

        # build.main shares kits, materials and world tables: cache it as one content stage.
        recipe = cache.stage(root, ['import_pipeline.py', 'build.py'], inputs,
                             {'runtime': env, 'parts': parts, 'audio_tools': audio_tools, 'version': cli.VERSION})
        files, converted = stages.run('content', recipe, convert)
        cache.copy_files(files, out)
        made = converted['made']
        for line in converted['diagnostics']:
            if stages.records['content']['reused']: print('  previous build: ' + line)

        if 'ships' in made and not a.no_icons:
            def render_icons(folder):
                note, notes = capture(lambda: cli.make_icons(out, render_blender))
                cache.copy_files(out, folder, [Path('ships.json')] + [p.relative_to(out) for p in (Path(out) / 'icons').rglob('*') if p.is_file()])
                return {'note': note, 'diagnostics': notes, 'reusable': 'failed' not in note.lower() and not any('failed' in n.lower() for n in notes)}
            recipe = cache.stage(root, ['import_pipeline.py', 'preview_blender.py', 'icons.py'], cache.inventory(out),
                                 {'runtime': env, 'blender': blender_info, 'atlas': atlas})
            files, result = stages.run('icons', recipe, render_icons)
            cache.copy_files(files, out)
            print('  icons: ' + result['note'])

        def preview(folder):
            note, notes = capture(lambda: cli.make_preview(out, None if a.no_preview else render_blender, remake))
            cache.copy_files(out, folder, [Path('preview.png')])
            if not (folder / 'preview.png').is_file(): raise RuntimeError('preview did not write preview.png')
            return {'note': note, 'diagnostics': notes, 'reusable': not any('failed' in n.lower() for n in notes)}
        recipe = cache.stage(root, ['import_pipeline.py', 'preview_card.py', 'preview_blender.py', 'preview_model_blender.py'],
                             cache.inventory(out), {'runtime': env, 'blender': None if a.no_preview else blender_info, 'sky': sky})
        files, result = stages.run('preview', recipe, preview)
        cache.copy_files(files, out)
        print('  preview.png: ' + result['note'])

        messages = [f'  the mod:           {out}', f'  holds:             {", ".join(made) or "nothing"}']
        if converted['missing_parts']: messages.append('  not built:         ' + ', '.join(converted['missing_parts']))
        desktop_inventory = cache.inventory(out) if a.zip or a.mobile else None
        if a.zip:
            recipe = cache.stage(root, ['import_pipeline.py'], desktop_inventory, {'format': 'zip', 'python': env['python']})
            files, _ = stages.run('desktop-zip', recipe, lambda f: {'archive': cli.zip_folder(out, str(f / 'mod.zip'))})
            shutil.copy2(files / 'mod.zip', out + '.zip')
            messages.append(f'  the mod as a zip:  {out}.zip')
        if a.mobile:
            def mobile(folder):
                _, notes = capture(lambda: cli.make_mobile(out, str(folder), a.ratio, render_blender))
                return {'diagnostics': notes, 'reusable': not any('failed' in n.lower() for n in notes)}
            recipe = cache.stage(root, ['import_pipeline.py', 'decimate_blender.py'], desktop_inventory,
                                 {'runtime': env, 'blender': blender_info, 'ratio': a.ratio})
            files, _ = stages.run('mobile', recipe, mobile)
            phone = out + '_phone'
            cli.prepare_out(phone)
            cache.copy_files(files, phone)
            recipe = cache.stage(root, ['import_pipeline.py'], cache.inventory(phone), {'format': 'zip', 'python': env['python']})
            files, _ = stages.run('phone-zip', recipe, lambda f: {'archive': cli.zip_folder(phone, str(f / 'mod.zip'))})
            shutil.copy2(files / 'mod.zip', phone + '.zip')
            messages.append(f'  the phone version: {phone}.zip')

        code = {'import.py': cache.file_hash(root / 'import.py')}
        code.update({'tools/' + p.name: cache.file_hash(p) for p in (root / 'tools').iterdir() if p.suffix in ('.py', '.json', '.txt')})
        manifest = {'schema': 1, 'built_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'importer': {'revision': cache.revision(root), 'files': code, 'sha256': cache.digest(code)},
                    'source': {'root': content, 'inputs': inputs}, 'runtime': dict(env, blender=blender_info, audio_tools=audio_tools),
                    'options': options, 'stages': stages.records, 'made': made, 'missing_parts': converted['missing_parts'],
                    'diagnostics': {name: record['result'].get('diagnostics', []) for name, record in stages.records.items()}}
        cache.write_json(provenance, manifest)
        cache.write_json(Path(work) / 'build-manifest.json', manifest)
        if a.mobile: cache.write_json(phone_provenance, manifest)
    print('\nDone:\n' + '\n'.join(messages))
    print('\nInstall: copy the es2_ships folder (or a zip) into the game\'s Mods folder and turn it on in the main menu\'s Mods screen.'
          '\nOn a phone: Mods > Import mod, and pick the _phone.zip.'
          '\nThe mod holds EVERSPACE 2\'s models and textures from your own copy of the game: keep it to yourself.')
