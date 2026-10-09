from __future__ import annotations

import logging
import os
from typing import Any

_providers: list[Any] = []
_request_counter: Any = None
_request_duration: Any = None
_model_outcomes: Any = None
_audit_runs: Any = None
_audit_findings: Any = None


def redact_request(span: Any, scope: dict[str, Any]) -> None:
    if span and span.is_recording():
        path = scope.get("path", "/")
        for key in ("http.url", "http.target", "url.full", "url.path"):
            span.set_attribute(key, path)
        span.set_attribute("url.query", "[REDACTED]")


def configure_observability(app: Any) -> bool:
    """Enable bounded, content-free OTLP export only when explicitly requested."""
    if os.getenv("GOVERP_OTEL_ENABLED", "false").casefold() != "true":
        return False

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": "goverp-api", "deployment.environment": "local"})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(), export_interval_millis=10_000
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = meter_provider.get_meter("goverp-api")
    global _request_counter, _request_duration, _model_outcomes, _audit_runs, _audit_findings
    _request_counter = meter.create_counter("goverp.http.requests", unit="{request}")
    _request_duration = meter.create_histogram("goverp.http.request.duration", unit="s")
    _model_outcomes = meter.create_counter("goverp.model.explanations", unit="{request}")
    _audit_runs = meter.create_counter("goverp.audit.runs", unit="{run}")
    _audit_findings = meter.create_counter("goverp.audit.findings", unit="{finding}")

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    request_logger = logging.getLogger("gov_erp.api")
    request_logger.setLevel(logging.INFO)
    request_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))
    LoggingInstrumentor().instrument(set_logging_format=False)

    FastAPIInstrumentor.instrument_app(
        app,
        server_request_hook=redact_request,
        excluded_urls=r"/health/(live|ready)",
        http_capture_headers_sanitize_fields=[r".*"],
        exclude_spans=["receive", "send"],
    )
    # SQL/client exception events can contain statements, DSNs or query strings.
    # Keep only content-free server spans and explicitly authored application signals.
    _providers.extend([tracer_provider, meter_provider, logger_provider])
    return True


def record_http_request(method: str, route: str, status: int, duration_seconds: float) -> None:
    if _request_counter is None or _request_duration is None:
        return
    attributes = {"http_method": method, "http_route": route, "http_status_code": str(status)}
    _request_counter.add(1, attributes)
    _request_duration.record(max(duration_seconds, 0), attributes)


def record_model_outcome(fallback: bool) -> None:
    if _model_outcomes is not None:
        _model_outcomes.add(1, {"fallback": str(fallback).lower()})


def record_audit_run(possible_duplicates: int) -> None:
    if _audit_runs is not None:
        _audit_runs.add(1)
        _audit_findings.add(max(possible_duplicates, 0))
