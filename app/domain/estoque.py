from app.domain.erros import ItemIndisponivel


class Estoque:
    """Estoque de uma unidade.

    A reserva e a baixa são etapas separadas: se o pagamento for recusado,
    a reserva é liberada e o item volta a ficar disponível.
    """

    def __init__(self, quantidades: dict[str, int]):
        self._disponivel = dict(quantidades)
        self._reservado: dict[str, int] = {}

    def disponivel(self, item_id: str) -> int:
        return self._disponivel.get(item_id, 0)

    def reservar(self, item_id: str, quantidade: int) -> None:
        self._validar_quantidade(quantidade)
        if self.disponivel(item_id) < quantidade:
            raise ItemIndisponivel("Item indisponível no momento. Escolha outro item.")
        self._disponivel[item_id] -= quantidade
        self._reservado[item_id] = self._reservado.get(item_id, 0) + quantidade

    def liberar(self, item_id: str, quantidade: int) -> None:
        self._retirar_da_reserva(item_id, quantidade)
        self._disponivel[item_id] = self.disponivel(item_id) + quantidade

    def confirmar(self, item_id: str, quantidade: int) -> None:
        self._retirar_da_reserva(item_id, quantidade)

    def _retirar_da_reserva(self, item_id: str, quantidade: int) -> None:
        self._validar_quantidade(quantidade)
        if self._reservado.get(item_id, 0) < quantidade:
            raise ValueError("Quantidade maior do que a reservada.")
        self._reservado[item_id] -= quantidade

    @staticmethod
    def _validar_quantidade(quantidade: int) -> None:
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")