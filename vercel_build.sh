#!/bin/bash
# Script de build do Flutter Web pro Vercel.
#
# Existe porque o Build Command do painel do Vercel tem limite de 256
# caracteres, e o comando completo (clonar o Flutter + flutter build web
# com os --dart-define de API_URL/SUPABASE_URL/SUPABASE_ANON_KEY) passa
# disso. As variáveis abaixo (API_URL, SUPABASE_URL, SUPABASE_ANON_KEY)
# devem ser configuradas em Project Settings > Environment Variables no
# Vercel — não aqui no script, e não no Build Command.
#
# Build Command no Vercel (curto, cabe no limite): bash vercel_build.sh
# Root Directory: em branco (raiz do repositório)
# Output Directory: frontend/build/web

set -e

git clone https://github.com/flutter/flutter.git --depth 1 -b stable _flutter_sdk
export PATH="$PWD/_flutter_sdk/bin:$PATH"

cd frontend
flutter pub get
flutter build web \
  --dart-define=API_URL="$API_URL" \
  --dart-define=SUPABASE_URL="$SUPABASE_URL" \
  --dart-define=SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
