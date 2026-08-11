-- =============================================================================
-- Migration: 20260804_02_remove_status_cadastro_aniversariantes
-- Descrição: Remove a coluna status_cadastro da tabela aniversariantes.
--
-- O registro do aniversariante deixou de nascer no momento em que o lead
-- entra no funil (status_id/tag "aniversario") e passou a nascer apenas ao
-- final do fluxo de chat, quando nome + foto já foram coletados e o flyer já
-- foi processado — evitando "dados fantasmas" de quem clica no fluxo mas
-- nunca envia a foto. O estado intermediário (aguardando nome / aguardando
-- foto) passou a ser controlado direto no Lead do Kommo (campo `name`), não
-- mais nesta tabela.
-- =============================================================================

ALTER TABLE public.aniversariantes
    DROP COLUMN IF EXISTS status_cadastro;
