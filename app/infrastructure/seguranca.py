import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Callable

from app.domain.cliente import Perfil


def hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    derivado = hashlib.scrypt(senha.encode(), salt=sal, n=2**14, r=8, p=1)
    return f"{sal.hex()}${derivado.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    sal_hex, hash_hex = armazenado.split("$")
    derivado = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(sal_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(derivado.hex(), hash_hex)


class SessoesMemoria:
    """Sessões que expiram por inatividade; cada uso renova o prazo."""

    def __init__(
        self,
        agora: Callable[[], datetime] = datetime.now,
        inatividade: timedelta = timedelta(minutes=30),
    ):
        self._agora = agora
        self._inatividade = inatividade
        self._sessoes: dict[str, tuple[str, Perfil, datetime]] = {}

    def criar(self, cliente_id: str, perfil: Perfil) -> str:
        token = secrets.token_urlsafe(32)
        self._sessoes[token] = (cliente_id, perfil, self._agora())
        return token

    def obter(self, token: str) -> tuple[str, Perfil] | None:
        sessao = self._sessoes.get(token)
        if sessao is None:
            return None
        cliente_id, perfil, ultimo_uso = sessao
        if self._agora() - ultimo_uso > self._inatividade:
            del self._sessoes[token]
            return None
        self._sessoes[token] = (cliente_id, perfil, self._agora())
        return cliente_id, perfil