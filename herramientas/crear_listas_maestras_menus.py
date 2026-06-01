from pathlib import Path
from urllib.parse import unquote
from collections import defaultdict, Counter
import re
import html
import datetime

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

TAG_RE = re.compile(r'<[^>]+>')

def excluido(path: Path) -> bool:
    name = path.name
    return any(x in name for x in EXCLUIR)

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

def linea_de_posicion(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1

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

def extraer_bloques(path: Path):
    texto = path.read_text(encoding="utf-8", errors="replace")
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
            "archivo": path.name,
            "linea": linea_de_posicion(texto, m.start()),
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
        cerca = e["linea"] - previo["linea"] <= 3

        if mismo_grupo and cerca:
            actual.append(e)
        else:
            if len(actual) >= 5:
                bloques.append(actual)
            actual = [e]

    if len(actual) >= 5:
        bloques.append(actual)

    return bloques

def firma_bloque(bloque):
    return tuple(e["destino"] for e in bloque)

def elegir_bloque_maestro(bloques):
    if not bloques:
        return None

    firmas = Counter(firma_bloque(b) for b in bloques)

    return sorted(
        bloques,
        key=lambda b: (
            len(b),
            firmas[firma_bloque(b)],
            -b[0]["linea"],
            b[0]["archivo"],
        ),
        reverse=True,
    )[0]

def href_es(genero: str, visible: str) -> str:
    return f"{genero} {visible}.htm"

def href_en(genero: str, visible: str) -> str:
    return f"{genero} {visible} English.htm"

def crear_lista_maestra(genero: str, bloque):
    lineas = []
    lineas.append(f"# Lista maestra del menú lateral de {genero}")
    lineas.append("# Formato: texto visible|archivo español|archivo inglés")
    lineas.append("# Edita aquí cuando añadas, quites o reordenes especies.")
    lineas.append("")

    for e in bloque:
        visible = e["visible"].strip()
        lineas.append(f"{visible}|{href_es(genero, visible)}|{href_en(genero, visible)}")

    lineas.append("")
    return "\n".join(lineas)

def especies_existentes(genero: str):
    patron = f"{genero} *.htm"
    especies = defaultdict(set)

    for p in sorted(Path(".").glob(patron)):
        if excluido(p):
            continue

        name = p.name
        if name.endswith(" English.htm"):
            especie = name.removeprefix(f"{genero} ").removesuffix(" English.htm")
            especies[especie].add("EN")
        else:
            especie = name.removeprefix(f"{genero} ").removesuffix(".htm")
            especies[especie].add("ES")

    return especies

def main():
    archivos = sorted(
        p for p in Path(".").glob("*.htm")
        if p.is_file()
        and not excluido(p)
        and (p.name.startswith("Tuber ") or p.name.startswith("Terfezia "))
    )

    bloques_por_genero = defaultdict(list)

    for p in archivos:
        for bloque in extraer_bloques(p):
            genero = bloque[0]["genero"]
            bloques_por_genero[genero].append(bloque)

    informe = []
    informe.append("INFORME DE LISTAS MAESTRAS PARA MENÚS LATERALES")
    informe.append(f"Generado: {datetime.datetime.now().isoformat(timespec='seconds')}")
    informe.append("")
    informe.append("Alcance:")
    informe.append("- Solo menús laterales compactos de fichas individuales Tuber y Terfezia.")
    informe.append("- No se han modificado fichas HTML existentes.")
    informe.append("- No se han tocado páginas índice ni bloques descriptivos.")
    informe.append("")

    salidas = {
        "Tuber": Path("fragmentos/menu-tuber.txt"),
        "Terfezia": Path("fragmentos/menu-terfezia.txt"),
    }

    for genero in ("Tuber", "Terfezia"):
        bloques = bloques_por_genero.get(genero, [])
        maestro = elegir_bloque_maestro(bloques)

        informe.append("=" * 72)
        informe.append(genero)
        informe.append("=" * 72)

        if not maestro:
            informe.append("No se encontró bloque maestro.")
            informe.append("")
            continue

        firmas = Counter(firma_bloque(b) for b in bloques)
        longitudes = Counter(len(b) for b in bloques)

        salidas[genero].write_text(crear_lista_maestra(genero, maestro), encoding="utf-8")

        visibles_master = {e["visible"].strip() for e in maestro}
        existentes = especies_existentes(genero)

        informe.append(f"Bloques compactos detectados: {len(bloques)}")
        informe.append("Longitudes detectadas: " + ", ".join(f"{k} enlaces: {v} bloques" for k, v in sorted(longitudes.items())))
        informe.append(f"Bloque usado como base: {maestro[0]['archivo']}, líneas {maestro[0]['linea']}-{maestro[-1]['linea']}")
        informe.append(f"Enlaces en la lista maestra creada: {len(maestro)}")
        informe.append(f"Veces que aparece la misma secuencia: {firmas[firma_bloque(maestro)]}")
        informe.append("")
        informe.append("Lista creada:")
        for e in maestro:
            informe.append(f"  - {e['visible']}")

        fuera = sorted(set(existentes) - visibles_master)
        if fuera:
            informe.append("")
            informe.append("ATENCIÓN: fichas existentes que NO están en el menú maestro actual:")
            for especie in fuera:
                idiomas = ",".join(sorted(existentes[especie]))
                informe.append(f"  - {genero} {especie} ({idiomas})")
        else:
            informe.append("")
            informe.append("Todas las fichas existentes aparecen en la lista maestra.")

        informe.append("")

    Path("informes/listas-maestras-menus.txt").write_text("\n".join(informe), encoding="utf-8")

    print("Archivos creados:")
    print("  fragmentos/menu-tuber.txt")
    print("  fragmentos/menu-terfezia.txt")
    print("  informes/listas-maestras-menus.txt")
    print("  herramientas/crear_listas_maestras_menus.py")
    print()
    print(Path("informes/listas-maestras-menus.txt").read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
