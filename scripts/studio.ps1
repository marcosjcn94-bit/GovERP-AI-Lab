param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Pre-requisito ausente: uv. Consulte o README.'
}
$studioArgs = @('run', '--project', 'studio', '--locked', '--managed-python', 'langgraph', 'dev', '--config', 'langgraph.json', '--host', '127.0.0.1', '--port', '2024')
if ($NoBrowser) { $studioArgs += '--no-browser' }
$previousUtf8 = $env:PYTHONUTF8
$previousAnalytics = $env:LANGGRAPH_CLI_NO_ANALYTICS
$traceNames = @('LANGSMITH_API_KEY', 'LANGSMITH_ENDPOINT', 'LANGSMITH_PROJECT', 'LANGSMITH_TRACING', 'LANGSMITH_HIDE_INPUTS', 'LANGSMITH_HIDE_OUTPUTS', 'LANGSMITH_HIDE_METADATA')
$tracePrevious = @{}
try {
    $localEnv = Get-Content -LiteralPath '.env' -Raw
    foreach ($name in $traceNames) {
        $tracePrevious[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        $match = [regex]::Match($localEnv, "(?m)^\s*$name\s*=\s*(.*?)\s*$")
        if ($match.Success -and $match.Groups[1].Value) {
            $value = $match.Groups[1].Value.Trim('"', "'")
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
    $env:PYTHONUTF8 = '1'
    $env:LANGGRAPH_CLI_NO_ANALYTICS = '1'
    & uv @studioArgs
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao executar o LangGraph Studio local.' }
} finally {
    $env:PYTHONUTF8 = $previousUtf8
    $env:LANGGRAPH_CLI_NO_ANALYTICS = $previousAnalytics
    foreach ($name in $traceNames) { [Environment]::SetEnvironmentVariable($name, $tracePrevious[$name], 'Process') }
}
