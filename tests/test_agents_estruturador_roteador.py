import json
import logging
import uuid

import pytest
from pydantic import ValidationError

from src.agents.estruturador_roteador import (
    MOTIVO_FALHA_ESTRUTURACAO,
    MOTIVO_RELATO_ININTELIGIVEL,
    estruturar_e_rotear,
)
from src.agents.llm import ErroLLM
from src.agents.schemas import ContratoRoteado

ENTRADA_MARIANA = {
    "perfil_usuario": {
        "faixa_etaria": "adulto",
        "idade_anos": 32,
        "gestante": True,
        "semanas_gestacao": 20,
    },
    "historico_vacinal": [
        {"vacina": "hepatite_b", "doses_tomadas": 3, "ano_ultima_dose": 2012}
    ],
    "consulta": {
        "relato_textual": "Estou grávida de 20 semanas. Posso tomar a dTpa?",
        "vacina_consultada": "dTpa",
    },
}

ENTRADA_PEDRO = {
    "request_id": "9f3b1c2e-7b4d-4d62-a2c9-5a8b6f1e4c11",
    "perfil_usuario": {
        "faixa_etaria": "adulto",
        "gestante": False,
        "comorbidades": ["Imunossuprimido"],
    },
    "consulta": {
        "relato_textual": "Acho que estou com dengue, febre alta. Posso tomar Advil?",
        "medicamento_consultado": "Advil",
        "suspeita_doenca": "Dengue",
    },
}


def saida_llm(**sobrescritas):
    base = {
        "request_id": None,
        "rota_definida": "triagem_vacinal",
        "agentes_alvo": ["agente_triagem_vacinal"],
        "entidades_normalizadas": {
            "medicamentos_dcb": [],
            "vacinas": ["dtpa"],
            "doencas_suspeitas": [],
            "sintomas": [],
        },
        "filtros_rag_recomendados": {
            "categorias": ["calendario_vacinal"],
            "secoes_prioritarias": ["esquema_vacinal"],
            "publico_alvo": ["geral", "gestante"],
        },
        "dentro_do_escopo_mvp": True,
        "entrada_suficiente": True,
        "motivo_insuficiencia": None,
    }
    base.update(sobrescritas)
    return base


class LLMFalso:
    """Devolve as respostas na ordem e guarda as mensagens recebidas."""

    modelo = "llm-falso"

    def __init__(self, *respostas):
        self.respostas = [
            r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
            for r in respostas
        ]
        self.chamadas = []

    def gerar_json(self, mensagens, schema, nome_schema):
        self.chamadas.append(mensagens)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class LLMQueFalha:
    modelo = "llm-fora-do-ar"

    def gerar_json(self, mensagens, schema, nome_schema):
        raise ErroLLM("O LLM respondeu HTTP 503: indisponível")


def test_triagem_vacinal_gera_contrato_validado() -> None:
    llm = LLMFalso(saida_llm())
    contrato = estruturar_e_rotear(ENTRADA_MARIANA, llm)

    assert isinstance(contrato, ContratoRoteado)
    roteamento = contrato.roteamento
    assert roteamento.rota_definida == "triagem_vacinal"
    assert roteamento.agentes_alvo == ["agente_triagem_vacinal"]
    assert roteamento.entidades_normalizadas.vacinas == ["dtpa"]
    # Perfil e vacinas tomadas seguem junto no contrato para os especialistas.
    assert contrato.entrada.perfil_usuario.gestante is True
    assert contrato.entrada.historico_vacinal[0].vacina == "hepatite_b"
    uuid.UUID(contrato.request_id)
    assert roteamento.request_id == contrato.request_id
    assert contrato.execucao.tentativas_llm == 1
    assert contrato.execucao.fallback_seguranca is False
    assert contrato.execucao.modelo_llm == "llm-falso"


