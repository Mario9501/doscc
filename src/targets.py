"""Build target definitions and pipeline orchestration."""

import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from config import ProjectConfig
from workspace import SourceFile
from xt import XTRunner


# ======================================================================
# Memory model codes for CL.EXE /A flag
# ======================================================================

MODEL_FLAGS = {
    "tiny": "T",
    "small": "S",
    "medium": "M",
    "compact": "C",
    "large": "L",
}


class Target(ABC):
    """Base class for all build targets."""

    def __init__(self, cfg: ProjectConfig, runner: XTRunner, build_dir: Path):
        self.cfg = cfg
        self.runner = runner
        self.build_dir = build_dir

    def build(self, sources: list[SourceFile], project_root: Path) -> Path:
        """Full build pipeline. Returns path to output binary."""
        obj_files = self._compile(sources)
        output_dos = self._link(obj_files, sources)
        output_path = self._post_process(output_dos)
        return self._copy_output(output_path, project_root)

    def _compile(self, sources: list[SourceFile]) -> list[str]:
        """Compile all source files. Returns list of DOS .OBJ paths."""
        obj_files = []
        for src in sources:
            if src.source_type == "asm":
                self._assemble(src)
            else:
                flags = self._compile_flags()
                args = f"{flags} /FoSRC\\ {src.dos_path}"
                self.runner.run_checked("BIN\\CL.EXE", args, tool_name="CL.EXE")
            obj_files.append(src.obj_path)
        return obj_files

    def _assemble(self, src: SourceFile) -> None:
        """Assemble a .ASM file with MASM. Produces .OBJ in SRC\\."""
        # /ML = case-sensitive names (required for C linkage)
        # Positional format: MASM source,object,listing,cross-ref;
        args = f"/ML /IINCLUDE {src.dos_path},{src.obj_path},NUL,NUL;"
        self.runner.run_checked("BIN\\MASM.EXE", args, tool_name="MASM.EXE")

    @abstractmethod
    def _compile_flags(self) -> str:
        """Return compiler flags string (without source file)."""
        ...

    @abstractmethod
    def _link(self, obj_files: list[str], sources: list[SourceFile]) -> str:
        """Link object files. Returns DOS path to output binary."""
        ...

    def _post_process(self, output_dos: str) -> Path:
        """Optional post-processing (e.g. E2M). Returns host path."""
        # Default: no post-processing, just resolve the DOS path
        return self.build_dir / output_dos.replace("\\", "/")

    def _copy_output(self, output_path: Path, project_root: Path) -> Path:
        """Copy output binary to project directory."""
        output_dir = project_root / self.cfg.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / output_path.name
        shutil.copy2(output_path, dest)

        # Also copy .MAP file if it exists
        map_path = output_path.with_suffix(".MAP")
        if map_path.exists():
            shutil.copy2(map_path, output_dir / map_path.name)

        return dest

    def _common_compile_flags(self) -> str:
        """Build common compiler flags from project config."""
        parts = ["/c"]

        # Memory model
        model = MODEL_FLAGS.get(self.cfg.compiler.model, "S")
        parts.append(f"/A{model}")

        # Suppress default library embedding - we link explicitly
        parts.append("/Zl")

        # Optimization
        opt = self.cfg.compiler.optimization
        if opt == "speed":
            parts.append("/Ot")
        elif opt == "size":
            parts.append("/Os")
        elif opt == "debug":
            parts.append("/Od")
            parts.append("/Zi")

        # Warnings
        w = self.cfg.compiler.warnings
        if w >= 1:
            parts.append(f"/W{min(w, 3)}")

        # Defines
        for d in self.cfg.compiler.defines:
            parts.append(f"/D{d}")

        # Include path - always add INCLUDE
        parts.append("/IINCLUDE")

        # Extra flags
        parts.extend(self.cfg.compiler.extra_flags)

        return " ".join(parts)

    def _output_name(self, ext: str) -> str:
        """Return uppercase output filename."""
        return self.cfg.name.upper() + ext

    def _link_flags(self) -> list[str]:
        """Return common linker flags."""
        flags = []
        if "/NOE" not in self.cfg.linker.extra_flags:
            flags.append("/NOE")
        if "/NOI" not in self.cfg.linker.extra_flags:
            flags.append("/NOI")
        flags.extend(self.cfg.linker.extra_flags)
        if self.cfg.linker.stack_size:
            flags.append(f"/STACK:{self.cfg.linker.stack_size}")
        return flags

    def _normalize_libs(self, libs: list[str]) -> list[str]:
        """Ensure library names have .LIB extension."""
        result = []
        for lib in libs:
            if not lib.upper().endswith(".LIB"):
                lib = lib + ".LIB"
            result.append(lib)
        return result


