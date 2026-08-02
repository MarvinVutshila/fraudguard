# fraud_detection/application/services/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email via SMTP. Returns True on success, False on failure.
    """
    logger.info(f"📧 send_email called: to={to_email}, subject='{subject}'")

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("❌ SMTP credentials not configured. Email not sent.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        logger.debug(f"Connecting to SMTP {SMTP_HOST}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            logger.debug("Logging in...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            logger.debug("Sending message...")
            server.send_message(msg)

        logger.info(f"✅ Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP authentication failed: {e}. Check your email/password or app password.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending email: {e}")
        return False