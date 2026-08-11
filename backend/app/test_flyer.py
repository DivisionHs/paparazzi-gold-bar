"""
Teste manual e isolado do serviço de geração de flyers (flyer_generator.py).

Gera uma foto fictícia em memória (sem depender de nenhum arquivo externo) e
testa generate_flyer com nome curto e nome muito longo, cobrindo dois caminhos:
    - carregamento real dos templates oficiais em backend/app/assets/templates/
      (placeholders gerados via Pillow, mas exercitam o carregamento de verdade);
    - fallback gracioso quando template_name não corresponde a nenhum arquivo.

Em todos os casos, garante que:
    - a função não lança nenhuma exceção;
    - o resultado é bytes não vazios;
    - o resultado é um JPEG válido de fato (reabre com o Pillow e confere o formato).

Uso (a partir da raiz do repositório):
    python -m backend.app.test_flyer
"""

import io
import sys

from colorama import Fore, Style, init as colorama_init
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
colorama_init(autoreset=True)

from backend.app.services.flyer_generator import (  # noqa: E402 (precisa vir após load_dotenv)
    TEMPLATES_OFICIAIS,
    generate_flyer,
    listar_templates_disponiveis,
)

_contador = {"sucesso": 0, "falha": 0}


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


def _gerar_foto_ficticia() -> bytes:
    """Cria uma foto colorida simples em memória, só para alimentar o teste."""
    imagem = Image.new("RGB", (800, 600), color=(90, 130, 200))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG")
    return buffer.getvalue()


def _testar_geracao(nome: str, descricao: str, template_name: str) -> None:
    foto_bytes = _gerar_foto_ficticia()

    try:
        flyer_bytes = generate_flyer(foto_bytes, nome, template_name=template_name)
    except Exception as e:
        erro(f"{descricao} ('{nome}', template={template_name}): generate_flyer lançou uma exceção inesperada: {e}")
        return

    if not flyer_bytes:
        erro(f"{descricao} ('{nome}'): o flyer retornou bytes vazios.")
        return

    sucesso(f"{descricao} ('{nome}', template={template_name}): flyer gerado sem exceções ({len(flyer_bytes)} bytes).")

    try:
        Image.open(io.BytesIO(flyer_bytes)).verify()
    except Exception as e:
        erro(f"{descricao} ('{nome}', template={template_name}): o arquivo gerado não é uma imagem válida: {e}")
        return

    # Precisa reabrir depois do verify() — o Pillow fecha o buffer internamente após verificar.
    flyer_imagem = Image.open(io.BytesIO(flyer_bytes))
    if flyer_imagem.format != "JPEG":
        erro(f"{descricao} ('{nome}', template={template_name}): formato inesperado ({flyer_imagem.format}), esperado JPEG.")
        return

    sucesso(
        f"{descricao} ('{nome}', template={template_name}): arquivo é um JPEG válido "
        f"({flyer_imagem.width}x{flyer_imagem.height}px)."
    )


def main() -> None:
    titulo("TESTE DO GERADOR DE FLYERS — PAPARAZZI GOLD BAR")

    disponiveis = listar_templates_disponiveis()
    info(f"Templates oficiais definidos: {TEMPLATES_OFICIAIS}")
    info(f"Templates com PNG presente em backend/app/assets/templates/: {disponiveis}")

    if len(disponiveis) == len(TEMPLATES_OFICIAIS):
        sucesso("Os 4 templates oficiais têm um PNG presente em assets/templates/.")
    else:
        erro(f"Faltam templates em assets/templates/: {set(TEMPLATES_OFICIAIS) - set(disponiveis)}")

    titulo("Carregamento real dos templates oficiais (assets/templates/)")
    _testar_geracao("Ana Lima", "Nome curto", template_name="sexta_boteco")
    _testar_geracao("Maria Eduarda Castro Fernandes de Albuquerque", "Nome muito longo", template_name="domingo")

    titulo("Fallback gracioso (template inexistente)")
    _testar_geracao("Convidado Teste", "Template sem PNG correspondente", template_name="inexistente")

    titulo("RESUMO")
    print(f"{Fore.GREEN}Sucessos: {_contador['sucesso']}{Style.RESET_ALL}")
    print(f"{Fore.RED}Falhas:   {_contador['falha']}{Style.RESET_ALL}")

    if _contador["falha"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
