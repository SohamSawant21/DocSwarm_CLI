# DocSwarm CLI

**Deterministic/local architecture analysis CLI for codebases.**

## What DocSwarm Does

DocSwarm provides a complete, user-facing pipeline for deep codebase architecture analysis. It:
* **Scans a repository** to map its internal structure.
* **Detects supported file types and languages** by analyzing file extensions.
* **Parses** Python, JavaScript, TypeScript, and JSX/TSX source code locally using Tree-sitter.
* **Resolves dependencies** between internal files.
* **Builds a dependency graph** representing the codebase structure.
* **Performs architecture analysis** to evaluate codebase health.
* **Detects cycles, hotspots, and rule violations** within the architecture.
* **Generates reports and graph artifacts** in multiple formats for review.

## Key Characteristics

DocSwarm is built with strict reliability guarantees:
* **Deterministic analysis**: Repeated runs on the same codebase yield identical results.
* **Local/offline execution**: All parsing, resolution, and analysis happen entirely on the local machine.
* **No LLM/cloud API requirement**: Zero dependencies on AI APIs or cloud processing.
* **No telemetry/network dependency during analysis**: The tool does not "phone home" or require an internet connection to analyze code.
* **Graceful handling of broken source files**: Malformed syntax is skipped gracefully without crashing the analysis pipeline.
* **Handling of unresolved/ambiguous/external dependencies**: Clearly separates well-resolved internal paths from ambiguous, missing, or external module references.
* **Binary-file skipping**: A lightweight heuristic identifies and safely ignores binary files.
* **Ignored directories**: Automatically skips standard ignored paths (e.g., `.git`, `node_modules`, `.venv`).
* **Symlink handling**: Symbolic links are skipped to avoid infinite loops and duplicate graph nodes.
* **Large/deep repository hardening**: Built to safely traverse large codebases and deep directory structures without stack overflows.

## Installation — Windows

### Option 1: Release-Based Installer (Recommended)
You can easily install the standalone DocSwarm CLI using the provided PowerShell script. Run the following command in PowerShell:

```powershell
.\install.ps1
```

This installer:
* Downloads the docswarm.exe executable from the DocSwarm GitHub release.
* Installs it under `%LOCALAPPDATA%\DocSwarm`.
* Adds that directory to the user's `PATH`.
* Verifies the executable.
* **Note**: You will need to open a new PowerShell window afterward to use the `docswarm` command.

