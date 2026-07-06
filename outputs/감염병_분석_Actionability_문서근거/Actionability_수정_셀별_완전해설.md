# Actionability 문서근거 반영 노트북 해설

## 원본 보존 원칙

원본 `outputs/감염병_분석/군_복무기_감염병_데이터분석.ipynb`은 수정하지 않았다. 이 폴더의 노트북은 원본을 복제한 뒤 Actionability 입력 부분과 출력 경로만 바꾼 별도 실행본이다.

## 바뀐 셀

### 파라미터 셀

기존의 `ACTIONABILITY_TAGS` 직접 입력 블록을 삭제하고 다음 순서로 바꿨다.

1. `rag_prototype/data/structured/actionability_evidence.csv`를 읽는다.
2. 질환 집합이 최종 8개와 정확히 같은지 검사한다.
3. 행동축 집합이 5개와 정확히 같은지 검사한다.
4. 40개 모든 행의 근거 원문이 비어 있지 않은지 검사한다.
5. 질환×행동축 피벗표에 결측이 없는지 검사한다.
6. 검증된 피벗표에서 `ACTIONABILITY_TAGS`를 생성한다.

따라서 파일이 누락되거나 질환·축·원문 중 하나라도 비면 노트북이 조용히 임의값을 사용하지 않고 즉시 중단된다.

### Actionability 설명 셀

Actionability의 의미를 “공식 문서에서 사용자가 실행할 수 있는 안내축의 존재 비율”로 수정했다. 임상 중증도나 통계적 추정치가 아니라는 점을 명시했다.

### RAG 메타데이터 셀

각 질환의 RAG용 정량 메타데이터에 `actionability_evidence_file`을 추가했다. 프로토타입에서 점수와 근거표의 연결 위치를 확인할 수 있다.

### 출력 파라미터

모든 CSV·차트·카드는 `outputs/감염병_분석_Actionability_문서근거` 아래에 저장한다. 원본 결과 폴더를 덮어쓰지 않는다.

## 바뀌지 않은 셀과 산식

원천 파일 읽기, long-format 전처리, KOSIS 인구 결합, AMR·SMR·RQ·Seasonality, NPS 가중치, PNPS 산식, 차트·카드 생성 과정은 원본과 동일하다.

NPS 가중치는 다음과 같이 유지했다.

- AMR 0.35
- RQ 0.25
- Seasonality 0.20
- Actionability 0.20

## 실행 검증

- 코드 셀 19개 전부 실행
- 실행 오류 0개
- Actionability 최대 절대차 0
- NPS 최대 절대차 0
- 질환 순위 동일
- PNPS 예시 최대 절대차 0

값이 동일한 이유는 새 공식 근거 판정 결과가 기존 임시 태그와 우연히 동일했기 때문이다. 중요한 변화는 값 자체보다 근거와 재현성이다.

## 근거표 읽는 방법

`actionability_evidence.csv`의 주요 열은 다음과 같다.

- `disease`: 질환명
- `dimension`: 다섯 행동축 중 하나
- `value`: 채택 1, 미채택 0
- `rationale`: 판정 이유
- `source_file`, `source_path`: 근거 문서
- `anchor`: 문서에서 찾은 기준어·조문
- `evidence_quote`: 실제 원문 발췌
- `authority_level`: 출처 등급
- `effective_status`: 현행성 상태

발표에서 특정 값의 이유를 질문받으면 질환명과 행동축으로 이 표를 필터링해 원문을 바로 제시하면 된다.
