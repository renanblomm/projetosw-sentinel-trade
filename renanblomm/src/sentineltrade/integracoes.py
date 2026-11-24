"""Camada de integrações externas (RNF2): timeout, retry controlado e circuit breaker.
Dados vindos de sistemas externos são tratados como NÃO confiáveis e revalidados."""
import logging
import threading
import time

from .dominio import RE_ATIVO
from .http_util import requisicao

log = logging.getLogger("sentineltrade.integracoes")


class CircuitBreaker:
    """FECHADO -> (falhas seguidas) -> ABERTO -> (tempo) -> MEIO_ABERTO -> FECHADO."""

    def __init__(self, nome, limite_falhas=3, tempo_reabertura_s=5.0):
        self.nome = nome
        self.estado = "FECHADO"
        self._falhas = 0
        self._limite = limite_falhas
        self._tempo = tempo_reabertura_s
        self._aberto_em = 0.0
        self._lock = threading.Lock()

    def executar(self, funcao):
        with self._lock:
            if self.estado == "ABERTO":
                if time.time() - self._aberto_em >= self._tempo:
                    self.estado = "MEIO_ABERTO"
                else:
                    raise ConnectionError(f'circuit breaker "{self.nome}" ABERTO')
        try:
            resultado = funcao()
        except Exception:
            with self._lock:
                self._falhas += 1
                if self.estado == "MEIO_ABERTO" or self._falhas >= self._limite:
                    self.estado = "ABERTO"
                    self._aberto_em = time.time()
                    log.warning('Circuit breaker "%s" ABERTO', self.nome)
            raise
        with self._lock:
            self._falhas = 0
            self.estado = "FECHADO"
        return resultado


def retry(funcao, tentativas=3, espera_inicial_s=0.1):
    """Retry com backoff exponencial. Seguro porque a bolsa é idempotente pelo id da ordem."""
    for i in range(tentativas):
        try:
            return funcao()
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(espera_inicial_s * 2 ** i)


ESTADOS_BOLSA = {"ABERTA", "EXECUTADA", "REJEITADA", "CANCELADA"}


def validar_resposta_bolsa(resp):
    estado = resp.get("estado")
    if estado not in ESTADOS_BOLSA:
        raise ValueError("Resposta da bolsa com estado inválido")
    limpo = {"estado": estado, "motivo": str(resp.get("motivo") or "")[:200] or None}
    if estado == "EXECUTADA":
        preco = resp.get("precoExecucao")
        if isinstance(preco, bool) or not isinstance(preco, (int, float)) or not 0 < preco < 1_000_000:
            raise ValueError("Preço de execução inválido")
        limpo["precoExecucao"] = round(float(preco), 2)
    return limpo


class GatewayBolsa:
    """ExchangeGatewayClient - RF7."""

    def __init__(self, url_bolsa, url_callback, timeout_s=1.5):
        self.url = url_bolsa
        self.url_callback = url_callback
        self.timeout = timeout_s
        self.breaker = CircuitBreaker("bolsa-simulada")

    def _chamar(self, metodo, caminho, corpo=None):
        def tentativa():
            status, resp = requisicao(metodo, self.url + caminho, corpo, timeout=self.timeout)
            if status >= 500:
                raise ConnectionError(f"bolsa respondeu {status}")
            return resp
        return self.breaker.executar(lambda: retry(tentativa))

    def mercado_aberto(self):
        return self._chamar("GET", "/mercado").get("estado") == "ABERTO"

    def definir_mercado(self, estado):
        return self._chamar("PUT", "/mercado", {"estado": estado})

    def enviar_ordem(self, o):
        resp = self._chamar("POST", "/ordens", {"id": o.id, "ativo": o.ativo, "lado": o.lado.value, "tipo": o.tipo.value,
                                                 "quantidade": o.quantidade, "precoLimite": o.preco_limite, "callbackUrl": self.url_callback})
        return validar_resposta_bolsa(resp)

    def cancelar_ordem(self, o):
        return validar_resposta_bolsa(self._chamar("POST", f"/ordens/{o.id}/cancelar"))


class IngestaoCotacoes:
    """MarketDataIngestionWorker - RF3. Roda em thread própria (RT2): se o provedor cair,
    o motor de ordens segue com a última cotação conhecida."""

    def __init__(self, url_provedor, intervalo_s=1.0):
        self.url = url_provedor
        self.intervalo = intervalo_s
        self.breaker = CircuitBreaker("provedor-cotacoes")
        self._cache = {}
        self._lock = threading.Lock()
        self.atualizado_em = None

    def iniciar(self):
        threading.Thread(target=self._laco, daemon=True, name="ingestao-cotacoes").start()

    def _laco(self):
        while True:
            try:
                self.atualizar()
            except Exception:
                pass
            time.sleep(self.intervalo)

    def atualizar(self):
        def buscar():
            status, resp = requisicao("GET", self.url + "/cotacoes", timeout=1.0)
            if status != 200 or not isinstance(resp, list):
                raise ConnectionError("provedor indisponível")
            return resp
        for c in self.breaker.executar(buscar):
            ativo, preco = c.get("ativo"), c.get("preco")
            if isinstance(ativo, str) and RE_ATIVO.match(ativo) and isinstance(preco, (int, float)) and 0 < preco < 1_000_000:
                with self._lock:
                    self._cache[ativo] = {"ativo": ativo, "preco": round(float(preco), 2),
                                          "variacaoDia": float(c.get("variacaoDia") or 0), "atualizadoEm": str(c.get("atualizadoEm"))[:30]}
        self.atualizado_em = time.time()

    def obter(self, ativo):
        with self._lock:
            return self._cache.get(ativo)

    def listar(self):
        with self._lock:
            return list(self._cache.values())
