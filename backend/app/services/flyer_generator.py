"""
Serviço de geração automática dos flyers de aniversário do Paparazzi Gold Bar.

Arquitetura (10/08/2026, 3ª revisão da arte): a moldura oficial tem, de
verdade, duas janelas VAZADAS (canal alfa real, não um retângulo preto
desenhado) — uma pra foto do aniversariante e outra, menor, pro cartão de
data/horário. O dia da semana ("SEXTA FEIRA" etc.) continua opaco/fixo na
própria arte.

As coordenadas dessas duas janelas são DETECTADAS EM TEMPO DE EXECUÇÃO a
partir do canal alfa da moldura carregada (`_detectar_areas_vazadas`) — não
são mais medidas a olho nem guardadas como constante. Isso elimina de vez o
trabalho manual de remapear coordenadas toda vez que a arte for atualizada
(3 revisões já teve só nesta sessão) e garante alinhamento perfeito com
qualquer moldura que já venha com essas duas janelas vazadas no padrão
esperado (cartão à esquerda, foto à direita).

Composição, de baixo pra cima:
    1. Base    -> canvas preto sólido, do tamanho da moldura
    2. Foto    -> colada na janela vazada da foto (detectada via alfa)
    3. Moldura -> alpha-composite por cima da base+foto — as áreas opacas
                  da arte cobrem tudo; as duas janelas vazadas revelam o
                  que já foi colado embaixo (foto, ou o preto da base)
    4. Cartão  -> data e horário desenhados dentro da janela vazada do
                  cartão (metade de cima = data, metade de baixo = horário)
    5. Faixa   -> tarja semitransparente na base da caixa da foto, com o
                  nome do aniversariante

Se a detecção de áreas vazadas falhar (arte sem exatamente as 2 janelas
esperadas), o módulo cai num fallback de coordenadas proporcionais
aproximadas — nunca lança exceção nem derruba o cadastro do aniversariante
por causa disso.
"""

import io
import logging
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.app.services import supabase_service

logger = logging.getLogger(__name__)

# Canvas genérico + área da foto aproximada, usados só quando NENHUMA
# moldura é encontrada (Storage nem assets locais) ou quando a detecção de
# áreas vazadas falha de forma inesperada — nunca o caminho normal.
LARGURA_FLYER_FALLBACK = 1080
ALTURA_FLYER_FALLBACK = 1920
AREA_FOTO_PROP_FALLBACK = (0.24, 0.19, 0.80, 0.65)

# Limiar de alfa abaixo do qual um pixel é considerado "vazado" (transparente).
LIMIAR_ALFA_VAZADO = 128

COR_FUNDO_BASE = (0, 0, 0)  # preto puro — amostrado do fundo real da arte, visível através da janela do cartão

# --- Paleta "dourado premium" (10/08/2026, spec visual detalhada pelo
# usuário a partir de referência gerada por IA) ---
COR_DATA = (216, 208, 200)  # #D8D0C8 — bege champagne fosco, sem dourado forte
GRADIENTE_DOURADO = [(184, 117, 0), (242, 185, 0), (201, 133, 0)]  # #B87500 -> #F2B900 -> #C98500
COR_CONTORNO_DOURADO = (138, 90, 0)  # #8A5A00, contorno fino
COR_BRILHO_DOURADO = (255, 210, 80)  # brilho sutil atrás do texto dourado, bem discreto

COR_SOMBRA_TEXTO = (0, 0, 0, 150)
OFFSET_SOMBRA_TEXTO = (3, 3)

# --- Faixa do nome, na base da caixa da foto ---
ALTURA_FAIXA_NOME_FRACAO = 0.20  # fração da altura da caixa da foto

TAMANHO_FONTE_MAXIMO_NOME = 76
TAMANHO_FONTE_MINIMO_NOME = 28
TAMANHO_FONTE_MAXIMO_CARTAO = 56
TAMANHO_FONTE_MINIMO_CARTAO = 20

DIR_ASSETS = Path(__file__).resolve().parent.parent / "assets"
DIR_FONTES = DIR_ASSETS / "fonts"
DIR_TEMPLATES = DIR_ASSETS / "templates"

