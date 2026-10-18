from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.exceptions import IndexingError
from app.db.session import get_db
from app.ml.indexer import CodeIndexer
from app.models.user import User
from app.repositories.repository_repo import RepositoryRepository


router = APIRouter()


@router.post("/{repo_id}/index")
def index_repo(
    repo_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    try:
        return {"chunks": CodeIndexer(db).index(repo)}
    except IndexingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{repo_id}")
def search(
    repo_id: int,
    q: str = Query(min_length=2),
    limit: int = Query(default=8, ge=1, le=20),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = RepositoryRepository(db).get_owned(repo_id, user.id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    return [
        {
            "score": round(float(score), 4),
            "path": chunk.path,
            "symbol": chunk.symbol,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
        }
        for score, chunk in CodeIndexer(db).search(repo_id, q, limit)
    ]
