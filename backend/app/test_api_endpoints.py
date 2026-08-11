"""
Teste integrativo e isolado dos contratos HTTP do backend.

Diferente de test_kommo.py, este script NÃO aciona nenhum webhook da Kommo
(não passa por /webhooks/kommo) e, portanto, não dispara mensagens reais no
WhatsApp. Ele mesmo insere e remove o registro mock do
aniversariante direto no Supabase, e testa apenas os contratos internos:

    GET  /aniversariantes/validar-token/{token}
    POST /convidados/confirmar
    POST /convidados/validar-qr
    GET  /convidados/buscar-cpf/{cpf}

Pré-requisitos:
    - Servidor FastAPI rodando localmente:
        uvicorn backend.app.main:app --reload
    - Variáveis SUPABASE_URL e SUPABASE_KEY configuradas no .env

Uso (a partir da raiz do repositório):
    python -m backend.app.test_api_endpoints
"""

import os
import sys
import uuid

import httpx
from colorama import Fore, Style, init as colorama_init
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
colorama_init(autoreset=True)

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DO TESTE
# ---------------------------------------------------------------------------
URL_SERVIDOR = "http://127.0.0.1:8000"

LEAD_ID_TESTE = "TESTE_KOMMO_999"
CPF_TESTE = "11144477735"  # CPF fictício com dígito verificador válido, apenas para teste

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(f"{Fore.RED}Erro: SUPABASE_URL/SUPABASE_KEY não configurados no .env{Style.RESET_ALL}")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

_contador = {"sucesso": 0, "falha": 0}


# ---------------------------------------------------------------------------
# HELPERS DE IMPRESSÃO E VERIFICAÇÃO
# ---------------------------------------------------------------------------
def titulo(texto: str) -> None:
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== {texto} ==={Style.RESET_ALL}")


def sucesso(texto: str) -> None:
    _contador["sucesso"] += 1
    print(f"{Fore.GREEN}✅ {texto}{Style.RESET_ALL}")


def erro(texto: str) -> None:
    _contador["falha"] += 1
    print(f"{Fore.RED}❌ {texto}{Style.RESET_ALL}")


def info(texto: str) -> None:
    print(f"{Fore.YELLOW}ℹ️  {texto}{Style.RESET_ALL}")


def verificar(condicao: bool, descricao_ok: str, descricao_falha: str) -> bool:
    """Registra sucesso/falha no contador e imprime o resultado, sem interromper o script."""
    if condicao:
        sucesso(descricao_ok)
    else:
        erro(descricao_falha)
    return condicao


# ---------------------------------------------------------------------------
# LIMPEZA DOS DADOS DE TESTE (usada antes E depois, para garantir idempotência)
# ---------------------------------------------------------------------------
def limpar_dados_de_teste() -> bool:
    try:
        # Remove primeiro os convidados (dependem do lead_id) e só então o aniversariante.
        supabase.table("convidados").delete().eq("lead_id", LEAD_ID_TESTE).execute()
        supabase.table("aniversariantes").delete().eq("kommo_lead_id", LEAD_ID_TESTE).execute()
        return True
    except Exception as e:
        erro(f"Falha ao limpar dados de teste no Supabase: {e}")
        return False


# ---------------------------------------------------------------------------
# ETAPA 1 — Inserção mock do aniversariante direto no Supabase (sem webhook)
# ---------------------------------------------------------------------------
def preparar_aniversariante_mock() -> str | None:
    titulo("ETAPA 1 — Inserção mock do aniversariante de teste")

    token_exclusivo = str(uuid.uuid4())

    try:
        resposta = supabase.table("aniversariantes").insert({
            "kommo_lead_id": LEAD_ID_TESTE,
            "nome_completo": "Aniversariante de Teste Automatizado",
            "token_exclusivo": token_exclusivo,
        }).execute()
    except Exception as e:
        erro(f"Falha ao inserir aniversariante mock no Supabase: {e}")
        return None

    if not verificar(
        bool(resposta.data),
        "Aniversariante mock inserido no Supabase.",
        "Falha ao inserir aniversariante mock no Supabase (resposta vazia).",
    ):
        return None

    info(f"kommo_lead_id de teste: {LEAD_ID_TESTE}")
    info(f"token_exclusivo gerado: {token_exclusivo}")

    return token_exclusivo


