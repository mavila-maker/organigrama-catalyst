#!/usr/bin/env python3
"""Opera sobre el HTML original: quita nodos por nombre y reasigna sus hijos.

Uso: python3 scripts/patch.py
"""
import json, re, shutil
from pathlib import Path

REPO = Path("/sessions/loving-laughing-archimedes/mnt/HUB/Handbook/Organigrama/organigrama-catalyst")
SRC = REPO / "organigrama_catalyst.html.bak"   # ORIGINAL intacto
OUT_HTML = REPO / "organigrama_catalyst.html"
OUT_INDEX = REPO / "index.html"

# Personas a remover; sus hijos se mueven al jefe indicado.
# None => se cuelgan del padre actual.
REMOVALS = [
    ("Pamela Lozano", "Hugo Armenta"),      # sus reportes van a Hugo
    ("Ana Karen Torres", None),             # sin reportes; se elimina
]


def find_node(root, name):
    if root.get("name", "").strip().lower() == name.strip().lower():
        return root, None
    for i, c in enumerate(root.get("children", [])):
        if c.get("name", "").strip().lower() == name.strip().lower():
            return c, root
        found, parent = find_node(c, name)
        if found:
            return found, parent
    return None, None


def remove_and_reassign(root, name, new_parent_name):
    node, parent = find_node(root, name)
    if not node:
        print(f"  ! No encontré nodo: {name}")
        return
    if parent is None:
        raise SystemExit(f"No se puede quitar la raíz ({name})")
    # sacar de parent.children
    parent["children"] = [c for c in parent["children"] if c is not node]
    kids = node.get("children", [])
    if new_parent_name:
        target, _ = find_node(root, new_parent_name)
        if not target:
            raise SystemExit(f"No encontré nuevo jefe: {new_parent_name}")
        target["children"].extend(kids)
        print(f"  ✓ {name} removido; {len(kids)} reporte(s) movido(s) a {new_parent_name}")
    else:
        if kids:
            # sin nuevo jefe -> subir al padre del nodo
            parent["children"].extend(kids)
            print(f"  ✓ {name} removido; {len(kids)} reporte(s) subieron a {parent['name']}")
        else:
            print(f"  ✓ {name} removido (sin reportes)")


def count(root):
    return 1 + sum(count(c) for c in root.get("children", []))


def main():
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r"const ORG = (\{.*?\});", html, re.DOTALL)
    if not m:
        raise SystemExit("No encontré const ORG en el HTML")
    org = json.loads(m.group(1))
    before = count(org)
    print(f"Antes: {before} nodos")

    for name, new_boss in REMOVALS:
        remove_and_reassign(org, name, new_boss)

    after = count(org)
    print(f"Después: {after} nodos")

    org_json = json.dumps(org, ensure_ascii=False, separators=(",", ":"))
    new_html = html[:m.start()] + f"const ORG = {org_json};" + html[m.end():]

    OUT_HTML.write_text(new_html, encoding="utf-8")
    OUT_INDEX.write_text(new_html, encoding="utf-8")
    print(f"OK. Escritos {OUT_HTML.name} y {OUT_INDEX.name}")


if __name__ == "__main__":
    main()
