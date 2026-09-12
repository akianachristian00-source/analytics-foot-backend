"""
Passe automatiquement en 'expired' tout abonnement dont expires_at est
dépassé mais qui est encore marqué 'active'.
Sans ce job, un Pass VIP resterait actif indéfiniment après sa date de fin.
"""
from datetime import datetime
from app.database import supabase


def expire_outdated_subscriptions() -> int:
    result = (
        supabase.table("subscriptions")
        .update({"status": "expired"})
        .eq("status", "active")
        .lt("expires_at", datetime.utcnow().isoformat())
        .execute()
    )
    return len(result.data)
