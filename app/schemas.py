"""
Schémas Pydantic : définissent la forme des données échangées avec l'API.
Séparés des modèles de base de données pour ne jamais exposer plus que nécessaire.
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Enums (miroir des types Postgres) ----------

class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    affiliate = "affiliate"


class PlanType(str, Enum):
    free = "free"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class PredictionType(str, Enum):
    single = "single"
    combo_securite = "combo_securite"
    combo_performance = "combo_performance"
    combo_jackpot = "combo_jackpot"


class PredictionResult(str, Enum):
    pending = "pending"
    won = "won"
    lost = "lost"


# ---------- Auth ----------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: str
    role: UserRole = UserRole.user
    referral_code: Optional[str] = None  # code du parrain, si affilié


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Profil ----------

class ProfileOut(BaseModel):
    id: str
    role: UserRole
    full_name: Optional[str]
    phone: Optional[str]
    email: EmailStr
    referral_code: Optional[str]
    commission_balance_fcfa: int
    created_at: datetime


# ---------- Abonnements / Pass VIP ----------

class SubscribeRequest(BaseModel):
    plan: PlanType


class SubscriptionOut(BaseModel):
    id: str
    plan: PlanType
    price_fcfa: int
    status: str
    started_at: datetime
    expires_at: datetime


# ---------- Paiements SenePay ----------

class PaymentInitResponse(BaseModel):
    payment_id: str
    senepay_payment_url: str  # URL de redirection SenePay pour finaliser le paiement


class SenePayWebhookPayload(BaseModel):
    """Payload générique reçu du webhook SenePay (à ajuster selon leur doc exacte)."""
    transaction_id: str
    status: str  # success / failed
    amount: int
    metadata: dict = {}


# ---------- Pronostics ----------

class PredictionOut(BaseModel):
    id: str
    match_date: date
    league: str
    home_team: str
    away_team: str
    type: PredictionType
    is_vip: bool
    confidence_pct: Optional[float]
    analysis_summary: Optional[str]
    odds: Optional[float]
    result: PredictionResult


class ComboLegOut(BaseModel):
    home_team: str
    away_team: str
    pick: str
    odds: Optional[float]


# ---------- Packs combinés créés par l'utilisateur ----------

class ComboPackCreateRequest(BaseModel):
    name: Optional[str] = None
    prediction_ids: List[str] = Field(min_length=10)  # 10+ matchs, comme spécifié


class ComboPackOut(BaseModel):
    id: str
    name: Optional[str]
    combined_probability: Optional[float]
    created_at: datetime


# ---------- Affiliation ----------

class AffiliateStatsOut(BaseModel):
    referral_code: str
    total_referred: int
    total_paying_referred: int
    commission_balance_fcfa: int


class WithdrawalRequest(BaseModel):
    amount_fcfa: int = Field(ge=5000)
    mobile_money_number: str


class WithdrawalOTPConfirm(BaseModel):
    withdrawal_id: str
    otp_code: str


class WithdrawalOut(BaseModel):
    id: str
    amount_fcfa: int
    status: str
    requested_at: datetime
    scheduled_for: Optional[date]


class PayoutStatsOut(BaseModel):
    """Suivi journalier vs limites du contrat SenePay (100 payouts/jour, 50M FCFA/jour)."""
    count_today: int
    total_amount_today_fcfa: int
    max_count_per_day: int = 100
    max_amount_per_day_fcfa: int = 50_000_000
    remaining_count: int
    remaining_amount_fcfa: int
