# CLAUDE.md — Diretrizes e Guia do Repositório (Paparazzi Gold Bar)

Este arquivo orienta o comportamento do Claude Code ao trabalhar com o código deste repositório. Ele define a arquitetura do projeto, padrões de código, comandos e regras de negócio essenciais para garantir a integridade do sistema.

## 1. Idioma Padrão e Comunicação

- **Idioma Obrigatório:** Português do Brasil (pt-BR).
- **Escopo:** Toda a comunicação, explicações, comentários no código, mensagens de erro, commits e documentações geradas ou alteradas DEVEM ser estritamente em pt-BR.

## 2. Contexto do Produto e Leitura Obrigatória

Antes de propor, criar ou alterar qualquer funcionalidade, regra de negócio, fluxo de dados ou rota no código, é obrigatório ler e consultar os documentos da pasta `docs/`:

- `docs/visao_geral_paparazzi.md`
- `docs/paparazzi_resumo_projeto.md`
- `docs/diario_projeto.md`

## 3. Mapeamento do Repositório e Arquitetura

O ecossistema do Paparazzi Gold Bar é composto por três aplicações independentes integradas a um backend central e ao Supabase (PostgreSQL + Storage).

### 3.1. Backend (`backend/`)

- **Tecnologia:** Serviço em FastAPI (Python).
- **Responsabilidades:**
  - Processar o webhook único do Kommo CRM (`POST /webhooks/kommo`), disparado quando o Lead entra na etapa "aniversário confirmado".
  - Processar e gerar flyers com a foto do aniversariante utilizando a biblioteca Pillow.
  - Gerenciar a API de convidados (confirmação de presença, validação e analytics).
  - Controlar a fila de abertura e sincronização de comandas no ERP Epoc.

### 3.2. Frontend Principal (`frontend/`)

- **Tecnologia:** Aplicação Flutter (Multiplataforma).
- **Módulos:**
  - **Flutter Web (Formulário do Convidado):** Rota `/cadastro?token=<UUID>`. Exibe a foto do aniversariante (com o flyer), valida os dados do convidado e gera o QR Code individual pós-cadastro.
  - **Portaria (Interface Operacional):** Módulo para leitura de QR Code e busca por CPF/Nome com validação em tempo real na recepção:
    - 🟢 **Sinal Verde:** Entrada autorizada e liberação de comanda.
    - 🔴 **Sinal Vermelho:** Entrada negada (inválido, duplicado ou não cadastrado).

### 3.3. Protótipos de Teste (`frontend-lista/`)

- **Tecnologia:** Arquivos estáticos em HTML + Tailwind CSS.
- **Propósito:** Validação rápida de layout, formulários e testes locais leves. Não deve ser utilizado como cliente principal em produção.

## 4. Diretrizes e Regras de Negócio (MVP Julho/2026)

### 4.1. Seleção de Datas do Salesbot (Kommo CRM)

- **Regra Rígida:** NÃO alterar o fluxo de menus e seleção de datas do Salesbot configurado no Kommo CRM neste ciclo de MVP.
- **Observação:** Qualquer ajuste no fluxo de mensagens ou datas do robô está reservado exclusivamente para o rebranding futuro.
- **Decisão de 05/08/2026 — cálculo automático de data descontinuado nesta fase:** a ideia anterior de calcular a "Data da reserva" no backend a partir de um Custom Field "Nome da semana" (ID `2068768`, botões de Sexta/Sábado/Domingo) foi **descontinuada/adiada** para este ciclo do MVP. O campo "Nome da semana" continua existindo no Salesbot, mas o backend não lê nem processa mais esse campo — a Data da reserva agora é coletada **diretamente** do cliente pelo próprio Salesbot (ver 4.2). Essa automação fica catalogada como ideia de aprimoramento futuro (Fase 2) — ver `docs/diario_projeto.md`.

### 4.2. Webhook Único da Etapa "PROCESSANDO FLYER" (Kommo CRM)