### Option 2: Direct Executable
Alternatively, you can download `docswarm.exe` directly from the [GitHub Release v0.1.0](https://github.com/SohamSawant21/DocSwarm_CLI/releases/tag/v0.1.0) and place or use it independently. 
* No Python installation or virtual environment is required.

## System Requirements

**Required for standalone CLI:**
* Windows Operating System
* No Python installation required
* No virtual environment required
* No Tree-sitter installation required (parsers are bundled)

**External Requirement:**
* **Graphviz** (`dot.exe`) must be installed and available on your system `PATH` if you wish to generate SVG visual graphs. 
* *Note: Graphviz is an external tool and is not bundled with DocSwarm.*

## Quick Start

To see all available commands and options, run:
```bash
docswarm --help
```

To run a full architecture analysis on a project:
```bash
docswarm analyze D:\Path\To\Project
```

## Complete CLI Reference

* `docswarm analyze [path]`
  Runs the complete architecture analysis pipeline (scanning, parsing, resolution, graph building, and reporting) on the target workspace path. Defaults to the current directory if `[path]` is not provided.
* `docswarm deps [file] [path]`
  Displays the dependency relationships (incoming, outgoing, external, unresolved/ambiguous) for a single `[file]`. The `[path]` is an optional workspace path (defaults to current directory).
* `docswarm inspect [file] [path]`
  Displays comprehensive architectural information (role, fan-in, fan-out, cycles, hotspots, violations) for a single `[file]`. The `[path]` is an optional workspace path (defaults to current directory).
* `docswarm graph [path]`
  Explicitly generates graph artifacts (`.dot` and `.svg`) from existing graph data in the specified workspace `[path]`.
* `docswarm report [path]`
  Regenerates the Markdown report (`report.md`) from existing graph data in the specified workspace `[path]`.

## Example Workflow

A typical session utilizing DocSwarm might look like this:

```bash
# 1. Analyze the entire project to generate the graph and initial reports
docswarm analyze D:\Projects\MyProject

# 2. Inspect the architectural properties of a specific file
docswarm inspect src\main.py D:\Projects\MyProject

# 3. View the dependencies associated with that file
docswarm deps src\main.py D:\Projects\MyProject

# 4. Explicitly regenerate visual graphs (if needed)
docswarm graph D:\Projects\MyProject

# 5. Explicitly regenerate the Markdown report (if needed)
docswarm report D:\Projects\MyProject
```
*Note: Path separators are normalized internally, making the CLI agnostic to forward (`/`) or backward (`\`) slashes.*

## Generated Artifacts

Following an `analyze` run, DocSwarm generates a `.docswarm/` directory in the target workspace containing the following artifacts:

```text
.docswarm/
├── graph.json  # Raw serialized data of the domain graph and analysis results
├── graph.dot   # Graphviz DOT file representing the dependency network
├── graph.svg   # Visual SVG representation of the dependency network
└── report.md   # Comprehensive human-readable architecture report
```

## Supported Languages and File Types

DocSwarm's scanner recognizes and maps the following file types:
* **Python** (`.py`)
* **JavaScript** (`.js`)
* **TypeScript** (`.ts`)
* **JSX / TSX** (`.jsx`, `.tsx`)
* **JSON** (`.json`)
* **YAML** (`.yaml`, `.yml`)
* **Markdown** (`.md`)
* **CSS** (`.css`)
* **HTML** (`.html`, `.htm`)

**Parsing Support:** Tree-sitter parsing is specifically implemented to construct semantic dependency graphs for **Python**, **JavaScript**, **TypeScript**, and **TSX**. **JSX** files are handled dynamically through the JavaScript parser. Other recognized file types appear in the graph as nodes but are not semantically parsed for internal dependencies.

## Dependency Resolution Behavior

DocSwarm explicitly categorizes all resolved dependencies to accurately represent the codebase without making external assumptions:
* **Internal / Resolved**: Dependencies pointing to actual source files located within the analyzed workspace.
* **External**: Dependencies referring to standard libraries, third-party packages, or out-of-workspace modules.
* **Unresolved**: Dependency statements for which no file could be found within the workspace.
* **Ambiguous**: Dependency references that map to multiple possible internal files (e.g., duplicated filenames in conflicting resolution paths).

*Note: External packages are NEVER installed, inspected, or contacted over the network. The resolver explicitly keeps external, unresolved, and ambiguous dependencies separate from internal structural graph edges.*

## Architecture Analysis

The analysis pipeline generates the following user-facing outputs:
* **Health Score**: A quantified 0-100 score representing the architectural health based on violations and complexity.
* **Dependency Relationships**: Internal fan-in and fan-out metrics indicating code coupling.
* **Cycles**: Detection of circular dependency loops.
* **Hotspots**: Identification of highly connected files that represent potential bottlenecks.
* **Architectural Rule Violations**: Breakages of common structural rules (e.g., UI code directly importing database drivers).
* **File Roles / Architectural Classification**: Heuristic classification of files (e.g., Models, Views, Controllers, Utilities).

## Offline Behavior

DocSwarm's analysis pipeline is designed to run locally and was explicitly tested under network-blocked conditions to ensure complete functionality without internet access. It requires no cloud APIs, does not send telemetry, and operates entirely using local compute.

## Testing and Hardening

The CLI and underlying core have been validated against a wide variety of edge cases:
* Empty repositories
* Unsupported languages
* Malformed Python and TypeScript code
* Unresolved dependencies
* Ambiguous dependencies
* Circular dependencies
* External dependencies
* Ignored directories
* Binary files (graceful skipping)
* Symlinks (bypassed to avoid recursion)
* Deep directory structures
* Large files
* Deterministic repeated runs
* CLI error handling
* Strict offline execution

## Packaging

The repository provides the necessary tools for Windows packaging:
* `docswarm.spec`: PyInstaller specification file.
* `docswarm_entry.py`: Isolated entry point for the compiled binary.
* A PyInstaller-based Windows packaging workflow that bundles all dependencies into a standalone `docswarm.exe`.

*Internal PyInstaller implementation details are maintained in developer/build documentation.*

## Building from Source / Developer Setup

If you prefer to run or build DocSwarm from the source code:

1. **Python Requirement**: Python 3.10+ is required.
2. **Installation**: Install dependencies using `pyproject.toml`.
   ```bash
   pip install -e .
   ```
3. **Development Dependencies**: Install with the `dev` flag to include `pytest` for running the test suite.
   ```bash
   pip install -e .[dev]
   pytest
   ```
4. **Building the Executable**: Build the standalone Windows executable using PyInstaller.
   ```bash
   pyinstaller docswarm.spec
   ```
   The resulting executable will be created in the `dist/` directory.

## Release Information

The Windows executable is distributed in the [v0.1.0 GitHub Release](https://github.com/SohamSawant21/DocSwarm_CLI/releases/tag/v0.1.0). The release contains the `docswarm.exe` Windows executable.

## Limitations

* **Graphviz is external**: `dot.exe` must be provided by the user to generate SVG graphs.
* **Heuristic Classification**: Architecture classification is heuristic and based on path and file characteristics.
* **Parser Support**: Only the explicitly implemented language parsers (Python, JS, TS, TSX, JSX) are described as parser-supported.
* **Binary Detection**: Binary file detection uses a lightweight heuristic (null-byte checking).
* **Symlink Testing**: Windows symlink testing and behavior may depend on specific OS privileges.
