from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time
from typing import Any, Dict
from urllib.error import URLError
from urllib.request import urlopen


@dataclass
class DashboardServerResult:
    status: str
    url: str
    port: int
    started: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "url": self.url,
            "port": self.port,
            "started": self.started,
            "message": self.message,
        }


def ensure_dashboard_server(root: Path, app_config: Dict[str, Any]) -> DashboardServerResult:
    dashboard_cfg = app_config.get("dashboard", {})
    if not isinstance(dashboard_cfg, dict) or not dashboard_cfg.get("enabled", True):
        return DashboardServerResult("disabled", "", 0, False, "看板已在配置中关闭。")

    host = str(dashboard_cfg.get("host", "127.0.0.1")).strip() or "127.0.0.1"
    base_port = int(dashboard_cfg.get("port", 8502))
    port_search_limit = max(1, int(dashboard_cfg.get("port_search_limit", 10)))
    startup_timeout = max(3, int(dashboard_cfg.get("startup_timeout_seconds", 25)))
    app_file = str(dashboard_cfg.get("app_file", "dashboard_app.py")).strip() or "dashboard_app.py"

    port = _find_available_or_live_port(host, base_port, port_search_limit)
    url = f"http://{host}:{port}"
    if _url_ready(url):
        return DashboardServerResult("ok", url, port, False, "看板已经在运行。")

    log_dir = root / "runtime"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "dashboard_server.log"
    stderr_path = log_dir / "dashboard_server.err.log"
    app_path = root / app_file

    command = [
        sys.executable,
        "-B",
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.address={host}",
        f"--server.port={port}",
        "--server.headless=true",
    ]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(root) if not existing_pythonpath else str(root) + os.pathsep + existing_pythonpath

    with stdout_path.open("a", encoding="utf-8") as stdout, stderr_path.open("a", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=_creation_flags(),
            env=env,
        )

    if _wait_for_url(url, timeout_seconds=startup_timeout):
        time.sleep(1.5)
        if process.poll() is not None:
            return DashboardServerResult(
                "error",
                url,
                port,
                False,
                "动态看板启动后退出，静态 HTML 看板仍可使用。",
            )
        _write_server_state(root, url=url, port=port, pid=process.pid)
        return DashboardServerResult("ok", url, port, True, "动态看板已启动。")

    return DashboardServerResult(
        "error",
        url,
        port,
        False,
        f"动态看板在 {startup_timeout} 秒内未就绪，请查看 runtime/dashboard_server.err.log。",
    )


def _find_available_or_live_port(host: str, base_port: int, limit: int) -> int:
    for offset in range(limit):
        port = base_port + offset
        if _url_ready(f"http://{host}:{port}"):
            return port
        if _port_available(host, port):
            return port
    return base_port + limit


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def _url_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=1.0) as response:
            return response.status < 500
    except Exception:
        return False


def _wait_for_url(url: str, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _url_ready(url):
            return True
        time.sleep(0.5)
    return False


def _write_server_state(root: Path, *, url: str, port: int, pid: int) -> None:
    payload = {
        "url": url,
        "port": port,
        "pid": pid,
        "started_at": time.time(),
    }
    path = root / "runtime" / "dashboard_server.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _creation_flags() -> int:
    if os.name == "nt":
        return subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    return 0
