from pathlib import Path
import sys

from _project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(sys.argv[1] if len(sys.argv) > 1 else None)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.display_rewrite import run_display_rewrite

if __name__ == '__main__':
    out = run_display_rewrite(PROJECT_ROOT)
    print(out)
