"""Normalização determinística das entidades clínicas da consulta.

O LLM extrai entidades do relato livre, mas os nomes variam ("AAS",
"Aspirina", "ácido acetilsalicílico"). Este módulo converte tudo para as
chaves do contrato e completa as entidades com os campos estruturados do
formulário, para que a mesma consulta gere sempre o mesmo JSON
(critério de aceite da issue #13).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# Medicamentos do escopo do MVP: nome comercial, sigla ou grafia -> DCB.
MEDICAMENTOS_MVP = frozenset(
    {"ibuprofeno", "acido_acetilsalicilico", "dipirona", "paracetamol"}
)
SINONIMOS_MEDICAMENTOS: dict[str, str] = {
    "advil": "ibuprofeno",
    "alivium": "ibuprofeno",
    "buscofem": "ibuprofeno",
    "ibuprofen": "ibuprofeno",
    "aas": "acido_acetilsalicilico",
    "aspirina": "acido_acetilsalicilico",
    "acido_acetil_salicilico": "acido_acetilsalicilico",
    "melhoral": "acido_acetilsalicilico",
    "novalgina": "dipirona",
    "dipirona_sodica": "dipirona",
    "dipirona_monoidratada": "dipirona",
    "metamizol": "dipirona",
    "anador": "dipirona",
    "tylenol": "paracetamol",
    "acetaminofeno": "paracetamol",
    "acetaminofen": "paracetamol",
}

# Vacinas do calendário adulto/gestante (mesmas chaves do checklist da UI).
VACINAS_MVP = frozenset(
    {
        "hepatite_b",
        "dupla_adulto_dt",
        "dtpa",
        "triplice_viral",
        "febre_amarela",
        "influenza",
        "dengue",
    }
)
SINONIMOS_VACINAS: dict[str, str] = {
    "hepb": "hepatite_b",
    "hep_b": "hepatite_b",
    "vacina_hepatite_b": "hepatite_b",
    "dt": "dupla_adulto_dt",
    "dupla_adulto": "dupla_adulto_dt",
    "dupla_bacteriana": "dupla_adulto_dt",
    "difteria_e_tetano": "dupla_adulto_dt",
    "antitetanica": "dupla_adulto_dt",
    "tetano": "dupla_adulto_dt",
    "dtpa_adulto": "dtpa",
    "triplice_bacteriana_acelular": "dtpa",
    "triplice_bacteriana_acelular_do_tipo_adulto": "dtpa",
    "triplice_viral_scr": "triplice_viral",
    "scr": "triplice_viral",
    "sarampo_caxumba_rubeola": "triplice_viral",
    "sarampo_caxumba_e_rubeola": "triplice_viral",
    "fa": "febre_amarela",
    "vacina_febre_amarela": "febre_amarela",
    "gripe": "influenza",
    "vacina_da_gripe": "influenza",
    "vacina_gripe": "influenza",
    "qdenga": "dengue",
    "vacina_dengue": "dengue",
    "vacina_da_dengue": "dengue",
}

DOENCAS_MVP = frozenset({"dengue", "malaria", "gripe"})
SINONIMOS_DOENCAS: dict[str, str] = {
    "influenza": "gripe",
    "sindrome_gripal": "gripe",
    "gripe_sindrome_gripal": "gripe",
    "paludismo": "malaria",
}

# Comorbidade do formulário -> público-alvo do RAG.
PUBLICO_POR_COMORBIDADE: dict[str, str] = {"imunossuprimido": "imunossuprimido"}
PUBLICO_POR_DOENCA: dict[str, str] = {
    "dengue": "pacientes_com_dengue",
    "malaria": "pacientes_com_malaria",
    "gripe": "pacientes_com_gripe",
}

_SEPARADORES = re.compile(r"[,;/]")
_NAO_PALAVRA = re.compile(r"[^a-z0-9]+")


def chave(texto: str) -> str:
    """Minúsculas, sem acento, com ``_`` no lugar de espaços e pontuação."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    )
    return _NAO_PALAVRA.sub("_", sem_acento.lower()).strip("_")


def _canonica(texto: str, sinonimos: dict[str, str]) -> str:
    valor = chave(texto)
    for prefixo in ("vacina_", "vacina_contra_", "vacina_da_", "vacina_de_"):
        if valor not in sinonimos and valor.startswith(prefixo):
            sem_prefixo = valor.removeprefix(prefixo)
            if sem_prefixo in sinonimos or sem_prefixo in VACINAS_MVP:
                valor = sem_prefixo
    return sinonimos.get(valor, valor)


def normalizar_medicamento(nome: str) -> str:
    return _canonica(nome, SINONIMOS_MEDICAMENTOS)


def normalizar_vacina(nome: str) -> str:
    return _canonica(nome, SINONIMOS_VACINAS)


def normalizar_doenca(nome: str) -> str:
    return _canonica(nome, SINONIMOS_DOENCAS)


def separar_itens(texto: str | None) -> list[str]:
    """Divide campos com vários itens ("febre_amarela, dengue, dtpa")."""
    if not texto:
        return []
    return [parte.strip() for parte in _SEPARADORES.split(texto) if parte.strip()]


def unir(*listas: Iterable[str]) -> list[str]:
    """Une listas sem repetir e preserva a ordem da primeira ocorrência."""
    vistos: dict[str, None] = {}
    for lista in listas:
        for item in lista:
            item = item.strip()
            if item:
                vistos.setdefault(item, None)
    return list(vistos)


def normalizar_sintoma(texto: str) -> str:
    """Sintomas ficam em linguagem simples: só limpa espaços e caixa."""
    return " ".join(texto.split()).lower()
