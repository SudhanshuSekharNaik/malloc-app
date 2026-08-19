"""
Read access to stored memories.

Day 2 scope: list only. Edit/delete (the "remember/forget/update
commands" feature) is Day 4 - don't add mutation endpoints here yet.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Memory
from app.schemas import MemoryOut, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/{user_external_id}", response_model=list[MemoryOut])
def list_memories(user_external_id: str, db: Session = Depends(get_db)) -> list[Memory]:
    user = db.query(User).filter(User.external_id == user_external_id).first()
    if user is None:
        return []
    return (
        db.query(Memory)
        .filter(Memory.user_id == user.id, Memory.status == "active")
        .order_by(Memory.created_at.desc())
        .all()
    )


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    db: Session = Depends(get_db)
) -> Memory:
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    if payload.content is not None:
        memory.content = payload.content.strip()
    if payload.importance is not None:
        memory.importance = payload.importance
    if payload.status is not None:
        memory.status = payload.status

    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    db.delete(memory)
    db.commit()
    return None
