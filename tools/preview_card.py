# The mod's preview card (preview.png, 1280 x 720): the Dreadnought in front of a nebula, a few warships, freighters and the
# Mobile Homebase behind it, four of the player ships in front, a strip of item icons along the bottom and the title. The
# models come from the Blender renders (preview_blender.py for the kit ships, preview_model_blender.py for the single-model
# ones); the sky is the remake's own (Assets/Resources/GoF2Sky, with --remake), else a dark gradient.
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

W, H = 1280, 720
# The single-model renders: id, the camera's direction in the model's frame (preview_model_blender.py), render size.
MODEL_SHOTS = [("es2_dreadnought", "1,-0.7,0.25", 2048), ("es2_homebase", "1,0.9,0.4", 1024),
               ("es2_okkar_corvette", "1,0.8,0.35", 1024), ("es2_cultist_battleship", "1,-0.8,0.3", 1024),
               ("es2_gb_freighter", "1,-0.8,0.3", 1024)]
# Where each goes on the card: id, centre x, y, width, brightness, haze (distance), mirrored. Back to front.
LAYOUT = [("es2_homebase", 175, 215, 230, 0.9, 0.3, False),
          ("es2_cultist_battleship", 1130, 175, 250, 0.9, 0.25, False),
          ("es2_okkar_corvette", 395, 345, 250, 0.85, 0.15, True),
          ("es2_gb_freighter", 1115, 400, 190, 0.75, 0.2, False),
          ("es2_dreadnought", 790, 300, 700, 1.05, 0.0, False),
          ("wraith", 215, 500, 230, 1.15, 0.0, False),
          ("sentinel", 470, 545, 230, 1.15, 0.0, False),
          ("gunship", 1040, 545, 250, 1.15, 0.0, False),
          ("striker", 785, 560, 160, 1.15, 0.0, False)]
ICONS = ["autocannon_okkar", "beamlaser_charged", "blaster_eclipse", "coilgun_judge", "cryolance", "chargeorb",
         "missile_defense_system", "static_overload", "phalanx", "cloak_field_generator", "energy_shield", "combat_drone"]


def font(size, bold=True):
    for n in ((("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf") if bold else ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf"))):
        try: return ImageFont.truetype(n, size)
        except OSError: pass
    return ImageFont.load_default()


def background(sky):
    """The red nebula (the game's nebula_005, its second face, turned) with a star layer; a gradient without the sky."""
    def face(name, i):
        return Image.open(os.path.join(sky, name + ".png")).crop((i * 2048, 0, (i + 1) * 2048, 2048))
    if sky and os.path.exists(os.path.join(sky, "nebula_005.png")) and os.path.exists(os.path.join(sky, "stars_000.png")):
        neb = face("nebula_005", 1).rotate(-20, resample=Image.BICUBIC).crop((180, 470, 1780, 1370)).resize((W, H), Image.LANCZOS)
        neb = ImageEnhance.Brightness(neb).enhance(0.85)
        stars = face("stars_000", 4).crop((0, 0, 2048, 1152)).resize((W, H), Image.LANCZOS)
        return ImageChops.add(neb, ImageEnhance.Brightness(stars).enhance(1.4)).convert("RGBA")
    bg = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(bg)
    for y in range(H): d.line([(0, y), (W, y)], fill=(14 + y * 30 // H, 12 + y * 8 // H, 22, 255))
    return bg


def compose(mod, renders, sky, out):
    """'renders': a folder with <id>.png of every model in LAYOUT (a missing one is left out). Returns what it drew."""
    bg = background(sky)

    def place(path, cx, cy, width, bright, haze, flip):
        im = Image.open(path).convert("RGBA"); box = im.getbbox()
        if not box: return False
        im = im.crop(box)
        if bright != 1.0:
            rgb = ImageEnhance.Brightness(im.convert("RGB")).enhance(bright).convert("RGBA"); rgb.putalpha(im.getchannel("A")); im = rgb
        if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        k = width / im.width; im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        if haze:   # far away: toward the nebula's colour, a little see-through
            a = im.getchannel("A")
            im = Image.blend(im, Image.new("RGBA", im.size, (90, 40, 40, 255)), haze); im.putalpha(a.point(lambda v: int(v * (1 - haze * 0.5))))
        # a soft warm halo so the dark hulls stand off the sky
        glow = Image.new("RGBA", im.size, (255, 150, 110, 0))
        glow.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.25)))
        at = (round(cx - im.width / 2), round(cy - im.height / 2))
        bg.alpha_composite(glow, at); bg.alpha_composite(im, at)
        return True

    drawn = [sid for sid, *p in LAYOUT if os.path.exists(os.path.join(renders, sid + ".png")) and place(os.path.join(renders, sid + ".png"), *p)]
    # the item icons along the bottom
    strip = Image.new("RGBA", (W, 74), (8, 10, 18, 205)); bg.alpha_composite(strip, (0, H - 74))
    shown = [n for n in ICONS if os.path.exists(os.path.join(mod, "icons", "items", n + ".png"))]
    iw, ih = 98, 48; gap = (W - len(shown) * iw) / (len(shown) + 1)
    for i, n in enumerate(shown):
        ic = Image.open(os.path.join(mod, "icons", "items", n + ".png")).convert("RGBA").resize((iw, ih), Image.LANCZOS)
        bg.alpha_composite(ic, (round(gap + i * (iw + gap)), H - 74 + 13))
    # the title over a shade at the top
    shade = Image.new("RGBA", (W, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    for y in range(130): sd.line([(0, y), (W, y)], fill=(5, 6, 12, int(190 * (1 - y / 130) ** 1.5)))
    bg.alpha_composite(shade, (0, 0))
    d = ImageDraw.Draw(bg)
    d.text((28, 16), "EVERSPACE 2", font=font(52), fill=(245, 246, 250))
    d.text((32, 78), "10 customizable ships  ·  warships & freighters  ·  the Dreadnought raids", font=font(19, False), fill=(225, 200, 190))
    d.text((32, 102), "ES2's weapons, devices & consumables  ·  the Mobile Homebase", font=font(19, False), fill=(225, 200, 190))
    bg.convert("RGB").save(out, optimize=True)
    return drawn, len(shown)
