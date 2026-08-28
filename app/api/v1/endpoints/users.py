from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, require_admin
from app.models.user import User, utcnow
from app.schemas.user import RoleUpdate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, user: CurrentUser, session: SessionDep) -> User:
    user.full_name = data.full_name
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: CurrentUser, session: SessionDep) -> None:
    user.is_active = False
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()


@router.get("/", response_model=list[UserRead])
async def list_users(_: AdminUser, session: SessionDep, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)) -> list[User]:
    result = await session.exec(select(User).offset(offset).limit(limit).order_by(User.created_at.desc()))
    return list(result.all())


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, _: AdminUser, session: SessionDep) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_role(user_id: UUID, data: RoleUpdate, _: AdminUser, session: SessionDep) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = data.role
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
