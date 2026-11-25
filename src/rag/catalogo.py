"""Catálogo das fontes oficiais do corpus (issue #11).

``data/catalogo_fontes.toml`` lista cada documento de ``data/raw/`` com os
metadados que o pipeline anexa aos chunks, a verificação de vigência e o
sha256 do PDF. Os ``doc_id`` são os mesmos de ``documentos_referencia`` no
golden dataset (``tests/eval/golden_dataset.json``).
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from src.agents.schemas import Categoria, OrgaoEmissor, PublicoAlvo, Secao
from src.rag.config import CAMINHO_CATALOGO, DIR_RAW
from src.rag.metadados import (
    PADRAO_DATA_PUBLICACAO,
    PADRAO_DOC_ID,
    PADRAO_VERSAO_CORPUS,
)

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Jornada = Literal["mariana", "pedro"]


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validar_regex(valor: str) -> str:
    try:
        re.compile(valor)
    except re.error as erro:
        raise ValueError(f"expressão regular inválida: {erro}") from erro
    return valor


class RegraSecao(_Modelo):
    """Título de seção (expressão regular) que define a ``secao`` do trecho.

    A busca ignora maiúsculas e minúsculas. ``secao = "descartar"`` tira do
    índice todos os trechos sob esse título.
    """

    padrao: Texto
    secao: Secao | Literal["descartar"]

    _regex_valida = field_validator("padrao")(_validar_regex)


class RegraEntidade(_Modelo):
    """Padrão que define a ``entidade_principal`` (vacina, fármaco ou doença).

    Vale para o título mais interno que casar. Um parágrafo que *começa* com o
    padrão também troca a entidade dele e dos seguintes, até o próximo título
    (caso das notas técnicas, em que cada vacina abre um parágrafo).
    """

    padrao: Texto
    entidade: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]

    _regex_valida = field_validator("padrao")(_validar_regex)


class Fonte(_Modelo):
    doc_id: Annotated[str, StringConstraints(pattern=PADRAO_DOC_ID)]
    slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")] = (
        Field(description="Prefixo dos chunk_id deste documento.")
    )
    arquivo: Annotated[
        str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]*\.pdf$")
    ] = Field(description="Nome do PDF dentro de data/raw/.")
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    orgao_emissor: OrgaoEmissor
    titulo_documento: Texto
    categoria: Categoria
    jornada: Jornada
    entidade_principal: Texto
    publico_alvo: list[PublicoAlvo] = Field(
        min_length=1, description="Público-alvo padrão dos chunks do documento."
    )
    data_publicacao: Annotated[str, StringConstraints(pattern=PADRAO_DATA_PUBLICACAO)]
    url_referencia: Texto
    data_coleta: date
    data_verificacao_vigencia: date
    situacao_vigencia: Literal["vigente"]
    evidencia_vigencia: Texto = Field(
        description="Como a vigência foi conferida (edição mais recente, data da bula)."
    )
    detentor_registro: Texto | None = Field(
        default=None, description="Empresa detentora do registro (bulas)."
    )
    registro_anvisa: (
        Annotated[str, StringConstraints(pattern=r"^\d\.\d{4}\.\d{4}$")] | None
    ) = None
    paginas: list[tuple[int, int]] | None = Field(
        default=None,
        description=(
            "Intervalos de páginas processados (inclusivos, começando em 1). "
            "Sem valor, o documento inteiro é processado."
        ),
    )
    regras_secao: list[RegraSecao] = Field(default_factory=list)
    regras_entidade: list[RegraEntidade] = Field(default_factory=list)
    secao_padrao: Secao | None = Field(
        default=None,
        description=(
            "Seção dos trechos cujo título não casa com nenhuma regra. "
            "Sem valor, esses trechos são descartados."
        ),
    )

    @field_validator("paginas")
    @classmethod
    def _intervalos_validos(
        cls, valor: list[tuple[int, int]] | None
    ) -> list[tuple[int, int]] | None:
        if valor is None:
            return valor
        if not valor:
            raise ValueError("paginas não pode ser uma lista vazia.")
        anterior = 0
        for inicio, fim in valor:
            if not 1 <= inicio <= fim:
                raise ValueError(
                    "cada intervalo precisa ser [inicio, fim] com 1 <= inicio <= fim."
                )
            if inicio <= anterior:
                raise ValueError("intervalos de paginas fora de ordem ou sobrepostos.")
            anterior = fim
        return valor

    def paginas_processadas(self, total: int) -> list[int]:
        """Números das páginas (começando em 1) que o pipeline deve ler."""
        if self.paginas is None:
            return list(range(1, total + 1))
        if self.paginas[-1][1] > total:
            raise ValueError(
                f"{self.doc_id}: intervalo de páginas além do total ({total})."
            )
        return [p for inicio, fim in self.paginas for p in range(inicio, fim + 1)]


class Catalogo(_Modelo):
    versao_corpus: Annotated[str, StringConstraints(pattern=PADRAO_VERSAO_CORPUS)]
    fontes: list[Fonte] = Field(min_length=1)

    @model_validator(mode="after")
    def _unicos(self) -> Catalogo:
        for campo in ("doc_id", "slug", "arquivo"):
            valores = [getattr(f, campo) for f in self.fontes]
            repetidos = sorted({v for v in valores if valores.count(v) > 1})
            if repetidos:
                raise ValueError(f"{campo} repetido no catálogo: {repetidos}")
        return self

    def fonte(self, doc_id: str) -> Fonte:
        for fonte in self.fontes:
            if fonte.doc_id == doc_id:
                return fonte
        raise KeyError(doc_id)


def carregar_catalogo(caminho: Path = CAMINHO_CATALOGO) -> Catalogo:
    """Lê e valida o catálogo de fontes."""
    with caminho.open("rb") as arquivo:
        return Catalogo.model_validate(tomllib.load(arquivo))


def sha256_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


class ErroIntegridade(Exception):
    """Algum PDF do catálogo está ausente ou difere do sha256 registrado."""


def verificar_integridade(catalogo: Catalogo, dir_raw: Path = DIR_RAW) -> None:
    """Confere se cada PDF existe em ``dir_raw`` e bate com o sha256 do catálogo."""
    problemas: list[str] = []
    for fonte in catalogo.fontes:
        caminho = dir_raw / fonte.arquivo
        if not caminho.is_file():
            problemas.append(f"{fonte.doc_id}: arquivo ausente ({caminho}).")
            continue
        obtido = sha256_arquivo(caminho)
        if obtido != fonte.sha256:
            problemas.append(
                f"{fonte.doc_id}: sha256 diferente do catálogo "
                f"(esperado {fonte.sha256}, obtido {obtido})."
            )
    if problemas:
        raise ErroIntegridade("\n".join(problemas))
