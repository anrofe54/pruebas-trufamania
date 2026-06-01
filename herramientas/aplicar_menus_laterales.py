from pathlib import Path
from urllib.parse import unquote
from collections import Counter
import argparse
import html
import re
import sys

EXCLUIR = (
    "_mal",
    "_bien",
    "_copia",
    "_antigua",
    "_claude",
    "_codex",
    "trufflesA.htm",
    "edisclaimer.htm",
)

ANCHOR_RE = re.compile(
    r'<a\b[^>]*\bhref\s*=\s*([\'"])(.*?)\1[^>]*>(.*?)</a>',
    re.I | re.S
)

ANCHOR_LINE_RE = re.compile(
    r'(<a\b[^>]*\bhref\s*=\s*)([\'"])(.*?)(\2)([^>]*>)(.*?)(</a>)',
    re.I | re.S
)

EM_RE = re.compile(r'(<em\b[^>]*>).*?(</em>)', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')

MENUS = {
    "Tuber": Path("fragmentos/menu-tuber.txt"),
    "Terfezia": Path("fragmentos/menu-terfezia.txt"),
}

EXCLUSIONES = Path("fragmentos/exclusiones-menu-especies.txt")

def excluido(path: Path) -> bool:
    name = path.name
    return any(x in name for x in EXCLUIR)

def leer_html(path: Path):
    data = path.read_bytes()

    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            texto = data.decode(enc)
            return texto, enc
        except UnicodeDecodeError:
            pass

    raise UnicodeDecodeError("desconocida", data, 0, 1, f"No se pudo decodificar {path}")

def escribir_html(path: Path, texto: str, encoding: str):
    path.write_bytes(texto.encode(encoding))

def salto_linea(texto: str) -> str:
    return "\r\n" if "\r\n" in texto else "\n"

def limpiar_texto(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    return " ".join(s.split())

def normalizar(s: str) -> str:
    s = html.unescape(s)
    s = s.lower()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    s = s.replace("ü", "u").replace("ñ", "n")
    s = re.sub(r'\b(tuber|terfezia)\b', '', s)
    s = re.sub(r'english\.htm$', '', s)
    s = re.sub(r'\.htm$', '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return " ".join(s.split())

def clasificar_href(href: str):
    href = html.unescape(href)
    href = unquote(href)
    href = href.split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
    base = href.rsplit("/", 1)[-1]

    if not base.lower().endswith(".htm"):
        return None

    if base.startswith("Tuber "):
        genero = "Tuber"
    elif base.startswith("Terfezia "):
        genero = "Terfezia"
    else:
        return None

    idioma = "EN" if base.endswith(" English.htm") else "ES"
    return genero, idioma, base

def es_lista_compacta(visible: str, destino: str) -> bool:
    v = visible.strip()
    vu = v.upper()

    if not v:
        return False

    if vu in ("ES", "EN"):
        return False

    if "NEW SPECIES" in vu or "NUEVA ESPECIE" in vu or "NUEVAS ESPECIES" in vu:
        return False

    if "FICHA DESCRIPTIVA" in vu or "FULL DESCRIPTION" in vu:
        return False

    return normalizar(v) == normalizar(destino)

def idioma_de_archivo(path: Path) -> str:
    return "EN" if path.name.endswith(" English.htm") else "ES"

def genero_de_archivo(path: Path):
    if path.name.startswith("Tuber "):
        return "Tuber"
    if path.name.startswith("Terfezia "):
        return "Terfezia"
    return None

def nombre_especie_de_archivo(path: Path):
    genero = genero_de_archivo(path)

    if not genero:
        return None

    name = path.name

    if name.endswith(" English.htm"):
        especie = name.removeprefix(f"{genero} ").removesuffix(" English.htm")
    else:
        especie = name.removeprefix(f"{genero} ").removesuffix(".htm")

    return f"{genero} {especie}"

def leer_exclusiones():
    if not EXCLUSIONES.exists():
        return set()

    excluidas = set()

    for linea in EXCLUSIONES.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()

        if not linea or linea.startswith("#") or linea.startswith("["):
            continue

        excluidas.add(normalizar(linea))

    return excluidas

def leer_menu(genero: str):
    ruta = MENUS[genero]

    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}")

    entradas = []

    for num, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()

        if not linea or linea.startswith("#"):
            continue

        partes = [p.strip() for p in linea.split("|")]

        if len(partes) != 3:
            raise ValueError(f"{ruta}:{num}: línea inválida: {linea}")

        visible, href_es, href_en = partes

        if not visible or not href_es or not href_en:
            raise ValueError(f"{ruta}:{num}: campos vacíos: {linea}")

        entradas.append({
            "visible": visible,
            "ES": href_es,
            "EN": href_en,
        })

    if not entradas:
        raise ValueError(f"{ruta}: menú vacío")

    return entradas

def linea_de_posicion(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos)

def detectar_bloques_compactos(texto: str):
    candidatos = []

    for m in ANCHOR_RE.finditer(texto):
        info = clasificar_href(m.group(2))

        if not info:
            continue

        genero, idioma, destino = info
        visible = limpiar_texto(m.group(3))

        if not es_lista_compacta(visible, destino):
            continue

        candidatos.append({
            "linea_idx": linea_de_posicion(texto, m.start()),
            "genero": genero,
            "idioma": idioma,
            "destino": destino,
            "visible": visible,
        })

    bloques = []
    actual = []

    for e in candidatos:
        if not actual:
            actual = [e]
            continue

        previo = actual[-1]
        mismo_grupo = previo["genero"] == e["genero"] and previo["idioma"] == e["idioma"]
        cerca = e["linea_idx"] - previo["linea_idx"] <= 3

        if mismo_grupo and cerca:
            actual.append(e)
        else:
            if len(actual) >= 5:
                bloques.append(actual)
            actual = [e]

    if len(actual) >= 5:
        bloques.append(actual)

    return bloques

def contenido_anchor_preservando_formato(inner_html: str, visible: str) -> str:
    if EM_RE.search(inner_html):
        return EM_RE.sub(rf'\1{visible}\2', inner_html, count=1)

    return visible

def reemplazar_anchor_en_linea(linea: str, href: str, visible: str) -> str:
    def repl(m):
        inner = m.group(6)
        nuevo_inner = contenido_anchor_preservando_formato(inner, visible)
        return f"{m.group(1)}{m.group(2)}{href}{m.group(4)}{m.group(5)}{nuevo_inner}{m.group(7)}"

    nueva, n = ANCHOR_LINE_RE.subn(repl, linea, count=1)

    if n == 0:
        return f'<li><a href="{href}"><em>{visible}</em></a></li>'

    return nueva

def crear_lineas_menu(genero: str, idioma: str, plantilla_lineas, menus):
    entradas = menus[genero]
    lineas_anchor = [l for l in plantilla_lineas if "<a" in l.lower() and "</a>" in l.lower()]

    if not lineas_anchor:
        lineas_anchor = ['                     <li><a href="__HREF__"><em>__VISIBLE__</em></a></li>']

    nuevas = []

    for i, entrada in enumerate(entradas):
        plantilla = lineas_anchor[i] if i < len(lineas_anchor) else lineas_anchor[-1]
        nuevas.append(
            reemplazar_anchor_en_linea(
                plantilla,
                entrada[idioma],
                entrada["visible"],
            )
        )

    return nuevas

def unir_lineas(lineas, texto_original):
    nl = salto_linea(texto_original)
    resultado = nl.join(lineas)

    if texto_original.endswith(("\n", "\r")):
        resultado += nl

    return resultado

def reemplazar_con_marcadores(path: Path, texto: str, menus):
    genero = genero_de_archivo(path)
    idioma = idioma_de_archivo(path)

    if genero not in MENUS:
        return texto, None

    inicio = f"<!-- INICIO MENU {genero.upper()} -->"
    fin = f"<!-- FIN MENU {genero.upper()} -->"

    lineas = texto.splitlines()

    idx_inicio = None
    idx_fin = None

    for i, linea in enumerate(lineas):
        if inicio in linea:
            idx_inicio = i
        if fin in linea:
            idx_fin = i
            break

    if idx_inicio is not None or idx_fin is not None:
        if idx_inicio is None or idx_fin is None or idx_fin <= idx_inicio:
            raise ValueError(f"{path}: marcadores incoherentes")

        plantilla = lineas[idx_inicio + 1:idx_fin]
        nuevas = crear_lineas_menu(genero, idioma, plantilla, menus)
        resultado = lineas[:idx_inicio + 1] + nuevas + lineas[idx_fin:]
        return unir_lineas(resultado, texto), {
            "modo": "marcadores existentes",
            "genero": genero,
            "idioma": idioma,
            "linea_inicio": idx_inicio + 1,
            "linea_fin": idx_fin + 1,
            "enlaces_nuevos": len(nuevas),
        }

    bloques = detectar_bloques_compactos(texto)
    bloques = [
        b for b in bloques
        if b[0]["genero"] == genero and b[0]["idioma"] == idioma
    ]

    if not bloques:
        return texto, None

    if len(bloques) > 1:
        raise ValueError(f"{path}: más de un bloque compacto detectado")

    bloque = bloques[0]
    idx_ini = bloque[0]["linea_idx"]
    idx_fin = bloque[-1]["linea_idx"]

    plantilla = lineas[idx_ini:idx_fin + 1]
    nuevas = crear_lineas_menu(genero, idioma, plantilla, menus)
    bloque_con_marcadores = [inicio] + nuevas + [fin]

    resultado = lineas[:idx_ini] + bloque_con_marcadores + lineas[idx_fin + 1:]

    return unir_lineas(resultado, texto), {
        "modo": "bloque compacto antiguo",
        "genero": genero,
        "idioma": idioma,
        "linea_inicio": idx_ini + 1,
        "linea_fin": idx_fin + 1,
        "enlaces_antiguos": len(bloque),
        "enlaces_nuevos": len(nuevas),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Modificar realmente los archivos")
    args = parser.parse_args()

    menus = {
        "Tuber": leer_menu("Tuber"),
        "Terfezia": leer_menu("Terfezia"),
    }

    exclusiones = leer_exclusiones()

    archivos = sorted(
        p for p in Path(".").glob("*.htm")
        if p.is_file()
        and not excluido(p)
        and genero_de_archivo(p) in MENUS
    )

    cambios = []
    sin_bloque = []
    saltados_por_exclusion = []
    errores = []

    for path in archivos:
        especie = nombre_especie_de_archivo(path)

        if especie and normalizar(especie) in exclusiones:
            saltados_por_exclusion.append(path.name)
            continue

        try:
            texto, encoding = leer_html(path)
            nuevo, info = reemplazar_con_marcadores(path, texto, menus)

            if info is None:
                sin_bloque.append(path.name)
                continue

            if nuevo != texto:
                cambios.append((path, info, encoding, nuevo))

        except Exception as e:
            errores.append((path.name, str(e)))

    print()
    if args.apply:
        print("=== APLICACIÓN REAL DE MENÚS LATERALES ===")
    else:
        print("=== SIMULACIÓN: NO SE MODIFICA NINGUNA FICHA HTML ===")
    print()

    print(f"Entradas en menu-tuber.txt: {len(menus['Tuber'])}")
    print(f"Entradas en menu-terfezia.txt: {len(menus['Terfezia'])}")
    print(f"Archivos saltados por exclusión deliberada: {len(saltados_por_exclusion)}")
    print(f"Archivos que se modificarían/modifican: {len(cambios)}")

    conteo = Counter((info["genero"], info["idioma"]) for _, info, _, _ in cambios)

    for clave in sorted(conteo):
        print(f"  {clave[0]} {clave[1]}: {conteo[clave]}")

    print()

    for path, info, _, _ in cambios:
        if info["modo"] == "bloque compacto antiguo":
            print(
                f"{path.name} | {info['genero']} {info['idioma']} | "
                f"líneas {info['linea_inicio']}-{info['linea_fin']} | "
                f"{info['enlaces_antiguos']} -> {info['enlaces_nuevos']} enlaces"
            )
        else:
            print(
                f"{path.name} | {info['genero']} {info['idioma']} | "
                f"marcadores existentes | "
                f"{info['enlaces_nuevos']} enlaces"
            )

    if saltados_por_exclusion:
        print()
        print("Archivos saltados por exclusión deliberada:")
        for nombre in saltados_por_exclusion:
            print(f"  - {nombre}")

    if sin_bloque:
        print()
        print("Archivos de especie sin bloque compacto sustituible:")
        for nombre in sin_bloque:
            print(f"  - {nombre}")

    if errores:
        print()
        print("ERRORES:")
        for nombre, error in errores:
            print(f"  - {nombre}: {error}")

    if errores:
        sys.exit(1)

    if args.apply:
        for path, _, encoding, nuevo in cambios:
            escribir_html(path, nuevo, encoding)
        print()
        print(f"Archivos modificados: {len(cambios)}")
    else:
        print()
        print("Simulación terminada. Para aplicar de verdad:")
        print("  python herramientas/aplicar_menus_laterales.py --apply")

if __name__ == "__main__":
    main()
