"""
Dépendances FastAPI réutilisables : extraction de l'utilisateur courant
à partir du token JWT Supabase, et contrôle d'accès par rôle.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_supabase
from app.schemas import UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase=Depends(get_supabase),
) -> dict:
    """Vérifie le token Supabase et retourne le profil complet de l'utilisateur."""
    token = credentials.credentials
    try:
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )

    profile = (
        supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profil introuvable")

    return profile.data


def require_role(*allowed_roles: UserRole):
    """Factory de dépendance : restreint l'accès à certains rôles (admin, affiliate...)."""

    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé pour ce rôle",
            )
        return user

    return checker
