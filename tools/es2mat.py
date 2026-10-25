"""EVERSPACE 2's material instances (FModel's .json exports) as the remake's ships.json "materials" entries.

FModel writes a material two ways: its model export's resolved form (a dict: "Textures", "Colors", "Scalars", "Switches",
"BlendMode", the whole parent chain already applied) and the package's properties (a list: the instance's own parameters and its
"Parent"). resolve() reads either, walking a list-form chain up to its root material and letting each child's values win.

classify() sorts a material into what the remake can draw:
  "decal"      M_*Decal*: cut away (they need ES2's decal atlas and projections);
  "field"      force fields / energy fields: see-through glow (a capital ship's "shieldMaterial" shows and hides them);
  "flame"      M_Vehicle_EngineExhaust: an engine flame (build.flame());
  "glow"       emissive-only materials (windows, lamps, the Okkar emissive, blockout glows): their colour, glowing;
  "glass"      glass;
  "dark"       interior occlusion: black;
  "pbr"        everything else: its textures, the packed masks split by their channel names (T_..._C_R_MT_E: colour /
               roughness / metal / emission), the base colour tints (BaseColor, BaseColor1-3 / BaseColorVtxR-B by the mesh's
               vertex colour masks when UseVertexColorMasks is on), Tiling, alpha clipping for masked materials.
The textures are made by the caller (save()): this module only reads parameters."""
import json, os, re, glob, functools

ROOT = None


def configure(src):
    global ROOT
    ROOT = src
    _index.cache_clear()


@functools.lru_cache(None)
def _index():
    """Every .json / .png of the export by its file name (without extension)."""
    j, p = {}, {}
    for f in glob.glob(os.path.join(ROOT, '**', '*.json'), recursive=True): j.setdefault(os.path.basename(f)[:-5], f)
    for f in glob.glob(os.path.join(ROOT, '**', '*.png'), recursive=True): p.setdefault(os.path.basename(f)[:-4], f)
    return j, p


def _name(path_or_name):
    """'/Game/A/B/MI_X.0' / "Texture2D'T_X'" / 'MI_X' -> 'MI_X'."""
    s = path_or_name or ''
    if "'" in s: s = s.split("'")[1]
    return s.split('/')[-1].split('.')[0]


def texture_file(name):
    return _index()[1].get(_name(name))


def _load(name):
    f = _index()[0].get(_name(name))
    if not f: return None
    try: return json.load(open(f, encoding='utf-8-sig'))
    except Exception: return None


def _hex(c):
    if isinstance(c, dict) and c.get('Hex'): h = c['Hex'][:6]; return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    if isinstance(c, dict):   # linear R / G / B -> sRGB
        return [max(0.0, min(1.0, float(c.get(k, 0)))) ** (1 / 2.2) for k in 'RGB']
    return None


