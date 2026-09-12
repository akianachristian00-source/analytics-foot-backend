"""
Programme d'affiliation.
Flux de retrait (rappel des règles définies) :
  1. L'affilié demande un retrait (>= 5000 FCFA)
  2. Un code OTP est envoyé par e-mail -> POST /withdrawals/{id}/confirm-otp
  3. Chaque dimanche, un job planifié rassemble les demandes confirmées
  4. L'admin valide sur son dashboard -> POST /withdrawals/{id}/admin-approve
     -> déclenche le virement SenePay (payout)
"""
import secrets
import httpx
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_supabase
from app.deps import get_current_user, require_role
from app.schemas import (
    AffiliateStatsOut,
    WithdrawalRequest,
    WithdrawalOTPConfirm,
    WithdrawalOut,
    PayoutStatsOut,
    UserRole,
)
from app.config import settings
from app.utils.email import send_otp_email

router = APIRouter(prefix="/affiliates", tags=["affiliates"])

MAX_PAYOUTS_PER_DAY = 100
MAX_PAYOUT_AMOUNT_PER_DAY_FCFA = 50_000_000


def _next_sunday() -> date:
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7
    days_ahead = 7 if days_ahead == 0 else days_ahead
    return today + timedelta(days=days_ahead)


def _get_todays_payout_stats(supabase) -> PayoutStatsOut:
    start_of_day = datetime.combine(date.today(), datetime.min.time()).isoformat()
    today_completed = (
        supabase.table("affiliate_withdrawals")
        .select("amount_fcfa")
        .eq("status", "completed")
        .gte("processed_at", start_of_day)
        .execute()
    )
    count_today = len(today_completed.data)
    total_today = sum(w["amount_fcfa"] for w in today_completed.data)

    return PayoutStatsOut(
        count_today=count_today,
        total_amount_today_fcfa=total_today,
        remaining_count=max(0, MAX_PAYOUTS_PER_DAY - count_today),
        remaining_amount_fcfa=max(0, MAX_PAYOUT_AMOUNT_PER_DAY_FCFA - total_today),
    )


@router.get("/me/stats", response_model=AffiliateStatsOut)
async def get_affiliate_stats(
    user: dict = Depends(require_role(UserRole.affiliate)),
    supabase=Depends(get_supabase),
):
    referred = (
        supabase.table("profiles").select("id").eq("referred_by", user["id"]).execute()
    )
    paying = (
        supabase.table("affiliate_commissions")
        .select("referred_user_id")
        .eq("affiliate_id", user["id"])
        .execute()
    )
    return AffiliateStatsOut(
        referral_code=user["referral_code"],
        total_referred=len(referred.data),
        total_paying_referred=len({r["referred_user_id"] for r in paying.data}),
        commission_balance_fcfa=user["commission_balance_fcfa"],
    )


@router.get("/admin/payout-stats", response_model=PayoutStatsOut)
async def get_payout_stats(
    admin: dict = Depends(require_role(UserRole.admin)),
    supabase=Depends(get_supabase),
):
    return _get_todays_payout_stats(supabase)


@router.get("/admin/withdrawals", response_model=list[WithdrawalOut])
async def list_withdrawals_for_admin(
    status: str = "pending_admin",
    admin: dict = Depends(require_role(UserRole.admin)),
    supabase=Depends(get_supabase),
):
    result = (
        supabase.table("affiliate_withdrawals")
        .select("*")
        .eq("status", status)
        .order("requested_at")
        .execute()
    )
    return result.data


@router.post("/withdrawals", response_model=WithdrawalOut)
async def request_withdrawal(
    payload: WithdrawalRequest,
    user: dict = Depends(require_role(UserRole.affiliate)),
    supabase=Depends(get_supabase),
):
    if payload.amount_fcfa > user["commission_balance_fcfa"]:
        raise HTTPException(status_code=400, detail="Solde de commission insuffisant")
    if payload.amount_fcfa < settings.min_withdrawal_fcfa:
        raise HTTPException(
            status_code=400,
            detail=f"Le retrait minimum est de {settings.min_withdrawal_fcfa} FCFA",
        )

    otp_code = f"{secrets.randbelow(1000000):06d}"

    withdrawal = (
        supabase.table("affiliate_withdrawals")
        .insert(
            {
                "affiliate_id": user["id"],
                "amount_fcfa": payload.amount_fcfa,
                "mobile_money_number": payload.mobile_money_number,
                "otp_code": otp_code,
                "status": "pending_otp",
                "scheduled_for": _next_sunday().isoformat(),
            }
        )
        .execute()
    )

    send_otp_email(to=user["email"], otp_code=otp_code)

    return withdrawal.data[0]


@router.post("/withdrawals/{withdrawal_id}/confirm-otp", response_model=WithdrawalOut)
async def confirm_withdrawal_otp(
    withdrawal_id: str,
    payload: WithdrawalOTPConfirm,
    user: dict = Depends(require_role(UserRole.affiliate)),
    supabase=Depends(get_supabase),
):
    withdrawal = (
        supabase.table("affiliate_withdrawals")
        .select("*")
        .eq("id", withdrawal_id)
        .eq("affiliate_id", user["id"])
        .single()
        .execute()
    )
    if not withdrawal.data:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if withdrawal.data["otp_code"] != payload.otp_code:
        raise HTTPException(status_code=400, detail="Code OTP invalide")
