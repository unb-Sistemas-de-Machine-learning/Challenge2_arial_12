"""Limpeza de ruído e remontagem de parágrafos (issue #11).

Etapas:

1. ``remover_ruido``: tira cabeçalhos e rodapés repetidos, números de página,
   texto miúdo de figuras e carimbos do SEI.
2. ``juntar_paragrafos``: junta as linhas em parágrafos e itens de lista,
   tratando hifenização de fim de linha e quebras de página.
3. ``descartar_boilerplate``: tira blocos sem valor clínico, como as
   assinaturas eletrônicas das notas técnicas.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from src.rag.extracao import Linha

# Texto de figuras e fluxogramas sai em fonte miúda e fora de ordem.
TAMANHO_MINIMO = 5.0
# Uma linha curta, na margem superior ou inferior, que se repete em muitas
# páginas é cabeçalho ou rodapé. Repetições no corpo (como "Dose: 0,5 mL." ou
# o subtítulo "Contraindicações" de cada vacina) são conteúdo e ficam.
FRACAO_REPETICAO = 0.3
MIN_PAGINAS_REPETICAO = 3
MAX_CARACTERES_CABECALHO = 120
MARGEM = 0.1

_LIGADURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_HIFEN_SUAVE = "­"

# Ruído reconhecível em qualquer posição da página.
_RUIDO_LINHA = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^\d{2}/\d{2}/\d{4},? \d{2}:\d{2}\s+SEI/MS",  # cabeçalho de impressão do SEI
        r"^https?://sei\.saude\.gov\.br",
        r"SEI \d{5}\.\d{6}/\d{4}-\d{2}\s*/\s*pg\.\s*\d+",  # rodapé do SEI
        r"\bp[áa]gina \d+ de \d+$",
    )
]
# Ruído só quando está na margem (no corpo, pode ser célula de tabela).
_RUIDO_MARGEM = [re.compile(r"^\d{1,3}$"), re.compile(r"^\d+/\d+$")]

_BOILERPLATE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"documento assinado eletronicamente por",
        r"a autenticidade deste documento pode ser conferida",
        r"acao=documento_conferir",
        r"informando o c[óo]digo verificador",
        r"^refer[êe]ncia: processo n",
    )
]

MARCADOR_LISTA = re.compile(
    r"^\s*(?:[•●▪◦■□➢✓\-–]\s+|[a-z][\.\)]\s+|\d{1,2}(?:\.\d{1,2})*[\.\)]?\s+(?=\S))"
)
_FIM_DE_FRASE = re.compile(r"[\.!?;:]\s*[\"”')\]]?$")
_INICIO_DE_FRASE = re.compile(r"^[\"“'(\[]?[A-ZÁÉÍÓÚÂÊÔÃÕÀÇ0-9]")


# Glifos de marcador mal mapeados encontrados no corpus (ex.: protocolo de dengue).
_MARCADORES_MAL_MAPEADOS = {"ࡿ"}


def _marcador(caractere: str) -> str:
    # Fontes de símbolos (Wingdings etc.) saem como caracteres de controle ou
    # de uso privado; nos PDFs do corpus eles são marcadores de lista.
    if caractere in "\t\n\r":
        return " "
    if caractere in _MARCADORES_MAL_MAPEADOS or unicodedata.category(caractere) in (
        "Cc",
        "Co",
    ):
        return "• "
    return caractere


def normalizar_texto(texto: str) -> str:
    """NFC, sem hífen suave, sem ligaduras e com espaços colapsados."""
    texto = unicodedata.normalize("NFC", texto).replace(_HIFEN_SUAVE, "")
    for ligadura, letras in _LIGADURAS.items():
        texto = texto.replace(ligadura, letras)
    texto = "".join(_marcador(c) for c in texto)
    texto = re.sub(r"(?:•\s*){2,}", "• ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _chave_repeticao(texto: str) -> str:
    return re.sub(r"\d+", "#", normalizar_texto(texto).lower())


def _na_margem(linha: Linha) -> bool:
    return (
        not linha.horizontal
        or not MARGEM <= linha.y_relativo <= 1 - MARGEM
        or not MARGEM <= linha.x_relativo <= 1 - MARGEM
    )


def remover_ruido(linhas: list[Linha]) -> list[Linha]:
    """Remove linhas de ruído, mantendo a ordem das demais."""
    paginas_por_chave: dict[str, set[int]] = defaultdict(set)
    for linha in linhas:
        if _na_margem(linha):
            paginas_por_chave[_chave_repeticao(linha.texto)].add(linha.pagina)
    n_paginas = len({linha.pagina for linha in linhas}) or 1
    limite = max(MIN_PAGINAS_REPETICAO, FRACAO_REPETICAO * n_paginas)

    limpas: list[Linha] = []
    for linha in linhas:
        texto = normalizar_texto(linha.texto)
        if not texto or linha.tamanho < TAMANHO_MINIMO:
            continue
        if any(p.search(texto) for p in _RUIDO_LINHA):
            continue
        if _na_margem(linha):
            if any(p.search(texto) for p in _RUIDO_MARGEM):
                continue
            repetida = len(paginas_por_chave[_chave_repeticao(linha.texto)]) >= limite
            if repetida and len(texto) <= MAX_CARACTERES_CABECALHO:
                continue
        limpas.append(linha)
    return limpas


@dataclass
class Paragrafo:
    texto: str
    pagina: int
    tamanho: float
    negrito: bool
    candidato_titulo: bool = False


def parece_subtitulo(linha: Linha, seguinte: Linha | None) -> bool:
    """Linha curta em negrito, sem pontuação final, seguida de frase ou lista."""
    texto = normalizar_texto(linha.texto)
    if seguinte is None:
        return False
    proximo = normalizar_texto(seguinte.texto)
    return (
        linha.negrito
        and 0 < len(texto) <= 80
        and not re.search(r"[\.,;:]$", texto)
        and bool(_INICIO_DE_FRASE.match(texto))
        and (
            bool(_INICIO_DE_FRASE.match(proximo)) or bool(MARCADOR_LISTA.match(proximo))
        )
    )


def _juntar(anterior: str, atual: str) -> str:
    bruto = anterior.rstrip()
    if bruto.endswith(_HIFEN_SUAVE):
        return bruto[:-1] + atual.lstrip()
    if bruto.endswith("-") and atual[:1].islower():
        return bruto + atual.lstrip()
    return bruto + " " + atual.lstrip()


def juntar_paragrafos(
    linhas: list[Linha],
    titulo: Iterable[bool] | None = None,
    detectar_subtitulos: bool = True,
    quebra: Iterable[bool] | None = None,
) -> list[Paragrafo]:
    """Junta linhas em parágrafos.

    ``titulo`` marca, linha a linha, as que a estratégia de seções já sabe que
    são títulos; um título sempre forma um parágrafo próprio, exceto quando a
    linha seguinte é a continuação do mesmo título (mesmo tamanho e negrito).
    Com ``detectar_subtitulos``, linhas curtas em negrito também viram títulos
    (útil em bulas; em protocolos, onde células de tabela são negritas, não).
    ``quebra`` força um novo parágrafo na linha marcada (ex.: um subtítulo logo
    depois de outro título do mesmo tamanho).
    """
    marcas = list(titulo) if titulo is not None else [False] * len(linhas)
    quebras = list(quebra) if quebra is not None else [False] * len(linhas)
    paragrafos: list[Paragrafo] = []
    brutos: list[str] = []  # texto bruto acumulado de cada parágrafo

    for i, linha in enumerate(linhas):
        seguinte = linhas[i + 1] if i + 1 < len(linhas) else None
        eh_titulo = marcas[i] or (
            detectar_subtitulos and parece_subtitulo(linha, seguinte)
        )
        texto = normalizar_texto(linha.texto)
        anterior = linhas[i - 1] if i else None
        novo = (
            anterior is None
            or quebras[i]
            or abs(linha.tamanho - anterior.tamanho) > 1.0
            or eh_titulo != paragrafos[-1].candidato_titulo
            or bool(MARCADOR_LISTA.match(texto))
            or (
                bool(_FIM_DE_FRASE.search(normalizar_texto(anterior.texto)))
                and bool(_INICIO_DE_FRASE.match(texto))
            )
        )
        if novo:
            paragrafos.append(
                Paragrafo(
                    texto="",
                    pagina=linha.pagina,
                    tamanho=linha.tamanho,
                    negrito=linha.negrito,
                    candidato_titulo=eh_titulo,
                )
            )
            brutos.append(linha.texto)
        else:
            brutos[-1] = _juntar(brutos[-1], linha.texto)

    for paragrafo, bruto in zip(paragrafos, brutos, strict=True):
        paragrafo.texto = normalizar_texto(bruto)
    return [p for p in paragrafos if p.texto]


def descartar_boilerplate(paragrafos: list[Paragrafo]) -> list[Paragrafo]:
    return [p for p in paragrafos if not any(r.search(p.texto) for r in _BOILERPLATE)]


_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


def eh_fragmento(paragrafo: Paragrafo) -> bool:
    """Célula de tabela ou rótulo de figura sem nenhuma palavra (ex.: "CQ CQ 15 15")."""
    return not paragrafo.candidato_titulo and not _PALAVRA.search(paragrafo.texto)
