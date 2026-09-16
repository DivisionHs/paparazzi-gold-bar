# Visão Geral de Arquitetura e Fluxos do Paparazzi Gold Bar

## 1. Diagrama de Conexão entre Sistemas

O documento deve começar explicando de forma simples a jornada da informação entre os 5 pilares da nossa tecnologia:

- O **Kommo CRM** captura a foto e os dados da reserva via WhatsApp.
- O **FastAPI (Backend Central)** recebe o webhook, processa a foto com a moldura dourada, salva no banco e gera a URL única com token seguro.
- O **Supabase (PostgreSQL e Storage)** armazena a foto, os dados do aniversariante e os cadastros dos convidados.
- O **Flutter Web (Vercel)** exibe o formulário para os convidados confirmarem presença — este lado continua público, sem login. A geração/exibição do QR Code individual está **pausada desde 15/09/2026** (a Paparazzi trocou de ERP recentemente; a integração fica em avaliação antes de reativar), mas o backend continua gerando o `qr_code_token` normalmente por trás.
- O **App de Portaria (Flutter)**, desde 18/08/2026, vive atrás de um login de funcionário (Supabase Auth) e divide o mesmo "Hub" pós-login com o painel de aniversariantes do dia. A leitura de QR Code está **temporariamente fora do ar** (mesma decisão de 15/09/2026) — o card da Portaria no Hub abre um aviso em vez da tela real. A integração com o Epoc ERP pra abertura automática de comanda **nunca chegou a ser implementada** (bloqueada por falta de acesso à API do ERP antigo, e agora também pela troca de ERP). Enquanto isso, a confirmação de entrada é feita manualmente: um botão "Confirmar entrada" na lista de convidados do painel do dia (ver Passo 5.1), adicionado em 16/09/2026.

## 2. Fluxo Operacional Passo a Passo (Jornada da Fase 1)

O texto deve detalhar as 6 etapas que compõem o ciclo completo de um aniversário:

### Passo 1 - Reserva e Coleta Direta pelo Salesbot (WhatsApp / Kommo)

O aniversariante fecha a reserva pelo chat. O Salesbot conduz, direto com o cliente, a coleta dos 5 dados obrigatórios da reserva, preenchendo os respectivos Custom Fields nativos do Lead no Kommo — **sem nenhuma automação de cálculo pelo backend**:

1. **Data da Reserva** (Custom Field ID `2068460`, tipo `date`).
2. **Horário da Reserva** (Custom Field ID `2068854`).
3. **Estimativa de Convidados** (Custom Field ID `2068456`).
4. **Nome do Flyer** (Custom Field ID `2068452`).
5. **Foto do Aniversariante** (Custom Field de arquivo, ID `2068458`).

> **Decisão de 05/08/2026:** a ideia anterior de calcular a Data da Reserva automaticamente a partir de um Custom Field "Nome da semana" (ID `2068768`, botões de Sexta/Sábado/Domingo) foi **descontinuada/adiada** para esta fase do MVP. O campo continua existindo no Salesbot, mas o backend não lê nem processa mais esse campo — a Data da Reserva agora é respondida diretamente pelo cliente. Essa automação vira ideia de aprimoramento para a Fase 2 (ver `docs/diario_projeto.md`).

**Disparo único do webhook:** o `POST /webhooks/kommo` só é chamado pelo Kommo quando o Lead atinge a etapa exclusiva **"PROCESSANDO FLYER"** (`status_id` `109983139`) — distinta da etapa anterior `109630671`, usada mais cedo no funil só para iniciar a coleta de nome/foto no Salesbot. A mudança para `109983139` só acontece depois que os 5 Custom Fields acima já estão preenchidos. Não há mais coleta incremental via chat nem um "gate" de confirmação adicional no backend: a chegada nessa etapa final já representa a confirmação. O backend recebe o payload consolidado com todos os campos de uma vez, baixa a foto a partir da URL do Custom Field `2068458` e segue direto para o processamento (Passo 2).

### Passo 2 - Processamento e Geração do Flyer (FastAPI)

Ao receber o payload consolidado com os 5 campos preenchidos, o backend baixa a foto, recorta a imagem, aplica o modelo visual dourado da casa, salva no Supabase Storage e **só então nasce o registro do aniversariante na tabela `aniversariantes`** — com nome (a partir do campo "Nome do flyer"), foto, data da reserva e um `token_exclusivo` (UUID v4) gerados nesse mesmo instante. É o único INSERT do fluxo. Se o payload chegar com algum dos 5 campos faltando, o backend loga quais estão ausentes e ignora o disparo (nada é inserido parcialmente).

### Passo 3 - Devolução e Compartilhamento

O backend devolve ao Kommo, via Custom Fields do Lead (lidos pelo Salesbot com merge tags), a URL do flyer pronto (`2069404`) e o link personalizado da lista (`2073759`, formato `https://paparazzi-gold-bar.vercel.app/?token=<UUID>` — corrigido em 15/09/2026, o formato anterior com `/cadastro` nunca funcionou de verdade, ver `docs/diario_projeto.md`).  
O aniversariante divulga o flyer e envia o link no grupo de convidados.

### Passo 4 - Cadastro do Convidado (Flutter Web)

O convidado acessa o link, visualiza o nome e foto do aniversariante e preenche **Nome**, **CPF**, **WhatsApp** e **Data de Nascimento**.  
O sistema valida se o CPF já está na lista e confirma a presença na tela. **Desde 15/09/2026, não gera mais QR Code na tela** (emissão pausada até a integração com o novo ERP da Paparazzi ser avaliada) — o backend continua gravando `qr_code_token` no registro do convidado por trás, só não é mostrado.

