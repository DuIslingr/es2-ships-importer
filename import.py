#!/usr/bin/env python3
"""EVERSPACE 2 ships for the Galaxy on Fire 2 Unity Remake: builds the es2_ships mod from your own FModel export of
EVERSPACE 2. Nothing of EVERSPACE 2 comes with this importer; the mod it writes is for your own use (don't share it).

    python3 import.py <FModel export folder> [--out FOLDER] [--mobile] [--ratio 0.25] [--blender PATH] [--zip]
                      [--vgmstream PATH] [--no-sounds]          (on Windows: py import.py ...)

<FModel export folder>: FModel's Output/Exports folder, its ES2 folder or its ES2/Content folder (see README.md for what
to export). --out: where the mod goes (default: es2_ships next to this script; the game's Mods folder works too).
--mobile: also a lighter version for phones (Blender decimates the models, the textures are halved), zipped for the
game's Import mod button. --zip: also zip the desktop mod.
"""
import argparse, glob, importlib, json, os, platform, re, shutil, stat, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = '1.0'
MOD_ID = 'es2_ships'

# What the export must have (relative to ES2/Content), and what it may have.
REQUIRED = [
    ('Blueprints/DataTables/DT_ShipModules_Light.json', 'the ship module tables (Blueprints/DataTables, as JSON)'),
    ('Blueprints/DataTables/DT_ShipModules_Medium.json', 'the ship module tables'),
    ('Blueprints/DataTables/DT_ShipModules_Heavy.json', 'the ship module tables'),
    ('Blueprints/DataTables/DT_ShipColors.json', 'the colour tables (Blueprints/DataTables)'),
    ('Blueprints/DataTables/DT_ShipColorSets.json', 'the colour tables'),
    ('Blueprints/DataTables/DT_DebugShipsKS.json', 'the ships\' default builds (Blueprints/DataTables)'),
    ('Assets/Vehicles/ShipModules/Shared/Textures/T_ShipModules_Hull_001_C_AO.png', 'the shared ship textures (as PNG)'),
    ('Assets/Vehicles/ShipModules/Shared/Textures/T_ShipModules_TechDetails_001_N.png', 'the shared ship textures'),
]
MESH_FOLDERS = ['Assets/Vehicles/ShipModules/Light/Meshes', 'Assets/Vehicles/ShipModules/Medium/Meshes', 'Assets/Vehicles/ShipModules/Heavy/Meshes']
OPTIONAL = [
    ('Assets/Equipment/Weapons/Meshes/SM_PrimaryWeapon_005.glb', 'weapon models (Assets/Equipment/Weapons: models, JSON, PNG)'),
    ('Assets/Equipment/Weapons/Textures/T_Weapons_001_C_AO.png', 'weapon textures'),
    ('Assets/Turrets/Meshes/SK_Turret_PlayerShip_001.glb', 'the player turret (Assets/Turrets/Meshes/SK_Turret_PlayerShip_001)'),
    ('Assets/Shared/Textures/Effects/T_Noise_018_M.png', 'engine flame noise (Assets/Shared/Textures/Effects/T_Noise_018_M, as PNG)'),
    ('Assets/Vehicles/Shared/Textures/T_Vehicles_Floaters_Emissive_M.png', 'nozzle glow mask (Assets/Vehicles/Shared/Textures/T_Vehicles_Floaters_Emissive_M, as PNG)'),
    ('Assets/Vehicles/Shared/Textures/T_ShipModules_FX_001_M_A.png', 'hologram pattern (Assets/Vehicles/Shared/Textures/T_ShipModules_FX_001_M_A, as PNG)'),
    ('Assets/Shared/Textures/Effects/T_Noise_001_M.png', 'nozzle shimmer noise (Assets/Shared/Textures/Effects/T_Noise_001_M, as PNG)'),
    ('Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_C_R_M_H.png', 'battle damage embers and charring (Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_C_R_M_H, as PNG)'),
    ('Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_N.png', 'battle damage pitting (Assets/Vehicles/Shared/Textures/T_Vehicles_Damage_N, as PNG)'),
    ('Audio/BP/DT_WeaponSounds.json', 'the sounds (Audio: properties as JSON and the audio, with FModel\'s "Convert audio on bulk export" on)'),
    ('Assets/Vehicles/ShipModules/Okkar/Meshes/SK_ShipOkkar_C_001.glb', 'the Wraith (Assets/Vehicles/ShipModules/Okkar/Meshes: models and JSON)'),
    ('Assets/Vehicles/Shared/Textures/T_Vehicles_Okkar_Techdetail_001_C_R_E_AO.png', 'the Wraith\'s plating (Assets/Vehicles/Shared/Textures/T_Vehicles_Okkar_Techdetail_001_*, as PNG)'),
]


