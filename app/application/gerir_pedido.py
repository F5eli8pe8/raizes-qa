from app.application.portas import PagamentoGateway, RepositorioPedidos
from app.domain.estoque import Estoque
from app.domain.pedido import Pedido, Status


class PedidoNaoEncontrado(Exception):
    pass


def _obter(repositorio: RepositorioPedidos, pedido_id: str) -> Pedido:
    pedido = repositorio.obter(pedido_id)
    if pedido is None:
        raise PedidoNaoEncontrado("Pedido não encontrado.")
    return pedido


class ConsultarPedido:
    def __init__(self, repositorio: RepositorioPedidos):
        self._repositorio = repositorio

    def executar(self, pedido_id: str) -> Pedido:
        return _obter(self._repositorio, pedido_id)


class CancelarPedido:
    def __init__(
        self,
        repositorio: RepositorioPedidos,
        estoques: dict[str, Estoque],
        pagamento: PagamentoGateway,
    ):
        self._repositorio = repositorio
        self._estoques = estoques
        self._pagamento = pagamento

    def executar(self, pedido_id: str) -> Pedido:
        pedido = _obter(self._repositorio, pedido_id)
        estava_pago = pedido.status == Status.RECEBIDO
        # Se o cancelamento for negado, a exceção sobe antes de qualquer efeito
        pedido.cancelar()
        estoque = self._estoques[pedido.unidade_id]
        for item in pedido.itens:
            if estava_pago:
                estoque.repor(item.item_id, item.quantidade)
            else:
                estoque.liberar(item.item_id, item.quantidade)
        if estava_pago:
            self._pagamento.estornar(pedido.pedido_id)
        return pedido


_ACOES = {
    Status.EM_PREPARO.value: Pedido.iniciar_preparo,
    Status.PRONTO.value: Pedido.marcar_pronto,
    Status.RETIRADO.value: Pedido.registrar_retirada,
}


class AtualizarStatusPedido:
    def __init__(self, repositorio: RepositorioPedidos):
        self._repositorio = repositorio

    def executar(self, pedido_id: str, novo_status: str) -> Pedido:
        acao = _ACOES.get(novo_status)
        if acao is None:
            raise ValueError("Status inválido.")
        pedido = _obter(self._repositorio, pedido_id)
        acao(pedido)
        return pedido