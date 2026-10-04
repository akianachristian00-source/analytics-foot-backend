"""
Gestion des abonnements Pass VIP.
La création d'un abonnement se fait ici en statut 'pending' ; il ne devient
'active' qu'après confirmation du paiement via le webhook SenePay
(voir routers/payments.py).
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_supabase
from app.deps import get_current_user
from app.schemas import SubscribeRequest, SubscriptionOut, PlanType
from app.config import settings

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

PLAN_PRICES = {
    PlanType.daily: (settings.price_daily, timedelta(hours=24)),
    PlanType.weekly: (settings.price_weekly, timedelta(days=7)),
    PlanType.monthly: (settings.price_monthly, timedelta(days=30)),
}


@router.post("", response_model=SubscriptionOut)
async def create_subscription(
    payload: SubscribeRequest,
    user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    if payload.plan == PlanType.free:
        raise HTTPException(status_code=400, detail="Le plan Free ne nécessite pas d'abonnement")

    price, duration = PLAN_PRICES[payload.plan]
    now = datetime.utcnow()

    sub = (
        supabase.table("subscriptions")
        .insert(
            {
                "user_id": user["id"],
                "plan": payload.plan.value,
                "price_fcfa": price,
                "status": "active",
                "started_at": now.isoformat(),
                "expires_at": (now + duration).isoformat(),
            }
        )
        .execute()
    )
    return sub.data[0]


@router.get("/me/active", response_model=SubscriptionOut)
async def get_my_active_subscription(
    user: dict = Depends(get_current_user), supabase=Depends(get_supabase)
):
    sub = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user["id"])
        .eq("status", "active")
        .gte("expires_at", datetime.utcnow().isoformat())
        .order("expires_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if sub is None or not sub.data:
        raise HTTPException(status_code=404, detail="Aucun abonnement actif")
    return sub.data
