import os
import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone
from supabase import create_client, Client

from backend.app.services.auth_service import obter_funcionario_autenticado

router = APIRouter(prefix="/convidados", tags=["Convidados"])

# Inicializa o client do Supabase puxando as variáveis do ambiente (.env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não foram configuradas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Modelo Pydantic para validar o Payload do Front-end
class ConfirmarPresencaSchema(BaseModel):
    lead_id: str = Field(..., description="ID do aniversariante vindo do CRM")
    nome_completo: str = Field(..., min_length=3)
    cpf: str = Field(..., min_length=11, max_length=11, description="Apenas os 11 dígitos do CPF")
    whatsapp: str = Field(..., min_length=10, max_length=11, description="Apenas os números com DDD")
    data_nascimento: date

# Modelo Pydantic do payload enviado pelo app da portaria ao bipar o QR Code
class ValidarQrSchema(BaseModel):
    qr_code_token: str = Field(..., description="Token UUID v4 lido do QR Code do convidado")

# 2. Endpoint POST que o formulário chama
@router.post("/confirmar", status_code=status.HTTP_201_CREATED)
async def confirmar_presenca(payload: ConfirmarPresencaSchema):
    try:
        dados_convidado = {
            "lead_id": payload.lead_id,
            "nome_completo": payload.nome_completo,
            "cpf": payload.cpf,
            "whatsapp": payload.whatsapp,
            "data_nascimento": str(payload.data_nascimento)
        }
        
        # Executa o insert no Supabase
        resposta = supabase.table("convidados").insert(dados_convidado).execute()
        
        # CHECAGEM 1: Algumas versões do Supabase não lançam exceção,
        # elas retornam o erro estruturado no objeto de resposta.
        if hasattr(resposta, 'error') and resposta.error is not None:
            erro_msg = str(resposta.error).lower()
            if "23505" in erro_msg or "unique" in erro_msg or "already exists" in erro_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este CPF já está cadastrado nesta lista de aniversário."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro no banco de dados: {resposta.error}"
            )

        # CHECAGEM 2: Se não retornou dados e não mapeou erro acima
        if not resposta.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao salvar confirmação no banco de dados."
            )

        # O qr_code_token é gerado pelo próprio Supabase (DEFAULT gen_random_uuid()),
        # então já volta preenchido na representação do registro recém-inserido.
        convidado_criado = resposta.data[0]
        qr_code_token = convidado_criado.get("qr_code_token")

        if not qr_code_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Convidado cadastrado, mas o QR Code não foi gerado. Contate o suporte."
            )

        return {"qr_code_token": qr_code_token}

    except HTTPException as http_exec:
        # Se o erro foi lançado por nós mesmos nas checagens acima, repassa ele
        raise http_exec

    except Exception as e:
        # CHECAGEM 3: Trata caso o banco lance uma exceção nativa do Python/Postgrest
        erro_str = str(e).lower()
        repr_erro = repr(e).lower()

        if "23505" in erro_str or "unique" in erro_str or "already exists" in erro_str or "unique" in repr_erro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este CPF já está cadastrado nesta lista de aniversário."
            )

        print(f"Erro interno não mapeado no Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Houve um problema interno ao salvar seus dados. Por favor, tente novamente em alguns instantes."
        )

# Busca o aniversariante responsável pela lista (kommo_lead_id == lead_id) e
# indica se o CPF do convidado lido é o mesmo do aniversariante daquela lista.
# Usado tanto por /validar-qr quanto por /buscar-cpf, para não duplicar a
# mesma consulta de "junção" nas duas rotas.
#
# Retorna uma tupla (aniversariante, e_aniversariante):
#   - aniversariante: dict com nome_completo/cpf do aniversariante da lista,
#     ou None se a lista não for encontrada.
#   - e_aniversariante: True somente se os dois CPFs existirem e forem iguais.
def _buscar_aniversariante_da_lista(lead_id: str | None, cpf_convidado: str | None):
    if not lead_id:
        return None, False

    try:
        resposta = supabase.table("aniversariantes")\
            .select("nome_completo, cpf")\
            .eq("kommo_lead_id", lead_id)\
            .maybe_single()\
            .execute()
    except Exception as e:
        print(f"Erro ao buscar aniversariante da lista {lead_id}: {e}")
        return None, False

    dados_aniversariante = getattr(resposta, "data", None) if resposta else None

    if not dados_aniversariante:
        return None, False

    cpf_aniversariante = dados_aniversariante.get("cpf")
    e_aniversariante = bool(cpf_aniversariante) and bool(cpf_convidado) and cpf_aniversariante == cpf_convidado

    aniversariante = {
        "nome_completo": dados_aniversariante.get("nome_completo"),
        "cpf": cpf_aniversariante,
    }

    return aniversariante, e_aniversariante


