from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_literacy_dashboard_symptom_and_private_insurance_flow():
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    assert not list(app.exception)

    app.selectbox[2].set_value("symptoms").run()
    assert not list(app.exception)
    assert any("즉시 진료가 먼저" in item.value for item in app.error)

    page_text = "\n".join(str(item.value) for item in app.markdown)
    assert "공식 근거 있음" in page_text
    assert "조건부 확인" in page_text
    assert "현재 근거 부족" in page_text

    private_prompt = next(button for button in app.button if "실손보험" in button.label)
    private_prompt.click().run()
    assert not list(app.exception)
    answer_text = "\n".join(str(item.value) for item in app.markdown)
    assert "특정 상품을 추천하거나 지급 여부를 단정할 수 없습니다" in answer_text
    assert "현행 보장을 판정할 수 있는 공식 약관이 아직 확보되지 않았습니다" in answer_text
