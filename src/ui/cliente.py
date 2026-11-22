"""Cliente HTTP da interface para a API REST do EvidencIA Saúde.

Enquanto a API (issue #21) não existe, a interface funciona em **modo
demonstração**: sem ``EVIDENCIA_API_URL`` definida, a consulta devolve uma
resposta simulada e segura, no formato do contrato de saída.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import requests

VARIAVEL_URL_API = "EVIDENCIA_API_URL"
ROTA_CONSULTAR = "/api/v1/consultar"
TIMEOUT_SEGUNDOS = 90

DISCLAIMER_PADRAO = (
    "Aviso importante: o EvidencIA Saúde é um assistente informativo baseado em "
    "documentos oficiais da Anvisa e do Ministério da Saúde. Ele não realiza "
    "diagnóstico médico, não substitui consulta profissional e não prescreve "
    "medicamentos ou vacinas. Em caso de sinais de alarme ou emergência, procure "
    "imediatamente uma UPA, pronto-socorro ou ligue para o SAMU (192)."
)


class ErroConsulta(Exception):
    """Falha ao consultar a API, com mensagem pronta para o usuário."""


def url_api() -> str | None:
    """URL base da API configurada no ambiente, ou ``None`` no modo demonstração."""
    valor = os.environ.get(VARIAVEL_URL_API, "").strip().rstrip("/")
    return valor or None


def resposta_demonstracao(payload: dict) -> dict:
    """Resposta simulada usada quando a API ainda não está configurada.

    Por segurança, não inventa orientação clínica: devolve
    ``EVIDENCIA_INSUFICIENTE`` sem evidências, como manda o guardrail do contrato.
    """
    return {
        "request_id": payload["request_id"],
        "timestamp_resposta": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rota_acionada": "evidencia_insuficiente",
        "agentes_executados": [],
        "classificacao_risco": "EVIDENCIA_INSUFICIENTE",
        "resumo_decisao": (
            "Modo demonstração: a API do EvidencIA Saúde ainda não está conectada, "
            "então nenhuma orientação foi gerada. Seus dados foram validados e "
            "montados no formato que será enviado aos agentes."
        ),
        "detalhamento_vacinal": None,
        "detalhamento_clinico_medicamentoso": None,
        "evidencias_oficiais": [],
        "disclaimer_medico": DISCLAIMER_PADRAO,
        "metadados_execucao": {
            "versao_pipeline": "demonstracao",
            "versao_prompt": None,
            "versao_indice_rag": None,
            "modelo_llm": None,
            "latencia_ms": 0,
        },
        "modo_demonstracao": True,
    }


def _mensagem_de_erro(resposta: requests.Response) -> str:
    try:
        erro = resposta.json().get("erro", {})
    except ValueError:
        erro = {}
    mensagem = erro.get("mensagem") if isinstance(erro, dict) else None
    return mensagem or f"A API respondeu com erro HTTP {resposta.status_code}."


def consultar(payload: dict, base_url: str | None = None) -> dict:
    """Envia a consulta à API e devolve o JSON de resposta.

    Sem ``base_url`` (nem ``EVIDENCIA_API_URL``), usa a resposta de demonstração.
    """
    base_url = base_url or url_api()
    if base_url is None:
        return resposta_demonstracao(payload)

    try:
        resposta = requests.post(
            f"{base_url}{ROTA_CONSULTAR}", json=payload, timeout=TIMEOUT_SEGUNDOS
        )
    except requests.Timeout as exc:
        raise ErroConsulta(
            "A consulta demorou demais para responder. Tente novamente."
        ) from exc
    except requests.RequestException as exc:
        raise ErroConsulta(
            "Não foi possível conectar à API do EvidencIA Saúde. "
            "Verifique se ela está em execução."
        ) from exc

    if not resposta.ok:
        raise ErroConsulta(_mensagem_de_erro(resposta))

    try:
        return resposta.json()
    except ValueError as exc:
        raise ErroConsulta("A API devolveu uma resposta em formato inválido.") from exc
