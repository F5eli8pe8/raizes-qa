import threading

from app.domain.erros import ItemIndisponivel


class Estoque:
    """Estoque de uma unidade.

    A reserva e a baixa são etapas separadas: se o pagamento for recusado,
    a reserva é liberada e o item volta a ficar disponível. Cada operação é
    atômica (trava interna), porque pedidos e cancelamentos chegam em paralelo.
    """

    def __init__(self, quantidades: dict[str, int]):
        self._disponivel = dict(quantidades)
        self._reservado: dict[str, int] = {}
        self._trava = threading.RLock()

    def disponivel(self, item_id: str) -> int:
        with self._trava:
            return self._disponivel.get(item_id, 0)

    def reservar(self, item_id: str, quantidade: int) -> None:
        self._validar_quantidade(quantidade)
        with self._trava:
            if self.disponivel(item_id) < quantidade:
                raise ItemIndisponivel("Item indisponível no momento. Escolha outro item.")
            self._disponivel[item_id] -= quantidade
            self._reservado[item_id] = self._reservado.get(item_id, 0) + quantidade

    def liberar(self, item_id: str, quantidade: int) -> None:
        with self._trava:
            self._retirar_da_reserva(item_id, quantidade)
            self._disponivel[item_id] = self.disponivel(item_id) + quantidade

    def confirmar(self, item_id: str, quantidade: int) -> None:
        with self._trava:
            self._retirar_da_reserva(item_id, quantidade)

    def repor(self, item_id: str, quantidade: int) -> None:
        """Devolve ao estoque um item cuja baixa já foi confirmada (cancelamento)."""
        self._validar_quantidade(quantidade)
        with self._trava:
            self._disponivel[item_id] = self.disponivel(item_id) + quantidade

    def _retirar_da_reserva(self, item_id: str, quantidade: int) -> None:
        self._validar_quantidade(quantidade)
        if self._reservado.get(item_id, 0) < quantidade:
            raise ValueError("Quantidade maior do que a reservada.")
        self._reservado[item_id] -= quantidade

    @staticmethod
    def _validar_quantidade(quantidade: int) -> None:
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")