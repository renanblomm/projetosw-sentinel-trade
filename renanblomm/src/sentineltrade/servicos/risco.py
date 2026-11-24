"""RF6 - Validação prévia de risco (pre-trade).
Padrão Strategy/Chain of Responsibility: cada regra é uma subclasse de RegraRisco;
o ValidadorRisco executa todas em ordem e para na primeira reprovação."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..dominio import Lado, TipoOrdem, r2
from .contas import TAXA

MARGEM_ORDEM_MERCADO = 0.02  # compra a mercado reserva 2% acima da última cotação


@dataclass
class ContextoRisco:
    ordem: object
    conta: object
    cotacao: Optional[dict]
    mercado_aberto: bool

    @property
    def valor_estimado(self):
        o = self.ordem
        if o.tipo == TipoOrdem.LIMITADA:
            preco = o.preco_limite
        else:
            preco = self.cotacao["preco"] * (1 + MARGEM_ORDEM_MERCADO if o.lado == Lado.COMPRA else 1)
        valor = preco * o.quantidade
        return r2(valor * (1 + TAXA) if o.lado == Lado.COMPRA else valor)


@dataclass
class ResultadoRisco:
    aprovada: bool
    motivo: Optional[str] = None
    valor_estimado: Optional[float] = None


class RegraRisco(ABC):
    @abstractmethod
    def avaliar(self, ctx: ContextoRisco) -> Optional[str]:
        """Retorna o motivo da rejeição, ou None se a regra passou."""


class RegraMercadoAberto(RegraRisco):
    def avaliar(self, ctx):
        return None if ctx.mercado_aberto else "Mercado fechado (RN3)"


class RegraCotacaoDisponivel(RegraRisco):
    def avaliar(self, ctx):
        return None if ctx.cotacao else "Ativo sem cotação disponível"


class RegraSaldo(RegraRisco):
    def avaliar(self, ctx):
        if ctx.ordem.lado != Lado.COMPRA:
            return None
        necessario, disponivel = ctx.valor_estimado, ctx.conta.saldo_disponivel
        if disponivel < necessario:
            return f"Saldo insuficiente (RN1): necessário R$ {necessario:.2f}, disponível R$ {disponivel:.2f}"


class RegraCustodia(RegraRisco):
    def avaliar(self, ctx):
        if ctx.ordem.lado != Lado.VENDA:
            return None
        livre = ctx.conta.custodia_livre(ctx.ordem.ativo)
        if livre < ctx.ordem.quantidade:
            return f"Custódia insuficiente (RN2): livre {livre}, solicitado {ctx.ordem.quantidade}"


class RegraLimiteDiario(RegraRisco):
    def avaliar(self, ctx):
        c = ctx.conta
        if c.operado_hoje + ctx.valor_estimado > c.limite_diario:
            return f"Limite diário excedido (RN5): restante R$ {c.limite_diario - c.operado_hoje:.2f}"


class ValidadorRisco:
    def __init__(self, regras=None):
        self.regras = regras or [RegraMercadoAberto(), RegraCotacaoDisponivel(), RegraSaldo(), RegraCustodia(), RegraLimiteDiario()]

    def validar(self, ordem, conta, cotacao, mercado_aberto) -> ResultadoRisco:
        ctx = ContextoRisco(ordem, conta, cotacao, mercado_aberto)
        for regra in self.regras:
            motivo = regra.avaliar(ctx)
            if motivo:
                return ResultadoRisco(False, motivo)
        return ResultadoRisco(True, valor_estimado=ctx.valor_estimado)
