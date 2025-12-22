$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
  Write-Host ".venv가 없습니다. 먼저 .\\setup.ps1를 실행하세요."
  exit 1
}

if (-not (Test-Path ".env")) {
  Write-Host ".env가 없습니다. 먼저 .\\setup.ps1를 실행하세요."
  exit 1
}

& .\.venv\Scripts\python webapp.py

