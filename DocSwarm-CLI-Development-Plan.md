# DocSwarm CLI: Complete Phased Development Plan

This document serves as the primary technical roadmap for building the **DocSwarm Local CLI** from start to finish. It is based directly on the transition from the web-based ZIP-upload architecture to a deterministic, offline, local static-analysis engine.

## 1. Recommendations and Technical Foundations

Before diving into the phases, here are the core technical standards and recommendations for the CLI tool.

### 1.1 CLI Architecture and Core Modules
The system follows a layered architecture to keep the CLI logic strictly decoupled from the analysis engine:
1.  **CLI Layer**: Handles terminal input/output, commands (`analyze`, `deps`, etc.), and argument parsing using **Typer** and **Rich**.
2.  **Application Layer**: Services orchestrating the flow (e.g., `AnalysisService`, `ReportService`).
3.  **Core Engine**: The deterministic offline brain:
    *   **Scanner**: Traverses local workspace, respects ignores, detects file types.
    *   **Parser Registry**: Uses **Tree-sitter** to generate syntax trees.
    *   **Resolver**: Resolves import paths to actual files.
    *   **Graph Builder**: Models relationships using **NetworkX**.
    *   **Architecture Analyzer**: Computes complexity, spots hotspots and circular dependencies.
    *   **Rule Engine**: Calculates the Architecture Health Score.
4.  **Output Generators**: Formats the internal graph into Markdown, JSON, HTML, and DOT/SVG formats.

### 1.2 Project and Folder Structure
Use a modern Python structure. Do not place everything in a single script.
```text
docswarm/
├── cli/                 # Typer commands (main.py, analyze.py, etc.)
├── core/                # Domain models and application services
├── scanner/             # Filesystem traversal and language detection
├── parsers/             # Tree-sitter language adapters
├── resolver/            # Import path resolution logic
├── graph/               # NetworkX builder and graph algorithms
├── architecture/        # Role classification, metrics, rules, health score
├── reports/             # Renderers (Markdown, HTML, JSON, DOT)
├── tests/               # Pytest suite and fixtures
├── pyproject.toml       # Dependencies and build configuration
└── README.md
```

### 1.3 Code Organization & Configuration
-   **Configuration**: Rely on zero-configuration by default. Optionally support a `.docswarm.yaml` in the project root for custom ignores and rule thresholds.
-   **Dependency Management**: Use `pyproject.toml` (with Poetry or standard pip/setuptools) to manage dependencies (Typer, Rich, NetworkX, tree-sitter).

### 1.4 Error Handling, Logging, and Debugging
-   **Error Handling**: Differentiate between Fatal (abort), Warning (skip file, continue), and Informational. Never crash the tool on a single malformed file.
-   **Logging**: Use standard Python `logging` for debug traces (hidden by default). Use `Rich` to display user-friendly progress indicators, warnings, and success messages in the terminal.
-   **Exit Codes**: Use standard POSIX exit codes (0 = Success, 1 = Analysis completed with issues/warnings, 2 = Fatal error, 3 = Invalid args) for CI/CD integrations.

### 1.5 Input/Output Handling
-   **Input**: The local directory (current working directory `.` by default).
-   **Output**: Console reports (using Rich) and persistent artifacts saved inside a local `.docswarm/` directory within the target project.

### 1.6 Performance and Optimization
-   **Large Files**: Set hard limits on file sizes (e.g., skip parsing files > 5MB) and directory depths to prevent memory overflow.
-   **Cache**: For V1, use JSON for caching (e.g., `index.json`, `graph.json`). Avoid heavy databases like SQLite or ChromaDB in V1.

### 1.7 Security and Reliability
-   **Offline Guarantee**: Ensure there are zero network calls in the core engine runtime. The code must never transmit telemetry or source code.
-   **Symlinks**: Explicitly ignore symlinks by default to prevent escaping the workspace root.
-   **Secrets**: Exclude contents of `.env` or credential files from logs/reports.

### 1.8 Testing Strategy
-   **Unit Tests**: Test each module independently (scanner, parsers, resolver).
-   **Integration Tests**: Run the full CLI against controlled fixture repositories.
-   **Determinism Tests**: Running analysis twice on the same codebase must yield identical output hashes (barring timestamps).
-   **Offline Tests**: Run tests with internet disconnected.

