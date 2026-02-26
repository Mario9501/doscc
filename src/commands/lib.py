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
  new <name>        Create a new library from template

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

    # Header-only libraries: have .H files but no compilable sources
    if not sources:
        has_headers = any(lib_dir.glob("*.H")) or any(lib_dir.glob("*.h"))
        if has_headers:
            print(f"{name.upper()}: header-only, nothing to build")
            return 0
        print(f"error: no .C or .ASM source files in {lib_dir}", file=sys.stderr)
        return 1

    # Check DEPS file — all dependencies must be built first
    deps_file = lib_dir / "DEPS"
    if deps_file.exists():
        for line in deps_file.read_text().splitlines():
            dep = line.strip()
            if not dep or dep.startswith("#"):
                continue
            dep_dir = LIBS_DIR / dep.lower()
            dep_lib = dep.upper() + ".LIB"
            if not dep_dir.exists() or not (dep_dir / dep_lib).exists():
                print(f"error: {name.upper()} depends on {dep.upper()} "
                      f"which is not built yet", file=sys.stderr)
                print(f"build it first: doscc lib build {dep}", file=sys.stderr)
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

        # Cross-library headers: symlink .H from all other installed libs
        if LIBS_DIR.exists():
            for other_lib in LIBS_DIR.iterdir():
                if other_lib.is_dir() and other_lib != lib_dir:
                    for h in other_lib.iterdir():
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


def _topo_sort_libs():
    """Topologically sort library directories by DEPS files."""
    if not LIBS_DIR.exists():
        return []

    # Collect all library names
    libs = {}
    for lib_dir in sorted(LIBS_DIR.iterdir()):
        if not lib_dir.is_dir():
            continue
        name = lib_dir.name.lower()
        deps = []
        deps_file = lib_dir / "DEPS"
        if deps_file.exists():
            for line in deps_file.read_text().splitlines():
                dep = line.strip().lower()
                if dep and not dep.startswith("#"):
                    deps.append(dep)
        libs[name] = deps

    # Kahn's algorithm for topological sort
    in_degree = {name: 0 for name in libs}
    for name, deps in libs.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[name] += 1

    queue = sorted([n for n, d in in_degree.items() if d == 0])
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for name, deps in libs.items():
            if node in deps:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)
                    queue.sort()

    # Append any remaining (circular deps) at the end
    for name in sorted(libs):
        if name not in order:
            order.append(name)

    return order


def _build_all(verbose: bool) -> int:
    """Build all libraries in dependency order."""
    if not LIBS_DIR.exists():
        print("no libraries installed")
        print("run 'doscc setup' to install library sources")
        return 0

    order = _topo_sort_libs()
    if not order:
        print("no libraries found")
        return 0

    built = 0
    rc = 0
    for name in order:
        lib_dir = LIBS_DIR / name
        has_source = (any(lib_dir.glob("*.C")) or any(lib_dir.glob("*.c"))
                      or any(lib_dir.glob("*.ASM")) or any(lib_dir.glob("*.asm")))
        has_headers = any(lib_dir.glob("*.H")) or any(lib_dir.glob("*.h"))
        if has_source or has_headers:
            result = _build_lib(name, verbose)
            if result != 0:
                rc = result
            else:
                built += 1

    if built == 0 and rc == 0:
        print("no libraries with source files found")

    return rc


# ======================================================================
# New library scaffolding
# ======================================================================

_TEMPLATE_H = """\
/* ======================================================================
 * {NAME}.H - {description}
 *
 * MS C 5.0 / small model
 * ====================================================================== */

#ifndef {NAME}_H
#define {NAME}_H

/* ======================================================================
 * Constants
 * ====================================================================== */


/* ======================================================================
 * Functions
 * ====================================================================== */

/* Initialize the {lower} subsystem. */
int   {prefix}_init(void);

/* Shut down the {lower} subsystem and release resources. */
void  {prefix}_cleanup(void);

#endif /* {NAME}_H */
"""

_TEMPLATE_C = """\
/* ======================================================================
 * {NAME}.C - {description}
 *
 * MS C 5.0 / small model
 * ====================================================================== */

#include <dos.h>
#include "{lower}.h"

/* ======================================================================
 * Internal state
 * ====================================================================== */

static int {prefix}_initialized = 0;

/* ======================================================================
 * Public API
 * ====================================================================== */

int {prefix}_init(void)
{{
    if ({prefix}_initialized)
        return 0;
    {prefix}_initialized = 1;
    return 0;
}}

void {prefix}_cleanup(void)
{{
    if (!{prefix}_initialized)
        return;
    {prefix}_initialized = 0;
}}
"""


def _new_lib(name: str) -> int:
    """Create a new library from template."""
    bundled = Path(__file__).parent.parent / "libs"
    lib_dir = bundled / name.lower()

    if lib_dir.exists():
        print(f"error: library '{name}' already exists at {lib_dir}",
              file=sys.stderr)
        return 1

    upper = name.upper()
    lower = name.lower()
    prefix = lower[:4] if len(lower) > 4 else lower
    desc = f"{upper} library"

    lib_dir.mkdir(parents=True)

    h_path = lib_dir / f"{upper}.H"
    c_path = lib_dir / f"{upper}.C"

    h_path.write_text(_TEMPLATE_H.format(
        NAME=upper, lower=lower, prefix=prefix, description=desc))
    c_path.write_text(_TEMPLATE_C.format(
        NAME=upper, lower=lower, prefix=prefix, description=desc))

    print(f"created library '{upper}' in {lib_dir}")
    print(f"  {h_path.name}")
    print(f"  {c_path.name}")
    print(f"\nprefix: {prefix}_")
    print("edit the files, then run 'doscc setup' to install")
    return 0


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

    elif subcmd == "new":
        if len(cmd_args) < 2:
            print("error: usage: doscc lib new <name>", file=sys.stderr)
            return 1
        return _new_lib(cmd_args[1])

    else:
        print(f"error: unknown subcommand '{subcmd}'", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1