def test_request_id_da_entrada_e_preservado_e_llm_nao_o_define() -> None:
    llm = LLMFalso(
        saida_llm(
            request_id="inventado-pelo-llm",
            rota_definida="hibrida",
            agentes_alvo=["agente_medicamentos_condutas"],
        )
    )
    contrato = estruturar_e_rotear(ENTRADA_PEDRO, llm)
    assert contrato.request_id == ENTRADA_PEDRO["request_id"]
    assert contrato.roteamento.request_id == ENTRADA_PEDRO["request_id"]
    # O request_id não vai para o LLM.
    assert ENTRADA_PEDRO["request_id"] not in llm.chamadas[0][1]["content"]


def test_entidades_do_formulario_e_do_relato_sao_normalizadas() -> None:
    llm = LLMFalso(
        saida_llm(
            rota_definida="hibrida",
            agentes_alvo=["agente_medicamentos_condutas"],
            entidades_normalizadas={
                "medicamentos_dcb": ["Advil", "ibuprofeno"],
                "vacinas": [],
                "doencas_suspeitas": ["dengue"],
                "sintomas": ["Febre  Alta", "febre alta"],
            },
            filtros_rag_recomendados={
                "categorias": [],
                "secoes_prioritarias": [],
                "publico_alvo": [],
            },
        )
    )
    roteamento = estruturar_e_rotear(ENTRADA_PEDRO, llm).roteamento
    entidades = roteamento.entidades_normalizadas
    assert entidades.medicamentos_dcb == ["ibuprofeno"]
    assert entidades.doencas_suspeitas == ["dengue"]
    assert entidades.sintomas == ["febre alta"]

    filtros = roteamento.filtros_rag_recomendados
    assert filtros.categorias == ["bula_medicamento", "protocolo_clinico"]
    assert "sinais_de_alarme" in filtros.secoes_prioritarias
    assert filtros.publico_alvo == [
        "geral",
        "adulto",
        "imunossuprimido",
        "pacientes_com_dengue",
    ]


def test_campo_do_formulario_entra_mesmo_se_o_llm_esquecer() -> None:
    entrada = {
        **ENTRADA_MARIANA,
        "consulta": {
            "relato_textual": "Quais vacinas posso tomar?",
            "vacina_consultada": "febre_amarela, Dengue, dTpa",
        },
    }
    sem_vacinas = saida_llm(
        entidades_normalizadas={
            "medicamentos_dcb": [],
            "vacinas": [],
            "doencas_suspeitas": [],
            "sintomas": [],
        }
    )
    roteamento = estruturar_e_rotear(entrada, LLMFalso(sem_vacinas)).roteamento
    assert roteamento.entidades_normalizadas.vacinas == [
        "febre_amarela",
        "dengue",
        "dtpa",
    ]
    assert roteamento.filtros_rag_recomendados.publico_alvo[:3] == [
        "geral",
        "adulto",
        "gestante",
    ]


def test_mesma_entrada_gera_o_mesmo_roteamento() -> None:
    resposta = saida_llm()
    primeiro = estruturar_e_rotear(ENTRADA_MARIANA, LLMFalso(resposta)).roteamento
    segundo = estruturar_e_rotear(ENTRADA_MARIANA, LLMFalso(resposta)).roteamento
    assert primeiro.model_dump(exclude={"request_id"}) == segundo.model_dump(
        exclude={"request_id"}
    )


@pytest.mark.parametrize(
    ("rota", "agentes"),
    [
        ("triagem_vacinal", ["agente_triagem_vacinal"]),
        ("interacao_medicamentosa", ["agente_medicamentos_condutas"]),
        ("condutas_doenca", ["agente_medicamentos_condutas"]),
        ("hibrida", ["agente_triagem_vacinal", "agente_medicamentos_condutas"]),
    ],
)
def test_rotas_acionam_os_agentes_certos(rota, agentes) -> None:
    contrato = estruturar_e_rotear(
        ENTRADA_PEDRO, LLMFalso(saida_llm(rota_definida=rota, agentes_alvo=agentes))
    )
    assert contrato.roteamento.agentes_alvo == agentes
    categorias = set(contrato.roteamento.filtros_rag_recomendados.categorias)
    if "agente_triagem_vacinal" in agentes:
        assert "calendario_vacinal" in categorias
    if "agente_medicamentos_condutas" in agentes:
        assert "bula_medicamento" in categorias


