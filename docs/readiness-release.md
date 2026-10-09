# Liberação das correções para o piloto

Esta entrega fecha riscos de cache HTTP e acrescenta proveniência ao catálogo.
O piloto de utilidade/recorrência e uma oferta paga continuam dependentes de
observação real. Não há cobrança, receita ou resultados de usuários nesta entrega.

## Ordem operacional

1. Aprovar CI da API (incluindo PostgreSQL efêmero) e do frontend.
2. Em banco isolado, ensaiar instalação limpa, migração 0010 → 0011 e
   recuperação de backup. Registrar IDs, avaliações e dono antes/depois.
3. Conferir `docs/catalog-provenance.md`: a 0011 depende dos bytes históricos
   do JSON. Não regenerar esse arquivo nem editar migrações publicadas.
4. Aplicar migração aditiva antes de iniciar a API nova. O ORM consulta as novas
   colunas; frontend novo tolera ausência de campos enquanto a API antiga está
   publicada. Downgrade remove metadados e exige rollback compatível da API.
5. Publicar frontend após API; executar o procedimento
   `merchant-app-web/docs/production-verification.md`, conferindo CSP real,
   proxy, cookie, `no-store`, imagens e atualização do service worker.
6. Só liberar piloto depois de validar buscar → abrir → avaliar → consultar
   depois → sair, com conta de teste identificável e ambiente autorizado.

## O que ainda exige decisão ou ambiente

- CSP enviada pelo Render difere da configuração versionada: precisa ser
  reconciliada no serviço, não é resolvida por alterar apenas código.
- Licença específica, autoria e atribuição completa das fotos ainda exigem
  confirmação antes de exploração comercial. Valores desconhecidos ficam nulos.
- Provedor de e-mail e canal de suporte precisam ser definidos/configurados.
- Backup/restauração e jornada autenticada real não são substituídos pelo CI.
- Entrevistas, retorno espontâneo e pagamento dependem de participantes reais.

Não substituir nenhum requisito acima por um badge verde. Cada resultado deve
registrar commit, ambiente, data e evidência sem cookies, tokens ou credenciais.
