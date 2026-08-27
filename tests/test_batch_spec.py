from collections import Counter

from reviva_shared.batch_spec import build_specs


def test_n100_distribution():
    specs = build_specs(100)
    assert len(specs) == 100
    c = Counter(s["ground_truth"] for s in specs)
    assert c["insufficient_funds"] == 40
    assert c["bank_downtime"] == 25
    assert c["auth_failure"] == 20
    assert c["abandonment"] == 15


def test_high_value_row_exists():
    specs = build_specs(100)
    assert any(s["amount_paise"] > 1_000_000 for s in specs)


def test_some_ambiguous_for_llm_path():
    specs = build_specs(100)
    assert any(s["error_reason"] is None for s in specs)
