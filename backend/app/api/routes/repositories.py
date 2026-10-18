from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.code_index import CodeChunk
from app.models.repository import Repository, RepositoryFile
from app.models.task import CodingTask
from app.models.user import User
from app.repositories.repository_repo import RepositoryRepository
from app.schemas.repository import FileContent, FileNode, RepositoryCreate, RepositoryOut
from app.services.git_service import GitService
from app.services.repository_service import RepositoryService


router = APIRouter()


@router.get("", response_model=list[RepositoryOut])
def list_repos(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return RepositoryRepository(db).list_for_user(user.id)


@router.get("/overview")
def overview(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repository_count = db.scalar(
        select(func.count(Repository.id)).where(Repository.owner_id == user.id)
    ) or 0
    file_count = db.scalar(
        select(func.count(RepositoryFile.id))
        .join(Repository, RepositoryFile.repository_id == Repository.id)
        .where(Repository.owner_id == user.id)
    ) or 0
    chunk_count = db.scalar(
        select(func.count(CodeChunk.id))
        .join(Repository, CodeChunk.repository_id == Repository.id)
        .where(Repository.owner_id == user.id)
    ) or 0
    task_count = db.scalar(
        select(func.count(CodingTask.id)).where(CodingTask.user_id == user.id)
    ) or 0
    pending_reviews = db.scalar(
        select(func.count(AgentRun.id))
        .join(CodingTask, AgentRun.task_id == CodingTask.id)
        .where(
            CodingTask.user_id == user.id,
            AgentRun.status == "awaiting_approval",
        )
    ) or 0

    return {
        "repositories": int(repository_count),
        "files": int(file_count),
        "chunks": int(chunk_count),
        "tasks": int(task_count),
        "pending_reviews": int(pending_reviews),
    }


@router.post("", response_model=RepositoryOut)
def import_repo(
    data: RepositoryCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        return RepositoryService(db).import_repo(
            user.id,
            data.clone_url,
            data.name,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Repository import failed: {exc}",
        ) from exc


@router.get("/{repo_id}/files", response_model=list[FileNode])
def files(
    repo_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    return [
        FileNode(path=path, name=path.rsplit("/", 1)[-1], type="file")
        for path in GitService().list_files(repo.local_path)
    ]


@router.get("/{repo_id}/file", response_model=FileContent)
def file(
    repo_id: int,
    path: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    try:
        content = GitService().read_file(repo.local_path, path)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return FileContent(path=path, content=content)


@router.delete("/{repo_id}")
def delete_repo(
    repo_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")

    local_path = repo.local_path
    try:
        db.delete(repo)
        db.commit()
        try:
            GitService().remove_repository(local_path)
        except Exception:
            pass
        return {"deleted": True}
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Could not delete repository: {exc}") from exc
