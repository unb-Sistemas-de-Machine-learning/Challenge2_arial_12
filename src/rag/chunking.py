"""Chunking semântico por seção e montagem dos metadados (issue #11).

Regras que preservam o contexto clínico:

* um chunk só junta parágrafos com a mesma ``secao`` e o mesmo título; nunca
  atravessa a fronteira de uma seção;
* parágrafos e itens de lista não são cortados; só um parágrafo maior que
  ``MAXIMO_CARACTERES`` é dividido, por frases;
* o embedding é calculado sobre o trecho precedido do título do documento e da
  seção (``texto_para_embedding``), mas o chunk guarda só o trecho literal, que
  vira o ``trecho_literal`` citado ao cidadão.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import groupby

from src.rag.catalogo import Fonte
from src.rag.metadados import (
    MIN_CARACTERES_UTEIS,
    Chunk,
    MetadadosChunk,
    caracteres_uteis,
)
from src.rag.secoes import ORDEM_PUBLICO, Auditoria, Bloco

ALVO_CARACTERES = 1000
MAXIMO_CARACTERES = 1500

ROTULO_SECAO = {
    "indicacoes": "Indicações",
    "contraindicacoes": "Contraindicações",
    "advertencias_e_precaucoes": "Advertências e precauções",
    "gravidez_e_lactacao": "Gravidez e lactação",
    "interacoes_medicamentosas": "Interações medicamentosas",
    "esquema_vacinal": "Esquema vacinal",
    "manejo_clinico": "Manejo clínico",
    "sinais_de_alarme": "Sinais de alarme",
    "condutas_gerais": "Condutas gerais",
}

_FIM_DE_FRASE = re.compile(r"(?<=[\.!?;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÀÇ0-9•\-–])")


@dataclass
class _Rascunho:
    textos: list[str]
    pagina: int
    publico: set[str]

    @property
    def tamanho(self) -> int:
        return sum(len(t) for t in self.textos) + max(len(self.textos) - 1, 0)


def _dividir_por_frases(texto: str) -> list[str]:
    """Divide um parágrafo longo em pedaços de até ``MAXIMO_CARACTERES``."""
    pedacos: list[str] = []
    atual = ""
    for frase in _FIM_DE_FRASE.split(texto):
        if atual and len(atual) + 1 + len(frase) > ALVO_CARACTERES:
            pedacos.append(atual)
            atual = frase
        else:
            atual = f"{atual} {frase}".strip()
    if atual:
        pedacos.append(atual)
    # Uma "frase" sem pontuação maior que o máximo é cortada em palavras.
    saida: list[str] = []
    for pedaco in pedacos:
        while len(pedaco) > MAXIMO_CARACTERES:
            corte = pedaco.rfind(" ", 0, ALVO_CARACTERES)
            corte = corte if corte > 0 else ALVO_CARACTERES
            saida.append(pedaco[:corte])
            pedaco = pedaco[corte:].strip()
        saida.append(pedaco)
    return saida


def _empacotar(blocos: list[Bloco]) -> list[_Rascunho]:
    rascunhos: list[_Rascunho] = []
    atual: _Rascunho | None = None
    for bloco in blocos:
        texto = bloco.texto.strip()
        partes = (
            _dividir_por_frases(texto) if len(texto) > MAXIMO_CARACTERES else [texto]
        )
        for parte in partes:
            cabe = (
                atual is not None and atual.tamanho + 1 + len(parte) <= ALVO_CARACTERES
            )
            if atual is None or not cabe:
                atual = _Rascunho([parte], bloco.pagina, set(bloco.publico_alvo))
                rascunhos.append(atual)
            else:
                atual.textos.append(parte)
                atual.publico.update(bloco.publico_alvo)
    return rascunhos


def _absorver_pequenos(rascunhos: list[_Rascunho]) -> list[_Rascunho]:
    """Junta ao vizinho da mesma seção os pedaços com poucos caracteres úteis."""
    resultado: list[_Rascunho] = []
    for rascunho in rascunhos:
        pequeno = caracteres_uteis(" ".join(rascunho.textos)) < MIN_CARACTERES_UTEIS
        if pequeno and resultado:
            resultado[-1].textos.extend(rascunho.textos)
            resultado[-1].publico.update(rascunho.publico)
        else:
            resultado.append(rascunho)
    if len(resultado) > 1:
        primeiro = resultado[0]
        if caracteres_uteis(" ".join(primeiro.textos)) < MIN_CARACTERES_UTEIS:
            resultado[1].textos[:0] = primeiro.textos
            resultado[1].pagina = primeiro.pagina
            resultado[1].publico.update(primeiro.publico)
            resultado = resultado[1:]
    return resultado


def montar_chunks(
    fonte: Fonte, blocos: list[Bloco], versao_ingestao: str, auditoria: Auditoria
) -> list[Chunk]:
    """Agrupa os blocos de um documento em chunks com os metadados do contrato."""
    chunks: list[Chunk] = []
    por_pagina: dict[int, int] = {}
    for (secao, titulo, entidade), grupo in groupby(
        blocos, key=lambda b: (b.secao, b.titulo_secao, b.entidade)
    ):
        for rascunho in _absorver_pequenos(_empacotar(list(grupo))):
            texto = "\n".join(rascunho.textos)
            if caracteres_uteis(texto) < MIN_CARACTERES_UTEIS:
                auditoria.descartados.append(
                    {
                        "pagina": rascunho.pagina,
                        "motivo": "seção com menos de 30 caracteres úteis",
                        "trecho": texto[:160],
                    }
                )
                continue
            por_pagina[rascunho.pagina] = por_pagina.get(rascunho.pagina, 0) + 1
            chunk_id = (
                f"{fonte.slug}-{secao.replace('_', '-')}"
                f"-p{rascunho.pagina:02d}-c{por_pagina[rascunho.pagina]:02d}"
            )
            metadados = MetadadosChunk(
                orgao_emissor=fonte.orgao_emissor,
                titulo_documento=fonte.titulo_documento,
                categoria=fonte.categoria,
                secao=secao,
                publico_alvo=[p for p in ORDEM_PUBLICO if p in rascunho.publico],
                doc_id=fonte.doc_id,
                entidade_principal=entidade or fonte.entidade_principal,
                versao_ingestao=versao_ingestao,
                data_publicacao=fonte.data_publicacao,
                pagina_origem=rascunho.pagina,
                url_referencia=fonte.url_referencia,
                titulo_secao=titulo or None,
                ordem=len(chunks),
            )
            chunks.append(Chunk(chunk_id=chunk_id, texto=texto, metadados=metadados))
    return chunks


def texto_para_embedding(chunk: Chunk) -> str:
    """Trecho precedido do título do documento e da seção (contexto do embedding)."""
    meta = chunk.metadados
    contexto = ROTULO_SECAO[meta.secao]
    if meta.titulo_secao:
        contexto = f"{contexto} — {meta.titulo_secao}"
    return f"{meta.titulo_documento}\n{contexto}\n\n{chunk.texto}"
