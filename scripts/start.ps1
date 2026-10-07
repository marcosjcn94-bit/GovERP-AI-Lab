$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
if (-not (Test-Path '.env')) { throw 'Execute scripts/bootstrap.ps1 primeiro.' }
docker compose up -d database
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL indisponível.' }
$runtime = Join-Path $repo '.runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$api = Start-Process -FilePath '.\.venv\Scripts\python.exe' -ArgumentList @('-m', 'uvicorn', 'gov_erp.api:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'api.stdout.log') -RedirectStandardError (Join-Path $runtime 'api.stderr.log')
$node = (Get-Command 'node.exe').Source
$vite = Join-Path $repo 'frontend/node_modules/vite/bin/vite.js'
$ui = Start-Process -FilePath $node -ArgumentList @($vite, '--host', '127.0.0.1') -WorkingDirectory (Join-Path $repo 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'ui.stdout.log') -RedirectStandardError (Join-Path $runtime 'ui.stderr.log')
try {
    $apiReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health/ready' -TimeoutSec 2
            if ($health.database -eq 'ready') { $apiReady = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $apiReady) { throw 'API não ficou pronta; consulte .runtime/api.stderr.log.' }
    $uiReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        & curl.exe --silent --fail --output NUL --max-time 2 'http://127.0.0.1:5173'
        if ($LASTEXITCODE -eq 0) { $uiReady = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $uiReady) { throw 'Interface não ficou pronta; consulte .runtime/ui.stderr.log.' }
    $apiWorker = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $api.Id -and $_.CommandLine -like '*gov_erp.api:app*' } | Select-Object -First 1
    @{
        api_launcher_pid = $api.Id
        api_worker_pid = if ($apiWorker) { $apiWorker.ProcessId } else { $api.Id }
        ui_pid = $ui.Id
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'processes.json') -Encoding utf8
    Start-Process -FilePath 'http://127.0.0.1:5173' | Out-Null
    Write-Host 'API em http://127.0.0.1:8000 e interface em http://127.0.0.1:5173.'
} catch {
    Stop-Process -Id $api.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $ui.Id -ErrorAction SilentlyContinue
    throw
}
