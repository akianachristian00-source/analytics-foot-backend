"""Envoi d'e-mails simples via SMTP (utilisé pour les codes OTP de retrait)."""
import smtplib
from email.mime.text import MIMEText
from app.config import settings


def send_otp_email(to: str, otp_code: str) -> None:
    msg = MIMEText(
        f"Votre code de validation pour le retrait de commission est : {otp_code}\n\n"
        f"Ce code est valable pour cette demande uniquement. Ne le partagez avec personne."
    )
    msg["Subject"] = "Code de validation — Retrait de commission"
    msg["From"] = settings.smtp_user
    msg["To"] = to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
