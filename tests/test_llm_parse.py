from reviva_shared.llm_classify import parse_llm_payload


def test_valid_json():
    hit = parse_llm_payload('{"root_cause":"bank_downtime","confidence":0.9,"reasoning":"timeout-ish"}')
    assert hit.root_cause == "bank_downtime"
    assert hit.rule_id == "llm"


def test_low_confidence_unknown():
    hit = parse_llm_payload('{"root_cause":"abandonment","confidence":0.2,"reasoning":"guess"}')
    assert hit.root_cause == "unknown"
    assert hit.rule_id == "llm_low_confidence"


def test_invalid_json():
    hit = parse_llm_payload("not json")
    assert hit.rule_id == "llm_fallback"
