# Plano de implementação do MVP

## Situação

Planejamento consolidado. Entregas 1–8 implementadas na branch `main`: fábrica FastAPI, configuração protegida, SQLAlchemy/Alembic, normalizadores, schemas, envelope seguro de erros, autenticação, produtos, avaliações transacionais, consultas, `/health`, OpenAPI e CI. A API está publicada no Render com HTTPS e PostgreSQL no Supabase. A Entrega 9 fecha a operação de produção com acesso mínimo ao banco, CORS configurável, smoke test e documentação atualizada.

Referências: [requisitos](requisitos.md), [casos de uso](casos-de-uso.md), [contrato](contrato-api.md), [modelo](modelo-banco.md) e [testes](matriz-testes.md). Ideação é histórico; mudanças posteriores estão refletidas nesses documentos.

## Sequência de entregas

| Ordem | Entrega | Dependência | Critério de conclusão |
|---|---|---|---|
| 1 | Estrutura FastAPI, configuração por ambiente e instruções locais | — | Aplicação inicia; segredos ausentes geram falha clara sem vazamento |
| 2 | PostgreSQL, modelos e migração inicial | 1 | Migração sobe em banco vazio; FKs, CHECKs, unicidades e timestamps verificados |
| 3 | Normalizadores, validadores, schemas e envelope de erro | 1 | Testes de limites, decimal, GTIN e PATCH aprovados |
| 4 | Cadastro, hash, login, JWT, limites de tentativa e /users/me | 2–3 | Testes de autenticação, privacidade e limitação aprovados |
| 5 | Criar, editar, excluir e reativar produtos | 2–4 | Unicidade, autorização e corridas entre operações testadas |
| 6 | Criar, editar e excluir avaliações e motivos | 5 | Atomicidade, autoria e unicidade testadas |
| 7 | Pesquisa, detalhe, comunidade e listas pessoais | 5–6 | Paginação, filtros e exclusão da própria avaliação conferidos |
| 8 | /health, documentação OpenAPI, revisão integrada e execução automatizada dos testes | 1–7 | Matriz mínima aprovada em PostgreSQL e README com execução reproduzível |
| 9 | Segurança e operação da API publicada | 8 | Papel restrito no banco, CORS explícito, smoke test não destrutivo e documentação de produção |

## Diretrizes técnicas para execução

- Usar uma aplicação monolítica simples. Como base de implementação, SQLAlchemy, Alembic e pytest são escolhas propostas; versões e APIs serão verificadas no início da implementação.
- Usar PostgreSQL também nos testes de integração, com banco isolado e nunca dados de produção.
- Separar schemas públicos das entidades persistidas e manter regras de negócio testáveis, sem criar camadas sem necessidade.
- Aplicar migrações em produção somente pelo Alembic durante o deploy, usando credencial separada da conexão diária da aplicação.
- Rate limiting precisa de contadores atômicos e prazo de expiração. Não presumir que memória de um processo proteja múltiplos workers; documentar o modo de execução e testar seus limites antes de ampliar.
- Senhas e tokens não entram em logs nem nos detalhes retornados por validadores. Usar HTTPS quando houver implantação.
- Unicidade deve ser protegida pelo banco, não apenas por consulta prévia. Verificações de estado e gravação compartilham transação e bloqueio do produto.
- Não adicionar fila, cache de indicadores, microserviços ou interface neste MVP.

## Precisões adotadas na consolidação

Não são funcionalidades novas: o recadastro troca o responsável atual e preserva a data original; datas empatadas usam ID para ordenar; GTIN e identidade que apontam a registros diferentes produzem conflito sem mesclar; senhas não sofrem trim; variante vazia equivale a null. O contrato registra essas convenções.

## Critério de encerramento

Cada entrega inclui implementação e testes pertinentes, sem postergar toda a validação para o fim. O backend do MVP está concluído e publicado: a matriz possui cobertura executável, a documentação reproduz a execução e o fluxo cadastro → login → produto → avaliação → consulta foi validado em produção. A interface web continua fora deste plano e será a próxima fase do produto.
