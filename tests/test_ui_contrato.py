import pytest

from src.ui.contrato import (
    FormularioConsulta,
    VacinaTomada,
    faixa_etaria,
    montar_payload,
    validar,
)


def formulario(**campos) -> FormularioConsulta:
    padrao = {"idade_anos": 26, "relato_textual": "Estou com febre alta."}
    return FormularioConsulta(**{**padrao, **campos})


@pytest.mark.parametrize(
    ("idade", "esperado"),
    [
        (0, "crianca"),
        (11, "crianca"),
        (12, "adolescente"),
        (18, "adulto"),
        (60, "idoso"),
    ],
)
def test_faixa_etaria(idade: int, esperado: str) -> None:
    assert faixa_etaria(idade) == esperado


def test_formulario_valido_nao_tem_erros() -> None:
    assert validar(formulario()) == []


@pytest.mark.parametrize("relato", ["", "   ", "abc"])
def test_relato_vazio_ou_curto_e_rejeitado(relato: str) -> None:
    assert validar(formulario(relato_textual=relato))


def test_relato_longo_demais_e_rejeitado() -> None:
    assert validar(formulario(relato_textual="a" * 2001))


def test_semana_de_gestacao_fora_do_intervalo_e_rejeitada() -> None:
    assert validar(formulario(gestante=True, semanas_gestacao=50))


def test_vacina_sem_doses_e_rejeitada() -> None:
    form = formulario(historico_vacinal=[VacinaTomada("dtpa", doses_tomadas=0)])
    assert validar(form)


def test_vacina_desconhecida_e_rejeitada() -> None:
    form = formulario(historico_vacinal=[VacinaTomada("bcg_x", doses_tomadas=1)])
    assert validar(form)


def test_payload_segue_o_contrato_da_jornada_mariana() -> None:
    form = formulario(
        idade_anos=32,
        gestante=True,
        semanas_gestacao=20,
        relato_textual="  Quais vacinas faltam para mim?  ",
        historico_vacinal=[
            VacinaTomada("hepatite_b", 3, 2012),
            VacinaTomada("dupla_adulto_dt", 1, 2014),
        ],
        vacina_consultada="dtpa",
    )

    payload = montar_payload(form, request_id="abc")

    assert payload == {
        "request_id": "abc",
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
            "relato_textual": "Quais vacinas faltam para mim?",
            "medicamento_consultado": None,
            "vacina_consultada": "dtpa",
            "suspeita_doenca": None,
        },
    }


def test_semanas_de_gestacao_sao_ignoradas_se_nao_gestante() -> None:
    payload = montar_payload(formulario(gestante=False, semanas_gestacao=20))
    assert payload["perfil_usuario"]["semanas_gestacao"] is None


def test_payload_gera_request_id_sem_dados_pessoais() -> None:
    payload = montar_payload(formulario())
    assert len(payload["request_id"]) == 36
    assert set(payload["perfil_usuario"]) == {
        "faixa_etaria",
        "idade_anos",
        "gestante",
        "semanas_gestacao",
        "lactante",
        "comorbidades",
        "alergias_conhecidas",
    }
