from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS_FILE = ROOT / "estilos-generales.css"

BLOCK_ES = """<div class="busqueda-desplegable">
  <input type="checkbox" id="search-toggle" class="search-toggle">
  <label for="search-toggle" class="search-toggle-label" title="Buscar">
    <span class="icono-lupa"></span>
  </label>
  <form class="buscador-web" action="https://www.google.com/search" method="get">
    <label for="search-toggle" class="search-close" title="Cerrar">&#8592;</label>
    <input type="hidden" name="sitesearch" value="trufamania.com">
    <input type="text" name="q" value="" placeholder="Busca en este sitio web" title="Buscar en Trufamania">
    <input type="submit" value="Buscar" title="Buscar">
  </form>
</div>
"""

BLOCK_EN = """<div class="busqueda-desplegable">
  <input type="checkbox" id="search-toggle" class="search-toggle">
  <label for="search-toggle" class="search-toggle-label" title="Search">
    <span class="icono-lupa"></span>
  </label>
  <form class="buscador-web" action="https://www.google.com/search" method="get">
    <label for="search-toggle" class="search-close" title="Close">&#8592;</label>
    <input type="hidden" name="sitesearch" value="trufamania.com">
    <input type="text" name="q" value="" placeholder="Search this site" title="Search in Trufamania">
    <input type="submit" value="Search" title="Search">
  </form>
</div>
"""

CSS_BLOCK = """/* Buscador desplegable */
#cabecera {
  position: relative;
}

.busqueda-desplegable {
  position: absolute;
  right: 66px;
  top: 17px;
  display: flex;
  align-items: center;
  z-index: 20;
  color: #fff;
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
  width: 19px;
  height: 19px;
  border: 2.5px solid currentColor;
  border-radius: 50%;
  position: relative;
  background: transparent;
  box-sizing: border-box;
}

.icono-lupa:after {
  content: "";
  position: absolute;
  width: 10px;
  height: 2.5px;
  left: 13px;
  top: 15px;
  background: currentColor;
  border-radius: 2px;
  transform: rotate(45deg);
  transform-origin: left center;
}

.buscador-web {
  display: none;
}

.search-toggle:checked + .search-toggle-label + .buscador-web {
  display: flex;
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  width: 520px;
  max-width: calc(100% - 48px);
  height: 48px;
  align-items: center;
  box-sizing: border-box;
  padding: 0 14px;
  background: #fff;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.30);
  z-index: 9999;
}

.search-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 42px;
  margin-right: 10px;
  color: #666;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  text-decoration: none;
}

.buscador-web input[type="text"] {
  flex: 1;
  min-width: 0;
  height: 36px;
  padding: 0 4px;
  font-size: 16px;
  border: 0;
  outline: 0;
  background: transparent;
  color: #333;
}

.buscador-web input[type="submit"] {
  position: absolute;
  left: -9999px;
  width: 1px;
  height: 1px;
  overflow: hidden;
}

@media screen and (max-width: 700px) {
  .busqueda-desplegable {
    left: 16px;
    right: auto;
    top: auto;
    bottom: 11px;
  }

  .search-toggle-label {
    width: 30px;
    height: 30px;
  }

  .icono-lupa {
    width: 17px;
    height: 17px;
    border-width: 2.4px;
  }

  .icono-lupa:after {
    width: 9px;
    height: 2.4px;
    left: 12px;
    top: 13px;
  }

  .search-toggle:checked + .search-toggle-label + .buscador-web {
    top: 20px;
    left: 36px;
    right: 36px;
    transform: none;
    width: auto;
    max-width: none;
    height: 50px;
    padding: 0 12px;
  }

  .search-close {
    width: 28px;
    height: 42px;
    margin-right: 8px;
    font-size: 24px;
  }

  .buscador-web input[type="text"] {
    font-size: 15px;
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

block_re = re.compile(
    r'(?ms)^[ \t]*<div class="busqueda-desplegable">\r?\n.*?^[ \t]*</div>\r?\n?'
)

modified_html = 0
missing = []

for path in sorted(ROOT.glob("*.htm")):
    text = read_latin1(path)
    block = BLOCK_EN if is_english(text, path) else BLOCK_ES
    new_text, n = block_re.subn(block, text, count=1)
    if n:
        write_latin1(path, new_text)
        modified_html += 1
    elif 'id="cabecera-subtitulo"' in text:
        missing.append(path.name)

css_text = read_latin1(CSS_FILE)
marker = "/* Buscador desplegable */"
if marker not in css_text:
    raise SystemExit("No encuentro el bloque CSS del buscador.")

css_text = css_text[:css_text.index(marker)] + CSS_BLOCK + "\n"
write_latin1(CSS_FILE, css_text)

print(f"HTML actualizados: {modified_html}")
print("CSS actualizado: estilos-generales.css")
if missing:
    print("Con cabecera pero sin bloque de buscador:")
    for name in missing[:40]:
        print(" -", name)
