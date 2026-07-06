import pandas as pd

from src.config import ANALYSIS_DIR
from src.quantitative_engine import QuantitativeEngine


def test_pnps_regression_examples_match_original():
    engine = QuantitativeEngine()
    expected = pd.read_csv(ANALYSIS_DIR / "pnps_examples.csv", encoding="utf-8-sig")
    for (region, month), group in expected.groupby(["selected_region", "selected_month"]):
        actual = engine.calculate(region, int(month)).head(3)
        assert actual["disease"].astype(str).tolist() == group.sort_values("personalized_rank")["disease"].tolist()
        merged = group.merge(actual, on="disease", suffixes=("_expected", "_actual"))
        assert (merged["pnps_0_100_expected"] - merged["pnps_0_100_actual"]).abs().max() < 1e-9


def test_top_demo_scenarios():
    engine = QuantitativeEngine()
    assert engine.calculate("강원", 7).iloc[0]["disease"] == "말라리아"
    assert engine.calculate("전남", 11).iloc[0]["disease"] == "쯔쯔가무시증"
