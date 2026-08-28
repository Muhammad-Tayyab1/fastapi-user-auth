from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import select

from app.deps import CurrentUser, SessionDep
from app.models.note import Note
from app.models.user import utcnow
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


async def owned_note(note_id: UUID, user_id: UUID, session: SessionDep) -> Note:
    result = await session.exec(select(Note).where(Note.id == note_id, Note.user_id == user_id))
    note = result.first()
    if not note:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note


@router.post("/", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(data: NoteCreate, user: CurrentUser, session: SessionDep) -> Note:
    note = Note(user_id=user.id, **data.model_dump())
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


@router.get("/", response_model=list[NoteRead])
async def list_notes(user: CurrentUser, session: SessionDep, offset: int = Query(0, ge=0),
                     limit: int = Query(20, ge=1, le=100)) -> list[Note]:
    result = await session.exec(
        select(Note).where(Note.user_id == user.id).order_by(Note.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.all())


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(note_id: UUID, user: CurrentUser, session: SessionDep) -> Note:
    return await owned_note(note_id, user.id, session)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(note_id: UUID, data: NoteUpdate, user: CurrentUser, session: SessionDep) -> Note:
    note = await owned_note(note_id, user.id, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    note.updated_at = utcnow()
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: UUID, user: CurrentUser, session: SessionDep) -> Response:
    note = await owned_note(note_id, user.id, session)
    await session.delete(note)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
