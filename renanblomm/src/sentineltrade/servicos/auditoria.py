"""RF10 / CA4 - Trilha de auditoria imutável com hash encadeado (SHA-256).
Cada registro guarda o hash do anterior; alterar qualquer registro quebra a cadeia.
Além disso, triggers no banco impedem UPDATE e DELETE na tabela."""
import hashlib
import json

from ..dominio import agora_iso


def _hash(base):
    return hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class AuditLogger:
    def __init__(self, db):
        self.db = db

    def registrar(self, tipo, usuario, dados=None):
        with self.db.transacao() as con:
            ultimo = con.execute("SELECT seq, hash FROM auditoria ORDER BY seq DESC LIMIT 1").fetchone()
            base = {
                "seq": (ultimo["seq"] + 1) if ultimo else 1,
                "timestamp": agora_iso(),
                "tipo": tipo,
                "usuario": usuario,
                "dados": dados or {},
                "hashAnterior": ultimo["hash"] if ultimo else "GENESIS",
            }
            h = _hash(base)
            con.execute("INSERT INTO auditoria (seq, timestamp, tipo, usuario, dados, hash_anterior, hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (base["seq"], base["timestamp"], tipo, usuario, json.dumps(base["dados"], ensure_ascii=False), base["hashAnterior"], h))
            return {**base, "hash": h}

    def listar(self, limite=None):
        sql = "SELECT * FROM auditoria ORDER BY seq"
        return [{"seq": r["seq"], "timestamp": r["timestamp"], "tipo": r["tipo"], "usuario": r["usuario"],
                 "dados": json.loads(r["dados"]), "hashAnterior": r["hash_anterior"], "hash": r["hash"]}
                for r in self.db.consultar(sql)]

    @staticmethod
    def verificar_cadeia(registros):
        anterior = "GENESIS"
        for r in registros:
            base = {k: v for k, v in r.items() if k != "hash"}
            if r["hashAnterior"] != anterior or _hash(base) != r["hash"]:
                return {"integro": False, "falhaNoRegistro": r["seq"], "total": len(registros)}
            anterior = r["hash"]
        return {"integro": True, "total": len(registros)}

    def verificar_integridade(self):
        return self.verificar_cadeia(self.listar())
