"""
Ferramenta administrativa: aplica um arquivo .sql de sql/migrations/ direto
no Postgres do Supabase, via conexão direta (SUPABASE_DB_URL) — não passa
pela API REST (PostgREST), que não expõe DDL.

sql/ continua sendo a fonte da verdade versionada do schema (ver CLAUDE.md
7.1): este script só remove a etapa manual de colar o SQL no dashboard,
não substitui a revisão/commit do arquivo antes de aplicar.

Uso (a partir da raiz do repositório, com .venv ativado):
    python -m backend.app.aplicar_migration sql/migrations/20260817_01_add_horario_estimativa_aniversariantes.sql
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python -m backend.app.aplicar_migration <caminho/para/migration.sql>")
        sys.exit(1)

    caminho_migration = sys.argv[1]

    with open(caminho_migration, "r", encoding="utf-8") as f:
        sql = f.read()

    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        print("SUPABASE_DB_URL não configurada no .env.")
        sys.exit(1)

    print(f"Aplicando {caminho_migration}...")
    conn = psycopg2.connect(db_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Migration aplicada e commitada com sucesso.")
    except Exception as erro:
        conn.rollback()
        print(f"Erro ao aplicar migration — rollback feito, nada foi alterado: {erro}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
