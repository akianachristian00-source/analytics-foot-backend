"""
Client Supabase côté serveur.
Utilise la clé service_role : contourne la RLS, donc à n'utiliser QUE côté
backend, jamais exposée au frontend.
"""
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
)


def get_supabase() -> Client:
    """Dependency FastAPI pour injecter le client Supabase dans les routes."""
    return supabase
