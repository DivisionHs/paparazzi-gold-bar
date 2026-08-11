"""
Camada de integração com a API REST v4 do Kommo CRM.

Estratégia de Consulta Ativa (ver CLAUDE.md 4.2): o webhook disparado pelo
Kommo em /webhooks/kommo funciona só como sinalizador leve (carrega o
lead_id e o status_id da etapa) — os valores dos Custom Fields não são mais
lidos do corpo do próprio webhook, porque o payload do Salesbot podia chegar
com campos vazios quando a gravação ainda não tinha propagado do lado do
Kommo no exato instante do disparo. Este módulo faz o GET ativo que busca o
estado mais atual possível do Lead direto na fonte.

NOTA sobre o Custom Field de arquivo (06/08/2026): o endpoint oficial de
arquivos (GET /api/v4/files/{uuid}) devolve 404 nesta conta — não é usado.
O dict de metadados do Custom Field também não traz nenhuma URL pronta em
lugar nenhum — só as peças usadas para MONTAR o link de download do CDN do
Kommo (padrão descoberto empiricamente): base fixa do drive da conta +
file_uuid + version_uuid + file_name. Ver montar_url_cdn_arquivo().
"""

import logging
from urllib.parse import quote

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Base fixa observada no CDN de arquivos desta conta do Kommo — inclui um
# identificador do "drive"/storage da conta que se manteve igual entre
# arquivos diferentes nos testes. Se um dia essa base passar a variar (outra
# conta, outra região), essa constante precisa ser revista.
_BASE_CDN_ARQUIVOS_KOMMO = "https://drive-g.kommo.com/download/662da799-7bfe-52a0-af12-661479954047"

# As 3 chaves do dict de metadados do Custom Field de arquivo necessárias
# para montar a URL de download — ver montar_url_cdn_arquivo().
_CHAVES_METADADOS_ARQUIVO = ("file_uuid", "version_uuid", "file_name")


def _montar_url_lead(lead_id: str) -> str:
    return f"https://{settings.KOMMO_SUBDOMAIN}.kommo.com/api/v4/leads/{lead_id}"


def montar_url_cdn_arquivo(metadados: dict) -> str | None:
    """
    Monta a URL de download direto do CDN do Kommo a partir do dict de
    metadados de um Custom Field de arquivo (ex.: "Foto do aniversariante").

    Padrão descoberto empiricamente em 06/08/2026 (a API de arquivos
    devolve 404 nesta conta, e o dict não traz nenhuma URL pronta):

        {base_fixa}/{file_uuid}/{version_uuid}/{file_name}

    Ex.: https://drive-g.kommo.com/download/662da799-.../c2a52ead-.../6ea1d1a9-.../file_4.jpg

    Nunca faz nenhuma chamada de rede — só concatena o que já foi obtido em
    buscar_custom_fields_lead(). `file_name` é URL-encoded antes de entrar
    na URL, para não quebrar em nomes de arquivo com espaço ou acento.

    Returns:
        A URL montada, ou None se `metadados` não for um dict ou se faltar
        alguma das 3 chaves obrigatórias (file_uuid, version_uuid,
        file_name) — nesse caso, loga exatamente o que faltou.
    """
    if not isinstance(metadados, dict):
        logger.error("💥 Valor do Custom Field de arquivo não é um dict de metadados: %r", metadados)
        return None

    faltando = [chave for chave in _CHAVES_METADADOS_ARQUIVO if not metadados.get(chave)]
    if faltando:
        logger.error(
            "💥 Dict de metadados do arquivo veio incompleto — faltando: %s. Metadados recebidos: %r",
            ", ".join(faltando), metadados,
        )
        return None

    file_uuid = metadados["file_uuid"]
    version_uuid = metadados["version_uuid"]
    file_name = quote(str(metadados["file_name"]), safe="")

    return f"{_BASE_CDN_ARQUIVOS_KOMMO}/{file_uuid}/{version_uuid}/{file_name}"


