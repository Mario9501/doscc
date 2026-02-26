"""SDK and toolchain auto-setup for doscc."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


DOSCC_DIR = Path.home() / ".doscc"
TOOLCHAINS_DIR = DOSCC_DIR / "toolchains"
SDKS_DIR = DOSCC_DIR / "sdks"

HP95LX_REPO = "https://github.com/95lx/hp95dev.git"
PAL_REPO = "https://github.com/JoakimCh/palmtop-application-library.git"
MSC50_REPO = "https://github.com/Mario9501/msc50.git"
MSC50_URL = (
    "https://archive.org/download/"
    "microsoft-c-compiler-5.0-1987-5.25-360k.-7z/"
    "Microsoft%20C%20Compiler%205.0.zip"
)


# ======================================================================
# Prerequisite checks
# ======================================================================

def check_tool(name: str) -> bool:
    """Check if a host tool is available."""
    return shutil.which(name) is not None


def require_tools(*names: str) -> list[str]:
    """Return list of missing tools from the given names."""
    return [n for n in names if not check_tool(n)]


# ======================================================================
# HP 95LX SDK
# ======================================================================

def clone_hp95lx_sdk(dest: Path) -> bool:
    """Clone the HP 95LX SDK from GitHub.

    Returns True on success, False on failure.
    """
    missing = require_tools("git")
    if missing:
        print(f"  error: required tool not found: {', '.join(missing)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  removing existing directory: {dest}")
        shutil.rmtree(dest)

    print(f"  cloning {HP95LX_REPO}...")
    result = subprocess.run(
        ["git", "clone", HP95LX_REPO, str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  error: git clone failed")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:5]:
                print(f"    {line}")
        return False

    if not validate_hp95lx_sdk(dest):
        print("  error: cloned SDK is missing expected files")
        return False

    print(f"  verified: TOOLS/E2M.EXE, TOOLS/CRT0.OBJ, TOOLS/CSVC.OBJ")
    return True


def validate_hp95lx_sdk(path: Path) -> bool:
    """Check that path contains a valid HP 95LX SDK."""
    required = ["TOOLS/E2M.EXE", "TOOLS/CRT0.OBJ", "TOOLS/CSVC.OBJ"]
    for f in required:
        if not (path / f).exists():
            return False
    return True


# ======================================================================
# PAL (Palmtop Application Library) for HP 100LX/200LX
# ======================================================================

def clone_pal(dest: Path) -> bool:
    """Clone the Palmtop Application Library from GitHub.

    Returns True on success, False on failure.
    """
    missing = require_tools("git")
    if missing:
        print(f"  error: required tool not found: {', '.join(missing)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  removing existing directory: {dest}")
        shutil.rmtree(dest)

    print(f"  cloning {PAL_REPO}...")
    result = subprocess.run(
        ["git", "clone", PAL_REPO, str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  error: git clone failed")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:5]:
                print(f"    {line}")
        return False

    if not validate_pal(dest):
        print("  error: cloned PAL is missing expected files")
        return False

    print(f"  verified: PAL/SRC/INC/PAL.H, PAL/LIBS/, PAL/SAMPLES/")
    return True


def validate_pal(path: Path) -> bool:
    """Check that path contains a valid PAL installation."""
    required = ["PAL/SRC/INC/PAL.H", "PAL/LIBS", "PAL/SAMPLES"]
    for f in required:
        if not (path / f).exists():
            return False
    return True


# ======================================================================
# MS C 5.0 toolchain - clone from GitHub
# ======================================================================

def clone_msc50(dest: Path) -> bool:
    """Clone the pre-assembled MS C 5.0 + MASM 5.1 toolchain from GitHub.

    Returns True on success, False on failure.
    """
    missing = require_tools("git")
    if missing:
        print(f"  error: required tool not found: {', '.join(missing)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  removing existing directory: {dest}")
        shutil.rmtree(dest)

    print(f"  cloning {MSC50_REPO}...")
    result = subprocess.run(
        ["git", "clone", MSC50_REPO, str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  error: git clone failed")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:5]:
                print(f"    {line}")
        return False

    if not validate_msc50(dest):
        print("  error: cloned toolchain is missing expected files")
        return False

    print(f"  verified: BIN/CL.EXE, INCLUDE/STDIO.H, LIB/SLIBC.LIB")
    return True


# ======================================================================
# MS C 5.0 toolchain - download
# ======================================================================

def download_msc50(dest: Path) -> bool:
    """Download and assemble MS C 5.0 from archive.org.

    Returns True on success, False on failure.
    """
    missing = require_tools("curl", "unzip")
    if missing:
        print(f"  error: required tools not found: {', '.join(missing)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        zip_path = tmp / "msc50.zip"

        # Download
        print(f"  downloading MS C 5.0 from archive.org...")
        result = subprocess.run(
            ["curl", "-L", "-o", str(zip_path), "--progress-bar", MSC50_URL],
            capture_output=False,
        )
        if result.returncode != 0 or not zip_path.exists():
            print("  error: download failed")
            return False

        # Extract zip
        print("  extracting...")
        extract_dir = tmp / "extracted"
        extract_dir.mkdir()
        result = subprocess.run(
            ["unzip", "-q", "-o", str(zip_path), "-d", str(extract_dir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("  error: unzip failed")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:5]:
                    print(f"    {line}")
            return False

        # Detect what we got: disk images or already-extracted directories
        disks_dir = find_msc50_disks(extract_dir)
        if disks_dir is None:
            print("  error: could not identify MS C 5.0 disk contents in archive")
            return False

        # Check if we have disk images that need mtools
        img_files = _find_disk_images(disks_dir)
        if img_files:
            missing = require_tools("mcopy")
            if missing:
                print(f"  error: disk images found but mtools not installed")
                print(f"  install mtools: brew install mtools (macOS) or apt install mtools (Linux)")
                return False
            print("  extracting disk images...")
            extracted = tmp / "disks"
            extract_disk_images(disks_dir, extracted)
            disks_dir = extracted

        # Assemble into final toolchain directory
        if dest.exists():
            print(f"  removing existing directory: {dest}")
            shutil.rmtree(dest)
        dest.mkdir(parents=True)

        print("  assembling toolchain (BIN, INCLUDE, LIB)...")
        assemble_msc50(disks_dir, dest)

        if not validate_msc50(dest):
            print("  error: assembled toolchain is missing critical files")
            return False

        ok_cl = "ok" if (dest / "BIN" / "CL.EXE").exists() else "MISSING"
        ok_stdio = "ok" if (dest / "INCLUDE" / "STDIO.H").exists() else "MISSING"
        ok_slibc = "ok" if (dest / "LIB" / "SLIBC.LIB").exists() else "MISSING"
        print(f"  validating: CL.EXE {ok_cl}, STDIO.H {ok_stdio}, SLIBC.LIB {ok_slibc}")

    return True


def assemble_from_local(source: Path, dest: Path) -> bool:
    """Assemble MS C 5.0 from local disk files or images.

    source can contain .img/.ima files (requires mtools) or already-extracted
    directory structure with the MS C 5.0 files.

    Returns True on success, False on failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    disks_dir = find_msc50_disks(source)
    if disks_dir is None:
        print("  error: could not identify MS C 5.0 disk contents at that path")
        return False

    # Check if we have disk images that need mtools
    img_files = _find_disk_images(disks_dir)
    if img_files:
        missing = require_tools("mcopy")
        if missing:
            print(f"  error: disk images found but mtools not installed")
            print(f"  install mtools: brew install mtools (macOS) or apt install mtools (Linux)")
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            extracted = Path(tmpdir) / "disks"
            print("  extracting disk images...")
            extract_disk_images(disks_dir, extracted)

            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True)

            print("  assembling toolchain (BIN, INCLUDE, LIB)...")
            assemble_msc50(extracted, dest)
    else:
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)

        print("  assembling toolchain (BIN, INCLUDE, LIB)...")
        assemble_msc50(disks_dir, dest)

    if not validate_msc50(dest):
        print("  error: assembled toolchain is missing critical files")
        return False

    ok_cl = "ok" if (dest / "BIN" / "CL.EXE").exists() else "MISSING"
    ok_stdio = "ok" if (dest / "INCLUDE" / "STDIO.H").exists() else "MISSING"
    ok_slibc = "ok" if (dest / "LIB" / "SLIBC.LIB").exists() else "MISSING"
    print(f"  validating: CL.EXE {ok_cl}, STDIO.H {ok_stdio}, SLIBC.LIB {ok_slibc}")
    return True