- **Gatilho:** o Lead precisa chegar na etapa (`status_id`) **`109983139`** — **"PROCESSANDO FLYER"** — no funil do Kommo. Essa etapa é exclusiva para este propósito (distinta da etapa anterior `109630671`, usada mais cedo no funil só para iniciar a coleta de nome/foto no Salesbot). O disparo em `109983139` é o **único** disparo de webhook do fluxo (`POST /webhooks/kommo`); não há mais coleta incremental via chat nem rota separada para mensagens (`/webhooks/chat` foi removida).
- **Coleta direta pelo Salesbot:** antes de mover o Lead para a etapa `109983139`, o Salesbot coleta sequencialmente e de forma direta do cliente os 5 dados obrigatórios, gravando cada um no respectivo Custom Field nativo do Kommo:
  1. Data da Reserva (ID `2068460`).
  2. Horário da Reserva (ID `2068854`).
  3. Estimativa de Convidados (ID `2068456`).
  4. Nome do Flyer (ID `2068452`).
  5. Foto do Aniversariante (ID `2068458`, Custom Field de arquivo — o backend baixa a foto direto da URL desse campo).
- **Estratégia de Consulta Ativa (decisão de 06/08/2026 — "Opção A"):** o webhook em si é tratado só como um **sinalizador leve**, carregando apenas `lead_id` e `status_id`. O backend **nunca lê valores de Custom Fields do corpo do próprio webhook** — assim que recebe o sinal de que o Lead chegou em `109983139`, ele faz um `GET` autenticado e imediato em `/api/v4/leads/{id}` direto na API do Kommo (`kommo_service.buscar_custom_fields_lead`) para buscar os valores **atualizados na hora** dos 5 Custom Fields. Essa mudança elimina o problema de payloads de webhook "frios" (campos vazios/`—`) que ocorria quando a gravação do Salesbot ainda não tinha propagado no Kommo no instante exato do disparo.
- **Processamento consolidado:** com os dados frescos da consulta ativa em mãos, o backend valida se os 5 campos estão preenchidos, envia **dois arquivos** ao Supabase Storage (`fotos-aniversariantes`) — a foto original do aniversariante (`foto_perfil_url`, direto do Custom Field `2068458`, sem nenhum processamento) e o flyer composto por ela (`foto_url`, via Pillow) — e executa o único upsert do fluxo na tabela `aniversariantes` (com `token_exclusivo` gerado na hora), devolvendo o link da lista. **Não existe gate de confirmação/resumo no backend** — a chegada na etapa `109983139` já é considerada a confirmação (o Kommo/Salesbot só move o Lead para essa etapa depois de coletar tudo).
- **Idempotência contra reentrega do webhook (decisão de 07/08/2026):** o Kommo entrega webhook em modelo "at least once" — confirmado em teste manual que o mesmo `lead_id` pode chegar 2-3 vezes seguidas na etapa `109983139` para um único evento real. Antes de qualquer trabalho pesado (consulta ativa, download, Pillow, Storage), `processar_lead_confirmado()` consulta se já existe um registro em `aniversariantes` para aquele `kommo_lead_id`; se existir, a reentrega é ignorada (só log, sem reprocessar). Sem essa checagem, cada reentrega gerava um `token_exclusivo` novo, invalidando silenciosamente o link já enviado ao cliente. Como segunda camada de defesa, os dois uploads no Storage usam nomes **determinísticos** por `lead_id` (`flyer_{lead_id}.jpg`, `foto_perfil_{lead_id}.jpg`, com `x-upsert: true`) — mesmo numa corrida rara entre reentregas quase simultâneas, o resultado é sobrescrita do mesmo objeto, nunca acúmulo de arquivos novos no bucket.
- **Ack imediato + processamento em background (decisão de 07/08/2026):** investigando por que o mesmo lead reentregava o webhook, o terminal do ngrok mostrou vários `POST /webhooks/kommo` empilhados sem `200 OK` até um finalmente completar — sintoma de o Kommo interpretar a demora da rota (consulta ativa + download do CDN + 2 uploads no Storage + insert, tudo síncrono, antes de responder) como falha e reenviar o mesmo webhook por timeout. A causa raiz não era duplicidade de disparo do Kommo/Salesbot nem do ngrok, e sim a rota demorar demais para responder. Correção: `POST /webhooks/kommo` agora só faz a extração leve de `lead_id`/`status_id` e o filtro de etapa de forma síncrona, agenda todo o resto (`processar_lead_confirmado`) via `BackgroundTasks` do FastAPI, e responde `{"status": "recebido", ...}` imediatamente — o Kommo recebe o ACK rápido e para de reenviar. O resultado real do processamento (sucesso, campos faltando, idempotência) só aparece nos logs do Uvicorn, não mais no corpo da resposta HTTP (ver `test_kommo.py` para o roteiro atualizado de como observar isso num teste manual).
- **Diagnóstico:** se a consulta ativa retornar algum dos 5 campos vazio, o backend loga um aviso com exatamente quais estão faltando e ignora o processamento (não insere nada parcial no Supabase) — ver `CAMPOS_OBRIGATORIOS` em `backend/app/routes/webhooks.py`. Se a própria consulta ao Kommo falhar (timeout, HTTP erro, credencial ausente), o backend também aborta com segurança em vez de seguir com dados incompletos.
- **Entrega do flyer ao cliente via Custom Field + Salesbot (decisão de 10/08/2026):** investigado o envio do flyer direto pelo chat via API (Chats API/amoJo, disparo de Salesbot por API) — nenhum dos dois caminhos se mostrou viável para esta integração: a Chats API é escopada por integração dona do canal (WhatsApp/Instagram/Facebook nesta conta pertencem à integração nativa do próprio Kommo com a Meta, não à integração privada do projeto), e não existe endpoint de disparo de Salesbot via API nesta conta (`/leads/{id}/salesbot/run` e variações retornam 404). A solução adotada: o backend grava (`kommo_service.atualizar_custom_fields_lead`, `PATCH /api/v4/leads/{id}`) a URL pública do flyer no Custom Field **"URL do Flyer"** (ID `2069404`) assim que o cadastro é salvo no Supabase — validado empiricamente que o Salesbot consegue **ler** esse valor de volta numa mensagem via merge tag `{{lead.cf.2069404}}`, desde que se use o **ID numérico** do campo (usar o nome do campo, ex. `{{lead.cf.dt1}}`, não funciona — o Kommo apenas imprime o texto literal sem substituir). Existe também o Custom Field **"Link do Formulário"** (ID `2069406`), já criado no Kommo mas **ainda não escrito pelo backend** — o link de cadastro do convidado hoje aponta para um domínio (`paparazzigoldbar.com.br`) diferente do domínio real do Vercel (`app-paparazzi.vercel.app`), e essa correção fica para uma etapa futura. A gravação do Custom Field é *best-effort* (não desfaz o cadastro no Supabase se falhar) e roda dentro do mesmo `processar_lead_confirmado()` em background, sem depender de nenhum evento novo do Kommo.
- **Link do flyer força download em vez de abrir no navegador (decisão de 10/08/2026):** com o botão dinâmico do Salesbot funcionando, o cliente reportou que o clique abria a imagem direto no navegador — exigindo print (perde qualidade, e o flyer final terá proporção fixa que o print distorce) em vez de baixar o arquivo original. Corrigido em `supabase_service.upload_flyer()`: a URL pública do flyer devolvida passou a incluir o parâmetro `?download=<nome>` (validado empiricamente via `HEAD`/`GET` contra um arquivo real do bucket — sem o parâmetro, a resposta não tem `Content-Disposition`; com ele, vem `Content-Disposition: attachment`, fazendo o navegador/WhatsApp baixar em vez de exibir). Só afeta a URL do flyer (`foto_url`/Custom Field `2069404`) — a URL da foto original (`foto_perfil_url`) não leva o parâmetro, pois continua sendo carregada normalmente (`Image.network`) no formulário do convidado, onde `Content-Disposition: attachment` não teria efeito de qualquer forma (só importa em navegação direta do navegador).
- **Resolução da foto (URL do CDN montada, não a API de arquivos):** o Custom Field "Foto do aniversariante" (`2068458`) devolve um `dict` de metadados (`file_uuid`, `version_uuid`, `file_name`, ...), não uma URL pronta. O endpoint oficial `GET /api/v4/files/{uuid}` **devolve 404 nesta conta** e não é usado — e o dict também **não traz nenhuma URL pronta em nenhuma chave**. A URL de download é **montada** concatenando a base fixa do CDN da conta (`https://drive-g.kommo.com/download/662da799-7bfe-52a0-af12-661479954047`) com `file_uuid`, `version_uuid` e `file_name` (URL-encoded), via `kommo_service.montar_url_cdn_arquivo()` (sem nenhuma chamada de rede extra), e só então validada por `eh_url_http_valida()` antes do download.
- **Download com `follow_redirects=True`:** a CDN de arquivos do Kommo (`drive-g.kommo.com`) responde com `301 Moved Permanently` antes de entregar o binário da imagem — o `httpx.AsyncClient` que baixa a foto em `webhooks.py` precisa desse parâmetro explícito, senão `resposta_imagem.content` vem vazio/redirecionamento em vez da foto real.
- **✅ Status validado end-to-end (06/08/2026):** fluxo completo confirmado em testes reais — webhook sinalizador → consulta ativa → montagem da URL do CDN → download da foto (com redirect) → geração do flyer (Pillow) → upload no Supabase Storage (`fotos-aniversariantes`) → `INSERT` em `aniversariantes`.
- **Status de implementação (06/08/2026, atualizado em 10/08/2026):** implementado em `backend/app/routes/webhooks.py` (`receber_webhook_kommo` + `processar_lead_confirmado` + `finalizar_cadastro_aniversariante`) e `backend/app/services/kommo_service.py` (`buscar_custom_fields_lead` para leitura, `atualizar_custom_fields_lead` para escrita), com `KOMMO_TARGET_STATUS_ID=109983139` no `.env`. As funções antigas de PATCH (`atualizar_nome_lead`, `atualizar_data_reserva_lead`), removidas em 06/08 por falta de uso, não voltaram — `atualizar_custom_fields_lead` é uma função nova, escrita para o propósito específico de devolver a URL do flyer ao Lead (ver decisão de 10/08/2026 acima).

