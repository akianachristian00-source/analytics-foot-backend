"""
Routes d'authentification.
L'inscription crée le compte Supabase Auth + le profil (avec rôle et,
si fourni, le lien vers le parrain via referral_code).
"""
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_supabase
from app.schemas import SignupRequest, LoginRequest, TokenResponse, ProfileOut
from app.deps import get_current_user
from pydantic import BaseModel
import secrets
import string

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_referral_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


class VerifyOtpRequest(BaseModel):
    email: str
    token: str


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, supabase=Depends(get_supabase)):
    auth_res = supabase.auth.sign_up(
        {"email": payload.email, "password": payload.password}
    )
    if auth_res.user is None:
        raise HTTPException(status_code=400, detail="Échec de la création du compte")

    user_id = auth_res.user.id

    referred_by = None
    if payload.referral_code:
        referrer = (
            supabase.table("profiles")
            .select("id")
            .eq("referral_code", payload.referral_code)
            .eq("role", "affiliate")
            .maybe_single()
            .execute()
        )
        if referrer.data:
            referred_by = referrer.data["id"]

    profile_data = {
        "id": user_id,
        "role": payload.role.value,
        "full_name": payload.full_name,
        "phone": payload.phone,
        "email": payload.email,
        "referred_by": referred_by,
    }
    if payload.role.value == "affiliate":
        profile_data["referral_code"] = _generate_referral_code()

    supabase.table("profiles").insert(profile_data).execute()

    # Si la confirmation par e-mail est activée sur Supabase, sign_up()
    # ne renvoie pas de session tant que l'utilisateur n'a pas confirmé
    # son adresse. On gère ce cas proprement au lieu de planter.
    if auth_res.session is None:
        raise HTTPException(
            status_code=202,
            detail="Compte créé avec succès. Veuillez confirmer votre e-mail avant de vous connecter.",
        )

    return TokenResponse(access_token=auth_res.session.access_token)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(payload: VerifyOtpRequest, supabase=Depends(get_supabase)):
    auth_res = supabase.auth.verify_otp(
        {"email": payload.email, "token": payload.token, "type": "signup"}
    )
    if auth_res.session is None:
        raise HTTPException(status_code=400, detail="Code invalide ou expiré")
    return TokenResponse(access_token=auth_res.session.access_token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, supabase=Depends(get_supabase)):
    auth_res = supabase.auth.sign_in_with_password(
        {"email": payload.email, "password": payload.password}
    )
    if auth_res.session is None:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    return TokenResponse(access_token=auth_res.session.access_token)


@router.get("/me", response_model=ProfileOut)
async def get_me(user: dict = Depends(get_current_user)):
    return user
