from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import IndexingError
from app.ml.chunker import chunk_file
from app.ml.embeddings import HashEmbeddingProvider, cosine
from app.models.code_index import CodeChunk
from app.models.repository import Repository
from app.services.git_service import GitService


class CodeIndexer:
    def __init__(self, db: Session):
        self.db = db
        self.git = GitService()
        self.embedder = HashEmbeddingProvider()

    def index(self, repo: Repository) -> int:
        try:
            self.db.execute(
                delete(CodeChunk).where(CodeChunk.repository_id == repo.id)
            )

            count = 0
            for rel in self.git.list_files(repo.local_path):
                if not self.git.is_text_path(rel):
                    continue

                try:
                    source = self.git.read_file(repo.local_path, rel)
                except (ValueError, OSError, UnicodeError):
                    continue

                for chunk in chunk_file(rel, source):
                    embedding = self.embedder.embed(chunk.content)
                    self.db.add(
                        CodeChunk(
                            repository_id=repo.id,
                            path=chunk.path,
                            language=chunk.language,
                            symbol=chunk.symbol,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                            content=chunk.content,
                            embedding=embedding,
                            metadata_json=chunk.metadata,
                        )
                    )
                    count += 1

            self.db.commit()
            return count
        except Exception as exc:
            self.db.rollback()
            raise IndexingError(f"Repository indexing failed: {exc}") from exc

    def search(self, repo_id: int, query: str, limit: int = 8):
        if limit < 1:
            return []

        query_embedding = self.embedder.embed(query)
        chunks = list(
            self.db.scalars(
                select(CodeChunk).where(CodeChunk.repository_id == repo_id)
            )
        )

        scored_chunks = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            score = float(cosine(query_embedding, chunk.embedding))
            scored_chunks.append((score, chunk))

        ranked = sorted(scored_chunks, key=lambda item: item[0], reverse=True)
        return ranked[: min(limit, 20)]
