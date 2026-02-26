# doscc

DOS cross-compiler CLI tool. Wraps the [XT](https://github.com/Mario9501/XT) DOS emulator and MS C 5.0 toolchain into a modern build system for DOS, HP 95LX/200LX, and Windows 3.x targets.

## Requirements

- Python 3.11+ (uses `tomllib`)
- [XT](https://github.com/Mario9501/XT) DOS emulator (patched fork)
- MS C 5.0 toolchain (BIN/, INCLUDE/, LIB/)
- Target SDKs as needed (HP 95LX SDK, Windows 3.x SDK)

## Installation

```sh
git clone https://github.com/Mario9501/doscc.git
# Add to PATH:
export PATH="$HOME/doscc:$PATH"
```

## Quick Start

```sh
# 1. Configure toolchains
doscc setup

# 2. Create a new project
mkdir myapp && cd myapp
doscc init dos-exe

# 3. Build
doscc build

# 4. Run
doscc run
```

## Setup

Run `doscc setup` to configure:

1. **XT path** - Path to the `xt` binary
2. **Toolchain** - Path to MS C 5.0 directory (must contain `BIN/CL.EXE`)
3. **SDKs** - HP 95LX SDK, Windows 3.x SDK (optional, as needed)

Config is stored at `~/.doscc/config.toml`.

## Project Configuration

Each project has a `doscc.toml` in its root:

```toml
[project]
name = "myapp"
target = "dos-exe"    # dos-exe | dos-com | hp95lx | hp200lx | win16

[compiler]
model = "small"       # tiny | small | medium | compact | large
optimization = ""     # speed | size | debug | (empty)
warnings = 0          # 0-3
defines = []
includes = []

[linker]
libraries = []
map_file = true
stack_size = 0

[sources]
files = ["*.c"]
```

## Targets

| Target | Output | Description |
|--------|--------|-------------|
| `dos-exe` | `.EXE` | Standard DOS executable |
| `dos-com` | `.COM` | DOS .COM (tiny model) |
| `hp95lx` | `.EXM` | HP 95LX System Manager app |
| `hp200lx` | `.EXM` | HP 200LX System Manager app |
| `win16` | `.EXE` | Windows 3.x 16-bit app |

## Commands

| Command | Description |
|---------|-------------|
| `doscc build [-v]` | Compile and link the project |
| `doscc clean` | Remove build artifacts |
| `doscc setup` | Interactive configuration wizard |
| `doscc init <target> [name]` | Create project from template |
| `doscc run [program] [args]` | Run a built program via XT |
| `doscc info` | Show configuration and project info |
| `doscc toolchain [list\|add\|test]` | Manage toolchain configs |

## How It Works

XT maps one host directory as the DOS `C:` drive. doscc creates a temporary workspace (`.doscc/build/`) that merges everything via symlinks:

```
.doscc/build/          (XT sees as C:\)
  BIN/      → MSC/BIN/
  INCLUDE/  → merged MSC/INCLUDE + SDK headers + project includes
  LIB/      → merged MSC/LIB + SDK libs
  TOOLS/    → SDK/TOOLS/ (E2M.EXE, CRT0.OBJ, CSVC.OBJ)
  SRC/      → copies of project .C files
```

Source files are copied (not symlinked) because CL.EXE writes `.OBJ` alongside source files. The workspace is rebuilt each build.

## Build Pipelines

**DOS EXE**: `CL /c /AS` → `LINK /NOE /NOI` → `.EXE`

**DOS COM**: `CL /c /AT` → `LINK /T` → `.COM`

**HP 95LX/200LX**: `CL /c /AS /Gs` → `LINK /M /NOE /NOI` + csvc.obj + crt0.obj → `E2M` → `.EXM`

**Win16**: `CL /c /AS /Gw` → `LINK4 /NOE /NOI /ALIGN:16` + SLIBCEW + LIBW → `RC` (bind .RES) → `.EXE`
