# Roteiro do vídeo — SentinelTrade (Parte 2)

**Duração-alvo:** cerca de 8 min (mínimo 5, máximo 10). Todos aparecem de rosto (câmera ligada durante toda a gravação, ou pelo menos enquanto cada um fala).

| # | Bloco | Quem | Tempo |
| :--- | :--- | :--- | :--- |
| 1 | Abertura e o projeto | Jonatas | 0:00–0:50 |
| 2 | Requisitos e diagramas | Leandro | 0:50–2:20 |
| 3 | Arquitetura e BFF | Renan | 2:20–3:50 |
| 4 | Código | Jonatas | 3:50–5:50 |
| 5 | Demonstração | Leandro | 5:50–7:50 |
| 6 | Testes e encerramento | Renan | 7:50–8:20 |

**Antes de gravar:**

1. Rodar `python src/main.py` e deixar o terminal visível (o código MFA aparece nele).
2. Abrir http://localhost:3000.
3. Deixar abertos no VS Code: `docs/requisitos/requisitos.md`, os 3 diagramas, `src/sentineltrade/servicos/risco.py`, `servicos/ordens.py`, `dominio.py`, `servicos/auditoria.py` e `bff.py`.
4. Para mostrar os diagramas como imagem: abra cada `.puml` no VS Code com a extensão PlantUML (Alt+D) ou cole o conteúdo em plantuml.com.

---

## 1. Abertura e o projeto — Jonatas (≈50 s)

*Tela: README no GitHub.*

> "Oi, professor. Somos o grupo do SentinelTrade: eu sou o Jonatas, aqui estão o Leandro e o Renan.
> O SentinelTrade é uma plataforma simulada de negociação de ações, ETFs e fundos imobiliários. O investidor entra com senha e um segundo fator, acompanha a carteira e as cotações e envia ordens de compra e venda.
> A ideia central é que nenhuma ordem chegue na bolsa sem antes passar por uma validação de risco: tem saldo? tem o ativo? o mercado está aberto? estourou o limite do dia? Além disso, uma ordem nunca pode ser processada duas vezes e tudo fica registrado numa auditoria que não dá para adulterar.
> Implementamos em Python, com banco SQLite, e tudo é simulado: não tem dinheiro real nem conexão com a B3.
> O Leandro vai começar pelos requisitos."

## 2. Requisitos e diagramas — Leandro (≈1 min 30 s)

*Tela: `docs/requisitos/requisitos.md`, depois o diagrama de casos de uso.*

> "A partir da devolutiva da Fase 1, transformamos os requisitos em tabelas, e agora cada requisito tem o seu critério de aceitação, prioridade e status.
> São 14 requisitos funcionais: login, MFA, consulta de carteira e cotações, ordem de compra, ordem de venda, cancelamento, validação pré-trade, envio para a bolsa, ciclo de vida, notificação, auditoria e a gestão de limites pelo analista de risco. O cadastro de ativos pelo administrador ficou marcado como planejado.
> Nos não funcionais, destaco segurança, auditabilidade, resiliência quando a bolsa cai e idempotência, ou seja, não duplicar ordem.
> *(mostrar `regras-de-negocio.md`)* As regras de negócio agora têm um arquivo próprio, e cada uma indica em que parte do código ela é aplicada.
> *(mostrar o diagrama de casos de uso)* No diagrama de casos de uso estão os atores que o professor pediu: Investidor, Analista de Risco, Auditor, Administrador, Bolsa, Provedor de Cotações e os serviços de Notificação e Auditoria. Usamos include onde a ação é obrigatória: enviar ordem inclui validar ordem, que inclui verificar saldo ou posição, e também inclui registrar auditoria. Colocamos estereótipos de segurança, como secureAuthentication, integrity e audit.
> *(mostrar `matriz-rastreabilidade.md`)* E a matriz liga cada requisito ao caso de uso, ao diagrama, ao arquivo do código e ao teste que comprova. Agora o Renan explica a arquitetura."

## 3. Arquitetura e BFF — Renan (≈1 min 30 s)

*Tela: diagrama de componentes, depois `bff.py`.*

