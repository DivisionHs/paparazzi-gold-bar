# Templates de Moldura do Flyer de Aniversário

Coloque aqui as molduras oficiais da casa, nomeadas como:

```
moldura_<template_name>.png
```

## Templates oficiais da Fase 1 (atualizado em 10/08/2026)

Um template por dia de evento da semana selecionado automaticamente por
`flyer_generator.selecionar_template_e_dia()` a partir do dia da semana de
`data_reserva` (ver `MAPA_DIA_SEMANA_TEMPLATE`):

| `template_name`     | Arquivo esperado                   | Evento                          |
|----------------------|-------------------------------------|-----------------------------------|
| `sexta_boteco`       | `moldura_sexta_boteco.png`          | Sexta — Boteco/Churrasco          |
| `sabado_feijoada`    | `moldura_sabado_feijoada.png`       | Sábado — Feijoada                 |
| `domingo_churrasco`  | `moldura_domingo_churrasco.png`     | Domingo — Churrasco               |

`sabado_noite` **não é usado nesta fase** (arte ainda não entregue) — se um
dia virar necessário, adicione a entrada em `MAPA_DIA_SEMANA_TEMPLATE` e o
arquivo `moldura_sabado_noite.png` aqui; nenhuma outra mudança de código é
necessária.

Os 3 arquivos hoje na pasta já são a **arte oficial da casa** (2ª revisão,
10/08/2026) — opacas, uniformes em 1080×1920 (9:16 exato). O dia da semana
("SEXTA FEIRA" etc.) vem fixo/impresso na própria arte; data e horário
ficam num espaço em branco (fundo preto já desenhado) preenchido pelo
Pillow. A moldura vira o próprio canvas de base do flyer; a foto do
cliente, a data/horário e o nome do aniversariante são sobrepostos por
cima usando coordenadas *proporcionais* ao tamanho do arquivo (ver
CLAUDE.md 4.6) — se a arte for atualizada mantendo o mesmo layout (posição
da caixa da foto e do cartão lateral), basta substituir o PNG com o mesmo
nome, sem mudar código. Se o layout mudar de posição, as constantes
`AREA_FOTO_PROP`/`AREA_CARTAO_*_PROP` em `flyer_generator.py` precisam ser
remapeadas (grade de coordenadas sobreposta na arte + zoom nas áreas).

`backup_molduras/` guarda a versão anterior da arte (com texto fictício de
data/hora já impresso) — só como referência visual/histórico, não é lida
pelo código.

## Ordem de busca e fallback

`flyer_generator.py` procura a moldura primeiro no Supabase Storage
(subpasta `molduras/` do bucket `fotos-aniversariantes`) e só depois aqui,
nos assets locais. Se `template_name` não corresponder a nenhum arquivo em
nenhum dos dois lugares, o flyer é gerado num canvas genérico, só com foto
+ nome, sem a moldura nem o cartão de dia/data/horário — um PNG faltando
nunca é motivo para o cadastro do aniversariante falhar.