### 4.3. Segurança e Identificadores (Tokens)

- **Geração de Tokens:** Uso obrigatório de UUID v4 para identificadores públicos:
  - `token_exclusivo`: Identificador do aniversariante no link enviado via WhatsApp.
  - `qr_code_token`: Identificador único do convidado embutido no QR Code.
- **Restrição:** Jamais expor IDs sequenciais do banco de dados ou dados sensíveis (ex: CPF puro) em URLs ou QR Codes.

### 4.4. Validação Rígida de CPF

- **Validação Dupla:** Algoritmo de validação de CPF obrigatório tanto no Flutter (frontend) quanto no FastAPI (backend).
- **Unicidade de Lista:** É proibido o cadastro duplicado de um mesmo CPF na lista do mesmo aniversariante. O backend deve tratar a violação de constraint do PostgreSQL e retornar uma mensagem clara em pt-BR.

### 4.5. Resiliência Operacional (Offline-First e ERP Epoc)

- **Validação Síncrona na Portaria:** A resposta da consulta na portaria deve ser instantânea na tela (🟢 / 🔴).
- **Processamento Assíncrono:** A comunicação com o ERP Epoc para abertura automática de comanda deve ser executada em background worker com política de re-tentativas (retry loop e exponential backoff).

### 4.6. Geração do Flyer (Pillow)

