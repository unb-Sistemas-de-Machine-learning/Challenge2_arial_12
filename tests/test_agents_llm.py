import pytest
import requests

from src.agents import llm as modulo_llm
from src.agents.llm import (
    BASE_URL_PADRAO,
    MODELO_PADRAO,
    ClienteOpenAICompativel,
    ConfigLLM,
    ErroLLM,
)

MENSAGENS = [{"role": "user", "content": "oi"}]
SCHEMA = {"type": "object"}


class RespostaFalsa:
    def __init__(self, status_code=200, corpo=None, headers=None):
        self.status_code = status_code
        self._corpo = corpo
        self.headers = headers or {}
        self.text = str(corpo)

    def json(self):
        if self._corpo is None:
            raise ValueError("sem json")
        return self._corpo


class SessaoFalsa:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.requisicoes = []

    def post(self, url, json, headers, timeout):
        self.requisicoes.append({"url": url, "json": json, "headers": headers})
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def ok(conteudo='{"a": 1}'):
    return RespostaFalsa(200, {"choices": [{"message": {"content": conteudo}}]})


def cliente(sessao, **config):
    return ClienteOpenAICompativel(ConfigLLM(api_key="chave-teste", **config), sessao)


def test_envia_structured_output_com_temperatura_zero() -> None:
    sessao = SessaoFalsa(ok())
    assert cliente(sessao).gerar_json(MENSAGENS, SCHEMA, "saida") == '{"a": 1}'

    requisicao = sessao.requisicoes[0]
    assert requisicao["url"] == f"{BASE_URL_PADRAO}/chat/completions"
    assert requisicao["headers"]["Authorization"] == "Bearer chave-teste"
    corpo = requisicao["json"]
    assert corpo["model"] == MODELO_PADRAO
    assert corpo["temperature"] == 0
    assert corpo["response_format"]["type"] == "json_schema"
    assert corpo["response_format"]["json_schema"]["schema"] == SCHEMA


def test_modo_json_object() -> None:
    sessao = SessaoFalsa(ok())
    cliente(sessao, modo_json="json_object").gerar_json(MENSAGENS, SCHEMA, "saida")
    assert sessao.requisicoes[0]["json"]["response_format"] == {"type": "json_object"}


def test_espera_e_repete_quando_ha_limite_de_taxa(monkeypatch) -> None:
    esperas = []
    monkeypatch.setattr(modulo_llm.time, "sleep", esperas.append)
    sessao = SessaoFalsa(RespostaFalsa(429, {}, {"retry-after": "1.5"}), ok())
    assert cliente(sessao).gerar_json(MENSAGENS, SCHEMA, "saida") == '{"a": 1}'
    assert esperas == [1.5]


def test_erro_http_vira_erro_llm() -> None:
    sessao = SessaoFalsa(RespostaFalsa(401, {"error": {"message": "chave inválida"}}))
    with pytest.raises(ErroLLM, match="401.*chave inválida"):
        cliente(sessao).gerar_json(MENSAGENS, SCHEMA, "saida")


def test_falha_de_conexao_vira_erro_llm() -> None:
    sessao = SessaoFalsa(requests.ConnectionError("sem rede"))
    with pytest.raises(ErroLLM, match="conexão"):
        cliente(sessao).gerar_json(MENSAGENS, SCHEMA, "saida")


@pytest.mark.parametrize("corpo", [{}, {"choices": []}, None])
def test_resposta_fora_do_formato(corpo) -> None:
    with pytest.raises(ErroLLM):
        cliente(SessaoFalsa(RespostaFalsa(200, corpo))).gerar_json(
            MENSAGENS, SCHEMA, "saida"
        )


def test_resposta_vazia() -> None:
    with pytest.raises(ErroLLM, match="vazia"):
        cliente(SessaoFalsa(ok("  "))).gerar_json(MENSAGENS, SCHEMA, "saida")


def test_config_do_ambiente(monkeypatch) -> None:
    for nome in (
        "EVIDENCIA_LLM_API_KEY",
        "EVIDENCIA_LLM_BASE_URL",
        "EVIDENCIA_LLM_MODELO",
        "EVIDENCIA_LLM_MODO_JSON",
    ):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-teste")
    config = ConfigLLM.do_ambiente()
    assert config.api_key == "gsk-teste"
    assert config.base_url == BASE_URL_PADRAO
    assert config.modelo == MODELO_PADRAO

    monkeypatch.setenv("EVIDENCIA_LLM_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("EVIDENCIA_LLM_MODELO", "qwen2.5:7b")
    config = ConfigLLM.do_ambiente()
    assert config.base_url == "http://localhost:11434/v1"
    assert config.modelo == "qwen2.5:7b"


def test_config_sem_chave(monkeypatch) -> None:
    monkeypatch.delenv("EVIDENCIA_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ErroLLM, match="API_KEY"):
        ConfigLLM.do_ambiente()


@pytest.mark.parametrize(
    ("mensagem", "espera"),
    [
        ("Please try again in 967.5ms. Need more tokens?", 1.4675),
        ("Please try again in 30.6225s. Need more tokens?", 31.1225),
        ("Please try again in 1m2.5s.", 60.0),
    ],
)
def test_espera_o_tempo_sugerido_na_mensagem_do_groq(
    monkeypatch, mensagem, espera
) -> None:
    esperas = []
    monkeypatch.setattr(modulo_llm.time, "sleep", esperas.append)
    limite = RespostaFalsa(429, {"error": {"message": mensagem}}, {"retry-after": "9"})
    cliente(SessaoFalsa(limite, ok())).gerar_json(MENSAGENS, SCHEMA, "saida")
    assert esperas == [pytest.approx(espera)]


def test_desiste_depois_de_esgotar_as_esperas(monkeypatch) -> None:
    monkeypatch.setattr(modulo_llm.time, "sleep", lambda _: None)
    limite = RespostaFalsa(429, {}, {"retry-after": "1"})
    sessao = SessaoFalsa(*[limite] * (modulo_llm.MAX_ESPERAS_LIMITE + 1))
    with pytest.raises(ErroLLM, match="429"):
        cliente(sessao).gerar_json(MENSAGENS, SCHEMA, "saida")
