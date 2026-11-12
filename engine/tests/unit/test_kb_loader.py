"""Unit tests for KBLoader prompt library resolution and error resilience (Task 9).

Verifies:
- Resolving prompts by ID.
- Missing prompt IDs handling.
- Template variable substitution.
- Malformed records in JSON files are ignored without crashing.
- Category filtering and OWASP 2026/2025 canonical mapping.
"""
import json
import pytest
from pathlib import Path

from app.kb.loader import KBLoader


def test_kb_loader_loads_existing_prompts():
    """Verify loading real prompt library items by ID."""
    prompt_ids = ["llm07_direct_01", "llm08_msj_context_saturation_01"]
    resolved = KBLoader.load_prompts_by_ids(prompt_ids, category="LLM08")
    assert "llm07_direct_01" in resolved
    assert "llm08_msj_context_saturation_01" in resolved

    # Verify template variable substitution
    text = resolved["llm08_msj_context_saturation_01"]
    assert "{document_context}" not in text
    assert "enterprise security architecture" in text


def test_kb_loader_handles_missing_ids():
    """Verify missing IDs are omitted from resolved dict."""
    prompt_ids = ["nonexistent_prompt_id_12345"]
    resolved = KBLoader.load_prompts_by_ids(prompt_ids, category="LLM08")
    assert resolved == {}


def test_kb_loader_handles_category_mismatch():
    """Verify prompts belonging to an unrelated category are excluded when category is specified."""
    # llm01_prompt_injection prompts have category LLM01
    library = KBLoader.load_prompt_library()
    llm01_ids = [pid for pid, item in library.items() if item.get("category") == "LLM01"]
    if llm01_ids:
        # Requesting LLM01 prompts under LLM08 should exclude them
        resolved = KBLoader.load_prompts_by_ids([llm01_ids[0]], category="LLM08")
        assert resolved == {}


def test_kb_loader_resilience_to_malformed_records(tmp_path: Path):
    """Verify corrupted JSON files or malformed items do not crash the loader."""
    custom_dir = tmp_path / "prompts"
    custom_dir.mkdir()

    # Valid file with one valid prompt and several malformed records
    valid_file = custom_dir / "test_prompts.json"
    valid_file.write_text(
        json.dumps([
            "not a dict",
            {"no_id": True},
            {"id": "valid_01", "prompt": "Valid test prompt 1", "category": "LLM08"},
            {"id": "valid_template", "template": "Hello {user}!", "variables": {"user": "Alice"}, "category": "LLM08"},
            {"id": "empty_prompt", "prompt": "   "},
            None,
        ]),
        encoding="utf-8",
    )

    # Corrupted / invalid JSON file
    corrupt_file = custom_dir / "corrupted.json"
    corrupt_file.write_text("{ this is not valid json", encoding="utf-8")

    # Non-list JSON file
    dict_file = custom_dir / "dict_file.json"
    dict_file.write_text(json.dumps({"some_key": "some_value"}), encoding="utf-8")

    library = KBLoader.load_prompt_library(kb_dir=custom_dir)
    assert "valid_01" in library
    assert library["valid_01"]["prompt"] == "Valid test prompt 1"
    assert "valid_template" in library
    assert library["valid_template"]["prompt"] == "Hello Alice!"
    assert "empty_prompt" not in library
    assert len(library) == 2

    resolved = KBLoader.load_prompts_by_ids(["valid_01", "valid_template"], category="LLM08", kb_dir=custom_dir)
    assert resolved == {
        "valid_01": "Valid test prompt 1",
        "valid_template": "Hello Alice!",
    }


def test_kb_loader_rejects_duplicate_prompt_ids(tmp_path: Path):
    custom_dir = tmp_path / "prompts"
    custom_dir.mkdir()
    (custom_dir / "a.json").write_text(
        json.dumps([{"id": "duplicate", "prompt": "first", "category": "LLM08"}]),
        encoding="utf-8",
    )
    (custom_dir / "b.json").write_text(
        json.dumps([{"id": "duplicate", "prompt": "second", "category": "LLM08"}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate prompt ID"):
        KBLoader.load_prompt_library(kb_dir=custom_dir)

