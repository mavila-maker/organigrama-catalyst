# Instrucciones — Actualizar organigrama Catalyst

Este archivo le dice a Claude cómo actualizar el organigrama cuando Mafer escriba el disparador: **"Actualizar organigrama"**.

---

## Archivos y rutas (siempre absolutas)

- Base de datos de colaboradores (fuente de verdad de nombres, puestos y jerarquía):
  `/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/Base de datos colaboradores .xlsx`
  - Hoja: `Hoja 1`
  - Columnas relevantes: `PATERNO`, `MATERNO`, `NOMBRE`, `PUESTO`, `REPORTA`
  - El campo `REPORTA` contiene el nombre completo del jefe (formato: `Nombre Paterno Materno`). El CEO se reporta a sí mismo.

- Carpeta de fotos (una foto por colaborador):
  `/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/Team/`
  - El nombre del archivo de foto debe coincidir (acentos incluidos) con el "nombre corto" del colaborador (ejemplos: `Mafer Avila.jpg`, `Darius Lau .jpg`, `César Arreola.jpg`, `Alfredo Carreón.png`).
  - Extensiones válidas: `.jpg`, `.jpeg`, `.png`.

- Organigrama actual (plantilla a regenerar):
  `/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/organigrama_catalyst.html`
  - Dentro trae `const ORG = {...};` con un árbol recursivo de nodos: `id`, `name`, `role`, `tag`, `initials`, `photo` (data URI base64), `logo`, `children`.

- Carpeta del repositorio (ya existe):
  `/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/organigrama-catalyst/`

- Remoto GitHub:
  `https://github.com/mavila-maker/organigrama-catalyst`

---

## Disparador

Cuando Mafer escriba **"Actualizar organigrama"** (o una frase equivalente muy cercana), Claude debe ejecutar los 7 pasos de abajo, en orden, sin pedir confirmación salvo que falte algo crítico (por ejemplo, que no se encuentre la foto de alguien — en ese caso avisar pero continuar con iniciales).

---

## Pasos a ejecutar

### 1. Leer la base de datos
- Abrir `Base de datos colaboradores .xlsx` con `openpyxl` (Python 3, `pip install openpyxl --break-system-packages` si no está).
- Recorrer `Hoja 1` desde la fila 2. Ignorar filas donde `NOMBRE` esté vacío.
- Para cada colaborador construir:
  - `fullName = f"{NOMBRE} {PATERNO} {MATERNO}"` (con trim de espacios dobles y `strip()`).
  - `shortName`: lo que viene antes del primer apellido compuesto normal. Regla simple: usar el primer nombre de pila + primer apellido paterno. Excepciones conocidas (mapear a archivo de foto):
    - `María Fernanda Avila Mendez` → `Mafer Avila`
    - `Darius Lau Castro` → `Darius Lau ` (ojo al espacio final en el archivo real)
    - `Edgar Roberto Antelo Méndez` → `Roberto Antelo`
    - `Francisco Alfredo Uribe Sánchez` → `Alfredo Uribe`
    - `Carlos Hiram Montes Pascual` → `Hiram Montes`
    - `Ana Daniela Aguilar Rocha` → `Daniela Aguilar`
    - `Ana Karen Torres Davalos` → `Ana Karen Torres`
    - `Ismael de Jesús Román Guzman` → `Ismael Román`
    - `Jose Isaac Gomez Villaseñor` → `Isaac Gómez`
    - `Jonathan de Jesús Gutierrez Sosa` → `Jonathan Gutierrez`
    - `Paulina Ivonne Trejo Ramirez` → `Paulina Trejo`
    - `Pamela Lozano Benitez` → `Pamela Lozano`
    - `Hugo Alejandro Armenta Briseño` → `Hugo Armenta`
    - `Diego Alejandro Aguilar Lopez` → `Alex Aguilar`
    - `María Guadalupe Castillo Gómez` → `María Castillo`
    - `Diana Patricia Juárez Martínez` → `Diana Juárez`
    - `Juan Pablo Grajeda Gonzaleza` → `Juan Pablo Grajeda`
    - `Sofía Isabel Aloisio Delgado` → `Sofía Aloisio`
    - `Alfredo Carreón Urbano` → `Alfredo Carreón`
  - Si aparece un colaborador nuevo sin entrada en el mapa, aplicar la regla por defecto (primer nombre + primer apellido) y hacer `fuzzy match` con los archivos de `Team/` (buscar por coincidencia parcial de ambos).
- `role` = columna `PUESTO`.
- `reportsToFullName` = columna `REPORTA` (puede venir con acentos; normalizar comparación con `unicodedata.normalize('NFC', ...).strip()`).

### 2. Armar el árbol jerárquico
- Indexar a todos los colaboradores por `fullName`.
- El CEO es quien `REPORTA == su propio fullName`.
- Cada otro colaborador cuelga de su jefe según `REPORTA`.
- Si un jefe referido no existe en la hoja, log de advertencia y colgar de CEO por defecto.

