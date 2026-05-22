from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import config


def _build_message(to: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((config.SMTP_FROM_NAME, config.SMTP_FROM))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send(to: str, subject: str, body: str) -> None:
    msg = _build_message(to, subject, body)
    context = ssl.create_default_context()
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
        s.ehlo()
        s.starttls(context=context)
        s.ehlo()
        s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        s.send_message(msg)


def send_verification(to: str, link: str) -> None:
    subject = "Подтверждение почты - MIPT Prompts CTF"
    body = (
        "Здравствуйте!\n\n"
        "Чтобы завершить регистрацию на MIPT Prompts CTF, перейдите по ссылке:\n\n"
        f"{link}\n\n"
        f"Ссылка действует {config.EMAIL_TOKEN_TTL_HOURS} часов.\n"
        "Если вы не регистрировались, просто проигнорируйте это письмо.\n"
    )
    send(to, subject, body)
