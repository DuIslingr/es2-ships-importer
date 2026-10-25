"""Renders a mod's interiors.json room in Blender from its own files, to compare with the game's capture:
blender -b -P render_room.py -- <mod folder> <interior id> <out.png> [camera marker] [target marker]
The room GLB is imported, every glTF material replaced by its interiors.json entry (by the 'material' filter, as
ModShipBuilder.MaterialFor does): diffuse x color, normal (OpenGL, as the importer writes it), metallicSmoothness (R metal,
A smoothness), emission, opacity / alphaClip, tiling. The camera is the room's marker (Unity room metres, x mirrored by
glTFast), its vertical field of view the room's fov; the key light at the 'light' marker, the ambient as the world colour."""
import bpy, json, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
mod, rid, out = argv[0], argv[1], argv[2]
cam_name = argv[3] if len(argv) > 3 else 'camera'
tgt_name = argv[4] if len(argv) > 4 else 'camera_target'
room = next(r for r in json.load(open(os.path.join(mod, 'interiors.json'))) if r['id'] == rid)
S = room.get('scale', 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(mod, room['model']))
for o in bpy.context.scene.objects:
    if o.parent is None: o.scale = (S, S, S)


def B(u):
    """Unity room metres -> Blender (glTFast mirrors x: glTF = (-ux, uy, uz); Blender = (gx, -gz, gy))."""
    return Vector((-u[0], -u[2], u[1]))


images = {}


def img(rel, colour):
    p = os.path.join(mod, rel)
    if not os.path.exists(p): print('MISSING', rel); return None
    key = (p, colour)
    if key not in images:
        im = bpy.data.images.load(p)
        im.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        images[key] = im
    return images[key]


def make(spec):
    m = bpy.data.materials.new(spec['material'])
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N['Principled BSDF']
    uv = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    t = spec.get('tiling', 1.0)
    mp.inputs['Scale'].default_value = (t, t, 1)
    L.new(uv.outputs['UV'], mp.inputs['Vector'])

    def tex(rel, colour):
        im = img(rel, colour)
        if im is None: return None
        n = N.new('ShaderNodeTexImage'); n.image = im
        L.new(mp.outputs['Vector'], n.inputs['Vector'])
        return n
    col = spec.get('color', [1, 1, 1])
    base = (*[c ** 2.2 for c in col[:3]], 1)       # sRGB colour -> linear, as Unity's colour space does
    d = tex(spec['diffuse'], True) if spec.get('diffuse') else None
    if d:
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        L.new(d.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = base
        L.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = base
    if spec.get('normal'):
        n = tex(spec['normal'], False)
        if n:
            nm = N.new('ShaderNodeNormalMap'); L.new(n.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if spec.get('metallicSmoothness'):
        n = tex(spec['metallicSmoothness'], False)
        if n:
            sep = N.new('ShaderNodeSeparateColor'); L.new(n.outputs['Color'], sep.inputs['Color'])
            L.new(sep.outputs['Red'], bsdf.inputs['Metallic'])
            inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
            L.new(n.outputs['Alpha'], inv.inputs[1]); L.new(inv.outputs['Value'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Metallic'].default_value = spec.get('metallic', 0.0)
        bsdf.inputs['Roughness'].default_value = 1 - spec.get('smoothness', 0.5)
    if spec.get('emissionColor'):
        ec = spec['emissionColor']; ei = spec.get('emissionIntensity', 1.0)
        bsdf.inputs['Emission Color'].default_value = (*[c ** 2.2 for c in ec], 1)
        bsdf.inputs['Emission Strength'].default_value = ei
        if spec.get('emission'):
            e = tex(spec['emission'], True)
            if e:
                mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
                L.new(e.outputs['Color'], mul.inputs['A']); mul.inputs['B'].default_value = (*[c ** 2.2 for c in ec], 1)
                L.new(mul.outputs['Result'], bsdf.inputs['Emission Color'])
    if 'opacity' in spec:
        bsdf.inputs['Alpha'].default_value = spec['opacity']; m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
        if d:   # URP multiplies the base map's alpha in (see-through with a texture: the emissive bands' opacity map)
            mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = spec['opacity']
            L.new(d.outputs['Alpha'], mul.inputs[0]); L.new(mul.outputs['Value'], bsdf.inputs['Alpha'])
    if spec.get('alphaClip') and d:
        L.new(d.outputs['Alpha'], bsdf.inputs['Alpha'])
    return m


specs = room.get('materials', [])
made = {s['material']: make(s) for s in specs}
unmatched = set()
for o in bpy.context.scene.objects:
    if o.type != 'MESH': continue
    for slot in o.material_slots:
        cur = slot.material.name if slot.material else ''
        hit = next((made[k] for k in made if k.lower() in cur.lower()), None)
        if hit: slot.material = hit
        else: unmatched.add(cur)
print('materials', len(specs), 'unmatched', sorted(unmatched))

mk = room['markers']
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
bpy.context.scene.collection.objects.link(cam)
if cam_name == 'top':
    # 'top' <x> <z> <size> <cut height> (Unity room metres): an orthographic plan view, everything above the cut left out
    x, z, size, cut = (float(v) for v in argv[4:8])
    cam.location = B([x, cut + 400.0, z]); cam.rotation_euler = (0, 0, 0)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = size; cam.data.clip_start = 400.0; cam.data.clip_end = 2000.0
    for name, p in mk.items():   # the markers as small red balls
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size / 160, location=B(p))
        o = bpy.context.object; m = bpy.data.materials.new('mk'); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 0, 0, 1)
        m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 20; o.data.materials.append(m)
        print('marker', name, [round(v) for v in p])
else:
    for name, p in mk.items():   # the visitors as red posts of a figure's height (2.2 m in the room's own metres)
        if not name.startswith('visitor'): continue
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5 * S, depth=2.2 * S, location=B(p) + Vector((0, 0, 1.1 * S)))
        o = bpy.context.object; m = bpy.data.materials.new('vis'); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 0, 0, 1)
        m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 8; o.data.materials.append(m)
    cam.location = B(mk[cam_name])
    d = B(mk[tgt_name]) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = math.radians(room.get('fov', 46))
    cam.data.clip_start = 0.5; cam.data.clip_end = room.get('far', 4000)
bpy.context.scene.camera = cam

if 'light' in mk:
    ld = bpy.data.lights.new('key', 'SUN'); ld.energy = 2.5 * room.get('lightIntensity', 1.0)
    lo = bpy.data.objects.new('key', ld); bpy.context.scene.collection.objects.link(lo)
    lo.rotation_euler = (B(mk.get(tgt_name, mk['camera_target'])) - B(mk['light'])).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new('w'); bpy.context.scene.world = w; w.use_nodes = True
a = room.get('ambient', [0.3, 0.3, 0.3])
w.node_tree.nodes['Background'].inputs['Color'].default_value = (*a, 1)

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('rendered', out)
