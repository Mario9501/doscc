"""Build workspace management for doscc.

Creates a temporary directory tree with symlinks that merges the toolchain,
SDK, and project sources into a single directory that XT maps as C:\\.
"""

import glob
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from config import GlobalConfig, ProjectConfig, ToolchainConfig, SDKConfig, LIBS_DIR


@dataclass
class SourceFile:
    """A source file and its expected object file in the workspace."""
    host_path: Path      # original file on host
    workspace_path: Path  # copy in .doscc/build/SRC/
    dos_path: str         # DOS path relative to C:\ (e.g. SRC\FOO.C)
    obj_path: str         # DOS path for .OBJ (e.g. SRC\FOO.OBJ)


class Workspace:
    """Manages the .doscc/build/ workspace directory."""

    def __init__(self, project_root: Path, project_cfg: ProjectConfig,
                 global_cfg: GlobalConfig):
        self.project_root = project_root
        self.project_cfg = project_cfg
        self.global_cfg = global_cfg
        self.build_dir = project_root / ".doscc" / "build"
        self.toolchain: ToolchainConfig = global_cfg.toolchains[project_cfg.toolchain]
        self.sdk: SDKConfig | None = None
        if project_cfg.sdk and project_cfg.sdk in global_cfg.sdks:
            self.sdk = global_cfg.sdks[project_cfg.sdk]

    def prepare(self) -> list[SourceFile]:
        """Build the workspace. Returns list of source files to compile."""
        # Clean and recreate
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True)

        self._link_bin()
        self._merge_includes()
        self._merge_libs()
        self._link_tools()
        sources = self._copy_sources()

        return sources

    def _link_bin(self) -> None:
        """Symlink toolchain BIN/ directory."""
        src = self.toolchain.path / "BIN"
        if src.exists():
            os.symlink(src, self.build_dir / "BIN")

    def _merge_includes(self) -> None:
        """Merge include directories from toolchain, SDK, and project."""
        inc_dir = self.build_dir / "INCLUDE"
        inc_dir.mkdir()

        # Toolchain includes (base layer)
        tc_inc = self.toolchain.path / "INCLUDE"
        if tc_inc.exists():
            for item in tc_inc.iterdir():
                os.symlink(item, inc_dir / item.name)

        # SDK headers (overlay)
        if self.sdk:
            headers_dir = self.sdk.path / "HEADERS"
            if headers_dir.exists():
                for item in headers_dir.iterdir():
                    dest = inc_dir / item.name
                    if not dest.exists():
                        os.symlink(item, dest)

        # Pre-built library headers (overlay)
        if LIBS_DIR.exists():
            for lib_dir in LIBS_DIR.iterdir():
                if lib_dir.is_dir():
                    for item in lib_dir.iterdir():
                        if item.suffix.upper() == ".H":
                            dest = inc_dir / item.name.upper()
                            if not dest.exists():
                                os.symlink(item, dest)

        # Project include directories (overlay)
        for inc_path in self.project_cfg.compiler.includes:
            proj_inc = self.project_root / inc_path
            if proj_inc.exists() and proj_inc.is_dir():
                for item in proj_inc.iterdir():
                    dest = inc_dir / item.name.upper()
                    if not dest.exists():
                        os.symlink(item, dest)

    def _merge_libs(self) -> None:
        """Merge library directories from toolchain and SDK."""
        lib_dir = self.build_dir / "LIB"
        lib_dir.mkdir()

        # Toolchain libs
        tc_lib = self.toolchain.path / "LIB"
        if tc_lib.exists():
            for item in tc_lib.iterdir():
                os.symlink(item, lib_dir / item.name)

        # SDK libs (if any)
        if self.sdk:
            sdk_lib = self.sdk.path / "LIB"
            if sdk_lib.exists():
                for item in sdk_lib.iterdir():
                    dest = lib_dir / item.name
                    if not dest.exists():
                        os.symlink(item, dest)

        # Pre-built library .LIB files
        if LIBS_DIR.exists():
            for doscc_lib in LIBS_DIR.iterdir():
                if doscc_lib.is_dir():
                    for item in doscc_lib.iterdir():
                        if item.suffix.upper() == ".LIB":
                            dest = lib_dir / item.name.upper()
                            if not dest.exists():
                                os.symlink(item, dest)

    def _link_tools(self) -> None:
        """Symlink SDK tools directory (E2M.EXE, CRT0.OBJ, CSVC.OBJ)."""
        if self.sdk:
            tools_dir = self.sdk.path / "TOOLS"
            if tools_dir.exists():
                os.symlink(tools_dir, self.build_dir / "TOOLS")

    def _copy_sources(self) -> list[SourceFile]:
        """Copy project source files into workspace SRC/ directory."""
        src_dir = self.build_dir / "SRC"
        src_dir.mkdir()

        sources = []
        for pattern in self.project_cfg.source_files:
            for match in sorted(glob.glob(str(self.project_root / pattern))):
                host_path = Path(match)
                if not host_path.is_file():
                    continue
                # Use uppercase name for DOS compatibility
                dos_name = host_path.name.upper()
                ws_path = src_dir / dos_name
                shutil.copy2(host_path, ws_path)

                obj_name = dos_name.rsplit(".", 1)[0] + ".OBJ"
                sources.append(SourceFile(
                    host_path=host_path,
                    workspace_path=ws_path,
                    dos_path=f"SRC\\{dos_name}",
                    obj_path=f"SRC\\{obj_name}",
                ))

        return sources
