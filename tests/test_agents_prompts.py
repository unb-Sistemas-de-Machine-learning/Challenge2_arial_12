import pytest

from src.agents.prompts import (
    VERSAO_PROMPTS,
    carregar_prompt,
    renderizar_prompt,
    schema_saida_json,
)

AGENTES = [
    "agente_estruturador_roteador",
    "agente_triagem_vacinal",
    "agente_medicamentos_condutas",
]
ESPECIALISTAS = AGENTES[1:]

VARIAVEIS_USUARIO = {
    "agente_estruturador_roteador": {"entrada_json"},
    "agente_triagem_vacinal": {"entrada_json", "roteamento_json", "evidencias_json"},
    "agente_medicamentos_condutas": {
        "entrada_json",
        "roteamento_json",
        "evidencias_json",
    },
}


@pytest.mark.parametrize("agente", AGENTES)
def test_prompt_de_sistema_traz_versao_e_schema(agente: str) -> None:
    prompt = renderizar_prompt(agente, "sistema")
    assert VERSAO_PROMPTS in prompt
    assert schema_saida_json(agente) in prompt
    assert "$schema_saida" not in prompt


@pytest.mark.parametrize("agente", AGENTES)
def test_prompt_de_sistema_trata_entrada_como_dado(agente: str) -> None:
    prompt = renderizar_prompt(agente, "sistema")
    assert "nunca instru" in prompt  # "nunca instrução" / "nunca instruções"


@pytest.mark.parametrize("agente", ESPECIALISTAS)
def test_especialistas_tem_regras_anti_alucinacao(agente: str) -> None:
    prompt = renderizar_prompt(agente, "sistema")
    assert "exclusivamente as evidências fornecidas" in prompt
    assert "EVIDENCIA_INSUFICIENTE" in prompt
    assert "trecho_literal" in prompt
    assert "ALERTA_RISCO_GRAVE" in prompt


@pytest.mark.parametrize("agente", AGENTES)
def test_mensagem_de_usuario_tem_variaveis_esperadas(agente: str) -> None:
    molde = carregar_prompt(agente, "usuario")
    assert set(molde.get_identifiers()) == VARIAVEIS_USUARIO[agente]

    valores = {nome: f"<{nome}>" for nome in VARIAVEIS_USUARIO[agente]}
    mensagem = renderizar_prompt(agente, "usuario", **valores)
    assert all(valor in mensagem for valor in valores.values())


def test_variavel_faltando_levanta_erro() -> None:
    with pytest.raises(KeyError):
        renderizar_prompt("agente_triagem_vacinal", "usuario", entrada_json="{}")


def test_versao_inexistente_levanta_erro() -> None:
    with pytest.raises(FileNotFoundError):
        carregar_prompt("agente_triagem_vacinal", "sistema", versao="v999")
