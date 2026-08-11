-- =============================================================================
-- Tabela: convidados
-- Descrição: Registro dos convidados confirmados na lista de um aniversariante.
--            A unicidade de CPF é escopada por aniversariante (lead_id + cpf),
--            permitindo que o mesmo CPF apareça em listas de aniversariantes
--            diferentes, mas nunca duplicado na mesma lista.
-- =============================================================================

CREATE TABLE public.convidados (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id TEXT NOT NULL, -- ID do aniversariante vindo do Kommo CRM
    nome_completo TEXT NOT NULL,
    cpf VARCHAR(11) NOT NULL,
    whatsapp VARCHAR(11) NOT NULL, -- Apenas números com DDD (ex: 11999999999)
    data_nascimento DATE NOT NULL,
    confirmado_em TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    CONSTRAINT unique_cpf_por_aniversariante UNIQUE (lead_id, cpf)
);

-- Índices para acelerar buscas por CPF ou por Aniversariante (Lead)
CREATE INDEX IF NOT EXISTS idx_convidados_lead_id ON public.convidados(lead_id);
CREATE INDEX IF NOT EXISTS idx_convidados_cpf ON public.convidados(cpf);