# Fonte condensada e pesada — usada em todo texto que o backend desenha
# (nome, dia, data, horário). Nunca serifada nem cursiva (pedido explícito
# do usuário, pra bater com a tipografia já usada na própria arte). É uma
# "variable font" (Google Fonts não distribui mais arquivo estático por
# peso) — peso Bold (700) setado explicitamente em _carregar_fonte.
NOME_ARQUIVO_FONTE = "RobotoCondensed-Bold.ttf"
PESO_FONTE_BOLD = 700

# Mapeamento dia da semana (date.weekday(): segunda=0 ... domingo=6) ->
# (template_name, texto exibido no cartão). Só sexta/sábado/domingo têm
# moldura pronta nesta fase — segunda a quinta não é um dia de reserva de
# aniversário esperado neste fluxo (ver TEMPLATE_FALLBACK).
MAPA_DIA_SEMANA_TEMPLATE = {
    4: ("sexta_boteco", "SEXTA FEIRA"),
    5: ("sabado_feijoada", "SÁBADO"),
    6: ("domingo_churrasco", "DOMINGO"),
}

# Template usado quando data_reserva cai num dia sem moldura própria
# (segunda a quinta) — não deveria acontecer no fluxo normal (o Salesbot
# coleta a Data da Reserva diretamente do cliente, sem restringir a
# fim de semana nesta fase), mas evita que o flyer falhe se acontecer.
TEMPLATE_FALLBACK = "domingo_churrasco"
TEXTO_DIA_FALLBACK = "SEU DIA"

TEMPLATES_OFICIAIS = tuple(nome for nome, _ in MAPA_DIA_SEMANA_TEMPLATE.values())


def selecionar_template_e_dia(data_reserva: str | None) -> tuple[str, str]:
    """
    A partir da Data da Reserva (formato "AAAA-MM-DD", já convertida por
    converter_valor_data_kommo em webhooks.py), decide qual moldura usar e
    qual texto de dia da semana desenhar no cartão.

    Se data_reserva vier vazia/inválida ou cair numa segunda-quinta (sem
    moldura própria nesta fase), cai no TEMPLATE_FALLBACK com um aviso no
    log — nunca lança exceção.
    """
    if data_reserva:
        try:
            data = datetime.strptime(data_reserva, "%Y-%m-%d").date()
            mapeado = MAPA_DIA_SEMANA_TEMPLATE.get(data.weekday())
            if mapeado:
                return mapeado
            logger.warning(
                "⚠️ Data da reserva '%s' cai numa %s, sem moldura própria nesta fase. Usando '%s'.",
                data_reserva, data.strftime("%A"), TEMPLATE_FALLBACK,
            )
        except ValueError:
            logger.warning("⚠️ Data da reserva '%s' em formato inesperado. Usando '%s'.", data_reserva, TEMPLATE_FALLBACK)
    else:
        logger.warning("⚠️ Data da reserva ausente. Usando '%s'.", TEMPLATE_FALLBACK)

    return TEMPLATE_FALLBACK, TEXTO_DIA_FALLBACK


def formatar_data_exibicao(data_reserva: str | None) -> str:
    """Converte "AAAA-MM-DD" para "DD/MM" (formato usado no cartão da arte)."""
    if not data_reserva:
        return ""
    try:
        return datetime.strptime(data_reserva, "%Y-%m-%d").strftime("%d/%m")
    except ValueError:
        return ""


def formatar_horario_exibicao(horario: str | None) -> str:
    """
    Converte o valor bruto do Custom Field "Horário da reserva" (ID
    2068854) para o formato "HH:00" usado no cartão da arte.

    O Kommo tem devolvido esse campo como só a hora, sem minutos (ex.:
    valor bruto "12" para meio-dia) — se vier só dígitos, formata como
    hora cheia. Se já vier num formato com separador (ex. "18:30"),
    devolve como está.
    """
    if not horario:
        return ""
    valor = horario.strip()
    if valor.isdigit():
        return f"{int(valor):02d}:00"
    return valor


