"""Cliente de LLM compatível com a API de Chat Completions da OpenAI.

O MVP usa o plano gratuito do **Groq** (ADR-001, custo zero), mas o cliente
serve a qualquer provedor com ``POST /chat/completions`` no padrão OpenAI
(Ollama, Gemini, OpenRouter...): basta trocar as variáveis de ambiente.

Variáveis de ambiente:

* ``EVIDENCIA_LLM_API_KEY`` (ou ``GROQ_API_KEY``): chave do provedor;
* ``EVIDENCIA_LLM_BASE_URL``: URL base (padrão: API do Groq);
* ``EVIDENCIA_LLM_MODELO``: modelo (padrão: ``openai/gpt-oss-20b``);
* ``EVIDENCIA_LLM_MODO_JSON``: ``json_schema`` (padrão, *Structured Output*) ou
  ``json_object`` para modelos sem suporte a schema.

A temperatura é 0: o roteamento precisa ser o mais reprodutível possível.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import requests

BASE_URL_PADRAO = "https://api.groq.com/openai/v1"
MODELO_PADRAO = "openai/gpt-oss-20b"
TIMEOUT_SEGUNDOS = 60
# O plano gratuito do Groq limita tokens por minuto (TPM): uma consulta pode
# precisar esperar até ~1 min pela janela seguinte.
MAX_ESPERAS_LIMITE = 6
ESPERA_MAXIMA_SEGUNDOS = 60.0
_TENTE_DE_NOVO_EM = re.compile(r"try again in (?:(\d+)m)?([\d.]+)(ms|s)", re.IGNORECASE)

ModoJson = Literal["json_schema", "json_object"]
Mensagem = dict[str, str]


class ErroLLM(Exception):
    """Provedor de LLM indisponível ou sem resposta utilizável.

    A API REST traduz este erro para ``503 SERVICO_INDISPONIVEL`` (Seção 6 do
    contrato). A mensagem nunca traz o conteúdo da consulta.
    """


class ClienteLLM(Protocol):
    """Interface mínima que os agentes usam para falar com um LLM."""

    @property
    def modelo(self) -> str: ...

    def gerar_json(
        self, mensagens: list[Mensagem], schema: dict[str, Any], nome_schema: str
    ) -> str:
        """Devolve o texto da resposta, que deve ser um objeto JSON."""
        ...


@dataclass(frozen=True)
class ConfigLLM:
    api_key: str
    base_url: str = BASE_URL_PADRAO
    modelo: str = MODELO_PADRAO
    modo_json: ModoJson = "json_schema"
    timeout_segundos: float = TIMEOUT_SEGUNDOS

    @classmethod
    def do_ambiente(cls) -> ConfigLLM:
        chave = (
            os.environ.get("EVIDENCIA_LLM_API_KEY") or os.environ.get("GROQ_API_KEY")
        ) or ""
        if not chave.strip():
            raise ErroLLM(
                "Defina EVIDENCIA_LLM_API_KEY (ou GROQ_API_KEY) para usar o LLM."
            )
        modo = os.environ.get("EVIDENCIA_LLM_MODO_JSON", "json_schema").strip()
        if modo not in ("json_schema", "json_object"):
            raise ErroLLM(
                "EVIDENCIA_LLM_MODO_JSON deve ser json_schema ou json_object."
            )
        return cls(
            api_key=chave.strip(),
            base_url=(
                os.environ.get("EVIDENCIA_LLM_BASE_URL", "").strip().rstrip("/")
                or BASE_URL_PADRAO
            ),
            modelo=os.environ.get("EVIDENCIA_LLM_MODELO", "").strip() or MODELO_PADRAO,
            modo_json=modo,  # type: ignore[arg-type]
        )


class ClienteOpenAICompativel:
    """Cliente HTTP para ``/chat/completions`` com saída em JSON."""

    def __init__(
        self, config: ConfigLLM, sessao: requests.Session | None = None
    ) -> None:
        self._config = config
        self._sessao = sessao or requests.Session()

    @classmethod
    def do_ambiente(cls) -> ClienteOpenAICompativel:
        return cls(ConfigLLM.do_ambiente())

    @property
    def modelo(self) -> str:
        return self._config.modelo

    def _formato_resposta(
        self, schema: dict[str, Any], nome_schema: str
    ) -> dict[str, Any]:
        if self._config.modo_json == "json_object":
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {"name": nome_schema, "schema": schema, "strict": False},
        }

    def gerar_json(
        self, mensagens: list[Mensagem], schema: dict[str, Any], nome_schema: str
    ) -> str:
        corpo = {
            "model": self._config.modelo,
            "messages": mensagens,
            "temperature": 0,
            "response_format": self._formato_resposta(schema, nome_schema),
        }
        url = f"{self._config.base_url}/chat/completions"
        cabecalhos = {"Authorization": f"Bearer {self._config.api_key}"}

        for tentativa in range(MAX_ESPERAS_LIMITE + 1):
            try:
                resposta = self._sessao.post(
                    url,
                    json=corpo,
                    headers=cabecalhos,
                    timeout=self._config.timeout_segundos,
                )
            except requests.RequestException as erro:
                raise ErroLLM(
                    f"Falha de conexão com o LLM: {type(erro).__name__}."
                ) from erro

            if resposta.status_code == 429 and tentativa < MAX_ESPERAS_LIMITE:
                # Limite de taxa do plano gratuito: espera e tenta de novo.
                time.sleep(_segundos_de_espera(resposta, tentativa))
                continue
            if resposta.status_code >= 400:
                raise ErroLLM(
                    f"O LLM respondeu HTTP {resposta.status_code}: "
                    f"{_mensagem_de_erro(resposta)}"
                )
            try:
                conteudo = resposta.json()["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as erro:
                raise ErroLLM("Resposta do LLM fora do formato esperado.") from erro
            if not isinstance(conteudo, str) or not conteudo.strip():
                raise ErroLLM("O LLM devolveu uma resposta vazia.")
            return conteudo

        raise ErroLLM("Limite de requisições do LLM excedido.")


def _segundos_de_espera(resposta: requests.Response, tentativa: int) -> float:
    """Usa o tempo sugerido pelo provedor (mensagem ou ``retry-after``)."""
    sugestao = _TENTE_DE_NOVO_EM.search(_mensagem_de_erro(resposta))
    if sugestao:
        minutos, valor, unidade = sugestao.groups()
        valor = float(valor) / (1000 if unidade.lower() == "ms" else 1)
        valor += 60 * int(minutos or 0) + 0.5  # margem para a janela virar
    else:
        try:
            valor = float(resposta.headers.get("retry-after", ""))
        except ValueError:
            valor = 2.0 * (2**tentativa)
    return min(max(valor, 0.5), ESPERA_MAXIMA_SEGUNDOS)


def _mensagem_de_erro(resposta: requests.Response) -> str:
    try:
        erro = resposta.json().get("error", {})
        mensagem = erro.get("message") if isinstance(erro, dict) else str(erro)
    except ValueError:
        mensagem = resposta.text
    return (mensagem or "sem detalhes")[:300]
