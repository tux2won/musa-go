import pandas as pd

from src.config import ACTIONABILITY_PATH


def test_actionability_evidence_is_complete():
    frame = pd.read_csv(ACTIONABILITY_PATH, encoding="utf-8-sig")
    assert len(frame) == 40
    assert frame["evidence_quote"].fillna("").str.len().gt(0).all()
    assert set(frame["value"].unique()) <= {0, 1}
    assert frame[["disease", "dimension"]].duplicated().sum() == 0


def test_actionability_document_grounding_preserves_expected_scores():
    frame = pd.read_csv(ACTIONABILITY_PATH, encoding="utf-8-sig")
    scores = frame.groupby("disease")["value"].mean().to_dict()
    assert scores["일본뇌염"] == 1.0
    assert scores["신증후군출혈열"] == 1.0
    for disease in ["수두", "말라리아", "유행성이하선염", "백일해", "A형간염", "쯔쯔가무시증"]:
        assert scores[disease] == 0.8
