import pytest

from src.agents.normalizacao import (
    MEDICAMENTOS_MVP,
    VACINAS_MVP,
    chave,
    normalizar_doenca,
    normalizar_medicamento,
    normalizar_sintoma,
    normalizar_vacina,
    separar_itens,
    unir,
)


def test_chave_remove_acentos_e_espacos() -> None:
    assert chave("  Ácido Acetilsalicílico ") == "acido_acetilsalicilico"
    assert chave("Febre-amarela") == "febre_amarela"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Advil", "ibuprofeno"),
        ("AAS", "acido_acetilsalicilico"),
        ("Aspirina", "acido_acetilsalicilico"),
        ("ácido acetilsalicílico", "acido_acetilsalicilico"),
        ("Novalgina", "dipirona"),
        ("Tylenol", "paracetamol"),
        ("Paracetamol", "paracetamol"),
        ("Clonazepam", "clonazepam"),
    ],
)
def test_normalizar_medicamento(entrada, esperado) -> None:
    assert normalizar_medicamento(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("dTpa", "dtpa"),
        ("Febre amarela", "febre_amarela"),
        ("vacina da febre amarela", "febre_amarela"),
        ("Dengue", "dengue"),
        ("Qdenga", "dengue"),
        ("dT", "dupla_adulto_dt"),
        ("vacina da gripe", "influenza"),
        ("Hepatite B", "hepatite_b"),
        ("HPV", "hpv"),
    ],
)
def test_normalizar_vacina(entrada, esperado) -> None:
    assert normalizar_vacina(entrada) == esperado


def test_normalizar_doenca() -> None:
    assert normalizar_doenca("Malária") == "malaria"
    assert normalizar_doenca("Síndrome gripal") == "gripe"


def test_chaves_do_mvp_ja_estao_normalizadas() -> None:
    assert all(normalizar_medicamento(m) == m for m in MEDICAMENTOS_MVP)
    assert all(normalizar_vacina(v) == v for v in VACINAS_MVP)


def test_separar_itens() -> None:
    assert separar_itens("febre_amarela, dengue; dtpa") == [
        "febre_amarela",
        "dengue",
        "dtpa",
    ]
    assert separar_itens("Difteria e tétano") == ["Difteria e tétano"]
    assert separar_itens(None) == []


def test_unir_preserva_ordem_sem_repetir() -> None:
    assert unir(["a", "b"], ["b", " ", "c"], ["a"]) == ["a", "b", "c"]


def test_normalizar_sintoma() -> None:
    assert normalizar_sintoma("  Dor   no Corpo ") == "dor no corpo"
