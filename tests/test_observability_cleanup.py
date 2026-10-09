import runpy
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

cleanup_services = runpy.run_path(
    Path(__file__).resolve().parents[1] / "scripts/observability_cleanup.py"
)["cleanup_services"]


def test_failed_compose_cleanup_invalidates_success(monkeypatch, tmp_path):
    config = tmp_path / "compose.json"
    config.touch()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    report = {"status": "passed"}
    cleanup_services(None, [], ["docker", "compose"], config, report)
    assert report["status"] == "failed"
    assert report["cleanup_exit_code"] == 1


def test_api_wait_failure_still_cleans_compose_and_closes_logs(monkeypatch, tmp_path):
    config = tmp_path / "compose.json"
    config.touch()
    process = Mock(pid=123)
    process.wait.side_effect = subprocess.TimeoutExpired("owned-api", 20)
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    handle = Mock()
    report = {"status": "passed"}
    cleanup_services(process, [handle], ["docker", "compose"], config, report)
    handle.close.assert_called_once()
    assert any("down" in args for args in commands)
    assert report["cleanup_exit_code"] == 0
    assert report["status"] == "failed"
