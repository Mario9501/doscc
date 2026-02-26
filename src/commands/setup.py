"""doscc setup - interactive configuration wizard."""

import shutil
from pathlib import Path

from config import (
    GlobalConfig, ToolchainConfig, SDKConfig,
    GLOBAL_CONFIG_PATH, LIBS_DIR, load_global_config, write_global_config,
)
from sdk_setup import (
    TOOLCHAINS_DIR, SDKS_DIR,
    clone_hp95lx_sdk, validate_hp95lx_sdk,
    clone_pal, validate_pal,
    clone_msc50, download_msc50, assemble_from_local, validate_msc50,
)


# ======================================================================
# Helpers
# ======================================================================

def _prompt(msg: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        raw = input(f"{msg} [{default}]: ").strip()
        return raw if raw else default
    return input(f"{msg}: ").strip()


def _choice(msg: str, options: list[str], default: int = 1) -> int:
    """Present numbered choices, return 1-based selection."""
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if not raw:
            return default
        try:
            n = int(raw)
            if 1 <= n <= len(options):
                return n
        except ValueError:
            pass
        print(f"  please enter 1-{len(options)}")


def _find_xt() -> str:
    """Try to find XT in PATH or common locations."""
    xt = shutil.which("xt")
    if xt:
        return xt

    home = Path.home()
    candidates = [
        home / "XT" / "bin" / "xt",
        home / ".local" / "bin" / "xt",
        Path("/usr/local/bin/xt"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return ""


# ======================================================================
# Section: MS C 5.0 Toolchain
# ======================================================================

def _setup_toolchain(cfg: GlobalConfig) -> None:
    """Interactive setup for MS C 5.0 toolchain."""
    print()
    print("-- MS C 5.0 Toolchain --")

    existing = cfg.toolchains.get("msc50")
    if existing and validate_msc50(existing.path):
        print(f"  configured: {existing.path}")
        update = _prompt("  reconfigure? (y/n)", "n")
        if update.lower() != "y":
            return
    else:
        if existing:
            print(f"  configured path invalid: {existing.path}")
        else:
            print("  no toolchain configured.")

    choice = _choice("Choice", [
        "Clone from GitHub (requires git)",
        "Download from archive.org (requires curl + unzip)",
        "Assemble from disk files or images (requires mtools for .img)",
        "Point to existing assembled toolchain",
        "Skip",
    ], default=1)

    if choice == 1:
        dest = TOOLCHAINS_DIR / "msc50"
        if clone_msc50(dest):
            cfg.toolchains["msc50"] = ToolchainConfig(name="msc50", path=dest)
            print(f"  toolchain installed at {dest}")
        else:
            print("  toolchain setup failed")

    elif choice == 2:
        dest = TOOLCHAINS_DIR / "msc50"
        if download_msc50(dest):
            cfg.toolchains["msc50"] = ToolchainConfig(name="msc50", path=dest)
            print(f"  toolchain installed at {dest}")
        else:
            print("  toolchain setup failed")

    elif choice == 3:
        source = _prompt("  path to disk files or images")
        if source:
            dest = TOOLCHAINS_DIR / "msc50"
            if assemble_from_local(Path(source), dest):
                cfg.toolchains["msc50"] = ToolchainConfig(name="msc50", path=dest)
                print(f"  toolchain installed at {dest}")
            else:
                print("  toolchain setup failed")

    elif choice == 4:
        path = _prompt("  path to MSC directory")
        if path:
            p = Path(path)
            if validate_msc50(p):
                cfg.toolchains["msc50"] = ToolchainConfig(name="msc50", path=p)
            else:
                print(f"  warning: missing expected files (BIN/CL.EXE, INCLUDE/STDIO.H, LIB/SLIBC.LIB)")
                use = _prompt("  use this path anyway? (y/n)", "n")
                if use.lower() == "y":
                    cfg.toolchains["msc50"] = ToolchainConfig(name="msc50", path=p)


# ======================================================================
# Section: HP 95LX / 200LX SDK
# ======================================================================

def _setup_hp95lx_sdk(cfg: GlobalConfig) -> None:
    """Interactive setup for HP 95LX SDK (also used by HP 200LX)."""
    print()
    print("-- HP 95LX / 200LX SDK --")

    existing = cfg.sdks.get("hp95lx")
    if existing and validate_hp95lx_sdk(existing.path):
        print(f"  configured: {existing.path}")
        update = _prompt("  reconfigure? (y/n)", "n")
        if update.lower() != "y":
            return
    else:
        if existing:
            print(f"  configured path invalid: {existing.path}")
        else:
            print("  no SDK configured.")

    choice = _choice("Choice", [
        "Clone from GitHub (requires git)",
        "Point to existing SDK directory",
        "Skip",
    ], default=1)

    if choice == 1:
        dest = SDKS_DIR / "hp95lx"
        if clone_hp95lx_sdk(dest):
            cfg.sdks["hp95lx"] = SDKConfig(name="hp95lx", path=dest)
            print(f"  SDK installed at {dest}")
        else:
            print("  SDK setup failed")

    elif choice == 2:
        path = _prompt("  path to HP 95LX SDK")
        if path:
            p = Path(path)
            if validate_hp95lx_sdk(p):
                cfg.sdks["hp95lx"] = SDKConfig(name="hp95lx", path=p)
            else:
                print(f"  warning: missing expected files (TOOLS/E2M.EXE, TOOLS/CRT0.OBJ, TOOLS/CSVC.OBJ)")
                use = _prompt("  use this path anyway? (y/n)", "n")
                if use.lower() == "y":
                    cfg.sdks["hp95lx"] = SDKConfig(name="hp95lx", path=p)


# ======================================================================
# Section: PAL (Palmtop Application Library)
# ======================================================================

def _setup_pal(cfg: GlobalConfig) -> None:
    """Interactive setup for PAL (HP 100LX/200LX application library)."""
    print()
    print("-- PAL (Palmtop Application Library) --")
    print("  optional C library for HP 100LX/200LX UI development")

    existing = cfg.sdks.get("pal")
    if existing and validate_pal(existing.path):
        print(f"  configured: {existing.path}")
        update = _prompt("  reconfigure? (y/n)", "n")
        if update.lower() != "y":
            return
    else:
        if existing:
            print(f"  configured path invalid: {existing.path}")

    choice = _choice("Choice", [
        "Clone from GitHub (requires git)",
        "Point to existing PAL directory",
        "Skip",
    ], default=3)

    if choice == 1:
        dest = SDKS_DIR / "pal"
        if clone_pal(dest):
            cfg.sdks["pal"] = SDKConfig(name="pal", path=dest)
            print(f"  PAL installed at {dest}")
        else:
            print("  PAL setup failed")

    elif choice == 2:
        path = _prompt("  path to PAL directory")
        if path:
            p = Path(path)
            if validate_pal(p):
                cfg.sdks["pal"] = SDKConfig(name="pal", path=p)
            else:
                print(f"  warning: missing expected files (PAL/SRC/INC/PAL.H, PAL/LIBS/)")
                use = _prompt("  use this path anyway? (y/n)", "n")
                if use.lower() == "y":
                    cfg.sdks["pal"] = SDKConfig(name="pal", path=p)


# ======================================================================
# Section: Pre-built libraries
# ======================================================================

def _install_libs() -> None:
    """Install library sources from doscc's bundled libs to ~/.doscc/libs/."""
    # Locate bundled library sources relative to this file:
    # src/commands/setup.py -> src/libs/
    bundled_libs = Path(__file__).parent.parent / "libs"
    if not bundled_libs.exists():
        return

    print()
    print("-- Pre-built Libraries --")

    installed = 0
    for lib_src in sorted(bundled_libs.iterdir()):
        if not lib_src.is_dir():
            continue

        name = lib_src.name
        dest = LIBS_DIR / name
        dest.mkdir(parents=True, exist_ok=True)

        # Copy .H and .C source files (don't overwrite .LIB if already built)
        for item in lib_src.iterdir():
            if item.suffix.upper() in (".H", ".C", ".ASM"):
                shutil.copy2(item, dest / item.name)

        installed += 1
        has_lib = any(dest.glob("*.LIB")) or any(dest.glob("*.lib"))
        status = "installed (built)" if has_lib else "installed (run 'doscc lib build' to compile)"
        print(f"  {name.upper()}: {status}")

    if installed == 0:
        print("  no bundled libraries found")


# ======================================================================
# Main entry point
# ======================================================================

def run(args: list[str]) -> int:
    print("doscc setup")
    print("=" * 40)
    print()

    # Load existing config if any
    if GLOBAL_CONFIG_PATH.exists():
        print(f"existing config found at {GLOBAL_CONFIG_PATH}")
        update = _prompt("update existing config? (y/n)", "y")
        if update.lower() != "y":
            return 0
        cfg = load_global_config()
    else:
        cfg = GlobalConfig()

    # XT Emulator
    print()
    print("-- XT Emulator --")
    detected = _find_xt()
    if detected:
        print(f"  found: {detected}")
    cfg.xt_path = _prompt("XT path", detected or cfg.xt_path)

    # MS C 5.0 Toolchain
    _setup_toolchain(cfg)

    # HP 95LX / 200LX SDK
    _setup_hp95lx_sdk(cfg)

    # PAL (Palmtop Application Library)
    _setup_pal(cfg)

    # Pre-built libraries
    _install_libs()

    # Write config
    write_global_config(cfg)
    print()
    print(f"config written to {GLOBAL_CONFIG_PATH}")
    return 0
