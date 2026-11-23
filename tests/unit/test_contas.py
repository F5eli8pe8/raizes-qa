from datetime import datetime, timedelta

import pytest

from app.application.contas import (
    AcessoBloqueado,
    AlterarConsentimento,
    Autenticar,
    CredenciaisInvalidas,
    DadosInvalidos,
    ExcluirConta,
    RegistrarCliente,
)
from app.infrastructure.repositorio_memoria import RepositorioClientesMemoria
from app.infrastructure.seguranca import SessoesMemoria

INICIO = datetime(2026, 11, 20, 12, 0, 0)


class Relogio:
    def __init__(self):
        self.agora = INICIO

    def __call__(self):
        return self.agora

    def avancar(self, **tempo):
        self.agora += timedelta(**tempo)


class Ambiente:
    def __init__(self):
        self.relogio = Relogio()
        self.repositorio = RepositorioClientesMemoria()
        self.sessoes = SessoesMemoria(self.relogio)
        self.registrar = RegistrarCliente(self.repositorio, self.relogio)
        self.autenticar = Autenticar(self.repositorio, self.sessoes, self.relogio)
        self.consentimento = AlterarConsentimento(self.repositorio, self.relogio)
        self.excluir = ExcluirConta(self.repositorio)

    def cadastrar(self, email="ana@exemplo.com", senha="senha-segura-1", **opcoes):
        return self.registrar.executar("Ana Souza", email, senha, canal="APP", **opcoes)


@pytest.mark.unit
def test_ct12_cadastro_sem_consentimentos_opcionais_registra_a_recusa():
    ambiente = Ambiente()
    cliente = ambiente.cadastrar()
    assert not cliente.consentimento_ativo("fidelizacao")
    assert not cliente.consentimento_ativo("promocoes")
    assert len(cliente.consentimentos) == 2
    registro = cliente.consentimentos[0]
    assert (registro.em, registro.versao_aviso, registro.canal) == (INICIO, "2026-11", "APP")


@pytest.mark.unit
def test_ct12_consentimento_concedido_fica_ativo():
    cliente = Ambiente().cadastrar(fidelizacao=True)
    assert cliente.consentimento_ativo("fidelizacao")
    assert not cliente.consentimento_ativo("promocoes")


@pytest.mark.unit
def test_senha_nunca_e_guardada_em_texto_puro():
    cliente = Ambiente().cadastrar(senha="senha-segura-1")
    assert "senha-segura-1" not in cliente.senha_hash
    assert "$" in cliente.senha_hash


@pytest.mark.unit
def test_ct14_campos_invalidos_geram_uma_mensagem_por_campo():
    ambiente = Ambiente()
    with pytest.raises(DadosInvalidos) as erro:
        ambiente.registrar.executar("", "joao@", "123", canal="APP")
    assert erro.value.erros == {
        "nome": "Informe seu nome.",
        "email": "Informe um e-mail válido.",
        "senha": "A senha deve ter pelo menos 8 caracteres.",
    }
    assert ambiente.repositorio.obter_por_email("joao@") is None


@pytest.mark.unit
def test_email_duplicado_e_rejeitado_sem_diferenciar_maiusculas():
    ambiente = Ambiente()
    ambiente.cadastrar(email="ana@exemplo.com")
    with pytest.raises(DadosInvalidos) as erro:
        ambiente.cadastrar(email="ANA@exemplo.com")
    assert erro.value.erros == {"email": "Este e-mail já está cadastrado."}


@pytest.mark.unit
def test_login_correto_cria_sessao_valida():
    ambiente = Ambiente()
    cliente = ambiente.cadastrar()
    token = ambiente.autenticar.executar("ana@exemplo.com", "senha-segura-1")
    assert ambiente.sessoes.obter(token) == (cliente.cliente_id, cliente.perfil)


@pytest.mark.unit
def test_ct09_senha_incorreta_nao_revela_qual_dado_esta_errado():
    ambiente = Ambiente()
    ambiente.cadastrar()
    with pytest.raises(CredenciaisInvalidas, match="E-mail ou senha inválidos."):
        ambiente.autenticar.executar("ana@exemplo.com", "errada-errada")
    with pytest.raises(CredenciaisInvalidas, match="E-mail ou senha inválidos."):
        ambiente.autenticar.executar("naoexiste@exemplo.com", "senha-segura-1")


@pytest.mark.unit
def test_ct09_quinta_falha_bloqueia_e_libera_apos_15_minutos():
    ambiente = Ambiente()
    ambiente.cadastrar()
    for _ in range(4):
        with pytest.raises(CredenciaisInvalidas):
            ambiente.autenticar.executar("ana@exemplo.com", "errada-errada")
    with pytest.raises(AcessoBloqueado, match="temporariamente bloqueado"):
        ambiente.autenticar.executar("ana@exemplo.com", "errada-errada")
    with pytest.raises(AcessoBloqueado):
        ambiente.autenticar.executar("ana@exemplo.com", "senha-segura-1")

    ambiente.relogio.avancar(minutes=15, seconds=1)
    assert ambiente.autenticar.executar("ana@exemplo.com", "senha-segura-1")


@pytest.mark.unit
def test_sessao_expira_apos_30_minutos_de_inatividade():
    ambiente = Ambiente()
    ambiente.cadastrar()
    token = ambiente.autenticar.executar("ana@exemplo.com", "senha-segura-1")
    ambiente.relogio.avancar(minutes=29)
    assert ambiente.sessoes.obter(token) is not None
    ambiente.relogio.avancar(minutes=31)
    assert ambiente.sessoes.obter(token) is None


@pytest.mark.unit
def test_ct13_revogar_consentimento_preserva_o_historico():
    ambiente = Ambiente()
    cliente = ambiente.cadastrar(promocoes=True)
    ambiente.consentimento.executar(cliente.cliente_id, "promocoes", False, canal="APP")
    assert not cliente.consentimento_ativo("promocoes")
    assert len(cliente.consentimentos) == 3


@pytest.mark.unit
def test_ct13_exclusao_remove_os_dados_pessoais_e_impede_o_login():
    ambiente = Ambiente()
    cliente = ambiente.cadastrar()
    ambiente.excluir.executar(cliente.cliente_id)
    assert cliente.nome == "Cliente removido"
    assert "ana@exemplo.com" not in cliente.email
    assert cliente.senha_hash == ""
    with pytest.raises(CredenciaisInvalidas):
        ambiente.autenticar.executar("ana@exemplo.com", "senha-segura-1")