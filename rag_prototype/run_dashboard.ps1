$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Root) ".venv-rag\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "가상환경을 찾을 수 없습니다: $Python"
}

Set-Location -LiteralPath $Root
& $Python -m streamlit run app.py
