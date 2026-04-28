from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_import_path(root: Path) -> None:
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def _run_collection(root: Path) -> None:
    command = [
        sys.executable,
        "-B",
        str(root / "src" / "pipeline" / "collect.py"),
        "--project-root",
        str(root),
    ]
    completed = subprocess.run(
        command,
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip(), file=sys.stderr)
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"Collection pipeline failed with exit code {completed.returncode}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行信息采集流程，并返回可视化看板链接。")
    parser.add_argument("--project-root", default=str(_project_root()))
    parser.add_argument("--no-dashboard", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    root = Path(args.project_root).resolve()
    _ensure_import_path(root)

    from src.config import load_project_config
    from src.dashboard.server import ensure_dashboard_server
    from src.dashboard.static_html import write_static_dashboard
    from src.dashboard.view_model import build_dashboard_payload

    config = load_project_config(root)
    _run_collection(root)
    dashboard_cfg = config["app"].get("dashboard", {})
    runtime_cfg = config["app"].get("runtime", {})
    runtime_dir = root / str(runtime_cfg.get("output_dir", "runtime"))
    static_name = "dashboard.html"
    if isinstance(dashboard_cfg, dict):
        static_name = str(dashboard_cfg.get("static_file", "dashboard.html"))
    static_path = write_static_dashboard(runtime_dir, runtime_dir / static_name)
    dashboard = None
    if not args.no_dashboard:
        dashboard = ensure_dashboard_server(root, config["app"])

    payload = build_dashboard_payload(runtime_dir)
    overview: Dict[str, Any] = payload.get("overview", {})
    result = {
        "status": "ok" if dashboard is None or dashboard.status == "ok" else "partial",
        "message": "信息采集和看板生成完成。" if dashboard is None or dashboard.status == "ok" else "信息采集完成，但动态看板启动不稳定，请优先使用静态 HTML 看板。",
        "dashboard_url": dashboard.url if dashboard is not None else "",
        "dashboard_file": str(static_path),
        "dashboard_file_url": static_path.resolve().as_uri(),
        "dashboard": dashboard.to_dict() if dashboard is not None else {"status": "skipped"},
        "overview": {
            "collected_total": overview.get("collected_total", 0),
            "candidate_count": overview.get("candidate_count", 0),
            "top10_count": overview.get("top10_count", 0),
            "ai_selected": overview.get("ai_selected", False),
            "urgent_count": overview.get("urgent_count", 0),
            "important_count": overview.get("important_count", 0),
            "mail_alert_count": overview.get("mail_alert_count", 0),
            "urgent_mail_count": overview.get("urgent_mail_count", 0),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
