"""SISTEMA EXTERNO SIMULADO - Bolsa/Corretora.
Recebe ordens, faz o matching contra a cotação atual e avisa o SentinelTrade por
callback quando uma ordem limitada é executada depois. É idempotente pelo id da ordem."""
import threading
import time

from ..dominio import ErroNaoEncontrado, ErroSentinel, ErroValidacao
from ..http_util import Roteador, criar_servidor, requisicao


class ForaDoAr(ErroSentinel):
    status = 503


class BolsaSimulada:
    def __init__(self, url_cotacoes):
        self.url_cotacoes = url_cotacoes
        self.mercado = "ABERTO"
        self.modo_falha = False  # para demonstrar o circuit breaker
        self.precos = {}
        self.ordens = {}
        self.lock = threading.Lock()

    def atualizar_precos(self):
        try:
            _, lista = requisicao("GET", self.url_cotacoes + "/cotacoes", timeout=1.0)
            self.precos = {c["ativo"]: c["preco"] for c in lista}
        except Exception:
            pass

    def tentar_executar(self, o):
        p = self.precos.get(o["ativo"])
        if p is None:
            return False
        executa = o["tipo"] == "MERCADO" or (p <= o["precoLimite"] if o["lado"] == "COMPRA" else p >= o["precoLimite"])
        if executa:
            o["estado"], o["precoExecucao"] = "EXECUTADA", p
        return executa

    def laco(self):
        while True:
            self.atualizar_precos()
            with self.lock:
                executadas = [o for o in self.ordens.values()
                              if o["estado"] == "ABERTA" and self.mercado == "ABERTO" and self.tentar_executar(o)]
            for o in executadas:
                try:
                    requisicao("POST", o["callbackUrl"], {"ordemId": o["id"], "estado": o["estado"], "precoExecucao": o["precoExecucao"]})
                except Exception:
                    pass
            time.sleep(1)

    def checar_falha(self):
        if self.modo_falha:
            raise ForaDoAr("Bolsa fora do ar (falha simulada)")

    def receber(self, corpo):
        self.checar_falha()
        with self.lock:
            if corpo.get("id") in self.ordens:
                return self.ordens[corpo["id"]]
            o = {**corpo, "estado": "ABERTA"}
            if self.mercado != "ABERTO":
                o.update(estado="REJEITADA", motivo="Mercado fechado")
            elif o.get("ativo") not in self.precos:
                o.update(estado="REJEITADA", motivo="Ativo desconhecido na bolsa")
            else:
                self.tentar_executar(o)
            self.ordens[o["id"]] = o
            return o

    def cancelar(self, ordem_id):
        self.checar_falha()
        with self.lock:
            o = self.ordens.get(ordem_id)
            if not o:
                raise ErroNaoEncontrado("Ordem não encontrada na bolsa")
            if o["estado"] == "ABERTA":
                o["estado"] = "CANCELADA"
            return o


def criar_bolsa(porta, url_cotacoes):
    b = BolsaSimulada(url_cotacoes)

    def definir_mercado(q):
        if q.corpo.get("estado") not in ("ABERTO", "FECHADO"):
            raise ErroValidacao("Estado inválido")
        b.mercado = q.corpo["estado"]
        return 200, {"estado": b.mercado}

    def falha(q):
        b.modo_falha = bool(q.corpo.get("ativo"))
        return 200, {"modoFalha": b.modo_falha}

    r = Roteador()
    r.add("GET", "/mercado", lambda q: (b.checar_falha() or 200, {"estado": b.mercado}))
    r.add("PUT", "/mercado", definir_mercado)
    r.add("POST", "/ordens", lambda q: (200, b.receber(q.corpo)))
    r.add("POST", "/ordens/:id/cancelar", lambda q: (200, b.cancelar(q.params["id"])))
    r.add("PUT", "/admin/falha", falha)
    b.atualizar_precos()
    threading.Thread(target=b.laco, daemon=True, name="bolsa-matching").start()
    return criar_servidor(r, porta)