# ======================================================================
# MS C 5.0 - disk image extraction
# ======================================================================

def _find_disk_images(path: Path) -> list[Path]:
    """Find floppy disk image files in a directory."""
    exts = {".img", ".ima", ".360", ".dsk"}
    images = []
    for f in path.iterdir():
        if f.is_file() and f.suffix.lower() in exts:
            images.append(f)
    return sorted(images)


# Files that identify which MS C 5.0 disk an image came from
_DISK_SIGNATURES = {
    "CL.EXE":      "SETUP",
    "C1.EXE":      "SETUP",
    "C2.EXE":      "COMPILER",
    "C3.EXE":      "COMPILER",
    "LINK.EXE":    "UTILITES",
    "LIB.EXE":     "UTILITES",
    "MAKE.EXE":    "UTILITES",
    "STDIO.H":     "INCLIBSM",
    "SLIBC.LIB":   "INCLIBSM",
    "C1L.EXE":     "ADDNUTIL",
    "MLIBC.LIB":   "ADDNLIBM",
    "LLIBC.LIB":   "ADDNLIBL",
}


def _identify_disk(contents: list[str]) -> str:
    """Try to identify a disk by its file contents."""
    upper = [f.upper() for f in contents]
    for sig_file, disk_name in _DISK_SIGNATURES.items():
        if sig_file in upper:
            return disk_name
    return ""


