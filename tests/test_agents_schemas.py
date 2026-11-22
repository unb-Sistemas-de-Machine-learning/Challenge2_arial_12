import copy

import pytest
from pydantic import ValidationError

from src.agents.schemas import (
    EntradaConsulta,
    SaidaEstruturadorRoteador,
    SaidaMedicamentosCondutas,
    SaidaTriagemVacinal,
    maior_severidade,
)

# Exemplos da Seção 3.2 do contrato.
ENTRADA_MARIANA = {
    "request_id": "9f3b1c2e-7b4d-4d62-a2c9-5a8b6f1e4c11",
    "origem_entrada": "formulario_texto",
    "perfil_usuario": {
        "faixa_etaria": "adulto",
        "idade_anos": 32,
        "gestante": True,
        "semanas_gestacao": 20,
        "lactante": False,
        "comorbidades": [],
        "alergias_conhecidas": [],
    },
    "historico_vacinal": [
        {"vacina": "hepatite_b", "doses_tomadas": 3, "ano_ultima_dose": 2012},
        {"vacina": "dupla_adulto_dt", "doses_tomadas": 1, "ano_ultima_dose": 2014},
    ],
    "consulta": {
        "relato_textual": "Estou grávida de 20 semanas. Posso tomar dTpa?",
        "medicamento_consultado": None,
        "vacina_consultada": "dtpa",
        "suspeita_doenca": None,
    },
}

ENTRADA_PEDRO = {
    "perfil_usuario": {"faixa_etaria": "adulto", "idade_anos": 26, "gestante": False},
    "consulta": {
        "relato_textual": "Febre alta e dor no corpo. Posso tomar Ibuprofeno?",
        "medicamento_consultado": "Ibuprofeno",
        "suspeita_doenca": "dengue",
    },
}

ROTEAMENTO_PEDRO = {
    "rota_definida": "hibrida",
    "agentes_alvo": ["agente_medicamentos_condutas"],
    "entidades_normalizadas": {
        "medicamentos_dcb": ["ibuprofeno"],
        "vacinas": [],
        "doencas_suspeitas": ["dengue"],
        "sintomas": ["febre alta", "dor no corpo"],
    },
    "filtros_rag_recomendados": {
        "categorias": ["bula_medicamento", "protocolo_clinico"],
        "secoes_prioritarias": ["contraindicacoes", "manejo_clinico"],
        "publico_alvo": ["geral", "adulto", "pacientes_com_dengue"],
    },
    "dentro_do_escopo_mvp": True,
    "entrada_suficiente": True,
}


def evidencia(evidencia_id: str = "EV-01", **campos) -> dict:
    padrao = {
        "evidencia_id": evidencia_id,
        "chunk_id": f"chunk-{evidencia_id}",
        "orgao_emissor": "MINISTERIO_DA_SAUDE",
        "titulo_documento": "Dengue: diagnóstico e manejo clínico (6ª edição)",
        "categoria": "protocolo_clinico",
        "secao": "contraindicacoes",
        "publico_alvo": ["geral", "pacientes_com_dengue"],
        "trecho_literal": "Não utilizar salicilatos ou anti-inflamatórios não esteroides.",
        "score_similaridade": 0.93,
    }
    return {**padrao, **campos}


SAIDA_TRIAGEM_MARIANA = {
    "classificacao_parcial": "CONTRAINDICADA",
    "achados_estruturados": {
        "vacinas_em_dia": ["hepatite_b"],
        "vacinas_pendentes": [
            {
                "vacina": "dtpa",
                "status": "INDICADA",
                "justificativa": "Recomendada a partir da 20ª semana.",
                "evidencia_ids": ["EV-01"],
            },
            {
                "vacina": "dengue",
                "status": "CONTRAINDICADA",
                "justificativa": "Vacina de vírus vivo atenuado.",
                "evidencia_ids": ["EV-02"],
            },
        ],
        "resumo_agente": "dTpa indicada; vacina da dengue contraindicada.",
    },
    "evidencias_recuperadas": [
        evidencia("EV-01", categoria="calendario_vacinal", secao="esquema_vacinal"),
        evidencia("EV-02", orgao_emissor="ANVISA", categoria="bula_vacina"),
    ],
}

