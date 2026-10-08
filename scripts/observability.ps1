param([ValidateSet('up', 'down')][string]$Action = 'up')

$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
if (-not (Test-Path '.env')) { throw 'Execute scripts/bootstrap.ps1 primeiro.' }
$services = @('otel-collector', 'prometheus', 'grafana', 'tempo', 'loki', 'blackbox-exporter')
if ($Action -eq 'up') {
    & docker compose --profile observability up -d --wait --wait-timeout 90 @services
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar observabilidade; revise docker compose --profile observability logs.' }
    Write-Host 'Grafana: http://127.0.0.1:3000 · Prometheus: http://127.0.0.1:9090'
    Write-Host 'Inicie/reinicie a API com .\scripts\start.ps1 -EnableObservability para habilitar a exportacao local.'
} else {
    & docker compose --profile observability stop @services
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar a stack de observabilidade.' }
}
