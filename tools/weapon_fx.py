"""EVERSPACE 2's weapon looks baked into the remake's weapon fx sprites (items.json "fx": "projectile" / "muzzle" / "impact"
with a "sprite"), after ES2's own effects: their Cascade emitters (es2_re cascade.py: each one's material, size, colour scale)
and their materials' compiled pixel shaders (es2_re fxmat, ShaderDump + disasm), recoded here in NumPy:

  glow       M_Particle_Glow_Unlit_001: d = max(1 - 2r, 0), g = d / ((1 - d) 8 + 1), g^Exponent (1.5), x (1 + 0.5 rays) x 2/3,
             its rays a texture turned round the centre (here a smooth noise of the angle)
  blaster    P_Projectile_Blaster_001: M_Projectile_Blaster_Parent's core (300 cm, x 50: a polar noise flicker, d^(8 - 8 n^0.1)
             through the contrast curve 8; T_Noise_013_M) inside a glow (3000 cm, x 2)
  body bolt  P_Projectile_Autocannon_001 / PulseLaser_001: SM_Projectile_001 / 002 with M_Projectile_Body_Parent (the
             particle colour x 20 x the mesh's gradient ^1.5, added): a streak bright toward its head
  slug       P_Projectile_CoilGun_001 / RailGun / GaussCannon_001 (beam emitters): across the beam p = 1 - |2v - 1|, the hot
             core p / ((1 - p) k + 1), k 98 (the coil's) or 18 (the gauss'), with a noise scrolling along it (T_Noise_013_M /
             T_Noise_001_M), fading at the beam's end
  beam       P_Projectile_BeamLaser_001: the same profile across the beam (x 50); the lightning gun's an arc wandering about
             the beam's centre (M_Projectile_LightningGun_Beam)
  muzzle     P_MuzzleFlash_Single_Base_001: a glow (2000 cm, x 5) and the side flame (MI_MuzzleFlash_Fire_Side, x 30: its shader
             not read, a four-point flash here); the beams' P_MuzzleFlash_Constant_Base_001 a larger glow (3000 cm)
  impact     P_Impact_Shield_001's glow (2000 cm); the beams' P_Impact_Constant_Sparks_001 (a glow, x 50, and black-body sparks in
             (1, 0.325, 0.1)); the lightning's arcs and glow; the flak's ring, star flash and glow (P_Impact_Flak_001)

ES2's light is HDR (a core 25 x its glow); a sprite holds 0-1, so each is tone-mapped (1 - exp(-I x colour)): the core white-
hot, the glow keeping the family's colour, the sprite's fx "glow" its brightness under the remake's bloom. The sizes are GoF2's
own bolts' (game units; the N'saan's bolt about 1600, its impact about 6300) at ES2's proportions between the parts."""
import math, os
import numpy as np
from PIL import Image

SRC = MOD = None
SIZE = 256
_made = {}
_noise_cache = {}


def configure(src, mod):
    global SRC, MOD
    SRC, MOD = src, mod


# ---- the shaders' pieces -------------------------------------------------------------------------------------------------

def _grid(w, h):
    """u, v in 0..1 across a w x h image (pixel centres), v 0 at the top."""
    v, u = np.mgrid[0:h, 0:w].astype(np.float32)
    return (u + 0.5) / w, (v + 0.5) / h


def _noise1(x, seed=0, octaves=3):
    """A smooth value noise of x (any shape), 0..1, periodic over 1 (64 cells): rays round a centre, flicker along a beam."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(x, dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = 16 * (2 ** o)
        vals = rng.random(n).astype(np.float32)
        t = (x % 1.0) * n
        i = np.floor(t).astype(int) % n
        f = t - np.floor(t)
        f = f * f * (3 - 2 * f)
        out += amp * (vals[i] * (1 - f) + vals[(i + 1) % n] * f)
        total += amp; amp *= 0.5
    return out / total


def _contrast(x, k):
    """ES2's contrast curve: 0.5 (2x)^k below a half, 1 - 0.5 (2 - 2x)^k above."""
    x = np.clip(x, 0, 1)
    return np.where(x < 0.5, 0.5 * (2 * x) ** k, 1 - 0.5 * (2 - 2 * x) ** k)


def hot(p, k):
    """The beams' and glows' hot profile: p / ((1 - p) k + 1)."""
    p = np.clip(p, 0, 1)
    return p / ((1 - p) * k + 1)


