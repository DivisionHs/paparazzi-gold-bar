-- =============================================================================
-- Migration: 20260804_01_add_data_reserva_aniversariantes
-- Descrição: Adiciona a coluna data_reserva à tabela aniversariantes, para
--            manter o Supabase sincronizado com o campo oficial "Data da
--            reserva" (ID 2068460) do Lead no Kommo CRM. Gravada tanto pelo
--            caminho feliz (clique nos botões de fim de semana do Salesbot,
--            calculado por /webhooks/kommo/data-reserva) quanto pelo caminho
--            de exceção (data digitada livremente pelo cliente, tratada
--            inteiramente pelo próprio Salesbot).
-- =============================================================================

ALTER TABLE public.aniversariantes
    ADD COLUMN IF NOT EXISTS data_reserva DATE;
