param()
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$npmCommand = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { 'npm.cmd' } else { 'npm' }
foreach ($command in @('uv', 'node', $npmCommand)) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Pre-requisito ausente: $command. Consulte o README." }
}
Push-Location $repo
$results = @()
$runtime = Join-Path $repo '.runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$steps = @(
    @{ Name = 'lint'; Command = 'uv'; Arguments = @('run', '--locked', '--extra', 'dev', '--managed-python', 'ruff', 'check', 'src', 'tests') }
    @{ Name = 'format'; Command = 'uv'; Arguments = @('run', '--locked', '--extra', 'dev', '--managed-python', 'ruff', 'format', '--check', 'src', 'tests') }
    @{ Name = 'tests'; Command = 'uv'; Arguments = @('run', '--locked', '--extra', 'dev', '--managed-python', 'pytest', '-q') }
    @{ Name = 'build'; Command = $npmCommand; Arguments = @('--prefix', 'frontend', 'run', 'build') }
)
try {
    foreach ($step in $steps) {
        $timer = [Diagnostics.Stopwatch]::StartNew()
        & $step.Command @($step.Arguments)
        $code = $LASTEXITCODE
        $timer.Stop()
        $results += @{ check = $step.Name; exit_code = $code; seconds = [Math]::Round($timer.Elapsed.TotalSeconds, 3) }
        if ($code -ne 0) { throw "Check $($step.Name) falhou (exit $code)." }
    }
    Write-Host 'Checks locais concluidos.'
} finally {
    @{ measured_at_utc = [DateTime]::UtcNow.ToString('o'); checks = $results } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $runtime 'check-report.json') -Encoding utf8
    Pop-Location
}