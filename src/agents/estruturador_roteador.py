"""Agente Estruturador e Roteador: porta de entrada dos agentes (issue #13).

Recebe a entrada mista da interface (formulário/checklist + relato livre) e,
em uma chamada de *Structured Output*, normaliza as entidades clínicas e
define a rota de execução. O fluxo é:

1. valida a entrada (``EntradaConsulta``) e fixa o ``request_id``;
2. barra sem chamar o LLM o relato sem nenhum texto compreensível;
3. chama o LLM com o prompt versionado e valida a saída
   (``SaidaEstruturadorRoteador``), com uma nova tentativa que mostra ao
   modelo o erro de validação;
4. consolida a saída de forma determinística: junta os campos do formulário,
   padroniza os nomes (``normalizacao``) e calcula os filtros do RAG pelos
   agentes acionados, pelo perfil e pela suspeita (a sugestão do LLM é
   descartada, porque já trouxe ``gestante`` para quem não está grávida);
5. se o LLM não devolver JSON válido, responde com o roteamento *fail-safe*
   (``fora_de_escopo`` + ``motivo_insuficiencia``);
6. registra uma linha de log por execução, sem o relato nem dados pessoais.

Falhas do provedor de LLM sobem como ``ErroLLM`` (a API devolve 503).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from pydantic import ValidationError

from src.agents.llm import ClienteLLM, ClienteOpenAICompativel, ErroLLM, Mensagem
from src.agents.normalizacao import (
    PUBLICO_POR_COMORBIDADE,
    PUBLICO_POR_DOENCA,
    chave,
    normalizar_doenca,
    normalizar_medicamento,
    normalizar_sintoma,
    normalizar_vacina,
    separar_itens,
    unir,
)
from src.agents.prompts import VERSAO_PADRAO, VERSAO_PROMPTS, renderizar_prompt
from src.agents.schemas import (
    ContratoRoteado,
    EntidadesNormalizadas,
    EntradaConsulta,
    ExecucaoRoteamento,
    FiltrosRag,
    SaidaEstruturadorRoteador,
)

AGENTE_ID = "agente_estruturador_roteador"
MAX_TENTATIVAS_LLM = 2

MOTIVO_RELATO_ININTELIGIVEL = (
    "O relato não traz texto compreensível. Descreva sua dúvida sobre vacina, "
    "medicamento ou sintomas com suas palavras."
)
MOTIVO_FALHA_ESTRUTURACAO = (
    "Não foi possível organizar a consulta com segurança. Reformule a dúvida com "
    "mais detalhes ou procure um profissional de saúde."
)

# Filtros de RAG de cada especialista (mesmos valores do prompt de sistema).
FILTROS_POR_AGENTE: dict[str, tuple[list[str], list[str]]] = {
    "agente_triagem_vacinal": (
        ["calendario_vacinal", "nota_tecnica", "bula_vacina"],
        ["esquema_vacinal", "indicacoes", "contraindicacoes", "gravidez_e_lactacao"],
    ),
    "agente_medicamentos_condutas": (
        ["bula_medicamento", "protocolo_clinico"],
        [
            "contraindicacoes",
            "advertencias_e_precaucoes",
            "gravidez_e_lactacao",
            "interacoes_medicamentosas",
            "manejo_clinico",
            "sinais_de_alarme",
            "condutas_gerais",
        ],
    ),
}
PUBLICO_POR_FAIXA = {"adulto": "adulto", "idoso": "idoso"}

_PALAVRA = re.compile(r"[a-zà-öø-ÿ]{2,}", re.IGNORECASE)
_CERCA_JSON = re.compile(r"^```(?:json)?\s*|\s*```$")

logger = logging.getLogger(__name__)


class SaidaInvalidaLLM(Exception):
    """O LLM respondeu, mas a resposta não segue o schema."""


def estruturar_e_rotear(
    entrada: EntradaConsulta | dict[str, Any],
    cliente: ClienteLLM | None = None,
    *,
    versao_prompt: str = VERSAO_PADRAO,
) -> ContratoRoteado:
    """Estrutura a consulta e define a rota. Levanta ``ValidationError`` para
    entrada inválida e ``ErroLLM`` se o provedor estiver indisponível."""
    inicio = time.perf_counter()
    entrada = EntradaConsulta.model_validate(entrada)
    if entrada.request_id is None:
        entrada = entrada.model_copy(update={"request_id": uuid.uuid4()})
    request_id = str(entrada.request_id)

    tentativas = 0
    fallback = False
    if _relato_ininteligivel(entrada):
        saida = _roteamento_insuficiente(entrada, MOTIVO_RELATO_ININTELIGIVEL)
        modelo = "nao_acionado"
    else:
        cliente = cliente or ClienteOpenAICompativel.do_ambiente()
        modelo = cliente.modelo
        try:
            saida, tentativas = _chamar_llm(entrada, cliente, versao_prompt)
            saida = _consolidar(saida, entrada)
        except ErroLLM as erro:
            _registrar(
                "roteamento_erro_llm",
                request_id=request_id,
                modelo_llm=modelo,
                latencia_ms=_ms_desde(inicio),
                erro=str(erro),
                nivel=logging.ERROR,
            )
            raise
        except (SaidaInvalidaLLM, ValidationError):
            tentativas = MAX_TENTATIVAS_LLM
            fallback = True
            saida = _roteamento_insuficiente(entrada, MOTIVO_FALHA_ESTRUTURACAO)

    saida = saida.model_copy(update={"request_id": request_id})
    contrato = ContratoRoteado(
        request_id=request_id,
        entrada=entrada,
        roteamento=saida,
        execucao=ExecucaoRoteamento(
            modelo_llm=modelo,
            versao_prompt=VERSAO_PROMPTS,
            latencia_ms=_ms_desde(inicio),
            tentativas_llm=tentativas,
            fallback_seguranca=fallback,
        ),
    )
    _registrar_execucao(contrato)
    return contrato


# --- Chamada ao LLM ----------------------------------------------------------


def _chamar_llm(
    entrada: EntradaConsulta, cliente: ClienteLLM, versao_prompt: str
) -> tuple[SaidaEstruturadorRoteador, int]:
    entrada_json = json.dumps(
        entrada.model_dump(mode="json", exclude={"request_id"}),
        ensure_ascii=False,
        indent=2,
    )
    mensagens: list[Mensagem] = [
        {
            "role": "system",
            "content": renderizar_prompt(AGENTE_ID, "sistema", versao_prompt),
        },
        {
            "role": "user",
            "content": renderizar_prompt(
                AGENTE_ID, "usuario", versao_prompt, entrada_json=entrada_json
            ),
        },
    ]
    schema = SaidaEstruturadorRoteador.model_json_schema()

    for tentativa in range(1, MAX_TENTATIVAS_LLM + 1):
        texto = cliente.gerar_json(mensagens, schema, "saida_estruturador_roteador")
        try:
            return _validar_saida(texto), tentativa
        except SaidaInvalidaLLM as erro:
            _registrar(
                "roteamento_saida_invalida",
                request_id=str(entrada.request_id),
                modelo_llm=cliente.modelo,
                tentativa=tentativa,
                erro=str(erro),
                nivel=logging.WARNING,
            )
            mensagens = [
                *mensagens,
                {"role": "assistant", "content": texto},
                {
                    "role": "user",
                    "content": (
                        "A resposta anterior não segue o JSON Schema. Corrija estes "
                        f"problemas e responda só com o JSON corrigido:\n{erro}"
                    ),
                },
            ]
    raise SaidaInvalidaLLM("O LLM não devolveu um JSON válido.")


def _validar_saida(texto: str) -> SaidaEstruturadorRoteador:
    try:
        dados = json.loads(_CERCA_JSON.sub("", texto.strip()))
    except json.JSONDecodeError as erro:
        raise SaidaInvalidaLLM(f"JSON malformado: {erro.msg}.") from erro
    if not isinstance(dados, dict):
        raise SaidaInvalidaLLM("A resposta deve ser um objeto JSON.")
    dados["request_id"] = None  # o backend preenche, nunca o LLM
    try:
        return SaidaEstruturadorRoteador.model_validate(dados)
    except ValidationError as erro:
        problemas = [
            f"- {'.'.join(map(str, e['loc'])) or '(raiz)'}: {e['msg']}"
            for e in erro.errors(include_url=False, include_input=False)
        ]
        raise SaidaInvalidaLLM("\n".join(problemas)) from erro


# --- Consolidação determinística --------------------------------------------


def _entidades(
    entrada: EntradaConsulta, do_llm: EntidadesNormalizadas | None = None
) -> EntidadesNormalizadas:
    """Formulário primeiro, depois o que o LLM extraiu do relato."""
    consulta = entrada.consulta
    do_llm = do_llm or EntidadesNormalizadas()
    return EntidadesNormalizadas(
        medicamentos_dcb=unir(
            map(normalizar_medicamento, separar_itens(consulta.medicamento_consultado)),
            map(normalizar_medicamento, do_llm.medicamentos_dcb),
        ),
        vacinas=unir(
            map(normalizar_vacina, separar_itens(consulta.vacina_consultada)),
            map(normalizar_vacina, do_llm.vacinas),
        ),
        doencas_suspeitas=unir(
            map(normalizar_doenca, separar_itens(consulta.suspeita_doenca)),
            map(normalizar_doenca, do_llm.doencas_suspeitas),
        ),
        sintomas=unir(map(normalizar_sintoma, do_llm.sintomas)),
    )


def _publico_alvo(entrada: EntradaConsulta, doencas: list[str]) -> list[str]:
    perfil = entrada.perfil_usuario
    do_perfil = [PUBLICO_POR_FAIXA.get(perfil.faixa_etaria, "")]
    if perfil.gestante:
        do_perfil.append("gestante")
    if perfil.lactante:
        do_perfil.append("lactante")
    do_perfil += [
        PUBLICO_POR_COMORBIDADE.get(chave(c), "") for c in perfil.comorbidades
    ]
    das_doencas = [PUBLICO_POR_DOENCA.get(d, "") for d in doencas]
    return unir(["geral"], do_perfil, das_doencas)


def _agentes_coerentes(
    saida: SaidaEstruturadorRoteador, entidades: EntidadesNormalizadas
) -> list[str]:
    """Na rota híbrida, a triagem vacinal só entra se houver vacina citada.

    Na avaliação com o golden dataset, o LLM às vezes marcava "dengue +
    dipirona" como híbrida com os dois especialistas, confundindo a doença
    com a vacina. Se sobrar só um agente, a rota híbrida continua válida.
    """
    agentes = list(saida.agentes_alvo)
    if (
        saida.rota_definida == "hibrida"
        and "agente_triagem_vacinal" in agentes
        and not entidades.vacinas
        and len(agentes) > 1
    ):
        agentes.remove("agente_triagem_vacinal")
    return agentes


def _consolidar(
    saida: SaidaEstruturadorRoteador, entrada: EntradaConsulta
) -> SaidaEstruturadorRoteador:
    entidades = _entidades(entrada, saida.entidades_normalizadas)
    agentes = _agentes_coerentes(saida, entidades)
    if agentes:
        categorias = [FILTROS_POR_AGENTE[a][0] for a in agentes]
        secoes = [FILTROS_POR_AGENTE[a][1] for a in agentes]
        filtros = {
            "categorias": unir(*categorias),
            "secoes_prioritarias": unir(*secoes),
            "publico_alvo": _publico_alvo(entrada, entidades.doencas_suspeitas),
        }
    else:
        filtros = FiltrosRag().model_dump()  # sem agente, não há busca no RAG

    dados = saida.model_dump()
    dados["agentes_alvo"] = agentes
    dados["entidades_normalizadas"] = entidades.model_dump()
    dados["filtros_rag_recomendados"] = filtros
    if dados["motivo_insuficiencia"] is not None:
        dados["motivo_insuficiencia"] = dados["motivo_insuficiencia"].strip() or None
    return SaidaEstruturadorRoteador.model_validate(dados)


def _roteamento_insuficiente(
    entrada: EntradaConsulta, motivo: str
) -> SaidaEstruturadorRoteador:
    """Roteamento *fail-safe*: nenhum especialista é acionado."""
    return SaidaEstruturadorRoteador(
        rota_definida="fora_de_escopo",
        agentes_alvo=[],
        entidades_normalizadas=_entidades(entrada),
        filtros_rag_recomendados=FiltrosRag(),
        dentro_do_escopo_mvp=False,
        entrada_suficiente=False,
        motivo_insuficiencia=motivo,
    )


def _relato_ininteligivel(entrada: EntradaConsulta) -> bool:
    """Relato sem nenhuma palavra e sem campo estruturado preenchido."""
    consulta = entrada.consulta
    if (
        consulta.medicamento_consultado
        or consulta.vacina_consultada
        or consulta.suspeita_doenca
    ):
        return False
    return not _PALAVRA.search(consulta.relato_textual)


# --- Log de execução ---------------------------------------------------------


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


def _registrar(evento: str, *, nivel: int = logging.INFO, **campos: Any) -> None:
    registro = {"evento": evento, "agente": AGENTE_ID, **campos}
    logger.log(
        nivel,
        json.dumps(registro, ensure_ascii=False),
        extra={"registro_execucao": registro},
    )


def _registrar_execucao(contrato: ContratoRoteado) -> None:
    roteamento = contrato.roteamento
    entidades = roteamento.entidades_normalizadas
    _registrar(
        "roteamento_concluido",
        request_id=contrato.request_id,
        origem_entrada=contrato.entrada.origem_entrada,
        rota_definida=roteamento.rota_definida,
        agentes_alvo=roteamento.agentes_alvo,
        dentro_do_escopo_mvp=roteamento.dentro_do_escopo_mvp,
        entrada_suficiente=roteamento.entrada_suficiente,
        qtd_entidades={
            "medicamentos": len(entidades.medicamentos_dcb),
            "vacinas": len(entidades.vacinas),
            "doencas": len(entidades.doencas_suspeitas),
            "sintomas": len(entidades.sintomas),
        },
        **contrato.execucao.model_dump(),
    )
