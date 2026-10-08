$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
$runtime = Join-Path $repo '.runtime'
$names = @('GOVERP_OTEL_ENABLED', 'OTEL_EXPORTER_OTLP_PROTOCOL', 'OTEL_EXPORTER_OTLP_ENDPOINT', 'LANGSMITH_TRACING')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$api = $null
$report = [ordered]@{ measured_at_utc = [DateTime]::UtcNow.ToString('o'); api_request = $false; prometheus_metric = $false; loki_log = $false; tempo_trace = $false }
try {
    $env:GOVERP_OTEL_ENABLED = 'true'
    $env:OTEL_EXPORTER_OTLP_PROTOCOL = 'http/protobuf'
    $env:OTEL_EXPORTER_OTLP_ENDPOINT = 'http://127.0.0.1:4318'
    $env:LANGSMITH_TRACING = 'false'
    $api = Start-Process -FilePath (Join-Path $repo '.venv\Scripts\python.exe') -ArgumentList @('-m', 'uvicorn', 'gov_erp.api:app', '--app-dir', 'src', '--host', '127.0.0.1', '--port', '8002', '--no-access-log') -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'observability-api.stdout.log') -RedirectStandardError (Join-Path $runtime 'observability-api.stderr.log')

    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/health/ready' -TimeoutSec 2
            if ($health.database -eq 'ready') { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'API instrumentada nao iniciou; banco funcional ou perfil OTLP indisponivel.' }

    $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8002/api/public/municipalities' -TimeoutSec 5 -UseBasicParsing
    $headers = $response.Headers
    $municipalities = ConvertFrom-Json $response.Content
    if (@($municipalities).Count -lt 1 -or -not $headers['X-Request-ID']) { throw 'A chamada sintética nao retornou dados e request_id.' }
    $report.api_request = $true

    $deadline = [DateTime]::UtcNow.AddSeconds(35)
    while ([DateTime]::UtcNow -lt $deadline -and -not ($report.prometheus_metric -and $report.loki_log -and $report.tempo_trace)) {
        try {
            $metrics = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/query?query=goverp_http_requests_total' -TimeoutSec 3
            $report.prometheus_metric = @($metrics.data.result).Count -gt 0
        } catch { }
        try {
            $logQuery = [Uri]::EscapeDataString('{service_name="goverp-api"}')
            $logs = Invoke-RestMethod -Uri "http://127.0.0.1:3100/loki/api/v1/query_range?query=$logQuery&limit=20" -TimeoutSec 3
            $report.loki_log = @($logs.data.result).Count -gt 0
        } catch { }
        try {
            $traceQuery = [Uri]::EscapeDataString('service.name=goverp-api')
            $traces = Invoke-RestMethod -Uri "http://127.0.0.1:3200/api/search?tags=$traceQuery&limit=10" -TimeoutSec 3
            $report.tempo_trace = @($traces.traces).Count -gt 0
        } catch { }
        if (-not ($report.prometheus_metric -and $report.loki_log -and $report.tempo_trace)) { Start-Sleep -Seconds 2 }
    }
    $report.request_id = $headers['X-Request-ID']
    if (-not ($report.prometheus_metric -and $report.loki_log -and $report.tempo_trace)) { throw 'Um ou mais sinais nao chegaram aos destinos locais.' }
} finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
    $report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'observability-report.json') -Encoding utf8
}

Write-Host 'OpenTelemetry local validado: metricas Prometheus, logs Loki e traces Tempo.'
