import os
import uuid  # Biblioteca nativa do Python para gerar tokens únicos (UUIDs)
import logging
from datetime import datetime
import httpx  # Necessário para consultar a API do Kommo e baixar a foto do Custom Field
from fastapi import APIRouter, BackgroundTasks, Request, status, HTTPException
from dotenv import load_dotenv
from supabase import create_client, Client  # Certifique-se de ter o supabase instalado no .venv

from backend.app.services import flyer_generator, supabase_service, kommo_service

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Configurações do Supabase extraídas do seu arquivo .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializa o cliente do Supabase
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Etapa (status_id) oficial do funil no Kommo — "PROCESSANDO FLYER": o
# Salesbot só move o Lead para cá depois de já ter coletado, direto do
# cliente, os 5 dados obrigatórios da reserva (ver CAMPOS_OBRIGATORIOS
# abaixo). O webhook disparado nesta etapa é o único disparo do fluxo — não
# há mais coleta incremental via chat.
try:
    TARGET_STATUS_ID = int(os.getenv("KOMMO_TARGET_STATUS_ID", 109983139))
except (ValueError, TypeError):
    TARGET_STATUS_ID = 109983139  # fallback seguro caso o valor no .env seja inválido ou ausente

# Modo de teste: permite ignorar a checagem de status_id durante os testes do
# "Novo funil teste" no Kommo (ngrok), já que o funil de teste usa etapas
# diferentes da etapa de produção. Mantenha "false" em produção.
KOMMO_WEBHOOK_TEST_MODE = os.getenv("KOMMO_WEBHOOK_TEST_MODE", "false").lower() == "true"

# IDs dos Custom Fields que o Salesbot preenche diretamente no Lead antes de
# mover o status para TARGET_STATUS_ID. O backend não escreve em nenhum
# deles — e, desde a Estratégia de Consulta Ativa (ver CLAUDE.md 4.2), também
# não lê mais esses valores do corpo do próprio webhook: o webhook é só o
# sinalizador (lead_id + status_id); os valores frescos são buscados via GET
# direto na API do Kommo (kommo_service.buscar_custom_fields_lead), para
# eliminar o atraso de persistência que causava campos vazios no payload do
# Salesbot.
# NOTA (decisão de 05/08/2026): o cálculo automático de "Data da reserva" a
# partir de um Custom Field "Nome da semana" (ID 2068768) foi descontinuado
# nesta fase do MVP — ver docs/diario_projeto.md para o registro da decisão
# e a ideia de retomar essa automação numa Fase 2.
CAMPO_DATA_DA_RESERVA_ID = "2068460"
CAMPO_HORARIO_ID = "2068854"
CAMPO_ESTIMATIVA_CONVIDADOS_ID = "2068456"
CAMPO_NOME_FLYER_ID = "2068452"
CAMPO_FOTO_ID = "2068458"

# Custom Fields de ESCRITA (decisão de 10/08/2026): o backend grava a URL do
# flyer de volta no Lead depois de gerá-lo, para que o Salesbot consiga
# mostrar esse link ao cliente via merge tag (`{{lead.cf.2069404}}`) numa
# mensagem/botão — validado empiricamente que a leitura de Custom Field por
# ID numérico funciona nesta conta (ver CLAUDE.md 4.2). "Link do Formulário"
# (2069406) já existe no Kommo mas ainda não é escrito por aqui — o domínio
# do formulário de convidados (app-paparazzi.vercel.app) ainda vai passar
# por ajustes numa etapa futura.
CAMPO_URL_FLYER_ID = "2069404"

# Nomes amigáveis dos 5 campos obrigatórios, usados nos logs de diagnóstico e
# na checagem de coleta completa. A ordem aqui é só para leitura humana nos
# logs — o Salesbot é quem garante a ordem real de coleta com o cliente.
CAMPOS_OBRIGATORIOS = {
    CAMPO_DATA_DA_RESERVA_ID: "Data da reserva",
    CAMPO_HORARIO_ID: "Horário da reserva",
    CAMPO_ESTIMATIVA_CONVIDADOS_ID: "Estimativa de convidados",
    CAMPO_NOME_FLYER_ID: "Nome do flyer",
    CAMPO_FOTO_ID: "Foto do aniversariante",
}


