# DocSwarm CLI

**Deterministic, local-first architecture analysis CLI for codebases.**

DocSwarm CLI analyzes a codebase locally, builds its dependency architecture, evaluates architectural health, and generates deterministic graph, report, and interactive visualization artifacts.

## What DocSwarm Does

DocSwarm provides a complete architecture-analysis pipeline:

- **Scans repositories** to map their internal structure.
- **Respects `.gitignore`** during workspace traversal.
- **Supports workspace configuration** through `.docswarm.yaml`.
- **Detects supported file types and languages** by extension.
- **Parses** Python, JavaScript, TypeScript, and JSX/TSX locally using Tree-sitter.
- **Resolves dependencies** between internal files.
- **Builds a dependency graph** representing the codebase.
- **Classifies architectural roles** using configurable glob patterns.
- **Evaluates declarative architectural rules**.
- **Detects cycles, hotspots, and rule violations**.
- **Generates deterministic JSON, Markdown, DOT, SVG, and interactive HTML artifacts**.
- **Provides read-only architecture queries** without re-running analysis.

## Key Characteristics

- **Deterministic analysis**: Repeated runs on the same workspace produce deterministic results.
- **Local/offline execution**: Analysis runs entirely on the local machine.
- **No LLM/cloud API requirement**: No AI API or cloud processing is required.
- **No telemetry/network dependency during analysis**.
- **Graceful parser failure handling**: Parser failures are tracked without unnecessarily terminating the full analysis.
- **Internal/external/unresolved/ambiguous dependency classification**.
- **Binary-file skipping**.
- **`.gitignore` integration**.
- **Configurable scanner exclusions**.
- **Mandatory safety exclusions** for `.git` and `.docswarm`.
- **Symlink skipping** to avoid recursion and duplicate nodes.
- **Configurable file-size limits**.
- **Bounded cycle analysis** to protect large or highly cyclic repositories.
- **Standalone interactive HTML reporting** with no external runtime assets.

---

## Installation — Windows

### Option 1: Release-Based Installer

Run the PowerShell installer from the repository:

```powershell
.\install.ps1
```

The installer:

- Downloads `docswarm.exe` from the GitHub release.
- Installs it under `%LOCALAPPDATA%\DocSwarm`.
- Adds that directory to the user's `PATH`.
- Verifies the executable.

Open a new PowerShell window afterward so the updated `PATH` is available.

### Option 2: Direct Executable

