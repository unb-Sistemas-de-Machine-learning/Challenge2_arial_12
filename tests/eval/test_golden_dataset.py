import json

import pytest
from pydantic import ValidationError

from src.eval.golden_dataset import (
    CAMINHO_PADRAO,
    GoldenDataset,
    carregar_golden_dataset,
)


@pytest.fixture(scope="module")
def dataset() -> GoldenDataset:
    return carregar_golden_dataset()


@pytest.fixture
def bruto() -> dict:
    return json.loads(CAMINHO_PADRAO.read_text(encoding="utf-8"))


def status_dos_itens(dataset: GoldenDataset, tema: str) -> dict[str, set[str]]:
    itens: dict[str, set[str]] = {}
    for caso in dataset.casos:
        if caso.tema == tema:
            for item in caso.gabarito.status_por_item:
                itens.setdefault(item.item, set()).add(item.status)
    return itens


def test_tem_pelo_menos_10_casos(dataset: GoldenDataset) -> None:
    assert len(dataset.casos) >= 10


def test_tem_pelo_menos_2_casos_de_abstinencia(dataset: GoldenDataset) -> None:
    abstinencias = [c for c in dataset.casos if c.gabarito.deve_abster]
    assert len(abstinencias) >= 2
    assert all(c.tema == "fora_de_escopo" for c in abstinencias)


def test_cobre_vacinacao_na_gestacao(dataset: GoldenDataset) -> None:
    itens = status_dos_itens(dataset, "vacinacao_gestacao")
    assert "INDICADA" in itens["dtpa"]
    assert "CONTRAINDICADA" in itens["febre_amarela"]
    assert "CONTRAINDICADA" in itens["dengue"]
    for caso in dataset.casos:
        if caso.tema == "vacinacao_gestacao":
            assert caso.entrada.perfil_usuario.gestante


@pytest.mark.parametrize("medicamento", ["ibuprofeno", "acido_acetilsalicilico"])
def test_aine_e_aas_na_dengue_geram_alerta_grave(
    dataset: GoldenDataset, medicamento: str
) -> None:
    casos = [
        c
        for c in dataset.casos
        if c.entrada.consulta.suspeita_doenca == "dengue"
        and any(i.item == medicamento for i in c.gabarito.status_por_item)
    ]
    assert casos
    for caso in casos:
        assert caso.critico
        assert caso.gabarito.classificacao_risco_esperada == "ALERTA_RISCO_GRAVE"


def test_cobre_dipirona_e_paracetamol(dataset: GoldenDataset) -> None:
    itens = status_dos_itens(dataset, "interacao_medicamentosa")
    assert "INDICADO" in itens["dipirona"]
    assert "CONTRAINDICADO" in itens["dipirona"]
    assert "INDICADO" in itens["paracetamol"]


def test_cobre_manejo_de_dengue_e_malaria(dataset: GoldenDataset) -> None:
    doencas = {
        c.entrada.consulta.suspeita_doenca
        for c in dataset.casos
        if c.tema == "manejo_doenca"
    }
    assert {"dengue", "malaria"} <= doencas


def test_casos_com_recomendacao_citam_fonte_oficial(dataset: GoldenDataset) -> None:
    for caso in dataset.casos:
        if caso.gabarito.deve_abster:
            continue
        for fonte in caso.gabarito.fontes_esperadas:
            doc = dataset.documento(fonte.doc_id)
            assert doc.orgao_emissor in {"ANVISA", "MINISTERIO_DA_SAUDE"}


def test_casos_criticos_esperam_contraindicacao_ou_alerta(
    dataset: GoldenDataset,
) -> None:
    assert dataset.casos_criticos
    for caso in dataset.casos_criticos:
        assert caso.gabarito.classificacao_risco_esperada in {
            "CONTRAINDICADA",
            "ALERTA_RISCO_GRAVE",
        }


def test_rejeita_id_de_caso_repetido(bruto: dict) -> None:
    bruto["casos"][1]["id"] = bruto["casos"][0]["id"]
    with pytest.raises(ValidationError, match="IDs de casos repetidos"):
        GoldenDataset.model_validate(bruto)


def test_rejeita_fonte_fora_do_catalogo(bruto: dict) -> None:
    bruto["casos"][0]["gabarito"]["fontes_esperadas"][0]["doc_id"] = "DOC-INEXISTENTE"
    with pytest.raises(ValidationError, match="fora de documentos_referencia"):
        GoldenDataset.model_validate(bruto)


def test_rejeita_abstinencia_com_fonte(bruto: dict) -> None:
    abstinencia = next(c for c in bruto["casos"] if c["gabarito"]["deve_abster"])
    abstinencia["gabarito"]["fontes_esperadas"] = [
        bruto["casos"][0]["gabarito"]["fontes_esperadas"][0]
    ]
    with pytest.raises(ValidationError, match="abstinência"):
        GoldenDataset.model_validate(bruto)


def test_rejeita_caso_critico_com_selo_nao_critico(bruto: dict) -> None:
    caso = next(c for c in bruto["casos"] if c["critico"])
    caso["gabarito"]["classificacao_risco_esperada"] = "INDICADA"
    with pytest.raises(ValidationError, match="caso crítico"):
        GoldenDataset.model_validate(bruto)


def test_rejeita_entrada_fora_do_contrato(bruto: dict) -> None:
    bruto["casos"][0]["entrada"]["consulta"]["relato_textual"] = "oi"
    with pytest.raises(ValidationError):
        GoldenDataset.model_validate(bruto)
