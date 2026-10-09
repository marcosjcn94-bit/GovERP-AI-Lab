"""Stop only the processes and services owned by the isolated smoke."""

import os
import subprocess


def cleanup_services(api_process, logs, compose, config_path, report):
    errors = []
    if api_process:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(api_process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                )
            else:
                api_process.terminate()
            api_process.wait(timeout=20)
        except (OSError, subprocess.SubprocessError):
            errors.append("api_shutdown_failed")
    for handle in logs:
        try:
            handle.close()
        except OSError:
            errors.append("log_close_failed")
    if config_path.exists():
        try:
            cleanup = subprocess.run(
                compose + ["down", "--timeout", "10"],
                cwd=config_path.parents[1],
                stdout=subprocess.DEVNULL,
                check=False,
            )
            report["cleanup_exit_code"] = cleanup.returncode
            if cleanup.returncode:
                errors.append("compose_shutdown_failed")
        except (OSError, subprocess.SubprocessError):
            report["cleanup_exit_code"] = -1
            errors.append("compose_shutdown_failed")
    if errors:
        report.update(status="failed", cleanup_errors=errors)
