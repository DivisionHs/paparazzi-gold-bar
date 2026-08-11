-- =============================================================================
-- Migration: 20260807_01_add_foto_perfil_url_aniversariantes
-- Descrição: Adiciona a coluna foto_perfil_url à tabela aniversariantes,
--            para guardar a URL da foto ORIGINAL do aniversariante (Custom
--            Field "Foto do aniversariante", ID 2068458), separada da URL
--            do flyer já composto (coluna foto_url).
--
-- Motivação: até esta migration, a foto original baixada do Kommo era usada
-- só como insumo do Pillow e descartada em seguida — só o flyer ficava
-- salvo no Storage. A foto original também precisa existir como arquivo
-- próprio, pois é exibida no formulário de cadastro do convidado (Flutter
-- Web), e não o flyer completo.
-- =============================================================================

ALTER TABLE public.aniversariantes
    ADD COLUMN IF NOT EXISTS foto_perfil_url TEXT;
