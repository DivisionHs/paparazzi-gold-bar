# Diário do Projeto — Paparazzi Gold Bar

## 1. Objetivo do Documento

Este arquivo registra o histórico contínuo de desenvolvimento, refatorações, arquivos modificados em cada sprint e o status de cada funcionalidade planejada para o MVP do Paparazzi Gold Bar.

## 2. Registro de Atividades e Sprints

### Registro [21/07/2026] — Estruturação do MVP e Formulário Web

#### O que foi feito

- Publicação inicial da interface em Flutter Web (`register_screen.dart`) na Vercel para o formulário de cadastro do convidado.
- Criação do endpoint no FastAPI para recebimento dos webhooks do Kommo CRM (`/webhooks/kommo`).
- Implementação da regra de validação de CPF (formato e duplicidade) no backend para evitar que o mesmo convidado se cadastre mais de uma vez na mesma lista.
- Padronização dos identificadores usando tokens UUID v4 para garantir URLs seguras e sem expor IDs numéricos sequenciais.

#### Arquivos afetados

- `frontend/lib/views/register_screen.dart`
- `frontend/lib/services/api_service.dart`
- `backend/app/routes/webhooks.py`
- `backend/app/routes/convidados.py`

### Registro [24/07/2026] — Definição de Molduras Máster, Estratégia de Mídia e Alinhamento Visual

#### O que foi feito

- **Definição dos Templates Visuais da Casa (Fase 1):** Finalização e alinhamento dos layouts visuais oficiais para todos os dias de eventos da semana (Sexta Boteco/Churrasco, Sábado Feijoada, Sábado Noite e Domingo).
- **Estratégia de Processamento de Imagem (Pillow/FastAPI):** Decisão de arquitetura visual adotando a abordagem de *Molduras Máster em PNG Transparente* (Alpha Channel). O backend em Python realiza a sobreposição em 3 camadas: foto do cliente no fundo, moldura máster no meio e nome dinâmico no topo, garantindo alta velocidade de geração e fidelidade às artes originais.
- **Padronização dos Benefícios da Casa:** Manutenção das informações comerciais essenciais na moldura (horários de buffet de feijoada/boteco, endereço e o slogan oficial "ISSO AQUI É PAPARAZZI!"), garantindo que o flyer sirva de gatilho de atração no WhatsApp/Instagram sem depender apenas da IA generativa.
- **Estruturação de Prompts e Preparação de Assets:** Criação e execução dos prompts de geração de imagem para fechamento dos gabaritos das molduras vazadas e organização para upload no Supabase Storage / diretório local `backend/app/assets/templates/`.

#### Arquivos afetados / Planejados

- `backend/app/assets/templates/moldura_sexta_boteco.png`
- `backend/app/assets/templates/moldura_sabado_feijoada.png`
- `backend/app/assets/templates/moldura_sabado_noite.png`
- `backend/app/assets/templates/moldura_domingo.png`
- `backend/app/services/flyer_generator.py`

### Registro [04/08/2026] — Fluxo de Seleção de Data e Remoção do status_cadastro

#### O que foi feito

- **Rota de cálculo dinâmico de datas para o Salesbot:** criado `POST/GET /webhooks/kommo/datas` para calcular sexta/sábado/domingo do fim de semana vigente (usado inicialmente para montar os textos dos botões nativos do WhatsApp).
- **Sincronização da data escolhida com o Kommo/Supabase:** o clique do cliente em um dos botões nativos de fim de semana do Salesbot preenche automaticamente o Custom Field de texto "Nome da semana" (ID `2068768`) no Lead. O webhook `/webhooks/kommo` passou a ler esse campo, calcular a data exata do dia escolhido e gravar no Custom Field oficial "Data da reserva" (ID `2068460`, tipo `date`) do Lead — sincronizando também a coluna `data_reserva` da tabela `aniversariantes`. Duas iterações anteriores dessa lógica (baseadas em 3 campos de texto separados `Data_opcao_1/2/3`, e depois em 3 etapas distintas do pipeline) foram descartadas em favor dessa abordagem mais enxuta de um único campo.
- **Remoção da coluna `status_cadastro`:** a tabela `aniversariantes` deixou de ter uma coluna de status intermediário. O registro do aniversariante agora só nasce no Supabase ao final do fluxo de chat (depois que nome e foto já foram coletados e o flyer processado), eliminando "dados fantasmas" de quem inicia a conversa mas nunca envia a foto. O estado intermediário (aguardando nome / aguardando foto) passou a ser controlado direto no campo `name` do Lead no Kommo, via `kommo_service.atualizar_nome_lead`/`buscar_lead`, no lugar da antiga coluna.
- **Novo serviço `kommo_service.py`:** centraliza todas as chamadas à API REST v4 do Kommo (PATCH de custom fields, PATCH/GET do nome do Lead) usando o `KOMMO_LONG_LIVED_TOKEN`.

#### Arquivos afetados

- `backend/app/routes/webhooks.py`
- `backend/app/services/kommo_service.py`
- `backend/app/config.py` (novo campo `KOMMO_LONG_LIVED_TOKEN` em `Settings`)
- `backend/app/test_api_endpoints.py` e `backend/app/test_kommo.py` (ajustados para o schema/fluxo novos)
- `sql/migrations/20260804_01_add_data_reserva_aniversariantes.sql`
- `sql/migrations/20260804_02_remove_status_cadastro_aniversariantes.sql`
- `docs/visao_geral_paparazzi.md`, `CLAUDE.md` (schema e fluxo atualizados)

### Registro [05/08/2026] — Alinhamento da Sequência de Coleta e da Regra de Confirmação

#### O que foi feito

- **Consolidação da ordem oficial de coleta no Salesbot:** definida e documentada em `CLAUDE.md` (4.2) e `docs/visao_geral_paparazzi.md` (Passo 1) a sequência definitiva: Nome da semana (`2068768`) → Data da reserva calculada (`2068460`) → Horário da reserva (`2068854`) → Estimativa de convidados (`2068456`) → Nome do flyer (`2068452`) → Foto do aniversariante.
- **Regra de confirmação antes do INSERT:** definido que, após a coleta de todos os dados acima e da foto, o Salesbot envia uma mensagem de resumo e só após o aceite positivo do cliente o backend gera o flyer, faz o upload e realiza o INSERT em `aniversariantes`. Enquanto a conversa está em andamento, o estado continua leve no Lead do Kommo (campo `name` + Custom Fields nativos), sem tocar o Supabase.
- **Gap identificado entre regra de negócio e código:** ao revisar `backend/app/routes/webhooks.py` e `backend/app/services/kommo_service.py`, confirmado que a implementação atual **ainda não** cobre Horário/Estimativa/Nome do flyer nem o gate de confirmação — o INSERT em `aniversariantes` dispara imediatamente ao receber a foto (rota `/webhooks/chat`, CASO B). A documentação foi atualizada para refletir a regra oficial já validada, com uma nota explícita de status de implementação em cada trecho afetado, para não confundir sessões futuras.

#### Arquivos afetados

- `CLAUDE.md` (nova seção 4.2 "Sequência de Coleta de Dados e Confirmação no Chat", renumeração de 4.2-4.4 para 4.3-4.5, nota em 7.)
- `docs/visao_geral_paparazzi.md` (Passo 1 e Passo 2 reescritos, observação da Tabela de Aniversariantes atualizada)

### Registro [05/08/2026] — Implementação da Sequência Completa e do Gate de Confirmação

#### O que foi feito

- **Correção do fallback de `lead_id` em `/webhooks/kommo`:** a extração de `lead_id` só reconhecia o formato verbose `leads[...][id]`, sem fallback simples (diferente do campo "Nome da semana", que já aceitava um parâmetro `dia` solto). Isso fazia requisições de teste manual serem descartadas cedo demais com "Sem ID de lead válido". Agora aceita também `lead_id`/`id` como parâmetro simples.
- **Generalização da extração de Custom Fields:** `extrair_nome_da_semana_do_payload` foi refatorada para reaproveitar uma nova função `extrair_custom_fields_do_payload`, que devolve todos os Custom Fields presentes no payload (não só o 2068768). Usada para reconhecer a chegada de Horário (`2068854`), Estimativa de convidados (`2068456`) e Nome do flyer (`2068452`) em `/webhooks/kommo`.
- **`kommo_service.buscar_lead` estendido** para também devolver `custom_fields` (dict `field_id -> valor`), lendo `custom_fields_values` do corpo padrão da resposta do Lead (não precisa de `with` extra, diferente de tags).
- **Foto pendente no Storage:** novas funções em `supabase_service.py` (`upload_foto_pendente`, `existe_foto_pendente`, `baixar_foto_pendente`, `remover_foto_pendente`) guardam a foto crua em `fotos-aniversariantes/pendentes/{lead_id}.jpg` enquanto o gate de confirmação está aberto — a foto não é mais processada/inserida na hora.
- **Gate de confirmação:** nova função `verificar_coleta_completa()` em `webhooks.py`, chamada tanto quando um Custom Field da sequência chega (`/webhooks/kommo`) quanto quando a foto chega (`/webhooks/chat`). Reconsulta o Lead, loga um diagnóstico campo a campo e, se tudo estiver presente, marca o Lead com `[[AGUARDANDO_CONFIRMACAO]]` (prefixo do nome real) e loga a simulação do envio da mensagem de resumo ao cliente (`🎉 TODOS OS DADOS COLETADOS`).
- **Confirmação positiva dispara o cadastro:** `/webhooks/chat` (CASO A) agora reconhece o estado `[[AGUARDANDO_CONFIRMACAO]]` e, com uma resposta afirmativa (`validar_confirmacao_positiva`), chama `finalizar_cadastro_aniversariante()` — que baixa a foto pendente, gera o flyer, faz upload e só então insere em `aniversariantes` (mesma lógica que antes rodava direto ao receber a foto, agora extraída para uma função reutilizável).
- **`test_kommo.py` reescrito** para exercitar o fluxo completo: lead ganho → nome → ruído (ignorado) → nome da semana → horário → estimativa → nome do flyer → foto (dispara confirmação simulada) → resposta não reconhecida (ignorada) → confirmação positiva (gera flyer e insere no Supabase).
- **Verificação:** `python -m py_compile` nos três arquivos alterados, import real do módulo `webhooks.py` (com `.env` carregado) confirmando que os novos símbolos existem, e testes unitários isolados (sem tocar rede) de `extrair_custom_fields_do_payload` e `validar_confirmacao_positiva`.

#### Arquivos afetados

- `backend/app/routes/webhooks.py`
- `backend/app/services/kommo_service.py`
- `backend/app/services/supabase_service.py`
- `backend/app/test_kommo.py`
- `CLAUDE.md`, `docs/visao_geral_paparazzi.md` (notas de status de implementação atualizadas)

### Registro [05/08/2026] — Simplificação do Fluxo: Webhook Único na Etapa "Aniversário Confirmado"

#### O que foi feito

