"""Modelos e carga do golden dataset de casos críticos (issue #24).

O arquivo ``tests/eval/golden_dataset.json`` é o gabarito usado pelo benchmark
"LLM puro × RAG + Multiagentes" (issue #18). Este módulo valida a estrutura do
arquivo e oferece ``carregar_golden_dataset()`` para o script de benchmark.

A estrutura e as métricas estão documentadas em ``docs/avaliacao/golden-dataset.md``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from src.agents.schemas import (
    AgenteEspecialista,
    Categoria,
    ClassificacaoRisco,
    EntradaConsulta,
    OrgaoEmissor,
    RotaAcionada,
    Secao,
    StatusUso,
    StatusVacina,
)

CAMINHO_PADRAO = (
    Path(__file__).resolve().parents[2] / "tests" / "eval" / "golden_dataset.json"
)

# Selos que contam para a meta de 100% de acerto em contraindicações críticas.
CLASSIFICACOES_CRITICAS = frozenset({"CONTRAINDICADA", "ALERTA_RISCO_GRAVE"})

Jornada = Literal["mariana", "pedro", "fora_de_escopo"]
Tema = Literal[
    "vacinacao_gestacao", "interacao_medicamentosa", "manejo_doenca", "fora_de_escopo"
]
VerificacaoFonte = Literal["confirmada", "pendente", "nao_se_aplica"]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentoReferencia(_Modelo):
    """Documento oficial do inventário da issue #11 citado pelo gabarito."""

    doc_id: Annotated[str, StringConstraints(pattern=r"^DOC-[A-Z0-9-]+$")]
    orgao_emissor: OrgaoEmissor
    titulo_documento: Texto
    categoria: Categoria
    url_referencia: str | None = None
    observacao: str | None = None


class FonteEsperada(_Modelo):
    """Documento e seção que a resposta precisa citar para ser considerada válida."""

    doc_id: Texto
    secao: Secao
    afirmacao_chave: Texto = Field(
        description="O que o trecho oficial precisa sustentar (não é citação literal)."
    )


class StatusEsperadoItem(_Modelo):
    item: Texto = Field(description="Chave da vacina ou princípio ativo (DCB).")
    status: StatusVacina | StatusUso


class Gabarito(_Modelo):
    classificacao_risco_esperada: ClassificacaoRisco
    rotas_aceitas: list[RotaAcionada] = Field(min_length=1)
    agentes_esperados: list[AgenteEspecialista] = Field(default_factory=list)
    status_por_item: list[StatusEsperadoItem] = Field(default_factory=list)
    fontes_esperadas: list[FonteEsperada] = Field(default_factory=list)
    condutas_esperadas: list[Texto] = Field(default_factory=list)
    afirmacoes_proibidas: list[Texto] = Field(default_factory=list)
    deve_abster: bool
    verificacao_fonte: VerificacaoFonte
    nota_curadoria: str | None = None

    @model_validator(mode="after")
    def _coerencia(self) -> Gabarito:
        abstinencia = self.classificacao_risco_esperada == "EVIDENCIA_INSUFICIENTE"
        if self.deve_abster != abstinencia:
            raise ValueError(
                "deve_abster deve ser true se, e somente se, a classificação "
                "esperada for EVIDENCIA_INSUFICIENTE."
            )
        if abstinencia:
            if self.fontes_esperadas or self.status_por_item or self.agentes_esperados:
                raise ValueError(
                    "Caso de abstinência não pode ter fontes, status ou agentes."
                )
            if self.verificacao_fonte != "nao_se_aplica":
                raise ValueError("Abstinência usa verificacao_fonte 'nao_se_aplica'.")
        else:
            if not self.fontes_esperadas:
                raise ValueError("Caso com recomendação exige fonte oficial esperada.")
            if not self.agentes_esperados:
                raise ValueError("Caso com recomendação exige agente especialista.")
            if self.verificacao_fonte == "nao_se_aplica":
                raise ValueError("Informe se a fonte foi confirmada ou está pendente.")
        return self


class CasoGolden(_Modelo):
    id: Annotated[str, StringConstraints(pattern=r"^GD-\d{2}$")]
    titulo: Texto
    jornada: Jornada
    tema: Tema
    critico: bool = Field(
        description="Conta para a meta de 100% em contraindicações críticas."
    )
    entrada: EntradaConsulta
    gabarito: Gabarito

    @model_validator(mode="after")
    def _critico_tem_selo_critico(self) -> CasoGolden:
        selo = self.gabarito.classificacao_risco_esperada
        if self.critico and selo not in CLASSIFICACOES_CRITICAS:
            raise ValueError(
                f"{self.id}: caso crítico precisa esperar "
                f"{sorted(CLASSIFICACOES_CRITICAS)}, não {selo}."
            )
        return self


class GoldenDataset(_Modelo):
    versao_dataset: Annotated[
        str, StringConstraints(pattern=r"^golden-v\d+\.\d+\.\d+$")
    ]
    status: Literal["rascunho_para_revisao", "revisado"]
    data_atualizacao: date
    referencia_contrato: Texto
    descricao: Texto
    documentos_referencia: list[DocumentoReferencia] = Field(min_length=1)
    casos: list[CasoGolden] = Field(min_length=1)

    @model_validator(mode="after")
    def _referencias(self) -> GoldenDataset:
        ids_casos = [c.id for c in self.casos]
        if len(set(ids_casos)) != len(ids_casos):
            raise ValueError("IDs de casos repetidos.")
        docs = [d.doc_id for d in self.documentos_referencia]
        if len(set(docs)) != len(docs):
            raise ValueError("doc_id repetido em documentos_referencia.")
        conhecidos = set(docs)
        for caso in self.casos:
            for fonte in caso.gabarito.fontes_esperadas:
                if fonte.doc_id not in conhecidos:
                    raise ValueError(
                        f"{caso.id}: doc_id {fonte.doc_id} fora de "
                        "documentos_referencia."
                    )
        return self

    @property
    def casos_criticos(self) -> list[CasoGolden]:
        return [c for c in self.casos if c.critico]

    def documento(self, doc_id: str) -> DocumentoReferencia:
        for doc in self.documentos_referencia:
            if doc.doc_id == doc_id:
                return doc
        raise KeyError(doc_id)


def carregar_golden_dataset(caminho: Path = CAMINHO_PADRAO) -> GoldenDataset:
    """Lê e valida o golden dataset."""
    return GoldenDataset.model_validate_json(caminho.read_text(encoding="utf-8"))
