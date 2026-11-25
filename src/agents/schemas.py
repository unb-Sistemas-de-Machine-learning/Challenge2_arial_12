"""Schemas Pydantic de entrada e saída dos 3 agentes do EvidencIA Saúde.

Implementam o contrato de ``docs/arquitetura/contrato-json-e-metadados-rag.md``:

* ``EntradaConsulta``: payload de ``POST /api/v1/consultar`` (Seção 3);
* ``SaidaEstruturadorRoteador``: saída do agente de entrada (Seção 4.1);
* ``SaidaTriagemVacinal`` e ``SaidaMedicamentosCondutas``: envelope dos agentes
  especialistas (Seção 4.2).

A especificação comentada está em ``docs/agentes/prompts-e-schemas.md``. Os
schemas de saída também são injetados nos prompts de sistema
(``src/agents/prompts``), então prompt e validação nunca se desalinham.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Literal

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

# --- Vocabulários controlados do RAG (Seção 2.1 do contrato) -----------------

OrgaoEmissor = Literal["ANVISA", "MINISTERIO_DA_SAUDE"]
Categoria = Literal[
    "bula_medicamento",
    "bula_vacina",
    "calendario_vacinal",
    "protocolo_clinico",
    "nota_tecnica",
]
Secao = Literal[
    "indicacoes",
    "contraindicacoes",
    "advertencias_e_precaucoes",
    "gravidez_e_lactacao",
    "interacoes_medicamentosas",
    "esquema_vacinal",
    "manejo_clinico",
    "sinais_de_alarme",
    "condutas_gerais",
]
PublicoAlvo = Literal[
    "geral",
    "adulto",
    "gestante",
    "lactante",
    "idoso",
    "imunossuprimido",
    "pacientes_com_dengue",
    "pacientes_com_malaria",
    "pacientes_com_gripe",
]

# --- Classificação, rotas e agentes (Seções 4 e 5 do contrato) ---------------

ClassificacaoRisco = Literal[
    "INDICADA",
    "CONTRAINDICADA",
    "ALERTA_RISCO_GRAVE",
    "ORIENTACAO_GERAL",
    "EVIDENCIA_INSUFICIENTE",
]
RotaDefinida = Literal[
    "triagem_vacinal",
    "interacao_medicamentosa",
    "condutas_doenca",
    "hibrida",
    "fora_de_escopo",
]
RotaAcionada = Literal[
    "triagem_vacinal",
    "interacao_medicamentosa",
    "condutas_doenca",
    "hibrida",
    "fora_de_escopo",
    "evidencia_insuficiente",
]
AgenteId = Literal[
    "agente_estruturador_roteador",
    "agente_triagem_vacinal",
    "agente_medicamentos_condutas",
]
AgenteEspecialista = Literal["agente_triagem_vacinal", "agente_medicamentos_condutas"]
StatusVacina = Literal["INDICADA", "CONTRAINDICADA", "AVALIAR_COM_MEDICO"]
StatusUso = Literal["INDICADO", "CONTRAINDICADO", "AVALIAR_COM_MEDICO"]
FaixaEtaria = Literal["crianca", "adolescente", "adulto", "idoso"]
OrigemEntrada = Literal["formulario_texto", "ocr_imagem", "asr_audio"]

# Ordem de precedência da Seção 5.2 (maior valor = mais grave).
# EVIDENCIA_INSUFICIENTE fica de fora: não é uma recomendação.
SEVERIDADE: dict[str, int] = {
    "INDICADA": 0,
    "ORIENTACAO_GERAL": 1,
    "CONTRAINDICADA": 2,
    "ALERTA_RISCO_GRAVE": 3,
}

# Classificação mínima implicada pelo status de cada item avaliado.
_CLASSIFICACAO_DO_STATUS: dict[str, str] = {
    "INDICADA": "INDICADA",
    "INDICADO": "INDICADA",
    "AVALIAR_COM_MEDICO": "ORIENTACAO_GERAL",
    "CONTRAINDICADA": "CONTRAINDICADA",
    "CONTRAINDICADO": "CONTRAINDICADA",
}

# Agentes que cada rota pode acionar.
AGENTES_POR_ROTA: dict[str, frozenset[str]] = {
    "triagem_vacinal": frozenset({"agente_triagem_vacinal"}),
    "interacao_medicamentosa": frozenset({"agente_medicamentos_condutas"}),
    "condutas_doenca": frozenset({"agente_medicamentos_condutas"}),
    "hibrida": frozenset({"agente_triagem_vacinal", "agente_medicamentos_condutas"}),
    "fora_de_escopo": frozenset(),
}


def maior_severidade(classificacoes: Iterable[str]) -> ClassificacaoRisco:
    """Aplica a precedência da Seção 5.2 do contrato.

    ``ALERTA_RISCO_GRAVE`` > ``CONTRAINDICADA`` > ``ORIENTACAO_GERAL`` >
    ``INDICADA``. Sem nenhuma recomendação, devolve ``EVIDENCIA_INSUFICIENTE``.
    """
    validas = [c for c in classificacoes if c in SEVERIDADE]
    if not validas:
        return "EVIDENCIA_INSUFICIENTE"
    return max(validas, key=SEVERIDADE.__getitem__)  # type: ignore[return-value]


TextoNaoVazio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TextoCurto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Entrada (Seção 3) -------------------------------------------------------


class PerfilUsuario(_Modelo):
    faixa_etaria: FaixaEtaria
    idade_anos: int | None = Field(default=None, ge=0, le=120)
    gestante: bool
    semanas_gestacao: int | None = Field(default=None, ge=1, le=42)
    lactante: bool = False
    comorbidades: list[str] = Field(default_factory=list)
    alergias_conhecidas: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _semanas_so_para_gestante(self) -> PerfilUsuario:
        if self.semanas_gestacao is not None and not self.gestante:
            raise ValueError(
                "semanas_gestacao só pode ser preenchido quando gestante for true."
            )
        return self


class VacinaTomada(_Modelo):
    vacina: TextoNaoVazio
    doses_tomadas: int = Field(ge=0)
    ano_ultima_dose: int | None = Field(default=None, ge=1950, le=2026)


class Consulta(_Modelo):
    relato_textual: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)
    ]
    medicamento_consultado: TextoCurto | None = None
    vacina_consultada: TextoCurto | None = None
    suspeita_doenca: str | None = None


class EntradaConsulta(_Modelo):
    """Payload recebido pelo Agente Estruturador/Roteador (Seção 3)."""

    request_id: UUID4 | None = None
    origem_entrada: OrigemEntrada = "formulario_texto"
    perfil_usuario: PerfilUsuario
    historico_vacinal: list[VacinaTomada] = Field(default_factory=list)
    consulta: Consulta


# --- Saída do Agente Estruturador/Roteador (Seção 4.1) ----------------------


class EntidadesNormalizadas(_Modelo):
    medicamentos_dcb: list[str] = Field(
        default_factory=list,
        description="Princípios ativos (DCB) em minúsculas, sem acento, com _.",
    )
    vacinas: list[str] = Field(
        default_factory=list, description="Chaves padronizadas das vacinas."
    )
    doencas_suspeitas: list[str] = Field(default_factory=list)
    sintomas: list[str] = Field(default_factory=list)


class FiltrosRag(_Modelo):
    categorias: list[Categoria] = Field(default_factory=list)
    secoes_prioritarias: list[Secao] = Field(default_factory=list)
    publico_alvo: list[PublicoAlvo] = Field(default_factory=list)


class SaidaEstruturadorRoteador(_Modelo):
    """Entrada normalizada + rota de execução + filtros para o RAG."""

    request_id: str | None = Field(
        default=None, description="Preenchido pelo backend; o LLM não o gera."
    )
    rota_definida: RotaDefinida
    agentes_alvo: list[AgenteEspecialista]
    entidades_normalizadas: EntidadesNormalizadas
    filtros_rag_recomendados: FiltrosRag
    dentro_do_escopo_mvp: bool
    entrada_suficiente: bool = Field(
        description="false quando o relato é incompreensível ou não traz dúvida."
    )
    motivo_insuficiencia: str | None = None

    @model_validator(mode="after")
    def _rota_coerente(self) -> SaidaEstruturadorRoteador:
        permitidos = AGENTES_POR_ROTA[self.rota_definida]
        alvos = set(self.agentes_alvo)
        if len(alvos) != len(self.agentes_alvo):
            raise ValueError("agentes_alvo não pode ter itens repetidos.")
        if self.rota_definida == "fora_de_escopo":
            if alvos:
                raise ValueError("A rota fora_de_escopo não aciona agentes.")
        elif not alvos or not alvos <= permitidos:
            raise ValueError(
                f"A rota {self.rota_definida} só aciona {sorted(permitidos)}."
            )
        if not self.dentro_do_escopo_mvp and self.rota_definida != "fora_de_escopo":
            raise ValueError("Consulta fora do escopo exige rota fora_de_escopo.")
        if not self.entrada_suficiente:
            if self.rota_definida != "fora_de_escopo":
                raise ValueError("Entrada insuficiente exige rota fora_de_escopo.")
            if not (self.motivo_insuficiencia or "").strip():
                raise ValueError("Informe motivo_insuficiencia.")
        return self


# --- Envelope dos agentes especialistas (Seção 4.2) -------------------------


class EvidenciaRecuperada(_Modelo):
    evidencia_id: TextoNaoVazio = Field(description="Ex.: EV-01.")
    chunk_id: TextoNaoVazio
    orgao_emissor: OrgaoEmissor
    titulo_documento: TextoNaoVazio
    categoria: Categoria
    secao: Secao
    publico_alvo: list[PublicoAlvo] = Field(min_length=1)
    trecho_literal: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=30)
    ] = Field(description="Cópia exata do trecho recuperado, sem paráfrase.")
    score_similaridade: float = Field(ge=0, le=1)


class _EnvelopeEspecialista(_Modelo):
    classificacao_parcial: ClassificacaoRisco
    evidencias_recuperadas: list[EvidenciaRecuperada] = Field(default_factory=list)

    def _ids_citados(self) -> set[str]:
        raise NotImplementedError

    def _classificacoes_dos_itens(self) -> list[str]:
        raise NotImplementedError

    def _tem_recomendacao(self) -> bool:
        raise NotImplementedError

    @model_validator(mode="after")
    def _guardrails(self) -> _EnvelopeEspecialista:
        ids = [e.evidencia_id for e in self.evidencias_recuperadas]
        if len(set(ids)) != len(ids):
            raise ValueError("evidencia_id repetido em evidencias_recuperadas.")

        if self.classificacao_parcial == "EVIDENCIA_INSUFICIENTE":
            # Zero Evidence, Zero Recommendation (Seção 5.2, regra 1).
            if self._tem_recomendacao():
                raise ValueError(
                    "EVIDENCIA_INSUFICIENTE não pode trazer recomendação de uso."
                )
            return self

        if not self.evidencias_recuperadas:
            raise ValueError(
                "Classificação diferente de EVIDENCIA_INSUFICIENTE exige ao menos "
                "uma evidência oficial."
            )
        faltando = self._ids_citados() - set(ids)
        if faltando:
            raise ValueError(f"evidencia_ids sem evidência correspondente: {faltando}.")

        exigida = maior_severidade(self._classificacoes_dos_itens())
        if exigida != "EVIDENCIA_INSUFICIENTE" and (
            SEVERIDADE.get(self.classificacao_parcial, -1) < SEVERIDADE[exigida]
        ):
            # Precedência máxima de severidade (Seção 5.2, regra 2).
            raise ValueError(
                f"classificacao_parcial deve ser pelo menos {exigida} "
                "pelos itens avaliados."
            )
        return self


class VacinaAvaliada(_Modelo):
    vacina: TextoNaoVazio
    status: StatusVacina
    justificativa: TextoNaoVazio
    evidencia_ids: list[str] = Field(min_length=1)


class AchadosTriagemVacinal(_Modelo):
    vacinas_em_dia: list[str] = Field(default_factory=list)
    vacinas_pendentes: list[VacinaAvaliada] = Field(
        default_factory=list,
        description="Vacinas pendentes ou consultadas, cada uma com status.",
    )
    resumo_agente: TextoNaoVazio


class SaidaTriagemVacinal(_EnvelopeEspecialista):
    """Saída do Agente de Triagem Vacinal e Segurança na Gestação."""

    agente_origem: Literal["agente_triagem_vacinal"] = "agente_triagem_vacinal"
    achados_estruturados: AchadosTriagemVacinal

    def _ids_citados(self) -> set[str]:
        return {
            ev
            for vacina in self.achados_estruturados.vacinas_pendentes
            for ev in vacina.evidencia_ids
        }

    def _classificacoes_dos_itens(self) -> list[str]:
        return [
            _CLASSIFICACAO_DO_STATUS[v.status]
            for v in self.achados_estruturados.vacinas_pendentes
        ]

    def _tem_recomendacao(self) -> bool:
        return bool(self.achados_estruturados.vacinas_pendentes)


class AchadosMedicamentosCondutas(_Modelo):
    medicamento_avaliado: str | None = None
    doenca_ou_condicao_contexto: str | None = None
    status_uso: StatusUso | None = None
    condutas_seguras: list[str] = Field(default_factory=list)
    sinais_de_alarme: list[str] = Field(default_factory=list)
    evidencia_ids: list[str] = Field(default_factory=list)
    resumo_agente: TextoNaoVazio

    @model_validator(mode="after")
    def _status_exige_medicamento(self) -> AchadosMedicamentosCondutas:
        if (self.status_uso is None) != (self.medicamento_avaliado is None):
            raise ValueError(
                "medicamento_avaliado e status_uso devem vir juntos (ou ambos nulos)."
            )
        return self


class SaidaMedicamentosCondutas(_EnvelopeEspecialista):
    """Saída do Agente de Medicamentos e Condutas em Doenças."""

    agente_origem: Literal["agente_medicamentos_condutas"] = (
        "agente_medicamentos_condutas"
    )
    achados_estruturados: AchadosMedicamentosCondutas

    def _ids_citados(self) -> set[str]:
        return set(self.achados_estruturados.evidencia_ids)

    def _classificacoes_dos_itens(self) -> list[str]:
        status = self.achados_estruturados.status_uso
        return [_CLASSIFICACAO_DO_STATUS[status]] if status else []

    def _tem_recomendacao(self) -> bool:
        achados = self.achados_estruturados
        return achados.status_uso is not None or bool(achados.condutas_seguras)


SCHEMA_SAIDA_POR_AGENTE: dict[str, type[BaseModel]] = {
    "agente_estruturador_roteador": SaidaEstruturadorRoteador,
    "agente_triagem_vacinal": SaidaTriagemVacinal,
    "agente_medicamentos_condutas": SaidaMedicamentosCondutas,
}
