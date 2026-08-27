from reviva_shared.rules import classify_rules


def test_known_reason_insufficient_funds():
    hit = classify_rules("insufficient_funds", None, None)
    assert hit is not None
    assert hit.root_cause == "insufficient_funds"
    assert hit.rule_id == "R_IF_REASON"


def test_gateway_maps_to_bank_downtime():
    hit = classify_rules("gateway_error", None, None)
    assert hit.root_cause == "bank_downtime"


def test_u28_in_description():
    hit = classify_rules(None, None, "Issuer U28 bank is down")
    assert hit.root_cause == "bank_downtime"


def test_abandon_text():
    hit = classify_rules(None, None, "checkout abandoned / user dropped")
    assert hit.root_cause == "abandonment"


def test_unknown_returns_none_for_llm():
    assert classify_rules(None, "ZX-99", "unclear gateway response code ZX-99") is None
