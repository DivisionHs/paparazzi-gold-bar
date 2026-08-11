# Paparazzi Gold Bar — Ecossistema de Portaria Expressa & Automação de Listas

## 1. Título e Descrição Geral

- **Nome:** Paparazzi Gold Bar — Ecossistema de Portaria Expressa & Automação de Listas.
- **Descrição:** Plataforma de tecnologia e automação operacional desenvolvida para o Paparazzi Gold Bar (Osasco/SP).  
  O sistema elimina filas na portaria, automatiza a criação de artes promocionais (flyers de aniversário), digitaliza a confirmação de presença dos convidados e integra a liberação da entrada com a abertura automática de comandas no ERP.

## 2. Guias e Documentação Completa

O documento deve orientar o leitor a consultar a pasta de documentação técnica e de produto (`docs/`):

- `docs/paparazzi_resumo_projeto.md`: Visão executiva do negócio, dores operacionais do bar, modelo comercial e escopo das Fases 1 (MVP) e 2 (Futuro).
- `docs/visao_geral_paparazzi.md`: Arquitetura de integração entre os sistemas (Kommo, FastAPI, Supabase, Flutter e Epoc ERP), modelo de dados e estratégia de resiliência offline.
- `docs/diario_projeto.md`: Linha do tempo do desenvolvimento, registro de alterações, arquivos modificados e checklist das entregas do MVP.

## 3. Tecnologias Utilizadas

Apresentação da stack de tecnologia adotada no ecossistema:

- **CRM & Bot de Atendimento:** Kommo CRM (Salesbot via WhatsApp).
- **Backend Central:** Python 3.11+, FastAPI e biblioteca Pillow (geração de imagem).
- **Banco de Dados & Storage:** Supabase (PostgreSQL e Buckets de Imagem).
- **Frontend Web Convidado:** Flutter Web (hospedado na Vercel).
- **Aplicativo de Portaria:** Flutter Mobile/Web.
- **Sistema de Caixa/PDV:** Epoc ERP (Integração via API REST).

## 4. Estrutura do Repositório

Uma visão simplificada da organização das pastas do projeto:

- `backend/`: Código-fonte da API em FastAPI, rotas de webhooks do Kommo, serviço de geração de flyers com Pillow, rotas da API de convidados e integração de fila com o Epoc ERP.
- `frontend/`: Aplicação em Flutter contendo a tela web de cadastro do convidado (`lib/views/register_screen.dart`) e o módulo de leitura e validação do QR Code para a portaria.
- `docs/`: Pasta concentradora de toda a documentação de produto, arquitetura e histórico do projeto.
- `CLAUDE.md`: Guia de instrução para assistentes de código e desenvolvedores que atuam no repositório.

## 5. Como Executar o Projeto Localmente

### Instruções para o Backend

- Entrar na pasta do backend ou raiz.
- Instalar as dependências do Python contidas em `requirements.txt`.
- Rodar o servidor de desenvolvimento utilizando o Uvicorn apontando para a aplicação FastAPI.

### Instruções para o Frontend

- Navegar até a pasta `frontend`.
- Baixar os pacotes e dependências do Flutter.
- Executar em ambiente local (navegador Chrome para a interface web ou emulador/dispositivo para a portaria).

## 6. Configuração de Variáveis de Ambiente

Lista das chaves obrigatórias que devem constar no arquivo de configuração local (`.env`):

- `SUPABASE_URL`: Endereço da instância do banco no Supabase.
- `SUPABASE_KEY`: Chave de serviço ou API key do Supabase.
- `KOMMO_SUBDOMAIN`: Subdomínio da conta do Kommo CRM.
- `KOMMO_API_TOKEN`: Token de acesso às APIs do Kommo CRM.
- `EPOC_API_URL`: Endereço da API de integração do Epoc ERP.
- `EPOC_API_TOKEN`: Credencial de autenticação do ERP.

## 7. Fechamento da Documentação Base

Com este passo, encerramos a estrutura textual de todos os 5 arquivos de documentação do repositório (`CLAUDE.md`, `visao_geral_paparazzi.md`, `paparazzi_resumo_projeto.md`, `diario_projeto.md` e `README.md`).  
A partir de agora, podemos focar nas regras de produto, telas ou jornadas operacionais!