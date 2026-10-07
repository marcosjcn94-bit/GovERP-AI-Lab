$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo

if (-not (Test-Path '.env')) {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $ownerBytes = New-Object byte[] 36
    $appBytes = New-Object byte[] 36
    $sessionBytes = New-Object byte[] 48
    $rng.GetBytes($ownerBytes)
    $rng.GetBytes($appBytes)
    $rng.GetBytes($sessionBytes)
    $ownerPassword = [Convert]::ToBase64String($ownerBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $appPassword = [Convert]::ToBase64String($appBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $sessionSecret = [Convert]::ToBase64String($sessionBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $rng.Dispose()
    @(
        "GOVERP_PG_OWNER_PASSWORD=$ownerPassword"
        "GOVERP_PG_APP_PASSWORD=$appPassword"
        "GOVERP_SESSION_SECRET=$sessionSecret"
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

if (-not (Test-Path '.venv/Scripts/python.exe')) {
    py -m venv .venv
}
& '.\.venv\Scripts\python.exe' -m pip install --disable-pip-version-check -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o ambiente Python.' }

docker compose up -d database
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o PostgreSQL local.' }

& '.\.venv\Scripts\python.exe' -m gov_erp.migrate
if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar as migrações locais.' }
& '.\.venv\Scripts\python.exe' -m gov_erp.seed
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar os dados demonstrativos.' }
& '.\.venv\Scripts\python.exe' -m gov_erp.rankings
if ($LASTEXITCODE -ne 0) { throw 'Falha ao importar o ranking público CLP; confira a conexão e a fonte oficial.' }

Write-Host 'Ambiente inicializado. Use scripts/start.ps1 para iniciar API e interface.'
