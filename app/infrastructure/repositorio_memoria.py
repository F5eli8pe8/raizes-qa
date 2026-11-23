from app.domain.cliente import Cliente
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


class RepositorioClientesMemoria:
    def __init__(self):
        self._clientes: dict[str, Cliente] = {}

    def salvar(self, cliente: Cliente) -> None:
        self._clientes[cliente.cliente_id] = cliente

    def obter(self, cliente_id: str) -> Cliente | None:
        return self._clientes.get(cliente_id)

    def obter_por_email(self, email: str) -> Cliente | None:
        alvo = email.strip().lower()
        for cliente in self._clientes.values():
            if cliente.email == alvo and not cliente.anonimizado:
                return cliente
        return None