# ---------------------------------------------------------------------------
# ETAPA 2 — GET /aniversariantes/validar-token/{token}
# ---------------------------------------------------------------------------
def testar_validar_token(cliente: httpx.Client, token_valido: str) -> None:
    titulo("ETAPA 2 — GET /aniversariantes/validar-token/{token}")

    # 2.1 — Token válido deve retornar 200 com os dados do aniversariante
    resposta = cliente.get(f"/aniversariantes/validar-token/{token_valido}")
    ok = verificar(
        resposta.status_code == 200,
        f"Token válido retornou HTTP 200. Corpo: {resposta.text}",
        f"Token válido deveria retornar 200, retornou {resposta.status_code}. Corpo: {resposta.text}",
    )
    if ok:
        corpo = resposta.json()
        verificar(
            corpo.get("lead_id") == LEAD_ID_TESTE,
            "lead_id retornado corresponde ao aniversariante de teste.",
            f"lead_id inesperado no retorno: {corpo.get('lead_id')}",
        )

    # 2.2 — Token inexistente deve retornar 404
    token_invalido = str(uuid.uuid4())
    resposta = cliente.get(f"/aniversariantes/validar-token/{token_invalido}")
    verificar(
        resposta.status_code == 404,
        "Token inválido retornou HTTP 404 corretamente.",
        f"Token inválido deveria retornar 404, retornou {resposta.status_code}.",
    )


# ---------------------------------------------------------------------------
# ETAPA 3 — POST /convidados/confirmar
# ---------------------------------------------------------------------------
def testar_confirmar_presenca(cliente: httpx.Client) -> str | None:
    titulo("ETAPA 3 — POST /convidados/confirmar")

    payload = {
        "lead_id": LEAD_ID_TESTE,
        "nome_completo": "Convidado Teste Automatizado",
        "cpf": CPF_TESTE,
        "whatsapp": "11999999999",
        "data_nascimento": "1995-05-20",
    }

    # 3.1 — Primeiro cadastro deve ser aceito (201) e devolver qr_code_token
    resposta = cliente.post("/convidados/confirmar", json=payload)
    ok = verificar(
        resposta.status_code == 201,
        f"Cadastro do convidado aceito com HTTP 201. Corpo: {resposta.text}",
        f"Cadastro deveria retornar 201, retornou {resposta.status_code}. Corpo: {resposta.text}",
    )

    qr_code_token = None
    if ok:
        qr_code_token = resposta.json().get("qr_code_token")
        verificar(
            bool(qr_code_token),
            f"qr_code_token recebido: {qr_code_token}",
            "Resposta de sucesso não trouxe o campo qr_code_token.",
        )

    # 3.2 — Repetir o MESMO CPF na MESMA lista deve ser recusado com 400
    resposta_duplicada = cliente.post("/convidados/confirmar", json=payload)
    ok_duplicado = verificar(
        resposta_duplicada.status_code == 400,
        "CPF duplicado na mesma lista foi recusado com HTTP 400.",
        f"CPF duplicado deveria retornar 400, retornou {resposta_duplicada.status_code}. Corpo: {resposta_duplicada.text}",
    )
    if ok_duplicado:
        detalhe = resposta_duplicada.json().get("detail", "")
        verificar(
            "cadastrado" in detalhe.lower(),
            f'Mensagem de erro de CPF duplicado está clara: "{detalhe}"',
            f'Mensagem de erro inesperada para CPF duplicado: "{detalhe}"',
        )

    return qr_code_token


