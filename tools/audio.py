# The es2_ships mod's sounds: EVERSPACE 2's engine, boost and weapon sounds from the player's own FModel export (Audio/: the
# sound cues as JSON and their waves). Best exported already playable: FModel's Settings > "Convert audio on bulk export" writes
# the waves as .ogg / .wav, which go into the mod as they are (a .wav is made Ogg Vorbis when ffmpeg or the soundfile package
# is there). Waves exported raw (.binka, Unreal's Bink Audio) are decoded by vgmstream: a native vgmstream-cli (the PATH,
# Homebrew's folders, ~/.local/bin, or one put next to import.py; --vgmstream), else FModel's own Windows copy in its
# Output/.data folder (through Wine off Windows, the last resort). The mod's audio/ folder; ships.json gets each ship's "sounds", the kits' hardpoint
# rules their weapon's "sound" (the game's ModShipSounds). Which sounds, as EVERSPACE 2 picks them:
#   engine       DT_PlayerShip_EngineSounds by ship type (else BP_ShipBase's S_SC_Engine_001)
#   boost        BP_ShipBase: S_SC_Booster_Init (start), S_SC_Boost_004 (loop: pitch 1 -> 1.5, volume 0.5 -> 1 as it builds),
#                S_SC_Booster_Stop (end)
#   charger      DT_PlayerShip_BoostChargerSounds by type: the boost refilling (pitch 0.5 -> 2, volume 0.2 -> 1.5)
#   weapons      DT_WeaponSounds' cue (else the Player/0 cue) of the weapon each hardpoint model is: its random shots, or a
#                beam's ignition and loop; the launchers' rocket / missile / mine cues
# Volumes: the cue's volume x a gain that puts EVERSPACE 2's mix at the game's level (measured on the game's own engine,
# booster and shot sounds against EVERSPACE 2's; GAIN_*). Nothing of EVERSPACE 2 comes with this importer; the sounds are
# from the player's own copy and stay in their mod.
import glob, json, os, platform, re, shutil, subprocess, sys, tempfile, wave
import numpy as np

SRC = MOD = None
AUDIO = None   # SRC/Audio

# x each cue's volume: EVERSPACE 2's waves at the game's level. Measured (loudness(): a loop's RMS, a shot's loudest 60 ms)
# against the game's own at the volumes it plays them: its engine (Spaceship_Engine_v1 0.388 x 0.27) against S_Engine_001 /
# 005 / 011 (0.156 / 0.143 x 0.8 / 0.528 x 0.3: all within 10 % at 0.67), its shots (Laser_Nirai_Impulse 0.371 x 0.7) against
# the median of the weapon cues (~0.6 x their volume), its booster (Booster_Linear 0.407 x 0.81) against the boost loop at
# full strength (0.343 x 0.6).
GAIN_ENGINE, GAIN_BOOST, GAIN_SHOT = 0.67, 1.6, 0.45

# EVERSPACE 2's ship type names (the sound tables' rows) by the kit type ids of build.py.
ES2_TYPE = {'vanguard': 'Vanguard', 'scout': 'Scout', 'stinger': 'Stinger', 'interceptor': 'Interceptor', 'sentinel': 'Sentinel',
            'striker': 'Striker', 'bomber': 'Bomber', 'vindicator': 'Vindicator', 'gunship': 'Gunship'}

# The weapon cue of each ES2 weapon model (build.py's W(n)): the model's weapon type -> its player cue.
WEAPON_CUES = {
    1: 'S_SC_CoilGun_MK4',                     # the turret's coil gun
    3: 'S_SC_BeamLaser_MK_Modular_Loop',       # beam laser (ignition + loop)
    4: 'S_SC_Blaster_MKModular',               # blaster
    5: 'S_SC_PulseLaser_MK1',                  # pulse laser
    6: 'S_SC_GaussCannon_0_MK1',               # gauss cannon
    7: 'S_SC_CoilGun_MK4',                     # coil gun
    8: 'S_SC_ThermoGun_0',                     # thermo gun
    9: 'S_SC_Railgun_MK_Modular',              # railgun
    10: 'S_SC_Flak_MK2',                       # flak
    11: 'S_SC_ScatterGun_MK1_Modular',         # scatter gun
    12: 'S_SC_Blaster_MK1',                    # the plasma gun (EMP blasters)
}
# The launchers (the secondary rules of the pod) by the game's item categories: rockets and cluster missiles (4, 40), mines
# (11), EMP bombs (6); every other secondary the homing missile's launch.
LAUNCHER_CUES = {4: 'S_SC_Rocket_Launcher', 40: 'S_SC_Rocket_Launcher', 11: 'S_SC_Mine_Thrower', 6: 'S_SC_EMPMissle_Launch'}
LAUNCHER_DEFAULT = 'S_SC_HomingMissle_Launch'


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the importer's folder
VGM_OVERRIDE, ENABLED = None, True
PLAYABLE = ('.ogg', '.wav')