- **Decisão de produto:** descontinuado/adiado o cálculo automático de data via Custom Field "Nome da semana" (ID `2068768`). O campo continua existindo no Salesbot, mas o backend não lê mais esse campo nem calcula datas — a "Data da Reserva" agora é coletada diretamente do cliente pelo próprio Salesbot. **Ideia para Fase 2:** retomar a automação de tradução "Nome da semana" → "Data da reserva" quando fizer sentido para o produto (ex.: reduzir o número de perguntas ao cliente).
- **Novo fluxo (substitui a implementação da sessão anterior no mesmo dia):** o gate de confirmação implementado horas antes (marcadores `[[AGUARDANDO_NOME_ANIVERSARIANTE]]`/`[[AGUARDANDO_CONFIRMACAO]]`, coleta incremental via chat, foto pendente no Storage) foi **removido por completo**. O novo modelo é mais simples: o Salesbot coleta os 5 dados obrigatórios diretamente com o cliente (Data da Reserva `2068460`, Horário `2068854`, Estimativa de convidados `2068456`, Nome do flyer `2068452`, Foto `2068458` — este último como Custom Field de arquivo) e só move o Lead para a etapa **"aniversário confirmado"** (`status_id` `109630671`) depois de tudo preenchido. O webhook `/webhooks/kommo` passa a ser o único disparo do fluxo inteiro.
- **`backend/app/routes/webhooks.py` reescrito do zero:** removidas todas as funções do fluxo anterior (`extrair_nome_da_semana_do_payload`, `calcular_datas_fim_de_semana`, `sincronizar_data_reserva`, `normalizar_dia_selecionado`, rota `/kommo/data-reserva`, `validar_nome_proprio`, `validar_confirmacao_positiva`, `verificar_coleta_completa`, e a rota `/chat` inteira). Nova lógica: `extrair_custom_fields_do_payload` (mantida, generalizada) lê os 5 Custom Fields do payload consolidado; `converter_valor_data_kommo` normaliza o valor recebido de "Data da reserva" (timestamp Unix ou texto) para o formato da coluna `data_reserva`; `finalizar_cadastro_aniversariante` baixa a foto direto da URL do Custom Field `2068458`, gera o flyer e faz o único INSERT.
- **`.env` atualizado:** `KOMMO_TARGET_STATUS_ID` alterado de `142` para `109630671`.
- **Limpeza de código morto:** removidas as funções de "foto pendente" (`upload_foto_pendente`, `existe_foto_pendente`, `baixar_foto_pendente`, `remover_foto_pendente`) de `supabase_service.py`, já que a foto não passa mais por uma etapa intermediária no Storage. `backend/app/services/kommo_service.py` ficou sem nenhum consumidor (o backend não faz mais nenhuma chamada de volta à API do Kommo — nem PATCH nem GET) — **a exclusão do arquivo está pendente**, bloqueada pelo classificador de ações destrutivas do Claude Code; aguardando confirmação manual do usuário para remover.
- **`test_kommo.py` reescrito** para o novo fluxo de disparo único: webhook com campos faltando (ignorado, loga o que falta) → webhook com os 5 campos completos (gera flyer e insere no Supabase) → webhook fora da etapa alvo (ignorado).
- **Verificação:** `python -m py_compile` nos arquivos alterados, import real do módulo com `.env` carregado confirmando que só a rota `/webhooks/kommo` restou no router, e testes unitários isolados (sem rede) de `extrair_custom_fields_do_payload` e `converter_valor_data_kommo` (timestamp Unix, `DD/MM/AAAA` e valor inválido).

#### Arquivos afetados

- `backend/app/routes/webhooks.py` (reescrito)
- `backend/app/services/supabase_service.py` (funções de foto pendente removidas)
- `backend/app/services/kommo_service.py` (sem consumidores — exclusão pendente de confirmação do usuário)
- `backend/app/test_kommo.py` (reescrito)
- `.env` (`KOMMO_TARGET_STATUS_ID` atualizado)
- `CLAUDE.md` (4.1 e 4.2 reescritas, seção 7 atualizada)
- `docs/visao_geral_paparazzi.md` (Passo 1 e Passo 2 reescritos, Tabela de Aniversariantes atualizada)

### Registro [05/08/2026] — Nova Etapa Exclusiva "PROCESSANDO FLYER" (ID `109983139`)

#### O que foi feito

- **Ajuste fino do gatilho do webhook:** a etapa `109630671` (usada como gatilho no registro anterior do mesmo dia) já é utilizada mais cedo no funil do Kommo, logo após o cliente confirmar o dia da reserva — é nesse ponto que o Salesbot começa a pedir nome e foto, **antes** dos 5 campos estarem completos (confirmado inspecionando o `config_bot.txt` exportado do funil: o step 40 dispara `change_status` para `109630671` imediatamente após o clique em "CONFIRMAR RESERVA", indo em seguida para o step 26, que só então pede a foto/nome). Ou seja, `109630671` nunca foi um gatilho seguro para "todos os 5 campos já preenchidos".
- **Criada uma etapa nova e exclusiva no pipeline do Kommo:** `109983139` — **"PROCESSANDO FLYER"**. O Salesbot foi ajustado para só mover o Lead para essa etapa depois que os 5 campos obrigatórios (Data da Reserva, Horário, Estimativa de Convidados, Nome do Flyer e Foto) já estiverem preenchidos. O webhook `/webhooks/kommo` agora escuta exclusivamente essa etapa.
- **`KOMMO_TARGET_STATUS_ID` atualizado** de `109630671` para `109983139` no `.env` e no fallback padrão em `backend/app/routes/webhooks.py`.
- **Nenhuma mudança na lógica de processamento:** a rota já processava o payload de forma atômica (lê os 5 Custom Fields, valida se todos estão preenchidos, gera o flyer, faz upload e insere) desde o registro anterior — só o valor do `status_id` alvo mudou.
- **Verificação:** `python -m py_compile` em `webhooks.py` e `test_kommo.py` após o ajuste.

#### Arquivos afetados

- `.env` (`KOMMO_TARGET_STATUS_ID`: `109630671` → `109983139`)
- `backend/app/routes/webhooks.py` (fallback padrão e comentários atualizados)
- `backend/app/test_kommo.py` (`STATUS_PROCESSANDO_FLYER` atualizado)
- `CLAUDE.md` (4.2 e seção 7 renomeadas/atualizadas para "PROCESSANDO FLYER")
- `docs/visao_geral_paparazzi.md` (Passo 1 e Tabela de Aniversariantes atualizados)

### Registro [06/08/2026] — Script de Inspeção de Lead e Estratégia de Consulta Ativa (Opção A)

#### O que foi feito

- **Novo script isolado `test_inspecionar_lead.py`:** faz um `GET` direto em `/api/v4/leads/{id}` (sem depender do Uvicorn nem de nenhuma rota do backend) e imprime, campo a campo, o ID, o nome (`field_name` da própria API) e o valor bruto de cada Custom Field do lead consultado — usado para diagnosticar se um valor que o Salesbot acabou de gravar já está visível para quem consulta o lead de fora.
- **Diagnóstico confirmado:** essa inspeção evidenciou que o payload que o próprio webhook do Salesbot manda podia chegar com Custom Fields vazios (`'—'` nos logs) mesmo depois do Salesbot já ter "preenchido" o campo — indício de atraso de propagação entre a gravação do Salesbot e o corpo do webhook disparado por ele.
- **Mudança de arquitetura — Estratégia de Consulta Ativa ("Opção A"):** o webhook (`POST /webhooks/kommo`) passou a ser tratado como um **sinalizador leve**, usado só para saber que um `lead_id` chegou na etapa `109983139`. Os valores dos 5 Custom Fields obrigatórios não são mais lidos do corpo do webhook — assim que o sinal chega, o backend dispara imediatamente um `GET` direto na API do Kommo para buscar os valores mais atuais possíveis, e só então valida/processa.
- **`backend/app/services/kommo_service.py` reescrito:** removida a lógica antiga de PATCH (`atualizar_nome_lead`, `atualizar_data_reserva_lead`, tags), que já estava órfã desde o registro de 05/08. Ficou só `buscar_custom_fields_lead(lead_id)`, a função de consulta ativa. O arquivo, que estava pendente de exclusão por falta de uso, ganhou um propósito novo e voltou a ser consumido por `webhooks.py`.
- **`backend/app/routes/webhooks.py` ajustado:** removida a extração de Custom Fields via regex do payload do webhook (`extrair_custom_fields_do_payload` e os padrões `_PADRAO_CUSTOM_FIELD_*`, que dependiam de confiar no corpo do webhook). A rota agora só extrai `lead_id`/`status_id` do payload e, ao confirmar a etapa alvo, chama `kommo_service.buscar_custom_fields_lead()`. Se a consulta falhar (timeout, erro HTTP, credencial ausente), a rota aborta com segurança (`status: erro`) em vez de seguir com dados potencialmente incompletos.
- **`test_kommo.py` simplificado:** o payload de teste deixou de simular Custom Fields (já que são ignorados), virando só um sinalizador (`leads[id]` + `leads[status_id]`). Como consequência, `LEAD_TESTE_ID` **precisa ser um lead real** existente na conta do Kommo — o resultado do teste passou a refletir o estado real do lead consultado ao vivo.
- **Verificação:** `python -m py_compile` em todos os arquivos alterados, import real do app FastAPI completo, e confirmação de que `extrair_custom_fields_do_payload`/os padrões regex antigos não existem mais no módulo.

#### Arquivos afetados

- `backend/app/test_inspecionar_lead.py` (novo)
- `backend/app/services/kommo_service.py` (reescrito — só `buscar_custom_fields_lead`)
- `backend/app/routes/webhooks.py` (consulta ativa substitui a extração via payload)
- `backend/app/test_kommo.py` (payload simplificado para sinalizador puro)
- `CLAUDE.md` (4.2 atualizada com a Estratégia de Consulta Ativa)

### Registro [06/08/2026] — Correção: Erro 500 ao Baixar a Foto (`Request URL is missing an 'http://' or 'https://' protocol`)

#### O que foi feito

- **Bug encontrado nos testes da Consulta Ativa:** com a busca dos 5 Custom Fields já funcionando via `test_kommo.py`, a etapa seguinte (baixar a foto a partir do valor do Custom Field `2068458`) estourava `500 Internal Server Error` — `httpx` recusava a requisição porque o valor recebido não é garantidamente uma URL `http(s)` completa. **Ponto de atenção operacional:** isso sugere que o Custom Field de arquivo "Foto do Aniversariante" no Kommo pode não devolver sempre um link público direto — vale conferir com `test_inspecionar_lead.py` o valor exato que esse campo está trazendo para leads reais.
- **Correção:** nova função `eh_url_http_valida()` em `webhooks.py`, que checa se o valor começa com `http://`/`https://` antes de qualquer requisição. Se não bater, a rota loga o valor bruto recebido do Kommo e retorna `{"status": "erro", ...}` sem quebrar. Como rede de segurança adicional, a chamada `httpx.AsyncClient().get()` também passou a capturar `httpx.InvalidURL` explicitamente.
- **Verificação:** `python -m py_compile`, import do app FastAPI completo, e teste unitário de `eh_url_http_valida()` cobrindo URL válida, vazia, `None`, relativa, com espaços e com protocolo não-HTTP (ex.: `ftp://`).

#### Arquivos afetados

- `backend/app/routes/webhooks.py` (`eh_url_http_valida` + blindagem do download da foto)

### Registro [06/08/2026] — Resolução de `file_uuid` para URL de Download (Custom Field de Arquivo)

#### O que foi feito