@functools.lru_cache(None)
def resolve(name):
    """{'name', 'root', 'chain', 'blend', 'tex': {param: texture name}, 'col': {param: sRGB [r, g, b]}, 'sca', 'sw'}."""
    out = {'name': _name(name), 'chain': [], 'blend': 0, 'tex': {}, 'col': {}, 'cola': {}, 'sca': {}, 'sw': {}}
    d = _load(name)
    if isinstance(d, dict):
        out['chain'].append(out['name'])
        out['blend'] = d.get('BlendMode', 0) or 0
        for k, v in (d.get('Textures') or {}).items():
            if isinstance(v, dict) and v.get('ObjectPath'): out['tex'][k] = _name(v['ObjectPath'])
        for k, v in (d.get('Colors') or {}).items():
            out['col'][k] = _hex(v)
            if isinstance(v, dict) and 'A' in v: out['cola'][k] = float(v['A'])
        out['sca'] = dict(d.get('Scalars') or {})
        out['sw'] = dict(d.get('Switches') or {})
        # (its root material isn't named in this form: the instance's properties file, when there is one, is also
        # read below for the chain)
    seen = set()
    cur = name
    while cur and _name(cur) not in seen:
        seen.add(_name(cur))
        d2 = _load(cur) if not isinstance(d, dict) or _name(cur) != out['name'] else None
        if isinstance(d2, list) and d2:
            e = d2[0]; pr = e.get('Properties', {})
            if _name(cur) not in out['chain']: out['chain'].append(_name(cur))
            if e.get('Type') == 'Material':
                out['blend'] = out['blend'] or _blend(pr.get('BlendMode'))
                break
            out['blend'] = out['blend'] or _blend((pr.get('BasePropertyOverrides') or {}).get('BlendMode'))
            for t in pr.get('TextureParameterValues', []):
                v = t.get('ParameterValue') or {}
                if v.get('ObjectPath'): out['tex'].setdefault(t['ParameterInfo']['Name'], _name(v['ObjectPath']))
            for t in pr.get('VectorParameterValues', []):
                out['col'].setdefault(t['ParameterInfo']['Name'], _hex(t.get('ParameterValue') or {}))
                if 'A' in (t.get('ParameterValue') or {}): out['cola'].setdefault(t['ParameterInfo']['Name'], float(t['ParameterValue']['A']))
            for t in pr.get('ScalarParameterValues', []):
                out['sca'].setdefault(t['ParameterInfo']['Name'], t.get('ParameterValue'))
            for t in ((pr.get('StaticParametersRuntime') or pr.get('StaticParameters') or {}).get('StaticSwitchParameters') or []):
                out['sw'].setdefault(t['ParameterInfo']['Name'], t.get('Value'))
            par = pr.get('Parent')
            cur = par.get('ObjectPath') if par else None
        else:
            # a dict-form instance: its parent from the properties file isn't available; the chain ends here
            if isinstance(d2, dict) or d2 is None:
                if cur != name: out['chain'].append(_name(cur))
            break
    out['root'] = out['chain'][-1] if out['chain'] else out['name']
    return out


def _blend(v):
    if v is None: return 0
    s = str(v)
    return 2 if 'Translucent' in s or 'Additive' in s else 1 if 'Masked' in s else 0


def classify(m):
    names = ' '.join(m['chain']).lower()
    if 'decal' in names: return 'decal'
    if 'forcefield' in names or 'energyabsorbing' in names or 'energyshield' in names or 'stasisbubble' in names: return 'field'
    if 'engineexhaust' in names: return 'flame'
    if 'interioroccl' in names: return 'dark'
    if 'glass' in names and not _tex(m, COLOUR + MASKS): return 'glass'   # (a full parent chain brings noise / grunge maps)
    if ('emissive' in names or 'window' in names or 'glow' in names or 'neon' in names or 'blockout' in names
            or 'transparent' in names) and not _tex(m, COLOUR + MASKS):
        return 'glow'
    if m['blend'] == 2 and not _tex(m, COLOUR + MASKS): return 'glow'
    return 'pbr'


COLOUR = ['ColorTexture', 'C', 'PM_Diffuse', 'Diffuse', 'BaseColorTexture', 'C_A', 'Color', 'Albedo', 'BaseColor']
MASKS = ['Masks', 'C_R_MT_A', 'C_R_MT_E', 'R_E_A', 'Roughness', 'R_MT_E', 'C_R_E', 'C_R_M', 'Mask']
CODES = {'C', 'R', 'MT', 'M', 'E', 'A', 'AO', 'H', 'N', 'O', 'D'}   # channel letters in a packed texture's name
NORMAL = ['N', 'Normal Map', 'Normal', 'NormalMap', 'PM_Normals']
ALPHA = ['ColorAlphaMask', 'Alpha Mask', 'AlphaMask', 'Opacity']


def _tex(m, keys):
    for k in keys:
        t = m['tex'].get(k)
        if t and texture_file(t): return t
    return None


