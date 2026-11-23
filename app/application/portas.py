from enum import Enum
from typing import Protocol

from app.domain.pedido import Pedido


class ResultadoPagamento(str, Enum):
    APROVADO = "aprovado"
    RECUSADO = "recusado"


class PagamentoIndisponivel(Exception):
    """Atraso acima do limite ou erro do serviço de pagamento."""


class PagamentoGateway(Protocol):
    def cobrar(
        self, pedido_id: str, valor_centavos: int, chave_idempotencia: str
    ) -> ResultadoPagamento: ...


class RepositorioPedidos(Protocol):
    def salvar(self, pedido: Pedido, chave_idempotencia: str) -> None: ...

    def obter(self, pedido_id: str) -> Pedido | None: ...

    def obter_por_chave(self, chave_idempotencia: str) -> Pedido | None: ...

    def quantidade(self) -> int: ...