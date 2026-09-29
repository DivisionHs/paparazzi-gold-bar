"""
Camada de autenticação de funcionários (Supabase Auth) — usada só nas rotas
operacionais/staff (Portaria, painel de aniversariantes do dia). O fluxo do
convidado (formulário público, handshake por token) nunca passa por aqui.

Validação feita chamando client.auth.get_user(token) do próprio SDK
supabase-py já usado em todo o resto do backend — por baixo dos panos isso
é um GET em /auth/v1/user na API do Supabase, então não precisa de nenhum
segredo novo (ex.: SUPABASE_JWT_SECRET): reaproveita SUPABASE_URL/SUPABASE_KEY
que já existem. Também garante que a validação reflete o estado real da
conta na hora (se um funcionário for desativado no Supabase, o acesso cai
na próxima chamada) — mesmo princípio da Estratégia de Consulta Ativa já
usada com o Kommo (ver CLAUDE.md 4.2).

Não há RLS por trás disso: o backend continua consultando as tabelas com a
mesma chave anônima de sempre, para qualquer funcionário logado. O Supabase
Auth aqui serve só de gate de acesso às rotas do FastAPI.
"""

import os

from fastapi import Depends, HTTPException, Request, status
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não foram configuradas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def obter_funcionario_autenticado(request: Request) -> dict:
    """
    Dependency do FastAPI para rotas staff-only. Exige um header
    `Authorization: Bearer <access_token>` com um token de sessão válido do
    Supabase Auth (gerado no login do app pelo funcionário). Levanta 401 em
    pt-BR se o header estiver ausente ou o token for inválido/expirado.

    Retorna o dict do usuário autenticado (útil, no futuro, para registrar
    qual funcionário validou cada entrada na Portaria — não usado ainda).
    """
    cabecalho = request.headers.get("Authorization", "")

    if not cabecalho.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não informada. Faça login novamente.",
        )

    token = cabecalho[len("Bearer "):].strip()

    try:
        resposta = supabase.auth.get_user(token)
    except Exception as e:
        print(f"Erro ao validar sessão do funcionário: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    usuario = getattr(resposta, "user", None) if resposta else None

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    metadata = getattr(usuario, "user_metadata", None) or {}
    # Papel do funcionário (decisão de 29/09/2026, ver CLAUDE.md 4.10):
    # gravado em user_metadata.role na criação/atualização da conta (script
    # administrativo pontual, mesmo padrão da 1ª conta criada em 18/08/2026 —
    # ver 4.7). Sem role gravado, cai no papel mais restrito ("porteiro") por
    # segurança, em vez de assumir acesso de admin por omissão.
    papel = metadata.get("role") or "porteiro"

    return {"id": usuario.id, "email": usuario.email, "role": papel}


async def exigir_admin(funcionario: dict = Depends(obter_funcionario_autenticado)) -> dict:
    """
    Dependency staff-only mais restrita: além de exigir sessão válida (via
    `obter_funcionario_autenticado`), exige que o papel gravado no
    user_metadata da conta seja "admin". Usada nas rotas que só o login
    administrativo deve enxergar (ex.: dashboard de estatísticas gerais —
    ver CLAUDE.md 4.10). Levanta 403 (não 401 — a sessão em si é válida, só
    não tem permissão) em pt-BR se o papel não for admin.
    """
    if funcionario.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este login não tem permissão para acessar esta área.",
        )
    return funcionario
