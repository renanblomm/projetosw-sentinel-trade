# Arquitetura — SentinelTrade

## Visão geral

O sistema é dividido em **quatro servidores independentes**, cada um na sua porta, que se comunicam por HTTP/JSON:

| Componente | Porta | Papel |
| :--- | :--- | :--- |
| BFF + interface web | 3000 | Única porta acessada pelo navegador |
| Core (serviços de domínio) | 4000 | Regras de negócio e persistência; escuta só em 127.0.0.1 |
| Bolsa simulada | 4001 | Sistema externo: matching de ordens, estado do mercado |
| Provedor de cotações | 4002 | Sistema externo: preços simulados a cada segundo |

Diagrama de componentes: [uml/componentes/componentes.puml](uml/componentes/componentes.puml).

## Camadas

1. **Interface** (`src/public`): HTML/JS que conversa **apenas** com o BFF.
2. **BFF** (`bff.py`): sessão, perfil, agregação e proteção dos serviços internos.
3. **Serviços / regras de negócio** (`servicos/`): `OrderService`, `ValidadorRisco`, `AuthService`, `AuditLogger`, `NotificationService`, `Conta`.
4. **Domínio** (`dominio.py`): entidade `Ordem` com estado encapsulado e máquina de estados; validação de entradas.
5. **Persistência** (`persistencia.py`): `BancoDados` (transações com lock) e repositórios (classe abstrata `Repositorio`).
6. **Integrações** (`integracoes.py`): `GatewayBolsa` e `IngestaoCotacoes`, com `CircuitBreaker` e `retry`.

## Por que um BFF?

O navegador não deve conhecer nem acessar os serviços internos. O BFF:

- **Protege:** toda rota (menos login e MFA) exige sessão, e a sessão só nasce depois do MFA (CA1).
- **Autoriza:** confere o perfil a cada requisição (Investidor, Analista de Risco, Auditor) e usa o usuário da **sessão**, nunca um usuário enviado pelo cliente.
- **Agrega:** `/api/painel` faz, em paralelo, 5 chamadas ao core (conta, cotações, ordens, notificações, mercado) e devolve uma resposta pronta para a tela, específica para cada perfil.
- **Isola:** se os serviços internos mudarem, só o BFF precisa ser ajustado; a interface não muda.

## Fluxo de uma ordem

```
Tela ─► BFF (sessão + perfil) ─► Core
  1. valida entrada (allowlist)                         → 400 se inválida
  2. clientOrderId já existe?                           → devolve a ordem original (idempotência)
  3. cria ordem CRIADA + auditoria
  4. consulta mercado na bolsa (timeout/retry/breaker)
  5. [transação] ValidadorRisco: mercado, cotação, saldo/custódia, limite
        reprovada → REJEITADA + auditoria + notificação (não vai à bolsa)
        aprovada  → bloqueia saldo/ativo → VALIDADA + auditoria
  6. envia à bolsa
        EXECUTADA → liquida carteira
        ABERTA    → aguarda; a bolsa chama /bolsa/eventos quando executar
        falha     → REJEITADA e reserva devolvida (carteira nunca fica inconsistente)
```

## Padrões de projeto

- **Strategy / Chain of Responsibility:** cada regra de risco é uma subclasse de `RegraRisco`; o `ValidadorRisco` as executa em sequência. Para criar uma regra nova, basta outra subclasse.
- **Repository:** acesso a dados isolado atrás de `Repositorio`.
- **Circuit Breaker e Retry:** resiliência nas integrações externas.
- **State machine:** `TRANSICOES` define quais mudanças de estado da ordem são permitidas.
- **Injeção de dependências:** `app.py` monta os objetos; os testes trocam a bolsa e as cotações por versões falsas.