def channels(tex):
    """A packed texture's channels by its name's suffix: T_X_001_C_R_MT_E -> ['C', 'R', 'MT', 'E'] (R, G, B, A); an RGB colour
    map (_C, _C_A, _C_AO) -> ['RGB', 'A' / 'AO']."""
    parts = _name(tex).split('_')
    digits = [i for i, p in enumerate(parts) if p.isdigit()]
    if digits and digits[-1] < len(parts) - 1:
        toks = [p.upper() for p in parts[digits[-1] + 1:]]
    else:
        # the channel letters at the end, before a trailing number (T_Container_C_R_MT_001) or without one
        # (T_Structures_Trims_GB_C_R_MT)
        end = len(parts) - 1 if digits else len(parts)
        i = end
        while i > 1 and parts[i - 1].upper() in CODES: i -= 1
        toks = [p.upper() for p in parts[i:end]]
    if not toks: return ['RGB']
    if toks[0] == 'C' and len(toks) <= 2 and (len(toks) == 1 or toks[1] in ('A', 'AO', 'M')): return ['RGB'] + toks[1:]
    return toks


def structure(m):
    """M_Structures_Parent's family: its base colour is saturate(the masks' curvature channel x 2 x the tint), the tint lerped
    BaseColor -> VtxR -> VtxG -> VtxB by the vertex colour, each weighted by its tint's alpha (its compiled base-pass
    shader). Known by a BaseColor beside a CurvatureChannel: the vehicle parents (the Ancient Swarmer) have the channel
    selector without a BaseColor."""
    return 'CurvatureChannel' in m['col'] and 'BaseColor' in m['col']


def _channel_vec(m, key):
    """A material's channel selector (RoughnessChannel '00FF00' ...): 0-3, or None."""
    c = m['col'].get(key)
    if not c: return None
    i = max(range(3), key=lambda k: c[k])
    return i if c[i] > 0.5 else None


