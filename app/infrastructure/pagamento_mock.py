from app.application.portas import PagamentoIndisponivel, ResultadoPagamento

CENARIOS = ("aprovado", "recusado", "timeout", "erro")


class PagamentoMock:
    """Simula o serviço de pagamento. O cenário define o comportamento.

    Só recebe ID do pedido, valor e chave de idempotência: nenhum dado pessoal.
    """

    def __init__(self, cenario: str = "aprovado"):
        self.cenario = cenario
        self.chamadas: list[tuple[str, int, str]] = []
        self._resultados: dict[str, ResultadoPagamento] = {}

    @property
    def cenario(self) -> str:
        return self._cenario

    @cenario.setter
    def cenario(self, valor: str) -> None:
        if valor not in CENARIOS:
            raise ValueError(f"Cenário desconhecido: {valor}")
        self._cenario = valor

    def cobrar(
        self, pedido_id: str, valor_centavos: int, chave_idempotencia: str
    ) -> ResultadoPagamento:
        self.chamadas.append((pedido_id, valor_centavos, chave_idempotencia))
        if chave_idempotencia in self._resultados:
            return self._resultados[chave_idempotencia]
        if self.cenario in ("timeout", "erro"):
            raise PagamentoIndisponivel(f"Serviço de pagamento indisponível ({self.cenario}).")
        if self.cenario == "aprovado":
            resultado = ResultadoPagamento.APROVADO
        else:
            resultado = ResultadoPagamento.RECUSADO
        self._resultados[chave_idempotencia] = resultado
        return resultado