def converter_valor_data_kommo(valor: str) -> str | None:
    """
    Converte o valor bruto do Custom Field "Data da reserva" (tipo `date`)
    para o formato "AAAA-MM-DD" esperado pela coluna aniversariantes.data_reserva.

    O Kommo pode entregar esse valor de formas diferentes dependendo de como
    o passo de Webhook do Salesbot foi montado: como timestamp Unix (padrão
    da API REST) ou já como texto "DD/MM/AAAA"/"DD.MM.AAAA". Tenta as
    variações mais prováveis, em ordem; se nenhuma bater, loga um aviso e
    devolve None (o INSERT segue sem essa coluna em vez de falhar por causa
    só da formatação da data).
    """
    if not valor:
        return None

    valor = valor.strip()

    if valor.isdigit():
        try:
            return datetime.fromtimestamp(int(valor)).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass

    for formato in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue

    logger.warning(f"⚠️ Não foi possível interpretar o valor da Data da reserva recebido do Kommo: '{valor}'.")
    return None


def converter_estimativa_convidados_kommo(valor: str | None) -> int | None:
    """
    Converte o valor bruto do Custom Field "Estimativa de Convidados" (ID
    2068456, ex.: "20") para inteiro. Campo não crítico para o cadastro em
    si (só alimenta o painel de aniversariantes do dia) — se vier vazio ou
    num formato inesperado, loga um aviso e devolve None em vez de derrubar
    o upsert por causa dele, mesmo princípio já usado em
    converter_valor_data_kommo.
    """
    if not valor:
        return None

    try:
        return int(valor.strip())
    except ValueError:
        logger.warning(f"⚠️ Não foi possível interpretar a Estimativa de Convidados recebida do Kommo: '{valor}'.")
        return None


def formatar_valor_para_log(valor) -> str:
    """
    Formata o valor de um Custom Field para exibição legível nos logs de
    diagnóstico. Custom Fields de arquivo (dict com file_uuid/file_name)
    ficam ilegíveis se apenas jogados como %s — aqui viram um resumo curto.
    """
    if isinstance(valor, dict):
        return f"[arquivo: {valor.get('file_name', '?')} | file_uuid={valor.get('file_uuid', '?')}]"
    return str(valor) if valor else "—"


def eh_url_http_valida(valor: str | None) -> bool:
    """
    Validação mínima para o valor do Custom Field "Foto do aniversariante"
    antes de usá-lo numa requisição HTTP.

    O `httpx` exige o prefixo `http://`/`https://` explícito e lança
    `httpx.InvalidURL` (mensagem: "Request URL is missing an 'http://' or
    'https://' protocol.") se o valor vier vazio, relativo ou malformado —
    o que pode acontecer se o Custom Field de arquivo no Kommo devolver algo
    diferente de uma URL pública completa (ex.: um identificador interno em
    vez do link do arquivo). Checar isso antes evita que um valor inesperado
    vindo do Kommo derrube a rota inteira com 500.
    """
    return bool(valor) and valor.strip().lower().startswith(("http://", "https://"))


