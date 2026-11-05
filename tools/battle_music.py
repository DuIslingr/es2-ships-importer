# The sectors' fight music (the remake's systems.json "battleMusic": [low, medium, full] for GoF2's three battle tracks by
# the hostiles around: 1-2, 3-4, 5+). EVERSPACE 2 plays a LayeredSong (S_SC_LayeredSong_NNN: a mixer of three looping
# layers, 1Calm, 2Tense, 3Battle, each with its own volume parameter its music manager crossfades; the layers are whole
# mixes of about the same loudness, not stems) and in a fight switches to the sector's battle set
# (Audio/MusikSets/DA_MusicSet_Battle_Sector_NNN), whose _BattleOnly songs play their 3Battle layer alone
# (DA_LayeredSong_NNN_BattleOnly: UsedLayers false, false, true). So:
#   low            the 2Tense layer of the sector's own first song (the one whose 1Calm layer is its spaceMusic;
#                  music/es2_tense_<song>, shared by the sectors with the same song)
#   medium, full   the 3Battle layers of its battle set's songs, one after the other (music/es2_battle_<set>: the ten
#                  sectors share three sets, each written once)
# ES2's transitions (Transition_0To1 / 1To0 / End) and its bar-synced crossfades are left out: the remake fades.
import json, os, shutil, subprocess

import audio

QUALITY = 3   # Ogg Vorbis -q:a (~110 kbit/s): ten sectors' worth of long songs at the calm music's 5 came to 44 MB

SRC = None   # the export's Content folder (sectors.SRC)


def _songs(set_name):
    """The song numbers of Audio/MusikSets/DA_MusicSet_<set_name> ('003', 'Okkar_001', ...; [] when missing)."""
    p = os.path.join(SRC, f'Audio/MusikSets/DA_MusicSet_{set_name}.json')
    if not os.path.exists(p): return []
    out = []
    for s in json.load(open(p, encoding='utf-8-sig'))[0]['Properties'].get('SongList', []):
        n = s['AssetPathName'].rsplit('.', 1)[-1].replace('DA_LayeredSong_', '')
        for tail in ('_BattleOnly', '_NoBattle', '_TenseAndBattle'): n = n.replace(tail, '')
        out.append(n)
    return out


def _layer(song, which):
    """The wave names a song's layer may have (ES2 spells some '3Batttle', and song 073's waves have no 'S_')."""
    spellings = [which] + (['3Batttle'] if which == '3Battle' else [])
    return [f'{pre}LayeredSong_{song}_{w}' for pre in ('S_', '') for w in spellings]


def _join(files, rel):
    """Concatenates playable files into the mod's rel (.ogg) at QUALITY; the path, or None."""
    ff = shutil.which('ffmpeg')
    if not files: return None
    if not ff: return audio.write(files[0], rel)   # (without ffmpeg the first song alone, as audio.write can)
    dst = os.path.join(audio.MOD, rel + '.ogg')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cmd = [ff, '-y', '-loglevel', 'error']
    for f in files: cmd += ['-i', f]
    cmd += ['-filter_complex', ''.join(f'[{i}:a]' for i in range(len(files))) + f'concat=n={len(files)}:v=0:a=1[out]',
            '-map', '[out]', '-c:a', 'libvorbis', '-q:a', str(QUALITY), dst]
    return rel + '.ogg' if subprocess.run(cmd, capture_output=True).returncode == 0 else None


def add(sectors, log=print):
    """sectors: [(sector key 'S01', its systems.json entry)]. Writes the tracks and sets each system's "battleMusic"."""
    plan, sets = {}, {}
    for key, system in sectors:
        num = f'{int(key[1:]):03d}'
        own = _songs(f'Sector_{num}')
        battle = tuple(_songs(f'Battle_Sector_{num}'))
        if not battle: continue
        sets.setdefault(battle, chr(ord('a') + len(sets)))
        plan[system['id']] = (own[0] if own else None, battle)
    if not plan: return 0
    names = [n for own, battle in plan.values() for s in ((own,) if own else ()) + battle
             for which in (('2Tense',) if s == own else ()) + ('3Battle',) for n in _layer(s, which)]
    waves, tmp = audio.decode(names)
    try:
        def find(song, which): return next((waves[n] for n in _layer(song, which) if n in waves), None)
        battle_tracks = {}
        for battle, letter in sets.items():
            files = [f for f in (find(s, '3Battle') for s in battle) if f]
            battle_tracks[battle] = _join(files, f'music/es2_battle_{letter}')
            if battle_tracks[battle]: log(f'  battle music es2_battle_{letter}: {len(files)} songs ({", ".join(battle)})')
        n, tense_tracks = 0, {}
        for key, system in sectors:
            if system['id'] not in plan: continue
            own, battle = plan[system['id']]
            fight = battle_tracks.get(battle)
            if not fight: continue
            fight = os.path.splitext(os.path.basename(fight))[0]
            if own not in tense_tracks:
                tense = find(own, '2Tense') if own else None
                tense_tracks[own] = _join([tense], f'music/es2_tense_{own}') if tense else None
            low = os.path.splitext(os.path.basename(tense_tracks[own]))[0] if tense_tracks[own] else fight
            system['battleMusic'] = [low, fight, fight]
            n += 1
        return n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
