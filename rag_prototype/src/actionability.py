from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from .config import ACTIONABILITY_PATH, SOURCE_DIR, SHORTLIST, ensure_directories


DIMENSIONS = ["vaccination", "region_season", "exposure_prevention", "early_response", "navigation"]

# Rules are deliberately explicit and auditable. A value of 1 means the current
# official corpus contains a concrete user action for the dimension; it is not a
# clinical severity score or a statistical estimate.
RULES = {
    "수두": {
        "vaccination": (1, "수두_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (0, "수두_질병관리청_국가건강정보포털.md", "연중 발생"),
        "exposure_prevention": (1, "수두_질병관리청_국가건강정보포털.md", "예방"),
        "early_response": (1, "수두_질병관리청_국가건강정보포털.md", "치료"),
    },
    "말라리아": {
        "vaccination": (0, "말라리아_질병관리청_국가건강정보포털.md", "백신"),
        "region_season": (1, "2026년도 말라리아 관리지침(수정).pdf", "위험지역"),
        "exposure_prevention": (1, "말라리아_질병관리청_국가건강정보포털.md", "모기"),
        "early_response": (1, "말라리아_질병관리청_국가건강정보포털.md", "신속"),
    },
    "유행성이하선염": {
        "vaccination": (1, "유행성이하선염_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (0, "유행성이하선염_질병관리청_국가건강정보포털.md", "예방"),
        "exposure_prevention": (1, "유행성이하선염_질병관리청_국가건강정보포털.md", "전파"),
        "early_response": (1, "유행성이하선염_질병관리청_국가건강정보포털.md", "치료"),
    },
    "백일해": {
        "vaccination": (1, "백일해_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (0, "백일해_질병관리청_국가건강정보포털.md", "예방"),
        "exposure_prevention": (1, "백일해_질병관리청_국가건강정보포털.md", "호흡기"),
        "early_response": (1, "백일해_질병관리청_국가건강정보포털.md", "치료"),
    },
    "A형간염": {
        "vaccination": (1, "A형간염_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (0, "A형간염_질병관리청 국가건강정보포털.md", "예방 및 예방접종"),
        "exposure_prevention": (1, "A형간염_질병관리청 국가건강정보포털.md", "손 씻기"),
        "early_response": (1, "A형간염_질병관리청 국가건강정보포털.md", "의사의 진료"),
    },
    "일본뇌염": {
        "vaccination": (1, "일본뇌염_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (1, "전국 일본뇌염 주의보 발령(3.20.금).md", "주의보"),
        "exposure_prevention": (1, "일본뇌염_질병관리청_국가건강정보포털.md", "모기"),
        "early_response": (1, "일본뇌염_질병관리청_국가건강정보포털.md", "치료"),
    },
    "신증후군출혈열": {
        "vaccination": (1, "신증후군출혈열_예방접종도우미 _ 예방접종 정보 _ 예방접종 알아보기.md", "접종 대상"),
        "region_season": (1, "2026년도 진드기설치류 매개 감염병 관리지침-전자용.pdf", "신증후군출혈열"),
        "exposure_prevention": (1, "신증후군출혈열(한타바이러스감염증)_질병관리청_국가건강정보포털.md", "설치류"),
        "early_response": (1, "신증후군출혈열(한타바이러스감염증)_질병관리청_국가건강정보포털.md", "입원치료"),
    },
    "쯔쯔가무시증": {
        "vaccination": (0, "쯔쯔가무시증_질병관리청_국가건강정보포털.md", "백신"),
        "region_season": (1, "쯔쯔가무시증_질병관리청_국가건강정보포털.md", "9~11월"),
        "exposure_prevention": (1, "쯔쯔가무시증_질병관리청_국가건강정보포털.md", "긴 옷"),
        "early_response": (1, "쯔쯔가무시증_질병관리청_국가건강정보포털.md", "항생제"),
    },
}

NAVIGATION_SOURCE = "0702/행정규칙 _ 국방 환자관리 훈령.md"
NAVIGATION_ANCHOR = "제6조"


def _plain_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import fitz

        doc = fitz.open(path)
        return "\n".join(page.get_text("text") for page in doc)
    return path.read_text(encoding="utf-8", errors="replace")


def _excerpt(text: str, anchor: str, width: int = 260) -> tuple[str, str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    index = normalized.lower().find(anchor.lower())
    if index < 0:
        return "", "anchor_not_found"
    start = max(0, index - width // 3)
    end = min(len(normalized), index + 2 * width // 3)
    return normalized[start:end].strip(), "anchor_match"


def build_actionability_evidence(output_path: Path = ACTIONABILITY_PATH) -> pd.DataFrame:
    ensure_directories()
    rows: list[dict] = []
    for disease in SHORTLIST:
        rules = dict(RULES[disease])
        rules["navigation"] = (1, NAVIGATION_SOURCE, NAVIGATION_ANCHOR)
        for dimension in DIMENSIONS:
            value, relative_source, anchor = rules[dimension]
            source_path = SOURCE_DIR / Path(relative_source)
            text = _plain_text(source_path)
            quote, method = _excerpt(text, anchor)
            if value == 0 and dimension == "region_season":
                rationale = "공식 문서에 예방·대응 근거는 있으나 지역·월 입력과 직접 연결할 특정 위험지역·유행월 행동 기준은 채택하지 않음"
                method = "documented_rule_no_specific_trigger"
            elif value == 0 and dimension == "vaccination":
                rationale = "현재 국내 공식 안내에서 일반 사용자가 확인할 예방접종 행동축을 채택하지 않음"
            elif dimension == "vaccination":
                rationale = "공식 예방접종 기준 또는 접종대상 확인 행동이 존재함"
            elif dimension == "region_season":
                rationale = "공식 위험지역·주의보·계절 노출 정보가 지역·월 입력과 직접 연결됨"
            elif dimension == "exposure_prevention":
                rationale = "노출 회피·위생·매개체 차단 등 구체적인 예방행동이 제시됨"
            elif dimension == "early_response":
                rationale = "증상 인지 후 보고·진료·조기치료 행동이 제시됨"
            else:
                rationale = "군 장병의 진료·후송·민간의료 확인 경로가 현행 국방 훈령에 규정됨"
            rows.append(
                {
                    "disease": disease,
                    "dimension": dimension,
                    "value": int(value),
                    "rationale": rationale,
                    "source_file": relative_source.replace("/", "\\"),
                    "source_path": str(source_path),
                    "anchor": anchor,
                    "evidence_quote": quote,
                    "evidence_method": method,
                    "authority_level": "A",
                    "effective_status": "current",
                    "retrieved_at": "2026-07-02",
                }
            )
    frame = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    score = frame.pivot(index="disease", columns="dimension", values="value").reindex(SHORTLIST)
    score["actionability"] = score[DIMENSIONS].mean(axis=1)
    score.reset_index().to_csv(
        output_path.with_name("actionability_scores.csv"), index=False, encoding="utf-8-sig"
    )
    return frame


def main() -> None:
    evidence = build_actionability_evidence()
    print(evidence.groupby("disease")["value"].mean().sort_values(ascending=False))
    print("missing_quotes=", int((evidence["evidence_quote"] == "").sum()))


if __name__ == "__main__":
    main()
