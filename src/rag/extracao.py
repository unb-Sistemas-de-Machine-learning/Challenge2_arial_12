"""Extração das linhas de texto dos PDFs oficiais com PyMuPDF (issue #11).

Cada linha guarda o texto bruto e os atributos tipográficos (tamanho da fonte e
negrito) que a etapa de seções usa para reconhecer títulos.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pymupdf

_NEGRITO = 1 << 4  # flag de negrito do PyMuPDF
_FONTES_NEGRITO = ("bold", "semibold", "black", "heavy", "extrabold", "ultra")


@dataclass(frozen=True)
class Linha:
    texto: str
    pagina: int
    tamanho: float
    negrito: bool
    # Centro da linha em relação à página (0 = topo/esquerda, 1 = rodapé/direita).
    y_relativo: float = 0.5
    x_relativo: float = 0.5
    # Texto girado (ex.: cabeçalho corrido na lateral da página).
    horizontal: bool = True


def _span_negrito(span: dict) -> bool:
    fonte = span.get("font", "").lower()
    return bool(span.get("flags", 0) & _NEGRITO) or any(
        marca in fonte for marca in _FONTES_NEGRITO
    )


def _linha(linha: dict, pagina: int, largura: float, altura: float) -> Linha | None:
    spans = linha["spans"]
    texto = "".join(s["text"] for s in spans)
    if not texto.strip():
        return None
    visiveis = [s for s in spans if s["text"].strip()]
    pesos: Counter[float] = Counter()
    for span in visiveis:
        pesos[round(span["size"], 1)] += len(span["text"].strip())
    x0, y0, x1, y1 = linha["bbox"]
    return Linha(
        texto=texto,
        pagina=pagina,
        tamanho=pesos.most_common(1)[0][0],
        negrito=all(_span_negrito(s) for s in visiveis),
        y_relativo=round(((y0 + y1) / 2) / altura, 3) if altura else 0.5,
        x_relativo=round(((x0 + x1) / 2) / largura, 3) if largura else 0.5,
        horizontal=abs(linha.get("dir", (1.0, 0.0))[0]) > 0.99,
    )


def extrair_linhas(caminho: Path, paginas: Iterable[int]) -> list[Linha]:
    """Lê as linhas das páginas indicadas (numeradas a partir de 1), em ordem."""
    linhas: list[Linha] = []
    with pymupdf.open(caminho) as documento:
        for numero in paginas:
            pagina = documento[numero - 1]
            largura, altura = pagina.rect.width, pagina.rect.height
            for bloco in pagina.get_text("dict")["blocks"]:
                for linha in bloco.get("lines", []):
                    extraida = _linha(linha, numero, largura, altura)
                    if extraida is not None:
                        linhas.append(extraida)
    return linhas


def total_paginas(caminho: Path) -> int:
    with pymupdf.open(caminho) as documento:
        return documento.page_count