- **Causa raiz confirmada:** o "valor bruto" que disparava o erro do registro anterior não era uma URL malformada — era o **dict de metadados completo** que a API do Kommo devolve para Custom Fields de arquivo: `{'file_uuid': '...', 'version_uuid': '...', 'file_name': 'file_2.jpg', ...}`. O código antigo em `kommo_service.buscar_custom_fields_lead` convertia esse dict para `str()` cegamente (igual fazia com campos de texto/data), produzindo uma string tipo `"{'file_uuid': ...}"` que nunca seria uma URL válida.
- **`kommo_service.buscar_custom_fields_lead` ajustada:** agora preserva o valor como `dict` quando ele vier como dict (em vez de forçar `str()`), só convertendo para string os campos que já são escalares (texto/data/número). Tipo de retorno atualizado para `dict[str, str | dict]`.
- **Nova função `kommo_service.buscar_url_download_arquivo(file_uuid)`:** consulta `GET /api/v4/files/{uuid}` na API do Kommo e tenta, em ordem, os caminhos mais prováveis onde a documentação do Kommo costuma expor o link de download (`download_link`, `download_url`, `_embedded.download_link`, `_links.download.href`). **Ressalva registrada no próprio docstring da função:** o formato exato dessa resposta ainda não foi validado contra uma conta real neste ambiente — se nenhuma dessas chaves bater, o log mostra as chaves de topo da resposta bruta para ajuste rápido na primeira execução real.
- **`webhooks.py` ajustado:** ao processar o Custom Field da foto, detecta se o valor é um `dict` (Custom Field de arquivo); se for, extrai `file_uuid` e chama `buscar_url_download_arquivo()` antes de validar o resultado com `eh_url_http_valida()` (mantendo a blindagem do registro anterior como última linha de defesa, agora aplicada também à URL resolvida). Se `file_uuid` estiver ausente ou a resolução falhar, aborta com log descritivo e sem 500.
- **Log de diagnóstico melhorado:** nova função `formatar_valor_para_log()` evita imprimir o dict inteiro do arquivo na linha "CHECAGEM DE CAMPOS" — mostra só `[arquivo: file_2.jpg | file_uuid=...]`.
- **Verificação:** `python -m py_compile`, import do app FastAPI completo, e teste unitário de `formatar_valor_para_log()` cobrindo string, vazio, `None` e dict de arquivo. **Não foi possível validar a resolução do `file_uuid` contra a API real do Kommo neste ambiente** (sem acesso de rede à conta) — a próxima execução real de `test_kommo.py` é quem vai confirmar se os nomes de chave tentados em `buscar_url_download_arquivo` batem com o formato real da resposta.

#### Arquivos afetados

- `backend/app/services/kommo_service.py` (`buscar_custom_fields_lead` ajustada + nova `buscar_url_download_arquivo`)
- `backend/app/routes/webhooks.py` (resolução de `file_uuid` antes da validação de URL, `formatar_valor_para_log`)

### Registro [06/08/2026] — Correção: Endpoint de Arquivos Retorna 404 (Uso Direto do CDN do Kommo)

#### O que foi feito

- **Causa raiz:** o registro anterior tentava resolver o `file_uuid` via `GET /api/v4/files/{uuid}`, mas esse endpoint devolve **404** nesta conta do Kommo — não é um caminho válido para esta integração. A URL de download real e funcional (padrão CDN, `https://drive-g.kommo.com/download/...`) já vem embutida nos próprios metadados do Custom Field, sem precisar de nenhuma chamada extra à API.
- **`kommo_service.py` ajustado:** removida `buscar_url_download_arquivo` (a função que batia no endpoint 404) e `_montar_url_arquivo`. Nova função **síncrona** (sem chamada de rede) `extrair_url_cdn_arquivo(valor)`, que recebe o valor já obtido do Custom Field (dict de metadados ou string) e extrai/limpa a URL: tenta primeiro chaves prováveis do dict (`url`, `download_url`, `download_link`, `link`, `cdn_url`, `path`) e, como fallback, varre todos os valores string do dict procurando algo que já bata com o padrão `drive-*.kommo.com` (regex `_PADRAO_URL_CDN_KOMMO`, cobrindo diferentes subdomínios de CDN, não só `drive-g`). Também limpa aspas/tags acidentais (`'`, `"`, `<`, `>`) que possam vir grudadas no valor.
- **`webhooks.py` simplificado:** o bloco de resolução da foto não é mais `async` nem depende de uma chamada de rede adicional — chama `kommo_service.extrair_url_cdn_arquivo(valor_foto)` diretamente (funciona tanto para o dict de metadados quanto para uma string simples) e segue para a validação de protocolo já existente (`eh_url_http_valida`).
- **Verificação:** `python -m py_compile`, import do app FastAPI completo, confirmação de que `buscar_url_download_arquivo`/`_montar_url_arquivo` não existem mais em lugar nenhum do backend, e bateria de testes unitários (sem rede) de `extrair_url_cdn_arquivo` cobrindo: dict com URL em chave conhecida, dict com URL entre aspas numa chave conhecida, dict com URL numa chave desconhecida (via fallback regex), dict sem nenhuma URL, string direta, string com tags `<>`, string com aspas, string inválida e `None` — todos batendo com o esperado, incluindo o exemplo exato reportado (`drive-g.kommo.com`).

#### Arquivos afetados

- `backend/app/services/kommo_service.py` (removida `buscar_url_download_arquivo`/`_montar_url_arquivo`; nova `extrair_url_cdn_arquivo` + `_limpar_url`)
- `backend/app/routes/webhooks.py` (bloco de resolução da foto simplificado, sem `await`)

### Registro [06/08/2026] — Padrão Exato do CDN Descoberto: Montagem por Concatenação (Substitui a Busca Heurística)

#### O que foi feito

- **Descoberta operacional final:** o dict de metadados do Custom Field de arquivo **não traz nenhuma URL pronta em nenhuma chave** — a busca heurística por chaves (`url`, `download_link`, etc.) do registro anterior nunca teria funcionado. O link de download do CDN precisa ser **montado por concatenação**: `{base fixa do drive da conta}/{file_uuid}/{version_uuid}/{file_name}`. Confirmado com o exemplo real: `https://drive-g.kommo.com/download/662da799-7bfe-52a0-af12-661479954047/c2a52ead-46b1-405f-82e1-ef90a71f2d08/6ea1d1a9-4447-45ff-b0ee-ec9366991af7/file_4.jpg`.
- **`kommo_service.py` reescrito (parte do arquivo):** removidas `extrair_url_cdn_arquivo`, `_limpar_url`, `_PADRAO_URL_CDN_KOMMO` e `_CHAVES_URL_CANDIDATAS` (toda a lógica de busca heurística/regex, que não se aplicava). Nova função `montar_url_cdn_arquivo(metadados)`, que concatena `_BASE_CDN_ARQUIVOS_KOMMO` (constante — `https://drive-g.kommo.com/download/662da799-7bfe-52a0-af12-661479954047`, o identificador do drive/storage desta conta) com `file_uuid`, `version_uuid` e `file_name` (URL-encoded via `urllib.parse.quote`, para não quebrar em nomes de arquivo com espaço/acento). Se faltar qualquer uma das 3 chaves obrigatórias no dict, loga exatamente quais faltaram e retorna `None`.
- **⚠️ Suposição a validar:** a base fixa do CDN (`662da799-...`) foi tratada como constante para esta conta — se ela variar por lead/arquivo em testes futuros, essa constante precisa virar parte do dict de metadados em vez de hardcoded.
- **`webhooks.py` atualizado:** troca simples de `extrair_url_cdn_arquivo` por `montar_url_cdn_arquivo`, mantendo a mesma validação de protocolo (`eh_url_http_valida`) como última linha de defesa antes do download.
- **Verificação:** `python -m py_compile`, import do app FastAPI completo, confirmação de que os símbolos antigos não existem mais em lugar nenhum, e teste unitário reproduzindo **exatamente** o exemplo reportado (URL montada bateu caractere a caractere), mais casos de erro (chave obrigatória faltando, valor não-dict, `None`) e um caso de nome de arquivo com espaço/acento para confirmar o URL-encoding.

#### Arquivos afetados

- `backend/app/services/kommo_service.py` (substituída a busca heurística por `montar_url_cdn_arquivo`, concatenação exata)
- `backend/app/routes/webhooks.py` (chamada atualizada para `montar_url_cdn_arquivo`)
- `CLAUDE.md` (4.2 atualizada com o padrão exato de montagem da URL)

### Registro [06/08/2026] — Correção do Download (Redirect 301) e Fluxo Validado Ponta a Ponta

#### O que foi feito

- **Último bug do fluxo, corrigido:** com a URL do CDN já sendo montada corretamente (registro anterior), os logs mostraram `301 Moved Permanently` ao baixar a imagem — a CDN de arquivos do Kommo (`drive-g.kommo.com`) redireciona antes de entregar o binário, e o `httpx.AsyncClient` usado em `webhooks.py` não seguia redirecionamentos por padrão. Corrigido com `httpx.AsyncClient(follow_redirects=True)` no download da foto.
- **✅ Fluxo completo validado end-to-end:** webhook sinalizador (`lead_id`/`status_id`) → consulta ativa dos 5 Custom Fields via GET direto na API do Kommo → montagem da URL do CDN a partir de `file_uuid`/`version_uuid`/`file_name` → download da foto (com redirect seguido corretamente) → geração do flyer via Pillow → upload no Supabase Storage (`fotos-aniversariantes`) → `INSERT` único na tabela `aniversariantes`. Este é o fechamento da sequência de correções iniciada com a Estratégia de Consulta Ativa mais cedo neste mesmo dia.
- **Governança de ambiente formalizada:** `CLAUDE.md` (5.1) agora exige explicitamente que todo comando Python do projeto (`uvicorn`, `python -m backend.app.test_kommo`, `test_api_endpoints`, `test_inspecionar_lead`) rode com o `.venv` da raiz ativado — nunca com o Python global do sistema. As dependências críticas (Pillow, httpx, supabase, FastAPI) já estavam pinadas com versão exata em `backend/requirements.txt`; a regra de governança formaliza que essa é a única fonte de verdade para instalação.
- **Verificação:** `python -m py_compile` em `webhooks.py`.

#### Arquivos afetados

- `backend/app/routes/webhooks.py` (`follow_redirects=True` no download da foto)
- `CLAUDE.md` (5.1 — regra de `.venv` obrigatório; 4.2 — nota de `follow_redirects` e status validado end-to-end)

### Registro [07/08/2026] — Idempotência do Webhook e Foto Original Salva Separadamente

#### O que foi feito

- **Bug reportado em teste manual real:** disparando o webhook uma única vez na plataforma do Kommo (entrada do lead na etapa `109983139`), o terminal do Uvicorn mostrou o mesmo `lead_id` sendo processado 3 vezes seguidas (`leads[add][0][id]` idêntico, mesmo `status_id`) — cada reentrega refazia a consulta ativa, o download da foto, o Pillow e o upload no Storage, empilhando um flyer novo a cada vez (nome do arquivo tinha um `uuid.uuid4()` aleatório, então o `x-upsert: true` nunca chegava a sobrescrever nada) e sobrescrevendo `token_exclusivo` com um UUID novo a cada upsert — invalidando silenciosamente qualquer link já enviado ao cliente. Além disso, a foto original baixada do Custom Field `2068458` nunca era salva como arquivo próprio — só era usada como insumo do Pillow e descartada.
- **Causa raiz:** o Kommo entrega webhook em modelo "at least once" (comportamento normal de CRMs/webhooks — não é bug do Kommo), e o backend não tinha nenhuma proteção de idempotência contra reentregas do mesmo `lead_id`/`status_id`.
- **Correção 1 — checagem de idempotência em `receber_webhook_kommo`:** antes de qualquer trabalho pesado (consulta ativa, download, Pillow, Storage), a rota agora consulta se já existe um registro em `aniversariantes` para aquele `kommo_lead_id`; se existir, a reentrega é ignorada e a rota retorna cedo (`{"status": "ignorado", "mensagem": "Lead já processado anteriormente."}`), sem regenerar token nem tocar no Storage.
- **Correção 2 — nomes determinísticos no Storage:** `supabase_service.upload_flyer` e a nova `supabase_service.upload_foto_perfil` deixaram de usar `uuid.uuid4()` no nome do arquivo (`flyer_{lead_id}.jpg` / `foto_perfil_{lead_id}.jpg`) — combinado com `x-upsert: true` (já existente), qualquer reprocessamento do mesmo lead agora sobrescreve o mesmo objeto em vez de empilhar arquivos novos. Camada de defesa extra para o caso raro de duas reentregas quase simultâneas passarem pela checagem de idempotência antes de qualquer uma delas commitar.
- **Correção 3 — foto original passa a ser salva:** `finalizar_cadastro_aniversariante` agora sobe DOIS arquivos ao bucket `fotos-aniversariantes` — a foto original do cliente (`foto_perfil_url`, via nova `upload_foto_perfil`) e o flyer composto (`foto_url`, como já era). Nova coluna `foto_perfil_url` em `aniversariantes` (migration `20260807_01_add_foto_perfil_url_aniversariantes.sql`, já refletida em `sql/schema/01_tables_aniversariantes.sql`).
- **Foto original exposta ao formulário do convidado:** `GET /aniversariantes/validar-token/{token}` (`backend/app/routes/aniversariantes.py`) agora também devolve `foto_perfil_url`. No Flutter (`aniversariante_model.dart` + `register_screen.dart`), o banner circular do aniversariante passou a priorizar `fotoPerfilUrl` (a foto crua, correta para um avatar circular) em vez do flyer completo, com fallback para `fotoUrl` em cadastros antigos que ainda não tenham a foto de perfil salva.
- **Nota operacional (não é código):** vale checar do lado do Kommo/Salesbot por que o webhook está disparando 2-3x por entrada na etapa (ex.: múltiplas assinaturas de webhook apontando para a mesma URL, ou o passo de Webhook do Salesbot duplicado no fluxo) — a correção aplicada aqui é defensiva (o backend nunca deveria confiar em "exactly once" de um webhook), mas reduzir o número de disparos na origem também evitaria chamadas desperdiçadas à API do Kommo.
- **Verificação:** `python -m py_compile` em todos os arquivos alterados e import real do app FastAPI completo (com `.venv` ativado), confirmando que a checagem de idempotência e o upload da foto de perfil estão presentes no código carregado em runtime.

