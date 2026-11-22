"""Montagem e validação do payload de entrada de ``POST /api/v1/consultar``.

Segue o contrato descrito em ``docs/arquitetura/contrato-json-e-metadados-rag.md``
(Seção 3). O módulo não depende do Streamlit, para poder ser testado isoladamente.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

RELATO_MIN = 5
RELATO_MAX = 2000
TEXTO_CURTO_MAX = 120
IDADE_MAX = 120
SEMANAS_GESTACAO_MIN = 1
SEMANAS_GESTACAO_MAX = 42
ANO_DOSE_MIN = 1950
ANO_DOSE_MAX = 2026

# Vacinas do calendário adulto/gestante usadas no checklist (chave do contrato -> rótulo).
VACINAS: dict[str, str] = {
    "hepatite_b": "Hepatite B",
    "dupla_adulto_dt": "Dupla adulto (dT — difteria e tétano)",
    "dtpa": "dTpa (difteria, tétano e coqueluche)",
    "triplice_viral": "Tríplice viral (sarampo, caxumba e rubéola)",
    "febre_amarela": "Febre amarela",
    "influenza": "Influenza (gripe)",
    "dengue": "Dengue",
}

COMORBIDADES: dict[str, str] = {
    "hipertensao": "Hipertensão",
    "diabetes": "Diabetes",
    "imunossuprimido": "Imunossupressão",
    "doenca_hepatica": "Doença hepática",
    "doenca_renal": "Doença renal",
}

ALERGIAS: dict[str, str] = {
    "aines": "Anti-inflamatórios (AINEs)",
    "dipirona": "Dipirona",
    "paracetamol": "Paracetamol",
    "acido_acetilsalicilico": "Ácido acetilsalicílico (AAS)",
    "ovo": "Ovo",
}

DOENCAS_SUSPEITAS: dict[str, str] = {
    "dengue": "Dengue",
    "malaria": "Malária",
    "gripe": "Gripe / síndrome gripal",
}


@dataclass
class VacinaTomada:
    vacina: str
    doses_tomadas: int
    ano_ultima_dose: int | None = None


@dataclass
class FormularioConsulta:
    """Dados preenchidos na tela de consulta."""

    idade_anos: int
    relato_textual: str
    gestante: bool = False
    semanas_gestacao: int | None = None
    lactante: bool = False
    comorbidades: list[str] = field(default_factory=list)
    alergias_conhecidas: list[str] = field(default_factory=list)
    historico_vacinal: list[VacinaTomada] = field(default_factory=list)
    medicamento_consultado: str = ""
    vacina_consultada: str = ""
    suspeita_doenca: str | None = None


def faixa_etaria(idade_anos: int) -> str:
    """Converte a idade na faixa etária do contrato."""
    if idade_anos < 12:
        return "crianca"
    if idade_anos < 18:
        return "adolescente"
    if idade_anos < 60:
        return "adulto"
    return "idoso"


def validar(form: FormularioConsulta) -> list[str]:
    """Retorna a lista de erros do formulário (vazia quando ele é válido)."""
    erros: list[str] = []

    relato = form.relato_textual.strip()
    if not relato:
        erros.append("Descreva sua dúvida, sintomas ou o que deseja saber.")
    elif len(relato) < RELATO_MIN:
        erros.append(f"O relato precisa ter pelo menos {RELATO_MIN} caracteres.")
    elif len(relato) > RELATO_MAX:
        erros.append(f"O relato pode ter no máximo {RELATO_MAX} caracteres.")

    if not 0 <= form.idade_anos <= IDADE_MAX:
        erros.append(f"Informe uma idade entre 0 e {IDADE_MAX} anos.")

    if form.gestante:
        semanas = form.semanas_gestacao
        if semanas is not None and not (
            SEMANAS_GESTACAO_MIN <= semanas <= SEMANAS_GESTACAO_MAX
        ):
            erros.append(
                "A semana de gestação deve estar entre "
                f"{SEMANAS_GESTACAO_MIN} e {SEMANAS_GESTACAO_MAX}."
            )

    for campo, valor in (
        ("medicamento", form.medicamento_consultado),
        ("vacina consultada", form.vacina_consultada),
    ):
        if len(valor.strip()) > TEXTO_CURTO_MAX:
            erros.append(
                f"O campo {campo} pode ter no máximo {TEXTO_CURTO_MAX} caracteres."
            )

    for item in form.historico_vacinal:
        rotulo = VACINAS.get(item.vacina, item.vacina)
        if item.vacina not in VACINAS:
            erros.append(f"Vacina desconhecida no checklist: {item.vacina}.")
        if item.doses_tomadas < 1:
            erros.append(f"{rotulo}: informe pelo menos 1 dose.")
        ano = item.ano_ultima_dose
        if ano is not None and not ANO_DOSE_MIN <= ano <= ANO_DOSE_MAX:
            erros.append(
                f"{rotulo}: o ano da última dose deve estar entre "
                f"{ANO_DOSE_MIN} e {ANO_DOSE_MAX}."
            )

    if form.suspeita_doenca is not None and form.suspeita_doenca not in (
        DOENCAS_SUSPEITAS
    ):
        erros.append(f"Doença suspeita desconhecida: {form.suspeita_doenca}.")

    return erros


def _texto_ou_none(valor: str) -> str | None:
    valor = valor.strip()
    return valor or None


def montar_payload(
    form: FormularioConsulta, request_id: str | None = None
) -> dict[str, object]:
    """Converte o formulário no JSON de entrada da API.

    Não inclui nenhum dado pessoal identificável (LGPD): o ``request_id`` é um
    UUID efêmero, usado apenas para correlacionar a consulta com o feedback.
    """
    return {
        "request_id": request_id or str(uuid.uuid4()),
        "origem_entrada": "formulario_texto",
        "perfil_usuario": {
            "faixa_etaria": faixa_etaria(form.idade_anos),
            "idade_anos": form.idade_anos,
            "gestante": form.gestante,
            "semanas_gestacao": form.semanas_gestacao if form.gestante else None,
            "lactante": form.lactante,
            "comorbidades": list(form.comorbidades),
            "alergias_conhecidas": list(form.alergias_conhecidas),
        },
        "historico_vacinal": [
            {
                "vacina": item.vacina,
                "doses_tomadas": item.doses_tomadas,
                "ano_ultima_dose": item.ano_ultima_dose,
            }
            for item in form.historico_vacinal
        ],
        "consulta": {
            "relato_textual": form.relato_textual.strip(),
            "medicamento_consultado": _texto_ou_none(form.medicamento_consultado),
            "vacina_consultada": _texto_ou_none(form.vacina_consultada),
            "suspeita_doenca": form.suspeita_doenca,
        },
    }
