import pytest
import requests

from src.ui import cliente

PAYLOAD = {"request_id": "abc"}


class RespostaFalsa:
    def __init__(self, status_code: int, corpo: object) -> None:
        self.status_code = status_code
        self.ok = status_code < 400
        self._corpo = corpo

    def json(self) -> object:
        if isinstance(self._corpo, Exception):
            raise self._corpo
        return self._corpo


def test_sem_url_usa_modo_demonstracao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(cliente.VARIAVEL_URL_API, raising=False)

    resposta = cliente.consultar(PAYLOAD)

    assert resposta["modo_demonstracao"] is True
    assert resposta["request_id"] == "abc"
    # Guardrail: sem evidência, nunca há recomendação.
    assert resposta["evidencias_oficiais"] == []
    assert resposta["classificacao_risco"] == "EVIDENCIA_INSUFICIENTE"
    assert resposta["disclaimer_medico"]


def test_url_vem_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cliente.VARIAVEL_URL_API, " http://localhost:8000/ ")
    assert cliente.url_api() == "http://localhost:8000"


def test_envia_payload_para_a_rota_de_consulta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas = []

    def post_falso(url, json, timeout):
        chamadas.append((url, json))
        return RespostaFalsa(200, {"classificacao_risco": "INDICADA"})

    monkeypatch.setattr(cliente.requests, "post", post_falso)

    resposta = cliente.consultar(PAYLOAD, base_url="http://api")

    assert resposta == {"classificacao_risco": "INDICADA"}
    assert chamadas == [("http://api/api/v1/consultar", PAYLOAD)]


def test_erro_da_api_usa_a_mensagem_do_contrato(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpo = {"erro": {"codigo": "PAYLOAD_INVALIDO", "mensagem": "Campo inválido."}}
    monkeypatch.setattr(
        cliente.requests, "post", lambda *a, **k: RespostaFalsa(422, corpo)
    )

    with pytest.raises(cliente.ErroConsulta, match="Campo inválido."):
        cliente.consultar(PAYLOAD, base_url="http://api")


def test_erro_sem_corpo_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cliente.requests, "post", lambda *a, **k: RespostaFalsa(500, ValueError())
    )

    with pytest.raises(cliente.ErroConsulta, match="HTTP 500"):
        cliente.consultar(PAYLOAD, base_url="http://api")


def test_api_fora_do_ar(monkeypatch: pytest.MonkeyPatch) -> None:
    def post_falso(*args, **kwargs):
        raise requests.ConnectionError

    monkeypatch.setattr(cliente.requests, "post", post_falso)

    with pytest.raises(cliente.ErroConsulta, match="Não foi possível conectar"):
        cliente.consultar(PAYLOAD, base_url="http://api")
