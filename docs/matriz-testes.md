# Matriz mínima de testes do MVP

Estado: cenários planejados, ainda não executados. Casos com múltiplos valores devem virar testes parametrizados. Integração usa PostgreSQL isolado.

| ID | Cobertura | Cenário e resultado esperado |
|---|---|---|
| T01 | RF01, UC01 | Cadastro válido 201; nome repetido permitido; senha/hash ausentes da resposta; hash verificável |
| T02 | RN03 | E-mails com caixa/espaços equivalentes conflitam com 409, inclusive em criação concorrente |
| T03 | UC01 | Senha com 14/15/128/129 caracteres; lista comum; espaços preservados; falhas 422 sem eco da senha |
| T04 | RF02, UC02 | Login válido 200 com bearer e 86400; e-mail inexistente e senha incorreta retornam 401 genérico |
| T05 | UC02 | JWT alterado, expirado, algoritmo não permitido ou claims obrigatórios ausentes retorna 401; token sem dados privados |
| T06 | UC02 | Limites por conta e IP, fronteiras temporais, 429, recuperação após janela e reset de conta após sucesso; conta inexistente não revelada |
| T07 | RN04, RF14 | Escrita e /users/me sem token: 401; leitura pública sem token: 200; token inválido em leitura opcional: 401 |
| T08 | RN05–RN14 | Textos Unicode, limites mínimos/máximos e trim; variante vazia=null; normalização de caixa/acentos/espaços, pontuação preservada |
| T09 | RN11 | 1.5 L=1500 ml; 2 kg=2000 g; zeros decimais equivalentes; não positivos, não finitos, precisão excessiva e un fracionário: 422 |
| T10 | RN09 | GTIN8/12/13/14 com checksum; zero inicial preservado; formato/comprimento/checksum inválido: 422; sem obrigação de prefixo brasileiro |
| T11 | UC06 | Produto novo 201; duplicado ativo 409 com existing_product_id no envelope; concorrência não cria duplicata |
| T12 | UC07 | Responsável sem terceiros edita 200, inclusive com avaliação própria; outro usuário 403; avaliação de terceiro bloqueia com 409 |
| T13 | UC07 | PATCH omitido preserva; null opcional remove; null obrigatório 422; edição duplicada 409 sem mudança parcial |
| T14 | UC11 | Produto sem avaliações: exclusão lógica 204 sem corpo; com avaliação própria ou alheia: 409; outro usuário: 403; repetição: 404 |
| T15 | UC06, UC11 | Inativo não aparece em listas e retorna 404 em detalhe, PATCH, DELETE e criação/lista de avaliações |
| T16 | UC06 | Recadastro reativa 200 com mesmo ID, novo responsável e dados válidos; listas/permissões passam ao novo responsável |
| T17 | RN11 | GTIN e identidade apontando a registros distintos: 409 sem mesclar ou reativar; colisão concorrente preserva unicidade |
| T18 | UC08 | Avaliação válida 201; segunda avaliação do mesmo usuário/produto 409, inclusive concorrente |
| T19 | RN16–RN24 | Critérios inválidos, motivos ausentes/vazios/duplicados e other sem comentário não branco: 422; comentário máximo 1000 |
| T20 | UC08–UC09 | Motivo inválido ou falha de persistência desfaz avaliação e motivos; nenhuma gravação parcial |
| T21 | UC09 | PATCH omitido preserva; reasons substitui lista; [] rejeitado; resultado com other exige comentário; criação preservada e atualização alterada |
| T22 | UC09–UC10 | Outro autor: 403; exclusão própria: 204 sem corpo e motivos removidos; repetição: 404; produto e outras avaliações intactos |
| T23 | UC04 | Sem filtros lista ativos; nome/marca parcial sem caixa/acentos; filtros com categoria usam AND; GTIN exato isolado permite paginação |
| T24 | UC04 | Filtro textual curto, categoria inválida/repetida, GTIN combinado, page/page_size inválidos: 422; padrões 1/20 e máximo 100 |
| T25 | UC04–UC05 | Pesquisa sem correspondência: 200 com items vazio; recurso específico inexistente: 404; ordenação estável com desempate |
| T26 | RF12, RN26–RN27 | Visitante considera todas; autenticado exclui própria em resumos e listas; intenção/avaliação própria separada; total acompanha o filtro |
| T27 | RF12 | Zero avaliações: total e porcentagens zero; três respostas iguais: 33.3 cada, sem ajuste; edição/exclusão refletida nas consultas |
| T28 | UC12–UC14 | Conta privada, avaliações completas com produto e produtos ativos do responsável; nunca inclui dados pessoais de outro usuário |
| T29 | RNF02 | Comunidade exibe nome público, não email/ID do autor; resposta pública sem hash, senha, chave de identidade ou responsável interno |
| T30 | RNF05 | Erros 401/403/404/409/422/429/500/503 no envelope; campos aninhados com caminho; erro inesperado sem SQL/segredos |
| T31 | RF15 | /health fora de /api/v1: 200 saudável; API respondendo sem banco: 503 padronizado |
| T32 | Integridade | Corridas avaliar versus editar/excluir produto preservam regras; transações com bloqueio consistente, sem órfãos |
| T33 | Persistência | Migração em banco vazio; CHECKs, FKs e UNIQUE efetivos; datas UTC e quantidades exatas no percurso entrada-banco-resposta |

## Estratégia

- Unitários: normalizadores, GTIN, identidade, critérios e cálculo de distribuições.
- Integração: HTTP, persistência, autorização, transações e migrações.
- Concorrência: requisições/transações realmente sobrepostas, não apenas chamadas sequenciais.
- Segurança: relógio controlável para expiração/limitação e inspeção de respostas/logs sem dados reais.
- Registrar resultado por ID ao implementar. Diagramas e documentação não substituem os testes executáveis.
