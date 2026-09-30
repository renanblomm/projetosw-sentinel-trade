# Matriz de Rastreabilidade — SentinelTrade

Esta matriz apresenta a relação entre os requisitos funcionais do SentinelTrade, os casos de uso, os componentes previstos para implementação e os casos de teste correspondentes.

| ID Requisito | Descrição do Requisito | Caso de Uso Relacionado | Componente / Implementação | Caso de Teste |
| :--- | :--- | :--- | :--- | :--- |
| RF1 | Autenticação com MFA | UC1 - Autenticar com MFA | AuthService / MFAProvider | CT1 - Login com MFA válido e inválido |
| RF2 | Consulta de Carteira e Limites | UC2 - Consultar Carteira e Limites | AccountService | CT2 - Consulta de saldo, carteira e limites |
| RF3 | Receção de Cotações | UC3 - Acompanhar Cotações | MarketDataIngestionWorker | CT3 - Receção de cotações simuladas |
| RF4 | Envio de Ordens | UC4 - Enviar Ordem de Compra/Venda | OrderService | CT4 - Envio de ordem de compra e venda |
| RF5 | Cancelamento de Ordens | UC5 - Cancelar Ordem | OrderCancellationHandler | CT5 - Cancelamento de ordem pendente |
| RF6 | Validação Prévia de Risco | UC4 - Enviar Ordem de Compra/Venda | RiskEngine / PreTradeValidator | CT6 - Rejeição por saldo, custódia ou limite insuficiente |
| RF7 | Encaminhamento de Ordens | UC6 - Processar Ordem | ExchangeGatewayClient | CT7 - Envio e resposta da Bolsa/Corretora simulada |
| RF8 | Acompanhamento do Ciclo de Vida da Ordem | UC7 - Consultar Histórico de Ordens | OrderLifecycleManager | CT8 - Validação das transições de estado |
| RF9 | Notificação do Investidor | UC8 - Receber Notificação | NotificationService | CT9 - Notificação de execução, rejeição ou cancelamento |
| RF10 | Registo Imutável de Auditoria | UC9 - Auditar Operações | AuditLogger | CT10 - Validação da integridade do log |