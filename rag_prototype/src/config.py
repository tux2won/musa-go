from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = APP_ROOT.parent
SOURCE_DIR = WORKSPACE_ROOT / "RAG_document"
ANALYSIS_DIR = WORKSPACE_ROOT / "outputs" / "감염병_분석" / "processed"
ACTION_ANALYSIS_DIR = WORKSPACE_ROOT / "outputs" / "감염병_분석_Actionability_문서근거" / "processed"
DATA_DIR = APP_ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
STRUCTURED_DIR = DATA_DIR / "structured"
INDEX_DIR = APP_ROOT / "index"
EVAL_DIR = APP_ROOT / "evaluation"

MANIFEST_PATH = DATA_DIR / "manifest.csv"
DOCUMENTS_PATH = NORMALIZED_DIR / "documents.jsonl"
CHUNKS_PATH = NORMALIZED_DIR / "chunks.jsonl"
INDEX_PATH = INDEX_DIR / "hybrid_index.joblib"
ACTIONABILITY_PATH = STRUCTURED_DIR / "actionability_evidence.csv"

SHORTLIST = [
    "수두",
    "말라리아",
    "유행성이하선염",
    "백일해",
    "A형간염",
    "일본뇌염",
    "신증후군출혈열",
    "쯔쯔가무시증",
]

DISEASE_ALIASES = {
    "수두": ["수두", "대상포진", "VZV", "varicella"],
    "말라리아": ["말라리아", "삼일열", "원충", "malaria"],
    "유행성이하선염": ["유행성이하선염", "유행성 이하선염", "볼거리", "mumps"],
    "백일해": ["백일해", "pertussis"],
    "A형간염": ["A형간염", "A형 간염", "hepatitis A"],
    "일본뇌염": ["일본뇌염", "일본 뇌염", "Japanese encephalitis"],
    "신증후군출혈열": ["신증후군출혈열", "신증후군 출혈열", "한타바이러스", "HFRS"],
    "쯔쯔가무시증": ["쯔쯔가무시증", "쯔쯔가무시", "털진드기", "tsutsugamushi"],
}

INTENT_KEYWORDS = {
    "risk_explanation": ["왜", "위험", "순위", "NPS", "PNPS", "지역", "월"],
    "prevention": ["예방", "접종", "백신", "피하려면", "수칙"],
    "symptom_response": ["증상", "열", "발진", "아프", "진단", "치료", "언제 병원"],
    "military_care": ["의무실", "군병원", "부대", "장병", "보고", "후송", "외진", "민간위탁", "휴가"],
    "nhis": ["건강보험", "급여", "비급여", "본인부담", "진료비", "심평원"],
    "state_support": ["공무상", "국가부담", "요양비", "환급", "지원"],
    "card_insurance": ["나라사랑카드", "카드보험", "KB 나라사랑", "나라사랑 보험"],
    "private_insurance": ["실손", "실손보험", "민간보험", "보험금", "보험약관", "보험증권", "가입내역", "보험기간", "피보험자", "면책", "중복보장"],
    "source_check": ["출처", "근거", "원문", "조항", "페이지", "기준일"],
}

AUTHORITY_WEIGHT = {"A": 1.18, "B": 1.08, "C": 1.0, "D": 0.72}


def ensure_directories() -> None:
    for path in [DATA_DIR, NORMALIZED_DIR, STRUCTURED_DIR, INDEX_DIR, EVAL_DIR]:
        path.mkdir(parents=True, exist_ok=True)