def fail(msg):
    print('\nERROR: ' + msg)
    sys.exit(1)


def find_content(path):
    """The ES2/Content folder at or under 'path'."""
    path = os.path.abspath(os.path.expanduser(path))
    for c in (path, os.path.join(path, 'Content'), os.path.join(path, 'ES2', 'Content'), os.path.join(path, 'Exports', 'ES2', 'Content'),
              os.path.join(path, 'Output', 'Exports', 'ES2', 'Content')):
        if os.path.isdir(os.path.join(c, 'Blueprints')) or os.path.isdir(os.path.join(c, 'Assets')):
            return c
    fail(f'no EVERSPACE 2 export found at {path}\n  Give FModel\'s Output/Exports folder, or the ES2/Content folder inside it.')


def check_export(content):
    missing = [(p, what) for p, what in REQUIRED if not os.path.exists(os.path.join(content, p))]
    for folder in MESH_FOLDERS:
        d = os.path.join(content, folder)
        glbs = glob.glob(os.path.join(d, 'SM_ShipModule_*.glb'))
        jsons = glob.glob(os.path.join(d, 'SM_ShipModule_*.json'))
        if not glbs: missing.append((folder + '/*.glb', 'the ship module models (as glTF / .glb)'))
        if not jsons: missing.append((folder + '/*.json', 'the ship module properties (as JSON: their weapon and engine sockets)'))
    if missing:
        lines = '\n'.join(f'  - {p}   ({what})' for p, what in missing)
        fail(f'the export is missing:\n{lines}\nSee README.md, "Exporting from FModel".')
    for p, what in OPTIONAL:
        if not os.path.exists(os.path.join(content, p)):
            print(f'  note: no {what} in the export: the mod is built without it')


def check_python():
    try:
        import numpy, PIL  # noqa: F401
    except ImportError as e:
        fail(f'{e.name} is missing: run   {os.path.basename(sys.executable)} -m pip install numpy pillow')


def prepare_out(out):
    """An empty folder for the mod: an earlier build of it is replaced, anything else is never touched."""
    if os.path.exists(out):
        info = os.path.join(out, 'mod.json')
        try:
            ours = json.load(open(info, encoding='utf-8-sig')).get('id') == MOD_ID
        except Exception:
            ours = False
        if not ours and os.listdir(out):
            fail(f'{out} exists and isn\'t an es2_ships mod: choose another --out')
        remove_tree(out)
    os.makedirs(out)