def extract_disk_images(img_dir: Path, dest: Path) -> None:
    """Extract all disk images from img_dir into named subdirectories in dest."""
    dest.mkdir(parents=True, exist_ok=True)
    images = _find_disk_images(img_dir)
    disk_num = 0

    for img_path in images:
        disk_num += 1
        # Extract to a temp subdir first so we can identify the disk
        tmp_name = f"DISK{disk_num}"
        disk_dir = dest / tmp_name
        disk_dir.mkdir(parents=True, exist_ok=True)

        # Use mcopy to extract all files from the image
        subprocess.run(
            ["mcopy", "-s", "-n", "-i", str(img_path), "::/", str(disk_dir) + "/"],
            capture_output=True, text=True,
        )

        # Try to identify the disk and rename the directory
        files = [f.name for f in disk_dir.rglob("*") if f.is_file()]
        disk_name = _identify_disk(files)
        if disk_name and disk_name != tmp_name:
            named_dir = dest / disk_name
            if not named_dir.exists():
                disk_dir.rename(named_dir)
            else:
                # Merge into existing named dir
                _copy_tree(disk_dir, named_dir)
                shutil.rmtree(disk_dir)


# ======================================================================
# MS C 5.0 - assembly from extracted disk contents
# ======================================================================

def _copy_tree(src: Path, dest: Path) -> None:
    """Copy all files from src into dest, merging directories."""
    for item in src.iterdir():
        dest_item = dest / item.name
        if item.is_dir():
            dest_item.mkdir(exist_ok=True)
            _copy_tree(item, dest_item)
        else:
            shutil.copy2(item, dest_item)


def _find_file_in(root: Path, filename: str) -> Optional[Path]:
    """Find a file (case-insensitive) anywhere under root. Returns its parent dir."""
    upper = filename.upper()
    for f in root.rglob("*"):
        if f.is_file() and f.name.upper() == upper:
            return f.parent
    return None


def _copy_file(src_dir: Path, filename: str, dest_dir: Path) -> bool:
    """Copy a single file (case-insensitive match) from src_dir to dest_dir."""
    upper = filename.upper()
    for f in src_dir.iterdir():
        if f.is_file() and f.name.upper() == upper:
            shutil.copy2(f, dest_dir / f.name.upper())
            return True
    return False


def _copy_files(src_dir: Path, filenames: list[str], dest_dir: Path) -> int:
    """Copy multiple files from src_dir to dest_dir. Returns count copied."""
    count = 0
    for fn in filenames:
        if _copy_file(src_dir, fn, dest_dir):
            count += 1
    return count


def _collect_by_ext(root: Path, ext: str, dest_dir: Path) -> int:
    """Copy all files with given extension from root tree to dest_dir."""
    count = 0
    upper_ext = ext.upper()
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.upper() == upper_ext:
            dest_file = dest_dir / f.name.upper()
            if not dest_file.exists():
                shutil.copy2(f, dest_file)
                count += 1
    return count


