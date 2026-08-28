from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication credentials",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token, "access")
        user = await session.get(User, UUID(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise unauthorized
    if not user or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
