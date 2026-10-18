from __future__ import annotations

import difflib

from sqlalchemy.orm import Session

from app.agents.providers import BaseLLMProvider, ProposedEdit, get_provider
from app.agents.tools import AgentTools
from app.core.config import settings
from app.ml.indexer import CodeIndexer
from app.models.agent import AgentRun, AgentStep, CodeChange, TestRun
from app.models.task import CodingTask
from app.services.git_service import GitService
from app.services.sandbox_service import SandboxService


class AgentOrchestrator:
    def __init__(
        self,
        db: Session,
        provider: BaseLLMProvider | None = None,
    ):
        self.db = db
        self.provider = provider or get_provider()
        self.sandbox = SandboxService()
        self.git = GitService()

    def _context(self, task: CodingTask, limit: int = 6) -> list[dict]:
        hits = CodeIndexer(self.db).search(task.repository_id, task.prompt, limit)
        return [
            {
                "path": chunk.path,
                "symbol": chunk.symbol,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            }
            for _, chunk in hits
        ]

    def _expanded_context(
        self,
        task: CodingTask,
        context: list[dict],
        max_files: int = 6,
    ) -> list[dict]:
        """Load complete, edit-worthy files instead of blindly trusting retrieval order.

        Retrieval can legitimately rank documentation above source files. For code edits,
        augment those hits with likely implementation/test files from the repository tree.
        """
        tools = AgentTools(task.repository.local_path)
        all_files = tools.list_files()
        prompt = task.prompt.lower()
        prompt_tokens = {
            token.strip(".,:;()[]{}'\\\"")
            for token in prompt.replace("/", " ").replace("-", " ").split()
            if len(token.strip(".,:;()[]{}'\\\"")) >= 3
        }

        def score(path: str) -> tuple[int, int, str]:
            low = path.lower()
            name = low.rsplit("/", 1)[-1]
            value = 0
            if low.startswith(("src/", "app/", "backend/", "frontend/")):
                value += 4
            if "test" in low:
                value += 5 if any(word in prompt for word in ("test", "route", "endpoint")) else 1
            if name in {"app.py", "routes.py", "views.py", "router.py", "urls.py", "main.py"}:
                value += 6
            if any(token in low for token in prompt_tokens):
                value += 3
            if low.startswith(("docs/", "doc/")):
                value -= 5
            if low.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java")):
                value += 2
            return (-value, len(path), path)

        paths: list[str] = []
        for item in sorted(
            context,
            key=lambda item: (
                item["path"].lower().startswith(("docs/", "doc/")),
                item["path"],
            ),
        ):
            path = item["path"]
            if path in all_files and path not in paths:
                paths.append(path)
            if len(paths) >= max_files:
                break

        for path in sorted(all_files, key=score):
            if path in paths:
                continue
            if score(path)[0] >= 0:
                continue
            paths.append(path)
            if len(paths) >= max_files:
                break

        expanded: list[dict] = []
        for path in paths:
            try:
                content = tools.read_file(path)
            except Exception:
                continue
            expanded.append(
                {
                    "path": path,
                    "symbol": None,
                    "start_line": 1,
                    "end_line": max(1, len(content.splitlines())),
                    "content": content,
                }
            )
        return expanded

    def _record_edits(
        self,
        run: AgentRun,
        task: CodingTask,
        edits: list[ProposedEdit],
    ) -> list[CodeChange]:
        """Validate/model edits and store one final CodeChange per file.

        Multiple model edits targeting the same file are applied in memory in order,
        so the database never stores overlapping partial changes for one path.
        Nothing is written to the repository before approval.
        """
        tools = AgentTools(task.repository.local_path)
        originals: dict[str, str] = {}
        working: dict[str, str] = {}
        existed: dict[str, bool] = {}
        errors: list[str] = []

        for edit in edits:
            path = edit.path
            try:
                if path not in working:
                    file_exists = tools.file_exists(path)
                    existed[path] = file_exists
                    original = tools.read_file(path) if file_exists else ""
                    originals[path] = original
                    working[path] = original

                working[path] = tools.apply_edit_to_content(
                    path=path,
                    current_content=working[path],
                    old_text=edit.old_text,
                    new_text=edit.new_text,
                    file_exists=existed[path] or bool(working[path]),
                )
                existed[path] = True
            except Exception as exc:
                errors.append(f"{path}: {exc}")

        if errors:
            raise ValueError("Invalid proposed edits: " + " | ".join(errors[:8]))

        created: list[CodeChange] = []
        for path, proposed in working.items():
            original = originals[path]
            if proposed == original:
                continue
            diff = "\n".join(
                difflib.unified_diff(
                    original.splitlines(),
                    proposed.splitlines(),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            change = CodeChange(
                run_id=run.id,
                file_path=path,
                original_content=original,
                proposed_content=proposed,
                diff=diff,
            )
            self.db.add(change)
            created.append(change)

        self.db.flush()
        return created

    def start(self, task: CodingTask) -> AgentRun:
        run = AgentRun(task_id=task.id, status="planning", iteration=0)
        self.db.add(run)
        self.db.flush()
        task.status = "planning"
        self.db.commit()
        self.db.refresh(run)

        try:
            retrieval_context = self._context(task, limit=6)

            if not retrieval_context:
                CodeIndexer(self.db).index(task.repository)
                retrieval_context = self._context(task, limit=6)

            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="retrieval",
                    detail=f"Selected {len(retrieval_context)} relevant code chunks",
                )
            )

            plan = self.provider.plan(task.prompt, retrieval_context)
            run.plan = plan
            run.status = "generating_patch"
            task.status = "generating_patch"
            self.db.add(AgentStep(run_id=run.id, kind="plan", detail=plan))
            self.db.commit()

            edit_context = self._expanded_context(
                task,
                retrieval_context,
                max_files=6,
            )
            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="context_expansion",
                    detail=f"Loaded {len(edit_context)} complete relevant files",
                )
            )

            recorded_changes: list[CodeChange] = []
            patch_error: str | None = None
            patch_attempts = min(max(settings.llm_max_attempts, 1), 3)

            for patch_attempt in range(1, patch_attempts + 1):
                try:
                    edits = self.provider.propose_edits(
                        task.prompt,
                        edit_context,
                        failure=patch_error,
                    )
                    if not edits:
                        patch_error = (
                            "No edits were returned. Re-check the repository structure and "
                            "produce the smallest safe change using only files present in context."
                        )
                        raise ValueError(patch_error)

                    recorded_changes = self._record_edits(run, task, edits)
                    if not recorded_changes:
                        patch_error = "The proposed edits produced no effective file changes."
                        raise ValueError(patch_error)

                    if patch_attempt > 1:
                        self.db.add(
                            AgentStep(
                                run_id=run.id,
                                kind="patch_retry_success",
                                detail=f"Generated a valid patch on attempt {patch_attempt}",
                            )
                        )
                    break
                except Exception as exc:
                    patch_error = str(exc)[:4000]
                    self.db.add(
                        AgentStep(
                            run_id=run.id,
                            kind="patch_retry",
                            detail=(
                                f"Patch attempt {patch_attempt}/{patch_attempts} failed: "
                                f"{patch_error}"
                            ),
                        )
                    )
                    self.db.commit()
                    if patch_attempt >= patch_attempts:
                        raise RuntimeError(
                            f"Could not generate a valid patch after {patch_attempts} attempts: "
                            f"{patch_error}"
                        ) from exc

            change_count = len(recorded_changes)

            if change_count:
                run.status = "awaiting_approval"
                task.status = "awaiting_approval"
                self.db.add(
                    AgentStep(
                        run_id=run.id,
                        kind="patch",
                        detail=f"Prepared {change_count} reviewable file change(s)",
                    )
                )
            else:
                run.status = "planned_no_changes"
                task.status = "planned_no_changes"
                self.db.add(
                    AgentStep(
                        run_id=run.id,
                        kind="no_changes",
                        detail=(
                            "The agent produced a plan but no safe file changes. "
                            "Try a more specific task or re-index the repository."
                        ),
                    )
                )

            self.db.commit()
            self.db.refresh(run)
            return run

        except Exception as exc:
            self.db.rollback()
            persisted = self.db.get(AgentRun, run.id)
            persisted_task = self.db.get(CodingTask, task.id)
            if persisted:
                persisted.status = "failed"
                self.db.add(
                    AgentStep(
                        run_id=persisted.id,
                        kind="error",
                        detail=str(exc)[:4000],
                    )
                )
            if persisted_task:
                persisted_task.status = "failed"
            self.db.commit()
            if persisted:
                self.db.refresh(persisted)
                return persisted
            raise

    def approve_and_execute(
        self,
        run: AgentRun,
        approved: bool,
        test_command: str = "pytest -q",
    ) -> AgentRun:
        if run.status != "awaiting_approval":
            return run

        if not approved:
            run.status = "rejected"
            run.task.status = "rejected"
            self.db.add(
                AgentStep(run_id=run.id, kind="approval", detail="Patch rejected by user")
            )
            self.db.commit()
            self.db.refresh(run)
            return run

        repo = run.task.repository
        branch = f"agent/task-{run.task_id}-run-{run.id}"
        tools = AgentTools(repo.local_path)

        try:
            self.git.create_branch(repo.local_path, branch)
        except Exception as exc:
            run.status = "failed"
            run.task.status = "failed"
            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="git_error",
                    detail=f"Could not create isolated agent branch: {exc}",
                )
            )
            self.db.commit()
            self.db.refresh(run)
            return run

        run.status = "applying"
        run.task.status = "applying"
        self.db.commit()

        try:
            for change in run.changes:
                change.approved = True
                tools.modify_file(change.file_path, change.proposed_content)
                change.applied = True

            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="apply",
                    detail=f"Applied {len(run.changes)} approved change(s) on {branch}",
                )
            )
            run.status = "testing"
            run.task.status = "testing"
            self.db.commit()
        except Exception as exc:
            run.status = "failed"
            run.task.status = "failed"
            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="apply_error",
                    detail=f"Could not apply approved changes: {exc}",
                )
            )
            self.db.commit()
            self.db.refresh(run)
            return run

        while run.iteration < settings.agent_max_iterations:
            result = self.sandbox.run(repo.local_path, test_command)
            self.db.add(
                TestRun(
                    run_id=run.id,
                    command=test_command,
                    exit_code=int(result.get("exit_code", -1)),
                    stdout=str(result.get("stdout", ""))[-20000:],
                    stderr=str(result.get("stderr", ""))[-20000:],
                )
            )
            run.iteration += 1
            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="test",
                    detail=(
                        f"Iteration {run.iteration}: tests exit code "
                        f"{result.get('exit_code', -1)}"
                    ),
                )
            )
            self.db.commit()

            if result.get("exit_code") == 0:
                run.status = "completed"
                run.task.status = "completed"
                self.db.commit()
                self.db.refresh(run)
                return run

            if result.get("kind") in {"dependency_error", "execution_disabled", "infrastructure_error"}:
                run.status = "tests_blocked"
                run.task.status = "tests_blocked"
                self.db.commit()
                self.db.refresh(run)
                return run

            if run.iteration >= settings.agent_max_iterations:
                break

            failure = (
                str(result.get("stdout", "")) + "\n" + str(result.get("stderr", ""))
            )[-12000:]

            try:
                retrieval_context = self._context(run.task, limit=6)
                edit_context = self._expanded_context(
                    run.task,
                    retrieval_context,
                    max_files=4,
                )
                edits = self.provider.propose_edits(
                    run.task.prompt,
                    edit_context,
                    failure=failure,
                )
            except Exception as exc:
                self.db.add(
                    AgentStep(
                        run_id=run.id,
                        kind="retry_error",
                        detail=f"Could not generate a repair patch: {exc}",
                    )
                )
                break

            if not edits:
                break

            retry_changes = self._record_edits(run, run.task, edits)
            retry_change_count = len(retry_changes)
            for change in retry_changes:
                tools.modify_file(change.file_path, change.proposed_content)
                change.approved = True
                change.applied = True

            self.db.add(
                AgentStep(
                    run_id=run.id,
                    kind="retry",
                    detail=f"Applied {retry_change_count} repair file change(s) after test failure",
                )
            )
            self.db.commit()

        run.status = "tests_failed"
        run.task.status = "tests_failed"
        self.db.commit()
        self.db.refresh(run)
        return run
