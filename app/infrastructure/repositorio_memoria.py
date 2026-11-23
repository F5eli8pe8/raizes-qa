from app.domain.pedido import Pedido


class RepositorioPedidosMemoria:
    def __init__(self):
        self._pedidos: dict[str, Pedido] = {}
        self._por_chave: dict[str, str] = {}

    def salvar(self, pedido: Pedido, chave_idempotencia: str) -> None:
        self._pedidos[pedido.pedido_id] = pedido
        self._por_chave[chave_idempotencia] = pedido.pedido_id

    def obter(self, pedido_id: str) -> Pedido | None:
        return self._pedidos.get(pedido_id)

    def obter_por_chave(self, chave_idempotencia: str) -> Pedido | None:
        pedido_id = self._por_chave.get(chave_idempotencia)
        return self._pedidos.get(pedido_id) if pedido_id else None

    def quantidade(self) -> int:
        return len(self._pedidos)