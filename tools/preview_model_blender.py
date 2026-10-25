# Blender script: renders of a built es2_ships mod's single-model ships and stations (the warships, freighters, the
# Dreadnought, the Mobile Homebase) for the mod's preview image, each with its ships.json / stations.json materials (the
# maps times the colour, normal, metallic / smoothness, emission, tiling, alpha clip) as the remake shows them.
# blender -b --factory-startup -P preview_model_blender.py -- <mod folder> <output folder> <id>:<from x,y,z>[:<size>] ...
# <from> is the direction the camera looks from in the ship's own frame (Blender axes: nose +X, left +Y, up +Z); <size> the
# render's width (square, default 1024). Writes <output>/<id>.png (transparent).
import bpy, bmesh, sys, os, json, math, mathutils

args = sys.argv[sys.argv.index("--") + 1:]
mod, out, jobs = args[0], args[1], args[2:]
entries = {e["id"]: e for e in json.load(open(os.path.join(mod, "ships.json"), encoding='utf-8-sig'))}
entries.update({e["id"]: e for e in json.load(open(os.path.join(mod, "stations.json"), encoding='utf-8-sig'))})

images = {}
def image(path, colour=True):
    p = os.path.join(mod, path)
    if p not in images:
        images[p] = bpy.data.images.load(p) if os.path.exists(p) else None
        if images[p] is not None and not colour: images[p].colorspace_settings.name = "Non-Color"
    return images[p]


def tex_node(nt, path, tiling, colour=True):
    im = image(path, colour)
    if im is None: return None
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = im
    if tiling and tiling != 1:
        uv = nt.nodes.new("ShaderNodeTexCoord"); m = nt.nodes.new("ShaderNodeMapping")
        m.inputs["Scale"].default_value = (tiling, tiling, 1)
        nt.links.new(uv.outputs["UV"], m.inputs["Vector"]); nt.links.new(m.outputs["Vector"], t.inputs["Vector"])
    return t


def setup(mat, specs):
    name = mat.name.lower()
    spec = next((s for s in specs if s.get("material") and s["material"].lower().rstrip("|") in name), None)
    if spec is None: return
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None: return
    for l in list(nt.links):
        if l.to_node == bsdf: nt.links.remove(l)
    tiling = spec.get("tiling", 1)
    if spec.get("opacity") and spec.get("diffuse", "").endswith("clear.png"):
        # additive (the light cards, the band glows): the emission over what is behind, nothing of its own
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        add = nt.nodes.new("ShaderNodeAddShader"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); em = nt.nodes.new("ShaderNodeEmission")
        e = spec.get("emissionColor", [1, 1, 1]); em.inputs["Strength"].default_value = spec.get("emissionIntensity", 1) * 4
        t = tex_node(nt, spec["emission"], tiling) if spec.get("emission") else None
        if t is not None:
            mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
            nt.links.new(t.outputs["Color"], mul.inputs[6]); mul.inputs[7].default_value = (*e[:3], 1)
            nt.links.new(mul.outputs[2], em.inputs["Color"])
        else:
            em.inputs["Color"].default_value = (*e[:3], 1)
        nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs["Surface"])
        if hasattr(mat, "surface_render_method"): mat.surface_render_method = "BLENDED"
        return
    col = list(spec.get("color", [1, 1, 1]))[:3]
    d = tex_node(nt, spec["diffuse"], tiling) if spec.get("diffuse") else None
    if d is not None:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(d.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = (*col, 1)
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        if spec.get("alphaClip"):
            nt.links.new(d.outputs["Alpha"], bsdf.inputs["Alpha"])
            if hasattr(mat, "blend_method"): mat.blend_method = "CLIP"
    else:
        bsdf.inputs["Base Color"].default_value = (*col, 1)
    ms = tex_node(nt, spec["metallicSmoothness"], tiling, False) if spec.get("metallicSmoothness") else None
    if ms is not None:   # Unity's layout: R metallic, A smoothness
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(ms.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(ms.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.3)
        bsdf.inputs["Roughness"].default_value = 1 - spec.get("smoothness", 0.4)
    n = tex_node(nt, spec["normal"], tiling, False) if spec.get("normal") else None
    if n is not None:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if spec.get("emission") or spec.get("emissionColor"):
        e = spec.get("emissionColor", [1, 1, 1]); k = spec.get("emissionIntensity", 1) * 4
        bsdf.inputs["Emission Color"].default_value = (*e[:3], 1)
        bsdf.inputs["Emission Strength"].default_value = k
        em = tex_node(nt, spec["emission"], tiling) if spec.get("emission") else None
        if em is not None:
            mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            nt.links.new(em.outputs["Color"], mul.inputs[6]); mul.inputs[7].default_value = (*e[:3], 1)
            nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])


for job in jobs:
    bits = job.split(":")
    sid = bits[0]; frm = mathutils.Vector([float(v) for v in bits[1].split(",")]).normalized()
    size = int(bits[2]) if len(bits) > 2 else 1024
    e = entries[sid]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    images.clear()
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=os.path.join(mod, e["model"]))
    for mat in bpy.data.materials: setup(mat, e.get("materials", []))
    meshes = [o for o in sc.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ mathutils.Vector(c) for o in meshes if len(o.data.vertices) for c in o.bound_box]
    lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; r = (hi - lo).length / 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 50; cam.data.clip_start = r * 0.01; cam.data.clip_end = r * 20
    cam.location = c + frm * r * 3.2
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    for i, (v, en) in enumerate([((0.5, -0.5, 1.0), 9.0), ((-0.9, 0.6, 0.2), 3.0), ((0.3, 0.9, -0.5), 1.5)]):
        l = bpy.data.objects.new(f"s{i}", bpy.data.lights.new(f"s{i}", "SUN")); l.data.energy = en; sc.collection.objects.link(l)
        l.rotation_euler = mathutils.Vector(v).to_track_quat("Z", "Y").to_euler()
    w = bpy.data.worlds.new("w"); sc.world = w; w.color = (0.35, 0.37, 0.42)
    eng = [x.identifier for x in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in eng else "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.view_settings.exposure = 1.3   # (the hulls are dark metal: lifted for a picture on a dark card)
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = os.path.join(out, sid + ".png")
    bpy.ops.render.render(write_still=True)
    print("preview:", sid, flush=True)