#### Arquivos afetados

- `backend/app/routes/webhooks.py` (checagem de idempotência antes da consulta ativa; `finalizar_cadastro_aniversariante` sobe foto original + flyer)
- `backend/app/services/supabase_service.py` (nomes determinísticos em `upload_flyer`; nova `upload_foto_perfil`)
- `backend/app/routes/aniversariantes.py` (`foto_perfil_url` no handshake de token)
- `frontend/lib/models/aniversariante_model.dart` (campo `fotoPerfilUrl`)
- `frontend/lib/views/register_screen.dart` (banner do aniversariante prioriza `fotoPerfilUrl`)
- `sql/migrations/20260807_01_add_foto_perfil_url_aniversariantes.sql` (nova)
- `sql/schema/01_tables_aniversariantes.sql` (coluna `foto_perfil_url` refletida na fonte da verdade)
- `CLAUDE.md` (4.2 — idempotência e nomes determinísticos; 7. — `foto_perfil_url` e descrição do bucket)

### Registro [07/08/2026] — Causa Raiz das Reentregas: Timeout do Kommo, Resolvido com Ack Imediato + Background Task

#### O que foi feito

- **Causa raiz real das múltiplas reentregas (complementa o registro anterior):** o usuário observou no terminal do ngrok que cada teste manual gerava vários `POST /webhooks/kommo` empilhados, todos sem `200 OK`, até um finalmente completar — a hipótese inicial era "duplicidade do Kommo ou do ngrok". Investigação confirmou que não é nem um nem outro: a rota fazia toda a cadeia pesada (consulta ativa na API do Kommo, download da foto no CDN com redirect, geração do flyer via Pillow, dois uploads no Supabase Storage, upsert no banco) de forma **síncrona**, só respondendo ao final. Somando os round-trips de rede dessa cadeia, a rota facilmente ultrapassava o tempo que o Kommo espera por um ACK — e o Kommo, não recebendo `200 OK` a tempo, reenviava o mesmo webhook. O padrão do ngrok (POSTs pendentes até um completar) é exatamente esse timeout+retry em ação.
- **Correção — ack imediato com `BackgroundTasks`:** `POST /webhooks/kommo` foi reestruturada. A parte síncrona da rota agora só extrai `lead_id`/`status_id` do payload e confere o filtro de etapa (`TARGET_STATUS_ID`) — tudo isso é local, sem I/O de rede, então é instantâneo. Todo o resto (idempotência, consulta ativa, download, Pillow, Storage, insert) foi extraído para uma nova função `processar_lead_confirmado(lead_id)`, agendada via `background_tasks.add_task(...)` (parâmetro `BackgroundTasks` do FastAPI). A rota responde `{"status": "recebido", ...}` e `200 OK` imediatamente após agendar, antes de qualquer chamada externa — o Kommo recebe o ACK rápido e não tem mais motivo para reenviar.
- **Efeito colateral esperado e aceito:** como o processamento agora roda depois da resposta HTTP já ter sido enviada, o corpo da resposta deixou de refletir o resultado real (sucesso, campos faltando, lead já processado) — esse resultado só aparece nos logs do Uvicorn (`🎉 TODOS OS DADOS COLETADOS`, `🏁 Processamento em background concluído`, ou os avisos de campos faltando/idempotência). `test_kommo.py` foi ajustado para deixar isso explícito no roteiro impresso.
- **A checagem de idempotência (registro anterior) continua sendo a defesa principal** contra efeitos colaterais de reentregas — ela não deixou de ser necessária com o ack imediato; mesmo com o Kommo parando de reenviar por timeout, uma reentrega genuína (ex.: falha de rede do lado do Kommo) ainda pode acontecer, e a checagem garante que ela não reprocesse nada.
- **Verificação:** `python -m py_compile` em `webhooks.py`, import real do app FastAPI completo (`.venv` ativado) confirmando a nova assinatura da rota (`request`, `background_tasks: BackgroundTasks`) e a presença de `processar_lead_confirmado`/`background_tasks.add_task` no código carregado em runtime.

#### Arquivos afetados

- `backend/app/routes/webhooks.py` (processamento pesado extraído para `processar_lead_confirmado`, agendado via `BackgroundTasks`; rota responde de imediato)
- `backend/app/test_kommo.py` (roteiro do PASSO 2 atualizado para explicar que o resultado real só aparece nos logs)
- `CLAUDE.md` (4.2 — nota de ack imediato + background task)

### Registro [10/08/2026] — Entrega do Flyer ao Cliente: Chats API e Salesbot API Descartados, Custom Field de Escrita Adotado

#### O que foi feito

- **Objetivo:** o cliente pede pra fazer o backend disparar o flyer pronto (imagem + link) direto no chat do Kommo (WhatsApp/Instagram/Facebook), sem depender do Salesbot pra montar a mensagem dinamicamente, já que o editor visual do Salesbot não suporta anexar mídia dinâmica por URL.
- **Investigação 1 — Chats API (amoJo):** a conta usa integração **nativa/oficial do Kommo com a Meta** para WhatsApp/Instagram/Facebook (confirmado pelo cliente) — não é um BSP terceiro. Ainda assim, a arquitetura de escopo do Kommo faz cada canal pertencer à integração que o criou; a integração privada do projeto é um app separado da integração nativa do Kommo, então **não deveria conseguir** injetar mensagem no canal nativo via Chats API. Confirmado indiretamente: `GET /api/v4/account?with=amojo_id` funciona e devolve um `amojo_id` real da conta, mas isso por si só não dá acesso de escrita ao canal nativo.
- **Investigação 2 — Disparo de Salesbot via API:** testadas 4 variações de endpoint (`/leads/{id}/salesbot/run`, `/leads/{id}/salesbot/{bot_id}/run`, `/salesbot/run`, leituras `GET /salesbot`) — todas retornaram **404 limpo** (rota inexistente, não erro de validação de campo). Também confirmado, inspecionando os handlers usados em `robo_teste_2.json` (export do Salesbot), que o robô só tem 6 tipos de passo (`action`, `buttons`, `goto`, `reaction`, `send_message`, `wait_answer`, `waits`) — nenhum deles chama uma URL externa e usa a resposta; o webhook que já dispara pro backend é configurado como automação da etapa do funil, fora do Salesbot.
- **Descoberta chave no `robo_teste_2.json`:** rastreada a sequência completa entre as duas etapas — `109983139` → espera **5s fixos** (timer cego, não checa se o backend terminou) → mensagem "criando seu flyer..." → `110029635` → espera **10s fixos** → mensagem final com um **botão de URL** (`"buttons": [{"type": "url", "url": "...", ...}]`) apontando pra uma URL de flyer **hardcoded** de um teste antigo. Duas conclusões: (1) confirma que depender da etapa `110029635` como gatilho seria arriscado — o timer de 15s é cego e pode disparar antes do backend terminar; (2) revela que o Salesbot **já** manda um botão de link com sucesso pros 3 canais — só falta tornar essa URL dinâmica.
- **Teste de merge tag — primeira tentativa falhou:** o cliente já tinha tentado (com apoio de outra IA) usar `{{lead.cf.dt1}}` (nome do campo) na mensagem, e o bot imprimiu o texto literal, sem substituir. Comparando com o único uso confirmado de `{{lead.cf.X}}` no export do bot (sempre como **ID numérico**, ex. `{{lead.cf.2068768}}`, usado como alvo de `set_custom_fields`), a hipótese foi: o problema era usar o *nome* do campo em vez do *ID*.
- **Teste de merge tag — confirmado funcionando:** cliente criou um Custom Field de teste ("Nome do flyer", ID `2068452`, já populado manualmente com `"TesteClaude123"`), montou um passo de teste com `Teste: {{lead.cf.2068452}}` e rodou no lead real de teste (`51640612`, criado a partir de uma mensagem real do WhatsApp pessoal do cliente, contato "Davi Henrick"). Resultado: a mensagem chegou como `Teste: TesteClaude123` — **leitura de Custom Field por ID numérico funciona** no texto de uma mensagem do Salesbot.
- **Solução adotada:** 2 Custom Fields novos criados no Kommo pelo cliente — **"URL do Flyer"** (ID `2069404`) e **"Link do Formulário"** (ID `2069406`, ainda sem uso — o domínio do formulário vai mudar pra `app-paparazzi.vercel.app` numa etapa futura). Nova função `kommo_service.atualizar_custom_fields_lead(lead_id, campos)` — primeira função de **escrita** do módulo (`PATCH /api/v4/leads/{id}`, corpo `custom_fields_values: [{field_id, values: [{value}]}]`), validada com um teste real de escrita+leitura no lead `51640612` antes de entrar no código de produção. Chamada em `finalizar_cadastro_aniversariante`, logo após o upsert em `aniversariantes` ter sucesso, gravando a URL do flyer (`foto_url`) no Custom Field `2069404`. Best-effort: se o Kommo recusar a gravação, só loga erro — não desfaz o cadastro já salvo no Supabase.
- **O que falta (fora do escopo deste registro):** ajuste manual do cliente no Salesbot, trocando o texto/botão hardcoded do step 166 (e possivelmente o timer de 15s, que hoje corre o risco de disparar antes do backend terminar de gravar o Custom Field) para referenciar `{{lead.cf.2069404}}`; e, numa etapa futura, escrever também o Custom Field `2069406` com o link do formulário no domínio correto do Vercel.
- **Verificação:** `python -m py_compile` em `webhooks.py` e `kommo_service.py`, import real do app FastAPI completo (`.venv` ativado) confirmando a presença de `atualizar_custom_fields_lead` e da chamada dentro de `finalizar_cadastro_aniversariante`, e teste real (não simulado) de escrita+leitura do Custom Field `2069404` no lead de teste `51640612` via API antes de escrever o código de produção.

#### Arquivos afetados

- `backend/app/services/kommo_service.py` (nova `atualizar_custom_fields_lead` — primeira função de escrita do módulo)
- `backend/app/routes/webhooks.py` (`CAMPO_URL_FLYER_ID`; `finalizar_cadastro_aniversariante` grava a URL do flyer no Kommo após o upsert)
- `CLAUDE.md` (4.2 — decisão de 10/08/2026: Chats API e Salesbot API descartados, Custom Field de escrita adotado)

### Registro [10/08/2026] — Botão do Flyer Abria no Navegador em Vez de Baixar: Corrigido com `?download`

