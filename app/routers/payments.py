"""
Intégration SenePay.
- POST /payments/initiate : crée une demande de paiement côté SenePay et
  renvoie l'URL de redirection au frontend.
- POST /payments/webhook : reçoit la confirmation SenePay (signature à
  vérifier), marque le paiement 'success' -> déclenche le trigger SQL qui
  calcule automatiquement la commission d'affiliation (30%).

NB : les noms d'endpoints/champs SenePay ci-dessous sont à ajuster selon
leur documentation exacte (https://api.sene-pay.com/docs.html) — la
structure générale (créer un payin, recevoir un webhook signé) est fiable,
mais les noms de champs doivent être vérifiés avant mise en prod.
"""
import hmac
import hashlib
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_supabase
from app.deps import get_current_user
from app.config import settings
from app.schemas import PaymentInitResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentInitResponse)
async def initiate_payment(
    subscription_id: str,
    user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    sub = (
        supabase.table("subscriptions")
        .select("*")
        .eq("id", subscription_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not sub.data:
        raise HTTPException(status_code=404, detail="Abonnement introuvable")

    payment = (
        supabase.table("payments")
        .insert(
            {
                "user_id": user["id"],
                "subscription_id": subscription_id,
                "amount_fcfa": sub.data["price_fcfa"],
                "method": "senepay",
                "status": "pending",
            }
        )
        .execute()
    )
    payment_id = payment.data[0]["id"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.senepay_base_url}/payin",
            headers={
                "X-Api-Key": settings.senepay_api_key,
                "X-Api-Secret": settings.senepay_api_secret,
            },
            json={
                "amount": sub.data["price_fcfa"],
                "currency": "XOF",
                "reference": payment_id,
                "customer_phone": user["phone"],
            },
        )
        resp.raise_for_status()
        senepay_data = resp.json()

    supabase.table("payments").update(
        {"senepay_transaction_id": senepay_data.get("transaction_id")}
    ).eq("id", payment_id).execute()

    return PaymentInitResponse(
        payment_id=payment_id,
        senepay_payment_url=senepay_data.get("payment_url"),
    )


def _verify_signature(raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.senepay_webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def senepay_webhook(request: Request, supabase=Depends(get_supabase)):
    raw_body = await request.body()
    signature = request.headers.get("X-SenePay-Signature", "")

    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Signature webhook invalide")

    payload = await request.json()
    transaction_id = payload["transaction_id"]
    status_ = payload["status"]

    payment = (
        supabase.table("payments")
        .select("*")
        .eq("senepay_transaction_id", transaction_id)
        .single()
        .execute()
    )
    if not payment.data:
        raise HTTPException(status_code=404, detail="Paiement introuvable")

    new_status = "success" if status_ == "success" else "failed"

    supabase.table("payments").update(
        {"status": new_status, "paid_at": "now()"}
    ).eq("id", payment.data["id"]).execute()

    return {"received": True}
