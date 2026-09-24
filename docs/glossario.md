# Glossário do domínio

Uma linguagem comum evita que produto, código e banco usem palavras diferentes para a mesma coisa. A interface fala português. A API usa valores técnicos em inglês. O banco usa nomes de colunas em português. Esta tabela é a ponte entre os três.

## Conceitos

| Termo | Definição | API | Banco |
|---|---|---|---|
| **Visitante** | Pessoa sem autenticação; pode consultar o catálogo | — | — |
| **Usuário autenticado** | Pessoa com token válido; pode cadastrar e avaliar | Bearer JWT | `usuarios` |
| **Conta pendente** | Conta cadastrada cujo e-mail ainda não foi confirmado; não obtém token e reserva o e-mail por 24 h | `email_verified: false` | `email_verificado_em` nulo |
| **Código de verificação** | Número de 6 dígitos, de uso único, enviado por e-mail para confirmar a conta ou redefinir a senha | `code` | `codigos_verificacao` (só o HMAC) |
| **Versão de sessão** | Contador que invalida todos os tokens anteriores quando a senha é trocada | claim `ver` do JWT | `versao_sessao` |
| **Nome público** | Nome exibido como autor de avaliações; pode se repetir | `name` | `nome_publico` |
| **Produto** | Item comercial vendido em mercado, com medida e marca definidas | `Product` | `produtos` |
| **Registro canônico** | O único registro de um produto no catálogo compartilhado | `id` | `produtos.id` |
| **Responsável** | Usuário que cadastrou (ou reativou) o produto; pode corrigi-lo com restrições | não exposto | `criador_id` |
| **Variante** | Diferencial opcional do produto: sabor, fragrância, versão | `variant` | `variante` |
| **GTIN** | Código de barras (GTIN-8/12/13/14) com dígito verificador | `barcode` | `codigo_barras` |
| **Chave de identidade** | Serialização normalizada de nome + marca + variante + quantidade + unidade, usada para deduplicar | não exposta | `chave_identidade` |
| **Unidade canônica** | Unidade em que a quantidade é armazenada: `g`, `ml` ou `un` (entrada aceita também `kg` e `L`) | `unit` | `unidade` |
| **Exclusão lógica** | Produto oculto do catálogo, mas preservado e reativável | `DELETE` → 204 | `excluido_em` |
| **Reativação** | Recadastro de um produto excluído, que mantém o ID e troca o responsável | `POST` → 200 | — |
| **Avaliação** | Experiência atual de um usuário com um produto; no máximo uma por par | `Review` | `avaliacoes` |
| **Intenção de recompra** | Resumo principal da avaliação | `repurchase_intent` | `intencao_recompra` |
| **Critério universal** | Qualidade, expectativa ou custo-benefício; vale para qualquer categoria | `quality`, `expectation`, `value_for_money` | `qualidade`, `expectativa`, `custo_beneficio` |
| **Motivo** | Par aspecto + percepção que justifica a avaliação | `reasons[]` | `motivos_avaliacao` |
| **Aspecto** | Dimensão do produto à qual o motivo se refere | `aspect` | `aspecto` |
| **Percepção** | Se o aspecto foi positivo ou negativo | `perception` | `percepcao` |
| **Sua experiência** | A avaliação do próprio usuário, apresentada separadamente | `your_review`, `your_repurchase_intent` | — |
| **Administração** | Contas cujo e-mail está em `ADMIN_EMAILS`; acessam o painel `/admin` | `is_admin` | — (configuração) |
| **Evento de uso** | Registro de uma ação na interface (busca, abertura de produto, etapa da avaliação…), sem dados pessoais | `events[]` | `eventos_produto` |
| **Sessão anônima** | UUID gerado por aba do navegador para agrupar eventos sem identificar a pessoa | `session_id` | `sessao` |
| **Usuário ativo** | Usuário autenticado com ao menos um evento no período | — | — |
| **North Star** | Consultas a produtos que o usuário já avaliou, por usuário ativo por semana | `product.north_star` | — (calculado) |
| **Indicadores comunitários** | Distribuições percentuais calculadas sob demanda a partir das avaliações de outras pessoas | `community_summary` | — (não armazenado) |

## Valores controlados

| Domínio | Português (interface) | Valor técnico |
|---|---|---|
| Categoria | Alimentos · Bebidas · Limpeza · Higiene pessoal · Utilidades domésticas · Outros | `food` · `beverages` · `cleaning` · `personal_hygiene` · `household_utilities` · `other` |
| Recompra | Compraria novamente · Talvez comprasse · Não compraria | `yes` · `maybe` · `no` |
| Qualidade | Baixa · Adequada · Alta | `low` · `adequate` · `high` |
| Expectativa | Não atendeu · Atendeu · Superou | `not_met` · `met` · `exceeded` |
| Custo-benefício | Ruim · Justo · Bom | `poor` · `fair` · `good` |
| Percepção | Positiva · Negativa | `positive` · `negative` |
| Aspecto | Sabor · Cheiro ou fragrância · Textura ou consistência · Eficácia ou desempenho · Quantidade ou rendimento · Facilidade de uso ou preparo · Embalagem · Durabilidade ou conservação · Composição ou ingredientes · Segurança ou tolerância · Preço · Outro | `taste` · `fragrance` · `texture_consistency` · `effectiveness_performance` · `quantity_yield` · `ease_of_use_preparation` · `packaging` · `durability_preservation` · `composition_ingredients` · `safety_tolerance` · `price` · `other` |

## Identificadores dos artefatos

| Prefixo | Significado | Documento |
|---|---|---|
| RF | Requisito funcional | [requisitos.md](requisitos.md) |
| RN | Regra de negócio | [requisitos.md](requisitos.md) |
| RNF | Requisito não funcional | [requisitos.md](requisitos.md) |
| UC | Caso de uso | [casos-de-uso.md](casos-de-uso.md) |
| US | História de usuário | [historias-usuario.md](historias-usuario.md) |
| T | Caso da matriz de testes | [matriz-testes.md](matriz-testes.md) |
| ADR | Registro de decisão | [decisoes/](decisoes/README.md) |
| H / R | Hipótese / risco de produto | [visao-produto.md](visao-produto.md#8-hipóteses-e-riscos) |
