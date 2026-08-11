-- =============================================================================
-- Tabela: comandas_temporarias
-- Descrição: Fila de sincronização entre a validação de entrada na portaria e a
--            abertura de comanda no ERP Epoc. Processamento assíncrono, com
--            re-tentativas controladas pelo campo status_epoc.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.comandas_temporarias (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    kommo_lead_id VARCHAR(255) NOT NULL,
    nome_cliente VARCHAR(255) NOT NULL,
    is_aniversariante BOOLEAN DEFAULT FALSE,
    qr_code_token VARCHAR(255) UNIQUE NOT NULL,
    status_epoc VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'sincronizado', 'falhou'
    criado_em TIMESTAMPTZ DEFAULT NOW()
);
