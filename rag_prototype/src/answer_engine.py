from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .retrieval import HybridRetriever, SearchResult, classify_intents, detect_diseases, tokenize


SYSTEM_PROMPT = """당신은 군 복무기 감염병 보장 네비게이터다.
제공된 정량 JSON과 검색 근거만 사용해 한국어로 답한다.
PNPS/NPS는 개인 발병확률, 임상 중증도, 보험 보장 가능성이 아니다.
질병명만으로 건강보험·나라사랑카드 보험 지급 여부를 단정하지 않는다.
특정 민간보험 상품을 추천하거나 가입을 유도하지 않는다.
과거·현행 미확인 약관은 현재 보장 근거로 사용하지 않는다.
진단하지 말고 증상이 있으면 부대 의무실 또는 의료기관 진료·보고를 안내한다.
근거가 부족하면 확인 불가라고 쓰고 확인할 기관·문서를 제시한다.
근거 문장 뒤에는 반드시 [S번호]를 붙인다.
답변 순서: 요약, 지금 할 행동, 진료·비용 확인 경로, 근거와 한계.
"""


@dataclass
class Answer:
    text: str
    sources: list[SearchResult]
    mode: str
    intents: list[str]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?다요함됨])\s+|\n+", text) if len(part.strip()) > 25]


def _best_sentence(result: SearchResult, query: str) -> str:
    query_tokens = set(tokenize(query))
    candidates = _sentences(result.chunk["text"])
    if not candidates:
        return result.chunk["text"][:260].strip()
    return max(candidates, key=lambda sentence: len(query_tokens.intersection(tokenize(sentence))))[:320]


def _local_compose(query: str, sources: list[SearchResult], quantitative: list[dict]) -> str:
    intents = classify_intents(query)
    disease_text = ", ".join(item["disease"] for item in quantitative[:3]) if quantitative else "선택 질환"
    lines = [f"**요약**  ", f"{disease_text} 관련 질문을 현재 공식 문서 범위에서 확인했습니다."]
    if "risk_explanation" in intents:
        lines += [
            "\n**점수 해석**  ",
            "NPS·PNPS는 개인 발병확률이나 중증도 점수가 아니라, 선택한 지역·월에서 어떤 질환 안내를 먼저 보여줄지 정하는 상대적 설명 우선순위입니다.",
        ]
    if "card_insurance" in intents:
        lines += [
            "\n**보장 판단**  ",
            "수집된 나라사랑카드 자료는 현행성이 확인되지 않은 과거 사고보험 자료이므로 감염병 진료비 보장을 단정할 수 없습니다. 카드 발급사·보험사의 현재 상품명, 적용기간, 사고 정의와 필요서류를 확인해야 합니다.",
        ]
    if "private_insurance" in intents:
        lines += [
            "\n**기존 보험 확인법**  ",
            "특정 상품을 추천하거나 지급 여부를 단정할 수 없습니다. 먼저 본인의 가입내역에서 보험기간·피보험자 상태·질병/상해 구분·입원/통원/검사·비급여 조건·면책 및 청구서류를 확인하고, 실제 진료비와 공공지원 내역을 보험사에 제시해 문의하세요.",
        ]
    if sources:
        lines.append("\n**근거에서 확인되는 행동**")
        for index, source in enumerate(sources[:4], start=1):
            lines.append(f"- {_best_sentence(source, query)} [S{index}]")
    elif "card_insurance" in intents or "private_insurance" in intents:
        lines += [
            "\n**현재 확보된 근거**  ",
            "현행 보장을 판정할 수 있는 공식 약관이 아직 확보되지 않았습니다. 가입을 새로 권하는 대신 기존 계약의 확인 항목과 문의 경로만 안내합니다.",
        ]
    if "military_care" in intents or "symptom_response" in intents:
        lines.append("- 증상이 있거나 노출이 의심되면 자가진단하지 말고 지체 없이 부대 의무실에 알리고 군 또는 민간 의료기관의 진료 지시를 따르세요.")
    lines += [
        "\n**한계**  ",
        "이 답변은 공식 문서 탐색을 돕는 안내이며 의료진·보험사·담당기관의 개별 판정을 대신하지 않습니다. NPS·PNPS는 상대적 설명 우선순위입니다.",
    ]
    return "\n".join(lines)


def _openai_compose(query: str, sources: list[SearchResult], quantitative: list[dict]) -> str:
    from openai import OpenAI

    evidence = "\n\n".join(
        f"[S{i}] {source.citation}\n{source.chunk['text'][:1800]}"
        for i, source in enumerate(sources, start=1)
    )
    prompt = f"질문: {query}\n\n정량 컨텍스트: {quantitative}\n\n검색 근거:\n{evidence}"
    client = OpenAI()
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        instructions=SYSTEM_PROMPT,
        input=prompt,
        max_output_tokens=900,
    )
    return response.output_text


def enforce_guardrails(text: str, query: str) -> str:
    unsafe_probability = re.search(r"(?:PNPS|NPS).{0,25}(?:확률|% 확률|걸릴 가능성)", text, re.I)
    probability_question = re.search(r"(?:PNPS|NPS).{0,30}(?:확률|%|감염|걸리|발병)", query, re.I)
    unsafe_coverage = re.search(r"(?:무조건|확실히|반드시).{0,20}(?:보장|지급|급여)", text)
    unsafe_recommendation = re.search(r"(?:이 보험|보험상품|실손보험).{0,20}(?:가입하세요|추천합니다|가입해야)", text)
    suffix = []
    if unsafe_probability or probability_question:
        suffix.append("NPS·PNPS는 개인 발병확률이 아니라 숏리스트 안의 상대적 설명 우선순위입니다.")
    if unsafe_coverage:
        suffix.append("질병명만으로 보험금 지급이나 건강보험 적용을 확정할 수 없습니다.")
    if unsafe_recommendation:
        suffix.append("이 서비스는 특정 보험상품을 추천하거나 가입을 중개하지 않습니다.")
    return text + ("\n\n**안전 보정**  \n" + " ".join(suffix) if suffix else "")


class AnswerEngine:
    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def answer(self, query: str, quantitative: list[dict] | None = None) -> Answer:
        quantitative = quantitative or []
        intents = classify_intents(query)
        explicit_diseases = detect_diseases(query)
        if explicit_diseases:
            diseases = explicit_diseases
        elif "military_care" in intents:
            diseases = []
        else:
            diseases = [item["disease"] for item in quantitative[:3]]
        include_historical = "source_check" in intents and "card_insurance" in intents
        pure_score_question = intents == ["risk_explanation"] and not explicit_diseases
        retrieval_query = query
        if "military_care" in intents and not explicit_diseases:
            retrieval_query += " 국방 환자관리 훈령 군의료기관 의무실 진료 보고 후송"
        sources = [] if pure_score_question else self.retriever.search(
                retrieval_query,
                top_k=6,
                diseases=diseases,
                intents=intents,
                include_historical=include_historical,
            )
        if os.getenv("OPENAI_API_KEY"):
            try:
                text = _openai_compose(query, sources, quantitative)
                mode = "OpenAI 근거 제한형 LLM"
            except Exception as exc:
                text = _local_compose(query, sources, quantitative)
                text += f"\n\nAPI 생성이 실패하여 로컬 근거형 답변으로 전환했습니다 ({type(exc).__name__})."
                mode = "로컬 근거형 대체모드"
        else:
            text = _local_compose(query, sources, quantitative)
            mode = "로컬 근거형 대체모드"
        return Answer(text=enforce_guardrails(text, query), sources=sources, mode=mode, intents=intents)