async def finalizar_cadastro_aniversariante(
    lead_id: str,
    nome_aniversariante: str,
    foto_bytes: bytes,
    data_reserva: str | None,
    horario_reserva: str | None = None,
    estimativa_convidados_raw: str | None = None,
) -> dict:
    """
    Único ponto de gravação do fluxo: envia ao Supabase Storage os DOIS
    arquivos do aniversariante — a foto original enviada pelo cliente
    (Custom Field 2068458) e o flyer construído a partir dela — e realiza o
    único upsert na tabela `aniversariantes`. Disparada pela rota
    /webhooks/kommo assim que a consulta ativa à API do Kommo confirma que
    os 5 campos obrigatórios já estão preenchidos no Lead, e só depois que
    a rota já confirmou (ver receber_webhook_kommo) que este lead_id ainda
    não tinha registro.

    Os dois uploads usam nomes determinísticos por lead_id (ver
    supabase_service.upload_foto_perfil/upload_flyer) — mesmo que esta
    função rode mais de uma vez para o mesmo lead, os arquivos são
    sobrescritos em vez de empilhados no bucket.
    """
    url_foto_perfil = supabase_service.upload_foto_perfil(foto_bytes, str(lead_id))
    logger.info(f"📤 Foto original do aniversariante enviada ao Storage! URL Pública: {url_foto_perfil}")

    try:
        flyer_bytes = flyer_generator.generate_flyer(
            foto_bytes, nome_aniversariante, data_reserva=data_reserva, horario=horario_reserva
        )
        url_publica_flyer = supabase_service.upload_flyer(flyer_bytes, str(lead_id))
        logger.info(f"🎨 Flyer gerado e enviado ao Storage! URL Pública: {url_publica_flyer}")
    except Exception as erro_flyer:
        logger.error(f"💥 Falha ao gerar/enviar o flyer, usando a foto original no lugar dele: {erro_flyer}")
        url_publica_flyer = url_foto_perfil

    token_unico = str(uuid.uuid4())
    dados_aniversariante = {
        "kommo_lead_id": str(lead_id),
        "nome_completo": nome_aniversariante,
        "foto_url": url_publica_flyer,
        "foto_perfil_url": url_foto_perfil,
        "token_exclusivo": token_unico,
    }
    if data_reserva:
        dados_aniversariante["data_reserva"] = data_reserva

    # Horário e estimativa de convidados: antes só usados pra desenhar o
    # flyer e descartados (ver diario_projeto.md, registro de 17/08/2026) —
    # agora também persistidos, pra alimentar o painel de aniversariantes do
    # dia. Reaproveita a mesma normalização já usada no flyer
    # (flyer_generator.formatar_horario_exibicao, "12" -> "12:00") pra não
    # duplicar essa lógica.
    horario_normalizado = flyer_generator.formatar_horario_exibicao(horario_reserva)
    if horario_normalizado:
        dados_aniversariante["horario_reserva"] = horario_normalizado

    estimativa_convidados = converter_estimativa_convidados_kommo(estimativa_convidados_raw)
    if estimativa_convidados is not None:
        dados_aniversariante["estimativa_convidados"] = estimativa_convidados

    try:
        supabase_client.table("aniversariantes").upsert(
            dados_aniversariante,
            on_conflict="kommo_lead_id",
        ).execute()
        logger.info(f"💾 Cadastro do aniversariante '{nome_aniversariante}' registrado no Supabase (Lead {lead_id}).")
    except Exception as db_err:
        logger.error(f"💥 Erro ao registrar o aniversariante no Supabase: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao registrar o aniversariante no banco de dados."
        )

    link_formulario = f"https://paparazzigoldbar.com.br/cadastro?token={token_unico}"
    logger.info(f"🔗 Link gerado para o cliente preencher: {link_formulario}")

    # Devolve a URL do flyer ao Kommo assim que o cadastro já está salvo no
    # Supabase (fonte da verdade primeiro) — o Salesbot referencia esse
    # Custom Field via merge tag para mostrar o link ao cliente. Best-effort:
    # se o Kommo recusar/falhar, só loga — não desfaz nada do que já foi
    # salvo, e a próxima reentrega do webhook não vai regravar isso porque a
    # checagem de idempotência em processar_lead_confirmado já ignora leads
    # que já têm registro em aniversariantes.
    gravou_no_kommo = await kommo_service.atualizar_custom_fields_lead(
        str(lead_id), {CAMPO_URL_FLYER_ID: url_publica_flyer}
    )
    if not gravou_no_kommo:
        logger.error(
            f"💥 Falha ao gravar a URL do flyer no Custom Field 'URL do Flyer' ({CAMPO_URL_FLYER_ID}) "
            f"do Lead {lead_id}. O Salesbot não vai ter esse valor disponível até isso ser corrigido manualmente."
        )

    logger.info(f"✅ Cadastro do aniversariante '{nome_aniversariante}' foi CONCLUÍDO!")

    return {
        "status": "sucesso",
        "mensagem": "Flyer gerado e cadastro concluído.",
        "link_gerado": link_formulario,
    }


