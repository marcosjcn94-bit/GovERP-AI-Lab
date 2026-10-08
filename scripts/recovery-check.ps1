param([Parameter(Mandatory)][string]$ProjectName)

$ErrorActionPreference = 'Stop'
if ($ProjectName -notmatch '^goverp-e2e-[a-f0-9]{12}$') { throw 'Projeto Compose fora do escopo isolado do E2E.' }
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
$runtime = Join-Path $repo '.runtime'
$pythonPath = if ($IsWindows) {
    Join-Path $repo '.venv\Scripts\python.exe'
} else {
    Join-Path $repo '.venv/bin/python'
}
if (-not (Test-Path $pythonPath)) { throw 'Python do ambiente uv não encontrado.' }
$projectArgs = @('--env-file', '.env.example', '-f', 'docker-compose.e2e.yml', '-p', $ProjectName)
$api = $null
$web = $null
$report = [ordered]@{ measured_at_utc = [DateTime]::UtcNow.ToString('o'); database_restart = $false; first_request = $false; request_after_restart = $false }
try {
    $apiStart = @{
        FilePath = $pythonPath
        ArgumentList = @('-m', 'uvicorn', 'gov_erp.api:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8002', '--no-access-log')
        WorkingDirectory = $repo.Path
        PassThru = $true
        RedirectStandardOutput = Join-Path $runtime 'recovery-api.stdout.log'
        RedirectStandardError = Join-Path $runtime 'recovery-api.stderr.log'
    }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        $apiStart.WindowStyle = 'Hidden'
    }
    $api = Start-Process @apiStart
    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/health/ready' -TimeoutSec 2
            if ($health.database -eq 'ready') { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'API de recuperacao nao iniciou com banco pronto.' }

    $web = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $login = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/auth/login' -Method Post -WebSession $web -ContentType 'application/json' -Body '{"email":"gestor@demo.pr.gov.br","password":"Local-Demo-Only-2026!","municipality_id":"4106902"}'
    $headers = @{ 'x-csrf-token' = $login.csrf_token }
    $assistantBody = '{"question":"auditoria demonstrativa"}'
    $firstResponse = Invoke-WebRequest -Uri 'http://127.0.0.1:8002/api/assistant' -Method Post -WebSession $web -Headers $headers -ContentType 'application/json' -Body $assistantBody -UseBasicParsing
    $firstHeaders = $firstResponse.Headers
    $first = ConvertFrom-Json $firstResponse.Content
    if ($first.run_id -ne $firstHeaders['X-Request-ID']) { throw 'O primeiro request_id nao corresponde ao run_id.' }
    $report.first_request = $true

    & docker compose @projectArgs stop database
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar o banco isolado para a prova de recuperacao.' }
    Start-Sleep -Seconds 2
    & docker compose @projectArgs up -d --wait --wait-timeout 90 database
    if ($LASTEXITCODE -ne 0) { throw 'Banco isolado nao recuperou prontidao apos reinicio.' }
    $report.database_restart = $true
    & $pythonPath -m gov_erp.migrate
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas migrations apos reiniciar PostgreSQL.' }
    & $pythonPath -m gov_erp.seed
    if ($LASTEXITCODE -ne 0) { throw 'Falha no seed isolado apos reiniciar PostgreSQL.' }

    $readyAfterRestart = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/health/ready' -TimeoutSec 2
            if ($health.database -eq 'ready') { $readyAfterRestart = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $readyAfterRestart) { throw 'A API nao recuperou prontidao depois da reinicializacao do PostgreSQL.' }

    $web = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $login = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/auth/login' -Method Post -WebSession $web -ContentType 'application/json' -Body '{"email":"gestor@demo.pr.gov.br","password":"Local-Demo-Only-2026!","municipality_id":"4106902"}'
    $headers = @{ 'x-csrf-token' = $login.csrf_token }
    $afterResponse = Invoke-WebRequest -Uri 'http://127.0.0.1:8002/api/assistant' -Method Post -WebSession $web -Headers $headers -ContentType 'application/json' -Body $assistantBody -UseBasicParsing
    $afterHeaders = $afterResponse.Headers
    $after = ConvertFrom-Json $afterResponse.Content
    if ($after.run_id -ne $afterHeaders['X-Request-ID']) { throw 'A correlacao nao foi preservada apos reinicializar o banco.' }
    $report.request_after_restart = $true
} finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
    $report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'recovery-report.json') -Encoding utf8
}

Write-Host 'Recuperacao da API apos reinicio do PostgreSQL isolado: aprovada.'