- **Molduras oficiais têm janelas vazadas de verdade (canal alfa real) — decisão de 10/08/2026, 3ª revisão da arte:** as duas revisões anteriores usavam arte totalmente opaca (RGB sem alfa, ou com alfa mas sem transparência de verdade), forçando o backend a **medir coordenadas a olho** (grade sobre a imagem + zoom) e guardar como constantes proporcionais fixas — processo frágil, que teve que ser refeito a cada nova versão da arte e ainda saía visivelmente desalinhado quando a arte mudava de tamanho/layout entre revisões. A 3ª revisão da arte em `backend/app/assets/templates/` (`moldura_sexta_boteco.png`, `moldura_sabado_feijoada.png`, `moldura_domingo_churrasco.png`, 1080×1920, RGBA) tem duas janelas **genuinamente vazadas** (canal alfa variando de 0 a 255): uma pra foto (maior, central) e outra pro cartão de data/horário (menor, à esquerda). `moldura_sabado_noite` não é usada nesta fase (arte ainda não entregue). Versões anteriores da arte ficaram preservadas em `backend/app/assets/templates/backup_molduras/` como referência histórica.
- **Coordenadas detectadas em tempo de execução via canal alfa, não mais medidas a olho:** `_detectar_areas_vazadas()` varre a máscara de transparência da moldura carregada e calcula o bounding box exato das duas janelas (a de menor `x` é sempre o cartão, a de maior é a foto — layout fixo da casa). Isso elimina de vez o processo manual de remapeamento a cada nova arte — qualquer moldura futura que já venha com essas 2 janelas vazadas no padrão esperado funciona automaticamente, sem tocar código. Se a arte não tiver exatamente 2 janelas vazadas (layout inesperado), cai num fallback de coordenada proporcional aproximada só pra foto (`AREA_FOTO_PROP_FALLBACK`) — nunca derruba a geração do flyer.
- **Composição, de baixo pra cima:** 1) canvas base preto sólido (`COR_FUNDO_BASE`, `(0,0,0)` — amostrado do fundo real da arte pra não sobrar nenhuma emenda visível contra o preto natural da moldura); 2) foto do cliente colada exatamente na janela vazada da foto (recorte "cover" centralizado, sem distorcer); 3) moldura (RGBA) composta por cima via `alpha_composite` — as áreas opacas cobrem tudo, as 2 janelas revelam o que já foi colado embaixo; 4) data (`DD/MM`) e horário (formatado a partir do Custom Field `2068854` — `buscar_custom_fields_lead` tem devolvido só a hora, sem minuto, ex. `"12"` → exibido como `"12:00"`) desenhados dentro da janela vazada do cartão (metade de cima = data, metade de baixo = horário); o dia da semana ("SEXTA FEIRA" etc., ainda opaco/fixo na arte, fora da janela vazada) só é apagado/redesenhado no caminho de fallback (quando o template usado não bate com o dia real — ver `forcar_dia` em `_desenhar_cartao_dia_data_horario`, área estimada por proximidade à janela do cartão já que não é detectável via alfa); 5) faixa semitransparente na base da caixa da foto, com o nome do aniversariante em destaque (a arte não tem espaço reservado pro nome — decisão do usuário foi sobrepor uma faixa na própria foto).
- **Acabamento "dourado premium" (decisão de 10/08/2026, spec visual detalhada pelo usuário a partir de referência gerada por IA):** `_desenhar_texto_com_efeito()` renderiza cada texto num tile RGBA próprio — sombra suave (preto, leve blur), contorno fino opcional, preenchimento sólido ou em **gradiente vertical** (`_criar_gradiente_vertical`) recortado exatamente na forma das letras (máscara do glifo), e brilho discreto opcional (camada borrada por baixo do texto principal). Aplicado assim:
  - **Data ("10/08"):** cor sólida bege-champanhe fosca (`COR_DATA`, `#D8D0C8`), sem contorno, só sombra.
  - **Horário ("18:00") e nome do aniversariante:** mesmo tratamento nos dois (pedido explícito do usuário — "a cor e fonte do horário seja igual ao nome") — gradiente dourado metálico (`GRADIENTE_DOURADO`: `#B87500` topo → `#F2B900` centro/brilho → `#C98500` base), contorno fino dourado escuro (`COR_CONTORNO_DOURADO`, `#8A5A00`) e brilho discreto (`COR_BRILHO_DOURADO`).
