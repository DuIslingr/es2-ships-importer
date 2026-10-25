"""The items' shop icons in Galaxy on Fire 2's style (items.json "icon"), made from EVERSPACE 2's own item icons
(UI/Images/Items, exported from the player's copy of the game: never shipped with this importer).

A GoF2 shop icon (ImageFactory::drawItem) is 180 x 88: the item drawn over a striped plate tinted by the item's type (red
primary weapons, orange secondaries, yellow turrets, green equipment, grey goods; the game's images 1274 / 1275 / 1271 /
1272 / 1273), the object large and glossy, a gun lying with its muzzle to the left and its back a little up. EVERSPACE 2's
icons are square paintings (172 x 172) of the same kind of object, so:
  - a painted icon is cut to its pixels, turned so its long axis lies like GoF2's guns (its muzzle, the upper left end in
    ES2's drawings, to the left; round things as drawn), its contrast and colour lifted a little toward GoF2's rendered look,
    sharpened, fitted to the plate with a soft drop shadow;
  - a flat white symbol (most of ES2's devices: no colour, bright) becomes an embossed steel emblem with a glow in the
    plate's colour, lit from the upper left like GoF2's renders, since a white glyph on GoF2's plate reads as a hole;
  - items sharing one ES2 icon (the pulse laser's variants, the DLC weapons without one of their own) get its glowing parts
    turned to their own projectile colour, as GoF2 does with the three Micro Guns' icons.
The plates come from a checkout of the remake (its gof2_interface2_ipad_large.png atlas) when given, else drawn stand-ins."""
import colorsys, math, os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

W, H = 178, 86                      # the picture inside the 180 x 88 icon
ICONS = None                        # the folder of ES2's item icon PNGs
REMAKE_ATLAS = None
_frames = {}

# The plates in gof2_interface2_ipad_large.png (Reference/research/item_icons.json, the frame_* entries) and the colour each
# shows (measured on them: the brightest stripes), for the drawn stand-ins and the emblems' glow.
FRAMES = {'primary': (112, 1294), 'secondary': (112, 1382), 'turret': (112, 1653), 'equipment': (399, 1),
          'commodity': (1581, 1), 'ship': (1821, 1)}
TINTS = {'primary': (1.0, 0.26, 0.26), 'secondary': (1.0, 0.63, 0.16), 'turret': (1.0, 0.95, 0.33),
         'equipment': (0.45, 1.0, 0.67), 'commodity': (1.0, 1.0, 1.0), 'ship': (0.0, 0.66, 1.0)}


def configure(icons, remake=None):
    """icons: the folder of ES2's item icons (FModel's export of UI/Images/Items as PNG); remake: a checkout of the remake
    (or its gof2_interface2_ipad_large.png) for the game's own plates."""
    global ICONS, REMAKE_ATLAS
    ICONS = icons if icons and os.path.isdir(icons) else None
    REMAKE_ATLAS = None
    if remake:
        p = os.path.expanduser(remake)
        if os.path.isdir(p): p = os.path.join(p, 'Assets', 'Textures', 'textures', 'gof2_interface2_ipad_large.png')
        if os.path.exists(p): REMAKE_ATLAS = p
    _frames.clear()


def available():
    return ICONS is not None


def has(name):
    return ICONS is not None and name is not None and os.path.exists(os.path.join(ICONS, name + '.png'))


# ---- the plates --------------------------------------------------------------------------------------------------------