# ---------------------------------------------------------------------------
# ETAPA 4 — POST /convidados/validar-qr (app da portaria)
# ---------------------------------------------------------------------------
def testar_validar_qr(cliente: httpx.Client, qr_code_token: str | None) -> None:
    titulo("ETAPA 4 — POST /convidados/validar-qr (Portaria)")

    if not qr_code_token:
        erro("Etapa pulada: nenhum qr_code_token disponível da etapa anterior.")
        return

    # 4.1 — Primeira leitura do QR Code deve liberar o acesso (Sinal Verde)
    resposta = cliente.post("/convidados/validar-qr", json={"qr_code_token": qr_code_token})
    corpo = resposta.json() if resposta.status_code == 200 else {}
    ok_liberado = verificar(
        corpo.get("status") == "LIBERADO",
        f"Primeira leitura do QR Code liberou a entrada (Sinal Verde). Corpo: {corpo}",
        f"Primeira leitura deveria retornar status LIBERADO. Retornou: {resposta.status_code} {resposta.text}",
    )
    if ok_liberado:
        aniversariante_na_resposta = corpo.get("aniversariante") or {}
        verificar(
            aniversariante_na_resposta.get("nome_completo") == "Aniversariante de Teste Automatizado",
            "Resposta LIBERADO trouxe o objeto aniversariante com o nome da lista.",
            f"Objeto aniversariante ausente ou inesperado: {aniversariante_na_resposta}",
        )
        verificar(
            corpo.get("e_aniversariante") is False,
            "e_aniversariante retornou False (aniversariante de teste ainda sem CPF cadastrado).",
            f"e_aniversariante deveria ser False neste ponto. Retornou: {corpo.get('e_aniversariante')}",
        )

    # 4.2 — Reler o MESMO QR Code deve recusar por já ter sido utilizado
    resposta = cliente.post("/convidados/validar-qr", json={"qr_code_token": qr_code_token})
    corpo = resposta.json() if resposta.status_code == 200 else {}
    ok_ja_utilizado = verificar(
        corpo.get("status") == "JA_UTILIZADO",
        f"Segunda leitura do mesmo QR Code foi recusada (JA_UTILIZADO). Corpo: {corpo}",
        f"Segunda leitura deveria retornar JA_UTILIZADO. Retornou: {corpo}",
    )
    if ok_ja_utilizado:
        verificar(
            bool(corpo.get("data_hora_entrada")),
            "Resposta JA_UTILIZADO trouxe o data_hora_entrada da primeira leitura.",
            "Resposta JA_UTILIZADO não trouxe o campo data_hora_entrada.",
        )

        convidado_na_resposta = corpo.get("convidado") or {}
        verificar(
            convidado_na_resposta.get("nome_completo") == "Convidado Teste Automatizado",
            "Resposta JA_UTILIZADO trouxe o objeto convidado com nome_completo correto.",
            f"Objeto convidado ausente ou com nome_completo inesperado: {convidado_na_resposta}",
        )
        verificar(
            convidado_na_resposta.get("cpf") == CPF_TESTE,
            "Resposta JA_UTILIZADO trouxe o objeto convidado com cpf correto.",
            f"Objeto convidado ausente ou com cpf inesperado: {convidado_na_resposta}",
        )

        aniversariante_na_resposta = corpo.get("aniversariante") or {}
        verificar(
            aniversariante_na_resposta.get("nome_completo") == "Aniversariante de Teste Automatizado",
            "Resposta JA_UTILIZADO também trouxe o objeto aniversariante da lista.",
            f"Objeto aniversariante ausente ou inesperado: {aniversariante_na_resposta}",
        )
        verificar(
            corpo.get("e_aniversariante") is False,
            "e_aniversariante retornou False (aniversariante de teste ainda sem CPF cadastrado).",
            f"e_aniversariante deveria ser False neste ponto. Retornou: {corpo.get('e_aniversariante')}",
        )

    # 4.3 — QR Code inexistente deve ser recusado como inválido (Sinal Vermelho)
    qr_inexistente = str(uuid.uuid4())
    resposta = cliente.post("/convidados/validar-qr", json={"qr_code_token": qr_inexistente})
    corpo = resposta.json() if resposta.status_code == 200 else {}
    verificar(
        corpo.get("status") == "INVALIDO",
        f"QR Code inexistente foi recusado corretamente (INVALIDO). Corpo: {corpo}",
        f"QR Code inexistente deveria retornar INVALIDO. Retornou: {corpo}",
    )


