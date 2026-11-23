import re
import uuid
from datetime import datetime, timedelta
from typing import Callable

from app.domain.cliente import FINALIDADES, Cliente
from app.infrastructure.repositorio_memoria import RepositorioClientesMemoria
from app.infrastructure.seguranca import SessoesMemoria, hash_senha, verificar_senha

VERSAO_AVISO = "2026-11"
MAX_FALHAS = 5
BLOQUEIO = timedelta(minutes=15)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DadosInvalidos(Exception):
    def __init__(self, erros: dict[str, str]):
        super().__init__("Dados inválidos.")
        self.erros = erros


class CredenciaisInvalidas(Exception):
    pass


class AcessoBloqueado(Exception):
    pass


class ClienteNaoEncontrado(Exception):
    pass


class RegistrarCliente:
    def __init__(
        self,
        repositorio: RepositorioClientesMemoria,
        agora: Callable[[], datetime] = datetime.now,
        gerar_id: Callable[[], str] = lambda: uuid.uuid4().hex[:12],
    ):
        self._repositorio = repositorio
        self._agora = agora
        self._gerar_id = gerar_id

    def executar(
        self,
        nome: str,
        email: str,
        senha: str,
        canal: str,
        fidelizacao: bool = False,
        promocoes: bool = False,
    ) -> Cliente:
        email = email.strip().lower()
        erros = {}
        if not nome.strip():
            erros["nome"] = "Informe seu nome."
        if not _EMAIL.match(email):
            erros["email"] = "Informe um e-mail válido."
        elif self._repositorio.obter_por_email(email) is not None:
            erros["email"] = "Este e-mail já está cadastrado."
        if len(senha) < 8:
            erros["senha"] = "A senha deve ter pelo menos 8 caracteres."
        if erros:
            raise DadosInvalidos(erros)

        cliente = Cliente(self._gerar_id(), nome.strip(), email, hash_senha(senha))
        escolhas = {"fidelizacao": fidelizacao, "promocoes": promocoes}
        for finalidade in FINALIDADES:
            cliente.registrar_consentimento(
                finalidade, escolhas[finalidade], self._agora(), VERSAO_AVISO, canal
            )
        self._repositorio.salvar(cliente)
        return cliente


class Autenticar:
    def __init__(
        self,
        repositorio: RepositorioClientesMemoria,
        sessoes: SessoesMemoria,
        agora: Callable[[], datetime] = datetime.now,
    ):
        self._repositorio = repositorio
        self._sessoes = sessoes
        self._agora = agora

    def executar(self, email: str, senha: str) -> str:
        cliente = self._repositorio.obter_por_email(email)
        if cliente is None:
            raise CredenciaisInvalidas("E-mail ou senha inválidos.")

        agora = self._agora()
        if cliente.bloqueado_ate is not None and agora < cliente.bloqueado_ate:
            raise AcessoBloqueado(
                "Acesso temporariamente bloqueado. Tente novamente em 15 minutos."
            )

        if not verificar_senha(senha, cliente.senha_hash):
            cliente.falhas_login += 1
            if cliente.falhas_login >= MAX_FALHAS:
                cliente.falhas_login = 0
                cliente.bloqueado_ate = agora + BLOQUEIO
                raise AcessoBloqueado(
                    "Acesso temporariamente bloqueado. Tente novamente em 15 minutos."
                )
            raise CredenciaisInvalidas("E-mail ou senha inválidos.")

        cliente.falhas_login = 0
        cliente.bloqueado_ate = None
        return self._sessoes.criar(cliente.cliente_id, cliente.perfil)


class AlterarConsentimento:
    def __init__(
        self,
        repositorio: RepositorioClientesMemoria,
        agora: Callable[[], datetime] = datetime.now,
    ):
        self._repositorio = repositorio
        self._agora = agora

    def executar(self, cliente_id: str, finalidade: str, concedido: bool, canal: str) -> Cliente:
        cliente = self._repositorio.obter(cliente_id)
        if cliente is None:
            raise ClienteNaoEncontrado("Cliente não encontrado.")
        cliente.registrar_consentimento(
            finalidade, concedido, self._agora(), VERSAO_AVISO, canal
        )
        return cliente


class ExcluirConta:
    def __init__(self, repositorio: RepositorioClientesMemoria):
        self._repositorio = repositorio

    def executar(self, cliente_id: str) -> None:
        cliente = self._repositorio.obter(cliente_id)
        if cliente is None:
            raise ClienteNaoEncontrado("Cliente não encontrado.")
        cliente.anonimizar()