def drawn_frame(kind='ship'):
    """A stand-in for the game's plate drawn to its measurements: a dark plate with corners rounded 9 px, scanlines 2 rows
    bright / 2 at 70 %, narrow brighter diagonal bands every 48 px leaning right, in the type's colour, brightest in the
    middle and fading to black at both ends."""
    w, h = W, H
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    band = ((x + 0.55 * y) % 48.0) < 21.0                                # the brighter diagonal bands
    scan = np.where((y.astype(int) // 2) % 2 == 0, 1.0, 0.7)            # the scanlines
    env = np.sin(np.pi * np.clip((x + 0.5) / w, 0, 1)) ** 1.1           # dark at both ends
    level = 0.34 * env * np.where(band, 1.0, 0.62) * scan               # (over black: up to ~80 / 255)
    alpha = np.where(band, 0.38, 0.45)
    pm = level[..., None] * np.array(TINTS[kind], np.float32)           # the colour as it shows over black
    r = 9.0                                                              # rounded corners
    cx, cy = np.clip(x, r, w - 1 - r), np.clip(y, r, h - 1 - r)
    alpha = alpha * np.clip(r + 0.5 - np.hypot(x - cx, y - cy), 0, 1)
    rgb = np.where(alpha[..., None] > 0, pm / np.maximum(alpha[..., None], 1e-3), 0)
    img = np.dstack([np.clip(rgb * 255, 0, 255), alpha * 255]).astype(np.uint8)
    out = Image.new('RGBA', (180, 88), (0, 0, 0, 0)); out.alpha_composite(Image.fromarray(img, 'RGBA'), (1, 1))
    return out


def frame(kind):
    """The 180 x 88 plate of an item type: the game's own from the remake's atlas, else a drawn one."""
    if kind not in _frames:
        out = None
        if REMAKE_ATLAS:
            a = Image.open(REMAKE_ATLAS).convert('RGBA')
            x, y = FRAMES[kind]
            out = Image.new('RGBA', (180, 88), (0, 0, 0, 0)); out.alpha_composite(a.crop((x, y, x + W, y + H)), (1, 1))
        _frames[kind] = out or drawn_frame(kind)
    return _frames[kind].copy()


def frame_kind():
    return 'the game\'s plates' if REMAKE_ATLAS else 'drawn plates'


# ---- the picture -------------------------------------------------------------------------------------------------------

def _crop(im):
    b = im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
    return im.crop(b) if b else im


def _fit(im, w, h):
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def is_symbol(im):
    """A flat symbol (ES2's device icons: white, no colour) rather than a painted object."""
    a = np.asarray(im).astype(np.float32) / 255
    m = a[..., 3] > 0.5
    if m.sum() < 20: return False
    rgb = a[..., :3][m]
    mx, mn = rgb.max(1), rgb.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-3), 0)
    return sat.mean() < 0.05 and mx.mean() > 0.8


def _orient(im):
    """Turns a long object so it lies like GoF2's guns: the long axis 12 deg up to the right, the end that was upper left in
    ES2's drawing (the muzzle, a missile's tip) on the left. Round things stay as drawn."""
    a = np.asarray(im)[..., 3].astype(np.float32)
    ys, xs = np.nonzero(a > 40)
    if len(xs) < 10: return im
    w = a[ys, xs]
    cx, cy = (xs * w).sum() / w.sum(), (ys * w).sum() / w.sum()
    ev, evec = np.linalg.eigh(np.cov(np.stack([xs - cx, ys - cy]), aweights=w))
    if ev[1] < 2.2 * ev[0]: return im
    d = evec[:, 1]
    if d[0] + d[1] < 0: d = -d                               # from the upper left end to the other
    angle = math.degrees(math.atan2(d[1], d[0]))             # (image y down)
    return im.rotate(angle + 12.0, resample=Image.BICUBIC, expand=True)


def _painted(im):
    # (ES2's faint drop shadows and haze, under 40 / 255, go: they'd count as the object when it is cut and fitted, and
    # the icon gets a shadow of its own)
    a = im.getchannel('A').point(lambda v: 0 if v < 40 else v)
    im = im.copy(); im.putalpha(a)
    im = _crop(_orient(_crop(im)))
    rgb, a = im.convert('RGB'), im.getchannel('A')
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Color(rgb).enhance(1.18)
    rgb = rgb.filter(ImageFilter.UnsharpMask(1.2, 60, 2))
    out = rgb.convert('RGBA'); out.putalpha(a)
    return out


