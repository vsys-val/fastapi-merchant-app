# Registro de decisões (ADRs)

Cada arquivo registra **uma** decisão relevante de produto ou arquitetura: o contexto, as alternativas consideradas, a escolha e suas consequências, inclusive as negativas.

As decisões foram tomadas durante a ideação (14 a 18/08/2026) e registradas em commits atômicos de `docs/ideacao.md`. Estes ADRs foram **escritos retroativamente** a partir desse histórico, para tornar explícitas as alternativas e os trade-offs que a ideação registrava apenas como resultado. O commit de origem é citado em cada ADR.

| ADR | Decisão | Tipo | Status |
|---|---|---|---|
| [0001](0001-avaliacao-estruturada-sem-nota.md) | Avaliação estruturada, sem nota geral | Produto | Aceita |
| [0002](0002-intencao-de-recompra-como-resumo.md) | Intenção de recompra como resumo principal | Produto | Aceita |
| [0003](0003-motivos-estruturados-obrigatorios.md) | Motivos obrigatórios no formato aspecto + percepção | Produto | Aceita |
| [0004](0004-catalogo-canonico-comunitario.md) | Catálogo canônico comunitário com deduplicação | Produto / Dados | Aceita |
| [0005](0005-bloqueio-de-edicao-apos-avaliacao.md) | Bloqueio de edição do produto após avaliação de terceiros | Produto | Aceita |
| [0006](0006-avaliacao-pessoal-separada.md) | Avaliação pessoal separada dos indicadores comunitários | Produto | Aceita |
| [0007](0007-avaliacao-unica-sem-historico.md) | Uma avaliação atual por produto, sem histórico | Produto / Dados | Aceita |
| [0008](0008-exclusao-logica-e-reativacao.md) | Exclusão lógica de produto e reativação por recadastro | Produto / Dados | Aceita |
| [0009](0009-leitura-publica-escrita-autenticada.md) | Leitura pública, escrita autenticada | Produto / Segurança | Aceita |
| [0010](0010-autenticacao-propria.md) | Autenticação própria na API, sem Supabase Auth | Arquitetura | Aceita |

## Modelo

```markdown
# ADR-NNNN — Título no infinitivo ou substantivo

- Status: proposta | aceita | substituída por ADR-XXXX
- Data: AAAA-MM-DD
- Origem: commit ou discussão

## Contexto
## Alternativas consideradas
## Decisão
## Consequências
## Rastreabilidade
```

Uma nova decisão que contrarie uma existente gera um ADR novo, que **substitui** o anterior. ADRs aceitos não são reescritos.
