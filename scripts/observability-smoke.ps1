$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repo
try {
    & uv run --locked --extra dev --managed-python python scripts/observability-smoke.py
    if ($LASTEXITCODE -ne 0) { throw 'Smoke isolado falhou; consulte .runtime/observability-report.json.' }
} finally { Pop-Location }
