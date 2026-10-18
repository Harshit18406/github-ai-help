from __future__ import annotations

from pathlib import Path
import re
import shutil
from urllib.parse import urlparse

from git import Repo

from app.core.config import settings
from app.core.exceptions import RepositoryError


IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".next",
    ".turbo",
    "target",
}

TEXT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".java", ".kt", ".kts", ".go", ".rs", ".cpp", ".cc", ".cxx",
    ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".md", ".mdx", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".properties", ".sql", ".graphql", ".gql",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".xml", ".sh",
    ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".dockerfile",
}

TEXT_FILENAMES = {
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".env.sample",
    "dockerfile",
    "makefile",
    "procfile",
    "license",
    "license.txt",
    "readme",
}

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class GitService:
    def _safe_repo_name(self, name: str) -> str:
        cleaned = _SAFE_NAME.sub("-", name.strip()).strip(".-")
        if not cleaned or cleaned in {".", ".."}:
            raise RepositoryError("Invalid repository name")
        return cleaned[:120]

    def _validate_clone_url(self, clone_url: str) -> str:
        url = clone_url.strip()
        if url.startswith("git@"):
            if ":" not in url:
                raise RepositoryError("Invalid Git SSH URL")
            return url

        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http", "ssh", "git"} or not parsed.netloc:
            raise RepositoryError("Use a valid Git repository URL")
        return url

    def is_text_path(self, rel_path: str | Path) -> bool:
        path = Path(rel_path)
        return (
            path.suffix.lower() in TEXT_EXTENSIONS
            or path.name.lower() in TEXT_FILENAMES
        )

    def clone(self, clone_url: str, owner_id: int, name: str) -> tuple[str, str]:
        url = self._validate_clone_url(clone_url)
        safe_name = self._safe_repo_name(name)
        target = Path(settings.repo_storage_path) / str(owner_id) / safe_name
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            shutil.rmtree(target, ignore_errors=False)

        try:
            repo = Repo.clone_from(url, target)
        except Exception as exc:
            shutil.rmtree(target, ignore_errors=True)
            raise RepositoryError(f"Git clone failed: {exc}") from exc

        branch = repo.active_branch.name if not repo.head.is_detached else "main"
        return str(target), branch

    def list_files(self, path: str) -> list[str]:
        base = Path(path).resolve()
        if not base.exists():
            return []

        out: list[str] = []
        for candidate in base.rglob("*"):
            if len(out) >= settings.max_repository_files:
                break
            if not candidate.is_file():
                continue
            try:
                relative = candidate.relative_to(base)
            except ValueError:
                continue
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            out.append(relative.as_posix())
        return sorted(out)

    def read_file(self, repo_path: str, rel_path: str) -> str:
        base = Path(repo_path).resolve()
        candidate = (base / rel_path).resolve()
        if candidate != base and base not in candidate.parents:
            raise ValueError("Invalid path")
        if not candidate.is_file():
            raise OSError("File not found")
        if not self.is_text_path(candidate.name):
            raise ValueError("Unsupported file type")
        if candidate.stat().st_size > settings.max_file_size_bytes:
            raise ValueError("File is too large to preview or index")
        return candidate.read_text(encoding="utf-8", errors="replace")

    def create_branch(self, repo_path: str, branch: str) -> str:
        repo = Repo(repo_path)
        if branch in [head.name for head in repo.heads]:
            repo.git.checkout(branch)
        else:
            repo.git.checkout("-b", branch)
        return branch

    def diff(self, repo_path: str) -> str:
        return Repo(repo_path).git.diff()

    def status(self, repo_path: str) -> list[str]:
        repo = Repo(repo_path)
        paths = [item.a_path or item.b_path for item in repo.index.diff(None)]
        paths.extend(repo.untracked_files)
        return sorted({path for path in paths if path})

    def revert_worktree(self, repo_path: str) -> None:
        repo = Repo(repo_path)
        repo.git.reset("--hard", "HEAD")
        repo.git.clean("-fd")

    def remove_repository(self, repo_path: str) -> None:
        target = Path(repo_path).resolve()
        storage = Path(settings.repo_storage_path).resolve()
        if target != storage and storage not in target.parents:
            raise RepositoryError("Refusing to delete path outside repository storage")
        if target.exists():
            shutil.rmtree(target, ignore_errors=False)