def glow(size=SIZE, exponent=1.5, rays=True, seed=1):
    """M_Particle_Glow_Unlit_001's intensity on a square sprite."""
    u, v = _grid(size, size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    g = hot(np.maximum(1 - 2 * r, 0), 8.0) ** exponent
    if rays:
        a = np.arctan2(y, x) / (2 * math.pi) + 0.5
        g = g * (1 + 0.5 * _noise1(a, seed)) * (2.0 / 3.0)
    return g


def blaster_core(size=SIZE, core_share=0.1, seed=2):
    """M_Projectile_Blaster_Parent's core at the sprite's middle (core_share of its width): d^(8 - 8 n^0.1), contrast 8."""
    u, v = _grid(size, size)
    x, y = (u - 0.5) / core_share, (v - 0.5) / core_share
    r = np.sqrt(x * x + y * y)
    d = np.maximum(1 - 2 * r, 0)
    a = np.arctan2(y, x) / (2 * math.pi) + 0.5
    n = np.maximum(_noise1(a * 2 + d * 0.5, seed), 1e-4)
    e = 8 - 8 * n ** 0.1
    return _contrast(np.where(d > 0, d ** e, 0), 8.0)


def streak(w=64, h=256, k=8.0, head=1.5, seed=3, noise=0.0):
    """A bolt along the sprite's height (head at the top): across it the hot profile, along it u^head (the body bolt's mesh
    gradient ^1.5; a slug's noise when 'noise'), soft at both ends."""
    u, v = _grid(w, h)
    along = 1 - v   # (1 at the head)
    p = 1 - np.abs(2 * u - 1)
    cross = hot(p, k)
    ends = np.clip(along / 0.08, 0, 1) * np.clip((1 - along) / 0.05, 0, 1)
    body = along ** head * ends
    if noise: body = body * (1 - noise + noise * _noise1(along * 3, seed))
    return cross * body


def beam(w=128, h=32, k=18.0, halo=0.35):
    """A beam laser's cross-section on a sprite running along its height (the remake fits it one game unit along the beam):
    the hot core plus a soft halo, the same down its length."""
    u, v = _grid(w, h)
    p = 1 - np.abs(2 * u - 1)
    return hot(p, k) + halo * hot(p, 1.5) ** 2


def lightning(w=128, h=512, seed=4):
    """The lightning gun's arc: a thin hot line wandering about the beam's centre, with a faint glow round it."""
    u, v = _grid(w, h)
    centre = 0.5 + (_noise1(v * 0.35, seed, 3) - 0.5) * 0.5
    dist = np.abs(u - centre)
    return hot(np.clip(1 - dist / 0.05, 0, 1), 6.0) + 0.15 * hot(np.clip(1 - dist / 0.15, 0, 1), 2.0)


def star(size=SIZE, points=4, sharp=60.0, seed=5):
    """A flash's rays (the side flame's stand-in, M_Particle_StarFlash's barcode rays): |cos(points/2 theta)|^sharp, falling
    off with the radius."""
    u, v = _grid(size, size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y) * 2
    a = np.arctan2(y, x)
    rays = np.abs(np.cos(a * points / 2.0)) ** sharp
    return rays * np.clip(1 - r, 0, 1) ** 2


def sparks(size=SIZE, count=40, seed=6):
    """Black-body sparks round an impact: short bright dashes flying out from the centre."""
    rng = np.random.default_rng(seed)
    u, v = _grid(size, size)
    x, y = u - 0.5, v - 0.5
    out = np.zeros((size, size), np.float32)
    for _ in range(count):
        ang = rng.random() * 2 * math.pi; dist = 0.15 + rng.random() * 0.3; length = 0.03 + rng.random() * 0.05
        cx, cy = math.cos(ang) * dist, math.sin(ang) * dist
        dx, dy = math.cos(ang), math.sin(ang)
        t = np.clip((x - cx) * dx + (y - cy) * dy, -length, length)
        px, py = cx + dx * t, cy + dy * t
        d = np.sqrt((x - px) ** 2 + (y - py) ** 2)
        out = np.maximum(out, np.clip(1 - d / 0.006, 0, 1) * (1 - np.abs(t) / length))
    return out


def ring(size=SIZE, radius=0.32, width=0.05):
    """The flak's ring (M_Impact_Flak_Ring): a band at 'radius' of the sprite's half width."""
    u, v = _grid(size, size)
    r = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2) * 2
    return np.clip(1 - np.abs(r - radius * 2) / (width * 2), 0, 1) ** 2


# ---- baking ----------------------------------------------------------------------------------------------------------------

def _linear(hex_or_rgb):
    if isinstance(hex_or_rgb, str):
        h = hex_or_rgb.lstrip('#'); c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.array(hex_or_rgb, np.float32)


def tone(intensity, colour, gain=1.0):
    """ES2's HDR light as a sprite: 1 - exp(-I x colour x gain) per channel (white-hot where bright, the colour where faint),
    sRGB-encoded, its alpha the brightest channel (the remake draws the sprites additively)."""
    c = _linear(colour)
    lin = 1 - np.exp(-intensity[..., None] * c[None, None, :] * gain)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.maximum(lin, 0), 1 / 2.4) - 0.055)
    rgba = np.dstack([srgb, srgb.max(axis=2)])
    return (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)


