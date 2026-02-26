"""doscc init - create a new project from template."""

import sys
from pathlib import Path

from config import ProjectConfig, CompilerConfig, LinkerConfig, write_project_config


# ======================================================================
# Templates (embedded strings)
# ======================================================================

TEMPLATES = {
    "dos-exe": {
        "doscc.toml": ProjectConfig(
            name="",  # filled from project name
            target="dos-exe",
            compiler=CompilerConfig(model="small"),
            linker=LinkerConfig(),
            source_files=["*.c"],
        ),
        "main.c": """\
#include <stdio.h>

int main(int argc, char *argv[])
{
    printf("Hello, DOS!\\n");
    return 0;
}
""",
    },
    "dos-com": {
        "doscc.toml": ProjectConfig(
            name="",
            target="dos-com",
            compiler=CompilerConfig(model="tiny"),
            linker=LinkerConfig(map_file=False),
            source_files=["*.c"],
        ),
        "main.c": """\
#include <stdio.h>

int main()
{
    printf("Hello, DOS!\\n");
    return 0;
}
""",
    },
    "hp95lx": {
        "doscc.toml": ProjectConfig(
            name="",
            target="hp95lx",
            sdk="hp95lx",
            compiler=CompilerConfig(model="small"),
            linker=LinkerConfig(),
            source_files=["*.c"],
        ),
        "main.c": """\
#include <interfac.h>
#include <event.h>

int main(int argc, char *argv[])
{
    EVENT event;
    int done = 0;

    m_init();
    m_fini();

    m_disp(0, 0, "Hello, HP 95LX!", 15, 0x07, 0);

    while (!done) {
        m_event(&event);
        if (event.kind == E_KEY && event.data == 27)
            done = 1;
    }

    m_fini();
    return 0;
}
""",
    },
    "hp200lx": {
        "doscc.toml": ProjectConfig(
            name="",
            target="hp200lx",
            sdk="hp95lx",
            compiler=CompilerConfig(model="small"),
            linker=LinkerConfig(),
            source_files=["*.c"],
        ),
        "main.c": """\
#include <interfac.h>
#include <event.h>

int main(int argc, char *argv[])
{
    EVENT event;
    int done = 0;

    m_init();
    m_fini();

    m_disp(0, 0, "Hello, HP 200LX!", 16, 0x07, 0);

    while (!done) {
        m_event(&event);
        if (event.kind == E_KEY && event.data == 27)
            done = 1;
    }

    m_fini();
    return 0;
}
""",
    },
    "win16": {
        "doscc.toml": ProjectConfig(
            name="",
            target="win16",
            sdk="win3x",
            compiler=CompilerConfig(model="small"),
            linker=LinkerConfig(),
            source_files=["*.c"],
        ),
        "main.c": """\
#include <windows.h>

int PASCAL WinMain(HANDLE hInstance, HANDLE hPrevInstance,
                   LPSTR lpCmdLine, int nCmdShow)
{
    MessageBox(NULL, "Hello, Windows!", "doscc", MB_OK);
    return 0;
}
""",
        "main.rc": """\
#include <windows.h>
""",
        "main.def": """\
NAME        MAIN
DESCRIPTION 'doscc Win16 application'
EXETYPE     WINDOWS
STUB        'WINSTUB.EXE'
CODE        PRELOAD MOVEABLE DISCARDABLE
DATA        PRELOAD MOVEABLE MULTIPLE
HEAPSIZE    1024
STACKSIZE   8192
""",
    },
}


def run(args: list[str]) -> int:
    if not args:
        print("usage: doscc init <target> [name]", file=sys.stderr)
        print(f"targets: {', '.join(TEMPLATES.keys())}", file=sys.stderr)
        return 1

    target = args[0]
    if target not in TEMPLATES:
        print(f"error: unknown target '{target}'", file=sys.stderr)
        print(f"valid targets: {', '.join(TEMPLATES.keys())}", file=sys.stderr)
        return 1

    name = args[1] if len(args) > 1 else Path.cwd().name

    template = TEMPLATES[target]
    cwd = Path.cwd()

    # Check for existing doscc.toml
    if (cwd / "doscc.toml").exists():
        print("error: doscc.toml already exists in current directory", file=sys.stderr)
        return 1

    # Write doscc.toml
    cfg = template["doscc.toml"]
    cfg.name = name
    write_project_config(cwd / "doscc.toml", cfg)
    print(f"created doscc.toml ({target})")

    # Write source files
    for filename, content in template.items():
        if filename == "doscc.toml":
            continue
        if isinstance(content, str):
            dest = cwd / filename
            if not dest.exists():
                dest.write_text(content)
                print(f"created {filename}")

    print(f"\nproject '{name}' initialized for target '{target}'")
    print("run 'doscc build' to compile")
    return 0