def options(vgmstream=None, enabled=True):
    """import.py's --vgmstream and --no-sounds."""
    global VGM_OVERRIDE, ENABLED, _vgm
    VGM_OVERRIDE, ENABLED, _vgm = vgmstream, enabled, False


def configure(src, out):
    global SRC, MOD, AUDIO
    SRC, MOD = src, out
    AUDIO = os.path.join(SRC, 'Audio')


def available():
    """There is something to build from: the Audio folder, and its waves playable already or a vgmstream to decode them."""
    return unavailable_reason() is None


def unavailable_reason():
    if not ENABLED: return '--no-sounds'
    if AUDIO is None or not os.path.isdir(os.path.join(AUDIO, 'SFX', 'Ship')) or not os.path.isdir(os.path.join(AUDIO, 'BP')):
        return 'no Audio folder in the export (ES2/Content/Audio: its properties and audio)'
    waves = _index()[1]
    if any(set(v) & set(PLAYABLE) for v in waves.values()) or vgmstream() is not None: return None
    return ('the export\'s sounds are raw .binka: export them again with FModel\'s Settings > "Convert audio on bulk export" on, '
            'or install vgmstream (vgmstream-cli on the PATH, or --vgmstream)')


def _native_vgmstream():
    """A vgmstream-cli built for this system: --vgmstream, the PATH, Homebrew / user folders, or next to import.py."""
    exe = '.exe' if platform.system() == 'Windows' else ''
    if VGM_OVERRIDE:
        p = os.path.expanduser(VGM_OVERRIDE)
        if os.path.isdir(p): p = os.path.join(p, 'vgmstream-cli' + exe)
        return p if os.path.exists(p) or shutil.which(p) else None
    for name in ('vgmstream-cli', 'vgmstream_cli'):
        found = shutil.which(name)
        if found: return found
    for d in ('/opt/homebrew/bin', '/usr/local/bin', os.path.expanduser('~/.local/bin'), HERE, os.path.join(HERE, 'vgmstream')):
        p = os.path.join(d, 'vgmstream-cli' + exe)
        if os.path.isfile(p) and (exe or os.access(p, os.X_OK)): return p
    return None


_vgm = False
def vgmstream():
    """The command that runs vgmstream-cli, None when there is none: a native one first; else FModel's Windows copy in its
    Output/.data folder (next to Output/Exports), natively on Windows, through Wine elsewhere as the last resort."""
    global _vgm
    if _vgm is not False: return _vgm
    _vgm = None
    native = _native_vgmstream()
    if native:
        _vgm = [native]
        if native.lower().endswith('.exe') and platform.system() != 'Windows':
            wine = shutil.which('wine') or shutil.which('wine64')
            _vgm = [wine, native] if wine else None
        return _vgm
    if VGM_OVERRIDE: return None
    d = os.path.abspath(SRC)
    for _ in range(5):
        fmodel = os.path.join(d, '.data', 'vgmstream-cli.exe')
        if os.path.exists(fmodel):
            if platform.system() == 'Windows': _vgm = [fmodel]
            else:
                wine = shutil.which('wine') or shutil.which('wine64')
                if wine: _vgm = [wine, fmodel]
            break
        d = os.path.dirname(d)
    return _vgm


_json = _wave = None
def _index():
    """The export's cue JSONs by name, and its waves by name -> {extension: path} (.binka raw, .ogg / .wav converted)."""
    global _json, _wave
    if _json is None:
        _json, _wave = {}, {}
        for p in glob.glob(os.path.join(AUDIO, '**', '*.json'), recursive=True): _json.setdefault(os.path.basename(p)[:-5], p)
        for ext in ('.binka',) + PLAYABLE:
            for p in glob.glob(os.path.join(AUDIO, '**', '*' + ext), recursive=True):
                _wave.setdefault(os.path.basename(p)[:-len(ext)], {}).setdefault(ext, p)
    return _json, _wave


def cue(name):
    """A sound cue: {'volume', 'pitch', 'waves': [(wave, looping)], 'pitchRange': (min, max) of its modulator or None}."""
    p = _index()[0].get(name)
    if not p: return None
    out = {'volume': 1.0, 'pitch': 1.0, 'waves': [], 'pitchRange': None}
    for o in json.load(open(p, encoding='utf-8-sig')):
        t, pr = o.get('Type'), o.get('Properties', {})
        if t == 'SoundCue':
            out['volume'] = pr.get('VolumeMultiplier', 1.0); out['pitch'] = pr.get('PitchMultiplier', 1.0)
        elif t == 'SoundNodeModulator':
            out['pitchRange'] = (pr.get('PitchMin', 0.95), pr.get('PitchMax', 1.05))   # (Unreal's defaults)
        elif t == 'SoundNodeWavePlayer':
            for x in re.findall(r'"(?:AssetPathName|ObjectPath)": "([^"]+)"', json.dumps(pr)):
                out['waves'].append((x.split('/')[-1].split('.')[0], pr.get('bLooping', False)))
    return out


