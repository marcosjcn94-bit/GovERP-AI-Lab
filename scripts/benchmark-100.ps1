$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo
if (-not (Test-Path '.env')) { throw 'Execute scripts/bootstrap.ps1 primeiro.' }
$python = Join-Path $repo '.venv\Scripts\python.exe'
$databaseName = 'goverp_benchmark100'

@'
from sqlalchemy.engine import make_url
import psycopg
from gov_erp.settings import settings

dsn = make_url(settings.owner_database_url).set(database="postgres", drivername="postgresql").render_as_string(hide_password=False)
with psycopg.connect(dsn, autocommit=True) as connection:
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("goverp_benchmark100",)).fetchone()
    if not exists:
        connection.execute("CREATE DATABASE goverp_benchmark100 OWNER goverp_owner")
    connection.execute("GRANT CONNECT ON DATABASE goverp_benchmark100 TO goverp_app")
'@ | & $python -
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o banco isolado do benchmark.' }

$originalOwnerUrl = $env:GOVERP_OWNER_DATABASE_URL
$originalAppUrl = $env:GOVERP_APP_DATABASE_URL
$ownerUrlLine = Get-Content -LiteralPath '.env' | Where-Object { $_.StartsWith('GOVERP_OWNER_DATABASE_URL=') } | Select-Object -First 1
$appUrlLine = Get-Content -LiteralPath '.env' | Where-Object { $_.StartsWith('GOVERP_APP_DATABASE_URL=') } | Select-Object -First 1
$ownerUrl = $ownerUrlLine.Substring('GOVERP_OWNER_DATABASE_URL='.Length)
$appUrl = $appUrlLine.Substring('GOVERP_APP_DATABASE_URL='.Length)
$env:GOVERP_OWNER_DATABASE_URL = $ownerUrl -replace '/goverp$', "/$databaseName"
$env:GOVERP_APP_DATABASE_URL = $appUrl -replace '/goverp$', "/$databaseName"
try {
    & $python -m gov_erp.migrate
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao migrar o banco isolado.' }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    & $python -m gov_erp.seed --mode benchmark-100
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar a carga do benchmark.' }
    $timer.Stop()
    $env:GOVERP_BENCHMARK_SEED_SECONDS = [string]$timer.Elapsed.TotalSeconds
    @'
import json
import os
from pathlib import Path
from datetime import UTC, datetime
from sqlalchemy import create_engine, text
from gov_erp.settings import settings

engine = create_engine(settings.owner_database_url)
with engine.connect() as connection:
    database_bytes = connection.scalar(text("SELECT pg_database_size(current_database())"))
    municipality_count = connection.scalar(text("SELECT count(*) FROM municipalities"))
    financial_rows = connection.scalar(text("SELECT count(*) FROM financial_transactions"))
    document_rows = connection.scalar(text("SELECT count(*) FROM tenant_documents"))
report_path = Path("data/benchmark-100-report.json")
previous_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
report = {
    **previous_report,
    "database": "goverp_benchmark100",
    "municipalities": municipality_count,
    "financial_rows": financial_rows,
    "documents": document_rows,
    "database_bytes": database_bytes,
    "database_megabytes": round(database_bytes / 1024 / 1024, 2),
    "measurement_scope": "gov_erp.seed only; includes IBGE fetch, synthetic generation and inserts; excludes migrations and CLP",
    "seed_seconds": round(float(os.environ["GOVERP_BENCHMARK_SEED_SECONDS"]), 2),
    "model_calls": 0,
    "measured_at_utc": datetime.now(UTC).isoformat(),
}
Path("data").mkdir(exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
'@ | & $python -
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao medir o banco do benchmark.' }
} finally {
    $env:GOVERP_OWNER_DATABASE_URL = $originalOwnerUrl
    $env:GOVERP_APP_DATABASE_URL = $originalAppUrl
    Remove-Item Env:GOVERP_BENCHMARK_SEED_SECONDS -ErrorAction SilentlyContinue
}
