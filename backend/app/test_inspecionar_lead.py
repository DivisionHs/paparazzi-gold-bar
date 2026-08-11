"""
Script de teste isolado para inspecionar, direto na API v4 do Kommo CRM, os
Custom Fields de um Lead específico.

Diferente de test_kommo.py, este script NÃO passa por nenhuma rota do
FastAPI (não precisa do Uvicorn nem do ngrok rodando) — ele consulta a API
do Kommo diretamente via GET, para responder uma pergunta simples: "o valor
que o Salesbot acabou de gravar já está persistido e visível para quem
consultar o lead de fora, ou ainda há algum delay de sincronização do lado
do Kommo?".

Uso (a partir da raiz do repositório):
    python -m backend.app.test_inspecionar_lead
    python -m backend.app.test_inspecionar_lead 51339304
"""

import sys

import httpx
from colorama import Fore, Style, init as colorama_init
from dotenv import load_dotenv

from backend.app.config import settings

load_dotenv()
colorama_init(autoreset=True)

# ID de lead usado como padrão quando nenhum é passado por linha de comando.
LEAD_ID_PADRAO = "51339304"

# Nomes amigáveis dos Custom Fields do fluxo de aniversariantes (ver
# CLAUDE.md 4.2), só para destacar no console quando um deles aparecer no
# lead consultado. A API do Kommo já devolve "field_name" para qualquer
# campo, mapeado ou não — este dict é só um reforço visual.
CAMPOS_DO_FLUXO_ANIVERSARIANTE = {
    "2068768": "Nome da semana (legado — descontinuado, ver diario_projeto.md)",
    "2068460": "Data da Reserva",
    "2068854": "Horário da Reserva",
    "2068456": "Estimativa de Convidados",
    "2068452": "Nome do Flyer",
    "2068458": "Foto do Aniversariante",
}


def buscar_lead_bruto(lead_id: str) -> dict | None:
    """
    Faz um GET direto em /api/v4/leads/{lead_id} usando o token de longa
    duração do .env — sem passar por kommo_service.py nem por nenhuma outra
    camada do backend, para isolar exatamente o que a API do Kommo devolve
    neste instante.
    """
    if not settings.KOMMO_SUBDOMAIN or not settings.KOMMO_LONG_LIVED_TOKEN:
        print(f"{Fore.RED}❌ Erro: KOMMO_SUBDOMAIN ou KOMMO_LONG_LIVED_TOKEN não configurados no .env{Style.RESET_ALL}")
        return None

    url = f"https://{settings.KOMMO_SUBDOMAIN}.kommo.com/api/v4/leads/{lead_id}"
    headers = {"Authorization": f"Bearer {settings.KOMMO_LONG_LIVED_TOKEN}"}

    try:
        resposta = httpx.get(url, headers=headers, params={"with": "contacts"}, timeout=10.0)
        resposta.raise_for_status()
        return resposta.json()
    except httpx.HTTPStatusError as erro:
        print(f"{Fore.RED}❌ Kommo recusou a consulta (HTTP {erro.response.status_code}): {erro.response.text}{Style.RESET_ALL}")
        return None
    except httpx.RequestError as erro:
        print(f"{Fore.RED}❌ Falha de conexão ao consultar o Kommo: {erro}{Style.RESET_ALL}")
        return None


def imprimir_dados_gerais(lead: dict) -> None:
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== DADOS GERAIS DO LEAD {lead.get('id')} ==={Style.RESET_ALL}")
    print(f"Nome (campo 'name'):     {lead.get('name')!r}")
    print(f"Status ID (etapa atual): {lead.get('status_id')}")
    print(f"Pipeline ID:             {lead.get('pipeline_id')}")
    print(f"Atualizado em (Unix):    {lead.get('updated_at')}")


def imprimir_custom_fields(lead: dict) -> None:
    custom_fields = lead.get("custom_fields_values") or []

    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== CUSTOM FIELDS ({len(custom_fields)} encontrados) ==={Style.RESET_ALL}")

    if not custom_fields:
        print(f"{Fore.YELLOW}⚠️  Nenhum custom_fields_values retornado pela API para este lead.{Style.RESET_ALL}")
        return

    for campo in custom_fields:
        field_id = str(campo.get("field_id"))
        field_type = campo.get("field_type") or "?"
        nome_api = campo.get("field_name") or "(sem nome retornado pela API)"
        nome_conhecido = CAMPOS_DO_FLUXO_ANIVERSARIANTE.get(field_id)

        valores = campo.get("values") or []
        valor_fmt = ", ".join(str(v.get("value")) for v in valores) if valores else "(vazio)"

        marcador = f"{Fore.GREEN}★{Style.RESET_ALL}" if nome_conhecido else " "
        rotulo = f"{nome_api} [{field_type}]"
        if nome_conhecido:
            rotulo += f" — {Fore.GREEN}{nome_conhecido}{Style.RESET_ALL}"

        print(f"{marcador} ID {Fore.CYAN}{field_id:>9}{Style.RESET_ALL} | {rotulo}")
        print(f"      valor: {Fore.YELLOW}{valor_fmt}{Style.RESET_ALL}")

    ids_encontrados = {str(c.get("field_id")) for c in custom_fields}
    faltando = [f"{fid} ({nome})" for fid, nome in CAMPOS_DO_FLUXO_ANIVERSARIANTE.items() if fid not in ids_encontrados]
    if faltando:
        print(f"\n{Fore.YELLOW}⚠️  Campos do fluxo de aniversariante AUSENTES neste lead: {', '.join(faltando)}{Style.RESET_ALL}")


def main() -> None:
    lead_id = sys.argv[1] if len(sys.argv) > 1 else LEAD_ID_PADRAO

    print(f"{Fore.YELLOW}🔎 Consultando Lead {lead_id} direto na API do Kommo (GET /api/v4/leads/{{id}})...{Style.RESET_ALL}")

    lead = buscar_lead_bruto(lead_id)
    if not lead:
        sys.exit(1)

    imprimir_dados_gerais(lead)
    imprimir_custom_fields(lead)


if __name__ == "__main__":
    main()
