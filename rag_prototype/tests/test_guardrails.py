from src.answer_engine import enforce_guardrails


def test_probability_guardrail():
    text = enforce_guardrails("PNPS가 100이면 걸릴 확률이 100%입니다.", "PNPS 의미")
    assert "개인 발병확률이 아니라" in text


def test_coverage_guardrail():
    text = enforce_guardrails("무조건 보험에서 보장됩니다.", "보험 보장")
    assert "질병명만으로" in text


def test_product_recommendation_guardrail():
    text = enforce_guardrails("이 보험상품을 가입하세요. 추천합니다.", "실손보험 추천")
    assert "특정 보험상품을 추천" in text
