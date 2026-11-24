"""Infraestrutura HTTP mínima (biblioteca padrão): roteador, servidor e cliente com timeout."""
import json
import logging
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .dominio import ErroSentinel

log = logging.getLogger("sentineltrade.http")
MAX_CORPO_BYTES = 16 * 1024  # limita o tamanho das requisições


class Requisicao:
    def __init__(self, params, corpo, query, headers):
        self.params = params
        self.corpo = corpo
        self.query = query
        self.headers = headers


class Roteador:
    def __init__(self):
        self._rotas = []

    def add(self, metodo, caminho, funcao):
        chaves = []

        def troca(m):
            chaves.append(m.group(1))
            return "([A-Za-z0-9_-]+)"  # parâmetros de rota só aceitam caracteres seguros

        self._rotas.append((metodo, re.compile("^" + re.sub(r":(\w+)", troca, caminho) + "$"), chaves, funcao))

    def resolver(self, metodo, caminho):
        for m, regex, chaves, funcao in self._rotas:
            if m != metodo:
                continue
            achou = regex.match(caminho)
            if achou:
                return funcao, dict(zip(chaves, achou.groups()))
        return None, None


def criar_servidor(roteador, porta, host="127.0.0.1", estaticos=None):
    """estaticos: dict {'/caminho': (arquivo, content-type)} - allowlist de arquivos servidos."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencia o log padrão
            pass

        def _responder(self, status, corpo, tipo="application/json; charset=utf-8"):
            dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(dados)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'")
            self.end_headers()
            try:
                self.wfile.write(dados)
            except (BrokenPipeError, ConnectionResetError):
                pass  # cliente desistiu (timeout); nada a fazer

        def _tratar(self, metodo):
            url = urlparse(self.path)
            if metodo == "GET" and estaticos and url.path in estaticos:
                arquivo, tipo = estaticos[url.path]
                with open(arquivo, "rb") as f:
                    return self._responder(200, f.read(), tipo)
            funcao, params = roteador.resolver(metodo, url.path)
            if not funcao:
                return self._responder(404, {"erro": "Rota não encontrada"})
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if tamanho > MAX_CORPO_BYTES:
                    return self._responder(413, {"erro": "Requisição muito grande"})
                corpo = {}
                if tamanho:
                    corpo = json.loads(self.rfile.read(tamanho))
                    if not isinstance(corpo, dict):
                        raise ValueError
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                status, resposta = funcao(Requisicao(params, corpo, query, self.headers))
                return self._responder(status, resposta)
            except ErroSentinel as e:
                self._responder(e.status, {"erro": str(e)})
            except (ValueError, json.JSONDecodeError):
                self._responder(400, {"erro": "Corpo da requisição inválido"})
            except Exception:  # tratamento seguro: não expõe detalhes internos ao cliente
                log.exception("Erro inesperado em %s %s", metodo, url.path)
                self._responder(500, {"erro": "Erro interno"})

        def do_GET(self):
            self._tratar("GET")

        def do_POST(self):
            self._tratar("POST")

        def do_PUT(self):
            self._tratar("PUT")

    servidor = ThreadingHTTPServer((host, porta), Handler)
    servidor.daemon_threads = True
    return servidor


def requisicao(metodo, url, corpo=None, headers=None, timeout=2.0):
    """Cliente HTTP com timeout. Retorna (status, json)."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except json.JSONDecodeError:
            return e.code, {}
