import pytest

from app.domain.erros import ItemIndisponivel
from app.domain.estoque import Estoque


@pytest.mark.unit
def test_reservar_reduz_o_disponivel():
    estoque = Estoque({"tapioca": 2})
    estoque.reservar("tapioca", 1)
    assert estoque.disponivel("tapioca") == 1


@pytest.mark.unit
def test_ct08_ultima_unidade_atende_apenas_uma_reserva():
    estoque = Estoque({"cuscuz": 1})
    estoque.reservar("cuscuz", 1)
    with pytest.raises(ItemIndisponivel, match="Item indisponível no momento"):
        estoque.reservar("cuscuz", 1)


@pytest.mark.unit
def test_liberar_devolve_a_reserva_ao_disponivel():
    estoque = Estoque({"cuscuz": 1})
    estoque.reservar("cuscuz", 1)
    estoque.liberar("cuscuz", 1)
    assert estoque.disponivel("cuscuz") == 1


@pytest.mark.unit
def test_confirmar_da_baixa_definitiva_e_impede_liberar_depois():
    estoque = Estoque({"cuscuz": 1})
    estoque.reservar("cuscuz", 1)
    estoque.confirmar("cuscuz", 1)
    assert estoque.disponivel("cuscuz") == 0
    with pytest.raises(ValueError):
        estoque.liberar("cuscuz", 1)


@pytest.mark.unit
def test_item_inexistente_esta_indisponivel():
    estoque = Estoque({"cuscuz": 1})
    with pytest.raises(ItemIndisponivel):
        estoque.reservar("pamonha", 1)


@pytest.mark.unit
@pytest.mark.parametrize("quantidade", [0, -1])
def test_quantidade_invalida_e_rejeitada(quantidade):
    estoque = Estoque({"cuscuz": 5})
    with pytest.raises(ValueError):
        estoque.reservar("cuscuz", quantidade)