def generate_flyer(
    foto_bytes: bytes,
    nome: str,
    data_reserva: str | None = None,
    horario: str | None = None,
    template_name: str | None = None,
) -> bytes:
    """
    Gera o flyer de aniversário: moldura oficial do dia + foto do cliente +
    nome + data/horário reais, tudo em memória.

    Args:
        foto_bytes: Bytes da foto original enviada pelo aniversariante.
        nome: Nome completo do aniversariante, exibido na faixa sobre a foto.
        data_reserva: Data da reserva, formato "AAAA-MM-DD". Decide qual
            moldura usar (sexta/sábado/domingo) e alimenta a data exibida
            no cartão. Opcional só por segurança — sem ela, cai no
            TEMPLATE_FALLBACK.
        horario: Valor bruto do Custom Field "Horário da reserva" (ID
            2068854), exibido no cartão.
        template_name: Força um template específico, ignorando o
            mapeamento automático por data_reserva — usado só em testes.

    Returns:
        Bytes do flyer final, já compilado no formato JPEG.

    Raises:
        ValueError: se foto_bytes não for uma imagem válida (a única
            entrada que é, de fato, obrigatória para existir um flyer).
    """
    if template_name is None:
        template_name, texto_dia = selecionar_template_e_dia(data_reserva)
    else:
        texto_dia = next(
            (dia for nome_t, dia in MAPA_DIA_SEMANA_TEMPLATE.values() if nome_t == template_name),
            TEXTO_DIA_FALLBACK,
        )

    try:
        foto = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
    except Exception as e:
        logger.error("Não foi possível processar a foto enviada para o flyer: %s", e)
        raise ValueError("Foto inválida ou corrompida — não foi possível gerar o flyer.") from e

    moldura_bytes = _buscar_bytes_da_moldura(f"moldura_{template_name}.png")

    if moldura_bytes:
        moldura = Image.open(io.BytesIO(moldura_bytes)).convert("RGBA")

        area_cartao = None
        try:
            area_cartao, area_foto = _detectar_areas_vazadas(moldura)
        except ValueError as e:
            logger.warning("⚠️ %s — usando área da foto aproximada (proporcional) e sem cartão de data/horário.", e)
            area_foto = _area_em_pixels(AREA_FOTO_PROP_FALLBACK, *moldura.size)

        canvas = _compor_moldura_e_foto(moldura, foto, area_foto)

        if area_cartao:
            forcar_dia = template_name != _template_esperado_para_dia(texto_dia)
            _desenhar_cartao_dia_data_horario(
                canvas, area_cartao, texto_dia, formatar_data_exibicao(data_reserva), formatar_horario_exibicao(horario), forcar_dia
            )

        _desenhar_faixa_nome(canvas, nome, area_foto)
    else:
        logger.warning(
            "Moldura 'moldura_%s.png' não encontrada (Supabase Storage nem %s). "
            "Flyer será gerado sem a camada decorativa nem o cartão de data/horário.",
            template_name, DIR_TEMPLATES,
        )
        canvas = _montar_canvas_fallback(foto, nome)

    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="JPEG", quality=92)

    logger.info("Flyer gerado com sucesso para '%s' (template=%s).", nome, template_name)
    return buffer.getvalue()


def _template_esperado_para_dia(texto_dia: str) -> str | None:
    """Descobre qual template_name normalmente exibe `texto_dia` — usado só pra decidir se o dia da semana da arte precisa ser sobrescrito."""
    for nome_t, dia in MAPA_DIA_SEMANA_TEMPLATE.values():
        if dia == texto_dia:
            return nome_t
    return None


def _compor_moldura_e_foto(moldura: Image.Image, foto: Image.Image, area_foto: tuple[int, int, int, int]) -> Image.Image:
    """
    Monta a base do flyer: cola a foto do cliente na janela vazada da
    moldura (já detectada por quem chama, via canal alfa) e compõe a
    moldura por cima.

    Returns:
        Canvas RGB pronto pra receber o cartão/faixa de texto.
    """
    base = Image.new("RGBA", moldura.size, (*COR_FUNDO_BASE, 255))

    foto_recortada = _redimensionar_com_crop_centralizado(foto, area_foto[2] - area_foto[0], area_foto[3] - area_foto[1])
    base.paste(foto_recortada, (area_foto[0], area_foto[1]))

    return Image.alpha_composite(base, moldura).convert("RGB")


