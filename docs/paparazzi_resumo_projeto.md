# Resumo Executivo do Projeto — Paparazzi Gold Bar

## 1. Visão Geral do Negócio

O Paparazzi Gold Bar é um gastrobar premium localizado em Osasco/SP, reconhecido por suas opções de gastronomia (feijoada, churrasco), shows ao vivo e, principalmente, por ser um polo de comemorações de aniversários e eventos.  
O objetivo deste projeto é implantar uma camada de tecnologia e automação para otimizar o fluxo de atendimento de reservas no CRM, automatizar a geração de materiais de divulgação (flyers), digitalizar o cadastro de convidados e transformar a portaria em um acesso expresso e automatizado.

## 2. Dores da Operação Atual (O Problema)

- **Gargalo e Filas Extensas na Portaria:** Filas de 20 minutos a 1 hora em horários de pico, geradas pela conferência verbal de listas de papel/WhatsApp e pela digitação manual do CPF de cada cliente para abertura de comanda no Epoc ERP.
- **Retrabalho e Tempo Gasto com Mídias:** Trabalho braçal da equipe para solicitar fotos no WhatsApp, formatar artes individualmente no ChatGPT via prompts e enviar aos aniversariantes.
- **Falta de Previsibilidade de Público:** O bar não possui dados antecipados sobre quantos convidados realmente virão para cada aniversário até que eles cheguem à porta.
- **Perda de Base de Clientes (Remarketing):** A ausência de um cadastro digitalizado dos convidados impede que o bar realize campanhas de retenção, fidelização e inteligência de vendas.

## 3. Escopo da Fase 1 / MVP (Entrega de Julho/2026)

A Fase 1 foca em eliminar o trabalho manual de criação de mídias, digitalizar a lista de convidados e acelerar o check-in na portaria:

- **Captura via CRM (Kommo):** Atendimento automatizado via WhatsApp para coletar a foto e os dados da reserva de aniversário.
- **Geração Automática do Flyer (FastAPI + Pillow):** Backend processa a foto enviada, aplica o layout e a moldura dourada oficial do bar e gera a arte em segundos.
- **Link de Lista Exclusiva:** O aniversariante recebe a imagem pronta e um link único seguro (UUID v4) para enviar aos seus convidados.
- **Formulário Web do Convidado (Flutter Web):** Os convidados acessam a página personalizada com a foto/nome do aniversariante e confirmam presença preenchendo Nome, CPF, WhatsApp e Data de Nascimento.
- **Geração de QR Code Individual:** Pós-cadastro, o convidado recebe na tela o seu passe de acesso individual com QR Code (UUID v4).
- **Validador da Portaria (App Flutter):** A equipe da recepção bipa o QR Code no celular/tablet em 2 segundos, liberando o acesso visualmente (Sinal Verde 🟢).
- **Abertura Assíncrona de Comanda (Epoc ERP):** A validação do QR Code dispara automaticamente a criação da comanda no sistema de caixa em segundo plano, sem travar a fila da entrada.

## 4. Visão de Futuro / Fase 2 (Roadmap de Expansão)

A Fase 2 foca em inteligência de dados, retenção de clientes e expansão da plataforma:

- **Hub do Aniversariante:** Painel web para o aniversariante acompanhar a quantidade de convidados confirmados na sua lista em tempo real.
- **Motor de Remarketing:** Automações no CRM para disparar convites de aniversário em massa e ofertas exclusivas para os convidados cadastrados na base no ano anterior.
- **BI e Analytics Operacional:** Dashboard mostrando gasto médio por lista, horários de pico de entrada, taxa de conversão de convidados e faixa etária do público.
- **Substituição Gradual do ERP:** Expansão de módulos proprietários de comanda e caixa para reduzir a dependência do ERP legado.

## 5. Modelo do Negócio e Indicadores de Sucesso (KPIs)

- **Tempo Médio de Entrada na Portaria:** Reduzir a validação por cliente de aproximadamente 2 minutos para menos de 5 segundos.
- **Tempo de Entrega do Flyer:** Reduzir de aproximadamente 15 minutos manuais para geração instantânea via código.
- **Taxa de Captura de Leads:** Atingir 100% dos convidados que entram no bar cadastrados com CPF e WhatsApp válidos no Supabase.
- **Modelo Comercial:** Contrato de consultoria e desenvolvimento contínuo (R$ 4.000/mês até dezembro/2026), com o objetivo de validar a operação do Paparazzi Gold Bar e transformar o produto em uma solução SaaS verticalizada para o mercado de eventos e gastronomia.