from __future__ import annotations

import os
from pathlib import Path
import subprocess

from app.core.config import settings
from app.services.dependency_service import DependencyService


class SandboxService:
    def __init__(self):
        self.dependencies = DependencyService()

    def run(self, repo_path: str, command: str) -> dict:
        repo = Path(repo_path).resolve()
        if not repo.exists():
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Repository path does not exist: {repo}",
                "kind": "infrastructure_error",
            }

        if settings.test_execution_mode.lower() == "disabled":
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test execution is disabled in this environment.",
                "kind": "execution_disabled",
            }

        info = self.dependencies.detect(str(repo))

        try:
            env = os.environ.copy()
            src_path = repo / "src"
            python_paths = [str(repo)]
            if src_path.exists():
                python_paths.insert(0, str(src_path))
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                python_paths.append(existing_pythonpath)
            env["PYTHONPATH"] = os.pathsep.join(python_paths)

            result = subprocess.run(
                command,
                cwd=repo,
                shell=True,
                capture_output=True,
                text=True,
                timeout=settings.sandbox_timeout_seconds,
                env=env,
            )

            combined = f"{result.stdout}\n{result.stderr}".lower()
            dependency_markers = (
                "modulenotfounderror",
                "no module named",
                "cannot find module",
                "command not found",
                "is not recognized as an internal or external command",
            )
            kind = "dependency_error" if any(marker in combined for marker in dependency_markers) else "test_failure"
            if result.returncode == 0:
                kind = "success"

            stderr = result.stderr
            if kind == "dependency_error" and info.manifests:
                stderr += (
                    "\n\nDependency environment is not prepared for this repository. "
                    f"Detected {info.ecosystem} manifest(s): {', '.join(info.manifests)}."
                )

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": stderr,
                "kind": kind,
            }

        except subprocess.TimeoutExpired as exc:
            return {
                "exit_code": -1,
                "stdout": exc.stdout or "",
                "stderr": (
                    f"Test command timed out after {settings.sandbox_timeout_seconds} seconds."
                ),
                "kind": "infrastructure_error",
            }
        except Exception as exc:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Local test execution failed: {exc}",
                "kind": "infrastructure_error",
            }
