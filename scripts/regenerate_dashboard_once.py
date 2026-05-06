from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/root/projects/Morning-Newspaper-Manager')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.newspaper_writer import run_newspaper_writer
from src.dashboard.static_html import write_static_dashboard

run_newspaper_writer(ROOT)
path = write_static_dashboard(ROOT / 'runtime', ROOT / 'runtime' / 'dashboard.html')
print(path)