### Passo 5 - Checagem na Portaria (App Portaria) — temporariamente fora do ar

**Desde 18/08/2026, o funcionário precisa estar logado** (Supabase Auth, e-mail/senha) para acessar o Hub administrativo. **Desde 15/09/2026, a leitura de QR Code na Portaria está pausada** (card do Hub abre um aviso "Temporariamente fora do ar" em vez da tela real) — a lógica de leitura (câmera, os três estados de resultado, busca manual por CPF) continua implementada no código, só desligada da navegação, pronta pra reativar quando o QR voltar. Comportamento normal, quando reativado: o porteiro lê o QR Code do convidado e a tela responde com Sinal Verde 🟢 (Acesso Liberado) ou Sinal Vermelho 🔴 (QR Code inválido ou já utilizado).

### Passo 5.1 - Painel de Aniversariantes do Dia e Confirmação Manual de Entrada (Hub, staff-only)

Mesmo Hub pós-login: uma tela lista os aniversariantes com reserva num dia — nome, horário da reserva, estimativa de convidados (vindos do Kommo, persistidos no Supabase) e a quantidade real de convidados já confirmados pelo formulário. **Desde 16/09/2026**, um ícone de calendário permite escolher qualquer data, não só o dia atual (com atalho pra voltar rápido pra "hoje"). Ao tocar no nome de um aniversariante, abre a lista com os convidados confirmados — mostrando, lado a lado, quantos confirmaram presença pelo formulário e quantos **já entraram de fato**. Como o QR Code está pausado (Passo 5), a entrada é confirmada manualmente: cada convidado tem um botão "Confirmar entrada" (vira um chip "Entrou", tocável pra desfazer em caso de engano) — grava exatamente a mesma marcação que o QR Code gravaria, então quando o QR voltar, os dois caminhos continuam alimentando a mesma contagem.

### Passo 6 - Integração com Comanda (Epoc ERP) — planejado, não implementado

O plano original era, no momento em que a entrada fosse validada (QR Code ou, hoje, confirmação manual), o sistema enfileirar a chamada para abrir a comanda correspondente no ERP. **Nunca foi implementado** — segue bloqueado por falta de acesso à API oficial do ERP (agora um ERP novo, trocado recentemente pela Paparazzi; o antigo Epoc nunca chegou a ter acesso liberado). A tabela `comandas_temporarias` já existe no schema (fila com `status_epoc` pra re-tentativas), esperando essa integração.

## 3. Modelagem de Dados no Supabase

O documento precisa descrever o que guardamos no banco de dados para garantir o funcionamento do sistema e futuras análises.

### Tabela de Aniversariantes

- Identificador único do lead no Kommo.
- Nome completo do aniversariante (a partir do Custom Field "Nome do flyer").
- Data, horário e estimativa de convidados da reserva, informados diretamente pelo cliente ao Salesbot (Custom Fields nativos do Lead no Kommo) — horário e estimativa persistidos no Supabase desde 18/08/2026, antes eram usados só para desenhar o flyer e descartados.
- Token exclusivo (UUID v4) que identifica o link da lista.
- Link da foto do flyer gerado e da foto original enviada pelo cliente.

### Contas de Funcionário (Supabase Auth)

Desde 18/08/2026, o acesso da equipe (Portaria, painel de aniversariantes do dia) exige login. Não é uma tabela própria do projeto — usa o esquema nativo de autenticação do Supabase (`auth.users`), gerenciado hoje via script administrativo pontual, sem tela de autoatendimento ainda (ver `docs/paparazzi_resumo_projeto.md`, seção de Fase 2, para o plano de evolução).

**Observação sobre o momento de criação:** o registro só é inserido nesta tabela quando o Lead chega na etapa "PROCESSANDO FLYER" (`status_id` `109983139`) com os 5 Custom Fields obrigatórios já preenchidos — é o único INSERT do fluxo, disparado por um único webhook. Não existe mais uma coluna de status intermediário (`status_cadastro`) nem qualquer estado intermediário guardado no Lead do Kommo ou no Supabase, já que não há mais coleta incremental via chat.

### Tabela de Convidados

- Identificador do convidado.
- Vínculo com a reserva do aniversariante.
- Nome completo, CPF, WhatsApp e Data de Nascimento.
- Token individual do QR Code (UUID v4) — continua sendo gerado no cadastro mesmo com a emissão/exibição de QR Code pausada (ver Passo 4).
- Status da entrada (PENDENTE ou ENTROU) — marcado tanto pela leitura de QR Code na Portaria (pausada) quanto pela confirmação manual no painel do dia (ativa desde 16/09/2026, ver Passo 5.1); os dois caminhos gravam a mesma coluna.
- Data e hora exata da entrada, seja qual for o caminho usado.

## 4. Estratégia de Resiliência e Contingência Operacional

Para evitar gargalos caso a internet oscile ou o sistema de caixa passe por instabilidade no final de semana, o documento deve definir duas regras práticas:

### Operação de Comanda Assíncrona (Offline-First)

A validação do convidado na portaria é síncrona e imediata na tela do porteiro.  
A comunicação com o Epoc ERP para criar a comanda roda em segundo plano.  
Se o ERP falhar ou demorar para responder, o sistema tenta novamente de forma automática sem reter a fila de clientes.

### Plano de Contingência Sem Celular

Caso o convidado chegue sem bateria ou sem o QR Code em mãos, o app da portaria permite uma busca manual rápida digitando apenas o CPF ou o Nome do convidado atrelado à lista daquele aniversariante.