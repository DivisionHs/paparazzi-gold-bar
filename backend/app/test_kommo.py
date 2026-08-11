import httpx

# Cole aqui a URL gerada pelo seu Ngrok
URL_SERVIDOR = "https://vaporizer-shimmer-proofread.ngrok-free.dev/"

# ATENÇÃO (mudança de 06/08/2026 — Estratégia de Consulta Ativa): o webhook
# agora é tratado só como um SINALIZADOR LEVE (lead_id + status_id). Assim
# que a rota recebe o sinal, ela faz um GET de verdade na API do Kommo para
# buscar os Custom Fields atualizados — ela NÃO lê mais nenhum valor de
# custom field do corpo deste payload de teste.
#
# Por isso, diferente da versão anterior deste script, LEAD_TESTE_ID
# PRECISA ser o ID de um Lead REAL e existente na sua conta do Kommo (use
# backend/app/test_inspecionar_lead.py para conferir, antes de rodar este
# script, quais Custom Fields esse lead realmente tem preenchidos agora).
LEAD_TESTE_ID = "51339304"

# status_id da etapa "PROCESSANDO FLYER" (ver KOMMO_TARGET_STATUS_ID no
# .env). O webhook só dispara a consulta ativa quando o lead chega nesta
# etapa; o resultado do PASSO 2 abaixo depende do que a API do Kommo
# realmente devolver para os 5 Custom Fields obrigatórios deste lead.
STATUS_PROCESSANDO_FLYER = "109983139"


def _montar_payload_sinalizador(lead_id: str, status_id: str) -> dict:
    """
    Monta o payload mínimo que o webhook espera receber: só o suficiente
    para identificar o lead e a etapa. Nenhum Custom Field é enviado aqui —
    a rota busca os valores atualizados direto na API do Kommo.
    """
    return {
        "leads[id]": lead_id,
        "leads[status_id]": status_id,
    }


def testar_fluxo_completo():
    client = httpx.Client(base_url=URL_SERVIDOR)

    print("--- 🚫 PASSO 1: WEBHOOK COM O LEAD FORA DA ETAPA ALVO (deve ser ignorado antes de qualquer consulta à API) ---")
    payload_etapa_errada = _montar_payload_sinalizador(LEAD_TESTE_ID, "142")
    res_etapa_errada = client.post("/webhooks/kommo", data=payload_etapa_errada)
    print(f"Status Code: {res_etapa_errada.status_code}")
    print(f"Resposta: {res_etapa_errada.json()}\n")

    print("--- 🔄 PASSO 2: WEBHOOK COM O LEAD NA ETAPA 'PROCESSANDO FLYER' (agenda o processamento em background) ---")
    payload_sinalizador = _montar_payload_sinalizador(LEAD_TESTE_ID, STATUS_PROCESSANDO_FLYER)
    res_sinalizador = client.post("/webhooks/kommo", data=payload_sinalizador)
    print(f"Status Code: {res_sinalizador.status_code}")
    print(f"Resposta: {res_sinalizador.json()}\n")
    print(
        "👉 ATENÇÃO (mudança de 07/08/2026 — ack imediato): a resposta acima é só a confirmação de que\n"
        "   o lead está na etapa alvo e o processamento foi agendado — ela SEMPRE vem rápido com\n"
        "   {'status': 'recebido', ...}, mesmo que o lead já tenha sido processado antes ou esteja com\n"
        "   Custom Field faltando. O resultado real do processamento em background só aparece no\n"
        "   terminal do Uvicorn, alguns segundos depois:\n"
        "   - 'já tem cadastro em aniversariantes' -> reentrega ignorada (idempotência).\n"
        "   - 'campos vazios' / 'Faltando: ...' -> algum dos 5 Custom Fields obrigatórios não veio preenchido.\n"
        "   - '🎉 TODOS OS DADOS COLETADOS' seguido de '🏁 Processamento em background concluído' -> sucesso.\n"
        "   Rode 'python -m backend.app.test_inspecionar_lead " + LEAD_TESTE_ID + "' antes, "
        "para saber de antemão o que esperar deste passo.\n"
    )


if __name__ == "__main__":
    testar_fluxo_completo()
