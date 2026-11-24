"""RF4, RF5, RF7, RF8 - Envio, cancelamento, encaminhamento e ciclo de vida das ordens.
RNF3 / CA2 - Idempotência por ClientOrderId."""
import time

from ..dominio import (ESTADOS_FINAIS, ErroNaoEncontrado, ErroRegraNegocio, EstadoOrdem, Ordem,
                       validar_entrada_ordem)
from .risco import ValidadorRisco

ESTADOS_NOTIFICADOS = {EstadoOrdem.EXECUTADA, EstadoOrdem.REJEITADA, EstadoOrdem.CANCELADA}


class OrderService:
    def __init__(self, db, ordens_repo, contas_repo, ativos_repo, cotacoes, gateway, auditoria, notificacoes, validador=None):
        self.db = db
        self.ordens = ordens_repo
        self.contas = contas_repo
        self.ativos = ativos_repo
        self.cotacoes = cotacoes      # cache da ingestão de cotações (isolada - RT2)
        self.gateway = gateway        # cliente da bolsa simulada
        self.auditoria = auditoria
        self.notificacoes = notificacoes
        self.validador = validador or ValidadorRisco()

    def _transicionar(self, ordem, novo, responsavel=None):
        with self.db.transacao():
            ordem.transicionar(novo)
            self.ordens.salvar(ordem)
            self.auditoria.registrar(f"ORDEM_{ordem.estado.value}", responsavel or ordem.usuario, {
                "ordemId": ordem.id, "clientOrderId": ordem.client_order_id, "ativo": ordem.ativo, "lado": ordem.lado.value,
                "quantidade": ordem.quantidade, "motivo": ordem.motivo, "precoExecucao": ordem.preco_execucao})
            if ordem.estado in ESTADOS_NOTIFICADOS:
                self.notificacoes.notificar(ordem)

    def enviar(self, usuario, dados):
        dados = validar_entrada_ordem(dados, self.ativos.codigos_negociaveis())

        # CA2: checagem e criação na mesma transação -> mesmo ClientOrderId nunca vira duas ordens
        with self.db.transacao():
            existente = self.ordens.por_client_order_id(usuario, dados["clientOrderId"])
            if existente:
                self.auditoria.registrar("ORDEM_DUPLICADA_DESCARTADA", usuario, {"clientOrderId": dados["clientOrderId"], "ordemId": existente.id})
                return {"duplicada": True, "ordem": existente}
            ordem = Ordem.nova(usuario, dados)
            self.ordens.salvar(ordem)
            self.auditoria.registrar("ORDEM_CRIADA", usuario, {"ordemId": ordem.id, "clientOrderId": ordem.client_order_id,
                                                               "ativo": ordem.ativo, "lado": ordem.lado.value, "quantidade": ordem.quantidade})

        inicio = time.perf_counter()
        try:
            mercado_aberto = self.gateway.mercado_aberto()
        except Exception:
            mercado_aberto = False  # indisponibilidade segura: na dúvida, não envia

        # RF6: validação + bloqueio na mesma transação (atômico)
        with self.db.transacao():
            conta = self.contas.obter(usuario)
            resultado = self.validador.validar(ordem, conta, self.cotacoes.obter(ordem.ativo), mercado_aberto)
            ordem.latencia_risco_ms = round((time.perf_counter() - inicio) * 1000, 3)
            if not resultado.aprovada:
                ordem.motivo = resultado.motivo
                self._transicionar(ordem, EstadoOrdem.REJEITADA)
                return {"duplicada": False, "ordem": ordem}
            ordem.valor_estimado = resultado.valor_estimado
            conta.reservar(ordem)
            self.contas.salvar(conta)
            self._transicionar(ordem, EstadoOrdem.VALIDADA)

        # RF7: encaminhamento à bolsa (timeout + retry + circuit breaker dentro do gateway)
        try:
            resposta = self.gateway.enviar_ordem(ordem)
        except Exception as e:
            resposta = {"estado": "REJEITADA", "motivo": f"Bolsa indisponível: {e}"}
        self.aplicar_resposta_bolsa(ordem, resposta)
        return {"duplicada": False, "ordem": ordem}

    def aplicar_resposta_bolsa(self, ordem, resposta):
        estado = resposta.get("estado")
        with self.db.transacao():
            conta = self.contas.obter(ordem.usuario)
            if estado == "EXECUTADA":
                preco = resposta["precoExecucao"]
                ordem.preco_execucao = preco
                _, ordem.taxa = conta.liquidar(ordem, preco)
                self.contas.salvar(conta)
                self._transicionar(ordem, EstadoOrdem.EXECUTADA, "BOLSA")
            elif estado == "ABERTA":
                self._transicionar(ordem, EstadoOrdem.ABERTA, "BOLSA")
            elif estado == "CANCELADA":
                conta.liberar(ordem)
                self.contas.salvar(conta)
                self._transicionar(ordem, EstadoOrdem.CANCELADA, ordem.usuario)
            else:  # REJEITADA ou resposta inesperada: libera e rejeita, nunca perde a ordem
                conta.liberar(ordem)
                self.contas.salvar(conta)
                ordem.motivo = str(resposta.get("motivo") or "Rejeitada pela bolsa")[:200]
                self._transicionar(ordem, EstadoOrdem.REJEITADA, "BOLSA")

    def evento_bolsa(self, ordem_id, resposta):
        """Callback da bolsa quando uma ordem limitada é executada depois (UC08)."""
        ordem = self.ordens.obter(ordem_id)
        if not ordem:
            raise ErroNaoEncontrado("Ordem não encontrada")
        if ordem.estado == EstadoOrdem.ABERTA:  # eventos repetidos/atrasados são ignorados
            self.aplicar_resposta_bolsa(ordem, resposta)
        return ordem

    def cancelar(self, usuario, ordem_id):
        ordem = self.ordens.obter(ordem_id)
        if not ordem or ordem.usuario != usuario:  # investidor só vê as próprias ordens
            raise ErroNaoEncontrado("Ordem não encontrada")
        if ordem.estado in ESTADOS_FINAIS:  # RN4
            raise ErroRegraNegocio(f"Ordem em estado final ({ordem.estado.value}) não pode ser cancelada (RN4)")
        if ordem.estado != EstadoOrdem.ABERTA:
            raise ErroRegraNegocio("Ordem ainda em processamento, tente novamente")
        self.auditoria.registrar("CANCELAMENTO_SOLICITADO", usuario, {"ordemId": ordem.id})
        resposta = self.gateway.cancelar_ordem(ordem)
        if resposta.get("estado") == "EXECUTADA":
            self.aplicar_resposta_bolsa(ordem, resposta)
            raise ErroRegraNegocio("A ordem foi executada antes do cancelamento (RN4)")
        self.aplicar_resposta_bolsa(ordem, {"estado": "CANCELADA"})
        return ordem

    def listar(self, usuario=None):
        return self.ordens.listar(usuario)
