import threading
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Callable

from app.application.portas import (
    PagamentoGateway,
    PagamentoIndisponivel,
    RepositorioPedidos,
    ResultadoPagamento,
)
from app.domain.cupom import Cupom
from app.domain.erros import CupomInvalido, ItemIndisponivel, PagamentoRecusado
from app.domain.estoque import Estoque
from app.domain.pedido import Canal, ItemPedido, Pedido


@dataclass(frozen=True)
class ItemSolicitado:
    item_id: str
    quantidade: int


@dataclass(frozen=True)
class ComandoPedido:
    unidade_id: str
    canal: Canal
    itens: list[ItemSolicitado]
    chave_idempotencia: str
    codigo_cupom: str | None = None


class RealizarPedido:
    def __init__(
        self,
        cardapios: dict[str, dict[str, int]],
        estoques: dict[str, Estoque],
        cupons: dict[str, Cupom],
        pagamento: PagamentoGateway,
        repositorio: RepositorioPedidos,
        hoje: Callable[[], date] = date.today,
        gerar_id: Callable[[], str] = lambda: uuid.uuid4().hex[:12],
    ):
        self._cardapios = cardapios
        self._estoques = estoques
        self._cupons = cupons
        self._pagamento = pagamento
        self._repositorio = repositorio
        self._hoje = hoje
        self._gerar_id = gerar_id
        # O Estoque não é seguro entre threads; a trava garante a regra do CT-08
        self._trava = threading.Lock()

    def executar(self, comando: ComandoPedido) -> Pedido:
        existente = self._repositorio.obter_por_chave(comando.chave_idempotencia)
        if existente is not None:
            return existente

        pedido = self._montar_pedido(comando)
        self._reservar_estoque(pedido)

        try:
            resultado = self._pagamento.cobrar(
                pedido.pedido_id, pedido.total_centavos, comando.chave_idempotencia
            )
        except PagamentoIndisponivel:
            pedido.marcar_pagamento_pendente()
            self._repositorio.salvar(pedido, comando.chave_idempotencia)
            return pedido

        if resultado is ResultadoPagamento.RECUSADO:
            self._liberar_estoque(pedido)
            raise PagamentoRecusado(
                "Pagamento não aprovado. Verifique os dados ou tente outra forma de pagamento."
            )

        pedido.confirmar_pagamento()
        self._confirmar_estoque(pedido)
        self._repositorio.salvar(pedido, comando.chave_idempotencia)
        return pedido

    def _montar_pedido(self, comando: ComandoPedido) -> Pedido:
        cardapio = self._cardapios.get(comando.unidade_id)
        if cardapio is None:
            raise ValueError("Unidade não encontrada.")
        itens = []
        for solicitado in comando.itens:
            preco = cardapio.get(solicitado.item_id)
            if preco is None:
                raise ItemIndisponivel("Item indisponível no momento. Escolha outro item.")
            itens.append(ItemPedido(solicitado.item_id, solicitado.quantidade, preco))
        pedido = Pedido(self._gerar_id(), comando.unidade_id, comando.canal, itens)
        if comando.codigo_cupom:
            cupom = self._cupons.get(comando.codigo_cupom)
            if cupom is None:
                raise CupomInvalido("Cupom inválido ou expirado.")
            pedido.aplicar_cupom(cupom, self._hoje())
        return pedido

    def _reservar_estoque(self, pedido: Pedido) -> None:
        estoque = self._estoques[pedido.unidade_id]
        with self._trava:
            reservados = []
            try:
                for item in pedido.itens:
                    estoque.reservar(item.item_id, item.quantidade)
                    reservados.append(item)
            except ItemIndisponivel:
                for item in reservados:
                    estoque.liberar(item.item_id, item.quantidade)
                raise

    def _liberar_estoque(self, pedido: Pedido) -> None:
        estoque = self._estoques[pedido.unidade_id]
        with self._trava:
            for item in pedido.itens:
                estoque.liberar(item.item_id, item.quantidade)

    def _confirmar_estoque(self, pedido: Pedido) -> None:
        estoque = self._estoques[pedido.unidade_id]
        with self._trava:
            for item in pedido.itens:
                estoque.confirmar(item.item_id, item.quantidade)