SAIDA_MEDICAMENTOS_PEDRO = {
    "classificacao_parcial": "ALERTA_RISCO_GRAVE",
    "achados_estruturados": {
        "medicamento_avaliado": "Ibuprofeno",
        "doenca_ou_condicao_contexto": "Suspeita de dengue",
        "status_uso": "CONTRAINDICADO",
        "condutas_seguras": ["Não usar anti-inflamatórios.", "Hidratação oral."],
        "sinais_de_alarme": ["Dor abdominal intensa e contínua"],
        "evidencia_ids": ["EV-01"],
        "resumo_agente": "Não tome ibuprofeno na suspeita de dengue.",
    },
    "evidencias_recuperadas": [evidencia("EV-01")],
}


def alterado(base: dict, caminho: str, valor) -> dict:
    copia = copy.deepcopy(base)
    alvo = copia
    *chaves, ultima = caminho.split(".")
    for chave in chaves:
        alvo = alvo[chave]
    alvo[ultima] = valor
    return copia


# --- Entrada -----------------------------------------------------------------


@pytest.mark.parametrize("payload", [ENTRADA_MARIANA, ENTRADA_PEDRO])
def test_exemplos_de_entrada_do_contrato_sao_validos(payload: dict) -> None:
    EntradaConsulta.model_validate(payload)


def test_entrada_aplica_padroes_do_contrato() -> None:
    entrada = EntradaConsulta.model_validate(ENTRADA_PEDRO)
    assert entrada.origem_entrada == "formulario_texto"
    assert entrada.historico_vacinal == []
    assert entrada.perfil_usuario.lactante is False


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        ("perfil_usuario.gestante", False),  # semanas sem gestação
        ("perfil_usuario.semanas_gestacao", 43),
        ("perfil_usuario.faixa_etaria", "bebe"),
        ("consulta.relato_textual", "oi"),
        ("consulta.vacina_consultada", "x" * 121),
        ("request_id", "nao-e-uuid"),
    ],
)
def test_entrada_invalida_e_rejeitada(caminho: str, valor) -> None:
    with pytest.raises(ValidationError):
        EntradaConsulta.model_validate(alterado(ENTRADA_MARIANA, caminho, valor))


def test_entrada_rejeita_campo_fora_do_contrato() -> None:
    with pytest.raises(ValidationError):
        EntradaConsulta.model_validate({**ENTRADA_PEDRO, "cpf": "000.000.000-00"})


# --- Estruturador/Roteador ---------------------------------------------------


def test_roteamento_valido() -> None:
    saida = SaidaEstruturadorRoteador.model_validate(ROTEAMENTO_PEDRO)
    assert saida.request_id is None


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ({"rota_definida": "fora_de_escopo"}, "não aciona agentes"),
        ({"rota_definida": "triagem_vacinal"}, "só aciona"),
        ({"agentes_alvo": []}, "só aciona"),
        ({"dentro_do_escopo_mvp": False}, "fora do escopo"),
        ({"entrada_suficiente": False}, "Entrada insuficiente"),
    ],
)
def test_roteamento_incoerente_e_rejeitado(campos: dict, mensagem: str) -> None:
    with pytest.raises(ValidationError, match=mensagem):
        SaidaEstruturadorRoteador.model_validate({**ROTEAMENTO_PEDRO, **campos})


def test_entrada_insuficiente_exige_motivo() -> None:
    base = {
        **ROTEAMENTO_PEDRO,
        "rota_definida": "fora_de_escopo",
        "agentes_alvo": [],
        "entrada_suficiente": False,
    }
    with pytest.raises(ValidationError, match="motivo_insuficiencia"):
        SaidaEstruturadorRoteador.model_validate(base)
    SaidaEstruturadorRoteador.model_validate(
        {**base, "motivo_insuficiencia": "Relato sem dúvida identificável."}
    )


# --- Triagem vacinal ---------------------------------------------------------


def test_triagem_valida() -> None:
    saida = SaidaTriagemVacinal.model_validate(SAIDA_TRIAGEM_MARIANA)
    assert saida.agente_origem == "agente_triagem_vacinal"


