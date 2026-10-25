"""EVERSPACE 2's factions for the ES2 Ships mod (the remake's mod factions, factions.json: Modding/README.md "Factions").

ES2's galaxy is its own: its ships fly for ES2's factions, never for Galaxy on Fire 2's races, and its sectors belong to
them. Each faction comes from ES2's own tables (DataFiles/factions.csv: the factions and their names;
DataFiles/faction_relations.csv: who is a Friend, Neutral or Enemy of whom, the player's row the starting standing), which
a plain FModel export leaves out: tools/shaders' `pak` mode extracts them (see the README). Without them the factions are
still made, without ES2's relations (only "hostile").

FACTIONS: the factions the mod's ships and sectors use (ES2's own faction name -> the mod's id), their look (the GoF2 race
whose hangar, bar and visitors they borrow), whether they are hostile to everyone (like GoF2's pirates: no diplomat can
reconcile them), their emblem (ES2's decal logos, UI/Images/Items/item_decal_*_logo, tinted in the faction's colour; none:
the look race's emblem) and colour."""
import os
import numpy as np
from PIL import Image

# ES2 faction -> (id, name, look, hostile, logo or None, colour); names are ES2's (factions.csv) where it has a proper one.
FACTIONS = {
    'GradyAndBrunt': ('gb', 'Grady & Brunt', 'midorian', False, 'grady_brunt', (1.0, 0.72, 0.22)),
    'Freelancer': ('freelancer', 'Freelancers', 'nivelian', False, None, (0.45, 0.85, 1.0)),
    'Coalition': ('coalition', 'Coalition', 'terran', False, 'coalition', (0.4, 0.62, 1.0)),
    'Okkar': ('okkar', 'Okkar', 'vossk', False, 'okkar', (0.35, 0.95, 0.62)),
    'KatoCartel': ('kato', "Mr. Kato's Cartel", 'terran', False, None, (0.95, 0.5, 0.9)),
    'OkkarRadical': ('okkar_prime', 'Okkar Prime', 'void', True, 'okkar', (0.82, 0.32, 1.0)),
    'Outlaw': ('outlaw', 'Outlaws', 'pirates', True, 'outlaw', (1.0, 0.32, 0.25)),
    'Cultist': ('cultist', 'Redeemers', 'void', True, None, (0.7, 0.25, 0.85)),
    'Ancient': ('ancient', 'Ancients', 'void', True, None, (0.55, 1.0, 0.85)),
    'Zurilia': ('zurilia', 'Zurilia', 'pirates', True, 'zurilia', (1.0, 0.55, 0.15)),
    'Retaliators': ('retaliators', 'Retaliators', 'pirates', True, 'retaliators', (0.9, 0.2, 0.35)),
    'CloneHunter': ('clonehunter', 'Colonial Clone Hunters', 'terran', False, 'colonial', (0.75, 0.8, 0.9)),
    'RogueAI': ('rogueai', 'Rogue AI', 'void', True, None, (0.3, 1.0, 0.4)),
}
# ES2's relation words -> factions.json's; the player's row -> the starting standing
RELATION = {'Friend': 'friend', 'Neutral': 'neutral', 'Enemy': 'enemy'}
PLAYER_START = {'Friend': 75, 'Neutral': 0, 'Enemy': -100}


def key(es2_name):
    """A faction's mod key ("es2_ships:<id>") by ES2's faction name."""
    return 'es2_ships:' + FACTIONS[es2_name][0]


def _csv(src, name):
    p = os.path.join(src, 'DataFiles', name)
    if not os.path.exists(p): return None
    return [line.rstrip('\r\n').split('|~') for line in open(p, encoding='utf-8-sig', errors='replace') if line.strip()]


def relations(src):
    """faction_relations.csv as {row faction: {column faction: 'Friend' | 'Neutral' | 'Enemy'}}, or None without it."""
    rows = _csv(src, 'faction_relations.csv')
    if not rows: return None
    head = [h.strip() for h in rows[0]]
    out = {}
    for r in rows[1:]:
        out[r[0].strip()] = {head[i]: r[i].strip() for i in range(1, min(len(head), len(r)))}
    return out


def names(src):
    """factions.csv's display names by faction (the rows that start a faction)."""
    rows = _csv(src, 'factions.csv') or []
    return {r[0].strip(): r[1].strip() for r in rows if r and r[0].strip() and len(r) > 1 and r[1].strip()}