def save(name, rgba):
    """The sprite into the mod (weapons/fx/<name>.png, once), its path in the mod."""
    rel = f'weapons/fx/{name}.png'
    if rel not in _made:
        path = os.path.join(MOD, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.fromarray(rgba, 'RGBA').save(path, optimize=True)
        _made[rel] = True
    return rel


def _key(colour):
    return colour.lstrip('#').lower() if isinstance(colour, str) else '%02x%02x%02x' % tuple(int(c * 255) for c in colour)


# family -> the ES2 look its parts bake (weapons.py PRIMARY's families)
LOOKS = {
    'Autocannon': 'body', 'ScatterGun': 'body', 'PulseLaser': 'body', 'ThermalPulse': 'body', 'CryoLance': 'body',
    'Blaster': 'blaster', 'ChargeOrb': 'blaster', 'GooGun': 'blaster', 'Flak': 'blaster', 'ThermoGun': 'blaster',
    'PlasmaThrower': 'blaster',
    'CoilGun': 'coil', 'RailGun': 'coil', 'GaussCannon': 'gauss',
    'BeamLaser': 'beam', 'ThermalBeam': 'beam', 'CryoBeam': 'beam', 'LightningGun': 'lightning',
}
BEAMS = ('beam', 'lightning')


def parts(family, kind, colour):
    """A family's fx parts (projectile, muzzle, impact) with baked sprites, or None for a family without an ES2 look (its
    GoF2 base's parts recoloured then: weapons.fx_parts). 'kind' the remake base's (a scatter gun has no impact)."""
    look = LOOKS.get(family)
    if look is None or MOD is None: return None
    key = _key(colour)
    out = {}
    if look == 'blaster':
        I = blaster_core() * 25.0 + glow() * 4.0   # (the glow lifted: ES2's bloom spreads its 50 : 2)
        out['projectile'] = {'sprite': save(f'es2_blaster_{key}', tone(I, colour, 1.0)), 'size': 1400, 'glow': 3.0, 'additive': True}
    elif look == 'body':
        out['projectile'] = {'sprite': save(f'es2_bolt_{key}', tone(streak() * 20.0, colour, 0.25)), 'size': 220, 'stretch': 4.0,
                             'alongFlight': True, 'glow': 2.5, 'additive': True}
    elif look in ('coil', 'gauss'):
        k = 98.0 if look == 'coil' else 18.0
        out['projectile'] = {'sprite': save(f'es2_{look}_{key}', tone(streak(k=k, head=0.6, noise=0.5) * (200.0 if look == 'coil' else 60.0), colour, 0.05)),
                             'size': 180, 'stretch': 6.0, 'alongFlight': True, 'glow': 3.0, 'additive': True}
    elif look == 'beam':
        out['projectile'] = {'sprite': save(f'es2_beam_{key}', tone(beam() * 50.0, colour, 0.05)), 'size': 160, 'glow': 2.5, 'additive': True}
    elif look == 'lightning':
        out['projectile'] = {'sprite': save(f'es2_lightning_{key}', tone(lightning() * 8.0, colour, 0.4)), 'size': 220, 'glow': 3.0, 'additive': True}
    # the muzzle flash
    if look in BEAMS:
        out['muzzle'] = {'sprite': save(f'es2_muzzle_beam_{key}', tone(glow() * 3.0, colour, 0.8)), 'size': 1500, 'glow': 2.0, 'lifetime': 100}
    else:
        I = glow() * 5.0 + star() * 30.0
        out['muzzle'] = {'sprite': save(f'es2_muzzle_{key}', tone(I, colour, 0.35)), 'size': 1000, 'glow': 2.0, 'lifetime': 60, 'grow': 1.3}
    # the impact (a scatter gun's base has none of its own)
    if kind != 'scatter':
        if look == 'lightning':
            I = sparks(count=10, seed=7) * 5.0 + glow() * 3.0   # (P_Impact_LightningGun: its arcs flying out, its glow)
            out['impact'] = {'sprite': save(f'es2_impact_lightning_{key}', tone(I, colour, 0.5)), 'size': 1800, 'glow': 2.5, 'lifetime': 200, 'spin': 90}
        elif look == 'beam':
            I = glow() * 6.0 + sparks() * 4.0
            out['impact'] = {'sprite': save(f'es2_impact_sparks_{key}', tone(I, [1.0, 0.325, 0.1], 0.6)), 'size': 1600, 'glow': 2.5, 'lifetime': 300, 'grow': 1.4}
        elif family == 'Flak':
            I = ring() * 8.0 + star(points=6) * 6.0 + glow() * 2.0
            out['impact'] = {'sprite': save(f'es2_impact_flak_{key}', tone(I, colour, 0.5)), 'size': 4000, 'glow': 2.5, 'lifetime': 250, 'grow': 1.8}
        else:
            I = glow() * 4.0 + sparks(count=24, seed=8) * 2.0
            out['impact'] = {'sprite': save(f'es2_impact_{key}', tone(I, colour, 0.5)), 'size': 1800, 'glow': 2.5, 'lifetime': 250, 'grow': 1.5}
    return out