#### O que foi feito

- **Bug reportado após o Custom Field entrar em produção:** com `{{lead.cf.2069404}}` já funcionando no botão de URL do Salesbot (confirmado pelo cliente, incluindo timers de 5s/10s do bot que se mostraram rápidos o suficiente na prática, sem precisar de ajuste), o clique no botão abria o flyer direto no navegador do celular em vez de baixar o arquivo — o cliente precisaria printar a tela pra guardar a imagem, perdendo qualidade (relevante porque o flyer final vai ter proporção fixa, que o print distorce).
- **Causa raiz e correção:** URLs públicas do Supabase Storage não vêm com `Content-Disposition: attachment` por padrão — o navegador decide exibir inline por ser `image/jpeg`. Validado empiricamente (`HEAD`/`GET` contra um objeto real do bucket, com e sem o parâmetro) que anexar `?download` (ou `?download=<nome>`) na URL pública faz o Supabase Storage responder com `Content-Disposition: attachment`, forçando o download do arquivo original em vez de abrir inline.
- **Implementação:** `supabase_service.upload_flyer()` agora devolve a URL do flyer com `?download=flyer-paparazzi-gold-bar.jpg` (nova constante `NOME_DOWNLOAD_FLYER`) — sem alterar o nome do objeto no bucket, só o nome sugerido no download. `upload_foto_perfil()` não foi alterada (essa URL é carregada normalmente via `Image.network` no formulário do convidado, onde `Content-Disposition` não tem efeito).
- **Verificação:** teste real (não simulado) — upload de um JPEG de 1x1 pixel para um objeto de teste (`flyer_TESTE_DOWNLOAD_PARAM.jpg`) usando a função real `upload_flyer()`, confirmando via `GET` que a URL retornada já vem com `?download=...` e que o Supabase responde com o header `Content-Disposition: attachment` correto. `python -m py_compile` em `supabase_service.py` e `webhooks.py`. O objeto de teste ficou no bucket (a chave configurada não tem permissão de `DELETE` no Storage — só upload/leitura); é inofensivo, nome claramente marcado como teste, nunca colide com um `kommo_lead_id` real (sempre numérico).

#### Arquivos afetados

- `backend/app/services/supabase_service.py` (`upload_flyer` devolve URL com `?download`; nova constante `NOME_DOWNLOAD_FLYER`)
- `CLAUDE.md` (4.2 — nota do `?download` na entrega do flyer)

### Registro [10/08/2026] — Composição Real do Flyer: Molduras Oficiais Opacas, Cartão Dinâmico e Fonte com Acentos

#### O que foi feito

- **Molduras placeholder substituídas pela arte oficial:** até este registro, `backend/app/assets/templates/` tinha 4 PNGs gerados via Pillow só pra testar o carregamento (confirmado inspecionando visualmente um deles: texto literal "PLACEHOLDER - SUBSTITUIR PELA ARTE OFICIAL"). O usuário substituiu pelos 3 arquivos reais (`moldura_sexta_boteco.png`, `moldura_sabado_feijoada.png`, `moldura_domingo_churrasco.png` — `sabado_noite` não usado nesta fase).
- **Mudança de arquitetura — moldura opaca, não mais PNG transparente:** a arte real vem em RGB (sem canal alfa), diferente do desenho original (moldura "vazada", alpha-composite sobre a foto). A moldura virou o próprio canvas de base do flyer; a foto do cliente é colada POR CIMA dela, dentro de uma janela retangular própria. `flyer_generator.py` foi reescrito para esse modelo.
- **Mapeamento de coordenadas por inspeção visual + amostragem de pixel:** sem nenhuma documentação de design pra essas coordenadas, mapeei a área da foto e as 3 linhas do cartão de dia/data/horário sobrepondo uma grade de coordenadas na própria arte (script Pillow ad-hoc) e lendo os limites a olho contra a grade, confirmando com amostragem de cor de pixel (`Image.load()[x,y]`) que a mesma proporção bate nas 3 molduras (cada uma com tamanho em pixels levemente diferente). Coordenadas guardadas como **frações (0–1)** do tamanho da moldura, não pixels fixos, exatamente por causa dessa variação de tamanho entre os 3 arquivos.
- **Cartão de dia/data/horário: apagar e redesenhar.** A arte já vem com um dia/data/horário fictício desenhado (ex.: "SEXTA FEIRA" / "10/08" / "18:00") — a pedido do usuário, sugeri (e ele aplicou na arte) abrir uma linha nova entre o dia e o horário especificamente pra data, formato `DD/MM`. Cores do texto (cinza-champanhe `(178,162,146)` para dia/data, âmbar `(161,101,0)` para horário) e cor de fundo do cartão (preto sólido) amostradas por histograma de pixel da própria arte, pra o texto redesenhado bater visualmente com o resto do design.
- **Faixa do nome sobre a foto:** a arte não reserva espaço pro nome do aniversariante — decisão do usuário foi desenhar uma faixa semitransparente na base da caixa da foto, com o nome centralizado (auto-scaling de fonte, mesma lógica já usada antes).
- **Bug encontrado e corrigido durante a validação visual — resquício do texto antigo:** o primeiro teste real mostrou um "fantasma" do texto fictício original (ex. "FEIRA", "18:00") vazando por cima do texto novo — a caixa de "apagar" estava medida rente demais ao texto original, que tem um leve efeito de brilho que sangra alguns pixels além do corpo da letra. Corrigido aumentando a margem das 3 áreas do cartão.
- **Bug encontrado e corrigido durante a validação visual — acentos quebrados:** `backend/app/assets/fonts/` nunca teve de fato a fonte customizada (só um README pedindo pra colocar uma) — o fallback (`ImageFont.load_default` do Pillow) não tem os acentos do português, e "SÁBADO"/"João" saíam com o caractere quebrado (□). Baixada `PlayfairDisplay-Bold.ttf` do repositório oficial `google/fonts` no GitHub (via API do GitHub, licença OFL) — a família só é distribuída como "variable font" hoje (sem mais arquivo estático por peso), então `_carregar_fonte()` passou a chamar `set_variation_by_axes([700])` pra garantir o peso Bold.
- **Seleção automática de moldura pelo dia da semana:** nova `selecionar_template_e_dia(data_reserva)` deriva o `template_name` e o texto do dia a partir de `data.weekday()`. Segunda a quinta (sem moldura própria nesta fase) cai num fallback com aviso no log, sem derrubar o flyer.
- **`horario` passa a ser lido e usado:** o Custom Field "Horário da reserva" (`2068854`) já era consultado pela busca ativa, mas nunca tinha sido de fato usado em nada — agora é extraído em `webhooks.py` e passado até `generate_flyer`. Formatação defensiva (`formatar_horario_exibicao`): o Kommo tem devolvido só a hora, sem minuto (ex. `"12"`), formatado como `"12:00"`.
- **Estimativa de convidados confirmada como fora do flyer** (decisão do usuário) — usada só para benefícios internos e para a equipe saber o número de cadeiras.
- **Verificação:** `python -m py_compile` em todos os arquivos alterados, import real do app FastAPI completo, e — mais importante — **geração real de flyers de teste** (não simulada) para os 3 templates, com foto sintética e nome longo/acentuado (`"João Pedro Nascimento"`), inspecionados visualmente após cada ajuste até o resultado ficar limpo (sem resquício de texto antigo, acentos corretos, faixa do nome legível). Também testados os caminhos de fallback (moldura inexistente, data em dia útil, data em formato inválido) sem derrubar a geração.

#### Arquivos afetados

- `backend/app/assets/templates/moldura_sexta_boteco.png`, `moldura_sabado_feijoada.png`, `moldura_domingo_churrasco.png` (substituídos pela arte oficial, fornecidos pelo usuário)
- `backend/app/assets/templates/README.md` (atualizado — molduras já são a arte oficial, `sabado_noite` fora de uso, coordenadas proporcionais)
- `backend/app/assets/fonts/PlayfairDisplay-Bold.ttf` (nova — baixada do `google/fonts`)
- `backend/app/assets/fonts/README.md` (atualizado)
- `backend/app/services/flyer_generator.py` (reescrito — moldura opaca como canvas base, cartão dinâmico, faixa do nome, seleção por dia da semana, fonte com peso Bold via variable font)
- `backend/app/routes/webhooks.py` (`horario_reserva` extraído e passado até `generate_flyer`; `finalizar_cadastro_aniversariante` ganhou o parâmetro `horario_reserva`)
- `CLAUDE.md` (nova seção 4.6 — Geração do Flyer)

### Registro [10/08/2026] — 2ª Revisão da Arte: Layout Uniforme 1080x1920, Acabamento "Dourado Premium" e Fonte Condensada

#### O que foi feito

- **Arte das molduras substituída de novo pelo usuário:** as 3 molduras (`sexta_boteco`, `sabado_feijoada`, `domingo_churrasco`) foram trocadas por uma 2ª revisão — agora uniformes em **1080×1920** (9:16 exato; a 1ª versão tinha um tamanho em pixels levemente diferente entre as 3). A versão anterior foi preservada pelo usuário em `backend/app/assets/templates/backup_molduras/`, usada como referência visual nesta sessão. O dia da semana ("SEXTA FEIRA" etc.) continua fixo na arte; o espaço de data/horário passou a vir **em branco** (fundo preto sólido já desenhado), sem mais nenhum texto fictício — coordenadas de sobreposição inteiramente remapeadas (grade de coordenadas + zoom, mesmo processo da sessão anterior).
- **Acabamento visual "dourado premium" especificado pelo usuário:** com base numa referência gerada por IA, o usuário passou uma especificação bem detalhada (cores hex exatas, gradiente, contorno, sombra, brilho, família tipográfica) pra data e horário, pedindo explicitamente que o horário usasse a mesma cor/fonte do nome do aniversariante. Implementado `_desenhar_texto_com_efeito()`, que renderiza cada texto num tile RGBA próprio com: sombra suave, contorno fino opcional (`stroke_width`/`stroke_fill` do Pillow), preenchimento sólido OU gradiente vertical multi-stop (`_criar_gradiente_vertical`, interpolação linear entre as cores) recortado exatamente na forma das letras via máscara do glifo, e brilho discreto opcional (camada borrada por baixo do texto principal, `ImageFilter.GaussianBlur`). Data usa preenchimento sólido bege-champanhe (`#D8D0C8`); horário e nome do aniversariante usam o mesmo gradiente dourado (`#B87500` → `#F2B900` → `#C98500`) + contorno (`#8A5A00`) + brilho.
- **Fonte trocada de serifada pra condensada:** a especificação do usuário pedia explicitamente uma tipografia condensada/pesada tipo "Roboto Condensed Bold / Arial Narrow Bold", nunca serifada nem cursiva — `PlayfairDisplay-Bold.ttf` (elegante, serifada, usada até a sessão anterior) foi trocada por `RobotoCondensed-Bold.ttf` em todo texto desenhado pelo backend. Baixada do repositório oficial `google/fonts` (mesmo processo da fonte anterior — API do GitHub pra achar o arquivo real, já que a família só é distribuída como "variable font").
- **Dia da semana só é reescrito no fallback:** como o dia da semana agora vem fixo na própria arte (sempre corresponde ao `template_name` no caminho normal, já que um deriva do outro), `_desenhar_cartao_dia_data_horario()` só apaga e redesenha essa linha quando `template_name` não bate com o dia calculado — ou seja, só no caminho de fallback (`TEMPLATE_FALLBACK`, quando a data cai numa segunda-quinta). Evita trabalho e risco de regressão visual desnecessários no caminho normal.
- **Verificação:** `python -m py_compile`, import real do app FastAPI, e geração real de flyers de teste pros 3 templates (nome longo/acentuado) e pro caminho de fallback (data numa terça-feira) — inspeção visual com zoom nas áreas de texto confirmando gradiente/contorno/brilho corretos, nenhum resquício de arte antiga (o "retângulo preto" atrás da data/horário foi confirmado como parte intencional da nova arte, comparando com a moldura original sem nenhuma edição — não é bug do código), e acentos corretos.

