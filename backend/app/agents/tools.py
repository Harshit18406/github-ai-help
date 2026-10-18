from pathlib import Path

from app.services.git_service import GitService


class AgentTools:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.git = GitService()

    def _safe_target(self, path: str) -> Path:
        base = Path(self.repo_path).resolve()
        target = (base / path).resolve()
        if target != base and base not in target.parents:
            raise ValueError("Invalid path")
        return target

    def list_files(self):
        return self.git.list_files(self.repo_path)

    def read_file(self, path: str) -> str:
        return self.git.read_file(self.repo_path, path)

    def file_exists(self, path: str) -> bool:
        return self._safe_target(path).is_file()

    def modify_file(self, path: str, content: str) -> None:
        target = self._safe_target(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def apply_edit_to_content(
        self,
        path: str,
        current_content: str,
        old_text: str | None,
        new_text: str,
        file_exists: bool,
    ) -> str:
        if old_text is None:
            if file_exists:
                raise ValueError(
                    f"Model requested a new file but {path} already exists"
                )
            return new_text

        if not file_exists:
            raise ValueError(
                f"Cannot replace text in missing file {path}; use old_text=null to create it"
            )

        occurrences = current_content.count(old_text)
        if occurrences == 0:
            raise ValueError(f"Target text not found in {path}")
        if occurrences > 1:
            raise ValueError(
                f"Target text is ambiguous in {path} ({occurrences} matches)"
            )

        return current_content.replace(old_text, new_text, 1)

    def git_diff(self):
        return self.git.diff(self.repo_path)
