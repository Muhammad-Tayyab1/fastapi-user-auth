import asyncio

import resend

from app.core.config import settings


async def send_otp_email(to: str, code: str, purpose: str) -> None:
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        return
    resend.api_key = api_key
    subject = "Verify your email" if purpose == "register" else "Reset your password"
    params = {"from": settings.email_from, "to": [to], "subject": subject,
              "html": f"<p>Your code: <strong>{code}</strong></p><p>Expires in {settings.otp_expire_min} minutes.</p>"}
    await asyncio.to_thread(resend.Emails.send, params)

