-- =============================================================================
-- Tabela: aniversariantes
-- Descrição: Armazena o lead do aniversariante vindo do Kommo CRM. O registro
--            só nasce quando o Lead chega na etapa "PROCESSANDO FLYER"
--            (status_id 109983139) com os 5 Custom Fields obrigatórios já
--            coletados pelo Salesbot — não há mais estado intermediário de
--            cadastro nesta tabela (ver CLAUDE.md 4.2 e 7.).
--
-- Este arquivo já reflete as migrations aplicadas em sql/migrations/:
--   - 20260725_01_add_cpf_aniversariantes.sql (coluna cpf)
--   - 20260804_01_add_data_reserva_aniversariantes.sql (coluna data_reserva)
--   - 20260804_02_remove_status_cadastro_aniversariantes.sql (remoção de status_cadastro)
--   - 20260807_01_add_foto_perfil_url_aniversariantes.sql (coluna foto_perfil_url)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.aniversariantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kommo_lead_id VARCHAR(50) UNIQUE NOT NULL, -- ID do lead no Kommo CRM (chave de conflito do upsert)
    nome_completo VARCHAR(255) NOT NULL,
    token_exclusivo UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL, -- Token público usado no link enviado por WhatsApp
    foto_url TEXT, -- Link do flyer gerado (bucket fotos-aniversariantes)
    foto_perfil_url TEXT, -- Link da foto ORIGINAL do aniversariante (Custom Field 2068458), exibida no formulário do convidado
    data_reserva DATE, -- Sincronizada com o Custom Field "Data da reserva" (ID 2068460) do Lead no Kommo
    cpf VARCHAR(11), -- Ainda não populado por nenhum fluxo real (ver migration 20260725_01)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
