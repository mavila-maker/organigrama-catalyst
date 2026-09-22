#!/usr/bin/env python3
"""Regenera organigrama_catalyst.html a partir del Excel y las fotos.

Uso:
  python3 scripts/build.py --remove "Nombre Paterno Materno" [--remove ...]
"""
import argparse, base64, json, re, shutil, sys, unicodedata
from pathlib import Path
import openpyxl

ROOT = Path("/sessions/loving-laughing-archimedes/mnt/HUB/Handbook/Organigrama")
XLSX = ROOT / "Base de datos colaboradores .xlsx"
TEAM = ROOT / "Team"
HTML_SRC = ROOT / "organigrama-catalyst" / "organigrama_catalyst.html"
REPO = ROOT / "organigrama-catalyst"

SHORT_NAME_MAP = {
    "María Fernanda Avila Mendez": "Mafer Avila",
    "Darius Lau Castro": "Darius Lau",
    "Edgar Roberto Antelo Méndez": "Roberto Antelo",
    "Francisco Alfredo Uribe Sánchez": "Alfredo Uribe",
    "Carlos Hiram Montes Pascual": "Hiram Montes",
    "Ana Daniela Aguilar Rocha": "Daniela Aguilar",
    "Ana Karen Torres Davalos": "Ana Karen Torres",
    "Ismael de Jesús Román Guzman": "Ismael Román",
    "Jose Isaac Gomez Villaseñor": "Isaac Gómez",
    "Jonathan de Jesús Gutierrez Sosa": "Jonathan Gutierrez",
    "Paulina Ivonne Trejo Ramirez": "Paulina Trejo",
    "Pamela Lozano Benitez": "Pamela Lozano",
    "Hugo Alejandro Armenta Briseño": "Hugo Armenta",
    "Diego Alejandro Aguilar Lopez": "Alex Aguilar",
    "María Guadalupe Castillo Gómez": "María Castillo",
    "Diana Patricia Juárez Martínez": "Diana Juárez",
    "Juan Pablo Grajeda Gonzaleza": "Juan Pablo Grajeda",
    "Sofía Isabel Aloisio Delgado": "Sofía Aloisio",
    "Alfredo Carreón Urbano": "Alfredo Carreón",
}


