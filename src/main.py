#!/usr/bin/env python3
"""doscc - DOS cross-compiler CLI tool.

Wraps XT DOS emulator + MS C 5.0 into a modern build system.
"""

import sys
from pathlib import Path

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent))

USAGE = """\
doscc - DOS cross-compiler CLI

usage: doscc <command> [options]

commands:
  build       Compile and link the project
  clean       Remove build artifacts
  setup       Interactive configuration wizard
  init        Create a new project from template
  run         Run a built program via XT
  info        Display configuration and project info
  toolchain   Manage toolchain configurations
  lib         Manage pre-built libraries

options:
  -v, --verbose   Show detailed build output
  -h, --help      Show this help message

run 'doscc <command> --help' for command-specific help
"""

COMMANDS = {
    "build": "commands.build",
    "clean": "commands.clean",
    "setup": "commands.setup",
    "init": "commands.init",
    "run": "commands.run",
    "info": "commands.info",
    "toolchain": "commands.toolchain",
    "lib": "commands.lib",
}


def main() -> int:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0

    cmd = args[0]
    cmd_args = args[1:]

    if cmd not in COMMANDS:
        print(f"error: unknown command '{cmd}'", file=sys.stderr)
        print(f"run 'doscc --help' for usage", file=sys.stderr)
        return 1

    # Import and run the command module
    import importlib
    module = importlib.import_module(COMMANDS[cmd])
    return module.run(cmd_args)


if __name__ == "__main__":
    sys.exit(main())
