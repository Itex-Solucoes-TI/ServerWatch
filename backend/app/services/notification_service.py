from sqlmodel import Session, select
from app.models.notification import AlertRule, NotificationChannel
from app.models.company_settings import CompanySettings
from app.models.health_check import HealthCheck, CheckResult
import httpx
import smtplib
from email.message import EmailMessage
from datetime import datetime


def evaluate_alerts(check: HealthCheck, result: CheckResult, session: Session):
    rules = session.exec(
        select(AlertRule).where(AlertRule.check_id == check.id, AlertRule.active == True)
    ).all()
    settings = session.exec(
        select(CompanySettings).where(CompanySettings.company_id == check.company_id)
    ).first()
    for rule in rules:
        if result.status != "OK":
            rule.consecutive_failures = (rule.consecutive_failures or 0) + 1
        else:
            rule.consecutive_failures = 0
            rule.last_notified_at = None
        if (rule.consecutive_failures or 0) >= rule.fail_threshold:
            channel = session.get(NotificationChannel, rule.channel_id)
            if channel and channel.active and not rule.last_notified_at:
                try:
                    send_notification(channel, check, result, settings)
                    rule.last_notified_at = datetime.utcnow()
                except Exception:
                    pass
        session.add(rule)
    session.commit()


def send_notification(channel: NotificationChannel, check: HealthCheck, result: CheckResult, settings: CompanySettings | None):
    msg = f"*[ServerWatch]* {check.name}\nStatus: {result.status}\n{result.message or ''}"
    if channel.channel_type == "WHATSAPP" and settings and settings.zapi_instance_id:
        _send_whatsapp_zapi(settings, channel.target, msg)
    elif channel.channel_type == "EMAIL" and settings and settings.smtp_host:
        _send_email_smtp(settings, channel.target, check.name, msg)
    elif channel.channel_type == "WEBHOOK":
        httpx.post(channel.target, json={"text": msg}, timeout=10)


def _send_whatsapp_zapi(settings: CompanySettings, phone: str, msg: str):
    url = f"https://api.z-api.io/instances/{settings.zapi_instance_id}/token/{settings.zapi_token}/send-text"
    headers = {"Client-Token": settings.zapi_client_token} if settings.zapi_client_token else {}
    httpx.post(url, json={"phone": phone, "message": msg}, headers=headers, timeout=10)


def _send_email_smtp(settings: CompanySettings, to: str, subject: str, body: str):
    email = EmailMessage()
    email["Subject"] = f"[ServerWatch] Alerta: {subject}"
    email["From"] = settings.smtp_from or settings.smtp_user or "serverwatch@local"
    email["To"] = to
    email.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
        if settings.smtp_tls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password or "")
        s.send_message(email)
