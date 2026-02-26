"""Configuration loading and writing for doscc."""

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


GLOBAL_CONFIG_DIR = Path.home() / ".doscc"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.toml"
LIBS_DIR = GLOBAL_CONFIG_DIR / "libs"


# ======================================================================
# Data classes
# ======================================================================

@dataclass
class ToolchainConfig:
    name: str
    path: Path


@dataclass
class SDKConfig:
    name: str
    path: Path


@dataclass
class GlobalConfig:
    xt_path: str = "xt"
    toolchains: dict[str, ToolchainConfig] = field(default_factory=dict)
    sdks: dict[str, SDKConfig] = field(default_factory=dict)


@dataclass
class CompilerConfig:
    model: str = "small"
    optimization: str = ""
    warnings: int = 0
    defines: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    extra_flags: list[str] = field(default_factory=list)


@dataclass
class LinkerConfig:
    libraries: list[str] = field(default_factory=list)
    map_file: bool = True
    stack_size: int = 0
    extra_flags: list[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    name: str = ""
    target: str = "dos-exe"
    toolchain: str = "msc50"
    sdk: str = ""
    compiler: CompilerConfig = field(default_factory=CompilerConfig)
    linker: LinkerConfig = field(default_factory=LinkerConfig)
    source_files: list[str] = field(default_factory=lambda: ["*.c"])
    output_dir: str = "."


# ======================================================================
# Loading
# ======================================================================

def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start directory to find doscc.toml."""
    d = start or Path.cwd()
    while True:
        if (d / "doscc.toml").exists():
            return d
        parent = d.parent
        if parent == d:
            return None
        d = parent


def load_global_config() -> GlobalConfig:
    """Load ~/.doscc/config.toml, returning defaults if not found."""
    cfg = GlobalConfig()
    if not GLOBAL_CONFIG_PATH.exists():
        return cfg

    with open(GLOBAL_CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)

    xt = data.get("xt", {})
    cfg.xt_path = xt.get("path", "xt")

    for name, tc in data.get("toolchains", {}).items():
        cfg.toolchains[name] = ToolchainConfig(name=name, path=Path(tc["path"]))

    for name, sdk in data.get("sdks", {}).items():
        cfg.sdks[name] = SDKConfig(name=name, path=Path(sdk["path"]))

    return cfg


def load_project_config(project_root: Path) -> ProjectConfig:
    """Load doscc.toml from project root."""
    toml_path = project_root / "doscc.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    proj = data.get("project", {})
    comp = data.get("compiler", {})
    link = data.get("linker", {})
    srcs = data.get("sources", {})

    cfg = ProjectConfig()
    cfg.name = proj.get("name", project_root.name)
    cfg.target = proj.get("target", "dos-exe")
    cfg.toolchain = proj.get("toolchain", "msc50")
    cfg.sdk = proj.get("sdk", "")
    cfg.output_dir = proj.get("output_dir", ".")

    cfg.compiler.model = comp.get("model", "small")
    cfg.compiler.optimization = comp.get("optimization", "")
    cfg.compiler.warnings = comp.get("warnings", 0)
    cfg.compiler.defines = comp.get("defines", [])
    cfg.compiler.includes = comp.get("includes", [])
    cfg.compiler.extra_flags = comp.get("extra_flags", [])

    cfg.linker.libraries = link.get("libraries", [])
    cfg.linker.map_file = link.get("map_file", True)
    cfg.linker.stack_size = link.get("stack_size", 0)
    cfg.linker.extra_flags = link.get("extra_flags", [])

    cfg.source_files = srcs.get("files", ["*.c"])

    # Auto-detect SDK requirement from target
    if not cfg.sdk:
        if cfg.target in ("hp95lx", "hp200lx"):
            cfg.sdk = "hp95lx"
        elif cfg.target == "win16":
            cfg.sdk = "win3x"

    return cfg


# ======================================================================
# Writing (hand-rolled TOML for setup)
# ======================================================================

def _toml_value(v) -> str:
    """Format a Python value as TOML."""
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        items = ", ".join(_toml_value(x) for x in v)
        return f"[{items}]"
    return str(v)


def write_global_config(cfg: GlobalConfig) -> None:
    """Write global config to ~/.doscc/config.toml."""
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []

    lines.append("[xt]")
    lines.append(f"path = {_toml_value(cfg.xt_path)}")
    lines.append("")

    for name, tc in cfg.toolchains.items():
        lines.append(f"[toolchains.{name}]")
        lines.append(f"path = {_toml_value(str(tc.path))}")
        lines.append("")

    for name, sdk in cfg.sdks.items():
        lines.append(f"[sdks.{name}]")
        lines.append(f"path = {_toml_value(str(sdk.path))}")
        lines.append("")

    with open(GLOBAL_CONFIG_PATH, "w") as f:
        f.write("\n".join(lines))


def write_project_config(path: Path, cfg: ProjectConfig) -> None:
    """Write a doscc.toml project config file."""
    lines = []

    lines.append("[project]")
    lines.append(f"name = {_toml_value(cfg.name)}")
    lines.append(f"target = {_toml_value(cfg.target)}")
    if cfg.toolchain != "msc50":
        lines.append(f"toolchain = {_toml_value(cfg.toolchain)}")
    if cfg.sdk:
        lines.append(f"sdk = {_toml_value(cfg.sdk)}")
    lines.append("")

    lines.append("[compiler]")
    lines.append(f"model = {_toml_value(cfg.compiler.model)}")
    if cfg.compiler.optimization:
        lines.append(f"optimization = {_toml_value(cfg.compiler.optimization)}")
    if cfg.compiler.warnings:
        lines.append(f"warnings = {_toml_value(cfg.compiler.warnings)}")
    if cfg.compiler.defines:
        lines.append(f"defines = {_toml_value(cfg.compiler.defines)}")
    if cfg.compiler.includes:
        lines.append(f"includes = {_toml_value(cfg.compiler.includes)}")
    lines.append("")

    lines.append("[linker]")
    if cfg.linker.libraries:
        lines.append(f"libraries = {_toml_value(cfg.linker.libraries)}")
    lines.append(f"map_file = {_toml_value(cfg.linker.map_file)}")
    if cfg.linker.stack_size:
        lines.append(f"stack_size = {_toml_value(cfg.linker.stack_size)}")
    lines.append("")

    lines.append("[sources]")
    lines.append(f"files = {_toml_value(cfg.source_files)}")
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