#### Arquivos afetados

- `backend/app/assets/templates/moldura_sexta_boteco.png`, `moldura_sabado_feijoada.png`, `moldura_domingo_churrasco.png` (2ª revisão da arte, fornecida pelo usuário — 1080x1920 uniforme)
- `backend/app/assets/templates/backup_molduras/` (nova — versão anterior da arte, preservada como referência)
- `backend/app/assets/templates/README.md` (atualizado)
- `backend/app/assets/fonts/RobotoCondensed-Bold.ttf` (nova — baixada do `google/fonts`, substitui Playfair Display no código)
- `backend/app/assets/fonts/README.md` (atualizado)
- `backend/app/services/flyer_generator.py` (reescrito — coordenadas remapeadas pro novo layout, `_desenhar_texto_com_efeito`/`_criar_gradiente_vertical` novos, dia da semana só reescrito no fallback)
- `CLAUDE.md` (4.6 reescrita)

### Registro [10/08/2026] — Causa Raiz do Desalinhamento: Janelas Vazadas de Verdade na 3ª Revisão da Arte, Coordenadas Passam a Ser Detectadas via Canal Alfa

#### O que foi feito

- **Bug reportado pelo usuário:** cores, fonte e posicionamento de foto/data/horário saindo "tortos", sem centralizar como esperado. Investigando, o usuário esclareceu o motivo: a arte mudou de novo — as áreas da foto e do cartão de data/horário agora são **janelas vazadas de verdade** (canal alfa variando de 0 a 255), não mais um retângulo preto opaco desenhado. O código ainda estava na arquitetura da revisão anterior (moldura 100% opaca, coordenadas medidas a olho e guardadas como proporção fixa) — descasado da arte real, causando o desalinhamento.
- **Confirmado por inspeção do canal alfa:** `moldura.getchannel("A")` tinha extremos `(0, 255)` — transparência real. Uma máscara binária (alfa < 128) revelou visualmente duas regiões brancas bem definidas: um retângulo maior (foto) e um menor à esquerda (cartão). O texto do dia da semana ("SEXTA FEIRA" etc.) continua opaco (alfa 255) — só foto e cartão de data/horário viraram vazados.
- **Mudança de arquitetura — detecção via canal alfa em vez de coordenadas medidas a olho:** nova `_detectar_areas_vazadas()`, que varre a máscara de transparência da moldura carregada, identifica as 2 faixas horizontais contíguas com pixel vazado, e calcula o bounding box exato de cada uma (a de menor `x` é sempre o cartão — layout fixo da casa). Elimina de vez o processo manual (grade de coordenadas + zoom + amostragem de pixel, repetido 3 vezes nesta sessão a cada nova versão da arte) — qualquer moldura futura com essas 2 janelas no padrão esperado passa a funcionar automaticamente.
- **Composição reestruturada:** canvas base preto → foto colada na janela exata (via `alpha_composite`, não mais paste numa coordenada fixa) → moldura RGBA composta por cima (as janelas revelam o que já foi colado embaixo) → data/horário desenhados dentro da janela do cartão (dividida ao meio) → faixa do nome. O dia da semana só é apagado/redesenhado no caminho de fallback (quando o template não bate com o dia real), já que não está mais dentro de nenhuma janela vazada detectável via alfa.
- **Bug secundário encontrado na validação visual:** mesmo com o alinhamento corrigido, sobrava uma emenda retangular sutil atrás da data — rastreada até a cor do canvas base (`(8,8,8)`) não bater exatamente com o preto real do fundo da arte (`(0,0,0)`, confirmado por amostragem). Corrigido trocando `COR_FUNDO_BASE` pra preto puro.
- **Pergunta do usuário sobre usar IA generativa (GPT/etc.) pra fazer essa composição inteira** (ler dados, pegar foto, redimensionar, montar na moldura) em vez de código: avaliado e **desaconselhado** como mecanismo principal do pipeline automatizado — motivos: (1) modelos de geração de imagem não são determinísticos, o mesmo input pode sair diferente a cada geração; (2) risco real de degradar texto/logo/elementos da arte original (esses modelos são conhecidos por "reinterpretar" partes da imagem em vez de preservar exatamente); (3) historicamente ruins pra renderizar strings exatas fornecidas pelo usuário (nome, data, hora) sem erro de grafia/acento — exatamente o problema que já estava sendo resolvido aqui; (4) custo e latência por geração, multiplicados pelo volume de aniversariantes; (5) novo ponto de falha externo (API terceira) na cadeia. A abordagem com Pillow é determinística, gratuita, quase instantânea, e agora auto-ajustável a mudanças de arte via detecção de canal alfa — resolvendo o problema real (imprecisão de coordenadas medidas a olho) sem trocar de tecnologia.
- **Verificação:** `python -m py_compile`, import real do app FastAPI, e geração real de flyers de teste pros 3 templates com foto sintética — zoom nas áreas da foto (encaixe perfeito, sem folga contra a borda dourada) e do cartão (data/horário corretamente centralizados dentro da janela detectada, emenda de cor corrigida).

#### Arquivos afetados

- `backend/app/services/flyer_generator.py` (reescrito — `_detectar_areas_vazadas` nova, composição via `alpha_composite` com janelas detectadas, `COR_FUNDO_BASE` corrigida pra preto puro)
- `CLAUDE.md` (4.6 reescrita — arquitetura de detecção via canal alfa)

### Registro [11/08/2026] — Preparação do Deploy Gratuito (saída do ngrok/uvicorn local)

#### O que foi feito

- **Decisão de hospedagem:** com o fluxo de flyer validado end-to-end, o próximo passo é tirar o backend da máquina local (hoje exposto via túnel ngrok + `uvicorn --reload`) para uma URL pública fixa e gratuita, antes de atacar as próximas frentes do MVP (formulário de convidados, app mobile). Avaliadas as opções gratuitas reais em 2026 — Railway e Fly.io deixaram de ter tier gratuito perene (viraram trial pago), Oracle Cloud Always Free teve a cota cortada pela metade em 15/06/2026 sem aviso e sofre com erro de capacidade esgotada ao provisionar a VM Ampere A1. Optou-se por **Render (plano free)** como primeira tentativa — deploy mais simples (conecta o GitHub, build automático), sem exigir cartão. Limitação conhecida: o serviço free hiberna após 15 min sem tráfego (acorda em ~1 min no próximo request), o que pode reintroduzir o sintoma de reentrega de webhook já depurado em 07/08/2026 caso o Kommo dispare o webhook justo com o serviço dormindo. Mitigação combinada: ping externo (UptimeRobot ou GitHub Actions agendado) batendo em `/health` a cada ~10-14 min para manter o serviço sempre acordado (consome quase toda a cota de 750h/mês, suficiente para 1 serviço 24/7). **Google Cloud Run** fica catalogado como plano B caso o Render não atenda (cota "Always Free" permanente maior e cold start de segundos em vez de minutos, sem precisar de hack de keep-alive) — migração é barata pois nenhuma lógica do app muda, só endpoint da URL do webhook no Kommo e a forma de empacotar (Dockerfile).
- **Endpoint de health check:** criado `GET /health` em `backend/app/main.py`, retornando `{"status": "ok"}` — usado tanto pelo health check nativo do Render quanto pelo ping externo de keep-alive, sem tocar Supabase/Kommo a cada chamada.
- **Blueprint do Render:** criado `render.yaml` na raiz do repositório, documentando build command (`pip install -r backend/requirements.txt`), start command (`uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`) e as chaves de variável de ambiente esperadas (valores sensíveis ficam de fora do arquivo, preenchidos manualmente no dashboard do Render).
- **Atenção para depois do deploy:** a URL do webhook cadastrada no Kommo precisa ser trocada da URL do ngrok para a URL fixa do Render, e o modo de teste (`KOMMO_WEBHOOK_TEST_MODE`) deve permanecer `false` em produção. Também sinalizado o risco de pausa automática do Supabase free (7 dias sem requisição ao banco) — mesma lógica de ping externo resolve.

#### Arquivos afetados

- `backend/app/main.py` (novo endpoint `GET /health`)
- `render.yaml` (novo — blueprint de deploy do Render)
- `docs/diario_projeto.md`

### Registro [17/08/2026] — Correção de Documentação e Validação com Lead Real (Foto e QR Code)

#### O que foi feito

- **Divergência encontrada entre documentação e código:** ao retomar o trabalho no formulário do convidado, uma auditoria do código-fonte (não só do diário/CLAUDE.md) mostrou que `frontend/lib/views/register_screen.dart` já tem a tela "Passaporte VIP" completa (QR Code real via `qr_flutter`, usando o `qr_code_token` devolvido por `POST /convidados/confirmar`) e que `frontend/lib/views/portaria_screen.dart` já implementa a Portaria Expressa inteira (leitura de câmera via `mobile_scanner`, os 3 estados de resultado, busca manual por CPF, modo VIP com confete). O backend (`backend/app/routes/convidados.py`) também já tinha as rotas `POST /convidados/validar-qr` e `GET /convidados/buscar-cpf/{cpf}` implementadas. Nenhum desses itens estava de fato pendente — só não tinham sido marcados como concluídos no diário nem no checklist (seção 3), provavelmente implementados numa sessão anterior sem o devido registro. Checklist da seção 3 corrigido nesta data.
- **Único item genuinamente pendente da Portaria/ERP:** a fila assíncrona de abertura de comanda no Epoc ERP — confirmado (via busca no backend) que nenhum código toca a tabela `comandas_temporarias` nem faz qualquer chamada ao Epoc. Segue bloqueado por falta de acesso à API do Epoc (nenhuma mudança nesta data).
- **Comentário obsoleto corrigido em `frontend/lib/services/api_service.dart`:** o método `buscarConvidadoPorCpf` tinha um comentário de 4 linhas avisando que `GET /convidados/buscar-cpf/{cpf}` "ainda não existe no backend" — desatualizado, já que a rota existe e está em uso pela busca manual da Portaria. Comentário removido/atualizado.
- **Dúvida do usuário sobre o deploy do Vercel:** o usuário reportou não se recordar se o build publicado no Vercel já é o que busca a foto do aniversariante dinamicamente a partir do `token` da URL (relato: o formulário publicado parece mostrar uma foto fixa/fictícia) e relatou que o QR Code gerado no site publicado parece **fixo**, não um UUID novo por convidado. Como não há nenhuma referência a uma URL do Render nem a um `vercel.json`/config de build neste repositório, não foi possível confirmar por código qual `API_URL` (`--dart-define`) o build publicado no Vercel está usando — há indício de que o deploy publicado é anterior a este fluxo dinâmico (foto/QR reais), ou está apontando para um backend fora do ar/errado. **Ação pendente do usuário:** conferir no dashboard do Vercel (1) se o último deploy é deste repositório/commit atual e (2) qual valor de `API_URL` foi usado no build (`flutter build web --dart-define=API_URL=...`).
- **Validação read-only contra dados reais, sem enviar nenhuma mensagem no chat do Kommo, para responder às duas dúvidas acima:**
  1. Localizado o pipeline **"Novo funil teste"** (`pipeline_id` `14128055`) via `GET /api/v4/leads/pipelines`; 3 leads nele têm os 5 Custom Fields obrigatórios preenchidos. Usado o Lead **`51343366`** ("Geovane", reserva em `2026-09-08`) — já tinha registro em `aniversariantes` de um teste anterior (`token_exclusivo` `ec69939c-39f0-4c78-a807-9cd277b1947d`).
  2. **Foto real, não fictícia — confirmado:** baixados os bytes da foto atual do Custom Field "Foto do aniversariante" (`2068458`) direto do CDN do Kommo (`kommo_service.montar_url_cdn_arquivo`) e os bytes de `foto_perfil_url` salva no Supabase para esse mesmo lead. SHA-256 e tamanho em bytes **idênticos** nos dois — prova que o backend está salvando exatamente a foto que o aniversariante enviou pelo chat, não uma foto de placeholder.
  3. **QR Code com UUID único — confirmado:** consultados (`SELECT` read-only) os últimos registros reais da tabela `convidados`; todos os `qr_code_token` retornados são diferentes entre si, confirmando na prática (não só pela leitura do schema, `DEFAULT gen_random_uuid()`) que cada confirmação de presença gera um token novo — nenhum valor fixo do lado do backend/banco.
  4. **Conclusão:** a lógica do backend (foto real + QR único) está correta e validada com dados reais. O comportamento "foto fictícia / QR fixo" relatado pelo usuário no site publicado no Vercel é, com alta probabilidade, um problema do **deploy publicado** (build desatualizado ou `API_URL` incorreta/apontando para um backend fora do ar), não do código atual do repositório.
  5. Token real e válido disponível para o usuário testar diretamente o formulário publicado (local ou Vercel) e comparar com o esperado (nome "Geovane", foto real do lead `51343366`): `ec69939c-39f0-4c78-a807-9cd277b1947d`.