def table_cue(table, row):
    """A sound table's (Audio/BP/<table>.json) cue name for a row, or None."""
    p = os.path.join(AUDIO, 'BP', table + '.json')
    if not os.path.exists(p): return None
    rows = json.load(open(p, encoding='utf-8-sig'))[0].get('Rows', {})
    m = re.findall(r'(S_SC_\w+)', json.dumps(rows.get(row, {})))
    return m[0] if m else None


def decode(names):
    """The waves (by name) as playable files: {name: .ogg / .wav path}, and a temporary folder to delete afterwards. The
    export's converted files as they are; raw .binka through vgmstream (one run per 60 files: Wine starts slowly)."""
    waves = _index()[1]
    tmp = tempfile.mkdtemp(prefix='es2audio_')
    out, raw = {}, []
    for n in sorted(set(names)):
        files = waves.get(n, {})
        playable = next((files[e] for e in PLAYABLE if e in files), None)
        if playable: out[n] = playable
        elif '.binka' in files: raw.append(n)
    cmd = vgmstream() if raw else None
    for i in range(0, len(raw) if cmd else 0, 60):
        batch = []
        for n in raw[i:i + 60]:
            dst = os.path.join(tmp, n + '.binka'); shutil.copy(waves[n]['.binka'], dst); batch.append(dst)
        env = dict(os.environ, WINEDEBUG='-all')
        subprocess.run(cmd + batch, cwd=tmp, env=env, capture_output=True)   # writes <file>.wav beside each
        for n in raw[i:i + 60]:
            wav = os.path.join(tmp, n + '.binka.wav')
            if os.path.exists(wav): out[n] = wav
    return out, tmp


def read_wav(path):
    with wave.open(path) as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        data = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32)
    data /= 32768.0 if sw == 2 else 2147483648.0
    return data.reshape(-1, ch).mean(axis=1), rate


def loudness(path, loop=False):
    """How loud a wave sounds: a loop's RMS, a shot's in its loudest 60 ms."""
    x, rate = read_wav(path)
    if loop or len(x) < rate * 0.06: return float(np.sqrt(np.mean(x * x)) + 1e-9)
    win = int(rate * 0.06)
    e = np.convolve(x * x, np.ones(win) / win, mode='valid')
    return float(np.sqrt(e.max()) + 1e-9)


def write(src, rel):
    """A wave into the mod (rel without extension): an .ogg as it is; a .wav as Ogg Vorbis through ffmpeg or the soundfile
    package, else as it is. Returns the path ships.json names, always the .ogg's: the game takes a .wav of the same name in
    its place, so ships.json (which multiplayer compares) is the same whatever this computer could encode."""
    def place(ext):
        dst = os.path.join(MOD, rel + ext)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        return dst
    if src.lower().endswith('.ogg'):
        shutil.copy(src, place('.ogg')); return rel + '.ogg'
    ff = shutil.which('ffmpeg')
    if ff and subprocess.run([ff, '-y', '-loglevel', 'error', '-i', src, '-c:a', 'libvorbis', '-q:a', '5', place('.ogg')],
                             capture_output=True).returncode == 0:
        return rel + '.ogg'
    try:
        import soundfile
        data, rate = soundfile.read(src)
        soundfile.write(place('.ogg'), data, rate, format='OGG', subtype='VORBIS')
        return rel + '.ogg'
    except Exception:
        if os.path.exists(os.path.join(MOD, rel + '.ogg')): os.remove(os.path.join(MOD, rel + '.ogg'))
    shutil.copy(src, place('.wav'))
    return rel + '.ogg'


def r3(v): return round(float(v), 3)


def pitch_range(c):
    """A one-shot's random pitch: the cue's modulator range (none without a modulator node) x its pitch."""
    lo, hi = c['pitchRange'] or (1.0, 1.0)
    return [lo * c['pitch'], hi * c['pitch']]