def _gray(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def _emblem(im, tint):
    """A white symbol as an embossed steel emblem: its brightness x alpha a height, lit from the upper left, a steel colour
    brighter at the top, its rims and a glow around it in the plate's colour."""
    im = _crop(im)
    px = np.asarray(im).astype(np.float32) / 255
    mask = px[..., 3] * px[..., :3].max(2)                   # (dark strokes inside a symbol are cut into it)
    s = 192.0 / max(mask.shape)                              # drawn at twice the size, then halved
    big = _gray(mask).resize((max(1, round(mask.shape[1] * s)), max(1, round(mask.shape[0] * s))), Image.LANCZOS)
    A = np.pad(np.asarray(big).astype(np.float32) / 255, 24)
    h = np.asarray(_gray(A).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * 6, -gy * 6, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array([-0.5, -0.65, 0.58]); L /= np.linalg.norm(L)
    diffuse = np.clip((n * L).sum(2), 0, 1)
    half = L + np.array([0, 0, 1.0]); half /= np.linalg.norm(half)
    spec = np.clip((n * half).sum(2), 0, 1) ** 24
    t = np.array(tint, np.float32)
    steel = np.array([0.80, 0.84, 0.88]) * np.linspace(1.1, 0.75, A.shape[0])[:, None, None]
    col = steel * (0.35 + 0.75 * diffuse[..., None]) + spec[..., None] * 0.9
    inner = np.asarray(_gray(A).filter(ImageFilter.MinFilter(5))).astype(np.float32) / 255
    edge = np.clip(A - inner, 0, 1)[..., None]
    col = col * (1 - 0.35 * edge) + t * 0.35 * edge
    glow = np.asarray(_gray(A).filter(ImageFilter.GaussianBlur(9))).astype(np.float32) / 255
    ga = np.clip(glow * 1.6, 0, 1) * 0.85 * (1 - A)
    out_a = A + ga * (1 - A)
    out_c = (col * A[..., None] + t * ga[..., None]) / np.maximum(out_a[..., None], 1e-4)
    img = np.dstack([np.clip(out_c, 0, 1) * 255, out_a * 255]).astype(np.uint8)
    return _crop(Image.fromarray(img, 'RGBA').resize((img.shape[1] // 2, img.shape[0] // 2), Image.LANCZOS))


def _hex(c):
    if isinstance(c, str):
        c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        return tuple(v / 255 if max(c[:3]) > 1 else v for v in c[:3])
    return None


def recolour(im, colour):
    """The icon's glowing parts (bright and saturated) turned to the colour's hue, keeping their brightness; the metal stays.
    Returns the image unchanged when its glow is already near that hue."""
    rgb = _hex(colour)
    if not rgb: return im
    target_h, target_s, _ = colorsys.rgb_to_hsv(*rgb)
    if target_s < 0.15: return im
    a = np.asarray(im.convert('RGBA')).astype(np.float32) / 255
    c = a[..., :3]
    mx, mn = c.max(2), c.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-3), 0)
    glow = np.clip((sat - 0.3) / 0.3, 0, 1) * np.clip((mx - 0.35) / 0.3, 0, 1)
    if glow.sum() < 30: return im
    # the hue now (where it glows): a circular mean
    hsv = np.asarray(im.convert('RGB').convert('HSV')).astype(np.float32) / 255
    ang = hsv[..., 0] * 2 * math.pi
    now = math.atan2((np.sin(ang) * glow).sum(), (np.cos(ang) * glow).sum()) / (2 * math.pi) % 1
    if min(abs(now - target_h), 1 - abs(now - target_h)) < 0.07: return im
    new_h = (hsv[..., 0] + (target_h - now)) % 1
    hsv2 = hsv.copy(); hsv2[..., 0] = new_h
    hsv2[..., 1] = np.maximum(hsv[..., 1], target_s * glow)
    turned = np.asarray(Image.fromarray((hsv2 * 255).astype(np.uint8), 'HSV').convert('RGB')).astype(np.float32) / 255
    out = c * (1 - glow[..., None]) + turned * glow[..., None]
    return Image.fromarray(np.dstack([out * 255, a[..., 3] * 255]).astype(np.uint8), 'RGBA')


def make(name, kind, colour=None):
    """The 180 x 88 icon of ES2's icon 'name' on the 'kind' plate (its glow turned to 'colour' when given), or None."""
    if not has(name): return None
    src = Image.open(os.path.join(ICONS, name + '.png')).convert('RGBA')
    icon = frame(kind)
    if is_symbol(src):
        im = _fit(_emblem(src, TINTS[kind]), W * 0.94, H * 0.96)
    else:
        if colour: src = recolour(src, colour)
        im = _fit(_painted(src), W * 0.92, H * 0.92)
        x, y = 1 + (W - im.width) // 2, 1 + (H - im.height) // 2
        shade = im.getchannel('A').filter(ImageFilter.GaussianBlur(2.5)).point(lambda v: int(v * 0.6))
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(shade)
        icon.alpha_composite(sh, (x + 2, y + 3))
    icon.alpha_composite(im, (1 + (W - im.width) // 2, 1 + (H - im.height) // 2))
    return icon


def apply(items, mod, folder='icons/items'):
    """Gives each item with '_icon' (ES2's icon name), '_frame' (the plate) and optionally '_recolour' (a colour for a shared
    icon) its icon file and items.json "icon". Returns how many were made."""
    if not available(): return 0
    os.makedirs(os.path.join(mod, folder), exist_ok=True)
    made = 0
    for it in items:
        icon = make(it.get('_icon'), it.get('_frame', 'equipment'), it.get('_recolour'))
        if icon is None: continue
        rel = f"{folder}/{it['id']}.png"
        icon.save(os.path.join(mod, rel), optimize=True)
        it['icon'] = rel; made += 1
    return made


def share(items):
    """Marks every item but the first (the shortest id: the family's plain weapon) of each shared icon to be recoloured to
    its projectile colour."""
    by = {}
    for it in items:
        if it.get('_icon'): by.setdefault(it['_icon'], []).append(it)
    for group in by.values():
        group.sort(key=lambda i: (not i.get('_own_icon', True), len(i['id']), i['id']))
        for it in group[1:]:
            c = ((it.get('fx') or {}).get('projectile') or {}).get('color')
            if c: it['_recolour'] = c
