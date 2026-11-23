from datetime import date

import pytest

from app.application.gerir_pedido import (
    AtualizarStatusPedido,
    CancelarPedido,
    ConsultarPedido,
    PedidoNaoEncontrado,
)
from app.application.realizar_pedido import ComandoPedido, ItemSolicitado, RealizarPedido
from app.domain.erros import CancelamentoNegado, TransicaoInvalida
from app.domain.estoque import Estoque
from app.domain.pedido import Canal, Status
from app.infrastructure.pagamento_mock import PagamentoMock
from app.infrastructure.repositorio_memoria import RepositorioPedidosMemoria

UNIDADE = "recife-centro"


class Ambiente:
    def __init__(self, cenario="aprovado"):
        self.estoque = Estoque({"tapioca": 5})
        self.pagamento = PagamentoMock(cenario)
        self.repositorio = RepositorioPedidosMemoria()
        estoques = {UNIDADE: self.estoque}
        self.realizar = RealizarPedido(
            cardapios={UNIDADE: {"tapioca": 1200}},
            estoques=estoques,
            cupons={},
            pagamento=self.pagamento,
            repositorio=self.repositorio,
            hoje=lambda: date(2026, 11, 20),
        )
        self.cancelar = CancelarPedido(self.repositorio, estoques, self.pagamento)
        self.atualizar = AtualizarStatusPedido(self.repositorio)
        self.consultar = ConsultarPedido(self.repositorio)

    def pedir(self, quantidade=2):
        comando = ComandoPedido(
            UNIDADE, Canal.APP, [ItemSolicitado("tapioca", quantidade)], "k1"
        )
        return self.realizar.executar(comando)


@pytest.mark.unit
def test_ct11_cancelar_antes_do_preparo_estorna_e_repoe_o_estoque():
    ambiente = Ambiente()
    pedido = ambiente.pedir(quantidade=2)
    assert ambiente.estoque.disponivel("tapioca") == 3

    cancelado = ambiente.cancelar.executar(pedido.pedido_id)

    assert cancelado.status == Status.CANCELADO
    assert ambiente.pagamento.estornos == [pedido.pedido_id]
    assert ambiente.estoque.disponivel("tapioca") == 5


@pytest.mark.unit
def test_ct11_cancelar_em_preparo_e_negado_sem_efeitos():
    ambiente = Ambiente()
    pedido = ambiente.pedir(quantidade=2)
    ambiente.atualizar.executar(pedido.pedido_id, "Em preparo")

    with pytest.raises(CancelamentoNegado, match="já está em preparo"):
        ambiente.cancelar.executar(pedido.pedido_id)

    assert pedido.status == Status.EM_PREPARO
    assert ambiente.pagamento.estornos == []
    assert ambiente.estoque.disponivel("tapioca") == 3


@pytest.mark.unit
def test_cancelar_pedido_pendente_libera_a_reserva_sem_estorno():
    ambiente = Ambiente(cenario="timeout")
    pedido = ambiente.pedir(quantidade=2)
    assert pedido.status == Status.PENDENTE_PAGAMENTO

    ambiente.cancelar.executar(pedido.pedido_id)

    assert ambiente.pagamento.estornos == []
    assert ambiente.estoque.disponivel("tapioca") == 5


@pytest.mark.unit
def test_atendente_avanca_o_status_ate_a_retirada():
    ambiente = Ambiente()
    pedido = ambiente.pedir()
    for novo in ("Em preparo", "Pronto", "Retirado"):
        ambiente.atualizar.executar(pedido.pedido_id, novo)
    assert ambiente.consultar.executar(pedido.pedido_id).status == Status.RETIRADO


@pytest.mark.unit
def test_status_fora_de_ordem_e_rejeitado():
    ambiente = Ambiente()
    pedido = ambiente.pedir()
    with pytest.raises(TransicaoInvalida):
        ambiente.atualizar.executar(pedido.pedido_id, "Pronto")


@pytest.mark.unit
def test_status_desconhecido_e_rejeitado():
    ambiente = Ambiente()
    pedido = ambiente.pedir()
    with pytest.raises(ValueError, match="Status inválido"):
        ambiente.atualizar.executar(pedido.pedido_id, "Voando")


@pytest.mark.unit
def test_pedido_inexistente_nao_e_encontrado():
    with pytest.raises(PedidoNaoEncontrado):
        Ambiente().consultar.executar("nao-existe")