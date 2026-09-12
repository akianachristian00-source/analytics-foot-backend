"""
Pronostics et combinés.
Point important : l'accès au contenu VIP est vérifié ICI (côté API),
pas seulement via RLS Supabase — la RLS seule ne sait pas si l'abonnement
de l'utilisateur est encore actif (cf. note dans le schéma SQL).
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_supabase
from app.deps import get_current_user
from app.schemas import PredictionOut, ComboPackCreateRequest, ComboPackOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


async def _user_has_active_subscription(user_id: str, supabase) -> bool:
    sub = (
        supabase.table("subscriptions")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "active")
        .gte("expires_at", datetime.utcnow().isoformat())
        .limit(1)
        .execute()
    )
    return len(sub.data) > 0


@router.get("/today", response_model=list[PredictionOut])
async def get_today_predictions(
    user: dict = Depends(get_current_user), supabase=Depends(get_supabase)
):
    has_vip = await _user_has_active_subscription(user["id"], supabase)

    query = supabase.table("predictions").select("*").eq("match_date", date.today().isoformat())
    if not has_vip:
        query = query.eq("is_vip", False)

    result = query.order("created_at").execute()
    return result.data


@router.get("/combos/{combo_type}", response_model=list[PredictionOut])
async def get_combos(
    combo_type: str,
    user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    has_vip = await _user_has_active_subscription(user["id"], supabase)
    if not has_vip:
        raise HTTPException(
            status_code=403,
            detail="Les combinés sont réservés aux abonnés Pass VIP",
        )

    result = (
        supabase.table("predictions")
        .select("*, combo_legs(*)")
        .eq("type", combo_type)
        .order("match_date", desc=True)
        .execute()
    )
    return result.data


@router.get("/history/transparency", response_model=list[PredictionOut])
async def get_transparency_history(supabase=Depends(get_supabase)):
    """Historique public des résultats (✅ GAGNÉ / ❌ PERDU) affiché sur la homepage."""
    result = (
        supabase.table("predictions")
        .select("*")
        .neq("result", "pending")
        .order("match_date", desc=True)
        .limit(20)
        .execute()
    )
    return result.data


@router.post("/combo-packs", response_model=ComboPackOut)
async def create_combo_pack(
    payload: ComboPackCreateRequest,
    user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    has_vip = await _user_has_active_subscription(user["id"], supabase)
    if not has_vip:
        raise HTTPException(status_code=403, detail="Réservé aux abonnés Pass VIP")

    pack = (
        supabase.table("user_combo_packs")
        .insert({"user_id": user["id"], "name": payload.name})
        .execute()
    )
    pack_id = pack.data[0]["id"]

    items = [{"pack_id": pack_id, "prediction_id": pid} for pid in payload.prediction_ids]
    supabase.table("user_combo_pack_items").insert(items).execute()

    return pack.data[0]
