from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import time

from app.core.config import settings
from app.core.exceptions import AIProviderError


@dataclass
class ProposedEdit:
    path: str
    old_text: str | None
    new_text: str


class BaseLLMProvider(ABC):
    @abstractmethod
    def plan(self, task: str, context: list[dict]) -> str:
        ...

    @abstractmethod
    def propose_edits(
        self,
        task: str,
        context: list[dict],
        failure: str | None = None,
    ) -> list[ProposedEdit]:
        ...

    @abstractmethod
    def answer(self, question: str, context: list[dict]) -> str:
        ...


class DeterministicProvider(BaseLLMProvider):
    def plan(self, task: str, context: list[dict]) -> str:
        paths = ", ".join(sorted({item["path"] for item in context})[:8]) or "no indexed files"
        return (
            f"1. Inspect relevant files: {paths}.\n"
            f"2. Identify the smallest change satisfying: {task}.\n"
            "3. Add or update tests.\n"
            "4. Review diff.\n"
            "5. Run tests."
        )

    def propose_edits(
        self,
        task: str,
        context: list[dict],
        failure: str | None = None,
    ) -> list[ProposedEdit]:
        return []

    def answer(self, question: str, context: list[dict]) -> str:
        if not context:
            return "No indexed code matched the question. Index the repository first."
        summary = "\n".join(
            f"- {item['path']}:{item['start_line']}-{item['end_line']} ({item.get('symbol') or 'module'})"
            for item in context[:6]
        )
        return f"Relevant code for '{question}':\n{summary}"


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self):
        from openai import OpenAI

        if not settings.openrouter_api_key:
            raise AIProviderError("OPENROUTER_API_KEY is not configured")

        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=settings.llm_timeout_seconds,
        )
        self.model = settings.openrouter_model

    def _context_text(self, context: list[dict]) -> str:
        blocks = []
        for item in context:
            blocks.append(
                f"FILE: {item['path']} "
                f"LINES {item['start_line']}-{item['end_line']} "
                f"SYMBOL {item.get('symbol')}\n{item['content']}"
            )
        return "\n\n---\n\n".join(blocks)

    def _ask(self, prompt: str) -> str:
        last_error = "unknown provider error"

        for attempt in range(1, settings.llm_max_attempts + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )

                if not response.choices:
                    last_error = "provider returned no choices"
                else:
                    choice = response.choices[0]
                    content = choice.message.content
                    if content and content.strip():
                        return content.strip()
                    last_error = (
                        "provider returned an empty response "
                        f"(finish_reason={getattr(choice, 'finish_reason', None)})"
                    )
            except Exception as exc:
                last_error = str(exc)

            if attempt < settings.llm_max_attempts:
                time.sleep(min(0.75 * attempt, 2.0))

        raise AIProviderError(
            f"AI provider failed after {settings.llm_max_attempts} attempts: {last_error}"
        )

    @staticmethod
    def _extract_json(text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1:
            cleaned = cleaned[first_brace:last_brace + 1]

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                "The AI returned malformed edit data. Please retry the task."
            ) from exc

        if not isinstance(payload, dict):
            raise AIProviderError("The AI returned an invalid edit payload.")
        return payload

    def plan(self, task: str, context: list[dict]) -> str:
        return self._ask(
            "You are a senior software engineer. Produce a concise numbered implementation plan. "
            "Use only the supplied repository context. Mention likely files and testing strategy.\n\n"
            f"TASK:\n{task}\n\nCONTEXT:\n{self._context_text(context)}"
        )

    def propose_edits(
        self,
        task: str,
        context: list[dict],
        failure: str | None = None,
    ) -> list[ProposedEdit]:
        failure_text = f"\nPREVIOUS TEST FAILURE:\n{failure}\n" if failure else ""

        text = self._ask(
            "You are editing a real software repository.\n\n"
            "Return ONLY valid raw JSON. Do not use markdown fences or explanations.\n\n"
            "Return this structure:\n"
            '{"edits":[{"path":"relative/file.py","old_text":"exact existing text","new_text":"replacement text"}]}\n\n'
            "For a NEW file use old_text=null and put the complete new file in new_text.\n"
            "Rules:\n"
            "- For existing files old_text MUST exactly match supplied text.\n"
            "- Keep old_text small but unique.\n"
            "- Do not return entire existing files.\n"
            "- Make the smallest safe set of edits.\n"
            "- Multiple edits are allowed.\n"
            '- If no safe edit is possible, return {"edits":[]}.\n\n'
            f"TASK:\n{task}\n{failure_text}\nCONTEXT:\n{self._context_text(context)}"
        )

        payload = self._extract_json(text)
        edits = payload.get("edits", [])
        if not isinstance(edits, list):
            raise AIProviderError("The AI returned an invalid 'edits' field.")

        result: list[ProposedEdit] = []
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            path = edit.get("path")
            old_text = edit.get("old_text")
            new_text = edit.get("new_text")
            if not isinstance(path, str) or not path.strip():
                continue
            if old_text is not None and not isinstance(old_text, str):
                continue
            if not isinstance(new_text, str):
                continue
            result.append(
                ProposedEdit(
                    path=path.strip().replace("\\", "/"),
                    old_text=old_text,
                    new_text=new_text,
                )
            )
        return result

    def answer(self, question: str, context: list[dict]) -> str:
        return self._ask(
            "Answer the codebase question using only the supplied context. "
            "Be concise and focus on key control flow. Use at most 5 short bullets or paragraphs. "
            "Cite file paths and line ranges when useful. If context is insufficient, say so.\n\n"
            f"QUESTION:\n{question}\n\nCONTEXT:\n{self._context_text(context)}"
        )


def get_provider() -> BaseLLMProvider:
    if settings.openrouter_api_key:
        return OpenRouterProvider()
    return DeterministicProvider()
