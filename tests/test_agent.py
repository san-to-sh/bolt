"""Tests for the Bolt audit agent."""

import json
import os
import pytest

from agent.state import merge_evidence

DEMO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "workpapers", "demo_cache")

WORKPAPER_REQUIRED_FIELDS = [
    "objective",
    "assertion",
    "control_id",
    "procedure_performed",
    "population_summary",
    "sample",
    "exceptions",
    "deviation_rate",
    "criteria_cited",
    "prior_year_reference",
    "preliminary_conclusion",
    "judgment_note",
    "recommended_disposition",
    "prepared_at",
]


def _load_cached_workpapers() -> list[tuple[str, dict]]:
    """Load all cached workpapers for parametrized testing."""
    results = []
    for filename in sorted(os.listdir(DEMO_CACHE_DIR)):
        if filename.endswith(".json"):
            with open(os.path.join(DEMO_CACHE_DIR, filename)) as f:
                wp = json.load(f)
            results.append((filename, wp))
    return results


CACHED_WORKPAPERS = _load_cached_workpapers()


@pytest.mark.parametrize("filename,wp", CACHED_WORKPAPERS, ids=[f[0] for f in CACHED_WORKPAPERS])
def test_workpaper_schema_complete(filename, wp):
    """Every workpaper must contain all required fields."""
    missing = [field for field in WORKPAPER_REQUIRED_FIELDS if field not in wp]
    assert not missing, f"{filename} missing fields: {missing}"


@pytest.mark.parametrize("filename,wp", CACHED_WORKPAPERS, ids=[f[0] for f in CACHED_WORKPAPERS])
def test_disposition_suffix(filename, wp):
    """recommended_disposition must end with '— Auditor judgment required'."""
    disposition = wp.get("recommended_disposition", "")
    assert disposition.endswith("— Auditor judgment required"), (
        f"{filename}: disposition '{disposition}' does not end with required suffix"
    )


@pytest.mark.parametrize("filename,wp", CACHED_WORKPAPERS, ids=[f[0] for f in CACHED_WORKPAPERS])
def test_no_final_opinion_in_conclusion(filename, wp):
    """preliminary_conclusion must not assert a final audit opinion."""
    conclusion = wp.get("preliminary_conclusion", "").lower()
    forbidden = ["control is effective", "financials are fairly stated", "we conclude"]
    for phrase in forbidden:
        assert phrase not in conclusion, (
            f"{filename}: preliminary_conclusion contains forbidden phrase '{phrase}'"
        )


@pytest.mark.parametrize("filename,wp", CACHED_WORKPAPERS, ids=[f[0] for f in CACHED_WORKPAPERS])
def test_exceptions_are_list(filename, wp):
    """exceptions must be a list."""
    assert isinstance(wp.get("exceptions"), list), f"{filename}: exceptions is not a list"


@pytest.mark.parametrize("filename,wp", CACHED_WORKPAPERS, ids=[f[0] for f in CACHED_WORKPAPERS])
def test_criteria_cited_nonempty(filename, wp):
    """Every workpaper must cite at least one criterion."""
    criteria = wp.get("criteria_cited", [])
    assert len(criteria) > 0, f"{filename}: no criteria cited"


def test_ctrl04_no_exception():
    """CTRL-04 must produce NO EXCEPTION disposition."""
    path = os.path.join(DEMO_CACHE_DIR, "CTRL-04.json")
    with open(path) as f:
        wp = json.load(f)
    assert "NO EXCEPTION" in wp["recommended_disposition"]
    assert len(wp["exceptions"]) == 0


def test_ctrl01_has_deviations():
    """CTRL-01 must surface the planted deviations."""
    path = os.path.join(DEMO_CACHE_DIR, "CTRL-01.json")
    with open(path) as f:
        wp = json.load(f)
    assert len(wp["exceptions"]) >= 2
    exceptions_text = " ".join(wp["exceptions"]).lower()
    assert "txn-003" in exceptions_text
    assert "txn-004" in exceptions_text


def test_merge_evidence_dedup():
    """merge_evidence should deduplicate list items."""
    e1 = {"population": ["item1", "item2"], "count": 5}
    e2 = {"population": ["item2", "item3"], "extra": "new"}
    merged = merge_evidence(e1, e2)
    assert merged["population"] == ["item1", "item2", "item3"]
    assert merged["count"] == 5
    assert merged["extra"] == "new"


def test_merge_evidence_nested():
    """merge_evidence should deep-merge nested dicts."""
    e1 = {"data": {"a": 1, "b": [1, 2]}}
    e2 = {"data": {"b": [2, 3], "c": 4}}
    merged = merge_evidence(e1, e2)
    assert merged["data"]["a"] == 1
    assert merged["data"]["b"] == [1, 2, 3]
    assert merged["data"]["c"] == 4
