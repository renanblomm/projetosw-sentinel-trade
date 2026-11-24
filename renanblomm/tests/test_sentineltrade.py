"""Testes das regras críticas do SentinelTrade. Rodar: python -m unittest discover -s tests -v
Cada teste cita o caso de teste (CT) da matriz de rastreabilidade."""
import contextlib
import io
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentineltrade.app import montar_aplicacao  # noqa: E402
from sentineltrade.dominio import ErroAutenticacao, ErroRegraNegocio, ErroValidacao, EstadoOrdem  # noqa: E402
from sentineltrade.integracoes import CircuitBreaker  # noqa: E402


class BolsaFalsa:
    def __init__(self, resposta=None, aberto=True, falha=False):
        self.resposta = resposta or {"estado": "EXECUTADA", "precoExecucao": 40.0}
        self.aberto, self.falha, self.chamadas = aberto, falha, 0
        self.breaker = CircuitBreaker("teste")

    def mercado_aberto(self):
        return self.aberto

    def enviar_ordem(self, o):
        self.chamadas += 1
        if self.falha:
            raise ConnectionError("timeout")
        return dict(self.resposta)

    def cancelar_ordem(self, o):
        return {"estado": "CANCELADA"}


class CotacoesFalsas:
    def obter(self, ativo):
        return {"ativo": ativo, "preco": 40.0} if ativo in ("PETR4", "VALE3") else None


def montar(**kw):
    bolsa = BolsaFalsa(**kw)
    return montar_aplicacao(":memory:", "", "", "", gateway=bolsa, cotacoes=CotacoesFalsas()), bolsa


def ordem(**extra):
    return {"clientOrderId": "C1", "ativo": "PETR4", "lado": "COMPRA", "tipo": "MERCADO", "quantidade": 10, **extra}


class TestAutenticacao(unittest.TestCase):
    def test_ct1_login_exige_senha_e_mfa(self):
        app, _ = montar()
        with self.assertRaises(ErroAutenticacao):
            app.auth.login("ana", "errada")
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            d = app.auth.login("ana", "Sentinel@2026")
        codigo = saida.getvalue().strip().split()[-1]
        with self.assertRaises(ErroAutenticacao):
            app.auth.verificar_mfa(d["desafioId"], "000000" if codigo != "000000" else "111111")
        s = app.auth.verificar_mfa(d["desafioId"], codigo)
        self.assertIsNotNone(app.auth.validar_sessao(s["token"]))
        self.assertIsNone(app.auth.validar_sessao("token-falso"))