def assemble_msc50(disks_dir: Path, dest: Path) -> None:
    """Assemble MS C 5.0 toolchain from extracted disk contents.

    disks_dir contains subdirectories (named or numbered) with the disk
    contents. dest will get BIN/, INCLUDE/, LIB/ subdirectories.
    """
    bin_dir = dest / "BIN"
    inc_dir = dest / "INCLUDE"
    lib_dir = dest / "LIB"
    bin_dir.mkdir(exist_ok=True)
    inc_dir.mkdir(exist_ok=True)
    lib_dir.mkdir(exist_ok=True)

    # --- BIN/ ---
    # Search all subdirs for known executables
    bin_files = [
        # SETUP disk
        "CL.EXE", "CL.ERR", "CL.HLP", "C1.EXE",
        # COMPILER disk
        "C2.EXE", "C3.EXE", "C1.ERR", "C23.ERR",
        # UTILITES disk
        "LINK.EXE", "LIB.EXE", "MAKE.EXE", "ERROUT.EXE",
        "EXEMOD.EXE", "EXEPACK.EXE", "SETENV.EXE",
        # ADDNUTIL disk
        "C1L.EXE",
    ]
    for fn in bin_files:
        src = _find_file_in(disks_dir, fn)
        if src:
            _copy_file(src, fn, bin_dir)

    # --- INCLUDE/ ---
    # Find the directory containing STDIO.H
    stdio_dir = _find_file_in(disks_dir, "STDIO.H")
    if stdio_dir:
        # Copy all .H files from that directory
        for f in stdio_dir.iterdir():
            if f.is_file() and f.suffix.upper() == ".H":
                shutil.copy2(f, inc_dir / f.name.upper())

        # Copy SYS/ subdirectory if present
        sys_src = None
        for d in stdio_dir.iterdir():
            if d.is_dir() and d.name.upper() == "SYS":
                sys_src = d
                break
        # Also check parent's SYS/ and sibling INCLUDE/SYS/
        if sys_src is None:
            for candidate in [stdio_dir.parent, stdio_dir]:
                for d in candidate.iterdir():
                    if d.is_dir() and d.name.upper() == "SYS":
                        sys_src = d
                        break
                if sys_src:
                    break

        if sys_src:
            sys_dest = inc_dir / "SYS"
            sys_dest.mkdir(exist_ok=True)
            for f in sys_src.iterdir():
                if f.is_file():
                    shutil.copy2(f, sys_dest / f.name.upper())

        # Also look for INCLUDE/ directories elsewhere in the disk tree that
        # might have additional headers (some archives nest things differently)
        for inc_candidate in disks_dir.rglob("*"):
            if (inc_candidate.is_dir()
                    and inc_candidate.name.upper() == "INCLUDE"
                    and inc_candidate != stdio_dir):
                for f in inc_candidate.iterdir():
                    if f.is_file() and f.suffix.upper() == ".H":
                        dest_f = inc_dir / f.name.upper()
                        if not dest_f.exists():
                            shutil.copy2(f, dest_f)

    # --- LIB/ ---
    # Collect all .LIB files from disk tree
    _collect_by_ext(disks_dir, ".LIB", lib_dir)

    # Collect specific .OBJ files used by MS C
    obj_files = ["BINMODE.OBJ", "SETARGV.OBJ"]
    for fn in obj_files:
        src = _find_file_in(disks_dir, fn)
        if src:
            _copy_file(src, fn, lib_dir)


# ======================================================================
# MS C 5.0 - validation and detection
# ======================================================================

def validate_msc50(path: Path) -> bool:
    """Check that path contains a valid assembled MS C 5.0 toolchain."""
    required = [
        "BIN/CL.EXE",
        "INCLUDE/STDIO.H",
        "LIB/SLIBC.LIB",
    ]
    for f in required:
        if not (path / f).exists():
            return False
    return True


def find_msc50_disks(path: Path) -> Optional[Path]:
    """Detect if path contains MS C 5.0 disk contents or images.

    Searches recursively for key files (CL.EXE, STDIO.H) or disk images.
    Returns the directory containing the disk structure, or None.
    """
    # Check for disk image files directly
    if _find_disk_images(path):
        return path

    # Check subdirs for disk images
    for d in path.iterdir():
        if d.is_dir() and _find_disk_images(d):
            return d

    # Check if this looks like an already-extracted disk structure
    # by searching for signature files
    has_cl = False
    has_stdio = False
    for f in path.rglob("*"):
        if f.is_file():
            upper = f.name.upper()
            if upper == "CL.EXE":
                has_cl = True
            elif upper == "STDIO.H":
                has_stdio = True
        if has_cl and has_stdio:
            return path

    # Check one level of subdirectories (archive may wrap in a folder)
    for d in path.iterdir():
        if d.is_dir():
            has_cl = False
            has_stdio = False
            for f in d.rglob("*"):
                if f.is_file():
                    upper = f.name.upper()
                    if upper == "CL.EXE":
                        has_cl = True
                    elif upper == "STDIO.H":
                        has_stdio = True
                if has_cl and has_stdio:
                    return d

    return None
