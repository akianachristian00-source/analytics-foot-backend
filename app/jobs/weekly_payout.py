"""
Job à planifier chaque dimanche.

Ce job ne fait PAS le virement lui-même : il rassemble les demandes prêtes
(OTP confirmé) et les rend visibles sur le dashboard admin pour validation
finale.

Exécution : `python -m app.jobs.weekly_payout`
"""
from app.database import supabase


def run_weekly_payout_batch() -> int:
    pending = (
        supabase.table("affiliate_withdrawals")
        .select("id")
        .eq("status", "pending_admin")
        .eq("otp_verified", True)
        .execute()
    )
    return len(pending.data)


if __name__ == "__main__":
    count = run_weekly_payout_batch()
    print(f"{count} demande(s) de retrait prête(s) pour validation admin.")
