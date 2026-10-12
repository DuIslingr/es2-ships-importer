# Blender script: one render per ship of a built es2_ships mod, for the mod's preview image (import.py makes the card), or
# with "icon" for the ships' shop icons (import.py puts them on the ship frame).
# blender -b --factory-startup -P preview_blender.py -- <mod folder> <output folder> [icon]
# Each ship's default build as the remake assembles it: the build's parts (and the tier's extensions) from shipkits.json, a
# part with an "anchor" moved to that point of the part offering it, the kit's materials (their maps) and the build's colours
# on the materials the colour slots name; the engine flames, boost cards, manoeuvring jets and holograms left out (they only
# show in flight). Writes <output>/<ship id>.png (transparent, 720 x 720).
import bpy, bmesh, sys, os, json, math, mathutils

args = sys.argv[sys.argv.index("--") + 1:]
mod, out = args[0], args[1]
ICON = len(args) > 2 and args[2] == "icon"
# The shop icons follow the game's own (HullIconBuilder): the ship seen from its left side, above and a little ahead (Unity
# (-1, 0.55, 0.3) with the model facing +Z; here nose +X, left +Y), turned 15 deg so the nose dips to the bottom left,
# 178 x 86 at four times the size (import.py fits the drawn pixels with a 4 % margin).
ICON_FROM = (0.3, 1.0, 0.55)
ICON_ROLL = -15.0
ICON_W, ICON_H = 178 * 4, 86 * 4
kits = {k["id"]: k for k in json.load(open(os.path.join(mod, "shipkits.json"), encoding='utf-8-sig'))}
ships = json.load(open(os.path.join(mod, "ships.json"), encoding='utf-8-sig'))
HIDE = ("lateral thruster", "boostvent")   # material names never shown parked


def gl(v):   # glTF (x, y, z) -> Blender (x, -z, y)
    return mathutils.Vector((v[0], -v[2], v[1]))


def hex_value(text):
    """'#RRGGBB[/metallic/smoothness]' -> (rgb linear, metallic or None, smoothness or None)."""
    if not text or not text.startswith("#"): return None
    bits = text.split("/")
    h = bits[0].lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    metal = float(bits[1]) if len(bits) > 1 else None
    smooth = float(bits[2]) if len(bits) > 2 else None
    return lin, metal, smooth


def resolve(kit, slot, value):
    if value is None: return None
    if value.startswith("#"): return hex_value(value)
    for c in kit.get("palettes", {}).get(slot.get("palette", ""), []):
        if c["id"].lower() == value.lower():
            r = hex_value(c["color"])
            if r: return r[0], c.get("metallic", r[1]), c.get("smoothness", r[2])
    return None


images = {}
def image(path):
    p = os.path.join(mod, path)
    if p not in images:
        images[p] = bpy.data.images.load(p) if os.path.exists(p) else None
    return images[p]


def setup_material(mat, kit, colors):
    name = mat.name.lower()
    spec = next((m for m in kit.get("materials", []) if m.get("material") and m["material"].lower() in name), None)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None: return
    base = list(bsdf.inputs["Base Color"].default_value)
    tex = None
    if spec:
        if spec.get("diffuse") and image(spec["diffuse"]):
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = image(spec["diffuse"])
        if spec.get("color"): base = list(spec["color"][:3]) + [1]
        if spec.get("emissionColor"):
            e = spec["emissionColor"]; k = min(spec.get("emissionIntensity", 1), 3)
            bsdf.inputs["Emission Color"].default_value = (e[0], e[1], e[2], 1); bsdf.inputs["Emission Strength"].default_value = k
    metal = smooth = None
    for slot in kit.get("colorSlots", []):
        if slot.get("steps"): continue
        for t in slot.get("targets", []):
            m = t.get("material")
            if not m or m.lower() not in name: continue
            r = resolve(kit, slot, colors.get(slot["id"], slot.get("default")))
            if not r: continue
            prop = t.get("property", "base")
            if prop == "emission":
                bsdf.inputs["Emission Color"].default_value = (*r[0], 1)
                bsdf.inputs["Emission Strength"].default_value = min(t.get("intensity", 1), 3)
            elif prop == "base":
                base = [c * t.get("intensity", 1) for c in r[0]] + [1]
                metal, smooth = r[1], r[2]
    if tex is not None:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = base
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = base
    if metal is not None: bsdf.inputs["Metallic"].default_value = metal
    if smooth is not None: bsdf.inputs["Roughness"].default_value = 1 - smooth


