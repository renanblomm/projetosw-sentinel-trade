"""Ponto de entrada do SentinelTrade. Sobe 4 servidores, cada um na sua porta:
   4002 Provedor de cotações (externo simulado)
   4001 Bolsa simulada (externo simulado)
   4000 Core - serviços de domínio (API interna)
   3000 BFF + interface web (única porta usada pelo navegador)
Uso:  python src/main.py"""
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentineltrade.app import montar_aplicacao  # noqa: E402
from sentineltrade.bff import criar_bff  # noqa: E402
from sentineltrade.core_api import criar_core  # noqa: E402
from sentineltrade.externos.bolsa_simulada import criar_bolsa  # noqa: E402
from sentineltrade.externos.provedor_cotacoes import criar_provedor  # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def carregar_env():
    """Lê .env (opcional) sem sobrescrever variáveis já definidas."""
    caminho = os.path.join(RAIZ, ".env")
    if os.path.exists(caminho):
        for linha in open(caminho, encoding="utf-8"):
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.strip().split("=", 1)
                os.environ.setdefault(k, v)


def main():
    logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
    carregar_env()
    p = {k: int(os.environ.get(f"{k}_PORT", d)) for k, d in (("BFF", 3000), ("CORE", 4000), ("BOLSA", 4001), ("COTACOES", 4002))}
    url = lambda porta: f"http://127.0.0.1:{porta}"  # noqa: E731
    db_path = os.path.join(RAIZ, os.environ.get("DB_PATH", "database/sentineltrade.db"))

    servidores = [("Provedor de cotações", criar_provedor(p["COTACOES"]))]
    servidores.append(("Bolsa simulada", criar_bolsa(p["BOLSA"], url(p["COTACOES"]))))
    app = montar_aplicacao(db_path, url(p["BOLSA"]), url(p["COTACOES"]), url(p["CORE"]) + "/bolsa/eventos")
    servidores.append(("Core (API interna)", criar_core(app, p["CORE"])))
    servidores.append(("BFF + interface web", criar_bff(p["BFF"], url(p["CORE"]))))

    for nome, s in servidores:
        threading.Thread(target=s.serve_forever, daemon=True, name=nome).start()
        print(f"[ok] {nome:22} http://127.0.0.1:{s.server_address[1]}")
    app.cotacoes.iniciar()
    print(f"\n>>> Acesse http://localhost:{p['BFF']}  (Ctrl+C para encerrar)\n", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando...")


if __name__ == "__main__":
    main()