### 1.9 Packaging, Distribution, Installation
-   **Packaging**: Use `PyInstaller` to compile the Python package into a standalone Windows `.exe`.
-   **Installation**: Provide a simple PowerShell install script that downloads the binary and adds it to the user's `PATH`.

### 1.10 Future Extensibility
-   Keep AI (Gemini), LSP integration, change-impact analysis, and Git integration strictly out of V1. The engine's decoupled architecture guarantees these can be added as adapters later.

---

## 2. Phased Development Roadmap

### Phase 0: Project Initialization & Architecture Setup
**1. What needs to be built**: The base Python project structure, dependency files, and core domain object models (e.g., `File`, `Dependency`, `GraphModel`).
**2. Why it is required**: Establishes a clean, professional foundation before any logic is written.
**3. How it should be implemented**: Initialize a Git repo, set up `pyproject.toml`, define abstract data classes for the domain, and copy reusable code from the old project.
**4. Modules to create**: `pyproject.toml`, `core/models.py`.
**5. Component interaction**: These core models will be passed around between all future modules (Scanner -> Parser -> Graph -> Report).
**6. Technical considerations**: Keep data classes simple and serializable to JSON.
**7. Dependencies**: `pydantic` or standard `dataclasses`.
**8. Expected outcome**: An empty but well-structured Python project.
**9. Testing**: Basic test verifying the environment works.

> **MANUAL WORK REQUIRED**
> *   **What**: Set up the local development environment.
> *   **Where**: On your Windows machine, in your EDI project folder.
> *   **Why**: You need a clean slate to build the CLI separate from the Next.js/FastAPI codebase.
> *   **Action Items**:
>     1. Initialize a new Git repository for `docswarm-cli`.
>     2. Install Python 3.10+ and set up a virtual environment (`python -m venv .venv`).
>     3. Create the folder structure outlined in Section 1.2.
>     4. From your *old* DocSwarm project, extract the abstract Python logic (NetworkX graph logic, architecture blueprint concepts, role detection rules) and place them into the new `core/` or `graph/` folders as reference materials.
> *   **Expected Result**: A running Python virtual environment with a clean folder structure.

---

### Phase 1: Core Analysis Engine Abstraction (The Foundation)
**1. What needs to be built**: A dummy pipeline that connects `Scanner` -> `Analyzer` -> `Reporter` programmatically without the CLI interface.
**2. Why it is required**: To enforce that the engine does not depend on CLI inputs/outputs (like `print()`) directly.
**3. How it should be implemented**: Create an `AnalysisService` class that orchestrates the flow. For now, mock the outputs.
**4. Modules to create**: `core/engine.py`.
**5. Component interaction**: Acts as the central controller for the analysis lifecycle.
**6. Technical considerations**: Must be fully synchronous and local.
**7. Dependencies**: None.
**8. Expected outcome**: A script that can be run in Python: `engine.analyze("./sample")`.
**9. Testing**: Unit tests asserting the engine calls the steps in order.

---

### Phase 2: Workspace Scanner
**1. What needs to be built**: A module to traverse the local directory, respect ignores, and classify files.
**2. Why it is required**: Replaces the old ZIP upload and extraction process.
**3. How it should be implemented**: Use `os.walk` or `pathlib.rglob`. Implement rules to ignore `.git/`, `node_modules/`, `dist/`, etc., and detect languages based on file extensions.
**4. Modules to create**: `scanner/scanner.py`.
**5. Component interaction**: Feeds a list of discovered `File` objects to the Parser Layer.
**6. Technical considerations**: Must skip symlinks and binary files. Needs safeguards against massively deep directories.
**7. Dependencies**: `pathlib`.
**8. Expected outcome**: A JSON index of all source files in a target directory.
**9. Testing**: Run against a dummy repository containing nested folders, ignored folders, and binary files to ensure they are skipped.

---

### Phase 3: Parser Layer (Tree-sitter Integration)
**1. What needs to be built**: The parser interface using Tree-sitter for TypeScript, JavaScript, and Python.
**2. Why it is required**: Replaces the fragile Regex-based JS/TS parser from the old project, providing robust, incremental syntax tree generation.
**3. How it should be implemented**: Create a `ParserRegistry` that routes a file to `TypeScriptAnalyzer`, `PythonAnalyzer`, etc. Use tree-sitter queries to extract `import` and `export` statements, classes, and functions.
**4. Modules to create**: `parsers/base.py`, `parsers/typescript.py`, `parsers/python.py`.
**5. Component interaction**: Receives files from the Scanner, returns AST metadata and raw import strings to the Resolver.
**6. Technical considerations**: Tree-sitter requires compiled language grammars.
**7. Dependencies**: `tree-sitter`, `tree-sitter-python`, `tree-sitter-typescript`, `tree-sitter-javascript`.
**8. Expected outcome**: Accurate extraction of imports/exports from files.
**9. Testing**: Unit tests parsing small `.ts` and `.py` fixture files.

