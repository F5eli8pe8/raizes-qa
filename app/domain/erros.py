class DominioErro(Exception):
    """Base das violações de regra de negócio."""


class ItemIndisponivel(DominioErro):
    pass


class CupomInvalido(DominioErro):
    pass


class CancelamentoNegado(DominioErro):
    pass


class TransicaoInvalida(DominioErro):
    pass