# ---------------------------------------------------------------------------
# ETAPA 5 — GET /convidados/buscar-cpf/{cpf} (contingência manual da portaria)
# ---------------------------------------------------------------------------
def testar_buscar_por_cpf(cliente: httpx.Client) -> None:
    titulo("ETAPA 5 — GET /convidados/buscar-cpf/{cpf}")

    # 5.1 — CPF cadastrado na Etapa 3 deve ser encontrado
    resposta = cliente.get(f"/convidados/buscar-cpf/{CPF_TESTE}")
    ok = verificar(
        resposta.status_code == 200,
        f"Busca manual encontrou o convidado de teste pelo CPF. Corpo: {resposta.text}",
        f"Busca manual deveria retornar 200, retornou {resposta.status_code}. Corpo: {resposta.text}",
    )
    if ok:
        corpo = resposta.json()
        verificar(
            corpo.get("cpf") == CPF_TESTE,
            "CPF retornado corresponde ao convidado de teste.",
            f"CPF inesperado no retorno: {corpo.get('cpf')}",
        )
        verificar(
            corpo.get("utilizado") is True,
            "Campo utilizado retornou True (QR Code já foi lido na Etapa 4).",
            f"Campo utilizado deveria ser True após a Etapa 4. Retornou: {corpo.get('utilizado')}",
        )
        verificar(
            corpo.get("e_aniversariante") is False,
            "e_aniversariante retornou False (aniversariante de teste ainda sem CPF cadastrado).",
            f"e_aniversariante deveria ser False neste ponto. Retornou: {corpo.get('e_aniversariante')}",
        )
        aniversariante_na_resposta = corpo.get("aniversariante") or {}
        verificar(
            aniversariante_na_resposta.get("nome_completo") == "Aniversariante de Teste Automatizado",
            "Busca manual trouxe o objeto aniversariante com o nome da lista.",
            f"Objeto aniversariante ausente ou inesperado: {aniversariante_na_resposta}",
        )

    # 5.2 — CPF com máscara (pontos/traço) também deve funcionar, já que o
    # backend limpa o valor recebido antes de consultar o Supabase.
    cpf_com_mascara = f"{CPF_TESTE[:3]}.{CPF_TESTE[3:6]}.{CPF_TESTE[6:9]}-{CPF_TESTE[9:]}"
    resposta = cliente.get(f"/convidados/buscar-cpf/{cpf_com_mascara}")
    verificar(
        resposta.status_code == 200,
        "Busca manual também funciona enviando o CPF com máscara (pontos/traço).",
        f"Busca com CPF mascarado deveria retornar 200, retornou {resposta.status_code}.",
    )

    # 5.3 — CPF inexistente deve retornar 404
    cpf_inexistente = "00000000000"
    resposta = cliente.get(f"/convidados/buscar-cpf/{cpf_inexistente}")
    verificar(
        resposta.status_code == 404,
        "CPF inexistente retornou HTTP 404 corretamente.",
        f"CPF inexistente deveria retornar 404, retornou {resposta.status_code}.",
    )

    # 5.4 — Simula o aniversariante tendo o MESMO CPF do convidado de teste.
    # Nenhum fluxo real preenche esse campo hoje (ver aviso na migration
    # 20260725_01_add_cpf_aniversariantes.sql), mas o contrato de
    # "e_aniversariante == True" precisa ser coberto mesmo assim.
    try:
        supabase.table("aniversariantes")\
            .update({"cpf": CPF_TESTE})\
            .eq("kommo_lead_id", LEAD_ID_TESTE)\
            .execute()
    except Exception as e:
        erro(f"Falha ao simular CPF do aniversariante para o teste 5.4: {e}")
        return

    resposta = cliente.get(f"/convidados/buscar-cpf/{CPF_TESTE}")
    ok_vip = verificar(
        resposta.status_code == 200,
        "Busca manual continua retornando 200 após o aniversariante ganhar CPF.",
        f"Busca manual deveria retornar 200, retornou {resposta.status_code}.",
    )
    if ok_vip:
        corpo = resposta.json()
        verificar(
            corpo.get("e_aniversariante") is True,
            "e_aniversariante virou True quando o CPF do convidado bate com o do aniversariante.",
            f"e_aniversariante deveria ser True. Retornou: {corpo.get('e_aniversariante')}",
        )
        aniversariante_na_resposta = corpo.get("aniversariante") or {}
        verificar(
            aniversariante_na_resposta.get("cpf") == CPF_TESTE,
            "Objeto aniversariante trouxe o cpf simulado corretamente.",
            f"cpf do aniversariante inesperado: {aniversariante_na_resposta.get('cpf')}",
        )


# ---------------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ---------------------------------------------------------------------------
def main() -> None:
    print(f"{Style.BRIGHT}{Fore.MAGENTA}{'=' * 68}")
    print(" TESTE INTEGRATIVO DOS CONTRATOS DE API — PAPARAZZI GOLD BAR")
    print(f"{'=' * 68}{Style.RESET_ALL}")

    info(f"Servidor alvo: {URL_SERVIDOR}")
    info("Nenhum webhook da Kommo será acionado neste teste.")

    # Limpeza defensiva: garante que uma execução anterior interrompida não deixe lixo
    limpar_dados_de_teste()

    try:
        token_exclusivo = preparar_aniversariante_mock()

        if token_exclusivo:
            with httpx.Client(base_url=URL_SERVIDOR, timeout=10.0) as cliente:
                testar_validar_token(cliente, token_exclusivo)
                qr_code_token = testar_confirmar_presenca(cliente)
                testar_validar_qr(cliente, qr_code_token)
                testar_buscar_por_cpf(cliente)
        else:
            erro("Testes de API pulados: não foi possível preparar o aniversariante mock.")

    except httpx.ConnectError:
        erro(f"Não foi possível conectar em {URL_SERVIDOR}. O servidor FastAPI está rodando?")
    except Exception as e:
        erro(f"Erro inesperado durante a execução dos testes: {e}")

    finally:
        # ETAPA 6 — Limpeza sempre executa, mesmo se algum teste acima falhar/lançar exceção
        titulo("ETAPA 6 — Limpeza dos dados de teste")
        if limpar_dados_de_teste():
            sucesso("Registros de teste removidos das tabelas convidados e aniversariantes.")

    # -------------------------------------------------------------------
    # RESUMO FINAL
    # -------------------------------------------------------------------
    titulo("RESUMO")
    total = _contador["sucesso"] + _contador["falha"]
    print(f"{Fore.GREEN}Sucessos: {_contador['sucesso']}{Style.RESET_ALL}")
    print(f"{Fore.RED}Falhas:   {_contador['falha']}{Style.RESET_ALL}")
    print(f"Total de verificações: {total}")

    if _contador["falha"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
