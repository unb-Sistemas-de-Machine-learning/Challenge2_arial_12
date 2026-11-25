"""Atribuição de seção, título, entidade e público-alvo a cada parágrafo (issue #11).

A estratégia depende da categoria do documento:

* **Bulas** (``bula_medicamento`` e ``bula_vacina``): as 9 perguntas da
  RDC nº 47/2009 definem a seção. Só entram as perguntas 1 (indicações),
  3 (contraindicações) e 4 (advertências, com os subtítulos de gravidez e de
  interações). As demais (como posologia) ficam de fora: o sistema não prescreve.
* **Protocolos clínicos**: títulos reconhecidos pelo tamanho da fonte.
* **Notas técnicas** (SEI): títulos curtos em negrito ("ASSUNTO", "ORIENTAÇÕES").
* **Calendário vacinal**: cada vacina ("13. Vacina febre amarela") define a
  entidade, e os subtítulos fixos de cada vacina ("Indicação", "Esquema de
  vacinação", "Contraindicações"...) definem a seção.

Em protocolos e notas técnicas, os títulos são mapeados para seções pelas
``regras_secao`` do catálogo, e um parágrafo com linguagem de contraindicação
("não utilizar", "contraindicado") passa para ``contraindicacoes`` mesmo dentro
de uma seção de manejo. A entidade vem das ``regras_entidade`` do catálogo.
Toda reclassificação e todo descarte ficam registrados na auditoria.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

from src.agents.schemas import PublicoAlvo
from src.rag.catalogo import Fonte
from src.rag.extracao import Linha, extrair_linhas, total_paginas
from src.rag.limpeza import (
    Paragrafo,
    descartar_boilerplate,
    eh_fragmento,
    juntar_paragrafos,
    normalizar_texto,
    remover_ruido,
)

ORDEM_PUBLICO = list(get_args(PublicoAlvo))
SEPARADOR_TITULOS = " > "

_PUBLICO_POR_PALAVRA = {
    "gestante": re.compile(
        r"\bgestant|\bgr[áa]vid|\bgravidez|\bgesta[çc][ãa]o", re.IGNORECASE
    ),
    "lactante": re.compile(
        r"\blactant|\bamamenta|\baleitamento|\blacta[çc][ãa]o", re.IGNORECASE
    ),
    "idoso": re.compile(r"\bidos[oa]s?\b", re.IGNORECASE),
    "imunossuprimido": re.compile(
        r"imunossupr|imunodeprim|imunocomprometid", re.IGNORECASE
    ),
}

CONTRAINDICACAO = re.compile(
    r"contraindica|contra-indica|contra indica"
    r"|\bn[ãa]o (?:se deve |devem? )?(?:utilizar|usar|administrar|tomar)\b(?! doses?\b)"
    r"|\bn[ãa]o devem? ser (?:utilizad|usad|administrad|aplicad|vacinad)"
    r"|\bdevem? ser evitad|\bevitar o uso",
    re.IGNORECASE,
)
# "não são contraindicadas" afirma que algo é permitido.
_CONTRAINDICACAO_NEGADA = re.compile(
    r"\bn[ãa]o (?:s[ãa]o|[ée]|est[áa]o?|h[áa]) (?:formalmente )?contra-?\s?indica\w*"
    r"|\b(?:n[ãa]o tenham?|n[ãa]o houver|sem|aus[êe]ncia de) contra-?\s?indica\w*",
    re.IGNORECASE,
)
_TITULO_DE_ANEXO = re.compile(r"^(AP[ÊE]NDICE|ANEXO)\b", re.IGNORECASE)


def menciona_contraindicacao(texto: str) -> bool:
    return bool(CONTRAINDICACAO.search(_CONTRAINDICACAO_NEGADA.sub(" ", texto)))


@dataclass
class Bloco:
    texto: str
    pagina: int
    secao: str
    titulo_secao: str
    publico_alvo: list[str]
    entidade: str | None = None


@dataclass
class Auditoria:
    descartados: list[dict] = field(default_factory=list)
    reclassificados: list[dict] = field(default_factory=list)

    def descartar(self, paragrafo: Paragrafo, motivo: str) -> None:
        self.descartados.append(
            {
                "pagina": paragrafo.pagina,
                "motivo": motivo,
                "trecho": paragrafo.texto[:160],
            }
        )

    def reclassificar(self, paragrafo: Paragrafo, de: str, para: str) -> None:
        self.reclassificados.append(
            {
                "pagina": paragrafo.pagina,
                "de": de,
                "para": para,
                "trecho": paragrafo.texto[:160],
            }
        )


def publico_alvo(fonte: Fonte, *textos: str) -> list[str]:
    """Público padrão do documento mais o que os textos mencionam."""
    publico = set(fonte.publico_alvo)
    conteudo = " ".join(textos)
    for valor, padrao in _PUBLICO_POR_PALAVRA.items():
        if padrao.search(conteudo):
            publico.add(valor)
    return [p for p in ORDEM_PUBLICO if p in publico]


def entidade_por_titulos(fonte: Fonte, titulos: list[str]) -> str | None:
    """Entidade do título mais interno que casar com as regras do catálogo."""
    for titulo in reversed(titulos):
        for regra in fonte.regras_entidade:
            if re.search(regra.padrao, titulo, re.IGNORECASE):
                return regra.entidade
    return None


def _entidade_no_inicio(fonte: Fonte, texto: str) -> str | None:
    for regra in fonte.regras_entidade:
        if re.match(regra.padrao, texto, re.IGNORECASE):
            return regra.entidade
    return None


def _bloco(
    fonte: Fonte,
    p: Paragrafo,
    secao: str,
    titulos: list[str],
    entidade: str | None = None,
) -> Bloco:
    titulo = SEPARADOR_TITULOS.join(titulos)
    return Bloco(
        texto=p.texto,
        pagina=p.pagina,
        secao=secao,
        titulo_secao=titulo,
        publico_alvo=publico_alvo(fonte, titulo, p.texto),
        entidade=entidade,
    )


def _salto_de_pagina(anterior: int | None, atual: int) -> bool:
    """Páginas não contíguas: o intervalo do catálogo pulou um trecho do PDF."""
    return anterior is not None and atual > anterior + 1


# --- Bulas (RDC nº 47/2009) --------------------------------------------------

_PERGUNTAS_RDC: list[tuple[re.Pattern[str], str | None]] = [
    (re.compile(p, re.IGNORECASE), secao)
    for p, secao in (
        (r"^(\d\.?\s*)?PARA QUE ESTE MEDICAMENTO", "indicacoes"),
        (r"^(\d\.?\s*)?COMO ESTE MEDICAMENTO FUNCIONA", None),
        (r"^(\d\.?\s*)?QUANDO N[ÃA]O DEVO USAR", "contraindicacoes"),
        (r"^(\d\.?\s*)?O QUE DEVO SABER ANTES", "advertencias_e_precaucoes"),
        (r"^(\d\.?\s*)?ONDE,? COMO E POR QUANTO TEMPO", None),
        (r"^(\d\.?\s*)?COMO DEVO USAR", None),
        (r"^(\d\.?\s*)?O QUE DEVO FAZER QUANDO EU ME ESQUECER", None),
        (r"^(\d\.?\s*)?QUAIS OS MALES", None),
        (r"^(\d\.?\s*)?O QUE FAZER SE ALGU[ÉE]M USAR", None),
    )
]
_TITULOS_FORA_DA_BULA = re.compile(
    r"^(I+\)\s*)?(APRESENTA|COMPOSI|DIZERES LEGAIS|IDENTIFICA[ÇC][ÃA]O"
    r"|INFORMA[ÇC][ÕO]ES AO PACIENTE|VIA DE ADMINISTRA|USO (ADULTO|PEDI))",
    re.IGNORECASE,
)
_SUB_GRAVIDEZ = re.compile(
    r"gravidez|gestant|gesta[çc]|lacta|amamenta|aleitamento", re.IGNORECASE
)
_SUB_INTERACAO = re.compile(r"intera[çc]", re.IGNORECASE)
# Rótulo no início do parágrafo ("Uso em idosos: ..."): abre um novo assunto
# dentro das advertências, mesmo sem subtítulo em linha própria.
_ROTULO_INICIAL = re.compile(r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^:.;]{2,60}):\s")


def _subsecao_advertencia(titulo: str) -> str:
    if _SUB_GRAVIDEZ.search(titulo):
        return "gravidez_e_lactacao"
    if _SUB_INTERACAO.search(titulo):
        return "interacoes_medicamentosas"
    return "advertencias_e_precaucoes"


def _maiusculo(texto: str) -> bool:
    letras = [c for c in texto if c.isalpha()]
    return bool(letras) and sum(c.isupper() for c in letras) / len(letras) >= 0.7


def _pergunta_rdc(paragrafo: Paragrafo) -> tuple[bool, str | None]:
    if not _maiusculo(paragrafo.texto):
        return False, None
    for padrao, secao in _PERGUNTAS_RDC:
        if padrao.match(paragrafo.texto):
            return True, secao
    return False, None


def segmentar_bula(
    fonte: Fonte, paragrafos: list[Paragrafo], auditoria: Auditoria
) -> list[Bloco]:
    blocos: list[Bloco] = []
    secao_pergunta: str | None = None  # None: fora das perguntas indexadas
    secao_atual: str | None = None
    titulos: list[str] = []
    for p in paragrafos:
        eh_pergunta, secao = _pergunta_rdc(p)
        if eh_pergunta:
            secao_pergunta = secao_atual = secao
            titulos = [p.texto]
            continue
        if (
            p.candidato_titulo
            and _maiusculo(p.texto)
            and _TITULOS_FORA_DA_BULA.match(p.texto)
        ):
            secao_pergunta = secao_atual = None
            titulos = []
            continue
        if secao_pergunta is None:
            auditoria.descartar(p, "fora das perguntas 1, 3 e 4 da RDC 47/2009")
            continue
        if p.candidato_titulo:
            titulos = titulos[:1] + [p.texto]
            if secao_pergunta == "advertencias_e_precaucoes":
                secao_atual = _subsecao_advertencia(p.texto)
            continue
        rotulo = _ROTULO_INICIAL.match(p.texto)
        if rotulo and secao_pergunta == "advertencias_e_precaucoes":
            nova = _subsecao_advertencia(rotulo.group(1))
            # Rótulo de gravidez ou de interação abre essa subseção. Um rótulo
            # generico só encerra o subtítulo de gravidez ("Uso em idosos: ..."
            # depois de "Gravidez e Amamentação"); dentro de interações,
            # "Medicamento-alimentos: ..." continua sendo interação.
            generico_fora_da_gravidez = (
                nova == "advertencias_e_precaucoes"
                and secao_atual != "gravidez_e_lactacao"
            )
            if nova != secao_atual and not generico_fora_da_gravidez:
                secao_atual, titulos = nova, titulos[:1]
        blocos.append(_bloco(fonte, p, secao_atual or secao_pergunta, titulos))
    return blocos


# --- Protocolos e notas técnicas (hierarquia de títulos) ---------------------

DIFERENCA_TITULO = 1.5


def tamanho_corpo(linhas: list[Linha]) -> float:
    pesos: Counter[float] = Counter()
    for linha in linhas:
        pesos[round(linha.tamanho * 2) / 2] += len(linha.texto)
    return pesos.most_common(1)[0][0]


def _niveis(tamanhos: list[float]) -> dict[float, int]:
    """Agrupa tamanhos de título próximos (até 1 pt) num mesmo nível."""
    niveis: dict[float, int] = {}
    nivel, anterior = -1, None
    for tamanho in sorted(set(tamanhos), reverse=True):
        if anterior is None or anterior - tamanho > 1.0:
            nivel += 1
        niveis[tamanho] = nivel
        anterior = tamanho
    return niveis


def _secao_por_regras(fonte: Fonte, titulos: list[str]) -> str | None:
    for titulo in reversed(titulos):  # do título mais interno ao mais geral
        for regra in fonte.regras_secao:
            if re.search(regra.padrao, titulo, re.IGNORECASE):
                return regra.secao
    return fonte.secao_padrao


def segmentar_por_titulos(
    fonte: Fonte, paragrafos: list[Paragrafo], auditoria: Auditoria
) -> list[Bloco]:
    niveis = _niveis([p.tamanho for p in paragrafos if p.candidato_titulo])
    pilha: list[tuple[int, str]] = []
    blocos: list[Bloco] = []
    anterior_titulo = False
    ultima_pagina: int | None = None
    entidade_paragrafo: str | None = None  # vale até o próximo título
    for p in paragrafos:
        if _salto_de_pagina(ultima_pagina, p.pagina):
            pilha, entidade_paragrafo = [], None
        ultima_pagina = p.pagina
        if p.candidato_titulo:
            if p.texto.isdigit():
                continue  # número de capítulo em destaque, sem título
            anexo = bool(_TITULO_DE_ANEXO.match(p.texto))
            # Apêndices e anexos ficam acima da hierarquia dos capítulos: os
            # títulos seguintes, mesmo do mesmo tamanho, ficam dentro deles.
            nivel = -1 if anexo else niveis[p.tamanho]
            continuacao = (
                anterior_titulo
                and pilha
                and pilha[-1][0] == nivel
                and not anexo
                and not re.match(r"^\d", p.texto)
            )
            if continuacao:
                # Título quebrado em duas linhas seguidas.
                pilha[-1] = (nivel, f"{pilha[-1][1]} {p.texto}")
            else:
                while pilha and pilha[-1][0] >= nivel:
                    pilha.pop()
                pilha.append((nivel, p.texto))
            anterior_titulo, entidade_paragrafo = True, None
            continue
        anterior_titulo = False
        if not pilha:
            auditoria.descartar(p, "texto antes do primeiro título processado")
            continue
        titulos = [t for _, t in pilha]
        secao = _secao_por_regras(fonte, titulos)
        if secao is None or secao == "descartar":
            auditoria.descartar(
                p, f"seção descartada: {SEPARADOR_TITULOS.join(titulos)}"
            )
            continue
        if secao != "contraindicacoes" and menciona_contraindicacao(p.texto):
            auditoria.reclassificar(p, secao, "contraindicacoes")
            secao = "contraindicacoes"
        entidade_paragrafo = _entidade_no_inicio(fonte, p.texto) or entidade_paragrafo
        entidade = entidade_paragrafo or entidade_por_titulos(fonte, titulos)
        blocos.append(_bloco(fonte, p, secao, titulos, entidade))
    return blocos


def _marcar_titulos_por_fonte(linhas: list[Linha]) -> list[bool]:
    limiar = tamanho_corpo(linhas) + DIFERENCA_TITULO
    return [linha.tamanho >= limiar and len(linha.texto) <= 200 for linha in linhas]


# --- Calendário Nacional de Vacinação ----------------------------------------

_VACINA = re.compile(r"^\d{1,2}\.\s+Vacina\b", re.IGNORECASE)
_INFORMACOES_GERAIS = re.compile(r"^Informa[çc][õo]es Gerais$", re.IGNORECASE)
_SUBTITULOS_CALENDARIO: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p + r"[\.:]?$", re.IGNORECASE), secao)
    for p, secao in (
        (r"^Indica[çc][ãa]o", "indicacoes"),
        (r"^Idade para vacina[çc][ãa]o e/ou grupo recomendado", "esquema_vacinal"),
        (r"^Esquema de vacina[çc][ãa]o", "esquema_vacinal"),
        (r"^Dose", "esquema_vacinal"),
        (r"^Via de administra[çc][ãa]o", "esquema_vacinal"),
        (r"^Precau[çc][õo]es(/Orienta[çc][õo]es)?", "advertencias_e_precaucoes"),
        (r"^Contraindica[çc][õo]es", "contraindicacoes"),
        (
            r"^Recomenda[çc][õo]es sobre administra[çc][ãa]o simult[âa]nea.*",
            "esquema_vacinal",
        ),
    )
]


def _subtitulo_calendario(texto: str) -> str | None:
    for padrao, secao in _SUBTITULOS_CALENDARIO:
        if padrao.match(texto):
            return secao
    return None


def _quebras_calendario(linhas: list[Linha]) -> list[bool]:
    """Nome de vacina e subtítulos sempre abrem parágrafo próprio."""
    return [
        bool(_VACINA.match(t) or _INFORMACOES_GERAIS.match(t))
        or _subtitulo_calendario(t) is not None
        for t in (normalizar_texto(linha.texto) for linha in linhas)
    ]


def _marcar_titulos_calendario(linhas: list[Linha]) -> list[bool]:
    marcas: list[bool] = []
    for i, linha in enumerate(linhas):
        texto = normalizar_texto(linha.texto)
        vacina = linha.negrito and bool(_VACINA.match(texto))
        # Nome de vacina longo, quebrado em duas linhas em negrito.
        continuacao = (
            i > 0
            and marcas[-1]
            and _VACINA.match(normalizar_texto(linhas[i - 1].texto))
            and linha.negrito
            and linha.tamanho == linhas[i - 1].tamanho
            and not _subtitulo_calendario(texto)
        )
        marcas.append(
            vacina
            or bool(continuacao)
            or bool(_INFORMACOES_GERAIS.match(texto))
            or _subtitulo_calendario(texto) is not None
        )
    return marcas


def segmentar_calendario(
    fonte: Fonte, paragrafos: list[Paragrafo], auditoria: Auditoria
) -> list[Bloco]:
    blocos: list[Bloco] = []
    vacina: str | None = None
    entidade: str | None = None
    secao: str | None = None
    subtitulo: str | None = None
    ultima_pagina: int | None = None
    for p in paragrafos:
        if _salto_de_pagina(ultima_pagina, p.pagina):
            vacina = entidade = secao = subtitulo = None
        ultima_pagina = p.pagina
        if p.candidato_titulo:
            sub = _subtitulo_calendario(p.texto)
            if sub is not None and vacina is not None:
                secao, subtitulo = sub, p.texto.rstrip(".:")
            elif _VACINA.match(p.texto) or _INFORMACOES_GERAIS.match(p.texto):
                vacina = re.sub(r"\s+", " ", p.texto)
                entidade = entidade_por_titulos(fonte, [vacina])
                geral = bool(_INFORMACOES_GERAIS.match(p.texto))
                secao = "condutas_gerais" if geral else fonte.secao_padrao
                subtitulo = None
            elif vacina is not None:
                vacina = f"{vacina} {p.texto}"  # continuação do nome da vacina
                entidade = entidade_por_titulos(fonte, [vacina])
            continue
        if vacina is None:
            auditoria.descartar(p, "texto antes do primeiro título processado")
            continue
        if secao is None:
            auditoria.descartar(p, f"sem subtítulo reconhecido em {vacina}")
            continue
        titulos = [vacina] + ([subtitulo] if subtitulo else [])
        blocos.append(_bloco(fonte, p, secao, titulos, entidade))
    return blocos


# --- Orquestração --------------------------------------------------------------

Estrategia = Callable[[Fonte, list[Paragrafo], Auditoria], list[Bloco]]


@dataclass(frozen=True)
class _Estrategia:
    segmentar: Estrategia
    marcar_titulos: Callable[[list[Linha]], list[bool]] | None = None
    subtitulos_em_negrito: bool = True
    quebrar: Callable[[list[Linha]], list[bool]] | None = None


_ESTRATEGIAS: dict[str, _Estrategia] = {
    "bula_medicamento": _Estrategia(segmentar_bula),
    "bula_vacina": _Estrategia(segmentar_bula),
    "protocolo_clinico": _Estrategia(
        segmentar_por_titulos, _marcar_titulos_por_fonte, subtitulos_em_negrito=False
    ),
    "nota_tecnica": _Estrategia(segmentar_por_titulos),
    "calendario_vacinal": _Estrategia(
        segmentar_calendario,
        _marcar_titulos_calendario,
        subtitulos_em_negrito=False,
        quebrar=_quebras_calendario,
    ),
}
CATEGORIAS_SUPORTADAS = frozenset(_ESTRATEGIAS)


class EstrategiaIndisponivel(Exception):
    """A categoria do documento ainda não tem estratégia de seções."""


def processar_fonte(fonte: Fonte, dir_raw: Path) -> tuple[list[Bloco], Auditoria]:
    """Extrai, limpa e segmenta um documento do catálogo."""
    if fonte.categoria not in _ESTRATEGIAS:
        raise EstrategiaIndisponivel(
            f"{fonte.doc_id}: categoria {fonte.categoria} ainda sem estratégia de seções."
        )
    estrategia = _ESTRATEGIAS[fonte.categoria]
    caminho = dir_raw / fonte.arquivo
    linhas = remover_ruido(
        extrair_linhas(caminho, fonte.paginas_processadas(total_paginas(caminho)))
    )
    marcas = estrategia.marcar_titulos(linhas) if estrategia.marcar_titulos else None
    quebras = estrategia.quebrar(linhas) if estrategia.quebrar else None
    paragrafos = descartar_boilerplate(
        juntar_paragrafos(linhas, marcas, estrategia.subtitulos_em_negrito, quebras)
    )
    auditoria = Auditoria()
    uteis = []
    for paragrafo in paragrafos:
        if eh_fragmento(paragrafo):
            auditoria.descartar(paragrafo, "fragmento de tabela ou figura sem texto")
        else:
            uteis.append(paragrafo)
    return estrategia.segmentar(fonte, uteis, auditoria), auditoria