# ======================================================================
# DOS EXE target
# ======================================================================

class DosExeTarget(Target):
    """Standard DOS .EXE using MS C runtime."""

    # Default C runtime library per memory model
    MODEL_LIBS = {
        "tiny": "SLIBC.LIB",
        "small": "SLIBC.LIB",
        "medium": "MLIBC.LIB",
        "compact": "CLIBC.LIB",
        "large": "LLIBC.LIB",
    }

    # Floating-point emulation library per memory model (provides __fltused, FI*RQQ symbols)
    MODEL_FP_LIBS = {
        "tiny": "SLIBFP.LIB",
        "small": "SLIBFP.LIB",
        "medium": "MLIBFP.LIB",
        "compact": "CLIBFP.LIB",
        "large": "LLIBFP.LIB",
    }

    def _compile_flags(self) -> str:
        return self._common_compile_flags()

    def _link(self, obj_files: list[str], sources: list[SourceFile]) -> str:
        objs = "+".join(obj_files)
        exe_name = self._output_name(".EXE")
        exe_path = f"SRC\\{exe_name}"
        map_name = self._output_name(".MAP") if self.cfg.linker.map_file else "NUL"
        map_path = f"SRC\\{map_name}" if self.cfg.linker.map_file else "NUL"

        # Libraries - normalize names, include C runtime + helper lib
        libs = self._normalize_libs(self.cfg.linker.libraries)
        crt_lib = self.MODEL_LIBS.get(self.cfg.compiler.model, "SLIBC.LIB")
        if crt_lib not in libs:
            libs.append(crt_lib)
        if "LIBH.LIB" not in libs:
            libs.append("LIBH.LIB")
        fp_lib = self.MODEL_FP_LIBS.get(self.cfg.compiler.model, "SLIBFP.LIB")
        if fp_lib not in libs:
            libs.append(fp_lib)
        if "EM.LIB" not in libs:
            libs.append("EM.LIB")
        libs_str = "+".join(libs)

        flags = self._link_flags()
        flags_str = " ".join(flags)
        # LINK positional format: LINK [flags] objs,exe,map,libs;
        args = f"{flags_str} {objs},{exe_path},{map_path},{libs_str};"
        self.runner.run_checked("BIN\\LINK.EXE", args, tool_name="LINK.EXE")
        return exe_path


# ======================================================================
# DOS COM target
# ======================================================================

class DosComTarget(Target):
    """DOS .COM (tiny model)."""

    def _compile_flags(self) -> str:
        flags = self._common_compile_flags()
        # Force tiny model for .COM
        flags = flags.replace(f"/A{MODEL_FLAGS.get(self.cfg.compiler.model, 'S')}", "/AT")
        return flags

    def _link(self, obj_files: list[str], sources: list[SourceFile]) -> str:
        objs = "+".join(obj_files)
        com_name = self._output_name(".COM")
        exe_path = f"SRC\\{self._output_name('.EXE')}"
        map_path = "NUL"

        flags = self._link_flags()
        flags_str = " ".join(flags)
        args = f"{flags_str} /T {objs},{exe_path},{map_path},;"
        self.runner.run_checked("BIN\\LINK.EXE", args, tool_name="LINK.EXE")

        # /T makes LINK produce a .COM instead of .EXE if possible
        # The output is at the exe_path but as .EXE name (LINK /T renames to .COM)
        # Actually LINK /T just outputs a .EXE that's COM-format
        # Need to check what LINK.EXE actually produces
        return exe_path


# ======================================================================
# HP 95LX target
# ======================================================================

class HP95LXTarget(Target):
    """HP 95LX .EXM (System Manager compliant)."""

    def _compile_flags(self) -> str:
        flags = self._common_compile_flags()
        # Force small model and no stack probes
        flags = flags.replace(f"/A{MODEL_FLAGS.get(self.cfg.compiler.model, 'S')}", "/AS")
        if "/Gs" not in flags:
            flags += " /Gs"
        return flags

    def _link(self, obj_files: list[str], sources: list[SourceFile]) -> str:
        objs = "+".join(obj_files)
        exe_name = self._output_name(".EXE")
        exe_path = f"SRC\\{exe_name}"
        map_name = self._output_name(".MAP") if self.cfg.linker.map_file else "NUL"
        map_path = f"SRC\\{map_name}" if self.cfg.linker.map_file else "NUL"

        # HP 95LX links with CSVC.OBJ and CRT0.OBJ from SDK
        sdk_objs = "TOOLS\\CSVC.OBJ+TOOLS\\CRT0.OBJ"

        normalized = self._normalize_libs(self.cfg.linker.libraries)
        libs = "+".join(normalized) if normalized else ""

        flags = " ".join(self._link_flags())
        if "/M" not in flags:
            flags = "/M " + flags
        args = f"{flags} {objs}+{sdk_objs},{exe_path},{map_path},{libs};"
        self.runner.run_checked("BIN\\LINK.EXE", args, tool_name="LINK.EXE")
        return exe_path

    def _post_process(self, output_dos: str) -> Path:
        """Convert .EXE to .EXM via E2M."""
        host_path = self.build_dir / output_dos.replace("\\", "/")
        # E2M takes basename without extension - it appends .EXE and .MAP itself
        base_dos = output_dos.rsplit(".", 1)[0]
        self.runner.run_checked("TOOLS\\E2M.EXE", base_dos, tool_name="E2M.EXE")
        # E2M produces .EXM alongside the .EXE
        exm_path = host_path.with_suffix(".EXM")
        return exm_path


