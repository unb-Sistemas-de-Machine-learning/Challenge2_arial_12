"""Prompts versionados dos 3 agentes do EvidencIA Saúde.

Cada versão fica em uma pasta (``v1/``) com uma subpasta por agente e dois
arquivos Markdown:

* ``sistema.md``: regras fixas do agente e schema de saída;
* ``usuario.md``: molde da mensagem com os dados da consulta.

Os dados do usuário e as evidências do RAG vão sempre na mensagem de usuário,
nunca no prompt de sistema, para reduzir o efeito de injeção de prompt.

Os arquivos usam placeholders de ``string.Template`` (``$variavel``), que não
colidem com as chaves dos exemplos em JSON. ``$schema_saida`` e
``$versao_prompt`` são preenchidos automaticamente no prompt de sistema.

Qualquer mudança no texto de um prompt exige subir ``VERSAO_PROMPTS``, que é
registrada no MLflow (issues #18 e #20) e em ``metadados_execucao.versao_prompt``.
"""

from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Literal

from src.agents.schemas import SCHEMA_SAIDA_POR_AGENTE, AgenteId

VERSAO_PROMPTS = "prompts-v1.0.0"
VERSAO_PADRAO = "v1"

ParteDoPrompt = Literal["sistema", "usuario"]

_DIRETORIO = Path(__file__).parent


def carregar_prompt(
    agente: AgenteId, parte: ParteDoPrompt, versao: str = VERSAO_PADRAO
) -> Template:
    """Lê o molde de um prompt sem preencher os placeholders."""
    caminho = _DIRETORIO / versao / agente / f"{parte}.md"
    if not caminho.is_file():
        raise FileNotFoundError(f"Prompt não encontrado: {caminho}")
    return Template(caminho.read_text(encoding="utf-8"))


def schema_saida_json(agente: AgenteId) -> str:
    """JSON Schema de saída do agente, como é injetado no prompt de sistema."""
    schema = SCHEMA_SAIDA_POR_AGENTE[agente].model_json_schema()
    return json.dumps(schema, ensure_ascii=False, indent=2)


def renderizar_prompt(
    agente: AgenteId,
    parte: ParteDoPrompt,
    versao: str = VERSAO_PADRAO,
    **variaveis: str,
) -> str:
    """Preenche o molde; levanta ``KeyError`` se faltar alguma variável."""
    if parte == "sistema":
        variaveis.setdefault("schema_saida", schema_saida_json(agente))
        variaveis.setdefault("versao_prompt", VERSAO_PROMPTS)
    return carregar_prompt(agente, parte, versao).substitute(variaveis)
