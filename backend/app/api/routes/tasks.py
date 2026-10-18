from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.task import CodingTask
from app.models.user import User
from app.repositories.repository_repo import RepositoryRepository
from app.schemas.task import TaskCreate, TaskOut


router = APIRouter()


@router.post("", response_model=TaskOut)
def create(
    data: TaskCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not RepositoryRepository(db).get_owned(data.repository_id, user.id):
        raise HTTPException(404, "Repository not found")

    task = CodingTask(
        repository_id=data.repository_id,
        user_id=user.id,
        prompt=data.prompt.strip(),
    )
    try:
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=list[TaskOut])
def list_tasks(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(CodingTask)
            .where(CodingTask.user_id == user.id)
            .order_by(CodingTask.id.desc())
        )
    )
