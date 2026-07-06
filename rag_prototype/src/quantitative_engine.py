from __future__ import annotations

import pandas as pd

from .config import ACTION_ANALYSIS_DIR, ANALYSIS_DIR, SHORTLIST


class QuantitativeEngine:
    def __init__(self) -> None:
        preferred = ACTION_ANALYSIS_DIR if (ACTION_ANALYSIS_DIR / "nps_shortlist_2016_2023.csv").exists() else ANALYSIS_DIR
        self.data_dir = preferred
        self.nps = pd.read_csv(preferred / "nps_shortlist_2016_2023.csv", encoding="utf-8-sig")
        self.features = pd.read_csv(
            preferred / "region_month_features_2016_2023.csv", encoding="utf-8-sig"
        )
        self.nps["disease"] = pd.Categorical(self.nps["disease"], categories=SHORTLIST, ordered=True)

    @property
    def regions(self) -> list[str]:
        return sorted(self.features["region"].dropna().unique().tolist())

    def calculate(self, region: str, month: int) -> pd.DataFrame:
        if region not in self.regions:
            raise ValueError(f"지원하지 않는 지역: {region}")
        if month not in range(1, 13):
            raise ValueError("월은 1~12여야 합니다.")
        local = self.features.query("region == @region and month == @month")[
            ["disease", "rq", "monthly_share_region", "cases_domestic", "rate_per_100k"]
        ].copy()
        result = self.nps.merge(local, on="disease", how="left", validate="one_to_one")
        result["region_factor"] = result["rq"].fillna(0.0)
        result["month_factor"] = result["monthly_share_region"].fillna(0.0)
        result["pnps_raw"] = result["nps"] * result["region_factor"] * result["month_factor"]
        maximum = result["pnps_raw"].max()
        result["pnps_0_100"] = 100 * result["pnps_raw"] / maximum if maximum > 0 else 0.0
        result["personalized_rank"] = result["pnps_raw"].rank(method="min", ascending=False).astype(int)
        result["selected_region"] = region
        result["selected_month"] = month
        return result.sort_values(["personalized_rank", "disease"]).reset_index(drop=True)

    @staticmethod
    def reason(row: pd.Series) -> str:
        rq = float(row.get("region_factor", 0))
        month_share = float(row.get("month_factor", 0))
        if rq >= 1.5 and month_share >= 0.15:
            return "지역 집중도와 해당 월 집중도가 함께 높습니다."
        if rq >= 1.5:
            return "전국 평균보다 이 지역에 상대적으로 집중됩니다."
        if month_share >= 0.15:
            return "이 지역에서 해당 월 발생 비중이 비교적 큽니다."
        return "기본 우선순위와 지역·월 요인을 함께 반영한 결과입니다."

    @staticmethod
    def context(row: pd.Series) -> dict:
        return {
            "selected_region": row["selected_region"],
            "selected_month": int(row["selected_month"]),
            "disease": str(row["disease"]),
            "personalized_rank": int(row["personalized_rank"]),
            "pnps_0_100": round(float(row["pnps_0_100"]), 2),
            "nps": round(float(row["nps"]), 2),
            "rq": round(float(row.get("region_factor", 0)), 4),
            "monthly_share_region": round(float(row.get("month_factor", 0)), 4),
            "quantitative_scope": "2016~2023년 신고통계와 KOSIS 인구를 이용한 상대 우선순위",
            "disclaimer": "개인 발병확률·임상적 중증도·보험 보장 판정이 아님",
        }
