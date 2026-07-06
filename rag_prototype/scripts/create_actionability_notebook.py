from __future__ import annotations

import re
from pathlib import Path

import nbformat


WORKSPACE = Path(__file__).resolve().parents[2]
SOURCE_NOTEBOOK = WORKSPACE / "outputs" / "감염병_분석" / "군_복무기_감염병_데이터분석.ipynb"
OUTPUT_DIR = WORKSPACE / "outputs" / "감염병_분석_Actionability_문서근거"
OUTPUT_NOTEBOOK = OUTPUT_DIR / "군_복무기_감염병_데이터분석_Actionability_근거반영.ipynb"
EVIDENCE_PATH = WORKSPACE / "rag_prototype" / "data" / "structured" / "actionability_evidence.csv"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.read(SOURCE_NOTEBOOK, as_version=4)

    parameter_cell = notebook.cells[2]
    parameter_cell.source = parameter_cell.source.replace(
        r'OUTPUT_DIR = Path(r"C:\Users\user\Documents\AI 활용 경진대회\outputs\감염병_분석")',
        r'OUTPUT_DIR = Path(r"C:\Users\user\Documents\AI 활용 경진대회\outputs\감염병_분석_Actionability_문서근거")',
    )
    start = parameter_cell.source.index("# 5개 사용자 행동 축")
    end = parameter_cell.source.index("NPS_WEIGHTS =")
    evidence_block = f'''# 5개 사용자 행동 축. 수집한 공식 문서의 근거표에서만 생성한다.\nACTIONABILITY_EVIDENCE_PATH = Path(r"{EVIDENCE_PATH}")\nassert ACTIONABILITY_EVIDENCE_PATH.exists(), f"Actionability 근거표 누락: {{ACTIONABILITY_EVIDENCE_PATH}}"\nactionability_evidence = pd.read_csv(ACTIONABILITY_EVIDENCE_PATH, encoding="utf-8-sig")\nACTION_DIMENSIONS = ["vaccination", "region_season", "exposure_prevention", "early_response", "navigation"]\nassert set(actionability_evidence["disease"]) == set(SHORTLIST), "8개 질환 근거 누락"\nassert set(actionability_evidence["dimension"]) == set(ACTION_DIMENSIONS), "5개 행동축 근거 누락"\nassert actionability_evidence["evidence_quote"].fillna("").str.len().gt(0).all(), "근거 원문이 비어 있는 태그 존재"\n_actionability_matrix = actionability_evidence.pivot(index="disease", columns="dimension", values="value").reindex(SHORTLIST)\nassert _actionability_matrix.notna().all().all(), "질환×행동축 근거 행렬 결측"\nACTIONABILITY_TAGS = {{\n    disease: {{dimension: int(_actionability_matrix.loc[disease, dimension]) for dimension in ACTION_DIMENSIONS}}\n    for disease in SHORTLIST\n}}\n'''
    parameter_cell.source = parameter_cell.source[:start] + evidence_block + parameter_cell.source[end:]

    for cell in notebook.cells:
        if cell.cell_type == "markdown" and "#### Actionability" in cell.source:
            cell.source = re.sub(
                r"#### Actionability[\s\S]*?(?=\n###|\Z)",
                """#### Actionability\n\n5개 이진 태그의 평균이다. 값은 코드에 직접 입력하지 않고 `actionability_evidence.csv`의 질환×행동축 공식 근거표에서 피벗한다.\n\n- 예방접종 확인\n- 지역·시기 확인\n- 노출 예방수칙\n- 증상 시 조기 대응\n- 군의료·비용 경로 확인\n\n각 행은 문서명, 근거 위치, 원문 발췌, 출처등급, 현행성 상태를 포함한다. 말라리아·쯔쯔가무시증의 예방접종 축은 0, 일본뇌염·신증후군출혈열은 5개 축이 모두 1이다. 이 점수는 임상적 중증도가 아니라 **공식 문서에서 사용자가 실행할 수 있는 안내축의 존재 비율**이다.\n""",
                cell.source,
            )
            break

    for cell in notebook.cells:
        if cell.cell_type == "code" and "rag_metadata_seed[\"quantitative_scope\"]" in cell.source:
            marker = 'rag_metadata_seed["quantitative_scope"]'
            insert = 'rag_metadata_seed["actionability_evidence_file"] = str(ACTIONABILITY_EVIDENCE_PATH)\n'
            cell.source = cell.source.replace(marker, insert + marker)
            cell.source = cell.source.replace(
                '"quantitative_scope", "quantitative_disclaimer", "stat_source_files",',
                '"quantitative_scope", "quantitative_disclaimer", "stat_source_files", "actionability_evidence_file",',
            )
            break

    notebook.metadata.setdefault("actionability_revision", {})
    notebook.metadata["actionability_revision"] = {
        "source_notebook": str(SOURCE_NOTEBOOK),
        "evidence_file": str(EVIDENCE_PATH),
        "revision_scope": "Actionability tags only; original notebook preserved",
    }
    nbformat.write(notebook, OUTPUT_NOTEBOOK)
    print(OUTPUT_NOTEBOOK)


if __name__ == "__main__":
    main()
