# Fontes do Flyer de Aniversário

`RobotoCondensed-Bold.ttf` (10/08/2026) — baixada do repositório oficial do
Google Fonts (`google/fonts`, licença OFL, livre para uso comercial), usada
em todo texto que o backend desenha no flyer: nome do aniversariante e o
cartão de dia/data/horário. Trocou a `PlayfairDisplay-Bold.ttf` (elegante,
serifada) por pedido do usuário — a tipografia precisava ser condensada e
pesada, batendo com o estilo já usado na própria arte das molduras
("SEXTA FEIRA" etc.), nunca serifada nem cursiva.

É uma "variable font" (Google Fonts não distribui mais arquivos estáticos
por peso para esta família) — `flyer_generator._carregar_fonte()` seleciona
o peso Bold (700) via `set_variation_by_axes([700])` depois de carregar.

Se o arquivo não existir (ou não puder ser carregado), `flyer_generator.py`
usa automaticamente a fonte padrão do Pillow (`ImageFont.load_default`)
como fallback seguro — mas essa fonte padrão **não tem os acentos do
português** (nomes como "João" ou o texto "SÁBADO" saem com o caractere
quebrado). Evite ficar sem este arquivo em produção.

`PlayfairDisplay-Bold.ttf` continua no repositório (não é mais usada pelo
código, mas é inofensiva manter caso sirva pra alguma peça futura).
