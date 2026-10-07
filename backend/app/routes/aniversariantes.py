import os
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client, Client

from backend.app.services.auth_service import exigir_admin, obter_funcionario_autenticado

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


# Painel operacional (staff-only): lista os aniversariantes com reserva
# numa data específica, com horário/estimativa (Custom Fields do Kommo,
# persistidos desde a migration 20260817_01) e a quantidade REAL de
# convidados já confirmados (COUNT em `convidados`, sempre atual — não
# depende de nada do Kommo).
#
# Query param `data` opcional (decisão de 16/09/2026 — pedido do usuário
# pra também conseguir ver aniversariantes de outros dias, não só hoje):
# formato "AAAA-MM-DD"; sem ele, cai no padrão de sempre (hoje). O nome da
# rota (`/hoje`) ficou como está por compatibilidade — nenhum client
# existente precisa mudar pra continuar vendo só o dia de hoje.
@router.get("/hoje", dependencies=[Depends(obter_funcionario_autenticado)])
async def listar_aniversariantes_hoje(
    data: date | None = Query(None, description="Data no formato AAAA-MM-DD. Padrão: hoje."),
):
    data_alvo = (data or date.today()).isoformat()

    try:
        resposta = supabase.table("aniversariantes")\
            .select("kommo_lead_id, nome_completo, horario_reserva, estimativa_convidados")\
            .eq("data_reserva", data_alvo)\
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

    return {"data": data_alvo, "total": len(lista), "aniversariantes": lista}


# Dashboard geral do login admin (decisão de 29/09/2026, ver CLAUDE.md 4.10).
# Três números cumulativos (desde sempre, não só do dia — diferente de
# /hoje): quantos agendamentos já foram processados pelo fluxo automático
# (linhas em `aniversariantes`), quantos convidados aproximados isso
# representa (soma de `estimativa_convidados`, valor vindo do Kommo) e
# quantos convidados já confirmaram presença de fato (linhas em
# `convidados`). Só o login admin acessa (ver `exigir_admin`) — o login da
# Portaria não deve ver números gerais do negócio, só a operação do dia.
#
# Filtro de período opcional (decisão de 07/10/2026, ver CLAUDE.md 4.11):
# `data_inicio`/`data_fim` (AAAA-MM-DD, ambos opcionais, inclusive nas duas
# pontas) filtram por `aniversariantes.data_reserva` — mesma coluna já usada
# em `/hoje`. Sem nenhum dos dois, cai no comportamento de sempre (tudo,
# desde o início). Esse filtro é o único incremento autorizado por enquanto
# no Dashboard — o resto do pedido de filtros/detalhamento (ver o "Dashboard
# completo" do próximo ciclo) fica condicionado ao contrato mensal.
@router.get("/estatisticas", dependencies=[Depends(exigir_admin)])
async def obter_estatisticas_gerais(
    data_inicio: date | None = Query(None, description="Filtra data_reserva >= esta data (AAAA-MM-DD)."),
    data_fim: date | None = Query(None, description="Filtra data_reserva <= esta data (AAAA-MM-DD)."),
):
    try:
        consulta_agendamentos = supabase.table("aniversariantes")\
            .select("kommo_lead_id, estimativa_convidados", count="exact")
        if data_inicio:
            consulta_agendamentos = consulta_agendamentos.gte("data_reserva", data_inicio.isoformat())
        if data_fim:
            consulta_agendamentos = consulta_agendamentos.lte("data_reserva", data_fim.isoformat())
        resposta_agendamentos = consulta_agendamentos.execute()
    except Exception as e:
        print(f"Erro ao consultar estatísticas de agendamentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao carregar as estatísticas gerais."
        )

    linhas_agendamentos = resposta_agendamentos.data or []
    total_agendamentos = resposta_agendamentos.count or 0
    total_convidados_estimados = sum(
        (linha.get("estimativa_convidados") or 0) for linha in linhas_agendamentos
    )

    # Sem filtro de período: mantém a contagem simples e global de sempre.
    # Com filtro: convidados confirmados só contam se pertencerem a um dos
    # agendamentos já filtrados por data (mesmo padrão de junção por
    # lead_id já usado em /hoje) — senão um convidado de uma reserva de
    # fora do período escolhido inflaria o número.
    if data_inicio or data_fim:
        lead_ids_filtrados = [l["kommo_lead_id"] for l in linhas_agendamentos]
        total_convidados_confirmados = 0
        if lead_ids_filtrados:
            try:
                resposta_convidados = supabase.table("convidados")\
                    .select("id", count="exact")\
                    .in_("lead_id", lead_ids_filtrados)\
                    .execute()
                total_convidados_confirmados = resposta_convidados.count or 0
            except Exception as e:
                print(f"Erro ao consultar estatísticas de convidados (com filtro de período): {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erro ao carregar as estatísticas gerais."
                )
    else:
        try:
            resposta_convidados = supabase.table("convidados")\
                .select("id", count="exact")\
                .execute()
            total_convidados_confirmados = resposta_convidados.count or 0
        except Exception as e:
            print(f"Erro ao consultar estatísticas de convidados: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao carregar as estatísticas gerais."
            )

    return {
        "total_agendamentos": total_agendamentos,
        "total_convidados_estimados": total_convidados_estimados,
        "total_convidados_confirmados": total_convidados_confirmados,
    }
