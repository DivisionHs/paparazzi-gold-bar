-- Permite SOBRESCREVER (UPDATE) arquivos já existentes no bucket
-- "fotos-aniversariantes" — até aqui só existia policy de leitura/criação
-- (INSERT), então o upload com upsert=true funcionava pra foto/flyer novos,
-- mas falhava com 403 ("new row violates row-level security policy") ao
-- tentar regerar o flyer de um lead que já tinha cadastro.
--
-- Achado em 23/09/2026 usando a ferramenta de atendimento manual
-- (backend/app/routes/admin.py, ver CLAUDE.md 4.9) pra corrigir a data de um
-- flyer já gerado (bug de data "31/12/1969" — Kommo tratou um campo de data
-- incompleto, sem ano, como timestamp Unix 0). O fluxo automático do bot
-- nunca esbarrava nisso porque tem checagem de idempotência (nunca tenta
-- reprocessar um lead que já tem registro) — a correção manual foi o
-- primeiro caminho a realmente tentar sobrescrever um arquivo existente.
--
-- Escopo restrito ao bucket específico, mesmo nível de permissividade que a
-- policy de INSERT já existente (qualquer chamada autenticada com a chave
-- anon do projeto, mesma que o backend já usa em produção).
CREATE POLICY "Permitir atualizacao de fotos de aniversariantes"
ON storage.objects
FOR UPDATE
TO public
USING (bucket_id = 'fotos-aniversariantes')
WITH CHECK (bucket_id = 'fotos-aniversariantes');
