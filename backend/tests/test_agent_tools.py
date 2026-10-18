from pathlib import Path

import pytest

from app.agents.tools import AgentTools


def test_create_file_edit(tmp_path: Path):
    tools = AgentTools(str(tmp_path))
    result = tools.apply_edit_to_content(
        path="src/new.py",
        current_content="",
        old_text=None,
        new_text="print('ok')\n",
        file_exists=False,
    )
    assert result == "print('ok')\n"


def test_replacement_requires_unique_text(tmp_path: Path):
    tools = AgentTools(str(tmp_path))
    with pytest.raises(ValueError, match="ambiguous"):
        tools.apply_edit_to_content(
            path="a.py",
            current_content="x = 1\nx = 1\n",
            old_text="x = 1",
            new_text="x = 2",
            file_exists=True,
        )


def test_path_traversal_is_blocked(tmp_path: Path):
    tools = AgentTools(str(tmp_path))
    with pytest.raises(ValueError, match="Invalid path"):
        tools.modify_file("../outside.py", "bad")
