# Matriz de Rastreabilidade — SentinelTrade

Relaciona cada requisito ao caso de uso, aos diagramas, à implementação e ao teste automatizado (`tests/test_sentineltrade.py`).
Os casos de uso seguem a numeração de [docs/uml/casos-de-uso/casos-de-uso.puml](../uml/casos-de-uso/casos-de-uso.puml).

| Requisito | Caso de uso | Diagramas | Implementação | Caso de teste |
| :--- | :--- | :--- | :--- | :--- |
| RF01 Autenticação | UC01 Autenticar-se com MFA | Casos de uso, Classes, Componentes | `servicos/autenticacao.py` (AuthService.login) | CT1 `test_ct1_login_exige_senha_e_mfa` |
| RF02 MFA | UC01 Autenticar-se com MFA | Casos de uso, Componentes | `AuthService.verificar_mfa`, `bff.py` (sessao) | CT1 |
| RF03 Carteira e saldo | UC02 Consultar carteira, UC03 Consultar saldo | Casos de uso, Classes | `servicos/contas.py` (Conta.resumo), `persistencia.py` (ContaRepositorio) | CT2 `test_ct2_consulta_carteira` |
| RF04 Cotações | UC04 Consultar cotação | Casos de uso, Componentes | `integracoes.py` (IngestaoCotacoes), `externos/provedor_cotacoes.py` | Demonstração no vídeo |
| RF05 Ordem de compra | UC05 Enviar ordem de compra | Casos de uso, Classes, Componentes | `servicos/ordens.py` (OrderService.enviar) | CT4/CT7 `test_ct4_ct7_...` |
| RF06 Ordem de venda | UC06 Enviar ordem de venda | Casos de uso, Classes | `OrderService.enviar`, `RegraCustodia` | CT6 `test_ct6_rn2_venda_sem_custodia` |
| RF07 Cancelar ordem | UC09 Cancelar ordem | Casos de uso, Classes | `OrderService.cancelar` | CT5 `test_ct5_cancelamento_libera_saldo`, `test_ct5_rn4_...` |
| RF08 Validação pré-trade | UC07 Validar ordem | Casos de uso, Classes (Strategy) | `servicos/risco.py` (ValidadorRisco + RegraRisco) | CT6 `test_ct6_ca3_...`, `test_ct6_rn3_...`, `test_ct6_rn5_...` |
| RF09 Transmitir à bolsa | UC08 Transmitir ordem à corretora | Casos de uso, Componentes | `integracoes.py` (GatewayBolsa), `externos/bolsa_simulada.py` | CT7 `test_ct4_ct7_...` |
| RF10 Ciclo de vida | UC10 Consultar status, UC11 Consultar histórico | Casos de uso, Classes | `dominio.py` (Ordem.transicionar, TRANSICOES) | CT8 `test_ct8_transicao_invalida_bloqueada` |
| RF11 Notificação | UC15 Enviar notificação | Casos de uso, Componentes | `servicos/notificacoes.py` | CT9 `test_ct9_notificacoes` |
| RF12 Auditoria | UC14 Registrar auditoria, UC16 Consultar trilha | Casos de uso, Classes, Componentes | `servicos/auditoria.py`, triggers em `database/schema.sql` | CT10 `test_ct10_ca4_...`, `test_ct10_banco_bloqueia_...` |
| RF13 Limites e mercado | UC13 Gerenciar limites de risco | Casos de uso | `core_api.py` (definir_limite, definir_mercado) | Demonstração no vídeo |
| RF14 Ativos e investidores | UC12 Gerenciar ativos | Casos de uso | Tabelas `ativos` e `usuarios` (interface planejada) | — (próxima fase) |
| RNF01 Segurança | UC01 | Componentes (UMLsec) | scrypt, MFA, `bff.py`, `dominio.validar_entrada_ordem` | CT1, CT14 `test_ct14_validacao_de_entrada` |
| RNF03 Auditabilidade | UC14 | Componentes (UMLsec) | Hash encadeado + triggers | CT10 |
| RNF04 Resiliência | UC08 | Componentes | `integracoes.py` (CircuitBreaker, retry, timeout) | CT13 `test_ct13_...` (2 testes) |
| RNF05 Desempenho | UC07 | — | `latencia_risco_ms` medido em cada ordem | CT12 `test_ct12_rnf1_risco_abaixo_de_50ms` |
| RNF06 Idempotência | UC05, UC06 | Classes, Banco | `OrderService.enviar` + `UNIQUE` no banco | CT11 `test_ct11_ca2_idempotencia` |
| RNF08 Privacidade | UC02, UC09 | Componentes | Usuário vem da sessão no BFF | Demonstração (403 para perfil errado) |