def _emblem(src, logo, colour, out):
    """ES2's white decal logo tinted in the faction's colour (its alpha kept), 172 x 172."""
    p = os.path.join(src, 'UI/Images/Items', f'item_decal_{logo}_logo_86x86_2x.png')
    if not os.path.exists(p): return False
    a = np.asarray(Image.open(p).convert('RGBA'), np.float32) / 255.0
    lum = a[..., :3].max(axis=2)
    rgb = np.clip(lum[..., None] * np.array(colour, np.float32) * 1.05 + lum[..., None] ** 6 * 0.15, 0, 1)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray((np.dstack([rgb, a[..., 3]]) * 255).astype(np.uint8), 'RGBA').save(out, optimize=True)
    return True


def build(src, mod, log=print):
    """factions.json's entries: every faction of FACTIONS with ES2's relations among them and the player's start."""
    rel = relations(src)
    shown = names(src)
    out = []
    for es2, (fid, name, look, hostile, logo, colour) in FACTIONS.items():
        e = {'id': fid, 'name': name, 'look': look, 'color': [round(c, 3) for c in colour]}
        # always the player's enemy where ES2's table says so (its other relations stay as ES2 has them)
        if hostile or (rel and rel.get(es2, {}).get('Player') == 'Enemy'): e['hostile'] = True
        if rel and es2 in rel:
            e['standing'] = PLAYER_START.get(rel[es2].get('Player', 'Neutral'), 0)
            r = {FACTIONS[o][0]: RELATION[v] for o, v in rel[es2].items() if o in FACTIONS and o != es2 and v in RELATION}
            if r: e['relations'] = r
        elif hostile:
            e['standing'] = -100
        if logo and _emblem(src, logo, colour, os.path.join(mod, 'factions', fid + '.png')): e['icon'] = f'factions/{fid}.png'
        out.append(e)
    log(f'  {len(out)} factions' + ('' if rel else ' (no DataFiles/faction_relations.csv: without ES2\'s relations)') +
        f', {sum(1 for e in out if "icon" in e)} emblems')
    return out


# The mod's old GoF2 races (before the factions) -> the faction that now flies them, for ships without a blueprint faction.
RACE_FACTION = {0: 'Coalition', 1: 'Okkar', 2: 'Freelancer', 3: 'GradyAndBrunt', 8: 'Outlaw', 9: 'Ancient'}
# A ship id's prefix -> its faction, where a blueprint names none of FACTIONS (ES2's own pawns sometimes name PlayerFriend).
PREFIX_FACTION = [('es2_zurilia', 'Zurilia'), ('es2_retaliator', 'Retaliators'), ('es2_clonehunter', 'CloneHunter'),
                  ('es2_rogueai', 'RogueAI'), ('es2_bloodstar', 'Outlaw'), ('es2_kato', 'KatoCartel'), ('es2_okkarprime', 'OkkarRadical'), ('es2_redeemer', 'Cultist'), ('es2_cultist', 'Cultist'),
                  ('es2_swarmer', 'Ancient'), ('es2_outlaw', 'Outlaw'), ('es2_okkar', 'Okkar'), ('es2_gb', 'GradyAndBrunt'),
                  ('es2_coalition', 'Coalition'), ('es2_colonial', 'Coalition'), ('es2_freelancer', 'Freelancer')]


def blueprint_faction(bp):
    """The ES2 faction a blueprint (or a parent) names (its "Faction": "EFactions::X"), if it is one of FACTIONS."""
    import re, json, warships
    n, seen = bp, set()
    while n and n not in seen:
        seen.add(n)
        for e in warships._bp(n) or []:
            m = re.search(r'"Faction":\s*"EFactions::(\w+)"', json.dumps(e.get('Properties') or {}))
            if m and m.group(1) in FACTIONS: return m.group(1)
        n = warships._super(n)
    return None


def for_ship(sid, bp=None, race=None):
    """A ship's faction key: its blueprint's faction, else its id's, else its old GoF2 race's."""
    f = blueprint_faction(bp) if bp else None
    if f is None: f = next((x for p, x in PREFIX_FACTION if sid.startswith(p)), None)
    if f is None and isinstance(race, int): f = RACE_FACTION.get(race)
    return key(f) if f else None


def races(ints):
    """The old GoF2 races of a traffic list as faction keys."""
    return list(dict.fromkeys(key(RACE_FACTION[r]) for r in ints if r in RACE_FACTION))