def _detectar_areas_vazadas(moldura: Image.Image) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """
    Detecta, via canal alfa da própria moldura, as coordenadas exatas das
    duas janelas vazadas da arte: a área do cartão (data/horário, mais
    estreita) e a área da foto (mais larga). O layout da casa sempre põe o
    cartão à esquerda da foto — a região com menor `x` é sempre o cartão.

    Nunca depende de coordenadas medidas a olho: varre as colunas da
    máscara de transparência procurando exatamente 2 faixas horizontais
    contíguas com algum pixel vazado, e calcula o bounding box exato de
    cada uma.

    Returns:
        (area_cartao, area_foto), cada uma (esquerda, topo, direita, baixo).

    Raises:
        ValueError: se a arte não tiver exatamente 2 janelas vazadas
            distintas (arte com layout inesperado) — quem chama decide o
            fallback.
    """
    alpha = moldura.getchannel("A")
    largura, altura = moldura.size
    mascara = alpha.point(lambda p: 255 if p < LIMIAR_ALFA_VAZADO else 0)
    px = mascara.load()

    colunas_com_vazado = [any(px[x, y] for y in range(0, altura, 3)) for x in range(largura)]

    regioes_x = []
    inicio = None
    for x, tem_vazado in enumerate(colunas_com_vazado + [False]):
        if tem_vazado and inicio is None:
            inicio = x
        elif not tem_vazado and inicio is not None:
            regioes_x.append((inicio, x))
            inicio = None

    if len(regioes_x) != 2:
        raise ValueError(f"esperava 2 janelas vazadas (cartão + foto) na moldura, encontrei {len(regioes_x)}")

    regioes_x.sort()
    areas = []
    for x_ini, x_fim in regioes_x:
        bbox_local = mascara.crop((x_ini, 0, x_fim, altura)).getbbox()
        areas.append((x_ini + bbox_local[0], bbox_local[1], x_ini + bbox_local[2], bbox_local[3]))

    return areas[0], areas[1]  # (cartão, foto) — cartão é sempre a região mais à esquerda


