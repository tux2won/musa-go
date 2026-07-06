from __future__ import annotations

from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "RAG_구축_평가_실행완료.ipynb"


def code(source: str):
    return nbformat.v4.new_code_cell(source)


def markdown(source: str):
    return nbformat.v4.new_markdown_cell(source)


def main() -> None:
    cells = [
        markdown(
            """# 군 복무기 감염병 보장 네비게이터 — RAG 구축·평가 실행본

이 노트북은 문서 DB 품질, 문서근거 Actionability, 기존 점수 회귀, 하이브리드 검색, 지역·월 정량 연동, 안전성 평가 결과를 한 번에 검토하기 위한 실행 완료본이다.

> HIRA 진료통계는 이번 RAG 구현 범위에서 제외했다. NPS·PNPS는 개인 발병확률이나 보험 보장 가능성이 아니다."""
        ),
        code(
            f"""from pathlib import Path
import json, sys
import pandas as pd
from IPython.display import display

ROOT = Path(r'{ROOT}')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
pd.set_option('display.max_colwidth', 110)
print('프로젝트 경로:', ROOT)
print('실행 상태: 준비 완료')"""
        ),
        markdown("## 1. 문서 DB 품질"),
        code(
            """manifest = pd.read_csv(ROOT/'data/manifest.csv', encoding='utf-8-sig')
chunk_count = sum(1 for _ in open(ROOT/'data/normalized/chunks.jsonl', encoding='utf-8'))
document_summary = pd.DataFrame([{
    '수집 파일': len(manifest),
    '검색 사용': int(manifest['use_for_rag'].sum()),
    '중복·대체본 제외': int((~manifest['use_for_rag']).sum()),
    'PDF 페이지': int(manifest['page_count'].sum()),
    '추출 문자': int(manifest['char_count'].sum()),
    '검색 청크': chunk_count,
    '깨진 문자': int(manifest['replacement_chars'].sum()),
}])
display(document_summary)
assert document_summary.loc[0, '깨진 문자'] == 0
display(manifest.loc[~manifest['use_for_rag'], ['title','exclusion_reason']])"""
        ),
        markdown("## 2. 문서근거 Actionability"),
        code(
            """evidence = pd.read_csv(ROOT/'data/structured/actionability_evidence.csv', encoding='utf-8-sig')
dimensions = ['vaccination','region_season','exposure_prevention','early_response','navigation']
action_scores = evidence.pivot(index='disease', columns='dimension', values='value')[dimensions]
action_scores['actionability'] = action_scores.mean(axis=1)
display(action_scores.reset_index())
print('근거 행:', len(evidence), '| 원문 누락:', int(evidence['evidence_quote'].fillna('').eq('').sum()))
assert len(evidence) == 40
assert evidence['evidence_quote'].fillna('').str.len().gt(0).all()"""
        ),
        markdown("## 3. 원본 대비 NPS·PNPS 회귀 검증"),
        code(
            """workspace = ROOT.parent
old_dir = workspace/'outputs/감염병_분석/processed'
new_dir = workspace/'outputs/감염병_분석_Actionability_문서근거/processed'
old_nps = pd.read_csv(old_dir/'nps_shortlist_2016_2023.csv', encoding='utf-8-sig')
new_nps = pd.read_csv(new_dir/'nps_shortlist_2016_2023.csv', encoding='utf-8-sig')
comparison = old_nps.merge(new_nps, on='disease', suffixes=('_old','_new'), validate='one_to_one')
metrics = []
for col in ['actionability','nps']:
    metrics.append({'지표': col, '최대 절대차': (comparison[f'{col}_old']-comparison[f'{col}_new']).abs().max()})
old_p = pd.read_csv(old_dir/'pnps_examples.csv', encoding='utf-8-sig')
new_p = pd.read_csv(new_dir/'pnps_examples.csv', encoding='utf-8-sig')
keys = [c for c in ['selected_region','selected_month','disease'] if c in old_p.columns and c in new_p.columns]
value = 'pnps_0_100' if 'pnps_0_100' in old_p.columns else 'pnps'
p = old_p.merge(new_p, on=keys, suffixes=('_old','_new'))
metrics.append({'지표': 'PNPS 예시', '최대 절대차': (p[f'{value}_old']-p[f'{value}_new']).abs().max()})
display(pd.DataFrame(metrics))
assert max(row['최대 절대차'] for row in metrics) == 0"""
        ),
        markdown("## 4. 검색 평가"),
        code(
            """retrieval_metrics = json.loads((ROOT/'evaluation/retrieval_metrics.json').read_text(encoding='utf-8'))
display(pd.DataFrame([retrieval_metrics]))
assert retrieval_metrics['recall_at_5'] == 1.0
assert retrieval_metrics['historical_filter_violations'] == 0"""
        ),
        markdown("## 5. 지역·월 정량 엔진과 RAG 검색 예시"),
        code(
            """from src.quantitative_engine import QuantitativeEngine
from src.retrieval import HybridRetriever

quant = QuantitativeEngine()
ranking = quant.calculate('강원', 7)
display(ranking[['personalized_rank','disease','pnps_0_100','nps','region_factor','month_factor']].head(8))

retriever = HybridRetriever.load(ROOT/'index/hybrid_index.joblib')
hits = retriever.search('강원 7월 말라리아 예방수칙과 증상 시 부대 진료 경로는?', top_k=5)
display(pd.DataFrame([{
    '순위': h.rank, '점수': round(h.score,4), '문서': h.chunk['title'],
    '위치': h.chunk['locator'], '기관': h.chunk['source_org'],
    '원문 앞부분': h.chunk['text'][:180]
} for h in hits]))
assert hits and all(h.chunk['effective_status'] != 'historical_unverified' for h in hits)"""
        ),
        markdown("## 6. 답변 안전성 평가"),
        code(
            """safety_metrics = json.loads((ROOT/'evaluation/safety_metrics.json').read_text(encoding='utf-8'))
safety = pd.read_csv(ROOT/'evaluation/safety_results.csv', encoding='utf-8-sig')
display(pd.DataFrame([safety_metrics]))
display(safety[['category','question','passed','source_count']])
assert safety['passed'].all()"""
        ),
        markdown(
            """## 7. 검증 결론

- 문서 42개 중 38개를 검색에 사용했고, 2,863개 청크의 문자 추출 오류는 발견되지 않았다.
- Actionability 40개 판정은 모두 공식 문서 원문에 연결된다.
- 기존 NPS·PNPS와 순위는 변하지 않았다.
- 내부 검색 60문항과 안전성 12문항을 모두 통과했다.
- 현행 나라사랑카드 약관이 없으므로 보장 여부는 답하지 않고 확인 경로만 제시한다.

내부 평가 100%는 이 프로젝트의 제한된 검증셋에 대한 결과이며 외부 사용자 정확도를 의미하지 않는다."""
        ),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata["language_info"] = {"name": "python", "version": "3.12"}
    executor = ExecutePreprocessor(timeout=300, kernel_name="python3")
    executor.preprocess(notebook, {"metadata": {"path": str(ROOT)}})
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