async def processar_lead_confirmado(lead_id: str) -> None:
    """
    Processamento pesado do lead que acabou de chegar na etapa "PROCESSANDO
    FLYER": consulta ativa, download da foto, Pillow, upload duplo no
    Storage e upsert em `aniversariantes`.

    Roda em background (ver `receber_webhook_kommo`, que agenda esta função
    via `BackgroundTasks` e responde 200 ao Kommo antes dela começar) —
    nota de 07/08/2026: com a cadeia inteira rodando de forma síncrona
    dentro da rota, a soma de round-trips externos (GET no Kommo, download
    do CDN, 2 uploads no Storage, insert) passava do tempo que o Kommo
    espera por um ACK, e o Kommo reenviava o mesmo webhook por timeout —
    visível no terminal do ngrok como vários `POST /webhooks/kommo`
    empilhados sem `200 OK` até um finalmente completar a tempo. Responder
    rápido e processar depois elimina esse reenvio na origem. A checagem de
    idempotência abaixo continua sendo a defesa principal contra
    reentregas (por timeout ou não) que cheguem de qualquer forma.

    Como já não há uma resposta HTTP para devolver (o Kommo já recebeu o
    ACK), cada desvio early-exit apenas loga o motivo e retorna, em vez de
    devolver um dict de resposta.
    """
    try:
        # Idempotência: o Kommo entrega webhook em modelo "at least once" — o
        # mesmo lead_id pode chegar mais de uma vez nesta etapa (confirmado
        # em teste manual: o mesmo lead disparou 3 reentregas idênticas em
        # sequência, causadas por timeout — ver docstring acima). Sem essa
        # checagem, cada reentrega refazia a consulta ativa, o download da
        # foto, o Pillow e o upload no Storage, e sobrescrevia
        # token_exclusivo com um UUID novo — invalidando silenciosamente o
        # link que já podia ter sido enviado ao cliente. Um lead com
        # registro em aniversariantes é considerado definitivamente
        # processado; reentregas são ignoradas aqui, antes de qualquer
        # chamada cara.
        try:
            aniversariante_existente = (
                supabase_client.table("aniversariantes")
                .select("id")
                .eq("kommo_lead_id", str(lead_id))
                .maybe_single()
                .execute()
            )
        except Exception as erro_checagem:
            logger.error(f"💥 Falha ao checar se o Lead {lead_id} já tinha cadastro (seguindo mesmo assim): {erro_checagem}")
            aniversariante_existente = None

        if getattr(aniversariante_existente, "data", None):
            logger.info(f"➡️ Lead {lead_id} já tem cadastro em aniversariantes (reentrega do webhook). Ignorando.")
            return

        # Busca ativa: consulta direta e imediata na API do Kommo para pegar
        # os valores FRESCOS dos Custom Fields no exato instante do
        # processamento — em vez de confiar no que veio (ou não veio) no
        # corpo do webhook.
        logger.info(f"🔄 Consultando dados atualizados do Lead {lead_id} direto na API do Kommo (GET ativo)...")
        campos = await kommo_service.buscar_custom_fields_lead(str(lead_id))

        if campos is None:
            logger.error(f"💥 Falha ao consultar o Lead {lead_id} na API do Kommo. Abortando com segurança (sem INSERT).")
            return

        logger.info(
            "🔎 CHECAGEM DE CAMPOS (via consulta ativa) -> Lead %s | Data da reserva (%s): '%s' | Horário (%s): '%s' | "
            "Estimativa de convidados (%s): '%s' | Nome do flyer (%s): '%s' | Foto (%s): '%s'",
            lead_id,
            CAMPO_DATA_DA_RESERVA_ID, formatar_valor_para_log(campos.get(CAMPO_DATA_DA_RESERVA_ID)),
            CAMPO_HORARIO_ID, formatar_valor_para_log(campos.get(CAMPO_HORARIO_ID)),
            CAMPO_ESTIMATIVA_CONVIDADOS_ID, formatar_valor_para_log(campos.get(CAMPO_ESTIMATIVA_CONVIDADOS_ID)),
            CAMPO_NOME_FLYER_ID, formatar_valor_para_log(campos.get(CAMPO_NOME_FLYER_ID)),
            CAMPO_FOTO_ID, formatar_valor_para_log(campos.get(CAMPO_FOTO_ID)),
        )

        campos_faltando = [nome for field_id, nome in CAMPOS_OBRIGATORIOS.items() if not campos.get(field_id)]
        if campos_faltando:
            logger.warning(
                f"⚠️ Lead {lead_id} chegou na etapa alvo, mas a consulta ativa à API do Kommo retornou campos vazios. "
                f"Faltando: {', '.join(campos_faltando)}. Ignorando com segurança (sem INSERT parcial)."
            )
            return

        logger.info(f"🎉 TODOS OS DADOS COLETADOS (confirmados via consulta ativa) para o Lead {lead_id}! Processando cadastro...")

        nome_aniversariante = campos[CAMPO_NOME_FLYER_ID]
        data_reserva = converter_valor_data_kommo(campos[CAMPO_DATA_DA_RESERVA_ID])
        horario_reserva = campos[CAMPO_HORARIO_ID]
        estimativa_convidados_raw = campos[CAMPO_ESTIMATIVA_CONVIDADOS_ID]
        valor_foto = campos[CAMPO_FOTO_ID]

        # O endpoint oficial de arquivos (GET /api/v4/files/{uuid}) devolve
        # 404 nesta conta — não é usado. O dict de metadados do Custom Field
        # também não traz nenhuma URL pronta: montamos o link do CDN do
        # Kommo concatenando file_uuid + version_uuid + file_name na base
        # fixa do drive da conta, sem nenhuma chamada de rede extra (ver
        # kommo_service.montar_url_cdn_arquivo).
        url_foto = kommo_service.montar_url_cdn_arquivo(valor_foto)

        if not url_foto:
            logger.error(
                f"❌ Não foi possível montar a URL de download do CDN do Kommo a partir do Custom Field "
                f"'Foto do aniversariante' ({CAMPO_FOTO_ID}) do Lead {lead_id}. Valor bruto recebido: {valor_foto!r}."
            )
            return

        # Validação defensiva final: garante que a URL extraída acima é
        # http(s) antes de qualquer requisição — evita que o httpx estoure
        # "Request URL is missing an 'http://' or 'https://' protocol." (erro
        # 500 genérico, sem contexto do que realmente veio do Kommo).
        if not eh_url_http_valida(url_foto):
            logger.error(
                f"❌ O Custom Field 'Foto do aniversariante' ({CAMPO_FOTO_ID}) do Lead {lead_id} não contém uma "
                f"URL http(s) válida. Valor bruto recebido do Kommo: {url_foto!r}."
            )
            return

        try:
            # follow_redirects=True é obrigatório aqui: a CDN de arquivos do
            # Kommo (drive-g.kommo.com) responde com 301/302 antes de
            # entregar o binário da imagem — sem isso, resposta_imagem.content
            # viria vazio/HTML de redirecionamento em vez da foto real.
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resposta_imagem = await client.get(url_foto)
        except httpx.InvalidURL as erro_url:
            # Rede de segurança: cobre qualquer outro formato inválido que
            # passe pela checagem acima (ex.: espaços, caracteres inválidos)
            # sem derrubar o processamento em background.
            logger.error(f"❌ URL inválida ao tentar baixar a foto do aniversariante ({url_foto!r}): {erro_url}")
            return

        if resposta_imagem.status_code != 200:
            logger.error(f"❌ Falha ao baixar a foto do aniversariante a partir da URL do Custom Field ({url_foto}).")
            return
        foto_bytes = resposta_imagem.content

        resultado = await finalizar_cadastro_aniversariante(
            str(lead_id), nome_aniversariante, foto_bytes, data_reserva, horario_reserva, estimativa_convidados_raw
        )
        logger.info(f"🏁 Processamento em background concluído para o Lead {lead_id}: {resultado}")

    except Exception as e:
        logger.error(f"💥 Erro inesperado ao processar o Lead {lead_id} em background: {e}")


