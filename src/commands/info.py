"""doscc info - display configuration and project information."""

import sys
from pathlib import Path

from config import (
    load_global_config, load_project_config, find_project_root,
    GLOBAL_CONFIG_PATH,
)


def run(args: list[str]) -> int:
    # Global config
    print("doscc info")
    print("=" * 40)
    print()

    if GLOBAL_CONFIG_PATH.exists():
        cfg = load_global_config()
        print(f"global config: {GLOBAL_CONFIG_PATH}")
        print(f"XT path:       {cfg.xt_path}")
        print()

        if cfg.toolchains:
            print("toolchains:")
            for name, tc in cfg.toolchains.items():
                exists = tc.path.exists()
                status = "ok" if exists else "NOT FOUND"
                print(f"  {name}: {tc.path} ({status})")
        else:
            print("toolchains: none configured")
        print()

        if cfg.sdks:
            print("SDKs:")
            for name, sdk in cfg.sdks.items():
                exists = sdk.path.exists()
                status = "ok" if exists else "NOT FOUND"
                print(f"  {name}: {sdk.path} ({status})")
        else:
            print("SDKs: none configured")
    else:
        print(f"global config: not found ({GLOBAL_CONFIG_PATH})")
        print("run 'doscc setup' to configure")

    # Project config
    print()
    project_root = find_project_root()
    if project_root:
        proj = load_project_config(project_root)
        print(f"project:     {proj.name}")
        print(f"root:        {project_root}")
        print(f"target:      {proj.target}")
        print(f"toolchain:   {proj.toolchain}")
        if proj.sdk:
            print(f"SDK:         {proj.sdk}")
        print(f"model:       {proj.compiler.model}")
        if proj.compiler.defines:
            print(f"defines:     {', '.join(proj.compiler.defines)}")
        if proj.compiler.includes:
            print(f"includes:    {', '.join(proj.compiler.includes)}")
        print(f"sources:     {', '.join(proj.source_files)}")
        print(f"map file:    {'yes' if proj.linker.map_file else 'no'}")
    else:
        print("project: no doscc.toml found in current directory tree")

    return 0
