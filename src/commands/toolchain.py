"""doscc toolchain - manage toolchain configurations."""

import sys
from pathlib import Path

from config import (
    GlobalConfig, ToolchainConfig, SDKConfig,
    load_global_config, write_global_config, GLOBAL_CONFIG_PATH,
)


def _cmd_list(cfg: GlobalConfig) -> int:
    """List configured toolchains and SDKs."""
    if cfg.toolchains:
        print("toolchains:")
        for name, tc in cfg.toolchains.items():
            exists = tc.path.exists()
            cl_exists = (tc.path / "BIN" / "CL.EXE").exists() if exists else False
            status = "ok" if cl_exists else ("path exists, CL.EXE missing" if exists else "NOT FOUND")
            print(f"  {name}: {tc.path} ({status})")
    else:
        print("no toolchains configured")

    print()
    if cfg.sdks:
        print("SDKs:")
        for name, sdk in cfg.sdks.items():
            exists = sdk.path.exists()
            print(f"  {name}: {sdk.path} ({'ok' if exists else 'NOT FOUND'})")
    else:
        print("no SDKs configured")

    return 0


def _cmd_add(cfg: GlobalConfig, args: list[str]) -> int:
    """Add a toolchain or SDK."""
    if len(args) < 3:
        print("usage: doscc toolchain add <type> <name> <path>", file=sys.stderr)
        print("  type: toolchain | sdk", file=sys.stderr)
        return 1

    kind, name, path = args[0], args[1], args[2]

    if kind == "toolchain":
        cfg.toolchains[name] = ToolchainConfig(name=name, path=Path(path))
        write_global_config(cfg)
        print(f"added toolchain '{name}' at {path}")
    elif kind == "sdk":
        cfg.sdks[name] = SDKConfig(name=name, path=Path(path))
        write_global_config(cfg)
        print(f"added SDK '{name}' at {path}")
    else:
        print(f"error: unknown type '{kind}' (use 'toolchain' or 'sdk')",
              file=sys.stderr)
        return 1

    return 0


def _cmd_test(cfg: GlobalConfig, args: list[str]) -> int:
    """Test a toolchain by running CL.EXE."""
    name = args[0] if args else "msc50"
    if name not in cfg.toolchains:
        print(f"error: toolchain '{name}' not found", file=sys.stderr)
        return 1

    tc = cfg.toolchains[name]
    cl = tc.path / "BIN" / "CL.EXE"
    if not cl.exists():
        print(f"error: CL.EXE not found at {cl}", file=sys.stderr)
        return 1

    import subprocess
    result = subprocess.run(
        [cfg.xt_path, "run", "-c", str(tc.path), "BIN\\CL.EXE"],
        capture_output=True, text=True,
    )

    if result.returncode == 255:
        print(f"error: XT failed to run CL.EXE", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return 1

    print(f"toolchain '{name}' is working:")
    output = (result.stdout + result.stderr).strip()
    for line in output.split("\n")[:3]:
        print(f"  {line}")

    return 0


def run(args: list[str]) -> int:
    if not GLOBAL_CONFIG_PATH.exists():
        print("error: no global config found, run 'doscc setup' first",
              file=sys.stderr)
        return 1

    cfg = load_global_config()

    if not args:
        return _cmd_list(cfg)

    subcmd = args[0]
    if subcmd == "list":
        return _cmd_list(cfg)
    elif subcmd == "add":
        return _cmd_add(cfg, args[1:])
    elif subcmd == "test":
        return _cmd_test(cfg, args[1:])
    else:
        print(f"error: unknown subcommand '{subcmd}'", file=sys.stderr)
        print("usage: doscc toolchain [list|add|test]", file=sys.stderr)
        return 1
