# Engenharia de Requisitos — SentinelTrade

> Versão 2.0 — revisada a partir da devolutiva da Fase 1 (requisitos em tabela, critérios de aceitação por requisito, atores e regras de negócio documentados).

## 1. Visão e objetivo

O **SentinelTrade** é uma plataforma **simulada** de negociação de ativos financeiros (ações, ETFs e fundos imobiliários) da corretora fictícia Orion Capital. O investidor autenticado com MFA acompanha cotações e carteira e envia ordens de compra e venda. Cada ordem passa obrigatoriamente por uma **validação de risco pré-trade** (saldo, custódia, limite diário e mercado aberto) antes de ser transmitida a uma **bolsa simulada**.

O sistema garante que toda ordem seja **rastreável**, que **não seja executada em duplicidade** e que todos os eventos relevantes fiquem numa **trilha de auditoria imutável**.

**Escopo — dentro:** autenticação com MFA simulado; consulta de carteira e cotações; ordens a mercado e limitadas; cancelamento; validação de risco; ciclo de vida da ordem; notificações; auditoria; parametrização de limites e do estado do mercado pelo Analista de Risco.

**Escopo — fora (nesta fase):** dinheiro real ou conexão com a B3 (RT1); execução parcial de ordens; cadastro de investidores e ativos pela interface (a estrutura já existe no banco e está planejada para a próxima fase).

## 2. Atores

| Ator | Tipo | Responsabilidade |
| :--- | :--- | :--- |
| Investidor | Humano (primário) | Consulta cotações, carteira, saldo e histórico; envia e cancela ordens. |
| Analista de Risco | Humano (primário) | Ajusta limites diários dos investidores, abre/fecha o mercado simulado, acompanha o fluxo de ordens e a auditoria. |
| Auditor | Humano (primário) | Consulta, somente em leitura, a trilha de auditoria e a verificação de integridade. |
| Administrador | Humano (primário) | Gerencia usuários, ativos e parâmetros do sistema (planejado para a próxima fase). |
| Bolsa/Corretora Simulada | Sistema externo | Recebe ordens válidas e devolve execução, abertura, rejeição ou cancelamento. |
| Provedor de Cotações | Sistema externo | Fornece cotações simuladas atualizadas a cada segundo. |
| Serviço de Notificação | Serviço (secundário) | Informa o investidor sobre execução, rejeição e cancelamento de ordens. |
| Serviço de Auditoria | Serviço (secundário) | Mantém o registro imutável de ações, decisões e mudanças de estado. |

## 3. Requisitos funcionais

| ID | Requisito | Critério de aceitação | Prioridade | Status |
| :--- | :--- | :--- | :--- | :--- |
| RF01 | O sistema deve autenticar usuários por usuário e senha. | Credencial válida avança para o MFA; credencial inválida é recusada com mensagem genérica (não revela se errou o usuário ou a senha); 5 falhas seguidas bloqueiam o usuário por 1 minuto. | Alta | Implementado |
| RF02 | O sistema deve exigir um segundo fator de autenticação (MFA simulado). | O acesso só é liberado após informar o código de 6 dígitos correto em até 2 minutos; 3 códigos errados invalidam o desafio. | Alta | Implementado |
| RF03 | O investidor deve consultar saldo, carteira e posição por ativo. | A tela mostra saldo disponível, saldo bloqueado, limite diário restante e, por ativo, quantidade total, bloqueada e livre. | Alta | Implementado |
| RF04 | O investidor deve consultar as cotações dos ativos disponíveis. | A tela mostra preço, horário da cotação e variação do dia, atualizados a cada ~2 segundos. | Alta | Implementado |
| RF05 | O investidor deve enviar ordem de compra (a mercado ou limitada). | A ordem só é aceita se houver saldo disponível para preço × quantidade + taxas e limite diário disponível. | Alta | Implementado |
| RF06 | O investidor deve enviar ordem de venda (a mercado ou limitada). | A ordem só é aceita se houver quantidade livre do ativo na carteira. | Alta | Implementado |
| RF07 | O investidor deve cancelar uma ordem ainda não executada. | Só ordens no estado ABERTA podem ser canceladas; o saldo/ativo bloqueado é devolvido; ordens EXECUTADA, REJEITADA ou CANCELADA retornam erro. | Alta | Implementado |
| RF08 | O sistema deve validar toda ordem antes de transmiti-la à bolsa (risco pré-trade). | Dados inválidos, mercado fechado, saldo ou custódia insuficientes ou limite excedido rejeitam a ordem localmente, sem chamar a bolsa. | Alta | Implementado |
| RF09 | O sistema deve transmitir as ordens aprovadas à bolsa simulada. | A ordem aprovada é enviada e o retorno da bolsa (EXECUTADA, ABERTA ou REJEITADA) é refletido na ordem e na carteira. | Alta | Implementado |
| RF10 | O sistema deve registrar e exibir o ciclo de vida e o histórico das ordens. | Cada ordem guarda o histórico de estados com data/hora; o investidor vê o estado atualizado de cada ordem. Estados: CRIADA, VALIDADA, ABERTA, EXECUTADA, REJEITADA, CANCELADA. | Alta | Implementado |
| RF11 | O sistema deve notificar o investidor sobre eventos críticos. | Uma notificação é gerada em toda execução, rejeição (inclusive por falha da bolsa) e cancelamento. | Média | Implementado |
| RF12 | O sistema deve registrar eventos de auditoria com integridade verificável. | Login, MFA, cada mudança de estado de ordem, reenvio duplicado e alteração de parâmetros geram registro com timestamp UTC em ms, usuário responsável e hash encadeado. | Alta | Implementado |
| RF13 | O Analista de Risco deve gerenciar limites e o estado do mercado. | O analista altera o limite diário de um investidor e abre/fecha o mercado; cada alteração fica na auditoria. | Média | Implementado |
| RF14 | O Administrador deve gerenciar investidores e ativos. | Inclusões e alterações ficam registradas e disponíveis para consulta. | Média | Planejado (tabelas já existem) |