def _desenhar_faixa_nome(canvas: Image.Image, nome: str, area_foto: tuple[int, int, int, int]) -> None:
    """
    Desenha uma faixa semitransparente na base da caixa da foto, com o
    nome do aniversariante no mesmo tratamento visual "dourado premium" do
    horário (gradiente + contorno fino + sombra + brilho sutil).
    """
    esquerda, topo, direita, baixo = area_foto
    altura_caixa_foto = baixo - topo

    altura_faixa = round(altura_caixa_foto * ALTURA_FAIXA_NOME_FRACAO)
    topo_faixa = baixo - altura_faixa

    camada = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(camada)
    draw.rectangle((esquerda, topo_faixa, direita, baixo), fill=(8, 8, 8, 175))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), camada).convert("RGB"), (0, 0))

    largura_area_texto = (direita - esquerda) - 40  # margem lateral de 20px de cada lado
    centro = (esquerda + (direita - esquerda) // 2, topo_faixa + altura_faixa // 2)
    _desenhar_texto_com_efeito(
        canvas, nome, centro, largura_area_texto,
        tamanho_maximo=TAMANHO_FONTE_MAXIMO_NOME, tamanho_minimo=TAMANHO_FONTE_MINIMO_NOME,
        cores_gradiente=GRADIENTE_DOURADO, cor_contorno=COR_CONTORNO_DOURADO, largura_contorno=2,
        cor_brilho=COR_BRILHO_DOURADO,
    )


def _desenhar_cartao_dia_data_horario(
    canvas: Image.Image, area_cartao: tuple[int, int, int, int], texto_dia: str, texto_data: str, texto_horario: str, forcar_dia: bool
) -> None:
    """
    Desenha data e horário dentro da janela vazada do cartão (metade de
    cima = data, metade de baixo = horário). O dia da semana ("SEXTA
    FEIRA" etc.) já vem fixo/opaco na própria arte — só é apagado e
    reescrito quando `forcar_dia=True` (caminho de fallback, onde o
    template usado não bate com o dia real da semana), numa área estimada
    logo acima do cartão (o dia da semana não faz parte da janela vazada,
    então não pode ser detectado via canal alfa).
    """
    esquerda, topo, direita, baixo = area_cartao
    altura_cartao = baixo - topo
    meio = topo + altura_cartao // 2

    area_data = (esquerda, topo, direita, meio - 4)
    area_horario = (esquerda, meio + 4, direita, baixo)

    if forcar_dia and texto_dia:
        area_dia = (esquerda, topo - 170, direita, topo - 10)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(area_dia, fill=COR_FUNDO_BASE)
        centro_dia = ((area_dia[0] + area_dia[2]) // 2, (area_dia[1] + area_dia[3]) // 2)
        _desenhar_texto_com_efeito(
            canvas, texto_dia, centro_dia, (direita - esquerda) - 10,
            tamanho_maximo=TAMANHO_FONTE_MAXIMO_CARTAO, tamanho_minimo=TAMANHO_FONTE_MINIMO_CARTAO,
            cor_solida=COR_DATA,
        )

    if texto_data:
        centro = ((area_data[0] + area_data[2]) // 2, (area_data[1] + area_data[3]) // 2)
        _desenhar_texto_com_efeito(
            canvas, texto_data, centro, (direita - esquerda) - 10,
            tamanho_maximo=TAMANHO_FONTE_MAXIMO_CARTAO, tamanho_minimo=TAMANHO_FONTE_MINIMO_CARTAO,
            cor_solida=COR_DATA,
        )

    if texto_horario:
        centro = ((area_horario[0] + area_horario[2]) // 2, (area_horario[1] + area_horario[3]) // 2)
        _desenhar_texto_com_efeito(
            canvas, texto_horario, centro, (direita - esquerda) - 10,
            tamanho_maximo=TAMANHO_FONTE_MAXIMO_CARTAO, tamanho_minimo=TAMANHO_FONTE_MINIMO_CARTAO,
            cores_gradiente=GRADIENTE_DOURADO, cor_contorno=COR_CONTORNO_DOURADO, largura_contorno=2,
            cor_brilho=COR_BRILHO_DOURADO,
        )


def _desenhar_texto_com_efeito(
    canvas: Image.Image,
    texto: str,
    centro: tuple[int, int],
    largura_disponivel: int,
    tamanho_maximo: int,
    tamanho_minimo: int,
    cor_solida: tuple[int, int, int] | None = None,
    cores_gradiente: list[tuple[int, int, int]] | None = None,
    cor_contorno: tuple[int, int, int] | None = None,
    largura_contorno: int = 0,
    cor_brilho: tuple[int, int, int] | None = None,
) -> None:
    """
    Renderiza `texto` centralizado em `centro` (tanto horizontal quanto
    verticalmente), num tile RGBA próprio (com folga pra sombra/contorno/
    brilho não cortarem), depois compõe esse tile sobre o canvas. Suporta
    preenchimento sólido (`cor_solida`) ou gradiente vertical
    (`cores_gradiente`), sempre com sombra suave; contorno fino e brilho
    discreto são opcionais (usados no texto dourado).

    Auto-scaling de fonte: começa em `tamanho_maximo` e encolhe (nunca
    abaixo de `tamanho_minimo`) até caber em `largura_disponivel`.
    """
    fonte = _calcular_fonte_com_auto_scaling(texto, largura_disponivel, tamanho_maximo, tamanho_minimo, largura_contorno)

    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bbox = tmp_draw.textbbox((0, 0), texto, font=fonte, stroke_width=largura_contorno)
    largura_texto = bbox[2] - bbox[0]
    altura_texto = bbox[3] - bbox[1]

    folga = max(abs(OFFSET_SOMBRA_TEXTO[0]), abs(OFFSET_SOMBRA_TEXTO[1])) + largura_contorno + (14 if cor_brilho else 0) + 8
    tile_w = largura_texto + folga * 2
    tile_h = altura_texto + folga * 2
    origem = (folga - bbox[0], folga - bbox[1])

    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))

    # 1. Sombra suave.
    camada_sombra = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    d_sombra = ImageDraw.Draw(camada_sombra)
    pos_sombra = (origem[0] + OFFSET_SOMBRA_TEXTO[0], origem[1] + OFFSET_SOMBRA_TEXTO[1])
    d_sombra.text(pos_sombra, texto, font=fonte, fill=COR_SOMBRA_TEXTO, stroke_width=largura_contorno, stroke_fill=COR_SOMBRA_TEXTO)
    camada_sombra = camada_sombra.filter(ImageFilter.GaussianBlur(2))
    tile = Image.alpha_composite(tile, camada_sombra)

    # 2. Brilho discreto (só quando pedido — texto dourado).
    if cor_brilho:
        camada_brilho = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        d_brilho = ImageDraw.Draw(camada_brilho)
        d_brilho.text(origem, texto, font=fonte, fill=(*cor_brilho, 110))
        camada_brilho = camada_brilho.filter(ImageFilter.GaussianBlur(5))
        tile = Image.alpha_composite(tile, camada_brilho)

    # 3. Contorno fino (desenhado sem preenchimento — só a borda do glifo).
    if cor_contorno and largura_contorno > 0:
        d_contorno = ImageDraw.Draw(tile)
        d_contorno.text(origem, texto, font=fonte, fill=(0, 0, 0, 0), stroke_width=largura_contorno, stroke_fill=(*cor_contorno, 255))

    # 4. Preenchimento — sólido ou gradiente vertical, recortado exatamente na forma das letras.
    mascara = Image.new("L", (tile_w, tile_h), 0)
    ImageDraw.Draw(mascara).text(origem, texto, font=fonte, fill=255)

    if cores_gradiente:
        preenchimento = _criar_gradiente_vertical((tile_w, tile_h), cores_gradiente)
    else:
        preenchimento = Image.new("RGB", (tile_w, tile_h), cor_solida or (255, 255, 255))

    preenchimento_rgba = preenchimento.convert("RGBA")
    preenchimento_rgba.putalpha(mascara)
    tile = Image.alpha_composite(tile, preenchimento_rgba)

    x_destino = centro[0] - tile_w // 2
    y_destino = centro[1] - tile_h // 2
    fundo_recorte = canvas.convert("RGBA").crop((x_destino, y_destino, x_destino + tile_w, y_destino + tile_h))
    canvas.paste(Image.alpha_composite(fundo_recorte, tile), (x_destino, y_destino))


def _criar_gradiente_vertical(tamanho: tuple[int, int], cores: list[tuple[int, int, int]]) -> Image.Image:
    """Gradiente vertical suave passando por todas as cores em `cores`, de cima pra baixo, esticado para `tamanho`."""
    largura, altura = tamanho
    altura = max(altura, 1)
    coluna = Image.new("RGB", (1, altura))
    n = len(cores)
    for y in range(altura):
        posicao = y / max(altura - 1, 1) * (n - 1)
        indice = min(int(posicao), n - 2)
        fracao = posicao - indice
        cor = tuple(round(cores[indice][c] + (cores[indice + 1][c] - cores[indice][c]) * fracao) for c in range(3))
        coluna.putpixel((0, y), cor)
    return coluna.resize((max(largura, 1), altura))


def _montar_canvas_fallback(foto: Image.Image, nome: str) -> Image.Image:
    """Sem nenhuma moldura disponível: canvas genérico só com foto + nome, sem cartão de data/horário."""
    canvas = Image.new("RGB", (LARGURA_FLYER_FALLBACK, ALTURA_FLYER_FALLBACK), color=COR_FUNDO_BASE)
    area_foto = _area_em_pixels(AREA_FOTO_PROP_FALLBACK, LARGURA_FLYER_FALLBACK, ALTURA_FLYER_FALLBACK)
    esquerda, topo, direita, baixo = area_foto
    foto_recortada = _redimensionar_com_crop_centralizado(foto, direita - esquerda, baixo - topo)
    canvas.paste(foto_recortada, (esquerda, topo))
    _desenhar_faixa_nome(canvas, nome, area_foto)
    return canvas


def _area_em_pixels(area_prop: tuple[float, float, float, float], largura: int, altura: int) -> tuple[int, int, int, int]:
    esquerda_p, topo_p, direita_p, baixo_p = area_prop
    return (round(esquerda_p * largura), round(topo_p * altura), round(direita_p * largura), round(baixo_p * altura))


def _redimensionar_com_crop_centralizado(imagem: Image.Image, largura_destino: int, altura_destino: int) -> Image.Image:
    """
    Redimensiona a imagem mantendo a proporção e recorta o excedente pelo
    centro, garantindo que ela preencha exatamente largura_destino x
    altura_destino sem distorcer nem deixar sobras (efeito "cover", como em CSS).
    """
    largura_destino = max(largura_destino, 1)
    altura_destino = max(altura_destino, 1)
    proporcao_origem = imagem.width / imagem.height
    proporcao_destino = largura_destino / altura_destino

    if proporcao_origem > proporcao_destino:
        nova_altura = altura_destino
        nova_largura = round(nova_altura * proporcao_origem)
    else:
        nova_largura = largura_destino
        nova_altura = round(nova_largura / proporcao_origem)

    imagem_redimensionada = imagem.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)

    esquerda = (nova_largura - largura_destino) // 2
    topo = (nova_altura - altura_destino) // 2
    caixa_corte = (esquerda, topo, esquerda + largura_destino, topo + altura_destino)

    return imagem_redimensionada.crop(caixa_corte)


def _buscar_bytes_da_moldura(nome_arquivo: str) -> bytes | None:
    """Busca o template primeiro no Supabase Storage e, se não achar, em assets/templates/ local."""
    try:
        moldura_bytes = supabase_service.buscar_moldura_do_storage(nome_arquivo)
        if moldura_bytes:
            return moldura_bytes
    except Exception as e:
        logger.info("Erro ao consultar o Supabase Storage por '%s': %s. Tentando assets locais.", nome_arquivo, e)

    caminho_local = DIR_TEMPLATES / nome_arquivo
    if caminho_local.is_file():
        return caminho_local.read_bytes()

    return None


def listar_templates_disponiveis() -> list[str]:
    """
    Lista os template_name que já têm um PNG presente em backend/app/assets/templates/
    (não reflete o que existe no Supabase Storage). Utilitário de apoio para
    debug/ops — não é usado no caminho principal de geração do flyer.
    """
    if not DIR_TEMPLATES.is_dir():
        return []

    disponiveis = []
    for template_name in TEMPLATES_OFICIAIS:
        if (DIR_TEMPLATES / f"moldura_{template_name}.png").is_file():
            disponiveis.append(template_name)

    return disponiveis


def _calcular_fonte_com_auto_scaling(
    texto: str,
    largura_disponivel: int,
    tamanho_maximo: int,
    tamanho_minimo: int,
    largura_contorno: int = 0,
):
    """
    Calcula o tamanho de fonte ideal partindo de `tamanho_maximo` e
    encolhendo (nunca abaixo de `tamanho_minimo`) até o texto renderizado
    (já contando o contorno, se houver) caber na largura disponível.
    """
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tamanho_fonte = tamanho_maximo
    fonte = _carregar_fonte(tamanho_fonte)

    while tamanho_fonte > tamanho_minimo:
        caixa = tmp_draw.textbbox((0, 0), texto, font=fonte, stroke_width=largura_contorno)
        largura_texto = caixa[2] - caixa[0]
        if largura_texto <= largura_disponivel:
            break
        tamanho_fonte -= 2
        fonte = _carregar_fonte(tamanho_fonte)

    return fonte


def _carregar_fonte(tamanho: int):
    """
    Carrega a fonte condensada da casa (Roboto Condensed Bold — variable
    font, peso 700 setado explicitamente); se não existir ou falhar, usa a
    fonte padrão do Pillow como fallback seguro.

    NOTA: a fonte padrão do Pillow (`ImageFont.load_default`) não tem os
    acentos do português — nomes como "João" ou o texto "SÁBADO" saem com
    o caractere quebrado (□) em vez do acento. Evite ficar sem o arquivo
    `RobotoCondensed-Bold.ttf` em produção.
    """
    caminho_fonte = DIR_FONTES / NOME_ARQUIVO_FONTE

    if caminho_fonte.is_file():
        try:
            fonte = ImageFont.truetype(str(caminho_fonte), tamanho)
            try:
                fonte.set_variation_by_axes([PESO_FONTE_BOLD])
            except Exception:
                pass  # fonte estática comum (não variable) — segue com o peso que já carregou
            return fonte
        except Exception as e:
            logger.warning("Falha ao carregar a fonte '%s': %s. Usando fonte padrão do Pillow.", caminho_fonte, e)

    return ImageFont.load_default(size=tamanho)
