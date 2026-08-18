import os
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import create_client, Client

from backend.app.services.auth_service import obter_funcionario_autenticado

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


# Painel operacional (staff-only): lista os aniversariantes com reserva para
# hoje, com horário/estimativa (Custom Fields do Kommo, persistidos desde a
# migration 20260817_01) e a quantidade REAL de convidados já confirmados
# (COUNT em `convidados`, sempre atual — não depende de nada do Kommo).
@router.get("/hoje", dependencies=[Depends(obter_funcionario_autenticado)])
async def listar_aniversariantes_hoje():
    hoje = date.today().isoformat()

    try:
        resposta = supabase.table("aniversariantes")\
            .select("kommo_lead_id, nome_completo, horario_reserva, estimativa_convidados")\
            .eq("data_reserva", hoje)\
            .execute()
    except Exception as e:
        print(f"Erro ao consultar aniversariantes do dia: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao consultar os aniversariantes do dia."
        )

    aniversariantes = resposta.data or []

    contagem_por_lead: Counter = Counter()
    if aniversariantes:
        lead_ids = [a["kommo_lead_id"] for a in aniversariantes]
        try:
            resposta_convidados = supabase.table("convidados")\
                .select("lead_id")\
                .in_("lead_id", lead_ids)\
                .execute()
            contagem_por_lead = Counter(c["lead_id"] for c in (resposta_convidados.data or []))
        except Exception as e:
            # Não crítico: o painel ainda é útil sem a contagem (mostra 0).
            print(f"Erro ao contar convidados confirmados dos aniversariantes do dia: {e}")

    lista = [
        {
            "lead_id": a["kommo_lead_id"],
            "nome_completo": a["nome_completo"],
            "horario_reserva": a.get("horario_reserva"),
            "estimativa_convidados": a.get("estimativa_convidados"),
            "quantidade_confirmada": contagem_por_lead.get(a["kommo_lead_id"], 0),
        }
        for a in aniversariantes
    ]
    lista.sort(key=lambda a: a["horario_reserva"] or "99:99")

    return {"data": hoje, "total": len(lista), "aniversariantes": lista}
