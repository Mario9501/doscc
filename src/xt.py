"""XT DOS emulator subprocess runner."""

import subprocess
import sys
from pathlib import Path
from typing import Optional


class BuildError(Exception):
    """Raised when an XT-invoked tool fails."""
    def __init__(self, tool: str, exit_code: int, output: str = ""):
        self.tool = tool
        self.exit_code = exit_code
        self.output = output
        super().__init__(f"{tool} failed with exit code {exit_code}")


class XTRunner:
    """Runs DOS programs via the XT emulator."""

    def __init__(self, xt_path: str, build_dir: Path, verbose: bool = False):
        self.xt_path = xt_path
        self.build_dir = build_dir
        self.verbose = verbose
        # Default DOS environment variables for all invocations
        self.default_env: dict[str, str] = {
            "LIB": "C:\\LIB",
            "INCLUDE": "C:\\INCLUDE",
            "PATH": "C:\\;C:\\BIN",
        }

    def run(self, program: str, args: str = "",
            env_vars: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
        """Run a DOS program via XT. Returns CompletedProcess."""
        cmd = [self.xt_path, "run", "-c", str(self.build_dir), program]
        if args:
            cmd.append(args)

        import os
        merged = dict(self.default_env)
        if env_vars:
            merged.update(env_vars)
        env = os.environ.copy()
        for k, v in merged.items():
            env[f"XT_DOS_ENV_{k}"] = v

        if self.verbose:
            dos_cmd = f"{program} {args}".strip()
            print(f"  > {dos_cmd}", file=sys.stderr)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
        )

        if self.verbose and result.stdout:
            for line in result.stdout.rstrip().split("\n"):
                print(f"    {line}", file=sys.stderr)
        if self.verbose and result.stderr:
            for line in result.stderr.rstrip().split("\n"):
                print(f"    {line}", file=sys.stderr)

        return result

    def run_checked(self, program: str, args: str = "",
                    env_vars: Optional[dict[str, str]] = None,
                    tool_name: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a DOS program and raise BuildError on failure."""
        result = self.run(program, args, env_vars)
        if result.returncode != 0:
            name = tool_name or program
            output = (result.stdout + result.stderr).strip()
            raise BuildError(name, result.returncode, output)
        return result
