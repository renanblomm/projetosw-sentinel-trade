# Descrição textual dos casos de uso críticos

## UC05 — Enviar ordem de compra

| Campo | Conteúdo |
| :--- | :--- |
| Ator principal | Investidor |
| Objetivo | Comprar uma quantidade de um ativo a mercado ou a um preço limite. |
| Pré-condições | Investidor autenticado com MFA; mercado simulado ABERTO. |
| Fluxo principal | 1. O investidor escolhe ativo, tipo (MERCADO/LIMITADA), quantidade e, se limitada, o preço. 2. A tela gera um `clientOrderId` único. 3. O BFF confere a sessão e o perfil e repassa ao core. 4. O sistema valida as entradas (allowlist). 5. O sistema verifica se o `clientOrderId` já existe (idempotência). 6. A ordem é criada (CRIADA) e auditada. 7. O risco pré-trade valida mercado, cotação, saldo e limite diário (UC07). 8. O valor estimado é bloqueado e a ordem fica VALIDADA. 9. A ordem é transmitida à bolsa (UC08). 10. A bolsa responde EXECUTADA (saldo debitado, ativo creditado) ou ABERTA (aguarda o preço). 11. O investidor é notificado e a tela mostra o novo estado. |
| Fluxos alternativos | **A1 Saldo insuficiente:** em 7, a ordem fica REJEITADA com o motivo e nada é enviado à bolsa. **A2 Limite excedido:** igual a A1, com motivo RN05. **A3 Ativo indisponível/inválido:** em 4, retorna erro 400 sem criar a ordem. **A4 Mercado fechado:** em 7, REJEITADA (RN03). **A5 Falha de comunicação com a bolsa:** em 9, após timeout e retries (ou circuit breaker aberto), a ordem fica REJEITADA e o saldo bloqueado é devolvido. **A6 Reenvio:** em 5, se o `clientOrderId` já existir, devolve a ordem original sem reprocessar. |
| Pós-condições | Ordem em EXECUTADA, ABERTA ou REJEITADA; saldo e custódia consistentes; todas as transições registradas na auditoria. |
| Regras de negócio | RN01, RN03, RN05, RN06, RN07, RN08, RN10 |
| Requisitos relacionados | RF05, RF08, RF09, RF10, RF11, RF12, RNF02, RNF04, RNF05, RNF06 |

## UC06 — Enviar ordem de venda

| Campo | Conteúdo |
| :--- | :--- |
| Ator principal | Investidor |
| Objetivo | Vender uma quantidade de um ativo que possui em carteira. |
| Pré-condições | Investidor autenticado com MFA; mercado ABERTO; ativo em custódia. |
| Fluxo principal | 1 a 6 iguais ao UC05. 7. O risco pré-trade valida mercado, cotação, **quantidade livre em custódia** e limite diário. 8. A quantidade vendida é bloqueada e a ordem fica VALIDADA. 9. Transmissão à bolsa. 10. Na execução, a quantidade sai da carteira e o valor menos a taxa entra no saldo. 11. Notificação. |
| Fluxos alternativos | **A1 Custódia insuficiente:** REJEITADA (RN02), sem enviar à bolsa. **A2 Limite excedido**, **A3 Ativo inválido**, **A4 Mercado fechado**, **A5 Falha da bolsa** (a quantidade bloqueada é devolvida) e **A6 Reenvio**: iguais ao UC05. |
| Pós-condições | Ordem em EXECUTADA, ABERTA ou REJEITADA; custódia consistente (bloqueada ≤ quantidade); auditoria registrada. |
| Regras de negócio | RN02, RN03, RN05, RN06, RN07, RN08, RN10 |
| Requisitos relacionados | RF06, RF08, RF09, RF10, RF11, RF12, RNF02, RNF04, RNF06 |

## UC09 — Cancelar ordem

| Campo | Conteúdo |
| :--- | :--- |
| Ator principal | Investidor |
| Objetivo | Desistir de uma ordem limitada que ainda não foi executada. |
| Pré-condições | Investidor autenticado; a ordem pertence a ele e está ABERTA. |
| Fluxo principal | 1. O investidor clica em "Cancelar" na ordem. 2. O BFF confere sessão e perfil. 3. O sistema confirma que a ordem é do investidor e está ABERTA. 4. O pedido é auditado e enviado à bolsa. 5. A bolsa confirma o cancelamento. 6. O saldo ou ativo bloqueado é devolvido (RN06). 7. A ordem vai para CANCELADA, é auditada e o investidor é notificado. |
| Fluxos alternativos | **A1 Ordem em estado final** (EXECUTADA, REJEITADA ou CANCELADA): erro 409 (RN04). **A2 Ordem de outro investidor ou inexistente:** erro 404 (RN11). **A3 Executada durante o pedido:** a bolsa responde EXECUTADA; o sistema aplica a execução e informa que não foi possível cancelar. **A4 Falha da bolsa:** erro informado; a ordem continua ABERTA, sem alteração na carteira. |
| Pós-condições | Ordem CANCELADA com reserva devolvida, ou inalterada em caso de erro; auditoria registrada. |
| Regras de negócio | RN04, RN06, RN08, RN11 |
| Requisitos relacionados | RF07, RF10, RF11, RF12, RNF08 |
