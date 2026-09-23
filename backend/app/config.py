from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    KOMMO_SUBDOMAIN: str = ""
    KOMMO_API_TOKEN: str = ""
    # Token de longa duração gerado na integração privada do Kommo (usado nas
    # chamadas PATCH/GET da API v4, ex.: sincronização de campos do Lead).
    KOMMO_LONG_LIVED_TOKEN: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    # Token estático simples (não é sessão do Supabase Auth) que protege as
    # rotas administrativas temporárias de atendimento manual (ver
    # backend/app/routes/admin.py e CLAUDE.md, seção 4.9). Compartilhado com
    # a equipe que for operar a página de atendimento manual.
    ADMIN_MANUAL_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
