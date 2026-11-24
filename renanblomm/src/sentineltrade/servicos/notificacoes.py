"""RF9 - Notificação do investidor sobre execução, rejeição e cancelamento."""
from ..dominio import EstadoOrdem, agora_iso


class NotificationService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _texto(o):
        base = f"Ordem de {o.lado.value.lower()} de {o.quantidade} {o.ativo}"
        if o.estado == EstadoOrdem.EXECUTADA:
            return f"{base} EXECUTADA a R$ {o.preco_execucao:.2f}"
        if o.estado == EstadoOrdem.REJEITADA:
            return f"{base} REJEITADA: {o.motivo}"
        return f"{base} CANCELADA"

    def notificar(self, ordem):
        with self.db.transacao() as con:
            con.execute("INSERT INTO notificacoes (usuario, ordem_id, estado, mensagem, em) VALUES (?, ?, ?, ?, ?)",
                        (ordem.usuario, ordem.id, ordem.estado.value, self._texto(ordem), agora_iso()))

    def listar(self, usuario, limite=10):
        return [dict(r) for r in self.db.consultar(
            "SELECT ordem_id AS ordemId, estado, mensagem, em FROM notificacoes WHERE usuario = ? ORDER BY id DESC LIMIT ?", (usuario, limite))]
