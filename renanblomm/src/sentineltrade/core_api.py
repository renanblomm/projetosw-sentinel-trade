"""API interna do núcleo (serviços de domínio). Escuta só em 127.0.0.1:
o navegador nunca fala com ela, apenas o BFF."""
from .dominio import ErroAutenticacao, ErroNaoEncontrado, RE_USUARIO
from .http_util import Roteador, criar_servidor


def criar_core(app, porta):
    """app: objeto com os serviços já montados (ver main.py)."""
    r = Roteador()

    def usuario_de(req):
        u = req.headers.get("X-Usuario", "")
        if not RE_USUARIO.match(u):
            raise ErroAutenticacao("Usuário não informado")
        return u

    def sessao(req):
        s = app.auth.validar_sessao(req.headers.get("X-Token"))
        if not s:
            raise ErroAutenticacao("Sessão inválida")
        return 200, s

    def logout(req):
        app.auth.logout(req.headers.get("X-Token"))
        return 200, {"ok": True}

    def conta(req):
        return 200, app.contas.obter(req.params["usuario"]).resumo()

    def definir_limite(req):
        alvo = req.params["usuario"]
        if alvo not in app.usuarios.investidores():
            raise ErroNaoEncontrado("Investidor não encontrado")
        with app.db.transacao():
            c = app.contas.obter(alvo)
            c.definir_limite(req.corpo.get("limiteDiario"))
            app.contas.salvar(c)
            app.auditoria.registrar("LIMITE_ALTERADO", usuario_de(req), {"investidor": alvo, "limiteDiario": c.limite_diario})
        return 200, c.resumo()

    def enviar_ordem(req):
        res = app.ordens.enviar(usuario_de(req), req.corpo)
        return (200 if res["duplicada"] else 201), {"duplicada": res["duplicada"], "ordem": res["ordem"].para_dict()}

    def cancelar(req):
        return 200, app.ordens.cancelar(usuario_de(req), req.params["id"]).para_dict()

    def evento_bolsa(req):
        from .integracoes import validar_resposta_bolsa
        return 200, app.ordens.evento_bolsa(str(req.corpo.get("ordemId")), validar_resposta_bolsa(req.corpo)).para_dict()

    def mercado(req):
        try:
            estado = "ABERTO" if app.gateway.mercado_aberto() else "FECHADO"
        except Exception:
            estado = "INDISPONIVEL"
        return 200, {"estado": estado, "circuitBreakerBolsa": app.gateway.breaker.estado}

    def definir_mercado(req):
        estado = req.corpo.get("estado")
        if estado not in ("ABERTO", "FECHADO"):
            from .dominio import ErroValidacao
            raise ErroValidacao("Estado deve ser ABERTO ou FECHADO")
        res = app.gateway.definir_mercado(estado)
        app.auditoria.registrar("MERCADO_ALTERADO", usuario_de(req), {"estado": estado})
        return 200, res

    def auditoria(req):
        regs = app.auditoria.listar()
        return 200, {"integridade": app.auditoria.verificar_cadeia(regs), "registros": regs[::-1][:80]}

    r.add("POST", "/auth/login", lambda q: (200, app.auth.login(q.corpo.get("usuario"), q.corpo.get("senha"))))
    r.add("POST", "/auth/mfa", lambda q: (200, app.auth.verificar_mfa(q.corpo.get("desafioId"), q.corpo.get("codigo"))))
    r.add("GET", "/auth/sessao", sessao)
    r.add("POST", "/auth/logout", logout)
    r.add("GET", "/contas/:usuario", conta)
    r.add("PUT", "/contas/:usuario/limite", definir_limite)
    r.add("GET", "/investidores", lambda q: (200, [app.contas.obter(u).resumo() for u in app.usuarios.investidores()]))
    r.add("GET", "/cotacoes", lambda q: (200, app.cotacoes.listar()))
    r.add("POST", "/ordens", enviar_ordem)
    r.add("GET", "/ordens", lambda q: (200, [o.para_dict() for o in app.ordens.listar(q.query.get("usuario"))]))
    r.add("POST", "/ordens/:id/cancelar", cancelar)
    r.add("POST", "/bolsa/eventos", evento_bolsa)
    r.add("GET", "/notificacoes/:usuario", lambda q: (200, app.notificacoes.listar(q.params["usuario"])))
    r.add("GET", "/auditoria", auditoria)
    r.add("GET", "/mercado", mercado)
    r.add("PUT", "/mercado", definir_mercado)
    return criar_servidor(r, porta)
