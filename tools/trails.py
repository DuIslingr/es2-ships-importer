"""EVERSPACE 2's customization engine trails (DT_ShipExhaustParticles: the Customize screen's Engine trail / Booster trail)
for the kits' "trails" (the remake's ModShipKits.EngineTrail, run by Es2Trails): each row's kind, its Niagara system's curve
tables (ShaderLUT, in the order Es2Trails reads them), the textures its materials sample and the shape trails' cross-section
meshes. What each system and material does: research/engine_trails.md."""
import json
import os
import struct

from PIL import Image

# DT_ShipExhaustParticles row -> the remake's kind
ROW_KIND = {'Default': 'default', 'Glitter': 'glitter', 'Rings': 'rings', 'Veils': 'veils', 'Triangles': 'triangles',
            'Squares': 'squares', 'FireTrail': 'firetrail', 'Sparks': 'sparks', 'Lightning': 'lightning', 'SpeedLines': 'lines',
            'Smoke': 'smoke', 'Bubbles': 'bubbles', 'DarkTrail': 'darktrail'}

# The curves Es2Trails reads, in its order: (the emitter, in the order the system lists them, the curve's index in its update
# script). (The export names the emitters with suffixes, Glitter_0, CrossShape_1, Empty001_8.)
CURVES = {
    'glitter': [(0, 0)],
    'smoke': [(0, 0), (0, 1)],                 # size, alpha
    'bubbles': [(0, 0), (0, 1), (0, 2)],       # colour, size, alpha
    'sparks': [(0, 0), (0, 1)],                # size, -
    'darktrail': [(0, 0)], 'firetrail': [(0, 0)], 'lines': [(0, 0)],
    'lightning': [(0, 0), (1, 0), (1, 1)],     # ribbon alpha, arc size, arc alpha
    'rings': [(0, 0), (0, 1)],                 # alpha, scale
    'squares': [(0, 0), (0, 1)],
    'triangles': [(0, 0), (0, 1)],
    'veils': [(0, 0), (1, 0)],                 # each veil's alpha
}

# The textures (Assets/Shared/Textures/Effects) each kind's materials sample: (field, texture)
TEXTURES = {
    'glitter': [('texture', 'T_Pattern_Barcode_001')],
    'smoke': [('texture', 'T_SmokeSeamless_001_H'), ('mask', 'T_SmokePuff_002_M'), ('normal', 'T_Sphere_001_N')],
    'bubbles': [('normal', 'T_Sphere_001_N')],
    'darktrail': [('texture', 'T_Noise_020_M')],
    'firetrail': [('texture', 'T_Noise_020_M')],
    'lines': [('texture', 'T_Noise_012_M')],
    'lightning': [('texture', 'T_Pattern_Barcode_001')],
}

MESHES = {'rings': 'SM_CrossShape_Circle', 'squares': 'SM_CrossShape_Square', 'triangles': 'SM_CrossShape_Triangle'}


def _curves(system_json, kind):
    """The kind's curve LUTs from its Niagara system's export (each a list over the normalized age 0..1)."""
    by, emitters = {}, []
    for o in json.load(open(system_json, encoding='utf-8')):
        if o.get('Type') != 'NiagaraDataInterfaceCurve': continue
        outer = (o.get('Outer') or {}).get('ObjectName', '')
        emitter = outer.split(':', 1)[-1].split('.', 1)[0] if ':' in outer else ''
        if emitter not in emitters: emitters.append(emitter)
        index = int(o['Name'].rsplit('_', 1)[-1])
        lut = (o.get('Properties') or {}).get('ShaderLUT') or []
        by[(emitters.index(emitter), index)] = [round(float(x), 5) for x in lut]
    out = []
    for key in CURVES.get(kind, []):
        if key not in by: raise KeyError(f'{os.path.basename(system_json)}: no curve {key}')
        out.append(by[key])
    return out


def _glb_mesh(path):
    """A cross-section mesh as EVERSPACE 2's centimetres and axes (FModel's glTF: metres, (x, z, y))."""
    b = open(path, 'rb').read()
    jl = struct.unpack_from('<I', b, 12)[0]
    j = json.loads(b[20:20 + jl])
    bin0 = 20 + jl + 8
    prim = j['meshes'][0]['primitives'][0]

    def acc(i):
        a = j['accessors'][i]
        v = j['bufferViews'][a['bufferView']]
        comps = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        fmt = {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B'}[a['componentType']]
        size = struct.calcsize(fmt)
        stride = v.get('byteStride', size * comps)
        off = bin0 + v.get('byteOffset', 0) + a.get('byteOffset', 0)
        return [struct.unpack_from('<' + fmt * comps, b, off + k * stride) for k in range(a['count'])]

    pos = acc(prim['attributes']['POSITION'])
    nrm = acc(prim['attributes']['NORMAL'])
    uv = acc(prim['attributes']['TEXCOORD_0'])
    idx = [i[0] for i in acc(prim['indices'])]
    flat = lambda rows, k=1.0: [round(c * k, 5) for r in rows for c in r]
    return {'positions': flat([(p[0], p[2], p[1]) for p in pos], 100.0),
            'normals': flat([(n[0], n[2], n[1]) for n in nrm]),
            'uv': flat(uv), 'indices': idx}


def build(src, mod, table, log=print):
    """The kits' "trails": every row of DT_ShipExhaustParticles, with its curves, textures (into trails/) and mesh."""
    try: rows = table('DT_ShipExhaustParticles.json')
    except FileNotFoundError:
        log('  no DT_ShipExhaustParticles: no engine trails')
        return []
    fx = os.path.join(src, 'Assets/Vehicles/Effects/Particles')
    tex = os.path.join(src, 'Assets/Shared/Textures/Effects')
    meshes = os.path.join(src, 'Assets/Shared/Meshes')
    icons = os.path.join(src, 'UI/Images/Items')
    os.makedirs(os.path.join(mod, 'trails'), exist_ok=True)
    out, copied = [], set()
    for rid, r in rows.items():
        kind = ROW_KIND.get(rid)
        if kind is None:
            log(f'  trail row {rid}: unknown (left out)')
            continue
        e = {'id': rid.lower(), 'name': r['ParticlesName']['SourceString'], 'kind': kind}
        icon = (r.get('Icon') or {}).get('AssetPathName', '').rsplit('/', 1)[-1].split('.')[0]
        if icon and os.path.exists(os.path.join(icons, icon + '.png')):
            Image.open(os.path.join(icons, icon + '.png')).convert('RGBA').save(os.path.join(mod, 'trails', e['id'] + '_icon.png'), optimize=True)
            e['icon'] = f'trails/{e["id"]}_icon.png'
        if kind != 'default':
            system = (r.get('ParticleSystem') or {}).get('AssetPathName', '').rsplit('/', 1)[-1].split('.')[0]
            e['curves'] = _curves(os.path.join(fx, system + '.json'), kind)
            for field, name in TEXTURES.get(kind, []):
                f = os.path.join(tex, name + '.png')
                if not os.path.exists(f): raise FileNotFoundError(f'{name}.png (export Assets/Shared/Textures/Effects)')
                if name not in copied:
                    # (the masks are sampled for their red channel, sRGB; the normal map whole)
                    Image.open(f).convert('RGB').save(os.path.join(mod, 'trails', name + '.png'), optimize=True)
                    copied.add(name)
                e[field] = f'trails/{name}.png'
            if kind in MESHES:
                e['mesh'] = _glb_mesh(os.path.join(meshes, MESHES[kind] + '.glb'))
        out.append(e)
    log(f'  {len(out)} engine trails (' + ', '.join(t['name'] for t in out) + ')')
    return out
