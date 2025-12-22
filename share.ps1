$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
  Write-Host ".venv가 없습니다. 먼저 .\\setup.ps1를 실행하세요."
  exit 1
}

if (-not (Test-Path ".env")) {
  Write-Host ".env(비밀번호 설정)가 없습니다. 먼저 .\\setup.ps1를 실행하세요."
  exit 1
}

$python = Join-Path $PSScriptRoot ".venv\\Scripts\\python.exe"

$cloudflaredDir = Join-Path $PSScriptRoot "tools"
$cloudflared = Join-Path $cloudflaredDir "cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
  New-Item -ItemType Directory -Force -Path $cloudflaredDir | Out-Null
  $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  Write-Host "cloudflared 다운로드 중..."
  Invoke-WebRequest -Uri $url -OutFile $cloudflared
}

Write-Host "로컬 서버 시작 중..."
$server = Start-Process -FilePath $python -ArgumentList "webapp.py" -PassThru -WindowStyle Hidden

try {
  $ready = $false
  for ($i=0; $i -lt 40; $i++) {
    try {
      Invoke-WebRequest -Uri "http://127.0.0.1:8000/login" -UseBasicParsing -TimeoutSec 2 | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Milliseconds 250
    }
  }
  if (-not $ready) {
    throw "서버가 8000 포트에서 준비되지 않았습니다. (다른 프로그램이 포트를 사용 중인지 확인)"
  }

  Write-Host ""
  Write-Host "이제 인터넷 공개 URL을 생성합니다. 아래 출력에 나오는 https://*.trycloudflare.com 주소를 복사해서 공유하세요."
  Write-Host "종료하려면 이 창에서 Ctrl+C를 누르세요. (로컬 서버도 같이 종료됩니다)"
  Write-Host ""

  & $cloudflared tunnel --url http://127.0.0.1:8000
} finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
  }
}

