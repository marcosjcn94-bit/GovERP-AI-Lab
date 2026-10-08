$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
$npmCommand = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { 'npm.cmd' } else { 'npm' }
foreach ($command in @('uv', 'node', $npmCommand, 'docker')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Pre-requisito ausente: $command. Consulte o README." }
}
$nodeVersion = & node --version
$nodeMajor = ($nodeVersion.TrimStart('v') -split '\.')[0]
if ($LASTEXITCODE -ne 0 -or $nodeMajor -ne '24') { throw 'Use Node.js 24 LTS, conforme .node-version.' }

if (-not (Test-Path '.env')) {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $ownerBytes = New-Object byte[] 36
    $appBytes = New-Object byte[] 36
    $sessionBytes = New-Object byte[] 48
    $grafanaBytes = New-Object byte[] 36
    $rng.GetBytes($ownerBytes)
    $rng.GetBytes($appBytes)
    $rng.GetBytes($sessionBytes)
    $rng.GetBytes($grafanaBytes)
    $ownerPassword = [Convert]::ToBase64String($ownerBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $appPassword = [Convert]::ToBase64String($appBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $sessionSecret = [Convert]::ToBase64String($sessionBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $grafanaPassword = [Convert]::ToBase64String($grafanaBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $rng.Dispose()
    @(
        "GOVERP_PG_OWNER_PASSWORD=$ownerPassword"
        "GOVERP_PG_APP_PASSWORD=$appPassword"
        "GOVERP_SESSION_SECRET=$sessionSecret"
        "GOVERP_GRAFANA_PASSWORD=$grafanaPassword"
        'GOVERP_OWNER_DATABASE_URL=postgresql+psycopg://goverp_owner:REPLACE_OWNER@127.0.0.1:5440/goverp'
        'GOVERP_APP_DATABASE_URL=postgresql+psycopg://goverp_app:REPLACE_APP@127.0.0.1:5440/goverp'
        'GOVERP_MODEL_URL=http://127.0.0.1:11434'
        'GOVERP_MODEL_NAME=qwen3:4b'
        'GOVERP_ALLOWED_ORIGIN=http://127.0.0.1:5173'
    ) | Set-Content -LiteralPath '.env' -Encoding utf8
    $raw = Get-Content -LiteralPath '.env' -Raw
    $raw = $raw.Replace('REPLACE_OWNER', $ownerPassword).Replace('REPLACE_APP', $appPassword)
    [IO.File]::WriteAllText((Join-Path $repo '.env'), $raw, [Text.UTF8Encoding]::new($false))
}

if (-not [regex]::IsMatch((Get-Content -LiteralPath '.env' -Raw), '(?m)^GOVERP_GRAFANA_PASSWORD=\S+')) {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $grafanaBytes = New-Object byte[] 36
    $rng.GetBytes($grafanaBytes)
    $grafanaPassword = [Convert]::ToBase64String($grafanaBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $rng.Dispose()
    Add-Content -LiteralPath '.env' -Value "GOVERP_GRAFANA_PASSWORD=$grafanaPassword" -Encoding utf8
}

& uv sync --locked --extra dev --managed-python
if ($LASTEXITCODE -ne 0) { throw 'Falha ao sincronizar o ambiente Python pelo uv.lock.' }
& $npmCommand --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw 'Falha ao sincronizar o frontend pelo package-lock.json.' }

docker compose up -d --wait --wait-timeout 90 database
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o PostgreSQL local.' }

& '.\.venv\Scripts\python.exe' -m gov_erp.migrate
if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar as migrações locais.' }
& '.\.venv\Scripts\python.exe' -m gov_erp.seed
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar os dados demonstrativos.' }

Write-Host 'Ambiente inicializado. Use scripts/start.ps1. O ranking CLP e importado explicitamente: uv run --locked --extra dev --managed-python python -m gov_erp.rankings.'
