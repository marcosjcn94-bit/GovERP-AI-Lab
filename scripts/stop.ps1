$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
$manifestPath = Join-Path $repo '.runtime/processes.json'
if (-not (Test-Path $manifestPath)) { throw 'Manifesto de processos nao encontrado em .runtime/processes.json.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$apiWorker = Get-CimInstance Win32_Process -Filter "ProcessId = $($manifest.api_worker_pid)" -ErrorAction SilentlyContinue
if ($apiWorker -and $apiWorker.CommandLine -like '*gov_erp.api:app*' -and $apiWorker.CommandLine -like '*--port 8000*') {
    Stop-Process -Id $apiWorker.ProcessId -Force -ErrorAction SilentlyContinue
}
$apiLauncher = Get-CimInstance Win32_Process -Filter "ProcessId = $($manifest.api_launcher_pid)" -ErrorAction SilentlyContinue
if ($apiLauncher -and $apiLauncher.CommandLine -like '*gov_erp.api:app*' -and $apiLauncher.CommandLine -like '*--port 8000*') {
    Stop-Process -Id $apiLauncher.ProcessId -Force -ErrorAction SilentlyContinue
}
$ui = Get-CimInstance Win32_Process -Filter "ProcessId = $($manifest.ui_pid)" -ErrorAction SilentlyContinue
if ($ui -and $ui.CommandLine -like '*frontend*vite.js*' -and $ui.CommandLine -like '*--host 127.0.0.1*') {
    Stop-Process -Id $ui.ProcessId -Force -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $manifestPath -Force
Write-Host 'API e interface encerradas. O PostgreSQL continua ativo.'
