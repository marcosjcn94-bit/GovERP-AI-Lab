param([switch]$InstallBrowser)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$npmCommand = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { 'npm.cmd' } else { 'npm' }
foreach ($command in @('uv', 'docker', 'node', $npmCommand)) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Pre-requisito ausente: $command." }
}
Push-Location $repo
$projectName = 'goverp-e2e-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$composeArgs = @('compose', '--env-file', '.env.example', '-f', 'docker-compose.e2e.yml', '-p', $projectName)
$testVariables = @{
    GOVERP_OWNER_DATABASE_URL = 'postgresql+psycopg://goverp_owner:test-owner-only@127.0.0.1:5441/goverp_e2e'
    GOVERP_APP_DATABASE_URL = 'postgresql+psycopg://goverp_app:test-app-only@127.0.0.1:5441/goverp_e2e'
    GOVERP_SESSION_SECRET = 'isolated-e2e-session-secret-at-least-32-bytes'
    GOVERP_MODEL_URL = 'http://127.0.0.1:1'
    GOVERP_MODEL_TIMEOUT_SECONDS = '1'
    GOVERP_MODEL_ENABLED = 'false'
    GOVERP_ALLOWED_ORIGIN = 'http://127.0.0.1:5174'
    LANGSMITH_TRACING = 'false'
    GOVERP_OTEL_ENABLED = 'false'
}
$previous = @{}
foreach ($key in $testVariables.Keys) {
    $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    [Environment]::SetEnvironmentVariable($key, $testVariables[$key], 'Process')
}
$timer = [Diagnostics.Stopwatch]::StartNew()
$status = 'failed'
$stage = 'database'
try {
    & docker @composeArgs up -d --wait --wait-timeout 90 database
    if ($LASTEXITCODE -ne 0) { throw 'Banco E2E nao ficou pronto.' }
    $stage = 'migrations'
    & uv run --locked --extra dev --managed-python python -m gov_erp.migrate
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas migrations E2E.' }
    $stage = 'seed'
    & uv run --locked --extra dev --managed-python python -m gov_erp.seed
    if ($LASTEXITCODE -ne 0) { throw 'Falha no seed E2E.' }
    if ($InstallBrowser) {
        & $npmCommand --prefix frontend run install:browser
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Chromium de teste.' }
    }
    $stage = 'browser'
    & $npmCommand --prefix frontend run test:e2e
    if ($LASTEXITCODE -ne 0) { throw 'E2E falhou; consulte .runtime/playwright-report.' }
    $stage = 'recovery'
    & (Join-Path $PSScriptRoot 'recovery-check.ps1') -ProjectName $projectName
    if ($LASTEXITCODE -ne 0) { throw 'A API nao recuperou apos a reinicializacao isolada do PostgreSQL.' }
    $status = 'passed'
} finally {
    & docker @composeArgs down --timeout 10
    $cleanupCode = $LASTEXITCODE
    $timer.Stop()
    New-Item -ItemType Directory -Path (Join-Path $repo '.runtime') -Force | Out-Null
    @{ measured_at_utc = [DateTime]::UtcNow.ToString('o'); project = $projectName; status = $status; last_stage = $stage; seconds = [Math]::Round($timer.Elapsed.TotalSeconds, 3); cleanup_exit_code = $cleanupCode; model_calls = 0 } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repo '.runtime/e2e-report.json') -Encoding utf8
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
    Pop-Location
    if ($cleanupCode -ne 0) { throw "Falha ao remover o projeto temporario $projectName." }
}
