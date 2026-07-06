# 군 복무기 감염병 보장 네비게이터 — RAG 프로토타입

지역·월별 감염병 안내순위와 상황별 보장 확인경로를 현행 공식 문서 검색과 결합한 로컬 실행형 보장 리터러시 프로토타입이다. HIRA 진료통계는 이번 버전에 포함하지 않았다.

## 구현 범위

- 기존 NPS/PNPS 계산 결과를 그대로 읽어 지역·월별 상위 질환을 제시한다.
- 사용자가 현재 상황을 선택하면 군의료·공공보장·민간의료·기존 민간보험 확인의 네 경로를 구조화 규칙으로 제시한다.
- 상황별 증빙서류 체크리스트와 보험 약관 확인교육을 제공하되 특정 상품을 추천하지 않는다.
- `RAG_document`의 PDF·Markdown·CSV·DOCX를 정규화하고 문서/청크 메타데이터를 만든다.
- 문자 n-gram TF-IDF와 BM25를 결합한 하이브리드 검색에 질환·질문 의도·출처 등급·현행성 재순위를 적용한다.
- 공식 문서 40개 근거 행으로 8개 질환 × 5개 행동축 Actionability를 재산출한다.
- 현행성이 확인되지 않은 나라사랑카드 OCR 자료는 기본 검색에서 제외한다.
- API 키가 없으면 로컬 근거형 답변으로 완전히 동작한다. 키가 있으면 OpenAI Responses API로 근거 제한형 답변을 생성한다.

RAG는 문서를 모델에 재학습시키는 방식이 아니다. 문서를 검색 가능한 인덱스로 만들고, 질문 시 관련 근거를 찾아 답변 컨텍스트로 제공한다.

## 빠른 실행

PowerShell에서 작업 폴더를 이 디렉터리로 이동한 뒤 실행한다.

```powershell
cd "C:\Users\user\Documents\AI 활용 경진대회\rag_prototype"
..\.venv-rag\Scripts\Activate.ps1
streamlit run app.py
```

브라우저에서 `http://localhost:8501`을 연다. 더블클릭 실행용으로 `run_dashboard.ps1`도 제공한다.

## 처음부터 다시 빌드

```powershell
cd "C:\Users\user\Documents\AI 활용 경진대회\rag_prototype"
..\.venv-rag\Scripts\python.exe -m src.ingest
..\.venv-rag\Scripts\python.exe -m src.actionability
..\.venv-rag\Scripts\python.exe -m src.retrieval
..\.venv-rag\Scripts\python.exe scripts\evaluate_retrieval.py
..\.venv-rag\Scripts\python.exe scripts\evaluate_safety.py
..\.venv-rag\Scripts\python.exe -m pytest -q
```

새 문서를 `RAG_document`에 추가하면 위 순서로 재빌드한다. 문서별 현행성·기관·출처등급 자동 추론 규칙은 `src/ingest.py`의 `infer_source()`에서 확인하고, 새 문서가 예외라면 규칙을 명시적으로 추가한다.

## 선택: OpenAI 생성모드

`.env.example`을 참고해 현재 PowerShell 세션에 키를 설정한다. 키가 없어도 검색·정량 엔진·대시보드는 정상 동작한다.

```powershell
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-5.4-mini"
streamlit run app.py
```

API 오류가 발생하면 로컬 근거형 답변으로 자동 전환한다. 키는 코드·노트북·CSV에 저장하지 않는다.

## 핵심 산출물

- `data/manifest.csv`: 42개 원본 파일의 사용 여부·체크섬·기관·현행성·문자 품질
- `data/normalized/chunks.jsonl`: 검색용 2,863개 청크
- `data/structured/actionability_evidence.csv`: 질환×행동축 40개 근거 원문
- `data/structured/coverage_routes.json`: 5개 상황×4개 보장경로의 조건·첫 행동·서류·근거상태
- `index/hybrid_index.joblib`: 로컬 하이브리드 검색 인덱스
- `evaluation/retrieval_metrics.json`: 60문항 검색 평가
- `evaluation/safety_metrics.json`: 14개 위험상황 안전성 평가
- `RAG_구축_평가_실행완료.ipynb`: 실행 결과가 저장된 검토용 노트북
- `RAG_LLM_구현_완전해설.md`: 구조·판정 원칙·한계 해설
- `보장리터러시_기획서_활용문안.md`: 공모전·포트폴리오용 문제정의·기대효과·사업화 문안

## 해석 안전규칙

- NPS·PNPS는 개인 발병확률, 임상적 중증도, 보험 보장 가능성이 아니다.
- 건강보험·나라사랑카드 지급 여부는 질병명만으로 단정하지 않는다.
- 과거 또는 현행성 미확인 약관은 현재 보장의 근거로 사용하지 않는다.
- 증상 질문은 진단하지 않고 부대 의무실 또는 의료기관 진료·보고 경로를 안내한다.
- 근거가 없으면 추측하지 않고 확인할 기관·문서를 제시한다.

## 현재 검증 결과

- 문서: 42개 중 38개 사용, 4개 중복/대체본 제외, 총 1,859 PDF 페이지, 깨진 문자 0개
- 검색: 60문항 Recall@5 100%, 질환 적중률 100%, 의도 적중률 100%, 과거자료 필터 위반 0건
- 안전성: 14/14 통과
- 코드: pytest 16/16 통과
- Actionability: 40/40 근거 원문 존재, 기존 NPS·PNPS와 회귀 차이 0

위 100% 수치는 현재 작성한 내부 평가세트에 대한 결과이며, 실제 배포 성능을 보장하는 외부 검증값은 아니다.
