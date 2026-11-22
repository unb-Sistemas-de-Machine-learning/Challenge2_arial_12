"""Interface unificada de consulta do EvidencIA Saúde (issue #12).

Executar na raiz do repositório:

    uv run streamlit run src/ui/app.py

Sem a variável ``EVIDENCIA_API_URL``, a interface roda em modo demonstração.
O painel completo de resposta (selo, evidências e condutas) é a issue #17.
"""

from __future__ import annotations

import sys
from pathlib import Path

# O `streamlit run` coloca apenas a pasta deste arquivo no sys.path.
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

import streamlit as st

from src.ui.cliente import (
    DISCLAIMER_PADRAO,
    ErroConsulta,
    consultar,
    url_api,
)
from src.ui.contrato import (
    ALERGIAS,
    ANO_DOSE_MAX,
    ANO_DOSE_MIN,
    COMORBIDADES,
    DOENCAS_SUSPEITAS,
    IDADE_MAX,
    RELATO_MAX,
    SEMANAS_GESTACAO_MAX,
    SEMANAS_GESTACAO_MIN,
    TEXTO_CURTO_MAX,
    VACINAS,
    FormularioConsulta,
    VacinaTomada,
    montar_payload,
    validar,
)

SELOS = {
    "INDICADA": (st.success, "Indicada"),
    "CONTRAINDICADA": (st.warning, "Contraindicada"),
    "ALERTA_RISCO_GRAVE": (st.error, "Alerta de risco grave"),
    "ORIENTACAO_GERAL": (st.info, "Orientação geral"),
    "EVIDENCIA_INSUFICIENTE": (st.info, "Evidência insuficiente"),
}


def secao_perfil() -> dict:
    st.subheader("1. Seu perfil")
    col_idade, col_gestante, col_lactante = st.columns([1, 1, 1])
    idade = col_idade.number_input(
        "Idade (anos)", min_value=0, max_value=IDADE_MAX, value=30, step=1
    )
    gestante = col_gestante.toggle("Estou gestante", key="gestante")
    lactante = col_lactante.toggle("Estou amamentando", key="lactante")

    semanas = None
    if gestante:
        semanas = st.number_input(
            "Semana de gestação (opcional)",
            min_value=SEMANAS_GESTACAO_MIN,
            max_value=SEMANAS_GESTACAO_MAX,
            value=None,
            step=1,
            placeholder="Ex.: 20",
        )

    col_comorb, col_alerg = st.columns(2)
    comorbidades = col_comorb.multiselect(
        "Condições de saúde (opcional)",
        options=list(COMORBIDADES),
        format_func=COMORBIDADES.get,
        placeholder="Selecione, se houver",
    )
    alergias = col_alerg.multiselect(
        "Alergias conhecidas (opcional)",
        options=list(ALERGIAS),
        format_func=ALERGIAS.get,
        placeholder="Selecione, se houver",
    )
    return {
        "idade_anos": int(idade),
        "gestante": gestante,
        "semanas_gestacao": int(semanas) if semanas is not None else None,
        "lactante": lactante,
        "comorbidades": comorbidades,
        "alergias_conhecidas": alergias,
    }


def secao_vacinas() -> list[VacinaTomada]:
    st.subheader("2. Vacinas que você já tomou")
    st.caption(
        "Marque as vacinas que constam no seu cartão. Se não souber, deixe em branco."
    )
    tomadas: list[VacinaTomada] = []
    for chave, rotulo in VACINAS.items():
        marcada = st.checkbox(rotulo, key=f"vacina_{chave}")
        if not marcada:
            continue
        col_doses, col_ano, _ = st.columns([1, 1, 2])
        doses = col_doses.number_input(
            "Doses tomadas",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            key=f"doses_{chave}",
        )
        ano = col_ano.number_input(
            "Ano da última dose (opcional)",
            min_value=ANO_DOSE_MIN,
            max_value=ANO_DOSE_MAX,
            value=None,
            step=1,
            placeholder="Ex.: 2014",
            key=f"ano_{chave}",
        )
        tomadas.append(
            VacinaTomada(
                vacina=chave,
                doses_tomadas=int(doses),
                ano_ultima_dose=int(ano) if ano is not None else None,
            )
        )
    return tomadas