# 3. Endpoint que o app da portaria chama ao bipar o QR Code do convidado.
#    A resposta sempre volta com HTTP 200: quem diferencia acesso liberado ou
#    negado é o campo "status" do corpo, no mesmo padrão já usado nos webhooks
#    da Kommo (evita misturar HTTP status de transporte com regra de negócio).
@router.post("/validar-qr", dependencies=[Depends(obter_funcionario_autenticado)])
async def validar_qr_code(payload: ValidarQrSchema):
    try:
        resposta = supabase.table("convidados")\
            .select("lead_id, nome_completo, cpf, utilizado, data_hora_entrada")\
            .eq("qr_code_token", payload.qr_code_token)\
            .maybe_single()\
            .execute()
    except Exception as e:
        print(f"Erro ao consultar QR Code na portaria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao validar o QR Code na portaria."
        )

    convidado = getattr(resposta, "data", None) if resposta else None

    # Sinal Vermelho: QR Code não corresponde a nenhum convidado cadastrado
    if not convidado:
        return {
            "status": "INVALIDO",
            "mensagem": "QR Code inválido ou não encontrado nesta lista."
        }

    aniversariante, e_aniversariante = _buscar_aniversariante_da_lista(
        convidado.get("lead_id"), convidado.get("cpf")
    )

    # Sinal Vermelho: QR Code já foi utilizado em uma entrada anterior
    if convidado.get("utilizado"):
        return {
            "status": "JA_UTILIZADO",
            "mensagem": "Este QR Code já foi utilizado.",
            "convidado": {
                "nome_completo": convidado["nome_completo"],
                "cpf": convidado["cpf"],
            },
            "data_hora_entrada": convidado.get("data_hora_entrada"),
            "e_aniversariante": e_aniversariante,
            "aniversariante": aniversariante,
        }

    # Sinal Verde: primeira leitura válida -> marca a entrada e libera o acesso
    data_hora_entrada = datetime.now(timezone.utc).isoformat()

    try:
        supabase.table("convidados")\
            .update({"utilizado": True, "data_hora_entrada": data_hora_entrada})\
            .eq("qr_code_token", payload.qr_code_token)\
            .execute()
    except Exception as e:
        print(f"Erro ao registrar entrada do convidado na portaria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao registrar a entrada do convidado."
        )

    return {
        "status": "LIBERADO",
        "mensagem": "Entrada liberada com sucesso.",
        "convidado": {
            "nome_completo": convidado.get("nome_completo"),
            "cpf": convidado.get("cpf"),
        },
        "data_hora_entrada": data_hora_entrada,
        "e_aniversariante": e_aniversariante,
        "aniversariante": aniversariante,
    }


# 4. Endpoint de contingência usado pelo app da portaria quando o convidado
#    chega sem o QR Code em mãos (busca manual por CPF).
@router.get("/buscar-cpf/{cpf}", dependencies=[Depends(obter_funcionario_autenticado)])
async def buscar_convidado_por_cpf(cpf: str):
    # Limpa pontos e traço para consultar sempre pelos 11 dígitos puros,
    # do mesmo jeito que o CPF é gravado no cadastro (POST /confirmar).
    cpf_limpo = re.sub(r"\D", "", cpf)

    try:
        resposta = supabase.table("convidados")\
            .select("id, lead_id, nome_completo, cpf, whatsapp, qr_code_token, utilizado, data_hora_entrada")\
            .eq("cpf", cpf_limpo)\
            .order("confirmado_em", desc=True)\
            .limit(1)\
            .execute()
    except Exception as e:
        print(f"Erro ao buscar convidado por CPF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar o convidado pelo CPF."
        )

    convidados_encontrados = resposta.data or []

    if not convidados_encontrados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convidado não encontrado com este CPF."
        )

    convidado = convidados_encontrados[0]
    aniversariante, e_aniversariante = _buscar_aniversariante_da_lista(
        convidado.get("lead_id"), convidado.get("cpf")
    )

    return {
        **convidado,
        "e_aniversariante": e_aniversariante,
        "aniversariante": aniversariante,
    }


@router.get("/resumo/{lead_id}")
async def obter_resumo_aniversariante(lead_id: str):
    try:
        # Busca todas as linhas da nossa View analítica para o aniversariante específico
        resposta = supabase.table("vw_analytics_convidados").select("*").eq("lead_id", lead_id).execute()
        
        convidados = resposta.data
        total_confirmados = len(convidados)
        
        if total_confirmados == 0:
            return {
                "lead_id": lead_id,
                "total_confirmados": 0,
                "mensagem": "Nenhum convidado confirmado para esta lista ainda.",
                "metricas": {}
            }
            
        # 1. Agrupando por Faixa Etária (Métrica de BI)
        resumo_faixa_etaria = {}
        # 2. Agrupando por Período de Confirmação
        resumo_periodo = {}
        
        for c in convidados:
            fx = c.get("faixa_etaria")
            resumo_faixa_etaria[fx] = resumo_faixa_etaria.get(fx, 0) + 1
            
            per = c.get("periodo_confirmacao")
            resumo_periodo[per] = resumo_periodo.get(per, 0) + 1
            
        return {
            "lead_id": lead_id,
            "total_confirmados": total_confirmados,
            "metricas": {
                "por_faixa_etaria": resumo_faixa_etaria,
                "por_periodo_do_dia": resumo_periodo
            }
        }
        
    except Exception as e:
        print(f"Erro ao extrair relatório: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar os indicadores analíticos da lista."
        )