def remove_tree(path):
    """Deletes a folder. On Windows a read-only file (a copied or unzipped mod) or one Explorer / a virus scanner still holds
    makes shutil.rmtree fail: the read-only flag is cleared, and a held file tried again for a few seconds."""
    def clear_readonly(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    for attempt in range(5):
        try:
            if sys.version_info >= (3, 12): shutil.rmtree(path, onexc=clear_readonly)   # (onerror is deprecated there)
            else: shutil.rmtree(path, onerror=clear_readonly)
            return
        except OSError as e:
            if attempt == 4:
                fail(f'can\'t replace {path}: {e}\n  Close anything that has a file of it open (the game, an Explorer / Finder window) and run it again.')
            time.sleep(1)


def version_key(path):
    """'Blender 4.10' after 'Blender 4.2': the numbers in a path, compared as numbers."""
    return [int(n) for n in re.findall(r'\d+', path)]


def find_blender(given, required=True):
    """Blender's executable; None when it isn't found and not 'required' (the preview then is a plain card). The PATH first,
    then where the installers put it: Windows' Program Files (blender.org's installer, the newest version) and Steam, macOS'
    Applications folders."""
    if given:
        given = os.path.expanduser(given)
        if os.path.isdir(given) and given.endswith('.app'): given = os.path.join(given, 'Contents', 'MacOS', 'Blender')
        if not os.path.exists(given) and not shutil.which(given): fail(f'Blender not found at {given}')
        return given
    b = shutil.which('blender')
    if b: return b
    system = platform.system()
    if system == 'Windows':
        found = []
        for root in {os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramW6432', r'C:\Program Files')}:
            found += glob.glob(os.path.join(root, 'Blender Foundation', 'Blender*', 'blender.exe'))
        if found: return sorted(found, key=version_key)[-1]
        for steam in (os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('ProgramFiles', r'C:\Program Files')):
            exe = os.path.join(steam, 'Steam', 'steamapps', 'common', 'Blender', 'blender.exe')
            if os.path.exists(exe): return exe
    if system == 'Darwin':
        apps = glob.glob('/Applications/Blender*.app') + glob.glob(os.path.expanduser('~/Applications/Blender*.app'))
        apps += [os.path.expanduser('~/Library/Application Support/Steam/steamapps/common/Blender/Blender.app')]
        exes = [os.path.join(a, 'Contents', 'MacOS', 'Blender') for a in apps]
        exes = [e for e in exes if os.path.exists(e)]
        if exes: return sorted(exes, key=version_key)[-1]
    if not required: return None
    fail('--mobile needs Blender (4.2 or newer): install it from blender.org, or give its path with --blender')


def make_preview(mod, blender, remake=None):
    """The mod's preview.png (the Mods screen's card). With Blender: the Dreadnought in front of the remake's red nebula (its
    sky with --remake), warships, freighters and the Mobile Homebase behind it, four player ships in front and a strip of item
    icons (tools/preview_card.py; the kit ships rendered by tools/preview_blender.py, the rest by
    tools/preview_model_blender.py). Without Blender, or when the renders fail, a plain 640 x 360 card with the names."""
    if blender:
        renders = os.path.join(mod, '.preview_renders')
        shutil.rmtree(renders, ignore_errors=True); os.makedirs(renders)
        subprocess.run([blender, '-b', '--factory-startup', '-P', os.path.join(HERE, 'tools', 'preview_blender.py'), '--', mod, renders],
                       capture_output=True, text=True)
        import preview_card
        known = {e['id'] for f in ('ships.json', 'stations.json') if os.path.exists(os.path.join(mod, f))
                 for e in json.load(open(os.path.join(mod, f), encoding='utf-8-sig'))}
        shots = [f'{i}:{d}:{n}' for i, d, n in preview_card.MODEL_SHOTS if i in known]
        if shots:
            subprocess.run([blender, '-b', '--factory-startup', '-P', os.path.join(HERE, 'tools', 'preview_model_blender.py'), '--', mod, renders]
                           + shots, capture_output=True, text=True)
        sky = os.path.join(os.path.expanduser(remake), 'Assets', 'Resources', 'GoF2Sky') if remake else None
        drawn, items = preview_card.compose(mod, renders, sky, os.path.join(mod, 'preview.png'))
        shutil.rmtree(renders, ignore_errors=True)
        if 'es2_dreadnought' in drawn:
            return f'rendered: {len(drawn)} models, {items} item icons' + ('' if sky and os.path.isdir(sky) else ' (no --remake: a plain sky)')
        print('  (the preview renders failed: a plain card instead)')
    return plain_preview(mod)


def plain_preview(mod):
    """The plain card: the ships' names in three rows."""
    from PIL import Image, ImageDraw, ImageFont
    ships = json.load(open(os.path.join(mod, 'ships.json'), encoding='utf-8-sig'))
    card = Image.new('RGB', (640, 360), (14, 18, 28))
    d = ImageDraw.Draw(card)
    def font(size):
        for name in ('DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf', 'Helvetica.ttc'):
            try: return ImageFont.truetype(name, size)
            except OSError: pass
        return ImageFont.load_default()
    title, small = font(24), font(13)
    d.text((18, 12), f'EVERSPACE 2 ships  \u00b7  {len(ships)}', fill=(235, 240, 250), font=title)
    cols = 3 if len(ships) <= 9 else 4 if len(ships) <= 12 else 5   # (three rows: nine ships three by three, more narrower)
    cw = 640 // cols
    for i, s in enumerate(ships[:cols * 3]):
        cx, cy = cw // 2 + (i % cols) * cw, 80 + (i // cols) * 98
        d.rounded_rectangle((cx - 90, cy - 30, cx + 90, cy + 30), 8, outline=(70, 110, 150), width=2)
        name = s.get('name', s['id'])
        d.text((cx - d.textlength(name, font=small) / 2, cy + 38), name, fill=(200, 215, 230), font=small)
    card.save(os.path.join(mod, 'preview.png'))
    return 'a plain card (Blender not found)'


def make_icons(mod, blender):
    """Each ship's shop icon (icons/<id>.png, ships.json "icon"): its default build rendered like the game's own ship icons
    (tools/preview_blender.py icon), fitted to the drawn pixels with a 4 % margin, over the ship frame. Returns a note."""
    from PIL import Image
    if not blender: return 'none (Blender not found: the ships show the Phantom\'s icon)'
    renders = os.path.join(mod, '.icon_renders')
    shutil.rmtree(renders, ignore_errors=True); os.makedirs(renders)
    r = subprocess.run([blender, '-b', '--factory-startup', '--python-exit-code', '1', '-P', os.path.join(HERE, 'tools', 'preview_blender.py'),
                        '--', mod, renders, 'icon'], capture_output=True, text=True)
    import icons
    frame, kind = icons.frame('ship'), icons.frame_kind()
    ships = json.load(open(os.path.join(mod, 'ships.json'), encoding='utf-8-sig'))
    os.makedirs(os.path.join(mod, 'icons'), exist_ok=True)
    made = 0
    for s in ships:
        png = os.path.join(renders, s['id'] + '.png')
        if not os.path.exists(png): continue
        im = Image.open(png).convert('RGBA')
        box = im.getchannel('A').point(lambda v: 255 if v > 25 else 0).getbbox()
        if not box: continue
        im = im.crop(box)
        k = min(icons.W * 0.96 / im.width, icons.H * 0.96 / im.height)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
        icon = frame.copy(); icon.alpha_composite(im, (1 + (icons.W - im.width) // 2, 1 + (icons.H - im.height) // 2))
        icon.save(os.path.join(mod, 'icons', s['id'] + '.png'), optimize=True)
        s['icon'] = f"icons/{s['id']}.png"; made += 1
    json.dump(ships, open(os.path.join(mod, 'ships.json'), 'w', encoding='utf-8'), indent=1)
    shutil.rmtree(renders, ignore_errors=True)
    if r.returncode != 0 and not made: return 'none (the renders failed: the ships show the Phantom\'s icon)'
    return f'{made} of {len(ships)}, on {kind}'


SKIP_IN_ZIP = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '__MACOSX', '__pycache__'}


def zip_folder(folder, zip_path):
    if os.path.exists(zip_path): os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in SKIP_IN_ZIP and not d.startswith('.')]
            for f in files:
                if f in SKIP_IN_ZIP or f.startswith('._'): continue   # (macOS / Windows litter)
                full = os.path.join(base, f)
                zf.write(full, os.path.relpath(full, folder).replace(os.sep, '/'))
    return zip_path


def make_mobile(mod, out, ratio, blender):
    """The phone version: the same mod id (saves move between devices), every part decimated in Blender, the textures
    halved; the weapons and the turret as they are (small, and their marker nodes must stay exactly)."""
    from PIL import Image
    if os.path.exists(out): remove_tree(out)
    os.makedirs(os.path.join(out, 'maps'))
    for f in ('shipkits.json', 'ships.json', 'exhausts.json', 'preview.png'):
        if os.path.exists(os.path.join(mod, f)): shutil.copy(os.path.join(mod, f), out)
    for d in ('equipment', 'icons', 'exhausts', 'audio'):
        if os.path.isdir(os.path.join(mod, d)): shutil.copytree(os.path.join(mod, d), os.path.join(out, d))
    info = json.load(open(os.path.join(mod, 'mod.json'), encoding='utf-8-sig'))
    info['name'] += ' (phone)'
    json.dump(info, open(os.path.join(out, 'mod.json'), 'w', encoding='utf-8'), indent=1)
    for f in sorted(os.path.relpath(os.path.join(d, n), os.path.join(mod, 'maps'))
                   for d, _, ns in os.walk(os.path.join(mod, 'maps')) for n in ns):   # (maps/cyber/ too)
        os.makedirs(os.path.dirname(os.path.join(out, 'maps', f)), exist_ok=True)
        im = Image.open(os.path.join(mod, 'maps', f))
        if im.size[0] > 8: im = im.resize((max(4, im.size[0] // 2), max(4, im.size[1] // 2)), Image.LANCZOS)
        im.save(os.path.join(out, 'maps', f), optimize=True)
    print(f'  decimating the parts in Blender (to {ratio:.0%} of their triangles; this takes a few minutes)...')
    # --python-exit-code: a Python error in the script fails Blender (it exits 0 otherwise).
    subprocess.run([blender, '-b', '--factory-startup', '--python-exit-code', '1', '-P', os.path.join(HERE, 'tools', 'decimate_blender.py'), '--',
                    os.path.join(mod, 'parts'), os.path.join(out, 'parts'), str(ratio), '400'], check=True)
    if len(os.listdir(os.path.join(out, 'parts'))) != len(os.listdir(os.path.join(mod, 'parts'))):
        fail('Blender didn\'t write every part: no phone version')
    return out


def main():
    # A Windows console that can't show a character (a name in another script) mustn't stop the build.
    for stream in (sys.stdout, sys.stderr):
        try: stream.reconfigure(errors='replace')
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(description='Builds the es2_ships mod for the Galaxy on Fire 2 Unity Remake from your own EVERSPACE 2 export.')
    ap.add_argument('export', help="FModel's Output/Exports folder (or its ES2/Content folder)")
    ap.add_argument('--out', default=os.path.join(HERE, MOD_ID), help='where the mod goes (default: es2_ships next to this script)')
    ap.add_argument('--mobile', action='store_true', help='also make a lighter version for phones (needs Blender)')
    ap.add_argument('--ratio', type=float, default=0.25, help='the phone version keeps this share of the triangles (default 0.25)')
    ap.add_argument('--blender', help='the Blender executable (or Blender.app on a Mac), if it isn\'t found by itself')
    ap.add_argument('--vgmstream', help='the vgmstream-cli executable for the sounds, if it isn\'t found by itself (FModel\'s '
                                        'Output/.data folder, or vgmstream-cli on the PATH)')
    ap.add_argument('--no-sounds', action='store_true', help='skip EVERSPACE 2\'s sounds (the ships keep the game\'s)')
    ap.add_argument('--zip', action='store_true', help='also zip the desktop mod')
    ap.add_argument('--jobs', type=int, help='worker threads for the maps and ships (default: half the CPUs, fewer when memory is short)')
    ap.add_argument('--no-preview', action='store_true', help='skip the preview image\'s renders (a plain card instead)')
    ap.add_argument('--no-icons', action='store_true', help='skip the ships\' shop icons (they show the Phantom\'s instead)')
    ap.add_argument('--remake', help='a checkout of the remake\'s source (or its gof2_interface2_ipad_large.png): the icons '
                                     'then use the game\'s own plates instead of drawn ones')
    ap.add_argument('--item-icons', help='a folder of EVERSPACE 2\'s item icons as PNG (default: the export\'s UI/Images/Items): '
                                         'the weapons\', devices\' and consumables\' shop icons are made from them')
    a = ap.parse_args()
    if not 0.05 <= a.ratio <= 1: fail('--ratio must be between 0.05 and 1')

    check_python()
    content = find_content(a.export)
    print(f'EVERSPACE 2 export: {content}')
    check_export(content)
    blender = find_blender(a.blender) if a.mobile else None
    out = os.path.abspath(os.path.expanduser(a.out))
    prepare_out(out)

    sys.path.insert(0, os.path.join(HERE, 'tools'))
    jobs = importlib.import_module('jobs')
    jobs.JOBS = a.jobs
    jobs.lower_priority()   # (the desktop stays usable while every worker runs)
    print(f'  {jobs.workers()} workers')
    build = importlib.import_module('build')
    audio = importlib.import_module('audio')
    audio.options(vgmstream=a.vgmstream, enabled=not a.no_sounds)
    build.configure(content, out)
    icons = importlib.import_module('icons')
    icons.configure(os.path.expanduser(a.item_icons) if a.item_icons else os.path.join(content, 'UI', 'Images', 'Items'), a.remake)
    print(f'Building the mod into {out} ...')
    build.main(VERSION)
    if not a.no_icons:
        print('Making the ships\' shop icons ...')
        print(f'  icons: {make_icons(out, find_blender(a.blender, required=False))}')
    print('Making the preview image ...')
    print(f'  preview.png: {make_preview(out, None if a.no_preview else find_blender(a.blender, required=False), a.remake)}')

    done = [f'  the mod:           {out}']
    if a.zip: done.append(f'  the mod as a zip:  {zip_folder(out, out + ".zip")}')
    if a.mobile:
        print('Making the phone version ...')
        phone = make_mobile(out, out + '_phone', a.ratio, blender)
        done.append(f'  the phone version: {zip_folder(phone, phone + ".zip")}')
    print('\nDone:\n' + '\n'.join(done))
    print('\nInstall: copy the es2_ships folder (or a zip) into the game\'s Mods folder and turn it on in the main menu\'s Mods screen.'
          '\nOn a phone: Mods > Import mod, and pick the _phone.zip.'
          '\nThe mod holds EVERSPACE 2\'s models and textures from your own copy of the game: keep it to yourself.')


if __name__ == '__main__':
    main()
