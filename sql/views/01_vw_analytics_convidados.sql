-- =============================================================================
-- View: vw_analytics_convidados
-- Descrição: Camada analítica consumida pelo endpoint GET /convidados/resumo/{lead_id}
--            (backend/app/routes/convidados.py), que agrupa os convidados
--            confirmados por faixa etária e por período do dia da confirmação.
--
-- ATENÇÃO: esta view ainda não possui DDL versionada no Supabase. A definição
-- abaixo foi reconstruída a partir do uso real dos campos `faixa_etaria` e
-- `periodo_confirmacao` no backend e deve ser validada/ajustada contra a
-- definição vigente no banco antes de ser aplicada em produção.
-- =============================================================================

CREATE OR REPLACE VIEW public.vw_analytics_convidados AS
SELECT
    c.id,
    c.lead_id,
    c.nome_completo,
    c.cpf,
    c.whatsapp,
    c.data_nascimento,
    c.confirmado_em,
    CASE
        WHEN DATE_PART('year', AGE(CURRENT_DATE, c.data_nascimento)) < 18 THEN 'Menor de 18'
        WHEN DATE_PART('year', AGE(CURRENT_DATE, c.data_nascimento)) BETWEEN 18 AND 25 THEN '18 a 25'
        WHEN DATE_PART('year', AGE(CURRENT_DATE, c.data_nascimento)) BETWEEN 26 AND 35 THEN '26 a 35'
        WHEN DATE_PART('year', AGE(CURRENT_DATE, c.data_nascimento)) BETWEEN 36 AND 45 THEN '36 a 45'
        ELSE 'Acima de 45'
    END AS faixa_etaria,
    CASE
        WHEN EXTRACT(HOUR FROM c.confirmado_em) BETWEEN 6 AND 11 THEN 'Manhã'
        WHEN EXTRACT(HOUR FROM c.confirmado_em) BETWEEN 12 AND 17 THEN 'Tarde'
        WHEN EXTRACT(HOUR FROM c.confirmado_em) BETWEEN 18 AND 23 THEN 'Noite'
        ELSE 'Madrugada'
    END AS periodo_confirmacao
FROM public.convidados c;
