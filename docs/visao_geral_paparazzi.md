# Visão Geral de Arquitetura e Fluxos do Paparazzi Gold Bar

## 1. Diagrama de Conexão entre Sistemas

O documento deve começar explicando de forma simples a jornada da informação entre os 5 pilares da nossa tecnologia:

- O **Kommo CRM** captura a foto e os dados da reserva via WhatsApp.
- O **FastAPI (Backend Central)** recebe o webhook, processa a foto com a moldura dourada, salva no banco e gera a URL única com token seguro.
- O **Supabase (PostgreSQL e Storage)** armazena a foto, os dados do aniversariante e os cadastros dos convidados.
- O **Flutter Web (Vercel)** exibe o formulário para os convidados confirmarem presença e gera o QR Code individual.
- O **App de Portaria (Flutter)** bipa o QR Code do convidado e aciona, em segundo plano, a API do Epoc ERP para abertura da comanda.

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

O backend devolve para o Kommo a imagem do flyer pronta e o link personalizado da lista.  
O aniversariante divulga o flyer e envia o link no grupo de convidados.

### Passo 4 - Cadastro do Convidado e Emissão do QR Code (Flutter Web)

O convidado acessa o link, visualiza o nome e foto do aniversariante e preenche **Nome**, **CPF**, **WhatsApp** e **Data de Nascimento**.  
O sistema valida se o CPF já está na lista e gera na tela um QR Code individual com o passaporte do evento.

### Passo 5 - Checagem Expressa na Portaria (App Portaria)

Na chegada ao bar, o convidado apresenta o QR Code.  
O porteiro faz a leitura com a câmera e a tela responde instantaneamente com:

- Sinal Verde 🟢 (Acesso Liberado), ou
- Sinal Vermelho 🔴 (QR Code inválido ou já utilizado).

### Passo 6 - Integração com Comanda (Epoc ERP)

No momento em que o porteiro valida a entrada, o sistema marca o cliente como presente e enfileira a chamada para abrir a comanda correspondente no Epoc ERP.

## 3. Modelagem de Dados no Supabase

O documento precisa descrever o que guardamos no banco de dados para garantir o funcionamento do sistema e futuras análises.

### Tabela de Aniversariantes

- Identificador único do lead no Kommo.
- Nome completo do aniversariante (a partir do Custom Field "Nome do flyer").
- Data da reserva, informada diretamente pelo cliente ao Salesbot (Custom Field "Data da reserva" do Lead no Kommo).
- Token exclusivo (UUID v4) que identifica o link da lista.
- Link da foto do flyer gerado.

**Observação sobre o momento de criação:** o registro só é inserido nesta tabela quando o Lead chega na etapa "PROCESSANDO FLYER" (`status_id` `109983139`) com os 5 Custom Fields obrigatórios já preenchidos — é o único INSERT do fluxo, disparado por um único webhook. Não existe mais uma coluna de status intermediário (`status_cadastro`) nem qualquer estado intermediário guardado no Lead do Kommo ou no Supabase, já que não há mais coleta incremental via chat.

### Tabela de Convidados

- Identificador do convidado.
- Vínculo com a reserva do aniversariante.
- Nome completo, CPF, WhatsApp e Data de Nascimento.
- Token individual do QR Code (UUID v4).
- Status da entrada (PENDENTE ou ENTROU).
- Data e hora exata do check-in na portaria.

## 4. Estratégia de Resiliência e Contingência Operacional

Para evitar gargalos caso a internet oscile ou o sistema de caixa passe por instabilidade no final de semana, o documento deve definir duas regras práticas:

### Operação de Comanda Assíncrona (Offline-First)

A validação do convidado na portaria é síncrona e imediata na tela do porteiro.  
A comunicação com o Epoc ERP para criar a comanda roda em segundo plano.  
Se o ERP falhar ou demorar para responder, o sistema tenta novamente de forma automática sem reter a fila de clientes.

### Plano de Contingência Sem Celular

Caso o convidado chegue sem bateria ou sem o QR Code em mãos, o app da portaria permite uma busca manual rápida digitando apenas o CPF ou o Nome do convidado atrelado à lista daquele aniversariante.