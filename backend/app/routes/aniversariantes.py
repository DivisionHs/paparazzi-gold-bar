import os
from fastapi import APIRouter, HTTPException, status
from supabase import create_client, Client

router = APIRouter(prefix="/aniversariantes", tags=["Aniversariantes"])

# Inicializa o client do Supabase puxando as variáveis do ambiente (.env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não foram configuradas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Handshake inicial do Flutter Web: valida o token_exclusivo (UUID v4) recebido
# na URL do link enviado por WhatsApp e devolve os dados do aniversariante para
# montar o banner da tela de cadastro do convidado.
@router.get("/validar-token/{token}")
async def validar_token_aniversariante(token: str):
    try:
        resposta = supabase.table("aniversariantes")\
            .select("kommo_lead_id, nome_completo, foto_url, foto_perfil_url")\
            .eq("token_exclusivo", token)\
            .maybe_single()\
            .execute()
    except Exception as e:
        print(f"Erro ao consultar aniversariante pelo token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao consultar a lista de aniversário."
        )

    dados_aniversariante = getattr(resposta, "data", None) if resposta else None

    if not dados_aniversariante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de aniversário não encontrada ou encerrada."
        )

    return {
        "lead_id": dados_aniversariante["kommo_lead_id"],
        "nome_completo": dados_aniversariante["nome_completo"],
        "foto_url": dados_aniversariante.get("foto_url"),
        "foto_perfil_url": dados_aniversariante.get("foto_perfil_url"),
    }
