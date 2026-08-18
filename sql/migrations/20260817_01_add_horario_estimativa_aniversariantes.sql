-- =============================================================================
-- Migration: 20260817_01_add_horario_estimativa_aniversariantes
-- Descrição: Adiciona as colunas horario_reserva e estimativa_convidados à
--            tabela aniversariantes. Os dois valores já chegavam a cada
--            webhook (Custom Fields "Horário da reserva", ID 2068854, e
--            "Estimativa de Convidados", ID 2068456), mas eram usados só
--            para desenhar o flyer (imagem) e descartados — nunca gravados
--            no Supabase. Passam a ser persistidos para alimentar o painel
--            de aniversariantes do dia (ver CLAUDE.md 4.2/4.7).
-- =============================================================================

ALTER TABLE public.aniversariantes
    ADD COLUMN IF NOT EXISTS horario_reserva TIME,
    ADD COLUMN IF NOT EXISTS estimativa_convidados INTEGER;
