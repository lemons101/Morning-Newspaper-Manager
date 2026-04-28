from __future__ import annotations

from pathlib import Path
import sys


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
    from src.pipeline.collect import main as collect_main

    collect_main()


if __name__ == "__main__":
    main()