> "O sistema roda em quatro servidores separados, cada um na sua porta. Dois são os sistemas externos simulados: a bolsa e o provedor de cotações. Os outros dois são nossos: o core, com as regras de negócio, e o BFF.
> O BFF, Backend for Frontend, é a única porta que o navegador enxerga. Ele faz três coisas. Primeiro, segurança: nenhuma rota funciona sem uma sessão, e a sessão só é criada depois do MFA; ele também confere o perfil em cada requisição. Segundo, agregação: *(mostrar a função `painel`)* quando a tela pede o painel, o BFF faz cinco chamadas ao core em paralelo e devolve tudo pronto. Terceiro, isolamento: o core só escuta localmente, então o navegador nunca fala direto com ele.
> Na integração com a bolsa usamos timeout, retentativa e circuit breaker. Se a bolsa cair, a ordem é rejeitada e o saldo bloqueado volta. A carteira nunca fica inconsistente.
> O Jonatas mostra o código por dentro."

## 4. Código — Jonatas (≈2 min)

*Tela: `dominio.py` → `risco.py` → `ordens.py` → `auditoria.py` / `schema.sql`. Mostrar o diagrama de classes no início.*

> "O diagrama de classes mostra as camadas: domínio, serviços, persistência e integrações.
> *(dominio.py)* A classe `Ordem` tem os atributos privados, e o estado só muda pelo método `transicionar`, que consulta esta tabela de transições. Uma ordem executada, por exemplo, não volta para aberta. Aqui também fica a validação de entrada: o ativo precisa estar numa lista permitida e a quantidade tem que ser um inteiro dentro de uma faixa. Qualquer coisa fora disso é recusada antes de chegar no banco.
> *(risco.py)* No risco usamos o padrão Strategy: `RegraRisco` é uma classe abstrata, e cada regra (mercado aberto, saldo, custódia, limite diário) é uma subclasse. O validador percorre as regras e para na primeira reprovação.
> *(ordens.py, método `enviar`)* Aqui fica a idempotência: se o mesmo `clientOrderId` chegar de novo, devolvemos a ordem original. E isso é garantido também no banco, por uma constraint UNIQUE. A validação de risco e o bloqueio do saldo acontecem na mesma transação, então duas ordens simultâneas não conseguem gastar o mesmo dinheiro.
> *(auditoria.py e schema.sql)* Na auditoria, cada registro guarda o hash do anterior, como uma corrente. Se alguém alterar uma linha, a verificação aponta onde quebrou. E colocamos triggers no banco que bloqueiam UPDATE e DELETE nessa tabela. Todas as consultas SQL são parametrizadas.
> Agora o Leandro mostra funcionando."

## 5. Demonstração — Leandro (≈2 min)

*Tela: navegador + terminal.*

> "Vou entrar como a investidora Ana. *(usuário `ana`, senha `Sentinel@2026`)* A senha está certa, agora ele pede o código. *(mostrar o terminal)* O código aparece aqui, simulando um SMS. *(digitar)* Entrei.
> Aqui está o saldo, o limite do dia, as cotações mudando a cada segundo e a carteira.
> **Compra a mercado:** 10 PETR4. *(enviar)* Executada; a validação de risco levou menos de 1 milissegundo, a carteira foi atualizada e chegou a notificação.
> **Idempotência:** vou clicar em 'Reenviar mesma ordem', com o mesmo ClientOrderId. *(clicar)* O sistema descartou o pedido e devolveu o estado da ordem original. Não comprou de novo.
> **Saldo insuficiente:** 5000 VALE3. *(enviar)* Rejeitada no risco; nem chegou na bolsa.
> **Venda sem custódia:** vender 999 VALE3, sendo que ela só tem 100. Rejeitada.
> **Ordem limitada e cancelamento:** compra de 10 PETR4 com limite bem abaixo do preço, tipo 30 reais. *(enviar)* Ficou ABERTA e o saldo bloqueado subiu. *(clicar em Cancelar)* Cancelada, e o saldo voltou.
> Agora vou sair e entrar como o Carlos, analista de risco. *(login + MFA)* Ele vê o fluxo de ordens de todos, pode alterar limites e abrir ou fechar o mercado. *(fechar o mercado)* Com o mercado fechado, uma ordem seria rejeitada. *(reabrir)*
> E aqui embaixo a trilha de auditoria: cada evento com o horário em UTC e milissegundos, o usuário e o hash, e o selo mostrando que a cadeia está íntegra."

## 6. Testes e encerramento — Renan (≈30 s)

*Tela: terminal rodando `python -m unittest discover -s tests -v`.*

> "Para fechar, os testes automatizados: são 18 testes cobrindo as regras críticas, como login com MFA, saldo, custódia, limite, idempotência, transições de estado, cancelamento, falha da bolsa e integridade da auditoria. *(rodar)* Todos passando.
> Os requisitos, os três diagramas, o banco e o código estão no repositório, ligados pela matriz de rastreabilidade. Obrigado, professor."
