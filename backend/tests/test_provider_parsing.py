import pytest

from app.agents.providers import OpenRouterProvider
from app.core.exceptions import AIProviderError


def test_extract_json_accepts_fenced_payload():
    payload = OpenRouterProvider._extract_json(
        '```json\n{"edits":[{"path":"a.py","old_text":null,"new_text":"x=1"}]}\n```'
    )
    assert payload["edits"][0]["path"] == "a.py"


def test_extract_json_rejects_malformed_payload():
    with pytest.raises(AIProviderError):
        OpenRouterProvider._extract_json("not json")
