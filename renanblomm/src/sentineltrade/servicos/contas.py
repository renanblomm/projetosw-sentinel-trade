"""RF2 - Conta do investidor: saldo, custódia e limite. RN1/RN2 - bloqueios."""
from ..dominio import ErroValidacao, Lado, r2

TAXA = 0.001  # 0,1% sobre o valor da operação


class Conta:
    """Atributos privados; só mudam pelos métodos de negócio."""

    def __init__(self, usuario, saldo, saldo_bloqueado, limite_diario, operado_hoje, custodia):
        self.__usuario = usuario
        self.__saldo = r2(saldo)
        self.__bloqueado = r2(saldo_bloqueado)
        self.__limite = r2(limite_diario)
        self.__operado = r2(operado_hoje)
        self.__custodia = {a: list(v) for a, v in custodia.items()}  # ativo -> [quantidade, bloqueada]

    usuario = property(lambda s: s.__usuario)
    saldo = property(lambda s: s.__saldo)
    saldo_bloqueado = property(lambda s: s.__bloqueado)
    saldo_disponivel = property(lambda s: r2(s.__saldo - s.__bloqueado))
    limite_diario = property(lambda s: s.__limite)
    operado_hoje = property(lambda s: s.__operado)
    custodia = property(lambda s: {a: list(v) for a, v in s.__custodia.items()})

    def custodia_livre(self, ativo):
        qtd, bloq = self.__custodia.get(ativo, [0, 0])
        return qtd - bloq

    def definir_limite(self, valor):
        try:
            valor = r2(valor)
        except (TypeError, ValueError):
            raise ErroValidacao("Limite diário deve ser numérico")
        if not 0 < valor <= 100_000_000:
            raise ErroValidacao("Limite diário fora da faixa permitida")
        self.__limite = valor

    def reservar(self, ordem):
        """Após aprovação no risco: bloqueia saldo (compra) ou ativos (venda)."""
        if ordem.lado == Lado.COMPRA:
            self.__bloqueado = r2(self.__bloqueado + ordem.valor_estimado)
        else:
            self.__custodia[ordem.ativo][1] += ordem.quantidade
        self.__operado = r2(self.__operado + ordem.valor_estimado)

    def liberar(self, ordem):
        """Cancelamento/rejeição depois da reserva: devolve exatamente o que foi bloqueado."""
        if ordem.lado == Lado.COMPRA:
            self.__bloqueado = r2(self.__bloqueado - ordem.valor_estimado)
        else:
            self.__custodia[ordem.ativo][1] -= ordem.quantidade
        self.__operado = r2(self.__operado - ordem.valor_estimado)

    def liquidar(self, ordem, preco):
        """Execução na bolsa: movimenta saldo e custódia com o preço real."""
        valor = preco * ordem.quantidade
        taxa = r2(valor * TAXA)
        if ordem.lado == Lado.COMPRA:
            self.__bloqueado = r2(self.__bloqueado - ordem.valor_estimado)
            self.__saldo = r2(self.__saldo - valor - taxa)
            self.__custodia.setdefault(ordem.ativo, [0, 0])[0] += ordem.quantidade
            efetivo = valor + taxa
        else:
            self.__custodia[ordem.ativo][1] -= ordem.quantidade
            self.__custodia[ordem.ativo][0] -= ordem.quantidade
            self.__saldo = r2(self.__saldo + valor - taxa)
            efetivo = valor
        self.__operado = r2(self.__operado - ordem.valor_estimado + efetivo)
        return r2(valor), taxa

    def resumo(self):
        return {
            "usuario": self.usuario, "saldoTotal": self.saldo, "saldoBloqueado": self.saldo_bloqueado,
            "saldoDisponivel": self.saldo_disponivel, "limiteDiario": self.limite_diario,
            "operadoHoje": self.operado_hoje, "limiteRestante": r2(self.limite_diario - self.operado_hoje),
            "custodia": [{"ativo": a, "quantidade": q, "bloqueada": b, "livre": q - b}
                         for a, (q, b) in sorted(self.__custodia.items()) if q > 0],
        }
