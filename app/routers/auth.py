from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlmodel import select

from app.core.config import settings
from app.core.security import create_token, hash_password, verify_password
from app.deps import SessionDep
from app.models.otp import OTPPurpose
from app.models.user import User, utcnow
from app.schemas.auth import (ForgotPasswordRequest, LoginRequest, MessageResponse, RefreshRequest,
                              RegisterRequest, ResetPasswordRequest, TokenResponse, VerifyOTPRequest)
from app.services.email_service import send_otp_email
from app.services.otp_service import create_otp, validate_otp
from app.services.user_service import get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])
resend_attempts: dict[str, deque[datetime]] = defaultdict(deque)


def token_pair(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_token(str(user.id), "access"),
                         refresh_token=create_token(str(user.id), "refresh"))


def check_resend_limit(email: str) -> None:
    attempts = resend_attempts[email]
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    if len(attempts) >= settings.otp_max_resend_per_hour:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")
    attempts.append(datetime.now(UTC))


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, background: BackgroundTasks, session: SessionDep) -> MessageResponse:
    email = str(data.email).lower()
    user = await get_user_by_email(session, email)
    if user and user.is_verified:
        return MessageResponse(message="If registration is available, a verification code has been sent")
    if user:
        user.hashed_password = hash_password(data.password)
        user.full_name = data.full_name
        user.updated_at = utcnow()
    else:
        user = User(email=email, hashed_password=hash_password(data.password), full_name=data.full_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    otp = await create_otp(session, user.id, OTPPurpose.REGISTER)
    background.add_task(send_otp_email, user.email, otp.code, otp.purpose)
    return MessageResponse(message="If registration is available, a verification code has been sent")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: VerifyOTPRequest, session: SessionDep) -> TokenResponse:
    user = await get_user_by_email(session, str(data.email))
    if not user or not await validate_otp(session, user.id, OTPPurpose.REGISTER, data.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    user.is_verified = True
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()
    return token_pair(user)


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(data: ForgotPasswordRequest, background: BackgroundTasks, session: SessionDep) -> MessageResponse:
    email = str(data.email).lower()
    check_resend_limit(email)
    user = await get_user_by_email(session, email)
    if user and not user.is_verified:
        otp = await create_otp(session, user.id, OTPPurpose.REGISTER)
        background.add_task(send_otp_email, user.email, otp.code, otp.purpose)
    return MessageResponse(message="If the account is eligible, a code has been sent")


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep) -> TokenResponse:
    user = await get_user_by_email(session, str(data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email is not verified")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")
    return token_pair(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, session: SessionDep) -> TokenResponse:
    from app.core.security import decode_token
    try:
        payload = decode_token(data.refresh_token, "refresh")
        user = await session.get(User, payload["sub"])
    except (ValueError, TypeError):
        user = None
    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return token_pair(user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, background: BackgroundTasks, session: SessionDep) -> MessageResponse:
    email = str(data.email).lower()
    check_resend_limit(email)
    user = await get_user_by_email(session, email)
    if user and user.is_verified and user.is_active:
        otp = await create_otp(session, user.id, OTPPurpose.RESET_PASSWORD)
        background.add_task(send_otp_email, user.email, otp.code, otp.purpose)
    return MessageResponse(message="If the account exists, a reset code has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, session: SessionDep) -> MessageResponse:
    user = await get_user_by_email(session, str(data.email))
    if not user or not await validate_otp(session, user.id, OTPPurpose.RESET_PASSWORD, data.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    user.hashed_password = hash_password(data.new_password)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()
    return MessageResponse(message="Password reset successfully")