- **Backend em produção no Render confirmado no ar (achado não documentado até então):** o `render.yaml` (registro de 11/08/2026) só descrevia o *blueprint*, sem nenhuma URL viva registrada em lugar nenhum do repositório. Testado diretamente: `GET https://paparazzi-api.onrender.com/health` responde `200 {"status":"ok"}`, e `GET /aniversariantes/validar-token/ec69939c-39f0-4c78-a807-9cd277b1947d` devolve os dados corretos do lead `51343366` (nome + `foto_perfil_url` batendo com o achado do item acima) — ou seja, o backend de produção já está deployado, acessível publicamente e servindo dados reais e corretos do Supabase. CORS também confirmado funcionando (`CORSMiddleware(allow_origins=["*"])` em `main.py`, testado com header `Origin: https://app-paparazzi.vercel.app` simulado — resposta veio com `access-control-allow-origin` refletido corretamente).
- **Causa mais provável do "deploy antigo" no Vercel identificada pelo usuário:** o projeto do Vercel parece estar conectado a um repositório Git com o mesmo nome do atual, mas que não é mais o mesmo repositório (histórico do Git deste repositório começa do zero em `d1ace7c "chore: estrutura inicial do repositório"` — indício de que o repositório atual foi recriado/reiniciado em algum momento após o trabalho já registrado neste diário ter sido feito). Isso é consistente com uma falha comum de integração do Vercel: quando um repositório GitHub é apagado e recriado com o mesmo nome, o ID interno muda e a integração Git do Vercel (que rastreia por ID, não por nome) fica órfã, continuando a servir o último build que conseguiu puxar do repositório antigo. Confirmado (via `git ls-files`) que `frontend/build/` **não é** a causa — está corretamente no `.gitignore`, nunca foi commitado.
- **Ação recomendada (fora do escopo de execução do Claude Code — requer acesso ao dashboard do Vercel):** tentar primeiro reconectar o repositório Git dentro do MESMO projeto Vercel existente (Settings → Git → Disconnect, depois Connect novamente apontando para o repositório atual) — preserva domínio, variáveis de ambiente e configuração de build já existentes. Se o Vercel não conseguir localizar/religar ao repositório correto, importar como projeto novo (New Project → Import Git Repository), reconfigurando build command com o backend de produção já confirmado: `flutter build web --dart-define=API_URL=https://paparazzi-api.onrender.com`.
- **Nenhuma escrita foi feita no Kommo nem no Supabase durante esta validação** — só `GET`/`SELECT`. Script de investigação usado ficou fora do repositório (pasta de scratchpad da sessão), por ser só uma ferramenta de diagnóstico pontual, não parte do produto.

#### Arquivos afetados

- `docs/diario_projeto.md` (este registro + checklist da seção 3 corrigido)
- `frontend/lib/services/api_service.dart` (comentário obsoleto sobre `buscar-cpf` corrigido)

### Registro [18/08/2026] — Login de Funcionários (Supabase Auth) + Painel de Aniversariantes do Dia

#### O que foi feito

- **Ajuste de UX na Portaria (pedido do usuário após teste real em campo):** o resultado do scan (verde/vermelho/laranja) sumia rápido demais — 3s não dava tempo de ler nome/CPF na tela. Aumentado para 7s (`portaria_screen.dart`); o toque na tela pra liberar leitura antes do tempo já existia (`GestureDetector` + texto "Toque na tela para voltar ao scanner"), só não tinha sido notado.
- **Decisão de produto (planejada com `EnterPlanMode`, plano aprovado antes de codar):** login de funcionário vira a porta de entrada de tudo que é operacional. Portaria (antes pública via `?modo=portaria`) e um painel novo de aniversariantes do dia passam a viver dentro de um Hub pós-login. O fluxo do convidado (`?token=`) continua público. Autenticação via Supabase Auth, um usuário por funcionário (não senha única compartilhada) — decisão do usuário, ver conversa da sessão.
- **Persistência de horário/estimativa:** `horario_reserva` (TIME) e `estimativa_convidados` (INTEGER) — Custom Fields do Kommo que antes só eram usados pra desenhar o flyer e descartados — passam a ser gravados em `aniversariantes` (`webhooks.py::finalizar_cadastro_aniversariante`, novo parâmetro `estimativa_convidados_raw` + nova `converter_estimativa_convidados_kommo`, reaproveitando `flyer_generator.formatar_horario_exibicao` já existente pra normalizar o horário).
- **Novo endpoint `GET /aniversariantes/hoje` (staff-only):** filtra `aniversariantes` por `data_reserva = hoje`, conta convidados confirmados por `lead_id` (2 queries + merge em Python — sem view SQL nova, volume diário baixo não justifica).
- **Autenticação sem segredo novo:** `backend/app/services/auth_service.py`, dependency `obter_funcionario_autenticado`, valida `Authorization: Bearer <token>` chamando `supabase_client.auth.get_user(token)` — método pronto do SDK `supabase-py` já usado em todo o backend (por baixo, `GET /auth/v1/user` na própria API do Supabase). Decisão tomada por um agente de planejamento (`Plan` subagent) depois de investigar o SDK instalado e achar que ele já expunha esse método pronto — descartou tanto decodificação local de JWT (exigiria `SUPABASE_JWT_SECRET` novo) quanto uma chamada HTTP manual (redundante, o SDK já faz isso). Protegidas: `POST /convidados/validar-qr`, `GET /convidados/buscar-cpf/{cpf}`, `GET /aniversariantes/hoje`. Não há RLS por trás — é só gate de rota no FastAPI, o backend continua usando a chave `anon` de sempre pra consultar as tabelas.
- **Frontend:** `supabase_flutter` adicionado; `main.dart` inicializa o client Supabase (`SUPABASE_URL`/`SUPABASE_KEY` via `--dart-define`, reaproveitando a MESMA `SUPABASE_URL`/chave que o backend já usa — confirmado antes, decodificando o JWT localmente, que é a chave `anon`, segura pro build Web). Novo `StaffGate` (StreamBuilder sobre `auth.onAuthStateChange`, sem Provider/Riverpod/Bloc) decide entre `LoginScreen` e `HubScreen`; `HubScreen` navega (Navigator 1.0 clássico) pra `PortariaScreen` e a nova `PainelDiaScreen`. `api_service.dart` anexa `Authorization: Bearer <access_token>` da sessão ativa nas 3 chamadas staff-only; nova `NaoAutorizadoException` pra 401.
- **`flutter build web` validado localmente** com os 3 `--dart-define` (`API_URL`, `SUPABASE_URL`, `SUPABASE_KEY`) antes de qualquer deploy — compilou limpo, só avisos de lint pré-existentes no resto do projeto (`flutter analyze`, 31 issues, todos `info`/deprecação, nenhum erro).
- **Acesso ao Supabase ampliado, a pedido do usuário, pra eu conseguir aplicar mudanças de schema e criar contas sem depender de intervenção manual a cada vez:** duas credenciais novas, validadas antes de usar (decodificação local do JWT + uma chamada real de cada uma) e guardadas **só no `.env` local** (nunca em `render.yaml`/Vercel):
  - `SUPABASE_DB_URL` (connection string direta do Postgres) — usada por um novo `backend/app/aplicar_migration.py`, que roda um arquivo de `sql/migrations/` direto no banco (sem precisar colar no SQL Editor do dashboard).
  - `SUPABASE_SERVICE_ROLE_KEY` — usada pra criar contas de funcionário via `auth.admin.create_user` (API administrativa do Supabase Auth).
- **Prática de backup antes de alteração de schema, adotada a pedido do usuário como padrão permanente (não precisa reautorizar a cada vez):** antes de cada `ALTER TABLE` em produção, um dump JSON das tabelas afetadas (`supabase.table(...).select("*")`) salvo fora do repositório. Feito duas vezes nesta sessão, antes de cada uma das duas migrations aplicadas.
- **Duas migrations aplicadas em produção nesta sessão** (via `aplicar_migration.py`, backup antes de cada uma):
  1. `20260817_01_add_horario_estimativa_aniversariantes.sql` (nova) — `horario_reserva`/`estimativa_convidados`.
  2. `20260725_01_add_cpf_aniversariantes.sql` — **achado durante o trabalho:** essa migration já existia no repositório desde 25/07/2026, documentada em `CLAUDE.md` como aplicada, mas a coluna `cpf` simplesmente não existia no banco real (confirmado consultando `information_schema.columns` antes e depois) — ficou só no papel por mais de 3 semanas. Aplicada agora, a pedido explícito do usuário. Continua sem nenhum fluxo real que a popule (mesmo aviso do arquivo original).
