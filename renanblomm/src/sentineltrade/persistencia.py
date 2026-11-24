"""Camada de persistência: banco SQLite e repositórios.
Todas as consultas são PARAMETRIZADAS (?), nunca concatenam entrada do usuário (prevenção de SQL Injection)."""
import json
import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager

from .dominio import ErroNaoEncontrado, Ordem
from .servicos.contas import Conta

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class BancoDados:
    def __init__(self, caminho=":memory:", recriar=True):
        if recriar and caminho != ":memory:" and os.path.exists(caminho):
            os.remove(caminho)
        self.con = sqlite3.connect(caminho, check_same_thread=False, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        self._profundidade = 0
        if recriar:
            for arquivo in ("schema.sql", "seed.sql"):
                with open(os.path.join(RAIZ, "database", arquivo), encoding="utf-8") as f:
                    self.con.executescript(f.read())

    @contextmanager
    def transacao(self):
        """Transação reentrante: o lock garante que checagem + bloqueio de saldo sejam atômicos."""
        with self._lock:
            externa = self._profundidade == 0
            if externa:
                self.con.execute("BEGIN IMMEDIATE")
            self._profundidade += 1
            try:
                yield self.con
                self._profundidade -= 1
                if externa:
                    self.con.execute("COMMIT")
            except BaseException:
                self._profundidade -= 1
                if externa:
                    self.con.execute("ROLLBACK")
                raise

    def consultar(self, sql, params=()):
        with self._lock:
            return self.con.execute(sql, params).fetchall()


class Repositorio(ABC):
    """Interface (classe abstrata) comum aos repositórios."""

    def __init__(self, db: BancoDados):
        self.db = db

    @abstractmethod
    def obter(self, chave):
        ...


class UsuarioRepositorio(Repositorio):
    def obter(self, usuario):
        linhas = self.db.consultar("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
        return dict(linhas[0]) if linhas else None

    def investidores(self):
        return [r["usuario"] for r in self.db.consultar("SELECT usuario FROM usuarios WHERE perfil = 'INVESTIDOR' ORDER BY usuario")]


class AtivoRepositorio(Repositorio):
    def obter(self, codigo):
        linhas = self.db.consultar("SELECT * FROM ativos WHERE codigo = ? AND ativo = 1", (codigo,))
        return dict(linhas[0]) if linhas else None

    def codigos_negociaveis(self):
        return {r["codigo"] for r in self.db.consultar("SELECT codigo FROM ativos WHERE ativo = 1")}


class ContaRepositorio(Repositorio):
    def obter(self, usuario):
        linhas = self.db.consultar("SELECT * FROM contas WHERE usuario = ?", (usuario,))
        if not linhas:
            raise ErroNaoEncontrado("Conta não encontrada")
        c = linhas[0]
        custodia = {r["ativo"]: [r["quantidade"], r["bloqueada"]] for r in
                    self.db.consultar("SELECT ativo, quantidade, bloqueada FROM custodia WHERE usuario = ?", (usuario,))}
        return Conta(c["usuario"], c["saldo"], c["saldo_bloqueado"], c["limite_diario"], c["operado_hoje"], custodia)

    def salvar(self, conta: Conta):
        with self.db.transacao() as con:
            con.execute("UPDATE contas SET saldo = ?, saldo_bloqueado = ?, limite_diario = ?, operado_hoje = ? WHERE usuario = ?",
                        (conta.saldo, conta.saldo_bloqueado, conta.limite_diario, conta.operado_hoje, conta.usuario))
            for ativo, (qtd, bloq) in conta.custodia.items():
                con.execute("INSERT INTO custodia (usuario, ativo, quantidade, bloqueada) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT(usuario, ativo) DO UPDATE SET quantidade = excluded.quantidade, bloqueada = excluded.bloqueada",
                            (conta.usuario, ativo, qtd, bloq))


class OrdemRepositorio(Repositorio):
    @staticmethod
    def _montar(r):
        return Ordem(r["id"], r["client_order_id"], r["usuario"], r["ativo"], r["lado"], r["tipo"], r["quantidade"],
                     r["preco_limite"], r["estado"], r["criada_em"], json.loads(r["historico"]),
                     valor_estimado=r["valor_estimado"], preco_execucao=r["preco_execucao"], taxa=r["taxa"],
                     motivo=r["motivo"], latencia_risco_ms=r["latencia_risco_ms"])

    def obter(self, ordem_id):
        linhas = self.db.consultar("SELECT * FROM ordens WHERE id = ?", (ordem_id,))
        return self._montar(linhas[0]) if linhas else None

    def por_client_order_id(self, usuario, client_order_id):
        linhas = self.db.consultar("SELECT * FROM ordens WHERE usuario = ? AND client_order_id = ?", (usuario, client_order_id))
        return self._montar(linhas[0]) if linhas else None

    def listar(self, usuario=None, limite=50):
        if usuario:
            linhas = self.db.consultar("SELECT * FROM ordens WHERE usuario = ? ORDER BY criada_em DESC LIMIT ?", (usuario, limite))
        else:
            linhas = self.db.consultar("SELECT * FROM ordens ORDER BY criada_em DESC LIMIT ?", (limite,))
        return [self._montar(r) for r in linhas]

    def salvar(self, o: Ordem):
        with self.db.transacao() as con:
            con.execute(
                "INSERT INTO ordens (id, client_order_id, usuario, ativo, lado, tipo, quantidade, preco_limite, estado, valor_estimado, "
                "preco_execucao, taxa, motivo, latencia_risco_ms, criada_em, historico) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET estado = excluded.estado, valor_estimado = excluded.valor_estimado, "
                "preco_execucao = excluded.preco_execucao, taxa = excluded.taxa, motivo = excluded.motivo, "
                "latencia_risco_ms = excluded.latencia_risco_ms, historico = excluded.historico",
                (o.id, o.client_order_id, o.usuario, o.ativo, o.lado.value, o.tipo.value, o.quantidade, o.preco_limite,
                 o.estado.value, o.valor_estimado, o.preco_execucao, o.taxa, o.motivo, o.latencia_risco_ms, o.criada_em,
                 json.dumps(o.historico)))
