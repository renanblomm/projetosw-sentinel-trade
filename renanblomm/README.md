# SentinelTrade

Plataforma **simulada** de negociação de ativos financeiros (ações, ETFs e FIIs) da corretora fictícia Orion Capital, com autenticação MFA, validação de risco pré-trade, prevenção de ordens duplicadas, BFF e trilha de auditoria imutável.

> ⚠️ **Aviso:** este projeto opera **exclusivamente com dados e operações simuladas**. Não há dinheiro real nem conexão com a B3 ou qualquer bolsa de verdade. Usuários, saldos e cotações são fictícios.

## Integrantes

- Jonatas Simonton Gouveia — 10736320
- Leandro Solovjovas dos Santos — 10438426
- Renan V. B. Rodrigues — 10735008

## Objetivo

Permitir que investidores autenticados acompanhem carteira e cotações e enviem ordens de compra e venda que **só chegam à bolsa simulada depois de validadas** (saldo, custódia, limite diário e mercado aberto), garantindo que nenhuma ordem seja processada duas vezes e que todo evento fique registrado numa auditoria verificável.

## Escopo

**Dentro:** login + MFA simulado; carteira e cotações; ordens a mercado e limitadas; cancelamento; risco pré-trade; ciclo de vida da ordem; notificações; auditoria com hash encadeado; painel do Analista de Risco (limites e mercado); painel do Auditor.

**Fora (nesta fase):** dinheiro real/B3; execução parcial; cadastro de investidores e ativos pela interface (tabelas já existem, interface planejada).

## Tecnologias e dependências

| Item | Escolha |
| :--- | :--- |
| Linguagem | **Python 3.10+** |
| Banco de dados | **SQLite** (relacional, módulo `sqlite3` da biblioteca padrão) |
| Servidor HTTP | `http.server` (biblioteca padrão) |
| Hash de senha | `hashlib.scrypt` + salt |
| Testes | `unittest` |
| Interface | HTML + CSS + JavaScript puro, servidos pelo BFF |
| Dependências externas | **Nenhuma**: não é preciso `pip install`, o que reduz a superfície de ataque da cadeia de dependências |

## Como executar

```bash
# 1. (opcional) copie as variáveis de exemplo
cp .env.example .env

# 2. suba o sistema (provedor de cotações, bolsa simulada, core e BFF)
python src/main.py
```

Acesse **http://localhost:3000**. O banco `database/sentineltrade.db` é recriado a cada execução a partir de `schema.sql` + `seed.sql`.

**Usuários de demonstração (fictícios)**, todos com a senha `Sentinel@2026`:

| Usuário | Perfil | Observação |
| :--- | :--- | :--- |
| `ana` | Investidor | R$ 50.000, PETR4, VALE3, MXRF11 |
| `bruno` | Investidor | R$ 5.000, ITUB4 |
| `carlos` | Analista de Risco | limites, mercado, fluxo de ordens, auditoria |
| `diana` | Auditor | somente leitura da auditoria |

O **código MFA** aparece no terminal onde o sistema está rodando (simula um SMS):
`[MFA simulado] Código de verificação para 'ana': 123456`

### Testes

```bash
python -m unittest discover -s tests -v
```

## Arquitetura

```
Navegador ──► BFF :3000 ──► Core :4000 ──► SQLite
              (única porta     │  ├─► Bolsa simulada :4001 ──(callback)──► Core
               pública)        │  └─► Provedor de cotações :4002
```

- **BFF (Backend for Frontend):** única porta acessada pelo navegador. Valida a sessão pós-MFA, aplica o controle por perfil, agrega várias chamadas internas numa só resposta (`/api/painel`) e esconde os serviços internos.
- **Core:** regras de negócio (ordens, risco, contas, autenticação, auditoria, notificação), acessível só em `127.0.0.1`.
- **Integrações:** gateway da bolsa com timeout, retry e circuit breaker; ingestão de cotações isolada em thread própria.
- **Persistência:** repositórios com SQL parametrizado sobre SQLite.

Detalhes em [docs/arquitetura.md](docs/arquitetura.md).

## Organização das pastas

```
renanblomm/
├── README.md
├── .gitignore
├── .env.example
├── database/
│   ├── schema.sql            # tabelas, constraints e triggers de auditoria imutável
│   └── seed.sql              # dados simulados (senhas só como hash)
├── docs/
│   ├── arquitetura.md
│   ├── FEEDBACK_FASE_1.md
│   ├── requisitos/
│   │   ├── requisitos.md               # visão, atores, RF, RNF, restrições, critérios de aceitação
│   │   ├── regras-de-negocio.md
│   │   └── matriz-rastreabilidade.md   # requisito → caso de uso → diagrama → código → teste
│   ├── uml/
│   │   ├── casos-de-uso/   (casos-de-uso.puml + descricoes-casos-de-uso.md)
│   │   ├── classes/        (classes.puml)
│   │   └── componentes/    (componentes.puml)
│   └── evidencias/         # saída dos testes
├── src/
│   ├── main.py                       # sobe os 4 servidores
│   ├── public/                       # interface web (HTML/CSS/JS)
│   └── sentineltrade/
│       ├── dominio.py                # entidades, estados, exceções, validação de entrada
│       ├── persistencia.py           # banco e repositórios
│       ├── integracoes.py            # gateway da bolsa, cotações, circuit breaker, retry
│       ├── bff.py                    # Backend for Frontend
│       ├── core_api.py               # API interna do núcleo
│       ├── app.py                    # composição (injeção de dependências)
│       ├── servicos/                 # ordens, risco, contas, autenticação, auditoria, notificações
│       └── externos/                 # bolsa e provedor de cotações SIMULADOS
└── tests/
    └── test_sentineltrade.py
```

## Segurança aplicada

- Senhas com scrypt + salt; MFA com validade de 2 min e 3 tentativas; bloqueio após 5 falhas de login; mensagens de erro genéricas.
- Validação no servidor com allowlist (ativo, quantidade, preço, `clientOrderId`, usuário, código MFA) antes de processar, gravar ou enviar.
- SQL sempre parametrizado; nenhum `eval`/`exec`.
- Saída codificada para HTML no navegador; cabeçalhos `Content-Security-Policy`, `X-Content-Type-Options` e `X-Frame-Options`.
- Arquivos estáticos servidos só por allowlist (sem caminhos montados a partir da entrada); limite de 16 KB por requisição.
- Dados de sistemas externos revalidados como não confiáveis.
- Exceções inesperadas viram "Erro interno", sem stack trace para o cliente.
- Nenhum segredo no repositório (`.env` no `.gitignore`).
