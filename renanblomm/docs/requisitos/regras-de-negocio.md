# Regras de Negócio — SentinelTrade

| ID | Regra | Onde é aplicada no código |
| :--- | :--- | :--- |
| RN01 | **Bloqueio de saldo na compra.** Ao aprovar uma compra, o valor estimado (preço × quantidade + taxa de 0,1%) é bloqueado. Na ordem a mercado, o preço estimado é a última cotação + 2% de margem. | `servicos/risco.py` (RegraSaldo), `servicos/contas.py` (Conta.reservar) |
| RN02 | **Custódia na venda.** A venda só é aceita se o investidor tiver a quantidade **livre** (não bloqueada por outra ordem) do ativo. A quantidade vendida fica bloqueada até a execução ou o cancelamento. | `RegraCustodia`, `Conta.reservar` |
| RN03 | **Mercado aberto.** Ordens só são aceitas e enviadas com o mercado simulado no estado ABERTO. Se não for possível consultar a bolsa, o mercado é tratado como fechado (falha segura). | `RegraMercadoAberto`, `OrderService.enviar` |
| RN04 | **Estados finais.** Ordens EXECUTADA, REJEITADA ou CANCELADA não podem ser canceladas nem voltar a um estado anterior. | `dominio.TRANSICOES`, `OrderService.cancelar` |
| RN05 | **Limite diário.** A ordem é rejeitada se o valor já operado no dia **mais o valor da nova ordem** ultrapassar o limite do investidor. | `RegraLimiteDiario` |
| RN06 | **Liberação.** Ao cancelar ou rejeitar uma ordem já reservada, o saldo ou os ativos bloqueados são devolvidos integralmente e o valor operado no dia é estornado. | `Conta.liberar` |
| RN07 | **Idempotência.** O mesmo `clientOrderId` do mesmo investidor nunca gera duas ordens: o reenvio devolve o estado da ordem original. | `OrderService.enviar`, `UNIQUE(usuario, client_order_id)` |
| RN08 | **Auditoria obrigatória.** Toda mudança de estado de ordem gera registro de auditoria. | `OrderService._transicionar` |
| RN09 | **Acesso por perfil.** Funções do Analista de Risco e do Auditor são restritas a esses perfis. | `bff.py` (sessao com perfis permitidos) |
| RN10 | **Indisponibilidade da bolsa.** Uma falha da bolsa não apaga a ordem nem altera a carteira indevidamente: a ordem fica REJEITADA com o motivo e a reserva é devolvida. | `OrderService.enviar`, `aplicar_resposta_bolsa` |
| RN11 | **Privacidade.** O investidor só consulta as próprias informações e ordens. | `bff.py` (usuário vem da sessão), `OrderService.cancelar` |
