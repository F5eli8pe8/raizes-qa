from dataclasses import dataclass
from datetime import datetime
from enum import Enum

FINALIDADES = ("fidelizacao", "promocoes")


class Perfil(str, Enum):
    CLIENTE = "cliente"
    ATENDENTE = "atendente"
    ADMINISTRADOR = "administrador"


@dataclass(frozen=True)
class RegistroConsentimento:
    finalidade: str
    concedido: bool
    em: datetime
    versao_aviso: str
    canal: str


class Cliente:
    def __init__(
        self,
        cliente_id: str,
        nome: str,
        email: str,
        senha_hash: str,
        perfil: Perfil = Perfil.CLIENTE,
    ):
        self.cliente_id = cliente_id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.perfil = perfil
        self.consentimentos: list[RegistroConsentimento] = []
        self.falhas_login = 0
        self.bloqueado_ate: datetime | None = None
        self.anonimizado = False

    def registrar_consentimento(
        self, finalidade: str, concedido: bool, em: datetime, versao_aviso: str, canal: str
    ) -> None:
        if finalidade not in FINALIDADES:
            raise ValueError(f"Finalidade desconhecida: {finalidade}")
        # O histórico é preservado: a revogação é um novo registro, não uma edição
        self.consentimentos.append(
            RegistroConsentimento(finalidade, concedido, em, versao_aviso, canal)
        )

    def consentimento_ativo(self, finalidade: str) -> bool:
        for registro in reversed(self.consentimentos):
            if registro.finalidade == finalidade:
                return registro.concedido
        return False

    def anonimizar(self) -> None:
        self.nome = "Cliente removido"
        self.email = f"removido-{self.cliente_id}@anonimizado.invalid"
        self.senha_hash = ""
        self.consentimentos.clear()
        self.anonimizado = True