- **Fonte condensada, não mais serifada:** `PlayfairDisplay-Bold.ttf` (elegante/serifada) foi trocada por `RobotoCondensed-Bold.ttf` em todo texto desenhado pelo backend (nome, dia/data/horário) — pedido explícito do usuário pra bater com a tipografia condensada/pesada já usada na arte ("SEXTA FEIRA" etc.), nunca serifada nem cursiva. Baixada do repositório oficial do Google Fonts (`google/fonts`, licença OFL). Ambas as fontes (Playfair e Roboto Condensed) são "variable fonts" — sem mais arquivo estático por peso —, por isso `_carregar_fonte()` chama `set_variation_by_axes([700])` depois de carregar, pra garantir o peso Bold.
- **Seleção automática de moldura pelo dia da semana:** `flyer_generator.selecionar_template_e_dia(data_reserva)` deriva o `template_name` (`sexta_boteco`/`sabado_feijoada`/`domingo_churrasco`) e o texto do dia a partir de `data_reserva.weekday()`. Segunda–quinta não tem moldura própria nesta fase — cai num fallback (`domingo_churrasco`, texto "SEU DIA") com aviso no log; não deveria acontecer no fluxo normal, mas evita que o flyer falhe se um cliente digitar uma data de dia útil.
- **Estimativa de convidados não aparece no flyer:** usada só para os benefícios do aniversariante e para a equipe saber quantas cadeiras preparar — não é impressa na arte.
- **Verificado com geração real (10/08/2026):** flyers de teste gerados de verdade (não simulados) para os 3 templates, com nome longo e acentuado (`"João Pedro Nascimento"`), confirmando visualmente o encaixe da foto, o gradiente/contorno/brilho do texto dourado (zoom nas áreas), a renderização correta dos acentos, e o caminho de fallback (data numa terça-feira, dia da semana da arte corretamente apagado e substituído por "SEU DIA").