async def buscar_custom_fields_lead(lead_id: str) -> dict[str, str | dict] | None:
    """
    Busca, via GET direto em /api/v4/leads/{lead_id}, os valores ATUAIS dos
    Custom Fields do Lead — chamada logo após o webhook de mudança de etapa
    confirmar que o Lead chegou em "PROCESSANDO FLYER" (status_id 109983139).

    Nunca lança exceção para quem chamou: qualquer oscilação da API do CRM
    (timeout, erro HTTP, credencial ausente) é registrada em log e resulta
    em `None`, para que a rota do webhook ignore o processamento com
    segurança em vez de seguir com dados incompletos.

    Returns:
        dict {field_id (str): valor} com todos os Custom Fields do Lead, ou
        None se a consulta falhar. Campos de texto/data/número vêm como
        `str`; Custom Fields de arquivo (ex.: "Foto do aniversariante")
        vêm como `dict` de metadados (`file_uuid`, `version_uuid`,
        `file_name`, ...) — preservado intacto, sem conversão para string,
        para que quem chamar possa montar a URL de download via
        `montar_url_cdn_arquivo()`.
    """
    if not settings.KOMMO_SUBDOMAIN or not settings.KOMMO_LONG_LIVED_TOKEN:
        logger.warning(
            "⚠️ KOMMO_SUBDOMAIN ou KOMMO_LONG_LIVED_TOKEN não configurados no "
            "ambiente. Não é possível consultar o Lead %s.",
            lead_id,
        )
        return None

    url = _montar_url_lead(lead_id)
    headers = {"Authorization": f"Bearer {settings.KOMMO_LONG_LIVED_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.get(url, headers=headers)
            resposta.raise_for_status()

        dados = resposta.json()

        custom_fields: dict[str, str | dict] = {}
        for campo in dados.get("custom_fields_values") or []:
            field_id = campo.get("field_id")
            valores = campo.get("values") or []
            if field_id is None or not valores:
                continue

            valor_bruto = valores[0].get("value")
            custom_fields[str(field_id)] = valor_bruto if isinstance(valor_bruto, dict) else str(valor_bruto)

        logger.info("📡 Consulta ativa ao Lead %s retornou %d Custom Field(s).", lead_id, len(custom_fields))
        return custom_fields

    except httpx.HTTPStatusError as erro_http:
        logger.error(
            "💥 Kommo CRM recusou a consulta do Lead %s (HTTP %s): %s",
            lead_id, erro_http.response.status_code, erro_http.response.text,
        )
        return None
    except httpx.RequestError as erro_conexao:
        logger.error(
            "💥 Falha de conexão/timeout ao consultar o Lead %s no Kommo CRM: %s",
            lead_id, erro_conexao,
        )
        return None
    except Exception as erro_inesperado:
        logger.error(
            "💥 Erro inesperado ao consultar o Lead %s no Kommo CRM: %s",
            lead_id, erro_inesperado,
        )
        return None


async def atualizar_custom_fields_lead(lead_id: str, campos: dict[str, str]) -> bool:
    """
    Grava (PATCH em /api/v4/leads/{lead_id}) o valor de um ou mais Custom
    Fields de texto do Lead. Primeira função de ESCRITA do módulo — usada
    para devolver ao Kommo a URL do flyer gerado (Custom Field "URL do
    Flyer", ID 2069404), assim que o backend termina de processá-lo, para
    que o Salesbot consiga referenciar esse valor via `{{lead.cf.<id>}}`
    numa mensagem/botão (ver CLAUDE.md 4.2 — decisão de 10/08/2026).

    Args:
        lead_id: ID do Lead no Kommo.
        campos: dict {field_id (str ou int): valor (str)} — cada entrada
            vira um Custom Field de texto sobrescrito no Lead.

    Nunca lança exceção para quem chamou: qualquer oscilação da API do CRM
    (timeout, erro HTTP, credencial ausente) é registrada em log e resulta
    em `False` — quem chama trata isso como best-effort (não deve travar
    nem desfazer o cadastro já salvo no Supabase por causa disso).

    Returns:
        True se o Kommo confirmou a gravação (HTTP 200), False caso contrário.
    """
    if not settings.KOMMO_SUBDOMAIN or not settings.KOMMO_LONG_LIVED_TOKEN:
        logger.warning(
            "⚠️ KOMMO_SUBDOMAIN ou KOMMO_LONG_LIVED_TOKEN não configurados no "
            "ambiente. Não é possível gravar Custom Field(s) no Lead %s.",
            lead_id,
        )
        return False

    url = _montar_url_lead(lead_id)
    headers = {"Authorization": f"Bearer {settings.KOMMO_LONG_LIVED_TOKEN}"}
    payload = {
        "custom_fields_values": [
            {"field_id": int(field_id), "values": [{"value": valor}]}
            for field_id, valor in campos.items()
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.patch(url, headers=headers, json=payload)
            resposta.raise_for_status()

        logger.info("✏️ Custom Field(s) %s gravado(s) no Lead %s.", list(campos.keys()), lead_id)
        return True

    except httpx.HTTPStatusError as erro_http:
        logger.error(
            "💥 Kommo CRM recusou a gravação de Custom Field(s) no Lead %s (HTTP %s): %s",
            lead_id, erro_http.response.status_code, erro_http.response.text,
        )
        return False
    except httpx.RequestError as erro_conexao:
        logger.error(
            "💥 Falha de conexão/timeout ao gravar Custom Field(s) no Lead %s no Kommo CRM: %s",
            lead_id, erro_conexao,
        )
        return False
    except Exception as erro_inesperado:
        logger.error(
            "💥 Erro inesperado ao gravar Custom Field(s) no Lead %s no Kommo CRM: %s",
            lead_id, erro_inesperado,
        )
        return False
