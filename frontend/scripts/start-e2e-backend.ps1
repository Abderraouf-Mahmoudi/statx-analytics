$ErrorActionPreference = "Stop"
$backend = Resolve-Path (Join-Path $PSScriptRoot "..\..\backend")
$database = Join-Path $backend ".pytest_cache\e2e-statx.db"
New-Item -ItemType Directory -Force -Path (Split-Path $database) | Out-Null
Remove-Item -LiteralPath $database -Force -ErrorAction SilentlyContinue
$env:DATABASE_URL = "sqlite:///$($database.Replace('\', '/'))"
$python = "C:\Users\MSI\Desktop\StatX\statx-analytics\backend\.venv\Scripts\python.exe"
Push-Location $backend
try {
  & $python -m alembic -c alembic.ini upgrade head
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Pop-Location
}
