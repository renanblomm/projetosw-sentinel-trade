"""BFF - Backend for Frontend.
Única porta de entrada do navegador. Responsabilidades:
 1. Servir a interface web (somente arquivos de uma allowlist).
 2. Barrar qualquer rota sem sessão validada com MFA (CA1).
 3. Controlar acesso por perfil (privilégio mínimo).
 4. Agregar várias chamadas internas numa resposta pronta para a tela (/api/painel).
 5. Esconder do navegador os serviços internos e os sistemas externos."""
import os
from concurrent.futures import ThreadPoolExecutor

from .dominio import ErroAutenticacao, ErroAutorizacao, ErroSentinel
from .http_util import Roteador, criar_servidor, requisicao

PUBLICO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
ESTATICOS = {
    "/": (os.path.join(PUBLICO, "index.html"), "text/html; charset=utf-8"),
    "/app.js": (os.path.join(PUBLICO, "app.js"), "text/javascript; charset=utf-8"),
    "/estilo.css": (os.path.join(PUBLICO, "estilo.css"), "text/css; charset=utf-8"),
}
INVESTIDOR = {"INVESTIDOR"}
OPERADOR = {"ANALISTA_RISCO"}
AUDITORIA = {"AUDITOR", "ANALISTA_RISCO"}


class ErroRepassado(ErroSentinel):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


def criar_bff(porta, url_core):
    pool = ThreadPoolExecutor(max_workers=8)

    def core(metodo, caminho, corpo=None, usuario=None, token=None):
        headers = {}
        if usuario:
            headers["X-Usuario"] = usuario
        if token:
            headers["X-Token"] = token
        status, resp = requisicao(metodo, url_core + caminho, corpo, headers)
        if status >= 400:
            raise ErroRepassado(status, resp.get("erro", "Erro no serviço interno"))
        return resp

    def sessao(req, perfis=None):
        token = (req.headers.get("Authorization") or "").replace("Bearer ", "", 1)
        if not token:
            raise ErroAutenticacao("Faça login com MFA para continuar")
        try:
            s = core("GET", "/auth/sessao", token=token)
        except ErroRepassado:
            raise ErroAutenticacao("Sessão inválida ou expirada")
        if perfis and s["perfil"] not in perfis:
            raise ErroAutorizacao("Seu perfil não tem acesso a esta função")
        return {**s, "token": token}

    def paralelo(**chamadas):
        futuros = {k: pool.submit(*v) for k, v in chamadas.items()}
        return {k: f.result() for k, f in futuros.items()}

    def painel(req):
        s = sessao(req)
        base = {"usuario": {k: s[k] for k in ("usuario", "nome", "perfil")}}
        u = s["usuario"]
        if s["perfil"] == "INVESTIDOR":
            d = paralelo(conta=(core, "GET", f"/contas/{u}"), cotacoes=(core, "GET", "/cotacoes"),
                         ordens=(core, "GET", f"/ordens?usuario={u}"), notificacoes=(core, "GET", f"/notificacoes/{u}"),
                         mercado=(core, "GET", "/mercado"))
            for o in d["ordens"]:
                o["podeCancelar"] = o["estado"] == "ABERTA"
            return 200, {**base, **d}
        if s["perfil"] == "ANALISTA_RISCO":
            d = paralelo(investidores=(core, "GET", "/investidores"), ordens=(core, "GET", "/ordens"),
                         mercado=(core, "GET", "/mercado"), cotacoes=(core, "GET", "/cotacoes"))
            return 200, {**base, **d}
        return 200, base

    def logout(req):
        s = sessao(req)
        core("POST", "/auth/logout", {}, token=s["token"])
        return 200, {"ok": True}

    r = Roteador()
    r.add("POST", "/api/login", lambda q: (200, core("POST", "/auth/login", q.corpo)))
    r.add("POST", "/api/mfa", lambda q: (200, core("POST", "/auth/mfa", q.corpo)))
    r.add("POST", "/api/logout", logout)
    r.add("GET", "/api/painel", painel)
    r.add("POST", "/api/ordens", lambda q: (200, core("POST", "/ordens", q.corpo, sessao(q, INVESTIDOR)["usuario"])))
    r.add("POST", "/api/ordens/:id/cancelar", lambda q: (200, core("POST", f"/ordens/{q.params['id']}/cancelar", {}, sessao(q, INVESTIDOR)["usuario"])))
    r.add("PUT", "/api/operador/limite", lambda q: (200, core("PUT", f"/contas/{str(q.corpo.get('usuario', ''))[:20]}/limite",
                                                             {"limiteDiario": q.corpo.get("limiteDiario")}, sessao(q, OPERADOR)["usuario"])))
    r.add("PUT", "/api/operador/mercado", lambda q: (200, core("PUT", "/mercado", {"estado": q.corpo.get("estado")}, sessao(q, OPERADOR)["usuario"])))
    r.add("GET", "/api/auditoria", lambda q: (sessao(q, AUDITORIA) and 200, core("GET", "/auditoria")))
    return criar_servidor(r, porta, host="127.0.0.1", estaticos=ESTATICOS)
