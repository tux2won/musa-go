from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.answer_engine import AnswerEngine
from src.config import ACTIONABILITY_PATH, INDEX_PATH, MANIFEST_PATH
from src.coverage_engine import CoverageEngine, CoverageRoute
from src.quantitative_engine import QuantitativeEngine
from src.retrieval import HybridRetriever


st.set_page_config(
    page_title="복무온 | 보장 리터러시 네비게이터",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { --navy:#15375f; --blue:#2e6f9e; --orange:#ef8f60; --paper:#f7f9fc; --ink:#172033; --muted:#64748b; --green:#18745b; --amber:#9a5a00; }
.stApp { background:linear-gradient(180deg,#f4f7fb 0,#ffffff 390px); color:var(--ink); }
[data-testid="stSidebar"] { background:#102a49; }
[data-testid="stSidebar"] * { color:#f8fafc; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color:#0f172a !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill:#0f172a !important; }
.hero { padding:26px 30px; border-radius:22px; background:linear-gradient(125deg,#15375f,#2b638e); color:white; margin-bottom:18px; box-shadow:0 16px 38px rgba(21,55,95,.18); }
.hero .eyebrow { font-size:13px; letter-spacing:.12em; text-transform:uppercase; opacity:.78; }
.hero h1 { font-size:34px; line-height:1.22; margin:8px 0 8px; font-weight:800; }
.hero p { margin:0; max-width:900px; color:#dbeafe; line-height:1.65; }
.disease-card { min-height:260px; background:white; border:1px solid #e2e8f0; border-radius:18px; padding:20px; box-shadow:0 10px 28px rgba(15,23,42,.06); }
.rank { display:inline-flex; padding:5px 10px; border-radius:999px; background:#e8f1f8; color:#15375f; font-size:12px; font-weight:800; }
.score { font-size:34px; color:#e66f3d; font-weight:850; margin:14px 0 2px; }
.label { color:#64748b; font-size:12px; }
.disease-card h3 { margin:8px 0 4px; font-size:23px; color:#15375f; }
.reason { color:#334155; line-height:1.55; min-height:48px; }
.factor { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:14px; }
.factor div { background:#f8fafc; border-radius:12px; padding:10px; }
.factor b { display:block; color:#15375f; font-size:16px; }
.context-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; padding:10px; margin:8px 0 18px; border:1px solid #dbe5ef; border-radius:16px; background:white; }
.context-step { padding:12px 10px; border-radius:11px; background:#f7f9fc; color:#15375f; font-size:13px; font-weight:750; text-align:center; }
.route-card { min-height:285px; background:white; border:1px solid #e2e8f0; border-top:4px solid #2e6f9e; border-radius:16px; padding:17px; box-shadow:0 8px 22px rgba(15,23,42,.05); }
.route-card h3 { color:#15375f; margin:10px 0 7px; font-size:20px; }
.route-card p { color:#334155; line-height:1.55; font-size:14px; }
.route-cost { padding:9px 10px; background:#f8fafc; border-radius:10px; color:#475569; font-size:12px; margin-top:12px; }
.status { display:inline-block; border-radius:999px; padding:4px 9px; font-size:11px; font-weight:800; }
.status-official { background:#e8f7f1; color:#16624e; }
.status-conditional { background:#fff4df; color:#8a5100; }
.status-gap { background:#f1f5f9; color:#475569; }
.notice { border-left:4px solid #ef8f60; background:#fff7ed; padding:12px 14px; border-radius:8px; color:#7c2d12; }
.safe-note { border-left:4px solid #2e6f9e; background:#eff6ff; padding:12px 14px; border-radius:8px; color:#173d62; }
.source-box { border:1px solid #e2e8f0; border-radius:14px; padding:14px; background:white; margin:8px 0; }
.source-meta { color:#64748b; font-size:12px; }
.literacy-card { background:white; border:1px solid #e2e8f0; border-radius:14px; padding:15px; min-height:145px; }
.literacy-card b { color:#15375f; }
.stButton>button, .stDownloadButton>button { border-radius:12px; font-weight:700; }
div[data-testid="stMetric"] { background:white; border:1px solid #e2e8f0; padding:14px; border-radius:14px; }
div[data-testid="stMetricValue"] { font-size:28px; }
@media (max-width:900px) { .context-strip { grid-template-columns:1fr 1fr; } }
</style>
""",
    unsafe_allow_html=True,
)


STATUS_CLASS = {
    "official": "status-official",
    "conditional": "status-conditional",
    "evidence_gap": "status-gap",
}
ACTION_LABELS = {
    "vaccination": "예방접종 확인",
    "region_season": "지역·시기 확인",
    "exposure_prevention": "노출 예방수칙",
    "early_response": "증상 시 조기대응",
    "navigation": "군의료·비용 경로",
}
CIVILIAN_CONTEXT = {
    "군의료기관이 의뢰·승인함": "승인 주체, 담당 군병원, 승인 기간과 진료 범위를 기록해 두세요.",
    "응급상황으로 먼저 이용해야 함": "비용 확인보다 진료가 먼저입니다. 가능한 한 부대가 의료종합상황센터 신고·승인 절차를 진행하도록 하세요.",
    "개인이 선택해 이용하려 함": "개인 선택 진료는 위탁진료비 지원이 제한될 수 있습니다. 비응급이면 결제 전에 군의료 경로를 확인하세요.",
    "당시 경로를 잘 모르겠음": "영수증과 의무기록을 보관한 채 담당 군병원에 승인·사후심의 가능 여부를 확인하세요.",
}


@st.cache_resource
def load_system():
    return QuantitativeEngine(), HybridRetriever.load(INDEX_PATH), CoverageEngine()


@st.cache_data
def load_actionability() -> pd.DataFrame:
    return pd.read_csv(ACTIONABILITY_PATH, encoding="utf-8-sig")


def route_card(route: CoverageRoute) -> None:
    st.markdown(
        f"""
<article class="route-card">
  <span class="status {STATUS_CLASS[route.certainty_status]}">{route.certainty_label}</span>
  <h3>{route.title}</h3>
  <div class="label">첫 행동</div>
  <p>{route.first_action}</p>
  <div class="route-cost"><b>비용 판단</b><br>{route.cost_responsibility_status}</div>
</article>
""",
        unsafe_allow_html=True,
    )
    with st.expander("조건·서류·근거"):
        st.markdown(f"**적용 조건**  \n{route.eligibility_condition}")
        st.markdown("**확인할 서류**")
        for document in route.documents_to_check:
            st.markdown(f"- {document}")
        if route.source_file:
            st.markdown(f"**근거**  \n`{Path(route.source_file).name}` · {route.source_locator}")
            st.caption(f"기준일·시행정보: {route.effective_date}")
        else:
            st.markdown("**근거 상태**  \n현행 공식 보험약관을 아직 확보하지 못했습니다.")
        st.warning(route.interpretation_warning)


if not INDEX_PATH.exists():
    st.error("검색 인덱스가 없습니다. README의 재빌드 명령을 먼저 실행하세요.")
    st.stop()

quant_engine, retriever, coverage_engine = load_system()
answer_engine = AnswerEngine(retriever)
action_evidence = load_actionability()

with st.sidebar:
    st.markdown("## 철수의 복무환경")
    default_region = "강원" if "강원" in quant_engine.regions else quant_engine.regions[0]
    region = st.selectbox("입영·복무 지역", quant_engine.regions, index=quant_engine.regions.index(default_region))
    month = st.select_slider("입영·복무 월", options=list(range(1, 13)), value=7, format_func=lambda value: f"{value}월")
    activity = st.selectbox(
        "주 활동환경",
        ["공동생활·야외훈련 혼합", "공동생활 중심", "야외훈련 포함", "아직 잘 모르겠음"],
    )
    st.markdown("---")
    st.markdown("## 지금 어떤 상황인가요?")
    scenario_id = st.selectbox(
        "현재 상황",
        list(coverage_engine.scenarios),
        format_func=lambda value: coverage_engine.scenarios[value],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("**맞춤의 의미**")
    st.caption("지역·월은 감염병 안내순위를, 현재 상황은 보장 확인경로를 바꿉니다. 개인 발병확률이나 보험금 지급 가능성을 계산하지 않습니다.")
    mode_label = "OpenAI LLM" if __import__("os").getenv("OPENAI_API_KEY") else "로컬 근거형"
    st.caption(f"답변 모드: {mode_label}")

ranking = quant_engine.calculate(region, month)
top3 = ranking.head(3)
scenario = coverage_engine.get(scenario_id)
quant_context = [quant_engine.context(row) for _, row in top3.iterrows()]

st.markdown(
    f"""
<section class="hero">
  <div class="eyebrow">MILITARY COVERAGE LITERACY NAVIGATOR</div>
  <h1>{region} · {month}월, 철수의 보장 브리핑</h1>
  <p>복무환경에 맞춰 감염병 정보를 먼저 보여주고, 현재 상황에 따라 군의료·공공보장·민간의료·기존 보험 확인 순서를 안내합니다.</p>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="context-strip">
  <div class="context-step">1. 복무환경 입력</div>
  <div class="context-step">2. 감염병 브리핑</div>
  <div class="context-step">3. 보장경로 확인</div>
  <div class="context-step">4. 서류·약관 준비</div>
</div>
""",
    unsafe_allow_html=True,
)

metrics = st.columns(3)
metrics[0].metric("복무환경", f"{region} · {month}월")
metrics[1].metric("현재 상황", scenario.label)
metrics[2].metric("안내 구조", "8개 질환 · 4단계")

st.markdown("### 복무환경 맞춤 감염병 브리핑")
st.caption("PNPS는 선택한 지역·월에 어떤 질환 정보를 먼저 보여줄지 정하는 상대점수입니다.")
columns = st.columns(3)
for column, (_, row) in zip(columns, top3.iterrows()):
    disease = str(row["disease"])
    with column:
        st.markdown(
            f"""
<article class="disease-card">
  <span class="rank">복무환경 맞춤 {int(row['personalized_rank'])}위</span>
  <h3>{disease}</h3>
  <div class="score">{row['pnps_0_100']:.1f}</div>
  <div class="label">안내 우선점수 · 발병확률 아님</div>
  <p class="reason">{quant_engine.reason(row)}</p>
  <div class="factor">
    <div><span class="label">지역 집중도</span><b>{row['region_factor']:.2f}</b></div>
    <div><span class="label">해당 월 비중</span><b>{row['month_factor']:.1%}</b></div>
  </div>
</article>
""",
            unsafe_allow_html=True,
        )
        with st.expander("왜 표시됐나요?"):
            a1, a2 = st.columns(2)
            a1.metric("20~24세 남성 AMR", f"{float(row.get('amr', 0)):.2f}")
            a2.metric("기본 NPS", f"{float(row.get('nps', 0)):.1f}")
            st.caption(f"집중 지역: {row.get('top_regions', '자료 확인 필요')}")
            st.caption(f"집중 시기: {row.get('top_months', '자료 확인 필요')}")
            active_actions = action_evidence.query("disease == @disease and value == 1")["dimension"].tolist()
            st.markdown("**공식 문서에서 확인된 행동축**  \n" + " · ".join(ACTION_LABELS[item] for item in active_actions))

tab_brief, tab_routes, tab_checklist, tab_chat, tab_evidence = st.tabs(
    ["내 브리핑", "보장경로 지도", "준비 체크리스트", "근거형 질문", "근거·안전장치"]
)

with tab_brief:
    st.markdown("#### 활동환경에 맞춘 예방 포인트")
    st.markdown(f'<div class="safe-note">{coverage_engine.activity_guidance(activity)}</div>', unsafe_allow_html=True)
    st.markdown("#### 8개 질환 안내순위")
    display = ranking[["personalized_rank", "disease", "pnps_0_100", "nps", "region_factor", "month_factor"]].copy()
    display.columns = ["순위", "질환", "안내 우선점수", "기본 NPS", "지역 RQ", "월 비중"]
    st.dataframe(
        display.style.format({"안내 우선점수": "{:.1f}", "기본 NPS": "{:.1f}", "지역 RQ": "{:.2f}", "월 비중": "{:.1%}"}),
        hide_index=True,
        width="stretch",
    )
    st.bar_chart(display.set_index("질환")[["안내 우선점수"]], color="#ef8f60")
    st.markdown('<div class="notice">점수가 높다는 것은 이 조건에서 먼저 설명할 질환이라는 뜻입니다. 개인 감염확률·중증도·보험 보장 가능성이 아닙니다.</div>', unsafe_allow_html=True)

with tab_routes:
    st.markdown(f"#### {scenario.label}: 보장경로 지도")
    st.write(scenario.summary)
    if scenario.urgent_first:
        st.error("응급하거나 빠르게 악화되는 증상은 비용·보험 확인보다 즉시 진료가 먼저입니다.")
    if scenario_id in {"civilian_needed", "already_paid"}:
        civilian_state = st.selectbox("민간병원을 이용한 경로", list(CIVILIAN_CONTEXT))
        st.info(CIVILIAN_CONTEXT[civilian_state])
    for start in range(0, len(scenario.routes), 2):
        route_columns = st.columns(2)
        for route_column, route in zip(route_columns, scenario.routes[start : start + 2]):
            with route_column:
                route_card(route)
    st.markdown('<div class="safe-note"><b>읽는 순서:</b> 군의료 경로를 먼저 확인하고, 공공보장과 민간의료 비용처리를 구분한 뒤, 남은 실제 본인부담에 대해 기존 민간보험 약관을 확인합니다.</div>', unsafe_allow_html=True)

with tab_checklist:
    st.markdown(f"#### {scenario.label}: 철수의 준비 체크리스트")
    st.caption("체크 상태는 현재 브라우저 세션에서만 유지되며 주민번호·진단명·보험증권은 입력받거나 저장하지 않습니다.")
    checklist_keys = []
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**지금 할 일**")
        for index, item in enumerate(scenario.checklist):
            key = f"task_{scenario_id}_{index}"
            st.checkbox(item, key=key)
            checklist_keys.append(key)
    route_documents = []
    for route in scenario.routes:
        route_documents.extend(route.documents_to_check)
    route_documents = list(dict.fromkeys(route_documents))
    with right:
        st.markdown("**서류 보관함**")
        for index, document in enumerate(route_documents):
            key = f"doc_{scenario_id}_{index}"
            st.checkbox(document, key=key)
            checklist_keys.append(key)
    completed = sum(bool(st.session_state.get(key)) for key in checklist_keys)
    st.progress(completed / len(checklist_keys) if checklist_keys else 0, text=f"준비 {completed}/{len(checklist_keys)}")

    st.markdown("#### 보험 리터러시 1분 점검")
    literacy = [
        ("보험기간", "진료일에 계약이 유효했는지 확인합니다."),
        ("보장범위", "질병·상해, 입원·통원·검사·비급여 조건을 나눠 봅니다."),
        ("면책조건", "보장하지 않는 사유와 대기기간을 확인합니다."),
        ("실제 본인부담", "군·공공 지원 후 본인이 실제로 부담한 금액을 구분합니다."),
        ("청구서류", "보험사마다 요구하는 진단서·확인서·영수증 기준을 확인합니다."),
    ]
    literacy_columns = st.columns(5)
    for col, (title, text) in zip(literacy_columns, literacy):
        col.markdown(f'<div class="literacy-card"><b>{title}</b><br><span class="label">{text}</span></div>', unsafe_allow_html=True)

    checklist_text = [
        "복무온 보장 리터러시 체크리스트",
        f"복무환경: {region} · {month}월 · {activity}",
        f"현재 상황: {scenario.label}",
        "",
        "[지금 할 일]",
        *[f"[ ] {item}" for item in scenario.checklist],
        "",
        "[확인할 서류]",
        *[f"[ ] {item}" for item in route_documents],
        "",
        "※ 개인 발병확률·의료진 판단·보험금 지급 판정을 제공하지 않습니다.",
    ]
    st.download_button(
        "체크리스트 내려받기",
        data="\n".join(checklist_text).encode("utf-8-sig"),
        file_name=f"복무온_{region}_{month}월_보장체크리스트.txt",
        mime="text/plain",
    )

with tab_chat:
    st.markdown("#### 공식 근거 안에서만 답하는 네비게이터")
    st.caption(f"현재 화면 맥락: {region} · {month}월 · {scenario.label}")
    prompts = [
        "증상이 생기면 부대에서 어떻게 해야 하나요?",
        "민간병원 진료 전 무엇을 확인하나요?",
        "이미 낸 진료비는 어떻게 확인하나요?",
        "기존 실손보험에서 무엇을 확인하나요?",
        "나라사랑카드 보험으로 보장되나요?",
    ]
    prompt_columns = st.columns(5)
    selected_prompt = None
    for col, prompt in zip(prompt_columns, prompts):
        if col.button(prompt, width="stretch"):
            selected_prompt = prompt
    if "literacy_messages" not in st.session_state:
        st.session_state.literacy_messages = []
    for message in st.session_state.literacy_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    user_query = st.chat_input("예: 민간병원 진료비 영수증을 이미 냈는데 무엇부터 확인하나요?")
    query = selected_prompt or user_query
    if query:
        st.session_state.literacy_messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        with st.chat_message("assistant"):
            with st.spinner("정량 결과와 공식 문서를 대조하고 있습니다..."):
                answer = answer_engine.answer(query, quant_context)
                st.markdown(answer.text)
                st.caption(f"답변 모드: {answer.mode}")
                with st.expander("사용한 근거 원문"):
                    if not answer.sources:
                        st.info("현재 질문을 판정할 현행 공식 약관 근거가 없습니다.")
                    for index, source in enumerate(answer.sources, start=1):
                        st.markdown(f"**[S{index}] {source.chunk['title']} · {source.chunk['locator']}**")
                        st.caption(f"{source.chunk['source_org']} | 출처등급 {source.chunk['authority_level']} | 검색점수 {source.score:.3f}")
                        st.write(source.chunk["text"][:700])
        st.session_state.literacy_messages.append({"role": "assistant", "content": answer.text})

with tab_evidence:
    st.markdown("#### 숫자·규칙·문서를 분리한 구조")
    st.markdown(
        """
1. **정량 엔진**은 지역·월에 따른 질환 안내순위만 계산합니다.  
2. **보장경로 규칙**은 현재 상황에 맞는 군의료·공공보장·민간의료·기존보험 확인 순서를 결정합니다.  
3. **RAG 검색**은 법령·훈령·질병관리청·심평원 문서를 찾아 쉬운 설명과 원문 인용을 제공합니다.  
4. **안전장치**는 공무상 여부, 건강보험 급여, 보험금 지급을 자동 확정하지 않습니다.
"""
    )
    m1, m2, m3 = st.columns(3)
    manifest = pd.read_csv(MANIFEST_PATH, encoding="utf-8-sig")
    used = manifest.query("use_for_rag == True")
    m1.metric("색인 공식문서", len(used))
    m2.metric("보장 상황", len(coverage_engine.scenarios))
    m3.metric("구조화 보장경로", sum(len(coverage_engine.get(key).routes) for key in coverage_engine.scenarios))
    st.code("PNPS = NPS × 지역 RQ × 해당 지역의 월별 발생비중", language="text")
    st.caption("활동환경 선택과 보장상황 선택은 PNPS 계산에 영향을 주지 않습니다.")
    st.markdown("#### 문서 근거 Actionability")
    scores = action_evidence.pivot(index="disease", columns="dimension", values="value")
    scores["Actionability"] = scores.mean(axis=1)
    st.dataframe(scores.reset_index(), hide_index=True, width="stretch")
    st.markdown('<div class="notice">현행 공식 근거가 없으면 ‘현재 근거 부족’으로 표시합니다. 과거 나라사랑카드 OCR 자료는 현재 보장 판정에 사용하지 않습니다.</div>', unsafe_allow_html=True)
