# GLB helpers: read accessors (strided or not), rewrite a GLB with only some vertex attributes, de-interleaved.
import json, struct
import numpy as np
COMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
DT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}

def load(path):
    b = open(path, 'rb').read()
    jl = struct.unpack_from('<I', b, 12)[0]
    g = json.loads(b[20:20 + jl])
    o = 20 + jl
    bl = struct.unpack_from('<I', b, o)[0]
    return g, b[o + 8:o + 8 + bl]

def read(g, binary, idx):
    a = g['accessors'][idx]; bv = g['bufferViews'][a['bufferView']]
    n, c = a['count'], COMP[a['type']]; dt = np.dtype(DT[a['componentType']])
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride') or c * dt.itemsize
    raw = np.frombuffer(binary, dtype=np.uint8, count=(n - 1) * stride + c * dt.itemsize, offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, shape=(n, c * dt.itemsize), strides=(stride, 1))
    return np.ascontiguousarray(rows).view(dt).reshape(n, c), a

def rewrite(path_in, path_out, keep=('POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0'), split=None, extra=None):
    """split(g, binary, primitive) -> None, or [(material name, triangle index array uint32), ...]: the primitive becomes
    one primitive per entry, sharing its vertices, each with that (new or existing) glTF material.
    extra(g, binary, primitive) -> None, or {attribute name: float array (vertices x components)}: added attributes."""
    g, binary = load(path_in)
    out_bin = bytearray(); views = []; accs = []; cache = {}
    def add_array(arr, target):
        arr = np.asarray(arr)
        small = arr.size == 0 or int(arr.max()) < 65535
        arr = arr.astype(np.uint16 if small else np.uint32)   # 16-bit indices wherever they fit
        data = np.ascontiguousarray(arr).tobytes()
        while len(out_bin) % 4: out_bin.append(0)
        views.append({'buffer': 0, 'byteOffset': len(out_bin), 'byteLength': len(data), 'target': target})
        out_bin.extend(data)
        accs.append({'bufferView': len(views) - 1, 'componentType': 5123 if small else 5125, 'count': int(arr.size), 'type': 'SCALAR'})
        return len(accs) - 1
    def material(name):
        mats = g.setdefault('materials', [])
        for i, m in enumerate(mats):
            if m.get('name') == name: return i
        mats.append({'name': name, 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.5}})
        return len(mats) - 1
    def add(idx, target):
        if idx in cache: return cache[idx]
        arr, a = read(g, binary, idx)
        data = arr.tobytes()
        while len(out_bin) % 4: out_bin.append(0)
        views.append({'buffer': 0, 'byteOffset': len(out_bin), 'byteLength': len(data), **({'target': target} if target else {})})
        out_bin.extend(data)
        na = {k: v for k, v in a.items() if k not in ('bufferView', 'byteOffset')}
        na['bufferView'] = len(views) - 1
        accs.append(na); cache[idx] = len(accs) - 1
        return cache[idx]
    for m in g.get('meshes', []):
        prims = []
        for p in m['primitives']:
            parts = split(g, binary, p) if split else None
            attrs = {k: add(v, 34962) for k, v in p['attributes'].items() if k in keep}
            for k, arr in ((extra(g, binary, p) if extra else None) or {}).items():
                arr = np.ascontiguousarray(arr, dtype=np.float32)
                data = arr.tobytes()
                while len(out_bin) % 4: out_bin.append(0)
                views.append({'buffer': 0, 'byteOffset': len(out_bin), 'byteLength': len(data), 'target': 34962})
                out_bin.extend(data)
                accs.append({'bufferView': len(views) - 1, 'componentType': 5126, 'count': int(arr.shape[0]), 'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[arr.shape[1]]})
                attrs[k] = len(accs) - 1
            if parts:
                for name, idx in parts:
                    if idx.size == 0: continue
                    q = {k: v for k, v in p.items() if k not in ('attributes', 'indices', 'material', 'targets')}
                    q['attributes'] = dict(attrs); q['indices'] = add_array(idx.astype(np.uint32), 34963); q['material'] = material(name)
                    prims.append(q)
                continue
            p['attributes'] = attrs
            if 'indices' in p: p['indices'] = add_array(read(g, binary, p['indices'])[0].reshape(-1), 34963)
            p.pop('targets', None)
            prims.append(p)
        m['primitives'] = prims
    g['accessors'] = accs; g['bufferViews'] = views
    g['buffers'] = [{'byteLength': len(out_bin)}]
    for k in ('images', 'textures', 'samplers'): g.pop(k, None)   # none in these exports
    js = json.dumps(g, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
    while len(out_bin) % 4: out_bin.append(0)
    total = 12 + 8 + len(js) + 8 + len(out_bin)
    with open(path_out, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total)); f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(out_bin), 0x004E4942)); f.write(out_bin)

