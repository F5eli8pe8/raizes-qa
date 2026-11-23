from datetime import date

import pytest

from app.domain.cupom import Cupom
from app.domain.erros import CancelamentoNegado, CupomInvalido, TransicaoInvalida
from app.domain.pedido import Canal, ItemPedido, Pedido, Status

HOJE = date(2026, 11, 20)


def criar_pedido():
    itens = [
        ItemPedido("tapioca", quantidade=2, preco_unitario_centavos=1200),
        ItemPedido("suco", quantidade=1, preco_unitario_centavos=800),
    ]
    return Pedido("P-001", "recife-centro", Canal.APP, itens)


@pytest.mark.unit
def test_total_soma_os_itens_sem_cupom():
    assert criar_pedido().total_centavos == 3200


@pytest.mark.unit
def test_cupom_valido_reduz_o_total():
    pedido = criar_pedido()
    pedido.aplicar_cupom(Cupom("PROMO10", 10, date(2026, 12, 31)), HOJE)
    assert pedido.total_centavos == 2880


@pytest.mark.unit
def test_ct10_cupom_expirado_mantem_o_total_inalterado():
    pedido = criar_pedido()
    with pytest.raises(CupomInvalido):
        pedido.aplicar_cupom(Cupom("PROMO10", 10, date(2026, 11, 19)), HOJE)
    assert pedido.total_centavos == 3200


@pytest.mark.unit
def test_pedido_sem_itens_e_rejeitado():
    with pytest.raises(ValueError):
        Pedido("P-002", "recife-centro", Canal.WEB, [])


@pytest.mark.unit
def test_item_com_quantidade_zero_e_rejeitado():
    with pytest.raises(ValueError):
        ItemPedido("tapioca", quantidade=0, preco_unitario_centavos=1200)


@pytest.mark.unit
def test_fluxo_completo_de_status():
    pedido = criar_pedido()
    assert pedido.status == Status.AGUARDANDO_PAGAMENTO
    pedido.confirmar_pagamento()
    pedido.iniciar_preparo()
    pedido.marcar_pronto()
    pedido.registrar_retirada()
    assert pedido.status == Status.RETIRADO


@pytest.mark.unit
def test_pagamento_pendente_pode_ser_confirmado_depois():
    pedido = criar_pedido()
    pedido.marcar_pagamento_pendente()
    assert pedido.status == Status.PENDENTE_PAGAMENTO
    pedido.confirmar_pagamento()
    assert pedido.status == Status.RECEBIDO


@pytest.mark.unit
def test_ct11_cancelar_antes_do_preparo():
    pedido = criar_pedido()
    pedido.confirmar_pagamento()
    pedido.cancelar()
    assert pedido.status == Status.CANCELADO


@pytest.mark.unit
def test_ct11_cancelar_em_preparo_e_negado():
    pedido = criar_pedido()
    pedido.confirmar_pagamento()
    pedido.iniciar_preparo()
    with pytest.raises(CancelamentoNegado, match="já está em preparo"):
        pedido.cancelar()
    assert pedido.status == Status.EM_PREPARO


@pytest.mark.unit
def test_transicao_fora_de_ordem_e_rejeitada():
    pedido = criar_pedido()
    with pytest.raises(TransicaoInvalida):
        pedido.iniciar_preparo()


@pytest.mark.unit
def test_pedido_cancelado_nao_pode_ser_confirmado():
    pedido = criar_pedido()
    pedido.cancelar()
    with pytest.raises(TransicaoInvalida):
        pedido.confirmar_pagamento()