> **MANUAL WORK REQUIRED**
> *   **What**: Install and configure Tree-sitter bindings.
> *   **Where**: In your Python virtual environment.
> *   **Why**: Tree-sitter relies on C bindings for language grammars.
> *   **Action Items**:
>     1. Run `pip install tree-sitter tree-sitter-python tree-sitter-typescript tree-sitter-javascript`.
>     2. Ensure the grammars load correctly in a simple Python test script.
> *   **Expected Result**: Python can successfully parse a dummy TS file and print its syntax tree.

---

### Phase 4: Dependency Engine & Graph Builder
**1. What needs to be built**: Path resolver and NetworkX graph generation.
**2. Why it is required**: To map raw import strings (e.g., `import { X } from '@/utils'`) to actual file paths and build the mathematical graph.
**3. How it should be implemented**: 
    *   **Resolver**: Resolve relative paths, aliases (via `tsconfig.json` if possible, or basic heuristics), and distinguish internal vs. external (npm/pip) dependencies.
    *   **Graph Builder**: Add nodes and directed edges using NetworkX `DiGraph`.
**4. Modules to create**: `resolver/resolver.py`, `graph/builder.py`.
**5. Component interaction**: Takes raw imports from the Parser, outputs a `DiGraph` to the Architecture Analyzer.
**6. Technical considerations**: If a path cannot be resolved confidently, mark it as `unresolved`—do not invent edges.
**7. Dependencies**: `networkx`.
**8. Expected outcome**: A fully populated directed graph representing the codebase.
**9. Testing**: Integration tests ensuring accurate edges are created for relative and alias imports.

---

### Phase 5: Architecture Analyzer & Rule Engine
**1. What needs to be built**: The intelligence layer computing metrics (cycles, hotspots) and the Architecture Health Score.
**2. Why it is required**: This is the core innovation of DocSwarm CLI—turning a raw graph into explainable architectural insights without relying on AI.
**3. How it should be implemented**:
    *   Use NetworkX algorithms (`nx.simple_cycles`, `nx.in_degree_centrality`) to find circular dependencies and high fan-in/fan-out modules.
    *   Implement `RoleClassifier` (heuristics on filenames/exports to detect controllers, services).
    *   Create `RuleEngine` to penalize the Health Score for violations (e.g., -15 for cycles, -10 for suspected layer violations).
**4. Modules to create**: `architecture/analyzer.py`, `architecture/rules.py`.
**5. Component interaction**: Consumes the `DiGraph` and produces an `AnalysisResult` containing warnings and scores.
**6. Technical considerations**: Keep rules heuristic-based and explicitly state when a violation is "suspected".
**7. Dependencies**: `networkx`.
**8. Expected outcome**: A scored architecture model identifying specific risks in specific files.
**9. Testing**: Construct artificial graphs in tests (e.g., A->B, B->C, C->A) and assert that the cycle rule fires correctly.

---

### Phase 6: Reporting & Output Generation
**1. What needs to be built**: Renderers for Terminal, Markdown, JSON, HTML, and DOT/SVG formats.
**2. Why it is required**: To provide machine-readable artifacts, rich documentation (replacing AI Docs), and visualizations (replacing React Flow).
**3. How it should be implemented**:
    *   Write artifacts to a `.docswarm/` folder.
    *   Generate a structured Markdown report.
    *   Convert NetworkX graph to Graphviz DOT format, then render to SVG.
**4. Modules to create**: `reports/markdown.py`, `reports/graphviz.py`, `reports/json_exporter.py`.
**5. Component interaction**: Takes the final `AnalysisResult` and formats it.
**6. Technical considerations**: For huge graphs, DOT generation might be slow or produce cluttered SVGs.
**7. Dependencies**: `pydot` (to interface with Graphviz).
**8. Expected outcome**: Generation of `.docswarm/report.md`, `graph.json`, `graph.dot`, and `graph.svg`.
**9. Testing**: Verify that output files are successfully written to disk and formatted correctly.

