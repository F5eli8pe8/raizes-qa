from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest

from app.application.realizar_pedido import ComandoPedido, ItemSolicitado, RealizarPedido
from app.domain.cupom import Cupom
from app.domain.erros import CupomInvalido, ItemIndisponivel, PagamentoRecusado
from app.domain.estoque import Estoque
from app.domain.pedido import Canal, Status
from app.infrastructure.pagamento_mock import PagamentoMock
from app.infrastructure.repositorio_memoria import RepositorioPedidosMemoria

UNIDADE = "recife-centro"


def montar(cenario="aprovado", quantidades=None):
    quantidades = quantidades or {"tapioca": 5, "suco": 5, "cuscuz": 1}
    estoque = Estoque(quantidades)
    pagamento = PagamentoMock(cenario)
    repositorio = RepositorioPedidosMemoria()
    caso_de_uso = RealizarPedido(
        cardapios={UNIDADE: {"tapioca": 1200, "suco": 800, "cuscuz": 900, "pamonha": 700}},
        estoques={UNIDADE: estoque},
        cupons={"PROMO10": Cupom("PROMO10", 10, date(2026, 12, 31))},
        pagamento=pagamento,
        repositorio=repositorio,
        hoje=lambda: date(2026, 11, 20),
    )
    return caso_de_uso, repositorio, pagamento, estoque


def comando(itens, chave="k1", cupom=None, canal=Canal.APP):
    return ComandoPedido(
        unidade_id=UNIDADE,
        canal=canal,
        itens=[ItemSolicitado(item_id, qtd) for item_id, qtd in itens],
        chave_idempotencia=chave,
        codigo_cupom=cupom,
    )


@pytest.mark.unit
def test_ct01_pedido_aprovado_e_registrado_e_baixa_o_estoque():
    caso_de_uso, repositorio, _, estoque = montar()
    pedido = caso_de_uso.executar(comando([("tapioca", 2), ("suco", 1)]))
    assert pedido.status == Status.RECEBIDO
    assert pedido.total_centavos == 3200
    assert repositorio.obter(pedido.pedido_id) is pedido
    assert estoque.disponivel("tapioca") == 3


@pytest.mark.unit
def test_ct06_pagamento_recusado_nao_cria_pedido_e_devolve_o_estoque():
    caso_de_uso, repositorio, pagamento, estoque = montar(cenario="recusado")
    with pytest.raises(PagamentoRecusado, match="Pagamento não aprovado"):
        caso_de_uso.executar(comando([("tapioca", 2)]))
    assert repositorio.quantidade() == 0
    assert estoque.disponivel("tapioca") == 5

    pagamento.cenario = "aprovado"
    caso_de_uso.executar(comando([("tapioca", 2)], chave="k2"))
    assert repositorio.quantidade() == 1


@pytest.mark.unit
@pytest.mark.parametrize("cenario", ["timeout", "erro"])
def test_ct07_falha_do_pagamento_deixa_o_pedido_pendente(cenario):
    caso_de_uso, repositorio, _, estoque = montar(cenario=cenario)
    pedido = caso_de_uso.executar(comando([("tapioca", 2)]))
    assert pedido.status == Status.PENDENTE_PAGAMENTO
    assert repositorio.quantidade() == 1
    assert estoque.disponivel("tapioca") == 3


@pytest.mark.unit
def test_mesma_chave_de_idempotencia_nao_duplica_o_pedido():
    caso_de_uso, repositorio, pagamento, _ = montar()
    primeiro = caso_de_uso.executar(comando([("tapioca", 1)], chave="k1"))
    segundo = caso_de_uso.executar(comando([("tapioca", 1)], chave="k1"))
    assert primeiro.pedido_id == segundo.pedido_id
    assert repositorio.quantidade() == 1
    assert len(pagamento.chamadas) == 1


@pytest.mark.unit
def test_ct08_segundo_pedido_da_ultima_unidade_e_recusado():
    caso_de_uso, repositorio, _, _ = montar()
    caso_de_uso.executar(comando([("cuscuz", 1)], chave="k1"))
    with pytest.raises(ItemIndisponivel, match="Item indisponível no momento"):
        caso_de_uso.executar(comando([("cuscuz", 1)], chave="k2"))
    assert repositorio.quantidade() == 1


@pytest.mark.unit
def test_ct08_pedidos_simultaneos_da_ultima_unidade_aceitam_apenas_um():
    caso_de_uso, repositorio, _, _ = montar()
    largada = Barrier(2)

    def pedir(chave):
        largada.wait()
        try:
            caso_de_uso.executar(comando([("cuscuz", 1)], chave=chave))
            return "aceito"
        except ItemIndisponivel:
            return "recusado"

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = sorted(pool.map(pedir, ["k1", "k2"]))

    assert resultados == ["aceito", "recusado"]
    assert repositorio.quantidade() == 1


@pytest.mark.unit
def test_reserva_parcial_e_desfeita_quando_um_item_esta_esgotado():
    quantidades = {"tapioca": 5, "pamonha": 0}
    caso_de_uso, _, _, estoque = montar(quantidades=quantidades)
    with pytest.raises(ItemIndisponivel):
        caso_de_uso.executar(comando([("tapioca", 2), ("pamonha", 1)]))
    assert estoque.disponivel("tapioca") == 5


@pytest.mark.unit
def test_cupom_valido_reduz_o_total_do_pedido():
    caso_de_uso, _, _, _ = montar()
    pedido = caso_de_uso.executar(comando([("tapioca", 2), ("suco", 1)], cupom="PROMO10"))
    assert pedido.total_centavos == 2880


@pytest.mark.unit
def test_cupom_desconhecido_e_rejeitado_sem_reservar_estoque():
    caso_de_uso, _, _, estoque = montar()
    with pytest.raises(CupomInvalido, match="Cupom inválido ou expirado."):
        caso_de_uso.executar(comando([("tapioca", 2)], cupom="NAOEXISTE"))
    assert estoque.disponivel("tapioca") == 5


@pytest.mark.unit
def test_rl09_pagamento_recebe_somente_id_valor_e_chave():
    caso_de_uso, _, pagamento, _ = montar()
    pedido = caso_de_uso.executar(comando([("tapioca", 1)], chave="k1"))
    assert pagamento.chamadas == [(pedido.pedido_id, 1200, "k1")]