"""Gera documento.html e documento.pdf a partir de ../documento.md.

Uso: uv run --with markdown --with pypdf python build.py
Diagramas ainda não existem: os marcadores "[Diagrama N: ...]" viram caixas com altura reservada,
para medir o número real de páginas.
"""

import re
import subprocess
from pathlib import Path

import markdown
from pypdf import PdfReader

HERE = Path(__file__).parent
SRC = HERE.parent / "documento.md"
HTML = HERE / "documento.html"
PDF = HERE.parent / "Fabricio-Espel_Desafio-Arquiteto-Solucoes-IA_Assistente-Agentico.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DIAGRAMS = HERE.parent / "diagramas"

# Altura reservada por diagrama (mm), estimativa de diagramas compactos.
DIAGRAM_HEIGHT_MM = {"1": 70, "2": 90, "3": 60, "4": 70}

CSS = """
@page { size: A4; margin: 14mm 15mm 14mm 15mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9.5pt;
       line-height: 1.32; color: #1a1a1a; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 2pt; }
h2 { font-size: 12pt; margin: 9pt 0 3pt; padding-bottom: 1pt; border-bottom: 1px solid #ccc; }
h3 { font-size: 10pt; margin: 6pt 0 2pt; }
p { margin: 0 0 4pt; }
ul, ol { margin: 0 0 4pt; padding-left: 14pt; }
li { margin: 0 0 1.5pt; }
hr { display: none; }
table { border-collapse: collapse; width: 100%; margin: 3pt 0 5pt; font-size: 8.3pt; line-height: 1.25; }
th, td { border: 1px solid #d0d0d0; padding: 2pt 3.5pt; vertical-align: top; text-align: left; }
th { background: #f0f2f5; }
blockquote { margin: 3pt 0 5pt; padding: 3pt 6pt; background: #f6f7f9; border-left: 3px solid #8a94a6; }
blockquote p { margin: 0; }
code { font-size: 8.5pt; }
.svg { margin: 3pt 0 1pt; break-inside: avoid; }
.svg svg { display: block; width: 100%; height: auto; }
.cap { font-size: 8pt; color: #56607a; margin: 0 0 5pt; font-style: italic; }
a { color: #1f5fae; text-decoration: none; }
.diagram { border: 1.5px dashed #8a94a6; display: flex; align-items: center; justify-content: center;
           color: #56607a; font-size: 9pt; margin: 4pt 0 6pt; break-inside: avoid; }
"""


def diagram_boxes(html: str) -> str:
    """Troca o blockquote do marcador de diagrama por uma caixa de altura fixa."""
    pattern = re.compile(
        r"<blockquote>\s*<p><strong>\[Diagrama (\d+): ([^\]]+)\]</strong>(.*?)</p>\s*</blockquote>",
        re.S,
    )

    def repl(m: re.Match) -> str:
        n, title, rest = m.group(1), m.group(2), m.group(3).strip()
        caption = f'<p class="cap">Diagrama {n}: {title}.{" " + rest if rest else ""}</p>'
        svg = DIAGRAMS / f"diagrama-{n}.svg"
        if svg.exists():
            return f'<div class="svg">{svg.read_text(encoding="utf-8")}</div>{caption}'
        h = DIAGRAM_HEIGHT_MM.get(n, 70)
        return f'<div class="diagram" style="height:{h}mm">Diagrama {n}: {title}</div>{caption}'

    return pattern.sub(repl, html)


APPENDIX_BREAK = '<div style="break-before: page"></div>'


def render(md_text: str, html_path: Path, pdf_path: Path) -> int:
    body = diagram_boxes(markdown.markdown(md_text, extensions=["tables", "sane_lists"]))
    html_path.write_text(
        f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{CSS}</style></head>'
        f"<body>{body}</body></html>",
        encoding="utf-8",
    )
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True,
    )
    return len(PdfReader(pdf_path).pages)


def main() -> None:
    md_text = SRC.read_text(encoding="utf-8")
    total = render(md_text, HTML, PDF)
    corpo = render(md_text.split(APPENDIX_BREAK)[0], HERE / "_corpo.html", HERE / "_corpo.pdf")
    print(f"{PDF.name}: {total} páginas no total; corpo: {corpo} páginas; apêndice: {total - corpo}")


if __name__ == "__main__":
    main()