> **MANUAL WORK REQUIRED**
> *   **What**: Install Graphviz locally for graph rendering.
> *   **Where**: On your Windows machine.
> *   **Why**: The Python `pydot` library requires the actual Graphviz binaries to convert `.dot` files to `.svg` images.
> *   **Action Items**:
>     1. Download and install Graphviz for Windows.
>     2. Ensure the Graphviz `bin` directory is added to your system `PATH`.
>     3. Verify by running `dot -V` in PowerShell.
> *   **Expected Result**: The CLI can successfully shell out to Graphviz to generate `graph.svg`.

---

### Phase 7: CLI Interface Implementation
**1. What needs to be built**: The user-facing terminal interface.
**2. Why it is required**: To expose the engine to users via terminal commands.
**3. How it should be implemented**: Use Typer to define commands:
    *   `docswarm analyze [path]`: Runs full pipeline, prints Rich console summary, writes to `.docswarm/`.
    *   `docswarm deps [file]`: Shows incoming/outgoing for one file.
    *   `docswarm inspect [file]`: Shows role, metrics, and specific risks for one file.
    *   `docswarm graph [path]`: Just generates graph artifacts.
    *   `docswarm report [path]`: Generates reports from existing graph data.
**4. Modules to create**: `cli/main.py`, `cli/commands.py`.
**5. Component interaction**: Parses CLI args, instantiates the `AnalysisService`, and uses `Rich` to format the console output.
**6. Technical considerations**: Ensure standard exit codes are returned on failure/success.
**7. Dependencies**: `typer`, `rich`.
**8. Expected outcome**: A fully functional, polished CLI tool running locally.
**9. Testing**: Invoke Typer's `CliRunner` in pytest to simulate terminal commands.

---

### Phase 8: Testing & Hardening
**1. What needs to be built**: A robust suite of edge-case tests.
**2. Why it is required**: Developer tools must not crash on messy, real-world repositories.
**3. How it should be implemented**: Run the CLI against deliberately broken repositories, repositories with massive files, and repositories with no supported languages.
**4. Modules to create**: Various fixtures in `tests/fixtures/`.
**5. Component interaction**: N/A.
**6. Technical considerations**: Implement the formal **OFFLINE-RUN-001** test.
**7. Dependencies**: `pytest`.
**8. Expected outcome**: 100% confidence in tool stability and offline capabilities.
**9. Testing**: Turn off Wi-Fi completely on your machine and run `docswarm analyze .`. It must succeed.

---

### Phase 9: Packaging & Distribution
**1. What needs to be built**: A standalone Windows executable and installation mechanism.
**2. Why it is required**: Users should not need to install Python, Tree-sitter, or manage virtual environments to use the tool.
**3. How it should be implemented**: Use PyInstaller to bundle the CLI into `docswarm.exe`. Create a simple PowerShell installer (`install.ps1`) that downloads the executable and adds it to the user's `PATH`.
**4. Modules to create**: `docswarm.spec` (PyInstaller config), `install.ps1`.
**5. Component interaction**: Bundles all dependencies, including Tree-sitter binary `.dll`/`.so` files, into one executable.
**6. Technical considerations**: Tree-sitter binaries can be tricky to package with PyInstaller. Ensure they are explicitly added as `datas` in the spec file.
**7. Dependencies**: `pyinstaller`.
**8. Expected outcome**: A single portable `docswarm.exe` file.
**9. Testing**: Move `docswarm.exe` to a completely new folder/machine and run it.

> **MANUAL WORK REQUIRED**
> *   **What**: Compile and test the standalone executable.
> *   **Where**: On your Windows machine.
> *   **Why**: PyInstaller creates platform-specific binaries. You must compile and test it manually.
> *   **Action Items**:
>     1. Run `pyinstaller --onefile --name docswarm cli/main.py`.
>     2. Verify that Tree-sitter language libraries are correctly bundled.
>     3. Take the resulting `dist/docswarm.exe` and test it on a different project folder without activating your Python virtual environment.
>     4. Create a GitHub Release and upload the `.exe` so the installation script has a URL to download from.
> *   **Expected Result**: A functioning standalone CLI tool that requires no external dependencies (other than Graphviz for SVG generation) to run.

---
*This roadmap correctly constraints the project scope for V1, keeping it strictly deterministic and offline, maximizing the EDI engineering value while remaining highly achievable for a student team.*
