"""
Filet de sécurité si le webhook SenePay n'arrive jamais (panne réseau,
serveur temporairement indisponible, etc.).

Toutes les X minutes : reprend les paiements encore 'pending' depuis plus
de 10 minutes, et interroge directement l'API SenePay pour connaître leur
statut réel.
"""
from datetime import datetime, timedelta
import httpx
from app.database import supabase
from app.config import settings

STALE_AFTER_MINUTES = 10


async def reconcile_pending_payments() -> int:
    threshold = (datetime.utcnow() - timedelta(minutes=STALE_AFTER_MINUTES)).isoformat()

    stale = (
        supabase.table("payments")
        .select("*")
        .eq("status", "pending")
        .lt("created_at", threshold)
        .not_.is_("senepay_transaction_id", "null")
        .execute()
    )

    updated_count = 0
    async with httpx.AsyncClient() as client:
        for payment in stale.data:
            resp = await client.get(
                f"{settings.senepay_base_url}/payin/{payment['senepay_transaction_id']}",
                headers={
                    "X-Api-Key": settings.senepay_api_key,
                    "X-Api-Secret": settings.senepay_api_secret,
                },
            )
            if resp.status_code != 200:
                continue

            senepay_status = resp.json().get("status")
            if senepay_status in ("success", "failed"):
                supabase.table("payments").update(
                    {
                        "status": senepay_status,
                        "paid_at": "now()" if senepay_status == "success" else None,
                    }
                ).eq("id", payment["id"]).execute()
                updated_count += 1

    return updated_count