def hidden(mat, kit):
    name = mat.name.lower()
    if any(h in name for h in HIDE): return True
    spec = next((m for m in kit.get("materials", []) if m.get("material") and m["material"].lower() in name), None)
    return bool(spec and (spec.get("flame") or spec.get("hologram") or spec.get("shimmer") or spec.get("boost")))


def import_part(path, offset):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(mod, path))
    for o in set(bpy.data.objects) - before:
        if o.parent is None: o.location += offset


for ship in ships:
    kit = kits.get(ship.get("kit", "").split(":")[-1])
    if kit is None: continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    images.clear()
    sc = bpy.context.scene
    build = ship.get("build", {}); tier = build.get("tier", 0)
    parts = {p["id"]: p for p in kit["parts"]}
    chosen = [parts[build[s]] for s in kit["slots"] if build.get(s) in parts]
    anchors = {}
    for p in chosen:
        for k, v in (p.get("anchors") or {}).items(): anchors[k] = gl(v)
    for p in chosen:
        off = anchors.get(p.get("anchor"), mathutils.Vector()) if p.get("anchor") else mathutils.Vector()
        import_part(p["model"], off)
        tiers = p.get("tiers") or []
        if 0 < tier <= len(tiers): import_part(tiers[tier - 1], off)
    colors = build.get("colors", {})
    for mat in bpy.data.materials: setup_material(mat, kit, colors)
    meshes = [o for o in sc.objects if o.type == "MESH"]
    for o in meshes:   # the parked ship: no flames, jets or holograms
        drop = [i for i, s in enumerate(o.material_slots) if s.material and hidden(s.material, kit)]
        if not drop: continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in drop], context="FACES")
        bm.to_mesh(o.data); bm.free()
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ mathutils.Vector(c) for o in meshes if len(o.data.vertices) for c in o.bound_box]
    if not pts: continue
    lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; r = (hi - lo).length / 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = r * 2.05; cam.data.clip_end = r * 10
    # Nose along +X (the kit's parts face glTF +X), its left +Y: from ahead-left and above, the nose toward the viewer's left.
    d = mathutils.Vector(ICON_FROM if ICON else (0.75, 1.0, 0.65)).normalized()
    cam.location = c + d * r * 4
    q = (c - cam.location).to_track_quat("-Z", "Y")
    if ICON:
        q = q @ mathutils.Quaternion((0, 0, 1), math.radians(ICON_ROLL))   # (about the view axis)
        cam.rotation_euler = q.to_euler()
        # Fitted to the bounding box's corners as the camera sees them (import.py tightens it to the drawn pixels).
        inv = q.to_matrix().inverted()
        xs = [(inv @ (p - c)).x for p in pts]; ys = [(inv @ (p - c)).y for p in pts]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        cam.location = cam.location + q @ mathutils.Vector((cx, cy, 0))
        cam.data.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * ICON_W / ICON_H) * 1.02
    else:
        cam.rotation_euler = q.to_euler()
    for i, (v, e) in enumerate([((0.6, -0.4, 1.0), 4.0), ((-0.8, 0.6, 0.3), 1.6), ((0.9, 0.3, -0.4), 1.0)]):
        l = bpy.data.objects.new(f"s{i}", bpy.data.lights.new(f"s{i}", "SUN")); l.data.energy = e; sc.collection.objects.link(l)
        l.rotation_euler = mathutils.Vector(v).to_track_quat("Z", "Y").to_euler()
    w = bpy.data.worlds.new("w"); sc.world = w; w.color = (0.35, 0.38, 0.45)
    eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in eng else "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = (ICON_W, ICON_H) if ICON else (720, 720)
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = os.path.join(out, ship["id"] + ".png")
    bpy.ops.render.render(write_still=True)
    print("preview:", ship["id"], flush=True)
