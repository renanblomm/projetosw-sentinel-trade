"""RF1 / CA1 - Autenticação com senha (hash scrypt) + segundo fator (MFA simulado).
O código MFA é exibido no console do servidor, simulando um SMS/e-mail (RT1)."""
import hashlib
import hmac
import logging
import secrets
import threading
import time

from ..dominio import RE_CODIGO_MFA, RE_USUARIO, ErroAutenticacao

log = logging.getLogger("sentineltrade.mfa")

VALIDADE_MFA_S = 120
VALIDADE_SESSAO_S = 3600
MAX_TENTATIVAS_MFA = 3
MAX_FALHAS_LOGIN = 5
BLOQUEIO_LOGIN_S = 60


def hash_senha(senha, salt_hex):
    return hashlib.scrypt(senha.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1, dklen=32).hex()


class AuthService:
    def __init__(self, usuarios_repo, auditoria):
        self._usuarios = usuarios_repo
        self._auditoria = auditoria
        self._desafios = {}
        self._sessoes = {}
        self._falhas = {}
        self._lock = threading.Lock()

    def login(self, usuario, senha):
        usuario, senha = str(usuario or ""), str(senha or "")
        # mensagem genérica: não revela se o erro foi no usuário ou na senha
        if not RE_USUARIO.match(usuario) or not 1 <= len(senha) <= 128:
            raise ErroAutenticacao("Usuário ou senha inválidos")
        with self._lock:
            falhas, desde = self._falhas.get(usuario, (0, 0))
            if falhas >= MAX_FALHAS_LOGIN and time.time() - desde < BLOQUEIO_LOGIN_S:
                raise ErroAutenticacao("Muitas tentativas. Aguarde 1 minuto.")
        u = self._usuarios.obter(usuario)
        if not u or not hmac.compare_digest(hash_senha(senha, u["salt"]), u["hash_senha"]):
            with self._lock:
                f, _ = self._falhas.get(usuario, (0, 0))
                self._falhas[usuario] = (f + 1, time.time())
            self._auditoria.registrar("LOGIN_FALHA", usuario)
            raise ErroAutenticacao("Usuário ou senha inválidos")
        self._falhas.pop(usuario, None)
        desafio = secrets.token_urlsafe(16)
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        with self._lock:
            self._desafios[desafio] = {"usuario": usuario, "codigo": codigo, "expira": time.time() + VALIDADE_MFA_S, "tentativas": 0}
        print(f"\n[MFA simulado] Código de verificação para '{usuario}': {codigo}\n", flush=True)
        self._auditoria.registrar("LOGIN_SENHA_OK", usuario)
        return {"desafioId": desafio, "mensagem": "Senha correta. Informe o código MFA enviado."}

    def verificar_mfa(self, desafio_id, codigo):
        codigo = str(codigo or "").strip()
        with self._lock:
            d = self._desafios.get(str(desafio_id or ""))
            if not d or time.time() > d["expira"]:
                raise ErroAutenticacao("Desafio MFA inválido ou expirado")
            if not RE_CODIGO_MFA.match(codigo) or not hmac.compare_digest(codigo, d["codigo"]):
                d["tentativas"] += 1
                if d["tentativas"] >= MAX_TENTATIVAS_MFA:
                    del self._desafios[desafio_id]
                usuario, tent = d["usuario"], d["tentativas"]
                erro = True
            else:
                del self._desafios[desafio_id]
                erro = False
        if erro:
            self._auditoria.registrar("MFA_FALHA", usuario, {"tentativas": tent})
            raise ErroAutenticacao("Código MFA incorreto")
        u = self._usuarios.obter(d["usuario"])
        token = secrets.token_hex(24)
        with self._lock:
            self._sessoes[token] = {"usuario": u["usuario"], "nome": u["nome"], "perfil": u["perfil"], "expira": time.time() + VALIDADE_SESSAO_S}
        self._auditoria.registrar("LOGIN_MFA_OK", u["usuario"])
        return {"token": token, "usuario": u["usuario"], "nome": u["nome"], "perfil": u["perfil"]}

    def validar_sessao(self, token):
        """Sessão só existe depois do MFA validado (CA1)."""
        s = self._sessoes.get(str(token or ""))
        if not s or time.time() > s["expira"]:
            return None
        return {k: v for k, v in s.items() if k != "expira"}

    def logout(self, token):
        s = self._sessoes.pop(str(token or ""), None)
        if s:
            self._auditoria.registrar("LOGOUT", s["usuario"])
