"""Composição da aplicação (injeção de dependências): liga persistência, serviços e integrações."""
from types import SimpleNamespace

from .integracoes import GatewayBolsa, IngestaoCotacoes
from .persistencia import AtivoRepositorio, BancoDados, ContaRepositorio, OrdemRepositorio, UsuarioRepositorio
from .servicos.auditoria import AuditLogger
from .servicos.autenticacao import AuthService
from .servicos.notificacoes import NotificationService
from .servicos.ordens import OrderService


def montar_aplicacao(db_path, url_bolsa, url_cotacoes, url_callback, gateway=None, cotacoes=None):
    db = BancoDados(db_path)
    auditoria = AuditLogger(db)
    usuarios = UsuarioRepositorio(db)
    contas = ContaRepositorio(db)
    notificacoes = NotificationService(db)
    gateway = gateway or GatewayBolsa(url_bolsa, url_callback)
    cotacoes = cotacoes or IngestaoCotacoes(url_cotacoes)
    ordens = OrderService(db, OrdemRepositorio(db), contas, AtivoRepositorio(db), cotacoes, gateway, auditoria, notificacoes)
    return SimpleNamespace(db=db, auditoria=auditoria, usuarios=usuarios, contas=contas, notificacoes=notificacoes,
                           gateway=gateway, cotacoes=cotacoes, ordens=ordens, auth=AuthService(usuarios, auditoria))