## 5. Comandos Principais

### 5.1. Backend (FastAPI)

Importante: Execute os comandos a partir da raiz do repositório para garantir a resolução correta dos pacotes Python (`backend.app`).

- **Regra de governança — `.venv` obrigatório:** todo comando Python deste projeto (servidor `uvicorn`, `python -m backend.app.test_kommo`, `test_api_endpoints`, `test_inspecionar_lead`, etc.) **deve rodar com o ambiente virtual `.venv` da raiz do repositório ativado**. Nunca instale ou rode nada com o Python global do sistema — isso evita divergência de versões entre máquinas/sessões e garante que as dependências pinadas em `backend/requirements.txt` (Pillow, httpx, supabase, FastAPI, etc., cada uma com versão exata) sejam exatamente as usadas em produção. O `.venv/` já está no `.gitignore`.

```bash
# Ativar o ambiente virtual (uma vez por sessão de terminal)
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Git Bash / Unix:
source .venv/bin/activate

# Instalar dependências (Garantir codificação UTF-8 no arquivo requirements.txt)
pip install -r backend/requirements.txt

# Executar o servidor de desenvolvimento FastAPI
uvicorn backend.app.main:app --reload

# Executar script de teste manual de webhook Kommo
python -m backend.app.test_kommo
```

### 5.2. Frontend (Flutter)

```bash
cd frontend

# Obter dependências
flutter pub get

# Rodar aplicação localmente (Web / Dispositivo)
flutter run

# Gerar build de produção para Web (Vercel)
flutter build web

# Executar testes unitários
flutter test
```

## 6. Débitos Técnicos e Arquitetura

### 6.1. Centralização de Configurações (`config.py`)

- **Situação Atual:** Algumas rotas (`convidados.py`, `webhooks.py`) leem variáveis de ambiente via `os.getenv()` diretamente.
- **Instrução:** Refatorar gradualmente para centralizar a leitura de configurações usando a classe `Settings` em `backend/app/config.py`.

### 6.2. Parametrização de URLs (`api_service.dart`)

- **Situação Atual:** O arquivo `frontend/lib/services/api_service.dart` e scripts de teste contêm URLs de desenvolvimento (ngrok) hardcoded.
- **Instrução:** Garantir a parametrização de URLs de API por meio de variáveis de ambiente no build do Flutter (`--dart-define`).

## 7. Esquema do Banco de Dados (Supabase PostgreSQL)