def plan(m):
    """What a "pbr" material needs: {'colour': (texture, mode), 'normal', 'rough': (texture, channel), 'metal': ..., 'emit':
    ..., 'alpha': ..., 'tint': [r, g, b], 'tints': [V1, V2, V3] by vertex colour, 'tiling', 'metallic', 'smoothness',
    'emissionColor', 'emission'}."""
    p = {}
    col = _tex(m, COLOUR)
    masks = _tex(m, MASKS)
    if col and col == masks: masks = None
    if structure(m) and m['sw'].get('UseColorTexture') is False:
        # M_Structures_Parent's family (its compiled shader): with its UseColorTexture switch off the colour is the masks'
        # curvature channel (structure_colour), and a 'C' map in the list is only a parent's default (no such parameter in
        # the compiled shader: the containers, the red tarp)
        col = None
    if col:
        ch = channels(col)
        p['colour'] = (col, 'rgb' if ch[0] == 'RGB' else ch.index('C') if 'C' in ch else 'rgb')
    if masks:
        ch = channels(masks)
        def at(code, vec):
            # the texture's own channel letters first: a selector inherited from a parent can name another texture's
            # layout (Plating_002's EmissiveChannel picked the metal of its C_R_MT)
            if len(ch) > 1 and ch[0] != 'RGB': return ch.index(code) if code in ch else None
            v = _channel_vec(m, vec)
            if v is not None: return v
            return ch.index(code) if code in ch else None
        r, mt, e = at('R', 'RoughnessChannel'), at('MT', 'MetalnessChannel'), at('E', 'EmissiveChannel')
        if r is not None: p['rough'] = (masks, r)
        if mt is not None: p['metal'] = (masks, mt)
        if e is not None: p['emit'] = (masks, e)
        if 'C' in ch and 'colour' not in p: p['colour'] = (masks, ch.index('C'))
        if 'A' in ch: p['alpha'] = (masks, ch.index('A'))
        elif 'M' in ch and m['blend'] == 1: p['alpha'] = (masks, ch.index('M'))   # (foliage's C_R_M: M the opacity mask)
    if m['blend'] == 1 and not masks and 'colour' not in p:
        # a masked parent naming its maps only by their defaults (M_Structures_Floaters_Parent: T_X_R_E_A, its B the
        # cut-out, and T_X_C_AO the colour)
        for t in sorted(set(m['tex'].values())):
            ch = channels(t)
            if 'A' not in ch or ch[0] == 'RGB' or not texture_file(t): continue
            p['alpha'] = (t, ch.index('A'))
            if 'R' in ch: p['rough'] = (t, ch.index('R'))
            stem = t.rsplit('_', len(ch))[0]
            c = next((u for u in sorted(set(m['tex'].values())) if u.startswith(stem + '_') and u != t
                      and channels(u)[0] == 'RGB' and texture_file(u)), None)
            p['colour'] = (c, 'rgb') if c else (t, ch.index('A'))
            break
    if 'colour' in p and p['colour'][1] == 'rgb' and 'A' in channels(p['colour'][0]): p.setdefault('alpha', (p['colour'][0], 3))
    am = _tex(m, ALPHA)
    if am and m.get('sw', {}).get('UseColorAlphaMask', True): p['alphaMask'] = am
    n = _tex(m, NORMAL)
    if n: p['normal'] = n
    base = m['col'].get('BaseColor') or m['col'].get('Color') or [1, 1, 1]
    p['tint'] = base
    if m['sw'].get('UseVertexColorMasks'):
        p['tints'] = [m['col'].get(f'BaseColor{i}') or m['col'].get('BaseColorVtx' + 'RGB'[i - 1]) or base for i in (1, 2, 3)]
        # each lerp toward a vertex channel's tint is weighted by that tint's alpha (M_Structures_Parent: v.x x VtxR.a ...;
        # the red tarp's are 0: no tint)
        p['tintw'] = [m['cola'].get('BaseColorVtx' + 'RGB'[i], 1.0) for i in range(3)]
    t = m['sca'].get('Tiling')
    if t and abs(t - 1) > 1e-3: p['tiling'] = float(t)
    mo = m['sca'].get('MetalOverride', m['sca'].get('MetalnessOverride'))
    if mo is not None and mo >= 0 and 'metal' not in p: p['metallic'] = float(mo)
    if 'Metal' in m['sca'] and 'metal' not in p: p['metallic'] = float(m['sca']['Metal'])
    br = m['sca'].get('BaseRoughness', m['sca'].get('Roughness'))
    if br is not None and 'rough' not in p: p['smoothness'] = max(0.0, min(1.0, 1.0 - float(br)))
    ec = m['col'].get('EmissiveColor')
    ei = m['sca'].get('EmissiveIntensity', m['sca'].get('Emissive', 1.0)) or 0.0
    if ec and max(ec) > 0.02 and ei > 0 and 'emit' in p:
        p['emissionColor'] = ec
        p['emission'] = round(min(6.0, max(0.8, float(ei) / 3.0)), 2)
    return p


def glow_colour(m):
    """An emissive-only material's colour and strength."""
    for k in ('EmissiveColor', 'Color', 'Colour', 'Glow Color', 'GlowColor', 'Emissive Color', '1) Primary', 'Color_1', 'BaseColor'):
        c = m['col'].get(k)
        if c and max(c) > 0.02: break
    else:
        c = [1.0, 0.95, 0.85]
    i = m['sca'].get('EmissiveIntensity', m['sca'].get('Emissive', m['sca'].get('Intensity', 5.0)))
    try: i = float(i)
    except Exception: i = 5.0
    return c, round(min(6.0, max(1.5, i / 3.0)), 2)


def vertex_tints(m):
    """The Okkar-style emissive by vertex colour ('1) Primary' / '2) Secondary' / '3) Tertiary'), or None."""
    keys = ['1) Primary', '2) Secondary', '3) Tertiary']
    if all(k in m['col'] for k in keys): return [m['col'][k] for k in keys]
    return None