# ======================================================================
# HP 200LX target (identical pipeline to 95LX)
# ======================================================================

class HP200LXTarget(HP95LXTarget):
    """HP 200LX .EXM (identical pipeline to HP 95LX)."""
    pass


# ======================================================================
# Windows 3.x (Win16) target
# ======================================================================

class Win16Target(Target):
    """Windows 3.x 16-bit .EXE."""

    def _compile_flags(self) -> str:
        flags = self._common_compile_flags()
        # Force small model and Windows prolog/epilog
        flags = flags.replace(f"/A{MODEL_FLAGS.get(self.cfg.compiler.model, 'S')}", "/AS")
        if "/Gw" not in flags:
            flags += " /Gw"
        return flags

    def _link(self, obj_files: list[str], sources: list[SourceFile]) -> str:
        objs = "+".join(obj_files)
        exe_name = self._output_name(".EXE")
        exe_path = f"SRC\\{exe_name}"
        map_name = self._output_name(".MAP") if self.cfg.linker.map_file else "NUL"
        map_path = f"SRC\\{map_name}" if self.cfg.linker.map_file else "NUL"

        # Windows libraries
        libs = list(self.cfg.linker.libraries)
        for default_lib in ["SLIBCEW", "LIBW"]:
            if default_lib not in libs:
                libs.append(default_lib)
        libs_str = "+".join(libs)

        # Check for .DEF file
        def_file = ""
        def_path = self.build_dir / "SRC" / self._output_name(".DEF")
        if def_path.exists():
            def_file = f"SRC\\{self._output_name('.DEF')}"

        flags = self._link_flags()
        flags.append("/ALIGN:16")
        flags_str = " ".join(flags)

        # Use LINK4 for Windows if available, otherwise LINK
        linker = "BIN\\LINK4.EXE"
        linker_path = self.build_dir / "BIN" / "LINK4.EXE"
        if not linker_path.exists():
            linker = "BIN\\LINK.EXE"

        args = f"{flags_str} {objs},{exe_path},{map_path},{libs_str},{def_file};"
        self.runner.run_checked(linker, args, tool_name="LINK")
        return exe_path

    def _post_process(self, output_dos: str) -> Path:
        """Bind resources with RC if .RES exists."""
        host_path = self.build_dir / output_dos.replace("\\", "/")

        # Check for .RC file in sources
        rc_name = self._output_name(".RC")
        rc_src = self.build_dir / "SRC" / rc_name
        if rc_src.exists():
            # Compile .RC to .RES
            res_path = f"SRC\\{self._output_name('.RES')}"
            self.runner.run_checked("BIN\\RC.EXE", f"/r SRC\\{rc_name}",
                                    tool_name="RC.EXE")
            # Bind .RES to .EXE
            self.runner.run_checked("BIN\\RC.EXE", f"{res_path} {output_dos}",
                                    tool_name="RC.EXE")

        return host_path


# ======================================================================
# Factory
# ======================================================================

TARGET_CLASSES = {
    "dos-exe": DosExeTarget,
    "dos-com": DosComTarget,
    "hp95lx": HP95LXTarget,
    "hp200lx": HP200LXTarget,
    "win16": Win16Target,
}

def create_target(cfg: ProjectConfig, runner: XTRunner, build_dir: Path) -> Target:
    """Create a target instance from config."""
    cls = TARGET_CLASSES.get(cfg.target)
    if cls is None:
        print(f"error: unknown target '{cfg.target}'", file=sys.stderr)
        print(f"valid targets: {', '.join(TARGET_CLASSES.keys())}", file=sys.stderr)
        sys.exit(1)
    return cls(cfg, runner, build_dir)
