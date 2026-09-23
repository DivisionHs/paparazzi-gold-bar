"""
Rotas administrativas TEMPORÁRIAS de atendimento manual (decisão de
23/09/2026 — ver CLAUDE.md, seção 4.9).

Contexto: o Salesbot de coleta automática (fluxo linear, pergunta a
pergunta) trava sempre que o cliente sai do roteiro esperado (responde algo
fora do padrão, manda foto errada, digita a data errado etc.) — em produção,
251 leads entraram no pipeline de teste desde a última madrugada, só 4
fecharam o flyer automaticamente e 44 ficaram parados na etapa "Aniversário"
sem nenhum dos 5 Custom Fields completos.

Esta rota permite que um atendente humano complete manualmente os dados que
estiverem faltando (o que já estiver preenchido no Lead do Kommo é
reaproveitado) e gere o flyer + os dois links (flyer e formulário) do mesmo
jeito que o fluxo automático faria — reaproveitando
`webhooks.finalizar_cadastro_aniversariante`, a mesma função usada pelo
webhook oficial, para não duplicar a lógica de geração/upload/upsert. O
resultado é devolvido como um texto pronto (com as URLs reais já
substituídas) para o atendente copiar e colar direto no chat do Kommo — não
tenta reativar o Salesbot, porque não existe endpoint de disparo de Salesbot
via API nesta conta (ver CLAUDE.md 4.2, decisão de 10/08/2026).

Autenticação: token estático simples (`ADMIN_MANUAL_TOKEN`), não é sessão do
Supabase Auth — decisão deliberada para não depender de provisionar contas
novas de funcionário sob urgência. Ver nota de escopo em CLAUDE.md 4.9.
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status

from backend.app.config import settings
from backend.app.routes import webhooks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin (temporário)"])


async def exigir_token_admin(request: Request) -> None:
    if not settings.ADMIN_MANUAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Atendimento manual não configurado neste ambiente (ADMIN_MANUAL_TOKEN ausente).",
        )

    token_recebido = request.headers.get("X-Admin-Token", "")
    if token_recebido != settings.ADMIN_MANUAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de atendimento manual inválido.",
        )


# Texto final enviado ao cliente após o flyer ficar pronto — mesmo texto
# aplicado no bloco final do Salesbot ("Novo Robo Paparazzi"), mas com as
# duas URLs escritas diretamente no corpo da mensagem (texto puro, não
# botão), porque a Meta passou a exigir validação manual de modelo aprovado
# para botões de URL em mensagem de formato livre (achado de 23/09/2026).
# Se o texto do bloco do bot for alterado no Kommo, atualize aqui também —
# não há nenhuma sincronização automática entre os dois.
_TEMPLATE_MENSAGEM_FINAL = (
    "🎉🥳 Seu flyer está pronto! Vamos deixar essa festa ainda mais incrível!\n\n"
    "👇 Toque nos botões abaixo:\n\n"
    "📸 Flyer personalizado — o download começa sozinho e já salva na galeria do seu celular. "
    "Se abrir uma tela em branco, pode fechar tranquilo, é só o navegador confirmando o download. "
    "Poste nos stories, no status do WhatsApp ou mande direto pra galera!\n\n"
    "📝 Link do formulário de convidados — esse é o mais importante! Envie pra todo mundo que você vai levar. "
    "É por ele que seus convidados confirmam presença e entram na sua lista — sem preencher, "
    "não tem como garantir a entrada deles.\n\n"
    "Na hora de entrar, é só informar o nome ou CPF na portaria. 😉\n\n"
    "🔥 Isso aqui é Paparazzi! Vai ser uma festa incrível! 🥂\n\n"
    "Flyer Personalizado: {url_flyer}\n"
    "Link do formulário de convidados: {link_formulario}\n\n"
    "Compartilhe com os seus convidados e boa festa! 🚀"
)


@router.get("/leads/{lead_id}/campos", dependencies=[Depends(exigir_token_admin)])
async def consultar_campos_lead(lead_id: str):
    """
    Devolve o estado atual dos 5 Custom Fields obrigatórios do Lead (o que já
    está preenchido no Kommo, vindo do Salesbot ou de digitação parcial do
    cliente) — para a tela de atendimento manual mostrar ao atendente
    exatamente o que falta preencher, sem pedir de novo o que já existe.
    """
    campos = await webhooks.kommo_service.buscar_custom_fields_lead(lead_id)
    if campos is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar esse Lead na API do Kommo.",
        )

    resultado = {}
    for field_id, nome in webhooks.CAMPOS_OBRIGATORIOS.items():
        valor = campos.get(field_id)
        if field_id == webhooks.CAMPO_FOTO_ID:
            resultado[field_id] = {
                "nome": nome,
                "preenchido": isinstance(valor, dict) and bool(valor.get("file_uuid")),
                "valor": valor.get("file_name") if isinstance(valor, dict) else None,
            }
        elif field_id == webhooks.CAMPO_DATA_DA_RESERVA_ID:
            # O valor bruto do Kommo pode vir como timestamp Unix,
            # "DD/MM/AAAA" ou "DD.MM.AAAA" — normaliza pra ISO com a mesma
            # função usada na hora de gerar o flyer de verdade, depois
            # reformata pra "DD/MM/AAAA" (formato que o campo de texto da
            # página de atendimento usa, igual ao que o atendente já está
            # acostumado a digitar/ler).
            data_iso = webhooks.converter_valor_data_kommo(valor) if valor else None
            data_br = datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y") if data_iso else None
            resultado[field_id] = {
                "nome": nome,
                "preenchido": bool(valor),
                "valor": data_br,
            }
        else:
            resultado[field_id] = {
                "nome": nome,
                "preenchido": bool(valor),
                "valor": valor,
            }

    ja_processado = (
        webhooks.supabase_client.table("aniversariantes")
        .select("foto_url")
        .eq("kommo_lead_id", str(lead_id))
        .maybe_single()
        .execute()
    )
    dados_ja_processado = getattr(ja_processado, "data", None) if ja_processado else None

    return {
        "lead_id": lead_id,
        "campos": resultado,
        "ja_tem_flyer_gerado": bool(dados_ja_processado),
    }


@router.post("/leads/{lead_id}/gerar-flyer", dependencies=[Depends(exigir_token_admin)])
async def gerar_flyer_manual(
    lead_id: str,
    nome: str | None = Form(None),
    data_reserva: str | None = Form(None, description="Formato DD/MM/AAAA"),
    horario: str | None = Form(None),
    estimativa_convidados: str | None = Form(None),
    foto: UploadFile | None = None,
):
    """
    Completa manualmente os campos que faltarem (o que não for enviado aqui
    é buscado do que já está no Lead do Kommo), gera o flyer e devolve o
    texto pronto pra colar no chat do cliente. Reaproveita
    finalizar_cadastro_aniversariante — mesmo caminho de geração/upload/
    upsert do fluxo automático, sem duplicar lógica.
    """
    campos_kommo = await webhooks.kommo_service.buscar_custom_fields_lead(lead_id) or {}

    nome_final = nome or campos_kommo.get(webhooks.CAMPO_NOME_FLYER_ID)
    horario_final = horario or campos_kommo.get(webhooks.CAMPO_HORARIO_ID)
    estimativa_raw_final = estimativa_convidados or campos_kommo.get(webhooks.CAMPO_ESTIMATIVA_CONVIDADOS_ID)

    # converter_valor_data_kommo já sabe interpretar "DD/MM/AAAA" (o que o
    # atendente digita no formulário) além de timestamp Unix e "DD.MM.AAAA"
    # (o que o Kommo pode devolver) — mesma função, um caminho só,
    # independente de onde o valor bruto veio.
    data_reserva_bruta = data_reserva or campos_kommo.get(webhooks.CAMPO_DATA_DA_RESERVA_ID)
    data_reserva_final = webhooks.converter_valor_data_kommo(data_reserva_bruta) if data_reserva_bruta else None

    if foto is not None:
        foto_bytes = await foto.read()
    else:
        valor_foto_kommo = campos_kommo.get(webhooks.CAMPO_FOTO_ID)
        foto_bytes = await webhooks.baixar_foto_via_cdn_kommo(valor_foto_kommo) if valor_foto_kommo else None

    # Validação de verdade dos 5 campos antes de gerar qualquer coisa — não
    # basta "ter algum valor", o valor precisa fazer sentido. Achado de
    # 23/09/2026: um lead tinha "Data da reserva" preenchida no Kommo, mas
    # incompleta (cliente não digitou o ano) — o Kommo guardou como
    # timestamp Unix 0, que converter_valor_data_kommo interpretava "com
    # sucesso" como 31/12/1969, e o flyer saía com uma data sem sentido sem
    # nenhum aviso. Reúne TODOS os problemas de uma vez (em vez de parar no
    # primeiro) pra o atendente corrigir tudo numa tentativa só.
    erros_validacao: list[str] = []

    if not nome_final or not nome_final.strip():
        erros_validacao.append("Nome do aniversariante não informado (nem no formulário, nem no Kommo).")

    if not data_reserva_final:
        erros_validacao.append(f"Data da reserva ausente ou em formato não reconhecido (valor bruto: {data_reserva_bruta!r}). Digite no formato DD/MM/AAAA.")
    else:
        ano_data = datetime.strptime(data_reserva_final, "%Y-%m-%d").year
        ano_atual = datetime.now().year
        if not (ano_atual - 1 <= ano_data <= ano_atual + 2):
            erros_validacao.append(
                f"Data da reserva não parece válida ({data_reserva_final}) — confira e digite de novo no formato DD/MM/AAAA."
            )

    horario_normalizado = webhooks.flyer_generator.formatar_horario_exibicao(horario_final) if horario_final else ""
    if not horario_final or not re.match(r"^\d{2}:\d{2}$", horario_normalizado):
        erros_validacao.append(f"Horário ausente ou em formato não reconhecido (valor bruto: {horario_final!r}).")

    estimativa_validada = webhooks.converter_estimativa_convidados_kommo(estimativa_raw_final)
    if estimativa_validada is None or estimativa_validada <= 0:
        erros_validacao.append(f"Estimativa de convidados ausente ou inválida (valor bruto: {estimativa_raw_final!r}).")

    if not foto_bytes:
        erros_validacao.append("Nenhuma foto disponível — envie o arquivo da foto ou preencha o Custom Field no Kommo antes.")

    if erros_validacao:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível gerar o flyer — corrija antes de tentar de novo: " + " | ".join(erros_validacao),
        )

    resultado = await webhooks.finalizar_cadastro_aniversariante(
        lead_id=lead_id,
        nome_aniversariante=nome_final,
        foto_bytes=foto_bytes,
        data_reserva=data_reserva_final,
        horario_reserva=horario_final,
        estimativa_convidados_raw=estimativa_raw_final,
    )

    mensagem_pronta = _TEMPLATE_MENSAGEM_FINAL.format(
        url_flyer=resultado["url_flyer"],
        link_formulario=resultado["link_gerado"],
    )

    logger.info(f"🧑‍💼 Flyer gerado manualmente para o Lead {lead_id} via atendimento manual.")

    return {
        "status": "sucesso",
        "url_flyer": resultado["url_flyer"],
        "link_formulario": resultado["link_gerado"],
        "mensagem_pronta": mensagem_pronta,
    }