def build(ships, hardpoints):
    """Writes the sounds and adds them to 'ships' (ships.json's entries, by their "id") and 'hardpoints' (the kits' rules).
    Returns a line for the log."""
    # The cues, by role.
    engine_default = 'S_SC_Engine_001'
    ship_cues = {}
    for s in ships:
        es2 = ES2_TYPE.get(s['id'])
        ship_cues[s['id']] = {
            'engine': (es2 and table_cue('DT_PlayerShip_EngineSounds', es2)) or engine_default,
            'charger': (es2 and table_cue('DT_PlayerShip_BoostChargerSounds', es2)) or 'S_SC_Boost_Charger_002',
        }
    boost = {'boostStart': 'S_SC_Booster_Init', 'boostLoop': 'S_SC_Boost_004', 'boostStop': 'S_SC_Booster_Stop'}
    weapon_cues = {}
    for r in hardpoints['weapons']:
        m = re.search(r'weapon_(\d+)\.glb', r.get('model') or '')
        if m and int(m.group(1)) in WEAPON_CUES: weapon_cues[id(r)] = WEAPON_CUES[int(m.group(1))]
        elif r.get('slot') == 'secondary':
            cats = r.get('categories') or []
            weapon_cues[id(r)] = next((LAUNCHER_CUES[c] for c in cats if c in LAUNCHER_CUES), LAUNCHER_DEFAULT)
    names = set(boost.values()) | set(weapon_cues.values()) | {c for v in ship_cues.values() for c in v.values()}
    cues = {n: cue(n) for n in names}
    cues = {n: c for n, c in cues.items() if c and c['waves']}
    waves = {w for c in cues.values() for w, _ in c['waves']}
    decoded, tmp = decode(waves)
    try:
        written = {}
        def files(c, looping):
            out = []
            for w, lp in c['waves']:
                if lp != looping or w not in decoded: continue
                if w not in written: written[w] = write(decoded[w], 'audio/' + w)
                out.append(written[w])
            return out
        def sound(c, looping, volume, pitch=None):
            fs = files(c, looping)
            if not fs: return None
            s = {'files' if len(fs) > 1 else 'file': fs if len(fs) > 1 else fs[0],
                 'volume': [r3(v) for v in volume] if isinstance(volume, (list, tuple)) else r3(volume)}
            if pitch is not None: s['pitch'] = [r3(p) for p in pitch] if isinstance(pitch, (list, tuple)) else r3(pitch)
            return s
        # Ships: the engine (a touch higher at top speed), the boost (start / loop building up / stop), the charger.
        for s in ships:
            sc, snd = ship_cues[s['id']], {}
            e = cues.get(sc['engine'])
            if e: snd['engine'] = sound(e, True, [0.55 * e['volume'] * GAIN_ENGINE, e['volume'] * GAIN_ENGINE], [0.9, 1.1])
            b = cues.get(boost['boostStart'])
            if b: snd['boostStart'] = sound(b, False, 0.5 * b['volume'] * GAIN_BOOST, pitch_range(b))   # (BP_ShipBase: the component at 0.5)
            b = cues.get(boost['boostLoop'])
            if b: snd['boostLoop'] = sound(b, True, [0.5 * b['volume'] * GAIN_BOOST, b['volume'] * GAIN_BOOST], [1.0, 1.5])   # BoostVolume / PitchMin..Max
            b = cues.get(boost['boostStop'])
            if b: snd['boostStop'] = sound(b, False, b['volume'] * GAIN_BOOST, pitch_range(b))
            c = cues.get(sc['charger'])
            # BoostChargerVolumeMin..Max 0.2 .. 1.5, PitchMin..Max 0.5 .. 2 (BP_Ship_Player); at half the boost's gain: at its
            # top it hissed over the engine.
            if c: snd['charger'] = sound(c, True, [0.2 * c['volume'] * GAIN_BOOST * 0.5, 1.5 * c['volume'] * GAIN_BOOST * 0.5], [0.5, 2.0])
            snd = {k: v for k, v in snd.items() if v}
            if snd: s['sounds'] = snd
        # Weapons: one shot per shot (Unreal's random node, its modulator's pitch), or the beam's ignition and loop.
        made = 0
        for r in hardpoints['weapons']:
            name = weapon_cues.get(id(r))
            c = cues.get(name) if name else None
            if not c: continue
            pr = pitch_range(c)
            w = {}
            shot = sound(c, False, c['volume'] * GAIN_SHOT, pr)
            loop = sound(c, True, c['volume'] * GAIN_SHOT)
            if shot: w['shot'] = shot
            if loop: w['loop'] = loop; w['release'] = 120
            if w: r['sound'] = w; made += 1
        line = f'{len(written)} waves; {sum(1 for s in ships if "sounds" in s)} ships, {made} weapon rules'
        missing = sorted(waves - set(decoded))
        if missing:
            line += (f'; {len(missing)} waves missing or not decoded ({", ".join(missing[:4])}{"..." if len(missing) > 4 else ""}): '
                     'export Audio with FModel\'s "Convert audio on bulk export" on, or check vgmstream')
        return line
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