def test_triagem_exige_maior_severidade() -> None:
    payload = alterado(SAIDA_TRIAGEM_MARIANA, "classificacao_parcial", "INDICADA")
    with pytest.raises(ValidationError, match="pelo menos CONTRAINDICADA"):
        SaidaTriagemVacinal.model_validate(payload)


def test_triagem_rejeita_evidencia_citada_inexistente() -> None:
    payload = copy.deepcopy(SAIDA_TRIAGEM_MARIANA)
    payload["achados_estruturados"]["vacinas_pendentes"][0]["evidencia_ids"] = ["EV-99"]
    with pytest.raises(ValidationError, match="EV-99"):
        SaidaTriagemVacinal.model_validate(payload)


def test_triagem_sem_evidencia_nao_pode_recomendar() -> None:
    payload = alterado(SAIDA_TRIAGEM_MARIANA, "evidencias_recuperadas", [])
    with pytest.raises(ValidationError, match="ao menos uma evidência"):
        SaidaTriagemVacinal.model_validate(payload)


def test_triagem_evidencia_insuficiente_sem_itens() -> None:
    payload = alterado(
        SAIDA_TRIAGEM_MARIANA, "classificacao_parcial", "EVIDENCIA_INSUFICIENTE"
    )
    with pytest.raises(ValidationError, match="não pode trazer recomendação"):
        SaidaTriagemVacinal.model_validate(payload)

    payload["achados_estruturados"]["vacinas_pendentes"] = []
    payload["evidencias_recuperadas"] = []
    SaidaTriagemVacinal.model_validate(payload)


# --- Medicamentos e condutas -------------------------------------------------


def test_medicamentos_valido() -> None:
    saida = SaidaMedicamentosCondutas.model_validate(SAIDA_MEDICAMENTOS_PEDRO)
    assert saida.agente_origem == "agente_medicamentos_condutas"


def test_contraindicado_nao_pode_virar_indicada() -> None:
    payload = alterado(SAIDA_MEDICAMENTOS_PEDRO, "classificacao_parcial", "INDICADA")
    with pytest.raises(ValidationError, match="pelo menos CONTRAINDICADA"):
        SaidaMedicamentosCondutas.model_validate(payload)


def test_status_de_uso_exige_medicamento() -> None:
    payload = alterado(
        SAIDA_MEDICAMENTOS_PEDRO, "achados_estruturados.medicamento_avaliado", None
    )
    with pytest.raises(ValidationError, match="devem vir juntos"):
        SaidaMedicamentosCondutas.model_validate(payload)


def test_evidencia_de_orgao_nao_oficial_e_rejeitada() -> None:
    payload = alterado(
        SAIDA_MEDICAMENTOS_PEDRO,
        "evidencias_recuperadas",
        [evidencia("EV-01", orgao_emissor="FDA")],
    )
    with pytest.raises(ValidationError):
        SaidaMedicamentosCondutas.model_validate(payload)


def test_orientacao_geral_sem_medicamento() -> None:
    payload = copy.deepcopy(SAIDA_MEDICAMENTOS_PEDRO)
    payload["classificacao_parcial"] = "ORIENTACAO_GERAL"
    achados = payload["achados_estruturados"]
    achados["medicamento_avaliado"] = None
    achados["status_uso"] = None
    SaidaMedicamentosCondutas.model_validate(payload)


# --- Precedência de severidade -----------------------------------------------


@pytest.mark.parametrize(
    ("classificacoes", "esperado"),
    [
        (["INDICADA", "CONTRAINDICADA"], "CONTRAINDICADA"),
        (["ORIENTACAO_GERAL", "ALERTA_RISCO_GRAVE", "INDICADA"], "ALERTA_RISCO_GRAVE"),
        (["INDICADA", "ORIENTACAO_GERAL"], "ORIENTACAO_GERAL"),
        (["EVIDENCIA_INSUFICIENTE", "INDICADA"], "INDICADA"),
        (["EVIDENCIA_INSUFICIENTE"], "EVIDENCIA_INSUFICIENTE"),
        ([], "EVIDENCIA_INSUFICIENTE"),
    ],
)
def test_maior_severidade(classificacoes: list[str], esperado: str) -> None:
    assert maior_severidade(classificacoes) == esperado
