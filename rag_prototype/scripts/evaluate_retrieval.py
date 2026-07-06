from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import EVAL_DIR, SHORTLIST, ensure_directories
from src.retrieval import HybridRetriever


DISEASE_TEMPLATES = [
    ("{disease} 예방접종 대상과 접종 확인 방법은?", "prevention"),
    ("{disease} 감염을 피하기 위한 노출 예방수칙은?", "prevention"),
    ("{disease}의 주요 증상과 조기 진료가 필요한 시점은?", "symptom_response"),
    ("{disease}가 많이 발생하는 지역이나 계절은?", "risk_explanation"),
    ("군 복무 중 {disease}가 의심되면 어디에 보고하고 진료받나요?", "military_care"),
]

GENERIC_QUESTIONS = [
    ("장병이 아프면 부대에서 가장 먼저 어디에 알려야 하나요?", "military_care"),
    ("군병원 진료가 원칙인가요?", "military_care"),
    ("민간병원 진료가 가능한 경우는 언제인가요?", "military_care"),
    ("응급상황에서 민간의료기관을 이용할 수 있나요?", "military_care"),
    ("외진과 환자후송 절차는 어떻게 다른가요?", "military_care"),
    ("민간위탁진료 승인 절차를 알려주세요.", "military_care"),
    ("진료 목적 청원휴가는 어떤 절차로 확인하나요?", "military_care"),
    ("감염병 환자를 발견하면 군에서 어떤 신고를 하나요?", "military_care"),
    ("공무상요양비 신청 시 어떤 서류를 확인해야 하나요?", "state_support"),
    ("군 의료기관과 민간 의료기관의 역할은 무엇인가요?", "military_care"),
    ("건강보험 급여와 비급여는 어떻게 다른가요?", "nhis"),
    ("병원에서 낸 본인부담금이 맞는지 확인하려면?", "nhis"),
    ("진료비 확인 제도는 어디에 신청하나요?", "nhis"),
    ("요양급여비용과 본인부담금의 의미는?", "nhis"),
    ("민간병원 검사 비용이 건강보험 대상인지 어떻게 확인하나요?", "nhis"),
    ("나라사랑카드 보험이 감염병 진료비를 보장하나요?", "card_insurance"),
    ("KB 나라사랑카드 보험금을 받을 수 있나요?", "card_insurance"),
    ("과거 나라사랑카드 약관을 현재 보장으로 봐도 되나요?", "card_insurance"),
    ("카드보험 상품명과 적용기간을 어디서 확인하나요?", "card_insurance"),
    ("질병명만으로 나라사랑카드 보험 지급을 판단할 수 있나요?", "card_insurance"),
]


def build_questions() -> list[dict[str, str]]:
    rows = []
    number = 1
    for disease in SHORTLIST:
        for template, intent in DISEASE_TEMPLATES:
            rows.append(
                {
                    "question_id": f"Q{number:03d}",
                    "question": template.format(disease=disease),
                    "expected_disease": disease,
                    "expected_intent": intent,
                }
            )
            number += 1
    for question, intent in GENERIC_QUESTIONS:
        rows.append(
            {
                "question_id": f"Q{number:03d}",
                "question": question,
                "expected_disease": "",
                "expected_intent": intent,
            }
        )
        number += 1
    return rows


def main() -> None:
    ensure_directories()
    questions = build_questions()
    retriever = HybridRetriever.load()
    results = []
    latencies = []
    for row in questions:
        start = time.perf_counter()
        hits = retriever.search(row["question"], top_k=5, include_historical=False)
        latencies.append((time.perf_counter() - start) * 1000)
        disease_ok = not row["expected_disease"] or any(
            row["expected_disease"] in hit.chunk.get("disease_tags", []) for hit in hits
        )
        intent_ok = any(row["expected_intent"] in hit.chunk.get("intent_tags", []) for hit in hits)
        if row["expected_intent"] == "card_insurance" and not hits:
            intent_ok = True  # Correct safe-gap behavior until current official terms are secured.
        historical_violation = any(hit.chunk.get("effective_status") == "historical_unverified" for hit in hits)
        results.append(
            {
                **row,
                "disease_hit_at_5": int(disease_ok),
                "intent_hit_at_5": int(intent_ok),
                "recall_pass": int(disease_ok and intent_ok),
                "historical_violation": int(historical_violation),
                "top_titles": " | ".join(hit.chunk["title"] for hit in hits),
                "top_scores": " | ".join(f"{hit.score:.4f}" for hit in hits),
            }
        )
    with (EVAL_DIR / "gold_questions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(questions[0]))
        writer.writeheader()
        writer.writerows(questions)
    with (EVAL_DIR / "retrieval_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    metrics = {
        "question_count": len(results),
        "recall_at_5": sum(item["recall_pass"] for item in results) / len(results),
        "disease_hit_at_5": sum(item["disease_hit_at_5"] for item in results) / len(results),
        "intent_hit_at_5": sum(item["intent_hit_at_5"] for item in results) / len(results),
        "historical_filter_violations": sum(item["historical_violation"] for item in results),
        "mean_latency_ms": sum(latencies) / len(latencies),
        "p95_latency_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
        "method": "character n-gram TF-IDF + BM25 + disease/intent/authority/current-status reranking",
    }
    (EVAL_DIR / "retrieval_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    failed = [item for item in results if not item["recall_pass"]]
    print("failed=", len(failed))
    for item in failed[:10]:
        print(item["question_id"], item["question"], item["top_titles"])


if __name__ == "__main__":
    main()
