from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.repository import Repository

class RepositoryRepository:
    def __init__(self, db: Session): self.db = db
    def list_for_user(self, user_id: int):
        return list(self.db.scalars(select(Repository).where(Repository.owner_id == user_id).order_by(Repository.id.desc())))
    def get_owned(self, repo_id: int, user_id: int):
        return self.db.scalar(select(Repository).where(Repository.id == repo_id, Repository.owner_id == user_id))