## 4. Requisitos não funcionais

| ID | Categoria | Requisito | Critério de aceitação | Status |
| :--- | :--- | :--- | :--- | :--- |
| RNF01 | Segurança | Senhas com hash, MFA, controle de acesso por perfil e validação de entradas no servidor. | Senhas só como scrypt + salt; nenhuma rota de negócio responde sem sessão pós-MFA (401); perfil sem permissão recebe 403; entradas fora da allowlist recebem 400. | Implementado |
| RNF02 | Integridade | Toda ordem deve ter investidor, ativo, tipo, quantidade e preço válidos. | Ativo só da allowlist (`^[A-Z0-9]{4,6}$` e cadastrado); quantidade inteira de 1 a 1.000.000; preço limite de 0,01 a 1.000.000; o banco reforça com CHECK e FOREIGN KEY. | Implementado |
| RNF03 | Auditabilidade | Eventos críticos com registro rastreável e protegido contra alteração. | Hash SHA-256 encadeado detecta adulteração; triggers no banco impedem UPDATE e DELETE na tabela de auditoria. | Implementado |
| RNF04 | Disponibilidade e resiliência | Falha em serviço externo não pode corromper ordens nem posições. | Timeout (1,5 s), retry com backoff (3 tentativas) e circuit breaker (abre após 3 falhas). Se a bolsa cair, a ordem vira REJEITADA e o saldo é devolvido integralmente. | Implementado |
| RNF05 | Desempenho | A validação de risco pré-trade deve ser rápida. | Validação concluída em menos de 50 ms no ambiente simulado (medida e exibida em cada ordem). | Implementado |
| RNF06 | Confiabilidade | Impedir duplicidade de ordens em reenvios ou falhas de comunicação. | Mesmo `clientOrderId` do mesmo investidor devolve a ordem original sem reprocessar; reforçado por `UNIQUE` no banco. | Implementado |
| RNF07 | Manutenibilidade | Código, documentação, banco e diagramas organizados e versionados. | Camadas separadas (interface, BFF, serviços, domínio, persistência, integrações); testes automatizados das regras críticas. | Implementado |
| RNF08 | Privacidade | Dados do investidor acessíveis somente a usuários autorizados. | O investidor só vê e cancela as próprias ordens (o BFF usa o usuário da sessão, nunca o informado pelo cliente). | Implementado |
| RNF09 | Confidencialidade em trânsito | Comunicação cifrada com TLS 1.2+. | Em produção, TLS terminado num proxy reverso à frente do BFF. Na demonstração local, os serviços escutam só em 127.0.0.1. | Planejado |
| RNF10 | Escalabilidade | Serviços independentes podem escalar separadamente. | Bolsa, provedor de cotações, core e BFF rodam em portas e servidores separados, comunicando-se por HTTP. | Implementado (demonstrativo) |

## 5. Restrições técnicas

| ID | Restrição |
| :--- | :--- |
| RT1 | O sistema opera **exclusivamente com dados e operações simuladas**: sem dinheiro real e sem conexão com a B3. |
| RT2 | A ingestão de cotações é isolada do motor de ordens (thread e circuit breaker próprios); se o provedor cair, as ordens usam a última cotação conhecida. |
| RT3 | É proibido versionar senhas, tokens, chaves ou arquivos `.env` reais. O `.env.example` contém só nomes de variáveis. |
| RT4 | Implementação em **Python 3.10+** usando apenas a biblioteca padrão, com banco relacional **SQLite**. |

## 6. Regras de negócio

Ver [regras-de-negocio.md](regras-de-negocio.md).
