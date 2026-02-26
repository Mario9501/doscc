"""doscc build - compile and link a DOS project."""

import sys
import time
from pathlib import Path

from config import load_global_config, load_project_config, find_project_root
from workspace import Workspace
from xt import XTRunner, BuildError
from targets import create_target


def run(args: list[str]) -> int:
    verbose = "-v" in args or "--verbose" in args

    # Find project
    project_root = find_project_root()
    if project_root is None:
        print("error: no doscc.toml found (searched up to filesystem root)",
              file=sys.stderr)
        return 1

    # Load configs
    global_cfg = load_global_config()
    project_cfg = load_project_config(project_root)

    if verbose:
        print(f"project: {project_cfg.name} ({project_cfg.target})")
        print(f"root:    {project_root}")

    # Validate toolchain exists
    if project_cfg.toolchain not in global_cfg.toolchains:
        print(f"error: toolchain '{project_cfg.toolchain}' not found in global config",
              file=sys.stderr)
        print(f"run 'doscc setup' to configure toolchains", file=sys.stderr)
        return 1

    # Validate SDK if needed
    if project_cfg.sdk and project_cfg.sdk not in global_cfg.sdks:
        print(f"error: SDK '{project_cfg.sdk}' not found in global config",
              file=sys.stderr)
        print(f"run 'doscc setup' to configure SDKs", file=sys.stderr)
        return 1

    # Prepare workspace
    start = time.time()
    ws = Workspace(project_root, project_cfg, global_cfg)
    sources = ws.prepare()

    if not sources:
        print("error: no source files found", file=sys.stderr)
        return 1

    if verbose:
        print(f"sources: {len(sources)} file(s)")
        for s in sources:
            print(f"  {s.host_path.name}")
        print()

    # Build
    runner = XTRunner(global_cfg.xt_path, ws.build_dir, verbose=verbose)
    target = create_target(project_cfg, runner, ws.build_dir)

    try:
        output = target.build(sources, project_root)
        ws.cleanup()
        elapsed = time.time() - start
        print(f"built {output.name} ({elapsed:.1f}s)")
        return 0
    except BuildError as e:
        print(f"\nerror: {e}", file=sys.stderr)
        if e.output:
            print(e.output, file=sys.stderr)
        return 1
