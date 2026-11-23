from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.domain.cupom import Cupom
from app.domain.erros import CancelamentoNegado, TransicaoInvalida


class Canal(str, Enum):
    APP = "APP"
    WEB = "WEB"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"


class Status(str, Enum):
    AGUARDANDO_PAGAMENTO = "Aguardando pagamento"
    PENDENTE_PAGAMENTO = "Pendente de pagamento"
    RECEBIDO = "Recebido"
    EM_PREPARO = "Em preparo"
    PRONTO = "Pronto"
    RETIRADO = "Retirado"
    CANCELADO = "Cancelado"


_TRANSICOES = {
    Status.AGUARDANDO_PAGAMENTO: {Status.RECEBIDO, Status.PENDENTE_PAGAMENTO, Status.CANCELADO},
    Status.PENDENTE_PAGAMENTO: {Status.RECEBIDO, Status.CANCELADO},
    Status.RECEBIDO: {Status.EM_PREPARO, Status.CANCELADO},
    Status.EM_PREPARO: {Status.PRONTO},
    Status.PRONTO: {Status.RETIRADO},
    Status.RETIRADO: set(),
    Status.CANCELADO: set(),
}


@dataclass(frozen=True)
class ItemPedido:
    item_id: str
    quantidade: int
    preco_unitario_centavos: int

    def __post_init__(self):
        if self.quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        if self.preco_unitario_centavos < 0:
            raise ValueError("O preço não pode ser negativo.")

    @property
    def subtotal_centavos(self) -> int:
        return self.quantidade * self.preco_unitario_centavos


class Pedido:
    def __init__(self, pedido_id: str, unidade_id: str, canal: Canal, itens: list[ItemPedido]):
        if not itens:
            raise ValueError("O pedido precisa ter ao menos um item.")
        self.pedido_id = pedido_id
        self.unidade_id = unidade_id
        self.canal = canal
        self.itens = tuple(itens)
        self.status = Status.AGUARDANDO_PAGAMENTO
        self.cupom: Cupom | None = None
        self.desconto_centavos = 0

    @property
    def subtotal_centavos(self) -> int:
        return sum(item.subtotal_centavos for item in self.itens)

    @property
    def total_centavos(self) -> int:
        return self.subtotal_centavos - self.desconto_centavos

    def aplicar_cupom(self, cupom: Cupom, hoje: date) -> None:
        # Se o cupom for inválido, a exceção sobe antes de qualquer alteração
        self.desconto_centavos = cupom.desconto_sobre(
            self.subtotal_centavos, self.unidade_id, hoje
        )
        self.cupom = cupom

    def confirmar_pagamento(self) -> None:
        self._mudar_status(Status.RECEBIDO)

    def marcar_pagamento_pendente(self) -> None:
        self._mudar_status(Status.PENDENTE_PAGAMENTO)

    def iniciar_preparo(self) -> None:
        self._mudar_status(Status.EM_PREPARO)

    def marcar_pronto(self) -> None:
        self._mudar_status(Status.PRONTO)

    def registrar_retirada(self) -> None:
        self._mudar_status(Status.RETIRADO)

    def cancelar(self) -> None:
        if self.status in (Status.EM_PREPARO, Status.PRONTO):
            raise CancelamentoNegado("O pedido já está em preparo e não pode ser cancelado.")
        self._mudar_status(Status.CANCELADO)

    def _mudar_status(self, novo: Status) -> None:
        if novo not in _TRANSICOES[self.status]:
            raise TransicaoInvalida(
                f"Não é possível passar de '{self.status.value}' para '{novo.value}'."
            )
        self.status = novo