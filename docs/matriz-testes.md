# Matriz mínima de testes do MVP

Estado: T01–T49 possuem cobertura automatizada unitária, de serviço, HTTP ou PostgreSQL. A execução local aprova 150 testes e ignora os 20 casos que exigem o PostgreSQL 17 efêmero do GitHub Actions; o CI executa os 170. O Supabase foi validado com consultas e transações revertidas, sem resíduos. Casos com múltiplos valores usam testes parametrizados quando adequado.

A [matriz de rastreabilidade](rastreabilidade.md) liga estes IDs aos requisitos, endpoints e telas do frontend.

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
| T34 | RF16, RN30, UC15 | Cadastro com entrega ativa cria conta pendente e envia código; login com senha correta retorna 403 `email_not_verified`; senha errada continua 401 genérico; código correto retorna token; código reutilizado retorna 400 |
| T35 | RN29 | Código com 5 erros é invalidado; código expirado é recusado; entrada que não tem 6 dígitos retorna 422; hash vinculado a usuário e finalidade |
| T36 | RF17, RN29, RN31 | Reenvio dentro de 60 s não gera e-mail; depois de 60 s substitui o código; e-mail desconhecido recebe 202 sem envio |
| T37 | RN30 | E-mail pendente fica reservado por 24 h (409); depois disso, o novo cadastro substitui a conta pendente |
| T38 | RF18, RN32, UC16 | Recuperação troca a senha, recusa a senha antiga, invalida tokens anteriores e aceita o novo login; dona do e-mail recupera conta criada por outra pessoa |
| T39 | RN33, RNF07 | 11º cadastro do mesmo IP em 1 h retorna 429 `too_many_requests` |
| T40 | RN34 | Sem entrega de e-mail, conta nasce confirmada e reenvio/recuperação retornam 503; `EMAIL_DELIVERY=log` é recusado em produção; migração `0006` preserva contas existentes como confirmadas |
| T41 | RN35 | Painel exige autenticação (401) e administração (403); `ADMIN_EMAILS` é normalizado; `/users/me` informa `is_admin` |
| T42 | RN36 | Lotes aceitam só eventos previstos, até 8 propriedades escalares com nomes identificadores, textos cortados em 200 caracteres, até 20 eventos e sessão UUID |
| T43 | RN37 | Evento com token válido é associado ao usuário; sem token ou com token inválido fica anônimo, sempre 202; lotes acima do limite por IP retornam 429 |
| T44 | RN38, RN39, RNF09 | Middleware registra o template da rota e ignora `/health`; agregação por minuto e classe; `UPSERT` soma contagens e faixas; falha de gravação devolve ao buffer; retenção remove dados antigos; p95 pelas faixas, com a faixa aberta sinalizada |
| T45 | RF19, RN40 | Painel sobre dados conhecidos: totais, 30 dias de série, North Star, buscas com resultado, ativação por coorte, funil e abandono, conflitos, catálogo, rotas com 5xx e p95, versões e erros do frontend |
| T46 | RNF08 | Interface: eventos só no build de produção, sem automação e sem Do Not Track; lote a cada 5 s ou 10 eventos; erros do navegador sem query string e limitados por sessão |
| T47 | RN41 | Motivos agregados por aspecto no detalhe: contagem positiva e negativa, ordem por menções, exclusão da avaliação própria, lista vazia sem avaliações e ausência na listagem |
| T48 | RN14, RN42 | Busca no PostgreSQL: filtro, contagem, ordem e paginação no banco; `%` e `_` literais; renomear atualiza a busca; erro de digitação devolve parecidos com `approximate`; categoria mantida; termo distante não sugere nada |
| T49 | RN43, RF20 | Leitor: dígito verificador, leitor nativo e ZXing, permissão negada, sem câmera e sem suporte, câmera desligada ao fechar; E2E com câmera falsa lendo um EAN-13; evento `barcode_scan` aceito e métricas no painel |

## Estratégia

- Unitários: normalizadores, GTIN, identidade, critérios e cálculo de distribuições.
- Integração: HTTP, persistência, autorização, transações e migrações.
- Concorrência: requisições/transações realmente sobrepostas, não apenas chamadas sequenciais.
- Segurança: relógio controlável para expiração/limitação e inspeção de respostas/logs sem dados reais.
- Registrar resultado por ID ao implementar. Diagramas e documentação não substituem os testes executáveis.

## Execução da revisão integrada

- `tests/test_end_to_end.py`: jornada cadastro → login/JWT → produto → avaliação → consultas pública e privada → edição → exclusões.
- `tests/test_operations.py`: saúde 200/503, erro 500 seguro e contrato OpenAPI com Bearer obrigatório/opcional.
- `tests/test_postgres_concurrency.py`: unicidade sob commits simultâneos e corrida avaliação versus exclusão usando sessões PostgreSQL independentes.
- `tests/test_account_flows_postgres.py`: confirmação de e-mail, reenvio, expiração, recuperação de senha e limites por IP via HTTP contra PostgreSQL real (T34–T39).
- `tests/test_account_security.py`: configuração de entrega, versão de sessão no JWT, formato e HMAC dos códigos (T35, T40).
- `tests/test_observability.py`: faixas e percentis, agregação, middleware, acesso ao painel e validação de eventos (T41, T42, T44).
- `tests/test_search_postgres.py`: busca exata e aproximada com pg_trgm (T48).
- `tests/test_admin_postgres.py`: gravação e retenção das métricas, ingestão de eventos e números do painel contra PostgreSQL real (T43–T45).
- Frontend: `src/features/barcode/*.test.ts(x)` e `e2e/barcode.spec.ts` (T49), `src/lib/analytics.test.ts` (T46) e `AdminDashboard.test.tsx` + `e2e/admin.spec.ts` (painel).
- `.github/workflows/tests.yml`: Python 3.12, PostgreSQL 17, verificação de dependências e suíte completa.