class TestOrdens(unittest.TestCase):
    def test_ct2_consulta_carteira(self):
        app, _ = montar()
        r = app.contas.obter("ana").resumo()
        self.assertEqual(r["saldoDisponivel"], 50000)
        self.assertIn({"ativo": "PETR4", "quantidade": 200, "bloqueada": 0, "livre": 200}, r["custodia"])

    def test_ct4_ct7_compra_validada_enviada_e_executada(self):
        app, _ = montar()
        o = app.ordens.enviar("ana", ordem())["ordem"]
        self.assertEqual(o.estado, EstadoOrdem.EXECUTADA)
        self.assertEqual([h["estado"] for h in o.historico], ["CRIADA", "VALIDADA", "EXECUTADA"])
        r = app.contas.obter("ana").resumo()
        self.assertEqual(r["saldoBloqueado"], 0)
        self.assertEqual(r["saldoTotal"], 50000 - 400 - 0.4)

    def test_ct5_cancelamento_libera_saldo(self):
        app, _ = montar(resposta={"estado": "ABERTA"})
        o = app.ordens.enviar("ana", ordem(tipo="LIMITADA", precoLimite=35))["ordem"]
        self.assertEqual(o.estado, EstadoOrdem.ABERTA)
        self.assertGreater(app.contas.obter("ana").saldo_bloqueado, 0)
        app.ordens.cancelar("ana", o.id)
        self.assertEqual(app.ordens.ordens.obter(o.id).estado, EstadoOrdem.CANCELADA)
        self.assertEqual(app.contas.obter("ana").saldo_bloqueado, 0)

    def test_ct5_rn4_ordem_executada_nao_cancela(self):
        app, _ = montar()
        o = app.ordens.enviar("ana", ordem())["ordem"]
        with self.assertRaises(ErroRegraNegocio):
            app.ordens.cancelar("ana", o.id)

    def test_ct6_ca3_saldo_insuficiente_nao_chega_na_bolsa(self):
        app, bolsa = montar()
        o = app.ordens.enviar("ana", ordem(quantidade=5000))["ordem"]
        self.assertEqual(o.estado, EstadoOrdem.REJEITADA)
        self.assertIn("Saldo insuficiente", o.motivo)
        self.assertEqual(bolsa.chamadas, 0)

    def test_ct6_rn2_venda_sem_custodia(self):
        app, _ = montar()
        o = app.ordens.enviar("ana", ordem(lado="VENDA", quantidade=999))["ordem"]
        self.assertIn("Custódia insuficiente", o.motivo)

    def test_ct6_rn3_mercado_fechado(self):
        app, _ = montar(aberto=False)
        self.assertIn("Mercado fechado", app.ordens.enviar("ana", ordem())["ordem"].motivo)

    def test_ct6_rn5_limite_diario(self):
        app, _ = montar()
        with app.db.transacao():
            c = app.contas.obter("ana")
            c.definir_limite(300)
            app.contas.salvar(c)
        self.assertIn("Limite diário", app.ordens.enviar("ana", ordem())["ordem"].motivo)

    def test_ct11_ca2_idempotencia(self):
        app, bolsa = montar()
        a = app.ordens.enviar("ana", ordem())
        b = app.ordens.enviar("ana", ordem())
        self.assertTrue(b["duplicada"])
        self.assertEqual(a["ordem"].id, b["ordem"].id)
        self.assertEqual(bolsa.chamadas, 1)

    def test_ct14_validacao_de_entrada(self):
        app, _ = montar()
        for ruim in (ordem(ativo="PETR4'; DROP TABLE ordens;--"), ordem(quantidade=-5), ordem(quantidade="10"),
                     ordem(lado="EMPRESTAR"), ordem(tipo="LIMITADA"), ordem(clientOrderId="<script>")):
            with self.assertRaises(ErroValidacao):
                app.ordens.enviar("ana", ruim)

    def test_ct8_transicao_invalida_bloqueada(self):
        app, _ = montar()
        o = app.ordens.enviar("ana", ordem())["ordem"]
        with self.assertRaises(ErroRegraNegocio):
            o.transicionar(EstadoOrdem.ABERTA)

    def test_ct13_bolsa_fora_do_ar_nao_corrompe_carteira(self):
        app, _ = montar(falha=True)
        o = app.ordens.enviar("ana", ordem())["ordem"]
        self.assertEqual(o.estado, EstadoOrdem.REJEITADA)
        self.assertIn("Bolsa indisponível", o.motivo)
        r = app.contas.obter("ana").resumo()
        self.assertEqual((r["saldoTotal"], r["saldoBloqueado"]), (50000, 0))

    def test_ct9_notificacoes(self):
        app, _ = montar()
        app.ordens.enviar("ana", ordem())
        app.ordens.enviar("ana", ordem(clientOrderId="C2", quantidade=5000))
        self.assertEqual([n["estado"] for n in app.notificacoes.listar("ana")], ["REJEITADA", "EXECUTADA"])

    def test_ct12_rnf1_risco_abaixo_de_50ms(self):
        app, _ = montar()
        self.assertLess(app.ordens.enviar("ana", ordem())["ordem"].latencia_risco_ms, 50)


class TestAuditoria(unittest.TestCase):
    def test_ct10_ca4_log_utc_ms_e_integridade(self):
        app, _ = montar()
        app.ordens.enviar("ana", ordem())
        regs = app.auditoria.listar()
        self.assertRegex(regs[0]["timestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        self.assertEqual(regs[0]["usuario"], "ana")
        self.assertTrue(app.auditoria.verificar_integridade()["integro"])
        regs[1]["usuario"] = "invasor"  # adulteração em memória é detectada
        self.assertEqual(app.auditoria.verificar_cadeia(regs)["falhaNoRegistro"], 2)

    def test_ct10_banco_bloqueia_alteracao_da_trilha(self):
        app, _ = montar()
        app.auditoria.registrar("TESTE", "ana")
        with self.assertRaises(sqlite3.IntegrityError):
            app.db.con.execute("UPDATE auditoria SET usuario = 'invasor'")
        with self.assertRaises(sqlite3.IntegrityError):
            app.db.con.execute("DELETE FROM auditoria")


class TestResiliencia(unittest.TestCase):
    def test_ct13_circuit_breaker_abre(self):
        cb = CircuitBreaker("teste", limite_falhas=2, tempo_reabertura_s=60)

        def falha():
            raise ConnectionError("fora")
        for _ in range(2):
            with self.assertRaises(ConnectionError):
                cb.executar(falha)
        self.assertEqual(cb.estado, "ABERTO")
        with self.assertRaises(ConnectionError):
            cb.executar(lambda: "ok")


if __name__ == "__main__":
    unittest.main()
