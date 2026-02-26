"""doscc clean - remove build artifacts."""

import shutil
import sys
from pathlib import Path

from config import find_project_root


def run(args: list[str]) -> int:
    project_root = find_project_root()
    if project_root is None:
        print("error: no doscc.toml found", file=sys.stderr)
        return 1

    build_dir = project_root / ".doscc"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("cleaned build directory")
    else:
        print("nothing to clean")

    return 0
