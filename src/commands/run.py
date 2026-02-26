"""doscc run - run a built program via XT."""

import sys
from pathlib import Path

from config import load_global_config, load_project_config, find_project_root


# Output extensions by target type
TARGET_EXTENSIONS = {
    "dos-exe": ".EXE",
    "dos-com": ".COM",
    "hp95lx": ".EXM",
    "hp200lx": ".EXM",
    "win16": ".EXE",
}


def run(args: list[str]) -> int:
    global_cfg = load_global_config()

    # Find project
    project_root = find_project_root()

    if args:
        # Run a specific program
        program = args[0]
        extra_args = " ".join(args[1:])
    elif project_root:
        # Run the project's output
        project_cfg = load_project_config(project_root)
        ext = TARGET_EXTENSIONS.get(project_cfg.target, ".EXE")
        program = project_cfg.name.upper() + ext
        output_dir = project_root / project_cfg.output_dir
        program_path = output_dir / program
        if not program_path.exists():
            print(f"error: {program} not found (run 'doscc build' first)",
                  file=sys.stderr)
            return 1
        extra_args = " ".join(args)
    else:
        print("error: no doscc.toml found and no program specified",
              file=sys.stderr)
        print("usage: doscc run [program] [args...]", file=sys.stderr)
        return 1

    import subprocess
    cmd = [global_cfg.xt_path, "run"]
    if project_root:
        output_dir = project_root / (load_project_config(project_root).output_dir
                                      if project_root else ".")
        cmd.extend(["-c", str(output_dir)])
    cmd.append(program)
    if extra_args:
        cmd.append(extra_args)

    result = subprocess.run(cmd)
    return result.returncode
