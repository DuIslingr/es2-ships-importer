"""EVERSPACE 2's crafting as the ES2 Ships mod's blueprints (blueprints.json, built in the hangar's Blueprints tab), from ES2's
own recipe grids (DataFiles: es2data.py):
  - crafting_tech.csv: its tech components (Supra Gel, Power Cell, Fusion Core, ...) out of its ores, crystals, plasma and scrap;
    each becomes a commodity item of the mod and a blueprint with ES2's amounts;
  - crafting_consumables.csv: its consumables out of crafting parts and tech components, for the consumables the mod has
    (devices.py; ES2's nanobots_small is the mod's "nanobots", its big_bang the Radial Repulsor);
  - ES2's crafting parts (Spare Parts, Circuitry, Power Coupling, Quantum Processor), which ES2 salvages by dismantling gear,
    become commodities of their own that the NPCs carry and the shops stock (their occurrence), since GoF2 has no dismantling.
Ingredients: ES2's ores and crystals of every purity are the mod's one resource of that name (sectors.RESOURCES), its iron and
titanium GoF2's (156, 155), its plasma GoF2's Green Plasma (201), its scrap metal GoF2's Space Waste (99). A recipe with an
ingredient none of those cover (biomass, dark matter, the Okkar's and the Leviathan's) is left out, and so is a product
the mod doesn't have. Every blueprint is known from the start (ES2's recipes need no finding). ES2's catalysts (affixes on
gear) and crafted gear by rarity (crafting_data.csv) have no GoF2 counterpart.
Prices: ES2's item_price x PRICE_FACTOR (its resources' prices against the mod's: copper 150 against 45, baromite 750
against 175); the crafting parts, which have none, the mod's resource prices by rarity."""
import json, os
import es2data, icons

LOG = print
MOD_ID = 'es2_ships'
PRICE_FACTOR = 0.25

GAME_ITEMS = {'ore_iron': 156, 'ore_titanium': 155, 'plasma': 201, 'scrap_metal': 99}
ALIASES = {'nanobots_small': 'nanobots', 'big_bang': 'radial_repulsor'}
PARTS = {   # ES2 id -> (rarity, occurrence: how often the NPCs carry it and the shops stock it)
    'crafting_resource_basic': ('common', 45), 'crafting_resource_common': ('common', 35),
    'crafting_resource_uncommon': ('uncommon', 20), 'crafting_resource_rare': ('rare', 10),
}
PART_PRICE = {'common': 30, 'uncommon': 95, 'rare': 175}
COMPONENT_BASE = 156   # (Iron: a commodity's look and kind)


def resource(es2_id, resources):
    """The mod item (or GoF2 item number) standing in for an ES2 ore, crystal or raw material; None when nothing does."""
    for prefix, n in GAME_ITEMS.items():
        if es2_id == prefix or es2_id.startswith(prefix + '_'): return n
    for kind in ('ore_', 'crystal_'):
        if es2_id.startswith(kind):
            key = es2_id[len(kind):].rsplit('_', 1)[0]
            if key in resources: return f'{MOD_ID}:es2_{key}'
    return None


def build(mod, resources, products):
    """(items, blueprints): the components' and parts' items.json entries and the recipes' blueprints.json entries.
    'resources' the mod's ES2 resource keys (sectors.RESOURCES), 'products' the item ids the mod has (devices.py)."""
    if not es2data.available('crafting_tech.csv'): return [], []
    table = es2data.items()
    items, blueprints = [], []
    have = {}   # ES2 id -> ingredient reference

    def add_item(es2_id, price, occurrence, rarity):
        e = table.get(es2_id) or {}
        row = e.get('row') or [''] * 9
        iid = 'es2_' + es2_id
        items.append({'id': iid, 'base': COMPONENT_BASE, 'name': e.get('name') or es2_id.replace('_', ' ').title(),
                      'description': (row[8].strip() if len(row) > 8 and row[8].strip() else f'An EVERSPACE 2 crafting {rarity} material.')
                                     + ' Used in EVERSPACE 2 recipes (the Blueprints tab).',
                      'techLevel': 1, 'occurrence': occurrence, 'price': [price, int(round(price * 1.1))],
                      '_icon': row[7].strip() if len(row) > 7 else None, '_frame': 'commodity'})
        have[es2_id] = f'{MOD_ID}:{iid}'

    for pid, (rarity, occ) in PARTS.items(): add_item(pid, PART_PRICE[rarity], occ, rarity)

    def ingredients(need):
        out = []
        for ing, amount in need.items():
            ref = have.get(ing) or resource(ing, resources)
            if ref is None: return None
            out.append({'item': ref, 'amount': int(amount)})
        return out

    left = []
    for pid, need in es2data.recipes('crafting_tech.csv').items():
        ing = ingredients(need)
        if ing is None: left.append(pid); continue
        price = int(round((es2data.attr(pid, 'item_price') or 200) * PRICE_FACTOR))
        add_item(pid, price, 0, 'tech')   # (occurrence 0: only crafted)
        blueprints.append({'id': 'es2_craft_' + pid, 'item': have[pid], 'ingredients': ing, 'unlocked': True})
    made_consumables = 0
    for pid, need in es2data.recipes('crafting_consumables.csv').items():
        product = ALIASES.get(pid, pid)
        ing = ingredients(need)
        if product not in products or ing is None: left.append(pid); continue
        blueprints.append({'id': 'es2_craft_' + pid, 'item': f'{MOD_ID}:{product}', 'ingredients': ing, 'unlocked': True})
        made_consumables += 1
    made = icons.apply(items, mod)
    for it in items:
        for k in [k for k in it if k.startswith('_')]: del it[k]
    LOG(f'  crafting: {len(blueprints) - made_consumables} tech components and {made_consumables} consumables from ES2\'s recipes, '
        f'{len(PARTS)} crafting parts ({len(left)} recipes left out: an ingredient or product the mod lacks), {made} icons')
    return items, blueprints


def write(mod, blueprints):
    """Merges the recipes into blueprints.json: its own entries ('es2_craft_') replaced, any other kept."""
    p = os.path.join(mod, 'blueprints.json')
    old = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []
    keep = [b for b in old if not str(b.get('id', '')).startswith('es2_craft_')]
    if keep or blueprints: json.dump(keep + blueprints, open(p, 'w', encoding='utf-8'), indent=1)
