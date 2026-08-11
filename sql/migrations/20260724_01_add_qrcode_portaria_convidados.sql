-- =============================================================================
-- Migration: 20260724_01_add_qrcode_portaria_convidados
-- Descrição: Adiciona suporte ao QR Code individual e ao check-in na portaria
--            para a tabela convidados (Fase 1 - Validador da Portaria).
-- =============================================================================

ALTER TABLE public.convidados
    ADD COLUMN IF NOT EXISTS qr_code_token UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    ADD COLUMN IF NOT EXISTS utilizado BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS data_hora_entrada TIMESTAMP WITH TIME ZONE;

-- Índice para a busca ultra-rápida do aplicativo da portaria ao bipar o QR Code
CREATE INDEX IF NOT EXISTS idx_convidados_qr_code_token ON public.convidados(qr_code_token);
