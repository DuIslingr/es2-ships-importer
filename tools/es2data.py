"""EVERSPACE 2's game tables (DataFiles/*.csv in the export: ES2 keeps them as '|~'-separated text in pakchunk0-Windows.pak,
not as DataTables; FModel exports them as they are). Rows are lines, cells split on '|~', text in cp1252.

items.CSV has no header: its first 13 cells are the item's category, name, id and texts (cell 4 the id, 5 the name), and
from cell 13 on each of attributes.CSV's columns, in its order: every attribute takes three cells, the minimum (a number or a
level list "20|19|18"), an operator ('!' or '*') and the maximum. attributes.CSV's rows: the names, the display formats,
the short formats, a flag, the units ('%', 's', 'm', 'cr'), the operators, the types.

The recipe tables (crafting_consumables.csv, crafting_tech.csv, crafting_catalysts.csv) are grids: the first row the
ingredients' ids (its first cell empty), each other row a product id and the amounts of those ingredients (empty: none)."""
import os

SRC = None
ITEM_COLUMNS = 13


def configure(src):
    global SRC, _items
    SRC, _items = src, None


def path(name):
    return os.path.join(SRC or '', 'DataFiles', name)


def available(name='items.CSV'):
    return bool(SRC) and os.path.exists(path(name))


def rows(name):
    """A table's rows (lists of cells); [] when the export doesn't have it."""
    p = path(name)
    if not os.path.exists(p): return []
    text = open(p, 'rb').read().decode('cp1252')
    return [line.split('|~') for line in text.replace('\r', '').split('\n') if line.strip()]


def number(cell, level=0):
    """A cell's number (a level list's 'level'-th entry, the last when shorter); None when empty or not a number."""
    cell = (cell or '').strip()
    if not cell: return None
    parts = cell.split('|')
    try: return float(parts[min(level, len(parts) - 1)])
    except ValueError: return None


_items = None
def items():
    """{item id: {'category', 'name', 'row': its cells, 'attr': {attribute: (min cell, max cell)}}} from items.CSV."""
    global _items
    if _items is None:
        _items = {}
        names = (rows('attributes.CSV') or [[]])[0]
        for r in rows('items.CSV'):
            if len(r) <= 5 or not r[4].strip(): continue
            attr = {}
            for j, n in enumerate(names):
                n = n.strip()
                c = ITEM_COLUMNS + j
                if not n or c >= len(r) or not r[c].strip(): continue
                attr[n] = (r[c], r[c + 2] if c + 2 < len(r) else r[c])
            _items[r[4].strip()] = {'category': r[0].strip(), 'name': r[5].strip(), 'row': r, 'attr': attr}
    return _items


def attr(item_id, name, level=0, maximum=False):
    """An item's attribute as a number (its minimum, or the maximum; a level list's entry); None when it has none."""
    it = items().get(item_id)
    if not it or name not in it['attr']: return None
    lo, hi = it['attr'][name]
    return number(hi if maximum else lo, level)


def recipes(name):
    """A recipe grid: {product id: {ingredient id: amount}}."""
    t = rows(name)
    if not t: return {}
    head = [c.strip() for c in t[0]]
    out = {}
    for r in t[1:]:
        if not r or not r[0].strip(): continue
        need = {}
        for j in range(1, min(len(r), len(head))):
            n = number(r[j])
            if n and head[j]: need[head[j]] = int(round(n))
        out[r[0].strip()] = need
    return out
