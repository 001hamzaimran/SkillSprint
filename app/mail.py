"""Minimal password-reset email delivery with no third-party dependency."""

import smtplib
from email.message import EmailMessage


def send_password_reset(settings, recipient, reset_url):
    """Send a reset link when SMTP is configured; return False otherwise."""
    if not settings.smtp_host or not settings.smtp_from_email:
        return False
    message = EmailMessage()
    message["Subject"] = "Reset your SkillSprint password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your SkillSprint account.\n\n"
        f"Open this one-time link within 30 minutes:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this message."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
    return True
