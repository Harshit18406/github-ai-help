from pathlib import Path

from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryFile
from app.repositories.repository_repo import RepositoryRepository
from app.services.git_service import GitService


LANG = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
}


class RepositoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_repo = RepositoryRepository(db)
        self.git = GitService()

    def import_repo(self, user_id: int, clone_url: str, name: str | None):
        inferred = name or clone_url.rstrip("/").split("/")[-1].removesuffix(".git")
        local_path = ""
        try:
            local_path, branch = self.git.clone(clone_url, user_id, inferred)
            entity = Repository(
                owner_id=user_id,
                name=inferred,
                clone_url=clone_url.strip(),
                local_path=local_path,
                default_branch=branch,
            )
            self.db.add(entity)
            self.db.flush()

            for path in self.git.list_files(local_path):
                full = Path(local_path) / path
                try:
                    size = full.stat().st_size
                except OSError:
                    continue
                self.db.add(
                    RepositoryFile(
                        repository_id=entity.id,
                        path=path,
                        language=LANG.get(full.suffix.lower()),
                        size=size,
                    )
                )

            self.db.commit()
            self.db.refresh(entity)
            return entity
        except Exception:
            self.db.rollback()
            if local_path:
                try:
                    self.git.remove_repository(local_path)
                except Exception:
                    pass
            raise