### 3. Matchear fotos y codificarlas en base64
- Para cada colaborador buscar en `/WIKI Catalyst/Team/` un archivo que empiece con su `shortName`. Si no existe, intentar match por primer nombre + primer apellido sin acentos.
- Si se encuentra: leer binario y codificar como data URI: `data:image/<ext>;base64,<...>`.
- Si no se encuentra: dejar `photo = null`. Las iniciales (`initials`) se calculan como primeras letras del primer nombre y primer apellido en mayúsculas (ej. `Mafer Avila` → `MA`).

### 4. Generar el JSON del árbol
Cada nodo debe tener esta forma exacta (compatible con el HTML actual):
```json
{
  "id": "<slug del shortName, minúsculas sin acentos>",
  "name": "<shortName>",
  "role": "<PUESTO>",
  "tag": "Ca.taly.st",
  "initials": "<INI>",
  "photo": "<data URI o null>",
  "logo": null,
  "children": [ ... ]
}
```
El nodo raíz (CEO) debe llevar `"tag": "Ca.taly.st"`.

### 5. Regenerar `organigrama_catalyst.html` e `index.html`
- Leer `organigrama_catalyst.html` y reemplazar el bloque `const ORG = {...};` por el nuevo JSON serializado (una sola línea, sin espacios extra, usando `json.dumps(org, ensure_ascii=False, separators=(',', ':'))`).
- Guardar el resultado sobreescribiendo `organigrama_catalyst.html`.
- Copiar el archivo actualizado a `/WIKI Catalyst/organigrama-catalyst/index.html` (misma ruta del repo local).
- También copiar `organigrama_catalyst.html` al repo: `/WIKI Catalyst/organigrama-catalyst/organigrama_catalyst.html` (para tener historial del archivo fuente).

### 6. Git: init (primera vez), commit y push
Rutina estándar desde la carpeta del repo:
```bash
cd "/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/organigrama-catalyst"

# Solo la PRIMERA vez:
if [ ! -d .git ]; then
  git init -b main
  git remote add origin https://github.com/mavila-maker/organigrama-catalyst.git
fi

git add index.html organigrama_catalyst.html CLAUDE.md .gitignore 2>/dev/null
git commit -m "Actualizar organigrama — $(date +%Y-%m-%d)"
git push -u origin main
```
- Si el push falla por autenticación, avisar a Mafer que configure credenciales (`gh auth login` o token en `~/.git-credentials`) y no reintentar automáticamente.
- Si `main` no existe remoto, el `-u origin main` lo crea en el primer push.

### 7. Entregar al usuario
- Reportar en respuesta:
  - Número de colaboradores procesados.
  - Colaboradores sin foto encontrada (si hubo).
  - Link al archivo actualizado: `[Ver organigrama](computer:///sessions/loving-laughing-archimedes/mnt/WIKI Catalyst/organigrama-catalyst/index.html)`.
  - Confirmación de commit y push (hash corto del commit).

---

## Plantilla de script (referencia rápida)

Guardar en `organigrama-catalyst/scripts/build.py` si aún no existe, y ejecutar con `python3 scripts/build.py`. Esqueleto:

```python
import base64, json, re, unicodedata
from pathlib import Path
import openpyxl

ROOT = Path("/sessions/loving-laughing-archimedes/mnt/WIKI Catalyst")
XLSX = ROOT / "Base de datos colaboradores .xlsx"
TEAM = ROOT / "Team"
HTML_SRC = ROOT / "organigrama_catalyst.html"
REPO = ROOT / "organigrama-catalyst"

SHORT_NAME_MAP = {
    "María Fernanda Avila Mendez": "Mafer Avila",
    "Darius Lau Castro": "Darius Lau",
    # ...completar con la tabla del paso 1
}

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def initials(short):
    parts = short.split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper()

def find_photo(short):
    # busca "short.jpg|jpeg|png" con o sin espacio final
    for p in TEAM.iterdir():
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            if p.stem.strip().lower() == short.strip().lower():
                return p
    return None

def photo_data_uri(path):
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"

# ... leer xlsx, armar mapa, construir árbol recursivo, serializar,
# reemplazar `const ORG = {...};` en HTML y copiar a index.html.
```

---

## Reglas de oro

1. **No borrar el HTML original** hasta confirmar que el nuevo renderiza (dejar `.bak` si hay dudas).
2. **No modificar** el CSS ni la estructura del HTML — solo el objeto `ORG`.
3. **Ignorar filas vacías** de la hoja Excel.
4. **Avisar, no adivinar**: si un jefe no se encuentra, reportar en la respuesta final.
5. **No hacer force push** al remoto nunca.
6. **No commitear** la base de datos `.xlsx` ni la carpeta `Team/` al repo — ese contenido vive en el workspace local, no en GitHub.

---

## `.gitignore` sugerido para la carpeta del repo

```
.DS_Store
scripts/__pycache__/
*.bak
```
