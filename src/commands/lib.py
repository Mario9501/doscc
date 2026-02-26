"""doscc lib - manage pre-built libraries."""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from config import GLOBAL_CONFIG_DIR, load_global_config
from xt import XTRunner, BuildError


LIBS_DIR = GLOBAL_CONFIG_DIR / "libs"

USAGE = """\
doscc lib - manage pre-built libraries

usage: doscc lib <subcommand>

subcommands:
  list              List installed libraries
  build [name]      Build a library (or all libraries)

options:
  -v, --verbose     Show detailed build output
"""


# ======================================================================
# List
# ======================================================================

def _list_libs() -> int:
    """List installed libraries and their build status."""
    if not LIBS_DIR.exists():
        print("no libraries installed")
        print("run 'doscc setup' to install library sources")
        return 0

    found = False
    for lib_dir in sorted(LIBS_DIR.iterdir()):
        if not lib_dir.is_dir():
            continue
        found = True
        name = lib_dir.name

        has_source = (any(lib_dir.glob("*.C")) or any(lib_dir.glob("*.c"))
                      or any(lib_dir.glob("*.ASM")) or any(lib_dir.glob("*.asm")))
        has_lib = any(lib_dir.glob("*.LIB")) or any(lib_dir.glob("*.lib"))

        if has_lib:
            status = "built"
        elif has_source:
            status = "source only (run 'doscc lib build')"
        else:
            status = "empty"

        print(f"  {name.upper()}: {status}")

    if not found:
        print("no libraries installed")

    return 0


# ======================================================================
# Build
# ======================================================================

def _build_lib(name: str, verbose: bool) -> int:
    """Build a single library."""
    lib_dir = LIBS_DIR / name.lower()
    if not lib_dir.exists():
        print(f"error: library '{name}' not found in {LIBS_DIR}", file=sys.stderr)
        return 1

    # Find source files (.C and .ASM)
    c_sources = sorted(lib_dir.glob("*.C"))
    if not c_sources:
        c_sources = sorted(lib_dir.glob("*.c"))
    asm_sources = sorted(lib_dir.glob("*.ASM"))
    if not asm_sources:
        asm_sources = sorted(lib_dir.glob("*.asm"))
    sources = c_sources + asm_sources
    if not sources:
        print(f"error: no .C or .ASM source files in {lib_dir}", file=sys.stderr)
        return 1

    # Load global config for toolchain
    global_cfg = load_global_config()
    if "msc50" not in global_cfg.toolchains:
        print("error: toolchain 'msc50' not configured", file=sys.stderr)
        print("run 'doscc setup' first", file=sys.stderr)
        return 1

    tc = global_cfg.toolchains["msc50"]
    lib_name = name.upper() + ".LIB"

    start = time.time()

    # Create temp workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir)

        # Symlink toolchain BIN/
        os.symlink(tc.path / "BIN", build_dir / "BIN")

        # Merge includes: toolchain headers + library's own headers
        inc_dir = build_dir / "INCLUDE"
        inc_dir.mkdir()
        tc_inc = tc.path / "INCLUDE"
        if tc_inc.exists():
            for item in tc_inc.iterdir():
                os.symlink(item, inc_dir / item.name)
        for h in lib_dir.iterdir():
            if h.suffix.upper() == ".H":
                dest = inc_dir / h.name.upper()
                if not dest.exists():
                    os.symlink(h, dest)

        # Copy source files into SRC/
        src_dir = build_dir / "SRC"
        src_dir.mkdir()
        for src in sources:
            shutil.copy2(src, src_dir / src.name.upper())

        # LIB/ for output
        lib_out_dir = build_dir / "LIB"
        lib_out_dir.mkdir()

        runner = XTRunner(global_cfg.xt_path, build_dir, verbose=verbose)

        # Compile each source file
        obj_files = []
        for src in sources:
            dos_name = src.name.upper()
            base, ext = dos_name.rsplit(".", 1)
            obj_name = base + ".OBJ"

            try:
                if ext == "ASM":
                    # MASM: /ML = case-sensitive (C linkage)
                    args = f"/ML /IINCLUDE SRC\\{dos_name},SRC\\{obj_name},NUL,NUL;"
                    runner.run_checked("BIN\\MASM.EXE", args, tool_name="MASM.EXE")
                else:
                    args = f"/c /AS /Zl /Gs /IINCLUDE /FoSRC\\ SRC\\{dos_name}"
                    runner.run_checked("BIN\\CL.EXE", args, tool_name="CL.EXE")
            except BuildError as e:
                print(f"\nerror: compiling {dos_name}: {e}", file=sys.stderr)
                if e.output:
                    print(e.output, file=sys.stderr)
                return 1
            obj_files.append(f"SRC\\{obj_name}")

        # Create .LIB using LIB.EXE
        # Format: LIB libname +obj1 +obj2 ;
        ops = " ".join(f"+{obj}" for obj in obj_files)
        args = f"LIB\\{lib_name} {ops};"

        try:
            runner.run_checked("BIN\\LIB.EXE", args, tool_name="LIB.EXE")
        except BuildError as e:
            print(f"\nerror: creating {lib_name}: {e}", file=sys.stderr)
            if e.output:
                print(e.output, file=sys.stderr)
            return 1

        # Copy built .LIB back to library directory
        built_lib = build_dir / "LIB" / lib_name
        if not built_lib.exists():
            print(f"error: {lib_name} was not created", file=sys.stderr)
            return 1

        shutil.copy2(built_lib, lib_dir / lib_name)

    elapsed = time.time() - start
    print(f"built {lib_name} ({elapsed:.1f}s)")
    return 0


def _build_all(verbose: bool) -> int:
    """Build all libraries that have source files."""
    if not LIBS_DIR.exists():
        print("no libraries installed")
        print("run 'doscc setup' to install library sources")
        return 0

    built = 0
    rc = 0
    for lib_dir in sorted(LIBS_DIR.iterdir()):
        if not lib_dir.is_dir():
            continue
        has_source = (any(lib_dir.glob("*.C")) or any(lib_dir.glob("*.c"))
                      or any(lib_dir.glob("*.ASM")) or any(lib_dir.glob("*.asm")))
        if has_source:
            result = _build_lib(lib_dir.name, verbose)
            if result != 0:
                rc = result
            else:
                built += 1

    if built == 0 and rc == 0:
        print("no libraries with source files found")

    return rc


# ======================================================================
# Entry point
# ======================================================================

def run(args: list[str]) -> int:
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0

    verbose = "-v" in args or "--verbose" in args
    cmd_args = [a for a in args if not a.startswith("-")]

    subcmd = cmd_args[0]

    if subcmd == "list":
        return _list_libs()

    elif subcmd == "build":
        if len(cmd_args) > 1:
            return _build_lib(cmd_args[1], verbose)
        else:
            return _build_all(verbose)

    else:
        print(f"error: unknown subcommand '{subcmd}'", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1
