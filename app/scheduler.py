"""
Planificateur intégré au serveur FastAPI : les jobs tournent en arrière-plan
tant que le serveur est démarré, sans dépendre d'un cron système externe.

- reconcile_pending_payments : toutes les 10 minutes (filet de sécurité webhook SenePay)
- expire_outdated_subscriptions : toutes les heures
- run_weekly_payout_batch : chaque dimanche à 00h05 (traitement des retraits affiliés)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.reconcile_payments import reconcile_pending_payments
from app.jobs.expire_subscriptions import expire_outdated_subscriptions
from app.jobs.weekly_payout import run_weekly_payout_batch

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    scheduler.add_job(
        reconcile_pending_payments,
        trigger="interval",
        minutes=10,
        id="reconcile_pending_payments",
    )
    scheduler.add_job(
        expire_outdated_subscriptions,
        trigger="interval",
        hours=1,
        id="expire_outdated_subscriptions",
    )
    scheduler.add_job(
        run_weekly_payout_batch,
        trigger=CronTrigger(day_of_week="sun", hour=0, minute=5),
        id="weekly_payout_batch",
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown()
