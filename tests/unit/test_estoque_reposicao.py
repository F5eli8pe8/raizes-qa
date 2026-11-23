import pytest

from app.domain.estoque import Estoque


@pytest.mark.unit
def test_repor_devolve_item_com_baixa_ja_confirmada():
    estoque = Estoque({"cuscuz": 1})
    estoque.reservar("cuscuz", 1)
    estoque.confirmar("cuscuz", 1)
    estoque.repor("cuscuz", 1)
    assert estoque.disponivel("cuscuz") == 1


@pytest.mark.unit
def test_repor_quantidade_invalida_e_rejeitado():
    with pytest.raises(ValueError):
        Estoque({"cuscuz": 1}).repor("cuscuz", 0)