def test_fora_de_escopo_nao_aciona_agentes_nem_rag() -> None:
    llm = LLMFalso(
        saida_llm(
            rota_definida="fora_de_escopo",
            agentes_alvo=[],
            dentro_do_escopo_mvp=False,
        )
    )
    roteamento = estruturar_e_rotear(ENTRADA_PEDRO, llm).roteamento
    assert roteamento.agentes_alvo == []
    assert roteamento.filtros_rag_recomendados.categorias == []
    assert roteamento.filtros_rag_recomendados.publico_alvo == []


def test_entrada_insuficiente_sinalizada_pelo_llm() -> None:
    llm = LLMFalso(
        saida_llm(
            rota_definida="fora_de_escopo",
            agentes_alvo=[],
            dentro_do_escopo_mvp=False,
            entrada_suficiente=False,
            motivo_insuficiencia="  O relato não traz nenhuma dúvida.  ",
        )
    )
    roteamento = estruturar_e_rotear(ENTRADA_PEDRO, llm).roteamento
    assert roteamento.entrada_suficiente is False
    assert roteamento.motivo_insuficiencia == "O relato não traz nenhuma dúvida."


def test_relato_sem_palavras_nem_chama_o_llm() -> None:
    entrada = {**ENTRADA_MARIANA, "consulta": {"relato_textual": "??? 123 !!!"}}
    llm = LLMFalso()
    contrato = estruturar_e_rotear(entrada, llm)
    assert llm.chamadas == []
    assert contrato.roteamento.rota_definida == "fora_de_escopo"
    assert contrato.roteamento.entrada_suficiente is False
    assert contrato.roteamento.motivo_insuficiencia == MOTIVO_RELATO_ININTELIGIVEL
    assert contrato.execucao.modelo_llm == "nao_acionado"
    assert contrato.execucao.tentativas_llm == 0


def test_saida_invalida_e_corrigida_na_segunda_tentativa() -> None:
    llm = LLMFalso('{"rota_definida": "triagem_vacinal"}', saida_llm())
    contrato = estruturar_e_rotear(ENTRADA_MARIANA, llm)
    assert contrato.roteamento.rota_definida == "triagem_vacinal"
    assert contrato.execucao.tentativas_llm == 2
    assert contrato.execucao.fallback_seguranca is False
    correcao = llm.chamadas[1][-1]["content"]
    assert "agentes_alvo" in correcao
    assert llm.chamadas[1][-2]["role"] == "assistant"


def test_rota_incoerente_tambem_e_tratada_como_saida_invalida() -> None:
    incoerente = saida_llm(agentes_alvo=["agente_medicamentos_condutas"])
    llm = LLMFalso(incoerente, "```json\n" + json.dumps(saida_llm()) + "\n```")
    contrato = estruturar_e_rotear(ENTRADA_MARIANA, llm)
    assert contrato.roteamento.agentes_alvo == ["agente_triagem_vacinal"]


def test_duas_saidas_invalidas_geram_fail_safe() -> None:
    llm = LLMFalso("não é json", '["lista"]')
    contrato = estruturar_e_rotear(ENTRADA_PEDRO, llm)
    roteamento = contrato.roteamento
    assert roteamento.rota_definida == "fora_de_escopo"
    assert roteamento.agentes_alvo == []
    assert roteamento.entrada_suficiente is False
    assert roteamento.motivo_insuficiencia == MOTIVO_FALHA_ESTRUTURACAO
    # Mesmo no fail-safe, as entidades do formulário são preservadas.
    assert roteamento.entidades_normalizadas.medicamentos_dcb == ["ibuprofeno"]
    assert contrato.execucao.fallback_seguranca is True


def test_llm_indisponivel_propaga_erro() -> None:
    with pytest.raises(ErroLLM):
        estruturar_e_rotear(ENTRADA_MARIANA, LLMQueFalha())


