-- SentinelTrade - esquema relacional (SQLite)
-- Todos os dados são SIMULADOS (RT1).

CREATE TABLE usuarios (
    usuario     TEXT PRIMARY KEY CHECK (length(usuario) BETWEEN 3 AND 20),
    nome        TEXT NOT NULL,
    perfil      TEXT NOT NULL CHECK (perfil IN ('INVESTIDOR', 'ANALISTA_RISCO', 'AUDITOR', 'ADMINISTRADOR')),
    salt        TEXT NOT NULL,
    hash_senha  TEXT NOT NULL            -- scrypt(senha, salt); senha nunca é guardada em texto
);

CREATE TABLE ativos (
    codigo  TEXT PRIMARY KEY CHECK (length(codigo) BETWEEN 4 AND 6),
    nome    TEXT NOT NULL,
    tipo    TEXT NOT NULL CHECK (tipo IN ('ACAO', 'ETF', 'FII')),
    ativo   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE contas (
    usuario          TEXT PRIMARY KEY REFERENCES usuarios (usuario),
    saldo            REAL NOT NULL CHECK (saldo >= 0),
    saldo_bloqueado  REAL NOT NULL DEFAULT 0 CHECK (saldo_bloqueado >= 0),
    limite_diario    REAL NOT NULL CHECK (limite_diario > 0),
    operado_hoje     REAL NOT NULL DEFAULT 0
);

CREATE TABLE custodia (
    usuario     TEXT NOT NULL REFERENCES contas (usuario),
    ativo       TEXT NOT NULL REFERENCES ativos (codigo),
    quantidade  INTEGER NOT NULL CHECK (quantidade >= 0),
    bloqueada   INTEGER NOT NULL DEFAULT 0 CHECK (bloqueada >= 0 AND bloqueada <= quantidade),
    PRIMARY KEY (usuario, ativo)
);

CREATE TABLE ordens (
    id                 TEXT PRIMARY KEY,
    client_order_id    TEXT NOT NULL,
    usuario            TEXT NOT NULL REFERENCES usuarios (usuario),
    ativo              TEXT NOT NULL REFERENCES ativos (codigo),
    lado               TEXT NOT NULL CHECK (lado IN ('COMPRA', 'VENDA')),
    tipo               TEXT NOT NULL CHECK (tipo IN ('MERCADO', 'LIMITADA')),
    quantidade         INTEGER NOT NULL CHECK (quantidade > 0),
    preco_limite       REAL,
    estado             TEXT NOT NULL CHECK (estado IN ('CRIADA', 'VALIDADA', 'ABERTA', 'EXECUTADA', 'REJEITADA', 'CANCELADA')),
    valor_estimado     REAL,
    preco_execucao     REAL,
    taxa               REAL,
    motivo             TEXT,
    latencia_risco_ms  REAL,
    criada_em          TEXT NOT NULL,
    historico          TEXT NOT NULL,     -- JSON com as transições de estado
    UNIQUE (usuario, client_order_id)     -- idempotência garantida também no banco (RNF3/CA2)
);

CREATE TABLE notificacoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario   TEXT NOT NULL REFERENCES usuarios (usuario),
    ordem_id  TEXT NOT NULL REFERENCES ordens (id),
    estado    TEXT NOT NULL,
    mensagem  TEXT NOT NULL,
    em        TEXT NOT NULL
);

CREATE TABLE auditoria (
    seq            INTEGER PRIMARY KEY,
    timestamp      TEXT NOT NULL,          -- ISO-8601 UTC com milissegundos (CA4)
    tipo           TEXT NOT NULL,
    usuario        TEXT NOT NULL,
    dados          TEXT NOT NULL,          -- JSON, sem senhas/tokens
    hash_anterior  TEXT NOT NULL,
    hash           TEXT NOT NULL           -- SHA-256 encadeado (RF10)
);

-- Trilha imutável: o próprio banco bloqueia alteração e exclusão
CREATE TRIGGER auditoria_sem_update BEFORE UPDATE ON auditoria
BEGIN SELECT RAISE(ABORT, 'Trilha de auditoria é imutável'); END;

CREATE TRIGGER auditoria_sem_delete BEFORE DELETE ON auditoria
BEGIN SELECT RAISE(ABORT, 'Trilha de auditoria é imutável'); END;

CREATE INDEX idx_ordens_usuario ON ordens (usuario, criada_em);
CREATE INDEX idx_notificacoes_usuario ON notificacoes (usuario, id);
