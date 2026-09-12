"""
Configuration centrale de l'application.
Toutes les valeurs sensibles viennent des variables d'environnement (.env),
jamais codées en dur dans le code source.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str  # clé service_role, backend uniquement (jamais exposée au client)
    supabase_anon_key: str

    # SenePay
    senepay_api_key: str
    senepay_api_secret: str
    senepay_base_url: str = "https://api.sene-pay.com"
    senepay_webhook_secret: str  # pour vérifier la signature des webhooks

    # Auth / sécurité
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # E-mail (envoi des codes OTP de retrait)
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str

    # Grille tarifaire (FCFA) — Pass VIP
    price_daily: int = 1000
    price_weekly: int = 2500
    price_monthly: int = 5000

    # Programme d'affiliation
    commission_rate: float = 0.30  # 30% pour l'affilié, 70% conservés
    min_withdrawal_fcfa: int = 5000

    class Config:
        env_file = ".env"


settings = Settings()
