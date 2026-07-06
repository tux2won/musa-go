from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import APP_ROOT, SOURCE_DIR


COVERAGE_ROUTES_PATH = APP_ROOT / "data" / "structured" / "coverage_routes.json"
ROUTE_ORDER = ["military_care", "public_support", "civilian_care", "private_insurance"]
CERTAINTY_LABELS = {
    "official": "공식 근거 있음",
    "conditional": "조건부 확인",
    "evidence_gap": "현재 근거 부족",
}
ACTIVITY_GUIDANCE = {
    "공동생활 중심": "환기·손위생·기침예절과 예방접종 이력을 먼저 확인하세요. 활동환경은 안내 내용만 바꾸며 PNPS에는 반영되지 않습니다.",
    "야외훈련 포함": "긴 옷·기피제·모기와 진드기 노출 회피수칙을 먼저 확인하세요. 활동환경은 안내 내용만 바꾸며 PNPS에는 반영되지 않습니다.",
    "공동생활·야외훈련 혼합": "공동생활 감염예방과 매개체 노출예방을 함께 확인하세요. 활동환경은 안내 내용만 바꾸며 PNPS에는 반영되지 않습니다.",
    "아직 잘 모르겠음": "배치 후 실제 생활·훈련환경에 맞춰 예방수칙을 다시 확인하세요. 현재 선택은 PNPS에 반영되지 않습니다.",
}


@dataclass(frozen=True)
class CoverageRoute:
    scenario: str
    route_type: str
    title: str
    eligibility_condition: str
    first_action: str
    documents_to_check: tuple[str, ...]
    cost_responsibility_status: str
    source_file: str
    source_locator: str
    effective_date: str
    certainty_status: str
    interpretation_warning: str

    @property
    def certainty_label(self) -> str:
        return CERTAINTY_LABELS[self.certainty_status]

    @property
    def source_path(self) -> Path | None:
        return SOURCE_DIR / Path(self.source_file) if self.source_file else None


@dataclass(frozen=True)
class CoverageScenario:
    scenario_id: str
    label: str
    summary: str
    urgent_first: bool
    checklist: tuple[str, ...]
    routes: tuple[CoverageRoute, ...]


class CoverageEngine:
    def __init__(self, path: Path = COVERAGE_ROUTES_PATH) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.version = payload["version"]
        self.interpretation = payload["interpretation"]
        self._scenarios: dict[str, CoverageScenario] = {}
        for scenario_id, item in payload["scenarios"].items():
            routes = tuple(
                CoverageRoute(
                    scenario=scenario_id,
                    documents_to_check=tuple(route["documents_to_check"]),
                    **{key: value for key, value in route.items() if key != "documents_to_check"},
                )
                for route in item["routes"]
            )
            self._scenarios[scenario_id] = CoverageScenario(
                scenario_id=scenario_id,
                label=item["label"],
                summary=item["summary"],
                urgent_first=bool(item["urgent_first"]),
                checklist=tuple(item["checklist"]),
                routes=tuple(sorted(routes, key=lambda route: ROUTE_ORDER.index(route.route_type))),
            )
        self._validate()

    @property
    def scenarios(self) -> dict[str, str]:
        return {key: value.label for key, value in self._scenarios.items()}

    def get(self, scenario_id: str) -> CoverageScenario:
        if scenario_id not in self._scenarios:
            raise ValueError(f"지원하지 않는 상황: {scenario_id}")
        return self._scenarios[scenario_id]

    def activity_guidance(self, activity: str) -> str:
        return ACTIVITY_GUIDANCE.get(activity, ACTIVITY_GUIDANCE["아직 잘 모르겠음"])

    def _validate(self) -> None:
        required_scenarios = {"prepare", "symptoms", "military_care", "civilian_needed", "already_paid"}
        if set(self._scenarios) != required_scenarios:
            raise ValueError("보장 시나리오 구성이 예상과 다릅니다.")
        for scenario in self._scenarios.values():
            if [route.route_type for route in scenario.routes] != ROUTE_ORDER:
                raise ValueError(f"보장경로 순서 오류: {scenario.scenario_id}")
            for route in scenario.routes:
                if route.certainty_status not in CERTAINTY_LABELS:
                    raise ValueError(f"알 수 없는 근거상태: {route.certainty_status}")
                if route.certainty_status == "evidence_gap":
                    if route.source_file:
                        raise ValueError("근거 부족 경로에 공식 출처 파일을 지정할 수 없습니다.")
                elif route.source_path is None or not route.source_path.exists():
                    raise FileNotFoundError(f"보장경로 근거파일 누락: {route.source_file}")
