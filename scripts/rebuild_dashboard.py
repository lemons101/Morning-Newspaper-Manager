from pathlib import Path
import sys

from _project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(sys.argv[1] if len(sys.argv) > 1 else None)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.static_html import write_static_dashboard


def main() -> int:
    runtime = PROJECT_ROOT / 'runtime'
    out = runtime / 'dashboard.html'
    result = write_static_dashboard(runtime, out)
    print(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
