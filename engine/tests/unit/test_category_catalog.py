"""Unit tests for the canonical OWASP GenAI 2026 Category Catalog."""
import json
import re
from pathlib import Path
import pytest

from app.agents.planner.category_catalog import (
    get_category_catalog,
    get_category_definition,
    CategoryDefinition,
)

CANONICAL_MD_PATH = (
    Path(__file__).parent.parent.parent
    / "knowledge"
    / "owasp"
    / "OWASP-LLM-Top-10-2026.md"
)
KB_2026_DIR = (
    Path(__file__).parent.parent.parent
    / "app"
    / "kb"
    / "01_OWASP"
    / "2026"
)


def test_catalog_contains_all_ten_2026_categories_in_order():
    catalog = get_category_catalog()
    assert len(catalog) == 10

    expected = [
        ("LLM01", "LLM01:2026", "Prompt Injection"),
        ("LLM02", "LLM02:2026", "Sensitive Information Disclosure"),
        ("LLM03", "LLM03:2026", "Excessive Agency"),
        ("LLM04", "LLM04:2026", "Supply Chain"),
        ("LLM05", "LLM05:2026", "Data and Model Poisoning"),
        ("LLM06", "LLM06:2026", "Unbounded Consumption"),
        ("LLM07", "LLM07:2026", "Misinformation"),
        ("LLM08", "LLM08:2026", "Hidden Context Exposure"),
        ("LLM09", "LLM09:2026", "Vector and Embedding Weaknesses"),
        ("LLM10", "LLM10:2026", "Improper Output Handling"),
    ]

    for item, (exp_id, exp_code, exp_name) in zip(catalog, expected):
        assert item.id == exp_id
        assert item.code == exp_code
        assert item.name == exp_name


def test_catalog_consistency_with_canonical_markdown():
    assert CANONICAL_MD_PATH.exists(), f"Missing canonical doc: {CANONICAL_MD_PATH}"
    content = CANONICAL_MD_PATH.read_text(encoding="utf-8")

    # Verify table entries: e.g. "LLM07:2026              Misinformation"
    catalog = get_category_catalog()
    for cat in catalog:
        # Match pattern: LLMxx:2026 followed by whitespace and risk name
        pattern = rf"{re.escape(cat.code)}\s+{re.escape(cat.name)}"
        match = re.search(pattern, content)
        assert match is not None, f"Failed to find {cat.code} {cat.name} in {CANONICAL_MD_PATH.name}"


def test_catalog_consistency_with_kb_json():
    assert KB_2026_DIR.exists()
    catalog = get_category_catalog()

    for cat in catalog:
        json_file = KB_2026_DIR / f"{cat.id}.json"
        assert json_file.exists(), f"Missing KB JSON for {cat.id}"
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["id"] == cat.code
        assert data["name"].lower() == cat.name.lower()


def test_legacy_2025_aliases_resolve_to_canonical_2026():
    # LLM07:2025 / System Prompt Leakage maps to LLM08:2026 Hidden Context Exposure
    defn1 = get_category_definition("LLM07:2025")
    assert defn1 is not None
    assert defn1.id == "LLM08"
    assert defn1.name == "Hidden Context Exposure"

    defn2 = get_category_definition("System Prompt Leakage")
    assert defn2 is not None
    assert defn2.id == "LLM08"
    assert defn2.name == "Hidden Context Exposure"

    # LLM06:2025 maps to LLM03 Excessive Agency
    defn3 = get_category_definition("LLM06:2025")
    assert defn3 is not None
    assert defn3.id == "LLM03"
    assert defn3.name == "Excessive Agency"

    # LLM08:2025 maps to LLM09 Vector and Embedding Weaknesses
    defn4 = get_category_definition("LLM08:2025")
    assert defn4 is not None
    assert defn4.id == "LLM09"
    assert defn4.name == "Vector and Embedding Weaknesses"


@pytest.mark.parametrize("value", ["LLM08anything", "LLM08-foo", "LLM08:2026-extra", "LLM080"])
def test_category_resolver_rejects_noncanonical_prefixes(value):
    assert get_category_definition(value) is None


def test_implementation_status():
    catalog = get_category_catalog()
    implemented = [c.id for c in catalog if c.implementation_status == "implemented"]
    # LLM08 has a verified end-to-end prompt, execution, and evaluation pipeline
    assert "LLM08" in implemented
    # Others must be under_development until full pipeline and evidence oracles exist
    under_dev = [c.id for c in catalog if c.implementation_status == "under_development"]
    assert "LLM01" in under_dev
    assert "LLM03" in under_dev
    assert "LLM07" in under_dev
    assert "LLM09" in under_dev
    assert "LLM10" in under_dev

