"""SISTEMA EXTERNO SIMULADO - Provedor de Cotações (passeio aleatório a cada segundo, RT1)."""
import random
import threading
import time

from ..dominio import agora_iso
from ..http_util import Roteador, criar_servidor

PRECOS_INICIAIS = {"PETR4": 38.50, "VALE3": 62.10, "ITUB4": 33.20, "BOVA11": 128.40, "HGLG11": 160.00, "MXRF11": 10.20}


def criar_provedor(porta):
    precos = dict(PRECOS_INICIAIS)
    lock = threading.Lock()

    def laco():
        while True:
            time.sleep(1)
            with lock:
                for a in precos:
                    precos[a] = max(0.01, round(precos[a] * (1 + random.uniform(-0.003, 0.003)), 2))

    def listar(_):
        with lock:
            return 200, [{"ativo": a, "preco": p, "variacaoDia": round((p / PRECOS_INICIAIS[a] - 1) * 100, 2),
                          "atualizadoEm": agora_iso()} for a, p in precos.items()]

    r = Roteador()
    r.add("GET", "/cotacoes", listar)
    threading.Thread(target=laco, daemon=True, name="provedor-cotacoes").start()
    return criar_servidor(r, porta)