- **Primeira conta de funcionário criada** via `service_role` (`auth.admin.create_user`, `email_confirm=True`) — usando o e-mail já conhecido do usuário como titular do projeto. Senha temporária gerada e comunicada fora do repositório (nunca gravada em nenhum arquivo versionado). **Decisão sobre o fluxo de criação de contas:** para este primeiro momento (MVP), manter a criação manual/via script é suficiente — não existe ainda tela de autoatendimento nem gestão de usuários no app. Avaliado usar CPF ou telefone como identificador de login em vez de e-mail, mas **descartado**: Supabase Auth é nativamente e-mail/telefone, CPF como login exigiria uma camada própria de mapeamento sem ganho real (todo funcionário já tem e-mail funcional). Catalogado como melhoria de Fase 1.5/2 (ver `docs/paparazzi_resumo_projeto.md`): tela de gestão de funcionários dentro do próprio Hub, atrás de um papel "admin", com CPF/telefone entrando só como dado de perfil (auditoria), não como credencial.
- **Checkpoint de git:** commit local criado antes de aplicar qualquer migration (rastreabilidade caso algo desse errado), seguido do commit/push desta etapa. Nenhum segredo (`.env`) foi commitado — conferido explicitamente antes do `git add`.
- **Risco de sequenciamento de deploy, sinalizado antes de publicar:** proteger as rotas da Portaria no backend antes do build novo do Vercel (com login) estar publicado quebraria a Portaria em uso real no bar (401 nas chamadas do frontend antigo, que não manda `Authorization`). Backend e frontend desta feature publicados juntos.
- **Deploy no Vercel — limite de 256 caracteres no Build Command:** o comando completo (clonar o Flutter + `flutter build web` com os 3 `--dart-define`) passa do limite do campo. Resolvido com `vercel_build.sh` (novo, raiz do repo) — script que lê `API_URL`/`SUPABASE_URL`/`SUPABASE_KEY` como variáveis de ambiente do próprio Vercel (Project Settings → Environment Variables, sem limite de tamanho) em vez de literais na linha de comando; Build Command no painel vira só `bash vercel_build.sh`.
- **Nome de variável ajustado pra reaproveitar o que já existia:** o Vercel já tinha `SUPABASE_URL`/`SUPABASE_KEY` configuradas (mesmo nome do `.env` do backend) de uma tentativa anterior — `vercel_build.sh`, `main.dart` e esta documentação ajustados para ler `SUPABASE_KEY` em vez do nome originalmente proposto (`SUPABASE_ANON_KEY`), evitando duplicar variável.
- **Troubleshooting do primeiro redeploy — "Failed to decode error response" no login:** mesmo com Build Command e variáveis aparentemente corretos (inclusive já escopadas para Production e Preview), o primeiro redeploy publicou um build com `SUPABASE_URL`/`SUPABASE_KEY` efetivamente vazios — diagnosticado baixando o `main.dart.js` publicado e conferindo que não havia nenhuma ocorrência de `supabase.co` nele (o `API_URL`, por outro lado, apareceu certinho, confirmando que o mecanismo de `--dart-define` via variável de ambiente funciona; só essas duas não tinham sido injetadas nesse build específico). Causa exata não identificada com certeza (suspeita de uma peculiaridade do painel do Vercel em não aplicar o valor de uma variável já existente ao build até ela ser reeditada/salva de novo) — **resolvido simplesmente reinserindo o mesmo valor nas mesmas variáveis e disparando novo Redeploy**, sem nenhuma mudança de código.
- **✅ Validado em produção (18/08/2026):** login, leitura de QR Code na Portaria e a tela do Painel de Aniversariantes do Dia todos funcionando dentro do Hub autenticado, publicado e testado pelo usuário no domínio real do Vercel (`paparazzi-gold-bar.vercel.app`).
- **Painel do dia sem nenhum aniversariante aparecendo — comportamento esperado, não é bug:** os 37 registros existentes em `aniversariantes` foram todos criados **antes** da migration de hoje — `horario_reserva`/`estimativa_convidados` ficaram `NULL` para todos eles (a migration só cria a coluna, não faz backfill retroativo a partir do Kommo, que exigiria uma consulta ativa por lead antigo — não tentado, fora do escopo de hoje). Além disso, o filtro da rota é por `data_reserva = hoje` — nenhum registro antigo necessariamente cai nessa data. A partir de agora, qualquer lead novo processado pelo webhook já grava os dois campos normalmente; o painel deve começar a mostrar dados assim que houver uma reserva real com `data_reserva` de hoje processada depois desta data.

#### Arquivos afetados

- `sql/migrations/20260817_01_add_horario_estimativa_aniversariantes.sql` (nova), `sql/schema/01_tables_aniversariantes.sql` (colunas refletidas)
- `backend/app/routes/webhooks.py` (persistência de horário/estimativa), `backend/app/routes/aniversariantes.py` (`GET /hoje`), `backend/app/routes/convidados.py` (rotas protegidas)
- `backend/app/services/auth_service.py` (novo), `backend/app/aplicar_migration.py` (novo, ferramenta administrativa)
- `backend/requirements.txt` (`psycopg2-binary` adicionado)
- `frontend/pubspec.yaml`/`pubspec.lock` (`supabase_flutter`), `frontend/lib/main.dart`
- `frontend/lib/views/staff_gate.dart`, `login_screen.dart`, `hub_screen.dart`, `painel_dia_screen.dart` (novos)
- `frontend/lib/services/api_service.dart`, `frontend/lib/models/aniversariante_model.dart`
- `frontend/lib/views/portaria_screen.dart` (timer de reset 3s → 7s)
- `vercel_build.sh` (novo, raiz do repo — build do Flutter Web pro Vercel)
- `CLAUDE.md` (nova seção 4.7, seção 7 e 7.1 atualizadas), `docs/visao_geral_paparazzi.md` (Passo 5/5.1, Modelagem de Dados), `docs/paparazzi_resumo_projeto.md` (Fase 1 e Fase 2)

## 3. Checklist de Entregas da Fase 1 (Meta: 24/07/2026)

### Automação de Flyer e Atendimento (Kommo + FastAPI)

- [x] Definição da arquitetura de composição de imagem e criação dos templates das molduras oficiais. **Atualizado (10/08/2026):** a arte final entregue é opaca (RGB), não o PNG "vazado" transparente do plano original — a moldura virou o próprio canvas do flyer, com foto/nome/cartão sobrepostos por cima em coordenadas proporcionais. 3 dos 4 templates entregues (`sexta_boteco`, `sabado_feijoada`, `domingo_churrasco`); `sabado_noite` fica para uma fase futura.
- [ ] Configuração do disparo do webhook no Salesbot do Kommo CRM.
- [x] Desenvolvimento do gerador de flyer em Python (Pillow) — recorte da foto, faixa com o nome do aniversariante, cartão de dia da semana/data/horário reais sobrepostos na arte, seleção automática de moldura pelo dia da semana, fonte com suporte a acentos (Playfair Display Bold).
- [x] Upload automático da foto do flyer gerado para o Supabase Storage.
- [ ] Devolução da imagem e do link da lista exclusiva (UUID v4) para a conversa do WhatsApp no Kommo CRM. **Parcial (10/08/2026):** backend já grava a URL do flyer no Custom Field "URL do Flyer" (`2069404`) via `kommo_service.atualizar_custom_fields_lead`; falta o ajuste manual do Salesbot (referenciar `{{lead.cf.2069404}}` no lugar do texto hardcoded do step 166) e a gravação do Custom Field "Link do Formulário" (`2069406`, aguardando o ajuste do domínio para `app-paparazzi.vercel.app`).
- [x] Leitura dos 5 Custom Fields obrigatórios (Data da reserva `2068460`, Horário `2068854`, Estimativa de convidados `2068456`, Nome do flyer `2068452`, Foto `2068458`) via consulta ativa (`GET` direto na API do Kommo, `kommo_service.buscar_custom_fields_lead`) — o webhook em si só sinaliza `lead_id`/`status_id`.
- [x] Processamento direto ao chegar na etapa "PROCESSANDO FLYER" (`status_id` `109983139`): geração do flyer + INSERT em `aniversariantes` em `finalizar_cadastro_aniversariante()`.
- [x] Etapa exclusiva "PROCESSANDO FLYER" (`109983139`) criada no pipeline do Kommo e Salesbot ajustado para só mover o Lead para lá com os 5 campos completos — backend alinhado (`KOMMO_TARGET_STATUS_ID`).
- [x] Download da foto a partir da URL montada do CDN do Kommo (`drive-g.kommo.com`), com `follow_redirects=True` tratando o `301 Moved Permanently` da CDN.
- [x] Validação ponta a ponta com um lead real: webhook → consulta ativa → montagem da URL do CDN → download da foto → Pillow → Supabase Storage → INSERT em `aniversariantes`, confirmada em 06/08/2026.
- [ ] *(Ideia de Fase 2)* Retomar o cálculo automático de "Data da reserva" a partir do Custom Field "Nome da semana" (`2068768`), reduzindo o número de perguntas ao cliente no Salesbot.

### Formulário do Convidado (Flutter Web)

- [x] Exibição dos dados e foto do aniversariante a partir do token da URL (`register_screen.dart`, prioriza `foto_perfil_url`, com fallback para `foto_url`).
- [x] Coleta dos dados do convidado (Nome, CPF com validação de dígito verificador, WhatsApp, Data de Nascimento), com máscaras e validação client-side.
- [x] Exibição da tela de confirmação com a geração do QR Code individual (UUID v4). **Atualizado (17/08/2026):** item estava marcado como pendente por desatualização do diário — a tela "Passaporte VIP" (`_buildPassaporteVip`) com `qr_flutter` já existe no código e foi validada nesta data (ver Registro [17/08/2026] abaixo): o backend gera um `qr_code_token` diferente a cada confirmação (`gen_random_uuid()` no Postgres), confirmado consultando registros reais em `convidados`.

### Validação na Portaria e Integração com ERP (Flutter Mobile/Web + FastAPI + Epoc ERP)

- [x] Endpoint backend para validação do QR Code (`POST /convidados/validar-qr`). **Atualizado (17/08/2026):** item estava marcado como pendente por desatualização do diário — a rota já existe em `convidados.py`, com os três estados (`LIBERADO`/`JA_UTILIZADO`/`INVALIDO`) e detecção de quando o CPF lido é o do próprio aniversariante da lista.
- [x] Interface simplificada no app da portaria para leitura de QR Code via câmera e busca por CPF/Nome. **Atualizado (17/08/2026):** `portaria_screen.dart` já implementa a leitura via `mobile_scanner` e o modal de busca manual por CPF (`GET /convidados/buscar-cpf/{cpf}`), incluindo card VIP com confete quando o CPF é do próprio aniversariante. **Atualizado de novo (18/08/2026):** deixou de ser acessível via `?modo=portaria` público — agora vive dentro do Hub administrativo pós-login (ver checklist nova abaixo).
- [x] Resposta visual instantânea na tela da portaria (Acesso Liberado 🟢 / Negado 🔴). **Atualizado (17/08/2026):** implementado com reset automático de 3s e toque na tela para voltar ao scanner. **Atualizado (18/08/2026):** tempo do reset automático aumentado de 3s para 7s — no teste real em campo, 3s sumia rápido demais pra dar tempo de ler nome/CPF na tela; toque na tela pra liberar leitura antes continua disponível.
- [ ] Agendamento em fila assíncrona para abertura de comanda na API do Epoc ERP vinculado ao CPF validado. **Sem acesso à API do Epoc até 18/08/2026** — item genuinamente não iniciado (nenhum código toca a tabela `comandas_temporarias` nem faz nenhuma chamada ao Epoc). Único item real pendente desta seção.

**Nota (17/08/2026):** até este registro, o diário e o `CLAUDE.md` descreviam o formulário do convidado e a portaria como parcialmente pendentes, mas uma auditoria do código-fonte mostrou que ambos já estavam implementados de ponta a ponta (provavelmente concluídos em uma sessão anterior sem o devido registro no diário). Ver Registro [17/08/2026] — Correção de Documentação e Validação com Lead Real para o detalhamento da divergência encontrada e da validação feita.

### Login de Funcionários e Painel de Aniversariantes do Dia (nova, 18/08/2026)

- [x] Login de funcionário via Supabase Auth (e-mail/senha), protegendo Portaria e painel do dia — ver Registro [18/08/2026] abaixo. **Validado em produção** (`paparazzi-gold-bar.vercel.app`) no mesmo dia.
- [x] `GET /aniversariantes/hoje` (staff-only): lista aniversariantes do dia com horário, estimativa e quantidade real confirmada. **Validado em produção** — tela carrega e responde corretamente; sem nenhum aniversariante ainda porque nenhum registro existente tem `data_reserva`/horário/estimativa preenchidos (todos anteriores à migration de hoje, ver Registro [18/08/2026]). Deve começar a popular com a próxima reserva real processada.
- [x] Persistência de `horario_reserva`/`estimativa_convidados` em `aniversariantes` (antes só usados no flyer e descartados).
- [ ] Tela de gestão de contas de funcionário dentro do app (hoje é só script administrativo manual) — catalogado como melhoria de Fase 1.5/2, ver `docs/paparazzi_resumo_projeto.md`.

## 4. Registro de Débitos Técnicos e Decisões de Arquitetura

- **Centralização de Configurações:** Mover variáveis de ambiente espalhadas pelas rotas para o módulo central de configurações (`backend/app/config.py`).
- **Tratamento de Indisponibilidade do ERP:** Garantir que, caso a API do Epoc ERP fique instável durante a operação de pico, o registro de entrada fique salvo no Supabase e a requisição de abertura de comanda seja executada assim que o serviço restabelecer.