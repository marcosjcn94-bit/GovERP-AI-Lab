"""Temporary services only: correlation, database fault, alert firing and recovery."""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
from observability_cleanup import cleanup_services

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
PROJECT = "goverp-observe-" + uuid.uuid4().hex[:12]
API, PROM, LOKI, TEMPO = [f"http://127.0.0.1:{port}" for port in (18002, 19090, 13100, 13200)]
CANARY = "GOVERP_PRIVATE_CANARY_9fd836"


def command(args, env=None):
    subprocess.run(args, cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)


def wait_until(check, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (httpx.HTTPError, KeyError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("Isolated smoke condition timed out")


def get(url):
    response = httpx.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def alert_firing():
    return any(
        item["labels"].get("alertname") == "GovERPApiUnavailable" and item["state"] == "firing"
        for item in get(PROM + "/api/v1/alerts")["data"]["alerts"]
    )


def main():
    RUNTIME.mkdir(exist_ok=True)
    report = {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "project": PROJECT,
        "status": "failed",
    }
    env = dict(
        os.environ,
        GOVERP_OWNER_DATABASE_URL="postgresql+psycopg://goverp_owner:test-owner-only@127.0.0.1:15441/goverp_e2e",
        GOVERP_APP_DATABASE_URL="postgresql+psycopg://goverp_app:test-app-only@127.0.0.1:15441/goverp_e2e",
        GOVERP_SESSION_SECRET="isolated-observe-secret-at-least-32-bytes",
        GOVERP_MODEL_ENABLED="false",
        GOVERP_OTEL_ENABLED="true",
        OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:14318",
        LANGSMITH_TRACING="false",
    )
    api_process, logs = None, []
    config_path = RUNTIME / f"{PROJECT}.json"
    compose = ["docker", "compose", "-f", str(config_path), "-p", PROJECT]
    try:

        def compose_config(extra):
            return json.loads(
                subprocess.check_output(
                    [
                        "docker",
                        "compose",
                        "--env-file",
                        ".env.example",
                        *extra,
                        "config",
                        "--format",
                        "json",
                    ],
                    cwd=ROOT,
                    env=dict(env, GOVERP_GRAFANA_PASSWORD="unused-isolated-grafana"),
                )
            )

        base = compose_config(["--profile", "observability"])
        database = compose_config(["-f", "docker-compose.e2e.yml"])["services"]["database"]
        names = ["otel-collector", "prometheus", "blackbox-exporter", "tempo", "loki"]
        services = {name: base["services"][name] for name in names}
        services["database"] = database
        ports = {
            "otel-collector": {4318: 14318, 9464: 19464, 4317: 14317, 13133: 23133},
            "prometheus": {9090: 19090},
            "loki": {3100: 13100},
            "tempo": {3200: 13200},
            "database": {5432: 15441},
        }
        for name, service in services.items():
            service.pop("profiles", None)
            for port in service.get("ports", []):
                port["published"] = str(ports[name][port["target"]])
        prom_path = RUNTIME / f"{PROJECT}-prometheus.yml"
        prom_path.write_text(
            (ROOT / "docker/observability/prometheus/prometheus.yml")
            .read_text(encoding="utf-8")
            .replace(":8000/health/ready", ":18002/health/ready"),
            encoding="utf-8",
        )
        for volume in services["prometheus"]["volumes"]:
            if volume["target"] == "/etc/prometheus/prometheus.yml":
                volume["source"] = str(prom_path)
        config_path.write_text(json.dumps({"services": services}), encoding="utf-8")
        command(compose + ["up", "-d", "--wait", "--wait-timeout", "120"], env)
        for module in ("gov_erp.migrate", "gov_erp.seed"):
            command([sys.executable, "-m", module], env)
        for suffix in ("stdout", "stderr"):
            logs.append((RUNTIME / f"observability-api.{suffix}.log").open("w", encoding="utf-8"))
        api_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "gov_erp.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                "18002",
                "--no-access-log",
            ],
            cwd=ROOT,
            env=env,
            stdout=logs[0],
            stderr=logs[1],
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        wait_until(lambda: get(API + "/health/ready").get("database") == "ready")
        with httpx.Client(base_url=API, timeout=10) as client:
            login = client.post(
                "/api/auth/login",
                json={
                    "email": "gestor@demo.pr.gov.br",
                    "password": "Local-Demo-Only-2026!",
                    "municipality_id": "4106902",
                },
            )
            login.raise_for_status()
            response = client.post(
                "/api/assistant?canary=" + CANARY,
                headers={"x-csrf-token": login.json()["csrf_token"]},
                json={"question": "auditoria sintetica"},
            )
            response.raise_for_status()
        request_id = response.headers["x-request-id"]
        assert response.json()["run_id"] == request_id
        query = urlencode(
            {"query": '{service_name="goverp-api"} | request_id="' + request_id + '"', "limit": 10}
        )
        signals = wait_until(
            lambda: get(LOKI + "/loki/api/v1/query_range?" + query)["data"]["result"]
        )
        metadata = [
            {**stream["stream"], **(value[2] if len(value) > 2 else {})}
            for stream in signals
            for value in stream["values"]
        ]
        report["signal_keys"] = [sorted(item) for item in metadata]
        same_run = next(
            item
            for item in metadata
            if item.get("request_id") == request_id and item.get("run_id") == request_id
        )
        trace_id = same_run["trace_id"]
        trace_data = wait_until(lambda: get(TEMPO + "/api/traces/" + trace_id))
        serialized = json.dumps(trace_data)
        assert request_id in serialized and "goverp.run_id" in serialized
        metric_query = urlencode(
            {
                "query": 'goverp_http_requests_total{http_route="/api/assistant",http_status_code="200"}'
            }
        )
        wait_until(lambda: get(PROM + "/api/v1/query?" + metric_query)["data"]["result"])
        assert CANARY not in serialized and CANARY not in json.dumps(signals)
        report.update(
            request_id=request_id,
            run_id=request_id,
            trace_id=trace_id,
            correlated=True,
            metric=True,
            content_scan=True,
        )
        command(compose + ["stop", "database"], env)
        failed_at = time.monotonic()
        failure = httpx.get(API + "/api/public/municipalities", timeout=15)
        assert failure.status_code == 503 and failure.json() == {
            "detail": "Banco local indisponivel"
        }
        report["database_503"] = True
        report["database_failure_seconds"] = round(time.monotonic() - failed_at, 3)
        failure_query = urlencode(
            {
                "query": 'goverp_http_requests_total{http_route="/api/public/municipalities",http_status_code="503"}'
            }
        )
        wait_until(lambda: get(PROM + "/api/v1/query?" + failure_query)["data"]["result"])
        print("Correlacao e 503 confirmados; aguardando alerta com for: 2m.", flush=True)
        wait_until(alert_firing, timeout=210)
        report["alert_firing"] = True
        command(compose + ["up", "-d", "--wait", "--wait-timeout", "90", "database"], env)
        for module in ("gov_erp.migrate", "gov_erp.seed"):
            command([sys.executable, "-m", module], env)
        wait_until(lambda: get(API + "/health/ready").get("database") == "ready")
        wait_until(lambda: not alert_firing())
        report.update(alert_resolved=True, recovered=True, status="passed")
    finally:
        cleanup_services(api_process, logs, compose, config_path, report)
        (RUNTIME / "observability-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    if report["status"] != "passed":
        raise RuntimeError("Isolated smoke cleanup failed; see observability-report.json")
    print("Observabilidade isolada aprovada.")


if __name__ == "__main__":
    main()