def save(path, g, out_bin):
    """Writes a glTF JSON + binary chunk as a GLB."""
    out_bin = bytearray(out_bin)
    g['buffers'] = [{'byteLength': len(out_bin)}]
    js = json.dumps(g, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
    while len(out_bin) % 4: out_bin.append(0)
    total = 12 + 8 + len(js) + 8 + len(out_bin)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total)); f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(out_bin), 0x004E4942)); f.write(out_bin)

def add_node(path, name, translation):
    """Adds an empty node (a marker such as "muzzle") under the scene's first root node of a GLB, in place."""
    g, binary = load(path)
    root = g['scenes'][g.get('scene', 0)]['nodes'][0]
    g['nodes'].append({'name': name, 'translation': [float(v) for v in translation]})
    g['nodes'][root].setdefault('children', []).append(len(g['nodes']) - 1)
    save(path, g, binary)

def add_primitives(path, prims):
    """Adds primitives to a GLB's meshes, in place: prims = [(mesh index, material name, {attribute: float array}, triangle
    index array), ...]; each gets its own vertices (POSITION carries min / max)."""
    g, binary = load(path)
    out = bytearray(binary)
    def put(arr, target, ctype, kind):
        data = np.ascontiguousarray(arr).tobytes()
        while len(out) % 4: out.append(0)
        g['bufferViews'].append({'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data), 'target': target})
        out.extend(data)
        a = {'bufferView': len(g['bufferViews']) - 1, 'componentType': ctype, 'count': int(arr.shape[0]), 'type': kind}
        g['accessors'].append(a)
        return len(g['accessors']) - 1, a
    for mesh, mat, attrs, idx in prims:
        if len(idx) == 0: continue
        mats = g.setdefault('materials', [])
        mi = next((i for i, m in enumerate(mats) if m.get('name') == mat), None)
        if mi is None:
            mats.append({'name': mat, 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.5}})
            mi = len(mats) - 1
        prim = {'attributes': {}, 'material': mi}
        for k, arr in attrs.items():
            arr = np.asarray(arr, np.float32)
            ai, a = put(arr, 34962, 5126, {2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[arr.shape[1]])
            if k == 'POSITION': a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
            prim['attributes'][k] = ai
        idx = np.asarray(idx).reshape(-1)
        small = int(idx.max()) < 65535
        prim['indices'] = put(idx.astype(np.uint16 if small else np.uint32), 34963, 5123 if small else 5125, 'SCALAR')[0]
        g['meshes'][mesh]['primitives'].append(prim)
    save(path, g, out)

class Writer:
    """Builds a GLB from numpy arrays: meshes of primitives, nodes, materials by name."""
    def __init__(self):
        self.g = {'asset': {'version': '2.0', 'generator': 'es2_ships build.py'}, 'scene': 0, 'scenes': [{'nodes': []}],
                  'nodes': [], 'meshes': [], 'materials': [], 'accessors': [], 'bufferViews': []}
        self.bin = bytearray()
    def material(self, name):
        for i, m in enumerate(self.g['materials']):
            if m['name'] == name: return i
        self.g['materials'].append({'name': name, 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.5}})
        return len(self.g['materials']) - 1
    def accessor(self, arr, target, kind=None):
        arr = np.ascontiguousarray(arr)
        ctype = {np.dtype(np.float32): 5126, np.dtype(np.uint16): 5123, np.dtype(np.uint32): 5125}[arr.dtype]
        data = arr.tobytes()
        while len(self.bin) % 4: self.bin.append(0)
        self.g['bufferViews'].append({'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data), 'target': target})
        self.bin.extend(data)
        a = {'bufferView': len(self.g['bufferViews']) - 1, 'componentType': ctype, 'count': int(arr.shape[0]),
             'type': kind or {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[1 if arr.ndim == 1 else arr.shape[1]]}
        if kind is None and arr.ndim == 2 and arr.shape[1] == 3:
            a['min'] = arr.min(axis=0).tolist(); a['max'] = arr.max(axis=0).tolist()
        self.g['accessors'].append(a)
        return len(self.g['accessors']) - 1
    def mesh(self, name, prims):
        """prims: [(attrs {name: float32 array}, triangle indices, material name)]"""
        out = []
        for attrs, idx, mat in prims:
            if idx.size == 0: continue
            a = {k: self.accessor(v.astype(np.float32), 34962) for k, v in attrs.items()}
            small = int(idx.max()) < 65535
            out.append({'attributes': a, 'indices': self.accessor(idx.astype(np.uint16 if small else np.uint32), 34963), 'material': self.material(mat)})
        if not out: return None
        self.g['meshes'].append({'name': name, 'primitives': out})
        return len(self.g['meshes']) - 1
    def node(self, name, translation=None, mesh=None, parent=None):
        n = {'name': name}
        if translation is not None: n['translation'] = [float(v) for v in translation]
        if mesh is not None: n['mesh'] = mesh
        self.g['nodes'].append(n); i = len(self.g['nodes']) - 1
        if parent is None: self.g['scenes'][0]['nodes'].append(i)
        else: self.g['nodes'][parent].setdefault('children', []).append(i)
        return i
    def write(self, path):
        save(path, self.g, self.bin)