def test_entrada_invalida_levanta_validation_error() -> None:
    entrada = {**ENTRADA_MARIANA, "consulta": {"relato_textual": "oi"}}
    with pytest.raises(ValidationError):
        estruturar_e_rotear(entrada, LLMFalso())


def test_log_de_execucao_nao_tem_relato_nem_dados_pessoais(caplog) -> None:
    entrada = {
        **ENTRADA_PEDRO,
        "consulta": {
            **ENTRADA_PEDRO["consulta"],
            "relato_textual": "Sou Joana, CPF 123.456.789-00. Posso tomar Advil?",
        },
    }
    with caplog.at_level(logging.INFO, logger="src.agents.estruturador_roteador"):
        estruturar_e_rotear(entrada, LLMFalso(saida_llm()))

    registros = [r for r in caplog.records if hasattr(r, "registro_execucao")]
    assert len(registros) == 1
    registro = registros[0].registro_execucao
    assert registro["evento"] == "roteamento_concluido"
    assert registro["rota_definida"] == "triagem_vacinal"
    assert registro["versao_prompt"].startswith("prompts-v")
    assert registro["latencia_ms"] >= 0
    texto = caplog.text
    assert "Joana" not in texto
    assert "123.456.789-00" not in texto


def test_mensagens_separam_sistema_e_dados_do_usuario() -> None:
    llm = LLMFalso(saida_llm())
    estruturar_e_rotear(ENTRADA_MARIANA, llm)
    sistema, usuario = llm.chamadas[0]
    assert sistema["role"] == "system"
    assert "Estou grávida" not in sistema["content"]
    assert usuario["role"] == "user"
    assert "<entrada_consulta>" in usuario["content"]
    assert "Estou grávida de 20 semanas" in usuario["content"]


def test_hibrida_sem_vacina_nao_aciona_triagem_vacinal() -> None:
    # Caso real da avaliação (GD-08): dengue + dipirona virou híbrida com os
    # dois especialistas, sem nenhuma vacina na consulta.
    llm = LLMFalso(
        saida_llm(
            rota_definida="hibrida",
            agentes_alvo=["agente_triagem_vacinal", "agente_medicamentos_condutas"],
            entidades_normalizadas={
                "medicamentos_dcb": ["dipirona"],
                "vacinas": [],
                "doencas_suspeitas": ["dengue"],
                "sintomas": ["febre"],
            },
        )
    )
    roteamento = estruturar_e_rotear(ENTRADA_PEDRO, llm).roteamento
    assert roteamento.rota_definida == "hibrida"
    assert roteamento.agentes_alvo == ["agente_medicamentos_condutas"]
    assert "calendario_vacinal" not in roteamento.filtros_rag_recomendados.categorias


def test_hibrida_com_vacina_do_formulario_mantem_os_dois_agentes() -> None:
    entrada = {
        **ENTRADA_PEDRO,
        "consulta": {**ENTRADA_PEDRO["consulta"], "vacina_consultada": "Dengue"},
    }
    llm = LLMFalso(
        saida_llm(
            rota_definida="hibrida",
            agentes_alvo=["agente_triagem_vacinal", "agente_medicamentos_condutas"],
            entidades_normalizadas={},
        )
    )
    roteamento = estruturar_e_rotear(entrada, llm).roteamento
    assert roteamento.agentes_alvo == [
        "agente_triagem_vacinal",
        "agente_medicamentos_condutas",
    ]


def test_triagem_vacinal_sem_vacina_citada_continua_valida() -> None:
    # GD-05: "perdi meu cartão, quais vacinas preciso?" não cita vacina.
    llm = LLMFalso(saida_llm(entidades_normalizadas={}))
    entrada = {**ENTRADA_MARIANA, "consulta": {"relato_textual": "Quais vacinas?"}}
    roteamento = estruturar_e_rotear(entrada, llm).roteamento
    assert roteamento.agentes_alvo == ["agente_triagem_vacinal"]
