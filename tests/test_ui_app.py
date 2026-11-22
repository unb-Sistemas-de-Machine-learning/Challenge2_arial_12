from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "ui" / "app.py")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.delenv("EVIDENCIA_API_URL", raising=False)
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    assert not app.exception
    return app


def test_tela_abre_sem_login_em_modo_demonstracao(app: AppTest) -> None:
    assert app.title[0].value == "EvidencIA Saúde"
    assert any("Modo demonstração" in info.value for info in app.info)


def test_envio_vazio_mostra_erro(app: AppTest) -> None:
    app.button[0].click().run()

    assert any("Descreva sua dúvida" in erro.value for erro in app.error)
    assert "resultado" not in app.session_state


def test_consulta_valida_mostra_resultado(app: AppTest) -> None:
    app.text_area(key="relato").input("Estou com febre alta, posso tomar ibuprofeno?")
    app.checkbox(key="vacina_dtpa").check().run()
    app.button[0].click().run()

    assert not app.exception
    assert not app.error
    assert "resultado" in app.session_state
    resposta, payload = app.session_state["resultado"]
    assert resposta["classificacao_risco"] == "EVIDENCIA_INSUFICIENTE"
    assert payload["historico_vacinal"] == [
        {"vacina": "dtpa", "doses_tomadas": 1, "ano_ultima_dose": None}
    ]


def test_gestante_mostra_campo_de_semanas(app: AppTest) -> None:
    quantidade_antes = len(app.number_input)
    app.toggle(key="gestante").set_value(True).run()
    assert len(app.number_input) == quantidade_antes + 1