@router.post("/kommo")
async def receber_webhook_kommo(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json() if request.headers.get("content-type") == "application/json" else await request.form()
        dados = dict(payload)

        # Estratégia de Consulta Ativa (ver CLAUDE.md 4.2): este payload é
        # tratado apenas como um SINALIZADOR LEVE — extraímos só lead_id e
        # status_id dele. Os valores dos Custom Fields nunca são lidos daqui,
        # porque o corpo do webhook do Salesbot podia chegar com campos
        # vazios quando a gravação ainda não tinha propagado no Kommo no
        # instante exato do disparo. Os valores frescos são buscados no
        # processamento em background (kommo_service.buscar_custom_fields_lead).
        logger.info("--- WEBHOOK RECEBIDO DO KOMMO CRM (SINALIZADOR) ---")
        logger.info(f"📦 PAYLOAD BRUTO: {dados}")

        lead_id = None
        lead_status = None

        for key, value in dados.items():
            if key.startswith("leads["):
                if "custom_fields" in key:
                    # Ignorado de propósito: não confiamos mais nos valores de
                    # Custom Fields vindos do corpo do webhook (ver acima) —
                    # só pulamos essas chaves aqui para não colidir com o
                    # "[id]" do próprio lead durante a extração abaixo.
                    continue
                if "[status_id]" in key:
                    lead_status = int(value)
                elif "[id]" in key and "tags" not in key:
                    lead_id = value

        # Fallback de lead_id: aceita também um parâmetro simples ("lead_id"
        # ou "id") quando o payload de teste não usa o formato verbose
        # "leads[...][id]".
        if not lead_id:
            lead_id = dados.get("lead_id") or dados.get("id")

        logger.info(f"📋 LEAD DETECTADO -> ID: {lead_id} | Status: {lead_status}")

        if not lead_id:
            logger.info("➡️ Disparo da Kommo ignorado (sem lead_id).")
            return {"status": "ignorado", "mensagem": "Sem ID de lead válido."}

        if lead_status is None:
            logger.info("➡️ Disparo da Kommo ignorado (sem status_id no payload).")
            return {"status": "ignorado", "mensagem": "Sem Status válido."}

        # Filtro de Etapa: só processa quando o Lead está na etapa oficial
        # "PROCESSANDO FLYER" (ID 109983139) — é nesse ponto que o Salesbot
        # garante que os 5 campos obrigatórios já foram coletados do cliente.
        if lead_status != TARGET_STATUS_ID:
            if KOMMO_WEBHOOK_TEST_MODE:
                logger.warning(
                    f"⚠️ MODO TESTE ATIVO (KOMMO_WEBHOOK_TEST_MODE=true): lead na etapa {lead_status} "
                    f"foi aceito mesmo divergindo da etapa alvo de produção ({TARGET_STATUS_ID})."
                )
            else:
                logger.info(f"➡️ Lead ignorado. Está na etapa {lead_status}, mas o gatilho está configurado para {TARGET_STATUS_ID}.")
                return {"status": "ignorado", "mensagem": f"Lead não está na etapa alvo ({TARGET_STATUS_ID})."}

        # Ack imediato: agenda o processamento pesado (consulta ativa,
        # download, Pillow, Storage, insert) em background e responde 200 na
        # hora. Ver docstring de processar_lead_confirmado — sem isso, o
        # Kommo interpretava a demora da cadeia síncrona como falha e
        # reenviava o mesmo webhook (padrão visto no ngrok: vários POSTs
        # empilhados sem 200 OK até um completar a tempo).
        background_tasks.add_task(processar_lead_confirmado, str(lead_id))
        logger.info(f"📨 Lead {lead_id} confirmado na etapa alvo — processamento agendado em background.")
        return {"status": "recebido", "mensagem": "Lead confirmado; processamento iniciado em segundo plano."}

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar."
        )
