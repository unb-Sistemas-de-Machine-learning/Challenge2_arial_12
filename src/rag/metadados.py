"""Modelo dos chunks indexados e quality gate da ingestão (issue #11).

Implementa a Seção 2 de ``docs/arquitetura/contrato-json-e-metadados-rag.md``:

* os 5 metadados obrigatórios (Seção 2.1), com o vocabulário controlado
  importado de ``src.agents.schemas`` para nunca divergir dos agentes;
* os campos complementares de rastreabilidade (Seção 2.2), mais o ``doc_id``
  do catálogo, que liga cada chunk às ``fontes_esperadas`` do golden dataset;
* a regra de validação da ingestão (Seção 2.4), aplicada por ``validar_lote``.

O ChromaDB aceita listas de strings nos metadados, então ``publico_alvo`` é
gravado como lista, sem conversão. Campos ``None`` são omitidos na gravação,
porque o ChromaDB não aceita valores nulos.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from src.agents.schemas import Categoria, OrgaoEmissor, PublicoAlvo, Secao

# Seção 2.4, regra 3: o texto precisa ter pelo menos 30 caracteres úteis.
MIN_CARACTERES_UTEIS = 30

PADRAO_DOC_ID = r"^DOC-[A-Z0-9-]+$"
PADRAO_CHUNK_ID = r"^[a-z0-9]+(-[a-z0-9]+)*$"
PADRAO_VERSAO_CORPUS = r"^corpus-v\d+\.\d+\.\d+$"
PADRAO_DATA_PUBLICACAO = r"^\d{4}(-(0[1-9]|1[0-2]))?$"

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def caracteres_uteis(texto: str) -> int:
    """Conta os caracteres do texto sem espaços em branco."""
    return len(re.sub(r"\s+", "", texto))


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetadadosChunk(_Modelo):
    # Seção 2.1: obrigatórios.
    orgao_emissor: OrgaoEmissor
    titulo_documento: Texto
    categoria: Categoria
    secao: Secao
    publico_alvo: list[PublicoAlvo] = Field(min_length=1)
    # Seção 2.2: rastreabilidade.
    doc_id: Annotated[str, StringConstraints(pattern=PADRAO_DOC_ID)]
    entidade_principal: Texto
    versao_ingestao: Annotated[str, StringConstraints(pattern=PADRAO_VERSAO_CORPUS)]
    data_publicacao: (
        Annotated[str, StringConstraints(pattern=PADRAO_DATA_PUBLICACAO)] | None
    ) = None
    pagina_origem: int | None = Field(default=None, ge=1)
    url_referencia: str | None = None
    titulo_secao: str | None = Field(
        default=None,
        description="Títulos do documento acima do trecho, do mais geral ao mais interno.",
    )
    ordem: int | None = Field(
        default=None, ge=0, description="Posição do chunk no documento (0, 1, 2...)."
    )

    @field_validator("publico_alvo")
    @classmethod
    def _sem_repeticao(cls, valor: list[str]) -> list[str]:
        if len(set(valor)) != len(valor):
            raise ValueError("publico_alvo tem valores repetidos.")
        return valor


class Chunk(_Modelo):
    chunk_id: Annotated[str, StringConstraints(pattern=PADRAO_CHUNK_ID)]
    texto: str = Field(description="Trecho literal do documento oficial.")
    metadados: MetadadosChunk

    @field_validator("texto")
    @classmethod
    def _texto_util(cls, valor: str) -> str:
        if caracteres_uteis(valor) < MIN_CARACTERES_UTEIS:
            raise ValueError(
                f"texto com menos de {MIN_CARACTERES_UTEIS} caracteres úteis."
            )
        return valor


def para_chroma(metadados: MetadadosChunk) -> dict[str, Any]:
    """Converte os metadados para o formato gravado no ChromaDB."""
    return metadados.model_dump(exclude_none=True)


def de_chroma(bruto: Mapping[str, Any]) -> MetadadosChunk:
    """Reconstrói os metadados lidos do ChromaDB (usado pela issue #14)."""
    return MetadadosChunk.model_validate(dict(bruto))


class ErroQualidade(Exception):
    """Um ou mais chunks violam a Seção 2.4 do contrato."""

    def __init__(self, problemas: list[str]) -> None:
        self.problemas = problemas
        resumo = "\n".join(f"  - {p}" for p in problemas[:20])
        extra = len(problemas) - 20
        if extra > 0:
            resumo += f"\n  ... e mais {extra} problema(s)"
        super().__init__(
            f"{len(problemas)} problema(s) no quality gate da ingestão:\n{resumo}"
        )


def validar_lote(chunks: Iterable[Mapping[str, Any] | Chunk]) -> list[Chunk]:
    """Aplica o quality gate a todos os chunks de uma carga.

    Valida cada chunk e confere se os ``chunk_id`` são únicos. Junta todos os
    problemas antes de falhar, para que um relatório mostre tudo de uma vez.
    Levanta ``ErroQualidade`` se houver qualquer problema.
    """
    validos: list[Chunk] = []
    problemas: list[str] = []
    vistos: set[str] = set()
    for posicao, bruto in enumerate(chunks):
        try:
            chunk = (
                bruto if isinstance(bruto, Chunk) else Chunk.model_validate(dict(bruto))
            )
        except ValidationError as erro:
            identificador = (
                bruto.get("chunk_id") if isinstance(bruto, Mapping) else None
            ) or f"posição {posicao}"
            for detalhe in erro.errors():
                campo = ".".join(str(parte) for parte in detalhe["loc"])
                problemas.append(f"{identificador}: {campo}: {detalhe['msg']}")
            continue
        if chunk.chunk_id in vistos:
            problemas.append(f"{chunk.chunk_id}: chunk_id repetido.")
            continue
        vistos.add(chunk.chunk_id)
        validos.append(chunk)
    if problemas:
        raise ErroQualidade(problemas)
    return validos