def norm(s): return re.sub(r"\s+", " ", (s or "").strip())
def norm_ci(s): return unicodedata.normalize("NFC", norm(s)).lower()
def token_key(s):
    """Clave por conjunto ordenado de tokens (sin acentos, minúsculas).
    Evita problemas de orden Paterno/Materno en la hoja."""
    s = unicodedata.normalize("NFKD", norm(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(t for t in s.split() if t))

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def initials(short):
    parts = [p for p in short.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return short[:2].upper()

def na(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def find_photo(short):
    target = norm_ci(short)
    tgt_na = na(short.strip())
    exts = {".jpg", ".jpeg", ".png"}
    for p in TEAM.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            if norm_ci(p.stem) == target:
                return p
    for p in TEAM.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            if na(p.stem.strip()) == tgt_na:
                return p
    return None

def photo_data_uri(path):
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"

def load_people():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Hoja 1"]
    people = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        paterno, materno, nombre, puesto, reporta = row[0], row[1], row[2], row[3], row[4]
        if not nombre or not paterno:
            continue
        full = norm(f"{nombre} {paterno} {materno or ''}")
        # También probar orden invertido (por si paterno/materno están swapped en Excel)
        full_alt = norm(f"{nombre} {materno or ''} {paterno}")
        short = SHORT_NAME_MAP.get(full) or SHORT_NAME_MAP.get(full_alt)
        if not short:
            first = nombre.strip().split()[0]
            short = f"{first} {paterno.strip()}"
        people.append({
            "full": full, "short": short,
            "role": norm(puesto or ""),
            "reports_to": norm(reporta or ""),
        })
    return people

def build_tree(people, removed_fulls):
    removed = {token_key(x) for x in removed_fulls}
    by_key = {token_key(p["full"]): p for p in people}
    # índice también por short name y por short-name "primer + apellido"
    def add_alias(alias, person):
        k = token_key(alias)
        by_key.setdefault(k, person)
    for p in people:
        add_alias(p["short"], p)
    ceo = next((p for p in people if token_key(p["reports_to"]) == token_key(p["full"])), None)
    if not ceo:
        # fallback: buscar puesto == "CEO"
        ceo = next((p for p in people if p["role"].upper() == "CEO"), None)
    if not ceo:
        raise SystemExit("No CEO en la hoja")

    def match_key(name):
        """Regresa la key canónica de la persona referida en `name`.
        Acepta full name (cualquier orden) o short name."""
        k = token_key(name)
        if k in by_key:
            return token_key(by_key[k]["full"])
        # fuzzy: buscar por subconjunto de tokens
        name_tokens = set(k.split())
        best = None
        for kk, p in by_key.items():
            if not p: continue
            p_tokens = set(token_key(p["full"]).split()) | set(token_key(p["short"]).split())
            if name_tokens and name_tokens.issubset(p_tokens):
                best = p; break
        return token_key(best["full"]) if best else k

    def resolve_boss(key):
        cur = by_key.get(key)
        if not cur: return token_key(ceo["full"])
        boss_key = match_key(cur["reports_to"])
        visited = set()
        while boss_key in removed and boss_key not in visited:
            visited.add(boss_key)
            b = by_key.get(boss_key)
            if not b: return token_key(ceo["full"])
            boss_key = match_key(b["reports_to"])
        return boss_key

    children_map = {}
    for p in people:
        k = token_key(p["full"])
        if k in removed or p is ceo:
            continue
        boss_key = resolve_boss(k)
        children_map.setdefault(boss_key, []).append(p)

    def make_node(person, is_ceo=False):
        short = person["short"]
        photo_path = find_photo(short)
        node = {
            "id": "ceo" if is_ceo else slug(short),
            "name": short,
            "role": person["role"],
            "tag": "Ca.taly.st" if is_ceo else "",
            "initials": initials(short),
            "photo": photo_data_uri(photo_path) if photo_path else None,
            "logo": None,
            "children": [],
        }
        for c in children_map.get(token_key(person["full"]), []):
            node["children"].append(make_node(c))
        return node

    return make_node(ceo, is_ceo=True)

def replace_org(html, org_json):
    pat = re.compile(r"const ORG = \{.*?\};", re.DOTALL)
    if not pat.search(html):
        raise SystemExit("No encontré 'const ORG = {...};'")
    return pat.sub(lambda m: f"const ORG = {org_json};", html, count=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="append", default=[])
    args = ap.parse_args()

    people = load_people()
    print(f"Colaboradores en Excel: {len(people)}")
    if args.remove:
        print(f"Removidos: {args.remove}")

    org = build_tree(people, args.remove)
    org_json = json.dumps(org, ensure_ascii=False, separators=(",", ":"))

    missing = []
    def walk(n):
        if n["photo"] is None: missing.append(n["name"])
        for c in n["children"]: walk(c)
    walk(org)

    html = HTML_SRC.read_text(encoding="utf-8")
    new_html = replace_org(html, org_json)

    bak = HTML_SRC.with_suffix(".html.bak")
    if not bak.exists():
        shutil.copy2(HTML_SRC, bak)
    HTML_SRC.write_text(new_html, encoding="utf-8")

    REPO.mkdir(exist_ok=True)
    (REPO / "index.html").write_text(new_html, encoding="utf-8")
    (REPO / "organigrama_catalyst.html").write_text(new_html, encoding="utf-8")

    total = len(people) - len(args.remove)
    print(f"En organigrama: {total} personas")
    if missing:
        print("Sin foto:", ", ".join(missing))
    print("OK")

if __name__ == "__main__":
    main()
