import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.otp import OTP, OTPPurpose


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_otp(session: AsyncSession, user_id: UUID, purpose: OTPPurpose) -> OTP:
    await session.exec(update(OTP).where(OTP.user_id == user_id, OTP.purpose == purpose.value,
                                         OTP.is_used.is_(False)).values(is_used=True))
    otp = OTP(user_id=user_id, code=generate_otp(), purpose=purpose.value,
              expires_at=datetime.now(UTC) + timedelta(minutes=settings.otp_expire_min))
    session.add(otp)
    await session.commit()
    await session.refresh(otp)
    return otp


async def validate_otp(session: AsyncSession, user_id: UUID, purpose: OTPPurpose, code: str) -> OTP | None:
    result = await session.exec(select(OTP).where(OTP.user_id == user_id, OTP.purpose == purpose.value,
                                                  OTP.is_used.is_(False)).order_by(OTP.created_at.desc()))
    otp = result.first()
    if not otp or otp.attempts >= 5:
        return None
    expires_at = otp.expires_at if otp.expires_at.tzinfo else otp.expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return None
    if not secrets.compare_digest(otp.code, code):
        otp.attempts += 1
        session.add(otp)
        await session.commit()
        return None
    otp.is_used = True
    session.add(otp)
    await session.commit()
    return otp