def secao_consulta() -> dict:
    st.subheader("3. Sua dúvida")
    relato = st.text_area(
        "Descreva seus sintomas ou sua dúvida",
        max_chars=RELATO_MAX,
        placeholder=(
            "Ex.: Estou com febre alta e dor no corpo desde ontem, suspeito de "
            "dengue. Posso tomar ibuprofeno?"
        ),
        key="relato",
    )
    col_doenca, col_med, col_vac = st.columns(3)
    doenca = col_doenca.selectbox(
        "Doença suspeita (opcional)",
        options=[None, *DOENCAS_SUSPEITAS],
        format_func=lambda chave: (
            "Nenhuma / não sei" if chave is None else DOENCAS_SUSPEITAS[chave]
        ),
    )
    medicamento = col_med.text_input(
        "Remédio que pretende tomar (opcional)",
        max_chars=TEXTO_CURTO_MAX,
        placeholder="Ex.: Ibuprofeno",
    )
    vacina = col_vac.text_input(
        "Vacina sobre a qual tem dúvida (opcional)",
        max_chars=TEXTO_CURTO_MAX,
        placeholder="Ex.: dTpa",
    )
    return {
        "relato_textual": relato,
        "suspeita_doenca": doenca,
        "medicamento_consultado": medicamento,
        "vacina_consultada": vacina,
    }


def exibir_resposta(resposta: dict, payload: dict) -> None:
    st.divider()
    st.subheader("Resultado")
    classificacao = resposta.get("classificacao_risco", "EVIDENCIA_INSUFICIENTE")
    exibir, rotulo = SELOS.get(classificacao, (st.info, classificacao))
    exibir(f"**{rotulo}**\n\n{resposta.get('resumo_decisao', '')}")

    if resposta.get("modo_demonstracao"):
        with st.expander("Dados que serão enviados aos agentes (modo demonstração)"):
            st.json(payload)

    # O aviso padrão já fica fixo no rodapé; aqui só entra um aviso específico da API.
    disclaimer = resposta.get("disclaimer_medico")
    if disclaimer and disclaimer != DISCLAIMER_PADRAO:
        st.caption(disclaimer)


def main() -> None:
    st.set_page_config(page_title="EvidencIA Saúde", page_icon="🩺", layout="wide")
    st.title("EvidencIA Saúde")
    st.write(
        "Tire dúvidas sobre vacinas, sintomas e medicamentos com base em "
        "documentos oficiais da Anvisa e do Ministério da Saúde. "
        "Não é preciso criar conta, e nenhum dado pessoal é armazenado."
    )
    if url_api() is None:
        st.info(
            "Modo demonstração: a API ainda não está conectada. "
            "Defina a variável EVIDENCIA_API_URL para usar a API real.",
            icon="ℹ️",
        )

    perfil = secao_perfil()
    vacinas = secao_vacinas()
    consulta = secao_consulta()

    if st.button("Consultar", type="primary", use_container_width=True):
        form = FormularioConsulta(**perfil, **consulta, historico_vacinal=vacinas)
        erros = validar(form)
        if erros:
            st.session_state.pop("resultado", None)
            for erro in erros:
                st.error(erro)
        else:
            payload = montar_payload(form)
            with st.spinner("Consultando os agentes de saúde..."):
                try:
                    resposta = consultar(payload)
                except ErroConsulta as exc:
                    st.session_state.pop("resultado", None)
                    st.error(str(exc))
                else:
                    st.session_state["resultado"] = (resposta, payload)

    if "resultado" in st.session_state:
        exibir_resposta(*st.session_state["resultado"])

    st.caption(DISCLAIMER_PADRAO)


main()
