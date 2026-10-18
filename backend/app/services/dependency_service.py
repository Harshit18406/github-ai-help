from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependencyInfo:
    ecosystem: str
    manifests: list[str]
    test_command: str | None


class DependencyService:
    """Detect a repository's dependency/build metadata without installing anything."""

    def detect(self, repo_path: str) -> DependencyInfo:
        repo = Path(repo_path)
        manifests: list[str] = []

        for name in (
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
        ):
            if (repo / name).exists():
                manifests.append(name)
        if manifests:
            return DependencyInfo("python", manifests, "pytest -q")

        if (repo / "package.json").exists():
            return DependencyInfo("node", ["package.json"], "npm test -- --runInBand")

        for name in ("pom.xml", "build.gradle", "build.gradle.kts"):
            if (repo / name).exists():
                manifests.append(name)
        if manifests:
            command = "mvn test" if "pom.xml" in manifests else "./gradlew test"
            return DependencyInfo("jvm", manifests, command)

        if (repo / "Cargo.toml").exists():
            return DependencyInfo("rust", ["Cargo.toml"], "cargo test")

        if (repo / "go.mod").exists():
            return DependencyInfo("go", ["go.mod"], "go test ./...")

        return DependencyInfo("unknown", [], None)
