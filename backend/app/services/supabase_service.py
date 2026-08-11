"""
Camada de integração com o Supabase Storage usada pelo gerador de flyers.

Centraliza o upload do flyer final (bucket `fotos-aniversariantes`) e a
busca opcional de molduras versionadas no próprio Storage. Quem decide o
fallback quando uma moldura não existe no Storage é o flyer_generator, que
tenta os assets locais antes de desistir da camada decorativa.
"""

import logging
import os

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Inicializa o client do Supabase puxando as variáveis do ambiente (.env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não foram configuradas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_FOTOS_ANIVERSARIANTES = "fotos-aniversariantes"

# Subpasta opcional dentro do mesmo bucket, usada para versionar molduras
# oficiais direto no Storage (sem precisar de deploy para trocar a arte).
PASTA_MOLDURAS_NO_STORAGE = "molduras"

# Nome de arquivo sugerido quando o cliente baixa o flyer pelo botão do
# Salesbot (ver upload_flyer). Não afeta o nome do objeto no bucket — só o
# nome sugerido pelo navegador/WhatsApp na hora de salvar o download.
NOME_DOWNLOAD_FLYER = "flyer-paparazzi-gold-bar.jpg"


def upload_flyer(flyer_bytes: bytes, kommo_lead_id: str) -> str:
    """
    Envia o flyer .jpg já compilado para o Supabase Storage e retorna a URL pública.

    Args:
        flyer_bytes: Bytes do flyer gerado por flyer_generator.generate_flyer.
        kommo_lead_id: ID do lead no Kommo, usado para nomear o arquivo de
            forma determinística (ex.: flyer_111222334.jpg).

    Nome determinístico + x-upsert=true: se o webhook do Kommo reenviar o
    mesmo lead (entrega duplicada, retry), o upload SOBRESCREVE o mesmo
    objeto em vez de criar um arquivo novo a cada chamada — sem isso, cada
    reentrega empilhava um flyer_{lead_id}_{uuid} diferente no bucket.

    A URL devolvida inclui `?download=<nome>` (decisão de 10/08/2026):
    validado que o Supabase Storage responde com `Content-Disposition:
    attachment` quando esse parâmetro está presente — sem ele, o link
    enviado pelo botão do Salesbot abria a imagem direto no navegador do
    cliente (útil só pra visualizar, exigindo print — que perde qualidade —
    pra guardar o arquivo). Com o parâmetro, o clique já baixa o arquivo
    original, na resolução exata que o Pillow gerou.

    Returns:
        URL pública do flyer (com `?download`) recém-enviado ao bucket
        fotos-aniversariantes.
    """
    nome_arquivo = f"flyer_{kommo_lead_id}.jpg"

    supabase.storage.from_(BUCKET_FOTOS_ANIVERSARIANTES).upload(
        path=nome_arquivo,
        file=flyer_bytes,
        file_options={"content-type": "image/jpeg", "x-upsert": "true"},
    )

    url_publica = supabase.storage.from_(BUCKET_FOTOS_ANIVERSARIANTES).get_public_url(nome_arquivo)
    url_publica = f"{url_publica}?download={NOME_DOWNLOAD_FLYER}"
    logger.info("Flyer enviado ao Supabase Storage: %s", nome_arquivo)

    return url_publica


def upload_foto_perfil(foto_bytes: bytes, kommo_lead_id: str) -> str:
    """
    Envia a foto ORIGINAL do aniversariante (baixada do Custom Field de
    arquivo do Kommo, ID 2068458, antes de qualquer composição do flyer)
    para o Supabase Storage e retorna a URL pública.

    Salva num arquivo separado do flyer (mesmo nome determinístico + regra
    de x-upsert=true) porque essa foto crua tem dois consumidores distintos
    do fluxo: 1) insumo do Pillow para montar o flyer, 2) exibida no
    formulário de cadastro do convidado (Flutter Web) via
    aniversariantes.foto_perfil_url.

    Args:
        foto_bytes: Bytes da foto original, sem nenhum processamento.
        kommo_lead_id: ID do lead no Kommo, usado para nomear o arquivo de
            forma determinística (ex.: foto_perfil_111222334.jpg).

    Returns:
        URL pública da foto original recém-enviada ao bucket fotos-aniversariantes.
    """
    nome_arquivo = f"foto_perfil_{kommo_lead_id}.jpg"

    supabase.storage.from_(BUCKET_FOTOS_ANIVERSARIANTES).upload(
        path=nome_arquivo,
        file=foto_bytes,
        file_options={"content-type": "image/jpeg", "x-upsert": "true"},
    )

    url_publica = supabase.storage.from_(BUCKET_FOTOS_ANIVERSARIANTES).get_public_url(nome_arquivo)
    logger.info("Foto original do aniversariante enviada ao Supabase Storage: %s", nome_arquivo)

    return url_publica


def buscar_moldura_do_storage(nome_arquivo: str) -> bytes | None:
    """
    Busca os bytes de uma moldura salva em `molduras/<nome_arquivo>` dentro
    do bucket fotos-aniversariantes.

    Args:
        nome_arquivo: nome do PNG da moldura, ex.: "moldura_padrao.png".

    Returns:
        Bytes do PNG se ele existir no Storage, ou None se não existir —
        quem chama decide o fallback (assets locais ou seguir sem moldura).
    """
    caminho = f"{PASTA_MOLDURAS_NO_STORAGE}/{nome_arquivo}"

    try:
        return supabase.storage.from_(BUCKET_FOTOS_ANIVERSARIANTES).download(caminho)
    except Exception as e:
        logger.info(
            "Moldura '%s' não encontrada no Supabase Storage (%s). Tentando assets locais.",
            nome_arquivo, e,
        )
        return None
