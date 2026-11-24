"""Camada de domínio: entidades, estados, exceções e validação de entradas."""
import re
import uuid
from datetime import datetime, timezone
from enum import Enum


def agora_iso():
    """Data/hora UTC com milissegundos (CA4)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def r2(valor):
    return round(float(valor) + 1e-9, 2)


# ---------------------------------------------------------------- exceções
class ErroSentinel(Exception):
    status = 500


class ErroValidacao(ErroSentinel):
    status = 400


class ErroAutenticacao(ErroSentinel):
    status = 401


class ErroAutorizacao(ErroSentinel):
    status = 403


class ErroNaoEncontrado(ErroSentinel):
    status = 404


class ErroRegraNegocio(ErroSentinel):
    status = 409


# ---------------------------------------------------------------- enums
class Lado(str, Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"


class TipoOrdem(str, Enum):
    MERCADO = "MERCADO"
    LIMITADA = "LIMITADA"


class EstadoOrdem(str, Enum):
    CRIADA = "CRIADA"
    VALIDADA = "VALIDADA"
    ABERTA = "ABERTA"
    EXECUTADA = "EXECUTADA"
    REJEITADA = "REJEITADA"
    CANCELADA = "CANCELADA"


class Perfil(str, Enum):
    INVESTIDOR = "INVESTIDOR"
    ANALISTA_RISCO = "ANALISTA_RISCO"
    AUDITOR = "AUDITOR"
    ADMINISTRADOR = "ADMINISTRADOR"


# Máquina de estados da ordem (RF8)
TRANSICOES = {
    EstadoOrdem.CRIADA: {EstadoOrdem.VALIDADA, EstadoOrdem.REJEITADA},
    EstadoOrdem.VALIDADA: {EstadoOrdem.ABERTA, EstadoOrdem.EXECUTADA, EstadoOrdem.REJEITADA},
    EstadoOrdem.ABERTA: {EstadoOrdem.EXECUTADA, EstadoOrdem.CANCELADA},
    EstadoOrdem.EXECUTADA: set(),
    EstadoOrdem.REJEITADA: set(),
    EstadoOrdem.CANCELADA: set(),
}
ESTADOS_FINAIS = {EstadoOrdem.EXECUTADA, EstadoOrdem.REJEITADA, EstadoOrdem.CANCELADA}


# ---------------------------------------------------------------- entidade Ordem
class Ordem:
    """Entidade Ordem. O estado é privado e só muda por transicionar() (encapsulamento)."""

    def __init__(self, id, client_order_id, usuario, ativo, lado, tipo, quantidade, preco_limite=None,
                 estado=EstadoOrdem.CRIADA, criada_em=None, historico=None, **extras):
        self.__id = id
        self.__client_order_id = client_order_id
        self.__usuario = usuario
        self.__ativo = ativo
        self.__lado = Lado(lado)
        self.__tipo = TipoOrdem(tipo)
        self.__quantidade = int(quantidade)
        self.__preco_limite = preco_limite
        self.__estado = EstadoOrdem(estado)
        self.__criada_em = criada_em or agora_iso()
        self.__historico = historico or [{"estado": self.__estado.value, "em": self.__criada_em}]
        self.valor_estimado = extras.get("valor_estimado")
        self.preco_execucao = extras.get("preco_execucao")
        self.taxa = extras.get("taxa")
        self.motivo = extras.get("motivo")
        self.latencia_risco_ms = extras.get("latencia_risco_ms")

    @classmethod
    def nova(cls, usuario, dados):
        return cls(str(uuid.uuid4()), dados["clientOrderId"], usuario, dados["ativo"], dados["lado"],
                   dados["tipo"], dados["quantidade"], dados.get("precoLimite"))

    id = property(lambda s: s.__id)
    client_order_id = property(lambda s: s.__client_order_id)
    usuario = property(lambda s: s.__usuario)
    ativo = property(lambda s: s.__ativo)
    lado = property(lambda s: s.__lado)
    tipo = property(lambda s: s.__tipo)
    quantidade = property(lambda s: s.__quantidade)
    preco_limite = property(lambda s: s.__preco_limite)
    estado = property(lambda s: s.__estado)
    criada_em = property(lambda s: s.__criada_em)
    historico = property(lambda s: list(s.__historico))

    @property
    def finalizada(self):
        return self.__estado in ESTADOS_FINAIS

    def transicionar(self, novo):
        novo = EstadoOrdem(novo)
        if novo not in TRANSICOES[self.__estado]:
            raise ErroRegraNegocio(f"Transição inválida: {self.__estado.value} -> {novo.value}")
        self.__estado = novo
        self.__historico.append({"estado": novo.value, "em": agora_iso()})

    def para_dict(self):
        return {
            "id": self.id, "clientOrderId": self.client_order_id, "usuario": self.usuario, "ativo": self.ativo,
            "lado": self.lado.value, "tipo": self.tipo.value, "quantidade": self.quantidade,
            "precoLimite": self.preco_limite, "estado": self.estado.value, "criadaEm": self.criada_em,
            "historico": self.historico, "valorEstimado": self.valor_estimado, "precoExecucao": self.preco_execucao,
            "taxa": self.taxa, "motivo": self.motivo, "latenciaRiscoMs": self.latencia_risco_ms,
        }


# ---------------------------------------------------------------- validação de entradas (allowlist)
RE_ATIVO = re.compile(r"^[A-Z0-9]{4,6}$")
RE_CLIENT_ORDER_ID = re.compile(r"^[A-Za-z0-9-]{1,40}$")
RE_USUARIO = re.compile(r"^[a-z]{3,20}$")
RE_CODIGO_MFA = re.compile(r"^\d{6}$")
QTD_MAXIMA = 1_000_000
PRECO_MAXIMO = 1_000_000


def validar_entrada_ordem(dados, ativos_permitidos):
    """Valida tipo, formato, tamanho e faixa de cada campo ANTES de qualquer processamento."""
    coid = str(dados.get("clientOrderId", "")).strip()
    if not RE_CLIENT_ORDER_ID.match(coid):
        raise ErroValidacao("clientOrderId inválido (1 a 40 caracteres: letras, números e hífen)")
    ativo = str(dados.get("ativo", "")).strip().upper()
    if not RE_ATIVO.match(ativo) or ativo not in ativos_permitidos:
        raise ErroValidacao("Ativo inválido ou não negociável")
    lado = dados.get("lado")
    if lado not in {l.value for l in Lado}:
        raise ErroValidacao("Lado inválido (COMPRA ou VENDA)")
    tipo = dados.get("tipo")
    if tipo not in {t.value for t in TipoOrdem}:
        raise ErroValidacao("Tipo inválido (MERCADO ou LIMITADA)")
    qtd = dados.get("quantidade")
    if isinstance(qtd, bool) or not isinstance(qtd, int) or not 1 <= qtd <= QTD_MAXIMA:
        raise ErroValidacao(f"Quantidade deve ser inteiro entre 1 e {QTD_MAXIMA}")
    preco = None
    if tipo == TipoOrdem.LIMITADA.value:
        try:
            preco = round(float(dados.get("precoLimite")), 2)
        except (TypeError, ValueError):
            raise ErroValidacao("Ordem limitada exige preço limite numérico")
        if not 0.01 <= preco <= PRECO_MAXIMO:
            raise ErroValidacao("Preço limite fora da faixa permitida")
    return {"clientOrderId": coid, "ativo": ativo, "lado": lado, "tipo": tipo, "quantidade": qtd, "precoLimite": preco}
