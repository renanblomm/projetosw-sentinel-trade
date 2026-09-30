## 1. Visão Geral e Objetivo
O SentinelTrade é uma plataforma distribuída, segura e tolerante a falhas voltada à negociação de ativos financeiros (ações, ETFs e fundos imobiliários) para a corretora Orion Capital. 

O objetivo do sistema é consolidar a gestão de carteiras, a receção de cotações em tempo quase real, a validação prévia de risco e o encaminhamento de ordens para uma bolsa simulada com rastreabilidade total, auditoria imutável e proteção contra duplicidade de operações, eliminando as vulnerabilidades de sistemas desintegrados e garantindo conformidade regulatória.

## 2. Atores -
Investidor: Utilizador autorizado que acompanha cotações, faz a gestão da sua carteira, emite ordens de compra/venda e solicita cancelamentos.

Operador de Risco: Profissional responsável por parametrizar limites operacionais, monitorizar o fluxo de ordens e supervisionar logs do sistema.

Auditor / Regulador: Utilizador com permissão de leitura sobre a trilha imutável de eventos e logs operacionais para efeitos de conformidade.

Provedor de Cotações Externo (Sistema Externo): Serviço externo que envia pacotes e fluxos de cotações de ativos em tempo quase real.

Bolsa/Corretora Simulada (Sistema Externo): Gateway simulador de mercado que recebe ordens, processa o matching e devolve o estado de execução ou rejeição.

## 3. Requisitos Funcionais - 
RF1 - Autenticação com MFA: O sistema deve autenticar utilizadores exigindo credenciais válidas e um segundo fator de autenticação (MFA).
RF2 - Consulta de Carteira e Limites: O sistema deve permitir ao investidor consultar o seu saldo financeiro, ativos sob custódia e limites operacionais disponíveis.
RF3 - Receção de Cotações: O sistema deve consumir e atualizar cotações de ativos em tempo quase real a partir de um provedor externo.
RF4 - Envio de Ordens: O sistema deve permitir que o investidor submeta ordens de compra e venda a mercado ou limitadas.
RF5 - Cancelamento de Ordens: O sistema deve permitir a solicitação de cancelamento de ordens pendentes de execução.
RF6 - Validação Prévia de Risco (Pre-Trade): O sistema deve validar de forma atómica e obrigatória saldo, custódia e limites operacionais antes de despachar a ordem para a bolsa.
RF7 - Encaminhamento de Ordens: O sistema deve transmitir as ordens aprovadas no risco diretamente para a Bolsa/Corretora Simulada.
RF8 - Acompanhamento do Ciclo de Vida da Ordem: O sistema deve manter e apresentar o histórico e o estado em tempo real das ordens (Criada, Validada, Rejeitada, Aberta, Executada, Cancelada).
RF9 - Notificação do Investidor: O sistema deve emitir notificações ao investidor sobre qualquer alteração de estado da ordem (execução, cancelamento ou rejeição).
RF10 - Registo Imutável de Auditoria: O sistema deve registar eventos críticos de ordens e autenticação numa trilha de log com integridade verificável.

## 4. Requisitos Não Funcionais -
RNF1 - Baixa Latência: O processo de validação pré-trade de risco e despacho não deve exceder 50 ms sob carga nominal de operações.
RNF2 - Tolerância a Falhas: O sistema deve implementar padrões de resiliência (circuit breaker e retry seguro) na comunicação com serviços externos.
RNF3 - Idempotência e Prevenção de Duplicidade: O processamento de ordens deve ser estritamente idempotente (via identificador único ClientOrderId) para impedir envio duplo acidental.
RNF4 - Segurança e Criptografia: Comunicação em trânsito com TLS 1.3 e dados sensíveis em repouso cifrados via norma AES-256.
RNF5 - Escalabilidade Horizontal: A arquitetura distribuída deve permitir que serviços independentes (motor de risco, encaminhador e ingestão de dados) escalem horizontalmente.
RNF6 - Alta Disponibilidade: O sistema deve operar com disponibilidade mínima de 99,9% durante os horários de negociação.

## 5. Regras de Negócio -
RN1 - Bloqueio de Saldo na Compra: Ao submeter uma ordem de compra, o valor financeiro total estimado (preço × quantidade + taxas) deve ser cativado imediatamente.
RN2 - Validação de Custódia na Venda: Uma ordem de venda só pode ser aceite se o investidor possuir a quantidade líquida do ativo livre em carteira.
RN3 - Horário de Negociação: Ordens de negociação só são aceites e despachadas caso o mercado simulado esteja com estado operacional "Aberto".
RN4 - Cancelamento Condicional: Ordens que já atingiram o estado final ("Totalmente Executada" ou "Rejeitada") não admitem cancelamento.
RN5 - Limite Diário Operacional: Nenhuma ordem poderá ser aceite caso o valor total operado no dia ultrapasse o teto financeiro parametrizado para o investidor.

## 6. Restrições Técnicas -
RT1: O sistema operará com ativos, contas e cotações exclusivamente simuladas (sem dinheiro real ou ligação direta à B3).
RT2: É obrigatório o isolamento entre o serviço de ingestão de cotações e o motor de execução de ordens.
RT3: É expressamente proibido o armazenamento de credenciais, palavras-passe ou segredos no repositório Git.

## 7. Critérios de Aceitação -
CA1 (Autenticação MFA): Nenhum utilizador pode aceder a ecrãs ou rotas de negociação sem ter validado o segundo fator com sucesso.
CA2 (Prevenção de Duplicidade): Se um pedido com o mesmo ID for enviado duas vezes consecutivas, o segundo deve ser descartado devolvendo o estado do primeiro.
CA3 (Saldo Insuficiente): Se a conta não tiver fundos livres suficientes para cobrir compra + taxas, a ordem deve ser rejeitada localmente no risco pré-trade.
CA4 (Auditoria): Toda a alteração de estado da ordem deve gerar log com carimbo de data/hora em milissegundos UTC e identificação do utilizador responsável.
