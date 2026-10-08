$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
$names = @('LANGSMITH_API_KEY', 'LANGSMITH_ENDPOINT', 'LANGSMITH_PROJECT', 'LANGSMITH_TRACING', 'LANGSMITH_HIDE_INPUTS', 'LANGSMITH_HIDE_OUTPUTS', 'LANGSMITH_HIDE_METADATA', 'LANGCHAIN_CALLBACKS_BACKGROUND')
$previous = @{}
try {
    $localEnv = Get-Content -LiteralPath '.env' -Raw
    foreach ($name in $names) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        $match = [regex]::Match($localEnv, "(?m)^\s*$name\s*=\s*(.*?)\s*$")
        if ($match.Success -and $match.Groups[1].Value) {
            [Environment]::SetEnvironmentVariable($name, $match.Groups[1].Value.Trim('"', "'"), 'Process')
        }
    }
    $env:LANGSMITH_TRACING = 'true'
    $env:LANGSMITH_HIDE_INPUTS = 'true'
    $env:LANGSMITH_HIDE_OUTPUTS = 'true'
    $env:LANGSMITH_HIDE_METADATA = 'true'
    $env:LANGCHAIN_CALLBACKS_BACKGROUND = 'false'
    & (Join-Path $repo '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'verify-langsmith.py')
    if ($LASTEXITCODE -ne 0) { throw 'A verificacao LangSmith nao confirmou o trace sanitizado.' }
} catch {
    Write-Error ("Falha na verificacao LangSmith: " + $_.Exception.GetType().Name)
    exit 1
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