- `aniversariantes`: Dados do lead — `kommo_lead_id`, `nome_completo`, `token_exclusivo` (UUID), `foto_url` (flyer composto), `foto_perfil_url` (foto original do Custom Field `2068458`, sem processamento — ver `sql/migrations/20260807_01_add_foto_perfil_url_aniversariantes.sql`) e `data_reserva`. **Regra oficial (ver 4.2):** o registro só nasce nesta tabela quando o Lead chega na etapa "PROCESSANDO FLYER" (`status_id` `109983139`) com os 5 Custom Fields obrigatórios já preenchidos pelo Salesbot, e só uma vez por `kommo_lead_id` — reentregas do mesmo webhook são ignoradas (checagem de idempotência, ver 4.2); não existe mais coluna de status intermediário (`status_cadastro` foi removida — ver `sql/migrations/20260804_02_remove_status_cadastro_aniversariantes.sql`). Não há mais estado intermediário no Lead do Kommo nem no Supabase — o webhook é um disparo único.
- `convidados`: Registro dos convidados confirmados (`id`, `lead_id`, `nome_completo`, `cpf`, `whatsapp`, `data_nascimento`, `qr_code_token`, `utilizado`).
- `vw_analytics_convidados`: View analítica para resumos e métricas de confirmação.
- **Storage (`fotos-aniversariantes`):** Bucket com dois arquivos por aniversariante, nomes determinísticos por `kommo_lead_id` (`flyer_{lead_id}.jpg` e `foto_perfil_{lead_id}.jpg`, ambos com `x-upsert: true`): o flyer final composto (Pillow) e a foto original do cliente, sem nenhum processamento — usada tanto como insumo do flyer quanto exibida no formulário de cadastro do convidado (Flutter Web).

### 7.1. Fonte da Verdade do Schema (`sql/`)

A pasta `sql/` na raiz do repositório é a **fonte da verdade versionada** do banco de dados. Qualquer alteração de schema (nova coluna, índice, constraint ou view) deve ser primeiro criada aqui e só depois aplicada manualmente no Supabase (não há runner de migration automático neste ciclo do MVP):

- `sql/schema/01_tables_aniversariantes.sql` — DDL completa da tabela `aniversariantes`.
- `sql/schema/02_tables_convidados.sql` — DDL da tabela `convidados`, incluindo os índices (`idx_convidados_lead_id`, `idx_convidados_cpf`) e a constraint `unique_cpf_por_aniversariante (lead_id, cpf)`.
- `sql/schema/03_tables_comandas.sql` — DDL da tabela `comandas_temporarias`, usada na fila de sincronização com o ERP Epoc.
- `sql/migrations/20260724_01_add_qrcode_portaria_convidados.sql` — adiciona `qr_code_token`, `utilizado` e `data_hora_entrada` à tabela `convidados`, além do índice `idx_convidados_qr_code_token`.
- `sql/migrations/20260725_01_add_cpf_aniversariantes.sql` — adiciona a coluna `cpf` à tabela `aniversariantes` (hoje ainda não populada por nenhum fluxo real).
- `sql/migrations/20260804_01_add_data_reserva_aniversariantes.sql` — adiciona a coluna `data_reserva` à tabela `aniversariantes`, sincronizada com o campo "Data da reserva" (ID `2068460`) do Lead no Kommo.
- `sql/migrations/20260804_02_remove_status_cadastro_aniversariantes.sql` — remove a coluna `status_cadastro` da tabela `aniversariantes`.
- `sql/migrations/20260817_01_add_horario_estimativa_aniversariantes.sql` — adiciona `horario_reserva` (TIME) e `estimativa_convidados` (INTEGER) à tabela `aniversariantes`, sincronizadas com os Custom Fields "Horário da reserva" (ID `2068854`) e "Estimativa de Convidados" (ID `2068456`) do Lead no Kommo — antes só usadas para desenhar o flyer e descartadas, agora persistidas para alimentar o painel de aniversariantes do dia.
- `sql/views/01_vw_analytics_convidados.sql` — DDL da view `vw_analytics_convidados`, consumida por `GET /convidados/resumo/{lead_id}`.

**Instrução:** ao alterar qualquer rota do backend que dependa de colunas do Supabase, consulte primeiro os arquivos em `sql/` para confirmar o schema vigente antes de assumir a estrutura das tabelas.