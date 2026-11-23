from dataclasses import dataclass
from datetime import date

from app.domain.erros import CupomInvalido


@dataclass(frozen=True)
class Cupom:
    codigo: str
    percentual: int
    validade: date
    unidade_id: str | None = None  # None: vale em todas as unidades

    def __post_init__(self):
        if not 1 <= self.percentual <= 100:
            raise ValueError("O percentual deve estar entre 1 e 100.")

    def validar(self, unidade_id: str, hoje: date) -> None:
        # "hoje" entra como parâmetro para os testes não dependerem do relógio
        expirado = hoje > self.validade
        outra_unidade = self.unidade_id is not None and self.unidade_id != unidade_id
        if expirado or outra_unidade:
            raise CupomInvalido("Cupom inválido ou expirado.")

    def desconto_sobre(self, subtotal_centavos: int, unidade_id: str, hoje: date) -> int:
        self.validar(unidade_id, hoje)
        return subtotal_centavos * self.percentual // 100