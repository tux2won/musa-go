# 복무온(Musa-GO)

지역·월별 감염병 설명 우선순위 분석과 공식 문서 기반 RAG 안내를 결합한 군 의료 정보 네비게이터입니다.

## 저장소 구성

- `rag_prototype/`: Streamlit 앱, 하이브리드 검색 인덱스, RAG 구현 코드, 테스트 및 평가 결과
- `outputs/감염병_분석_Actionability_문서근거/`: 데이터 분석 노트북, 가공 데이터, PNPS 산출물, 차트 및 해설
- `RAG_document/0702/`: 보장경로 검증에 필요한 최소 공식 근거 문서

## 로컬 실행

Python 3.12 환경을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r rag_prototype/requirements.txt
streamlit run rag_prototype/app.py
```

OpenAI API 키가 없으면 로컬 근거형 모드로 실행됩니다. LLM 생성 모드를 사용하려면 환경변수 또는 Streamlit Cloud의 Secrets에 다음 값을 설정합니다.

```toml
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-5.4-mini"
```

비밀키가 담긴 `.streamlit/secrets.toml`과 `.env` 파일은 저장소에 커밋하지 않습니다.

## Streamlit Community Cloud 배포

1. GitHub 저장소를 Streamlit Community Cloud에 연결합니다.
2. 앱 진입점으로 `rag_prototype/app.py`를 지정합니다.
3. Python 버전은 로컬 검증 환경과 같은 3.12를 선택합니다.
4. LLM 생성 모드가 필요하면 Advanced settings의 Secrets에 위 값을 입력합니다.
5. Deploy를 실행합니다.

앱의 `requirements.txt`는 진입점과 같은 폴더에 있으며, 실행에 필요한 분석 데이터와 검색 인덱스도 저장소에 포함됩니다.

## 검증

```powershell
python -m pip install -r rag_prototype/requirements-dev.txt
python -m pytest -q rag_prototype/tests
```

현재 평가 산출물은 `rag_prototype/evaluation/`에서 확인할 수 있습니다.
