$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python이 필요합니다. Microsoft Store 또는 https://www.python.org 에서 Python 3.11+ 설치 후 다시 실행하세요."
  exit 1
}

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
  & .\.venv\Scripts\python tools\set_password.py
}

Write-Host "설정 완료. 다음은 .\\run.ps1 실행하세요."

