-- =============================================================================
-- Migration: 20260725_01_add_cpf_aniversariantes
-- Descrição: Adiciona a coluna cpf à tabela aniversariantes. Necessária para
--            a portaria identificar quando o convidado lido no QR Code (ou
--            buscado manualmente) é o próprio aniversariante daquela lista,
--            comparando o CPF do convidado com o CPF salvo aqui.
--
-- ATENÇÃO: nenhum fluxo atual (webhook do Kommo, chat) coleta ou grava o CPF
-- do aniversariante — hoje essa coluna fica NULL para todo mundo. Sem um
-- passo adicional no fluxo de cadastro (ex: nova etapa no chat da Kommo, ou
-- preenchimento manual) para popular este campo, a comparação de
-- "e_aniversariante" no backend nunca vai dar TRUE em produção.
-- =============================================================================

ALTER TABLE public.aniversariantes
    ADD COLUMN IF NOT EXISTS cpf VARCHAR(11);