Download `docswarm.exe` from the [GitHub Release v0.2.0](https://github.com/SohamSawant21/DocSwarm_CLI/releases/tag/v0.2.0).

No Python installation or virtual environment is required for the standalone executable.

---

## System Requirements

### Standalone CLI

- Windows
- No Python installation required
- No virtual environment required
- No Tree-sitter installation required

### External Requirement

**Graphviz** (`dot.exe`) must be installed and available on `PATH` if SVG graph generation is required.

Graphviz is not bundled with DocSwarm.

---

## Quick Start

Display the CLI:

```powershell
docswarm --help
```

Run a complete analysis:

```powershell
docswarm analyze D:\Projects\MyProject
```

After analysis, DocSwarm creates a `.docswarm/` directory inside the target workspace.

---

# Configuration

DocSwarm v0.2.0 supports workspace-level configuration through:

```text
.docswarm.yaml
```

The configuration file is loaded from the target workspace.

If `.docswarm.yaml` does not exist, DocSwarm uses its built-in defaults.

Configuration is strictly validated. Malformed YAML, invalid values, or unknown fields are rejected with actionable errors rather than silently applying incorrect configuration.

### Example

```yaml
schema_version: "1.0"

scanner:
  max_file_size_kb: 2048
  custom_excludes:
    - "tests/fixtures/**"

roles:
  - role_name: Model
    patterns:
      - "*model*.py"
      - "entities/*"

  - role_name: Controller
    patterns:
      - "*controller*"
      - "routes/*"

rules:
  - id: ARCH-100
    source_role: Model
    forbidden_target_role: Controller
    severity: medium
    penalty: 10
    message: "Models should not depend on Controllers."
```

### Scanner Configuration

`scanner` controls workspace scanning:

```yaml
scanner:
  max_file_size_kb: 2048
  custom_excludes:
    - "tests/fixtures/**"
```

Exclusion precedence is:

1. Mandatory DocSwarm safety exclusions (`.git`, `.docswarm`)
2. `.gitignore` patterns
3. `.docswarm.yaml` custom exclusions

### Roles

Roles are assigned using deterministic workspace-relative glob patterns.

```yaml
roles:
  - role_name: Service
    patterns:
      - "*service*"
```

Role matching is case-insensitive and follows the configured classification order.

### Rules

Rules express bounded architectural constraints:

```yaml
rules:
  - id: ARCH-100
    source_role: Model
    forbidden_target_role: Controller
    severity: medium
    penalty: 10
    message: "Models should not depend on Controllers."
```

The rule system is declarative and bounded; it is not an arbitrary programming DSL.

---

# CLI Reference

## `docswarm analyze [path]`

Runs the complete architecture analysis pipeline:

```text
Scan → Parse → Resolve → Graph → Analyze → Reports
```

Example:

```powershell
docswarm analyze D:\Projects\MyProject
```

If `path` is omitted, the current directory is used.

The command reports:

- Health score
- Analysis state
- Files scanned
- Graph nodes
- Internal edges
- Cycles
- Hotspots
- Rule violations
- Parsing/skipping information

### Analysis State

The analysis state can indicate whether cycle enumeration completed normally or was bounded.

A bounded result is still a valid artifact, but the serialized cycle list represents only the retained bounded subset.

---

## `docswarm deps [file] [path]`

Displays dependency relationships for a specific file.

It can show:

- Incoming dependencies
- Outgoing dependencies
- External dependencies
- Unresolved dependencies
- Ambiguous dependencies

Example:

```powershell
docswarm deps src\main.py D:\Projects\MyProject
```

---

## `docswarm inspect [file] [path]`

Displays comprehensive architectural information for a file:

- Architectural role
- Fan-in
- Fan-out
- Cycle participation
- Hotspots
- Rule violations

Example:

```powershell
docswarm inspect src\main.py D:\Projects\MyProject
```

---

## `docswarm graph [path]`

Generates graph artifacts from the existing graph data.

Example:

```powershell
docswarm graph D:\Projects\MyProject
```

Produces:

```text
graph.dot
graph.svg
```

---

## `docswarm report [path]`

Regenerates the Markdown report from existing graph data.

Example:

```powershell
docswarm report D:\Projects\MyProject
```

---

## `docswarm query [path]`

Queries the existing `.docswarm/graph.json` artifact without re-running analysis.

The query command:

- Does not scan the workspace.
- Does not parse source files.
- Does not resolve dependencies.
- Does not regenerate the graph.
- Does not re-evaluate architectural rules.
- Does not load `.docswarm.yaml`.

### Filter by Role

```powershell
docswarm query D:\Projects\MyProject --role Model
```

Role matching is case-insensitive.

### Files Involved in Cycles

```powershell
docswarm query D:\Projects\MyProject --has-cycles
```

If the artifact was bounded, a warning is emitted to `stderr` explaining that the cycle results represent an incomplete subset.

### Minimum Fan-in

```powershell
docswarm query D:\Projects\MyProject --min-fan-in 5
```

### Minimum Fan-out

```powershell
docswarm query D:\Projects\MyProject --min-fan-out 10
```

### Hotspots

```powershell
docswarm query D:\Projects\MyProject --hotspot
```

### Rule Violations

```powershell
docswarm query D:\Projects\MyProject --has-violations
```

### Combining Filters

Multiple filters use strict **AND** semantics.

```powershell
docswarm query D:\Projects\MyProject --role Controller --has-violations
```

Only nodes satisfying both filters are returned.

### Query Output Contract

Query output is designed for UNIX-style/PowerShell pipelines:

- Exactly one node ID per line.
- Alphabetically sorted.
- No tables or decorative output on `stdout`.
- Warnings and errors are sent to `stderr`.
- A valid query with no matches exits successfully and prints nothing.
- At least one filter must be supplied.
- Negative fan-in/fan-out thresholds are rejected.

---

# Example Workflow

```powershell
# 1. Run the complete analysis
docswarm analyze D:\Projects\MyProject

# 2. Inspect a file
docswarm inspect src\main.py D:\Projects\MyProject

# 3. View dependencies
docswarm deps src\main.py D:\Projects\MyProject

# 4. Find architectural violations
docswarm query D:\Projects\MyProject --has-violations

# 5. Find high fan-in modules
docswarm query D:\Projects\MyProject --min-fan-in 5

# 6. Find high fan-out modules
docswarm query D:\Projects\MyProject --min-fan-out 10

# 7. Find files involved in cycles
docswarm query D:\Projects\MyProject --has-cycles

# 8. Find Controller files with violations
docswarm query D:\Projects\MyProject --role Controller --has-violations

# 9. Regenerate graph artifacts
docswarm graph D:\Projects\MyProject

# 10. Regenerate Markdown report
docswarm report D:\Projects\MyProject
```

Path separators are normalized internally, so both `/` and `\` are supported.

---

# Generated Artifacts

After:

```powershell
docswarm analyze D:\Projects\MyProject
```

DocSwarm generates:

```text
.docswarm/
├── graph.json
├── graph.dot
├── graph.svg
├── report.md
└── interactive_report.html
```

### `graph.json`

Machine-readable serialized architecture data containing the graph, analysis results, metadata, and artifact schema information.

The v0.2.0 artifact schema is:

```text
artifact_schema_version: 1.1
```

### `graph.dot`

Graphviz DOT representation of the dependency graph.

### `graph.svg`

SVG visualization generated using Graphviz.

### `report.md`

Human-readable Markdown architecture report.

### `interactive_report.html`

Standalone interactive architecture visualization.

The HTML report is self-contained:

- No CDN dependency
- No external JavaScript dependency
- No external CSS dependency
- No network connection required
- Can be opened directly in a browser

---

# Artifact Compatibility

DocSwarm v0.2.0 uses artifact schema version `1.1`.

Commands that consume existing artifacts validate the artifact before processing it.

Incompatible or legacy artifacts are rejected through the established artifact-loader error path.

If an artifact is missing, malformed, or incompatible, regenerate it:

```powershell
docswarm analyze D:\Projects\MyProject
```

---

# Supported Languages and File Types

DocSwarm recognizes:

- **Python** (`.py`)
- **JavaScript** (`.js`)
- **TypeScript** (`.ts`)
- **JSX / TSX** (`.jsx`, `.tsx`)
- **JSON** (`.json`)
- **YAML** (`.yaml`, `.yml`)
- **Markdown** (`.md`)
- **CSS** (`.css`)
- **HTML** (`.html`, `.htm`)

### Semantic Parsing

Tree-sitter semantic parsing is implemented for:

- Python
- JavaScript
- TypeScript
- TSX

JSX is handled through the JavaScript parser.

Other recognized file types can appear as graph nodes but are not semantically parsed for internal dependencies.

---

# Dependency Resolution

Dependencies are categorized as:

- **Internal / Resolved** — points to a source file inside the workspace.
- **External** — refers to a standard-library, third-party, or out-of-workspace module.
- **Unresolved** — could not be mapped to an internal workspace file.
- **Ambiguous** — maps to multiple possible internal files.

DocSwarm does not install, inspect, or contact external packages during analysis.

---

# Architecture Analysis

DocSwarm calculates and reports:

- **Health Score**
- **Fan-in**
- **Fan-out**
- **Cycles**
- **Hotspots**
- **Rule Violations**
- **Role Classifications**

## Cycle Bounding

Cycle enumeration is bounded to protect analysis from pathological graphs.

The artifact records the resulting analysis state so consumers can distinguish a complete analysis from a bounded one.

The `query --has-cycles` command reflects the serialized artifact exactly and does not recalculate cycles.

---

# Offline and Security Model

DocSwarm is designed for local execution:

- No cloud APIs.
- No LLM requirement.
- No source-code upload.
- No telemetry requirement.
- No network dependency during analysis.
- No arbitrary code execution from the analyzed repository.
- Symlinks are skipped.
- Binary files are skipped.
- Large files can be excluded through the scanner size limit.

---

# Testing

The final v0.2.0 test suite was validated with:

```text
110 passed
2 skipped
0 failed
```

The test suite covers the core scanner, parser, resolver, architecture, reporting, configuration, CLI, artifact hardening, and query functionality.

The standalone Windows executable was additionally validated outside the repository environment, including:

- CLI startup
- `--help`
- Full analysis
- `.gitignore` behavior
- `.docswarm.yaml` exclusions
- Query functionality
- Artifact generation
- Artifact metadata
- Bundled PyYAML and pathspec functionality

---

# Packaging

DocSwarm provides a PyInstaller specification:

```text
docswarm.spec
```

Build the Windows executable from source:

```powershell
pyinstaller docswarm.spec
```

The generated executable is placed under:

```text
dist\
```

The release executable is distributed as:

```text
docswarm.exe
```

---

# Developer Setup

Python 3.10+ is required for development.

Install the project:

```powershell
pip install -e .
```

Install development dependencies:

```powershell
pip install -e ".[dev]"
```

Run the test suite:

```powershell
pytest
```

Build the standalone executable:

```powershell
pyinstaller docswarm.spec
```

---

# Release Information

## DocSwarm CLI v0.2.0

**Theme:** Configurability, Reliability, and Interactive Reporting

v0.2.0 extends the deterministic/local-first v0.1.0 foundation with:

- Workspace configuration through `.docswarm.yaml`
- `.gitignore` integration
- Configurable scanner exclusions
- Configurable file-size limits
- Configurable architectural roles
- Declarative architectural rules
- Improved parsing/error reporting
- Artifact schema versioning
- Artifact validation and compatibility handling
- Bounded cycle analysis
- Standalone interactive HTML reporting
- Read-only architecture querying through `docswarm query`
- Hardened Windows standalone packaging

The Windows executable is available from the [GitHub Release v0.2.0](https://github.com/SohamSawant21/DocSwarm_CLI/releases/tag/v0.2.0).

---

# Limitations

- **Graphviz is external**: `dot.exe` must be installed separately for SVG generation.
- **Role classification is pattern-based**: Default and configured classifications depend on deterministic glob matching.
- **Cycle analysis is bounded**: A bounded analysis does not claim to contain every possible cycle.
- **Query results reflect serialized artifacts**: `docswarm query` does not re-run analysis.
- **Interactive HTML visualization**: Very large graphs may become less responsive in a browser.
- **Semantic parsing support** is limited to the implemented Tree-sitter parser paths.
- **Binary detection** uses a lightweight heuristic.
- **Symlink behavior** may depend on operating-system permissions.

---

# License

See the repository license for licensing information.
