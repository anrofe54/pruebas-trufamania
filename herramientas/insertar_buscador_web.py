from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
CSS_FILE = ROOT / "estilos-generales.css"

FORM_ES = """<div class="busqueda-desplegable">
  <input type="checkbox" id="search-toggle" class="search-toggle">
  <label for="search-toggle" class="search-toggle-label" title="Buscar">
    <span class="icono-lupa"></span>
  </label>
  <form class="buscador-web" action="https://www.google.com/search" method="get">
    <input type="hidden" name="sitesearch" value="trufamania.com">
    <input type="text" name="q" value="" placeholder="Buscar..." title="Buscar en Trufamania">
    <input type="submit" value="OK" title="Buscar">
  </form>
</div>
"""

FORM_EN = """<div class="busqueda-desplegable">
  <input type="checkbox" id="search-toggle" class="search-toggle">
  <label for="search-toggle" class="search-toggle-label" title="Search">
    <span class="icono-lupa"></span>
  </label>
  <form class="buscador-web" action="https://www.google.com/search" method="get">
    <input type="hidden" name="sitesearch" value="trufamania.com">
    <input type="text" name="q" value="" placeholder="Search..." title="Search in Trufamania">
    <input type="submit" value="OK" title="Search">
  </form>
</div>
"""

CSS_BLOCK = """

/* Buscador desplegable */
#cabecera {
  position: relative;
}

.busqueda-desplegable {
  position: absolute;
  right: 62px;
  top: 18px;
  display: flex;
  align-items: center;
  z-index: 5;
  color: #111;
}

.search-toggle {
  display: none;
}

.search-toggle-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  cursor: pointer;
  background: transparent;
  border: 0;
  color: inherit;
}

.icono-lupa {
  display: inline-block;
  width: 17px;
  height: 17px;
  border: 3px solid currentColor;
  border-radius: 50%;
  position: relative;
  background: transparent;
  box-sizing: border-box;
}

.icono-lupa:after {
  content: "";
  position: absolute;
  width: 10px;
  height: 3px;
  background: currentColor;
  right: -8px;
  bottom: -5px;
  transform: rotate(45deg);
  transform-origin: left center;
}

.buscador-web {
  display: flex;
  align-items: center;
  overflow: hidden;
  width: 0;
  opacity: 0;
  margin-left: 0;
  transition: width 0.25s ease, opacity 0.2s ease, margin-left 0.25s ease;
  white-space: nowrap;
}

.buscador-web input[type="text"] {
  width: 150px;
  padding: 4px 6px;
  font-size: 13px;
  border: 1px solid #999;
  border-radius: 3px 0 0 3px;
}

.buscador-web input[type="submit"] {
  padding: 4px 7px;
  font-size: 12px;
  border: 1px solid #999;
  border-left: 0;
  background: #eee;
  cursor: pointer;
  border-radius: 0 3px 3px 0;
}

.buscador-web input[type="submit"]:hover {
  background: #ddd;
}

.search-toggle:checked + .search-toggle-label + .buscador-web {
  width: 210px;
  opacity: 1;
  margin-left: 8px;
}

@media screen and (max-width: 700px) {
  .busqueda-desplegable {
    position: static;
    margin: 8px auto 0 auto;
    justify-content: center;
    width: fit-content;
  }

  .search-toggle:checked + .search-toggle-label + .buscador-web {
    width: 7px;
  font-size: 12px;
  border: 1px solid #999;
  border-left: 0;
  background: #eee;
  cursor: pointer;
  border-radius: 0 3px 3px 0;
}

.buscador-web input[type="submit"]:hover {
  background: #ddd;
}

.search-toggle:checked + .search-toggle-label + .buscador-web {
  width: 210px;
  opacity: 1;
  margin-left: 8px;
}

@media screen and (max-width: 700px) {
  .busqueda-desplegable {
    position: static;
    margin: 8px auto 0 auto;
    justify-content: center;
    width: fit-content;
 190px;
  }

  .buscador-web input[type="text"] {
    width: 130px;
  }
}
"""

def read_latin1(path):
    return path.read_text(encoding="iso-8859-1")

def write_latin1(path, text):
    path.write_text(text, encoding="iso-8859-1", newline="")

def is_english(text, path):
    name = path.name.lower()
    return (
        '<html lang="en"' in text.lower()
        or 'shadowbox.init({language: "en"' in text.lower()
        or " english.htm" in name
    )

def insert_form(text, path):
    if 'class="busqueda-desplegable"' in text or 'class="buscador-web"' in text:
        return text, "ya tenia buscador"

    lines = text.splitlines(keepends=True)
    form = FORM_EN if is_english(text, path) else FORM_ES

    for i, line in enumerate(lines):
        if 'id="cabecera-subtitulo"' in line:
            indent = line[:len(line) - len(line.lstrip())]
            form_indented = "".join(indent + x if x.strip() else x for x in form.splitlines(True))
            lines.insert(i + 1, form_indented)
            return "".join(lines), "modificado"

    return text, "sin cabecera"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="aplica los cambios")
    args = parser.parse_args()

    html_files = sorted(ROOT.glob("*.htm"))

    modified = []
    already = []
    no_header = []

    for path in html_files:
        text = read_latin1(path)
        new_text, status = insert_form(text, path)

        if status == "modificado":
            modified.append(path.name)
            if args.apply:
                write_latin1(path, new_text)
        elif status == "ya tenia buscador":
            already.append(path.name)
        else:
            no_header.append(path.name)

    css_changed = False
    if CSS_FILE.exists():
        css_text = read_latin1(CSS_FILE)
        if ".busqueda-desplegable" not in css_text and ".icono-lupa" not in css_text:
            css_changed = True
            if args.apply:
                write_latin1(CSS_FILE, css_text.rstrip() + CSS_BLOCK + "\n")
    else:
        print("AVISO: no encuentro estilos-generales.css")

    modo = "APLICADO" if args.apply else "SIMULACION"
    print(f"Modo: {modo}")
    print(f"HTML que se modificarian: {len(modified)}")
    print(f"HTML que ya tenian buscador: {len(already)}")
    print(f"HTML sin cabecera reconocida: {len(no_header)}")
    print(f"CSS {'se modificaria' if css_changed else 'no necesita cambios'}: estilos-generales.css")

    if no_header:
        print("\\nArchivos sin cabecera reconocida:")
        for name in no_header[:50]:
            print(" -", name)

    if modified:
        print("\\nPrimeros archivos a modificar:")
        for name in modified[:30]:
            print(" -", name)
        if len(modified) > 30:
            print(f" ... y {len(modified) - 30} mas")

if __name__ == "__main__":
    main()
