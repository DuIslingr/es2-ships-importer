# Run by import.py (--mobile) inside Blender: decimates every part GLB of the mod for phones (keeps the material names, so the kit's
# materials and colour slots still find them). blender -b -P decimate_blender.py -- <src parts> <dst parts> <ratio> <min tris>
import bpy, os, sys
args = sys.argv[sys.argv.index('--') + 1:]
src, dst, ratio, keep_below = args[0], args[1], float(args[2]), int(args[3])
os.makedirs(dst, exist_ok=True)
files = sorted(f for f in os.listdir(src) if f.endswith('.glb'))
before = after = 0
for i, f in enumerate(files):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(src, f))
    for ob in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        before += tris
        if tris > keep_below:
            m = ob.modifiers.new('decimate', 'DECIMATE')
            m.decimate_type = 'COLLAPSE'
            m.ratio = max(ratio, keep_below / tris)
            m.use_collapse_triangulate = True
            # The engine flames' cards (M_Vehicle_EngineExhaust, a few quads each) stay whole: collapsed, they vanish.
            flame = [i for i, mat in enumerate(ob.data.materials) if mat and 'EngineExhaust' in mat.name]
            if flame:
                keep = ob.vertex_groups.new(name='flame')
                keep.add(sorted({v for poly in ob.data.polygons if poly.material_index in flame for v in poly.vertices}), 1.0, 'REPLACE')
                m.vertex_group = keep.name
                m.invert_vertex_group = True
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=m.name)
            # The imported custom normals don't survive the collapse: smooth by angle like the hard-surface originals.
            bpy.ops.object.shade_smooth_by_angle(angle=0.6)
        after += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    bpy.ops.export_scene.gltf(filepath=os.path.join(dst, f), export_format='GLB', export_tangents=True, export_normals=True,
                              export_texcoords=True, export_vertex_color='NONE', export_materials='EXPORT', export_image_format='NONE',
                              export_apply=True, export_yup=True)
    if i % 20 == 0: print(f'decimate: {i + 1}/{len(files)}', flush=True)
print(f'decimate: done, {before} -> {after} triangles', flush=True)
