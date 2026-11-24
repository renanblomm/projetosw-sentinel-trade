-- SentinelTrade - dados iniciais SIMULADOS (RT1)
-- Senhas guardadas apenas como hash scrypt + salt. Senha de demonstração no README (dado fictício).

INSERT INTO usuarios (usuario, nome, perfil, salt, hash_senha) VALUES ('ana', 'Ana Souza', 'INVESTIDOR', 'd3669423eec841db33b066f47f706891', '2514a9f0b1f8ac1cb610a6c07e0989d95ac9ee0956af60e5844372c77b021150');
INSERT INTO usuarios (usuario, nome, perfil, salt, hash_senha) VALUES ('bruno', 'Bruno Lima', 'INVESTIDOR', '0ce9494f60bb375fccd1e41c2ce6eb3f', 'c6d7610834c34e6deaa1375698096f6f5fa9d55160b06d08abfa20f79529e468');
INSERT INTO usuarios (usuario, nome, perfil, salt, hash_senha) VALUES ('carlos', 'Carlos Mendes', 'ANALISTA_RISCO', 'da3787884c0e875d9d1a330713c0bca5', '59ba82c032cf242e4839f373fba37dcba88c46a7b9e13cc4a568e7c74b78d317');
INSERT INTO usuarios (usuario, nome, perfil, salt, hash_senha) VALUES ('diana', 'Diana Rocha', 'AUDITOR', 'c603346cde378837d364a9c8137f6116', 'c46e80f1c9e031949b1ecce46af235dce26ce443503c93a3b4d504929efce401');

INSERT INTO ativos (codigo, nome, tipo) VALUES ('PETR4', 'Petrobras PN', 'ACAO'), ('VALE3', 'Vale ON', 'ACAO'), ('ITUB4', 'Itaú Unibanco PN', 'ACAO'),
    ('BOVA11', 'iShares Ibovespa', 'ETF'), ('HGLG11', 'CSHG Logística', 'FII'), ('MXRF11', 'Maxi Renda', 'FII');

INSERT INTO contas (usuario, saldo, limite_diario) VALUES ('ana', 50000, 100000), ('bruno', 5000, 20000);

INSERT INTO custodia (usuario, ativo, quantidade) VALUES ('ana', 'PETR4', 200), ('ana', 'VALE3', 100), ('ana', 'MXRF11', 500), ('bruno', 'ITUB4', 50);
