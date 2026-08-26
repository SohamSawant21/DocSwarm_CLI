# DocSwarm CLI v0.2.0 — Planning & Roadmap

## 1. Executive Summary

DocSwarm CLI v0.1.0 successfully delivered a deterministic, local-first architecture analysis tool. 

The primary objective for **v0.2.0** is defined as: **"Configurability, Reliability, and Interactive Reporting"**. 

This release will make the existing v0.1.0 engine less rigid, more configurable, more transparent about failures, safer for large projects, and capable of producing self-contained interactive HTML visualizations, all while strictly preserving the offline and deterministic constraints of the original architecture. 

## 2. Verified v0.1.0 Baseline

A direct inspection of the v0.1.0 repository confirms the following facts which inform the v0.2.0 roadmap:

*   **Orchestration**: `core/engine.py` already defines an `AnalysisService` protocol, but the actual execution is currently hardcoded sequentially in `cli/commands.py`.
*   **Parsers**: An explicit `ParserRegistry` exists in `parsers/registry.py`. `ParsedMetadata` (in `parsers/base.py`) already contains a `has_syntax_error` flag to represent Tree-sitter AST errors.
*   **Rules & Roles**: `architecture/analyzer.py` and `architecture/rules.py` use hardcoded heuristic strings and explicit rule logic (e.g., "Models should not depend on Controllers").
*   **Artifacts**: `reports/` generates `.docswarm/graph.json`, `report.md`, `graph.dot`, and `graph.svg`.

## 3. Architecture Changes

*   **Refactor Orchestration**: `cli/commands.py` will be stripped of execution logic. `core/engine.py`'s `AnalysisService` will be extended to handle the actual orchestration (Scan -> Parse -> Resolve -> Analyze -> Report).
*   **Explicit Registry**: We will **NOT** build dynamic plugin discovery. `ParserRegistry` will explicitly register the included parsers during `AnalysisService` initialization to remain deterministic and PyInstaller-friendly.
*   **Typed Configuration**: Introduction of Pydantic-based models to represent user configuration loaded from `.docswarm.yaml`. Existing v0.1.0 hardcoded heuristics will be ported into the built-in Pydantic defaults to preserve backward compatibility.

## 4. Configuration Schema Proposal

The configuration system will use strict Pydantic models. 

**Precedence Order:**
Built-in defaults (v0.1.0 heuristics) -> `.docswarm.yaml` -> CLI overrides (where applicable).

**Behavior & Error Handling:**
*   **Discovery**: The engine will strictly look for `.docswarm.yaml` relative to the target workspace supplied to `docswarm analyze`. Parent-directory discovery is out of scope.
*   **Missing File**: If not found, the built-in Pydantic defaults (representing v0.1.0 logic) are used.
*   **Valid Configuration**: A valid YAML file overrides or extends the defaults.
*   **Malformed YAML / Schema Validation Failure**: The system will **fail clearly with an actionable error**. It will NOT silently fall back to defaults, ensuring users do not mistakenly believe their invalid configuration was applied.
*   **Unknown Fields**: Unknown fields will be rejected with a clear validation error (strict Pydantic parsing).

**Proposed Schema (Conceptual):**
```yaml
# .docswarm.yaml
schema_version: "1.0"

scanner:
  max_file_size_kb: 2048
  custom_excludes:
    - "tests/fixtures/**"

roles:
  - role_name: Model
    # Glob patterns ONLY. Workspace-relative and deterministic.
    patterns: ["*model*.py", "entities/*"]
  - role_name: Controller
    patterns: ["*controller*", "routes/*"]

rules:
  - id: ARCH-100
    source_role: Model
    forbidden_target_role: Controller
    severity: medium
    penalty: 10
    message: "Models should not depend on Controllers."
```
*Note: The rule system is strictly a bounded declarative model, not an arbitrary programming DSL.*

## 5. Detailed Phased Implementation Plan

### Phase 1 — Core Stabilization & Existing Engine Refactor
*   **Objective**: Refactor existing pipeline and improve error visibility.
*   **Implementation**: 
    *   Move sequential execution from `cli/commands.py` to `AnalysisService` in `core/engine.py`.
    *   Implement precise parsing error tracking. Differentiate between:
        1. `syntax_error` (`has_syntax_error=True` from Tree-sitter).
        2. `parser_exception` (Python exception during parsing execution).
        3. `skipped_binary` / `skipped_oversized`.
    *   Catch, log, and report `parser_exception` in the CLI summary without halting the full analysis.
*   **Testing**: Assert that `AnalysisService` correctly outputs the pipeline. Test parser exceptions are caught and reported without crashing.

### Phase 2 — Configuration Foundation
*   **Objective**: Build the Pydantic configuration models and preserve v0.1.0 defaults.
*   **Implementation**:
    *   Create `core/config.py` with `DocSwarmConfig` Pydantic models. Port v0.1.0 logic into default parameters.
    *   Implement strict YAML loading. Fail visibly on syntax/schema/unknown field errors.
*   **Testing**: 
    *   Test default initialization and explicit regression tests proving a project without `.docswarm.yaml` behaves exactly as it did in v0.1.0.
    *   Test loading valid YAML, handling malformed YAML (fails with actionable error), and schema validation failures (fails with actionable error).

### Phase 3 — Scanner & `.gitignore` Integration
*   **Objective**: Respect Git ignores and enforce file size limits.
*   **Implementation**:
    *   Integrate `pathspec` into `scanner/scanner.py`.
    *   Enforce path exclusion precedence: 
        1. Mandatory DocSwarm safety (`.docswarm/`, `.git/`).
        2. `.gitignore` patterns.
        3. `.docswarm.yaml` custom exclusions.
    *   Implement the configurable `max_file_size_kb` policy and track skipped oversized files.
*   **Testing**: Test normal ignores, directory ignores, wildcard/nested/negation patterns, and precedence ensuring safety directories cannot be included. Test file boundaries (exact size, over size) and user reporting.

### Phase 4 — Configurable Architecture Rules/Roles
*   **Objective**: Replace hardcoded logic with declarative configuration using Glob matching.
*   **Implementation**:
    *   Inject `DocSwarmConfig` into `ArchitectureAnalyzer` and `RuleEngine`.
    *   Apply role classifications based on the configured workspace-relative glob patterns.
    *   Evaluate declarative constraints (`source_role` -> `forbidden_target_role`).
*   **Testing**: Verify rules apply correctly. Verify heuristic semantic preservation (v0.1.0 baseline behavior).

### Phase 5 — Artifact Compatibility + Interactive HTML Reporting
*   **Objective**: Add schema versioning, artifact error handling, and self-contained visualization.
*   **Implementation**:
    *   Add `schema_version` and `docswarm_version` metadata to the `graph.json` models.
    *   Create `reports/html_reporter.py`. Embed a JS graphing library (e.g., Cytoscape.js) *directly* into the generated HTML (No CDNs, no external JS). 
    *   Ensure XSS-safe escaping of JSON payload.
    *   **Cycle Bounding**: Replace unbounded `nx.simple_cycles` with a deterministic cycle/result budget mechanism. The analysis state must explicitly distinguish between `complete`, `bounded`, and `failed`. If bounded, CLI and JSON must communicate the cycle list is incomplete.
    *   Preserve existing `graph.dot` and `graph.svg` artifacts.
*   **Testing**: 
    *   Test downstream CLI commands (`deps`, `inspect`, etc.) handling missing `graph.json`, invalid JSON, incompatible `schema_version`, and malformed structures cleanly with useful CLI errors rather than tracebacks.
    *   Test deterministic cycle bounding.
    *   **HTML Portability Acceptance Test**: Prove the HTML is self-contained (no CDN/runtime network requests), contains required JS, can be copied independently, and opens without Python/Graphviz/Internet access.

### Phase 6 — Query CLI
*   **Objective**: Query the existing `graph.json` artifact without re-parsing.
*   **Implementation**:
    *   Add `docswarm query` in `cli/commands.py`.
    *   Support simple deterministic filters: `--role`, `--has-cycles`, `--min-fan-in`, `--min-fan-out`, `--hotspot`, `--has-violations`.
*   **Testing**: Run queries against a fixture `graph.json` and assert correct filtered output. Ensure downstream commands fail cleanly on bad artifacts.

### Phase 7 — Final Hardening & Release Validation
*   **Objective**: Ensure release readiness and PyInstaller compatibility.
*   **Implementation**:
    *   Run the complete existing regression suite and all newly added v0.2.0 tests. The pre-v0.2.0 baseline of 67 passed / 2 skipped must remain green unless an intentional behavioral change is explicitly documented.
    *   Ensure new dependencies (`PyYAML`, `pathspec`) and static HTML/JS assets do not break PyInstaller packaging. Rebuild and test the Windows executable natively.

## 6. Dependencies Between Phases

*   **Phase 1** must occur first to centralize pipeline logic.
*   **Phase 2** establishes the configuration models and the v0.1.0 backward-compatible defaults.
*   **Phase 3** and **Phase 4** can occur in parallel after Phase 2.
*   **Phase 5** (Reporting) and **Phase 6** (Querying) require the stabilized JSON schema from Phase 1/2.
*   **Phase 7** validates all previous phases and PyInstaller functionality.

## 7. Exact Files/Modules Expected to Change

*   `cli/commands.py` (Refactored to call `AnalysisService`, added `query`, enhanced artifact error handling)
*   `core/engine.py` (Implementation of `AnalysisService`)
*   `core/config.py` (New file for Pydantic config models and v0.1.0 defaults)
*   `core/models.py` (Updates for error tracking and schema versioning)
*   `scanner/scanner.py` (`pathspec` integration, size limits)
*   `architecture/analyzer.py` (Config injection, deterministic cycle budget limit)
*   `architecture/rules.py` (Declarative rule processing)
*   `reports/html_reporter.py` (New file for self-contained HTML generation)
*   `pyproject.toml` (Add dependencies: `PyYAML`, `pathspec`)

## 8. Testing Strategy for Every Phase

Testing is a first-class requirement. Every phase includes unit and integration tests.
Testing will explicitly cover:
*   Strict configuration parsing failures.
*   `.gitignore` edge cases and safety-exclusion precedence.
*   Oversized files and parser exceptions.
*   Artifact schema compatibility and downstream failure messages.
*   Strictly offline HTML report portability.
*   The pre-v0.2.0 baseline regression suite (67 passed / 2 skipped).

## 9. Backward Compatibility Requirements

*   **Defaults**: Without `.docswarm.yaml`, the CLI acts exactly as v0.1.0.
*   **Commands**: `docswarm analyze`, `docswarm deps`, `docswarm inspect`, `docswarm graph`, and `docswarm report` remain fully functional.
*   **Artifacts**: `graph.json`, `graph.dot`, `graph.svg`, and `report.md` are preserved. The new `interactive_report.html` is strictly additive.
*   **Packaging**: The PyInstaller executable process is fully preserved.

## 10. Offline / Determinism Requirements

*   The HTML report must not use CDNs or runtime network calls.
*   Dependency resolution must not make network requests.
*   Consecutive runs on the same codebase must produce identical JSON hashes and graph structures.
*   Cycle bounding and glob matching must be strictly deterministic.

## 11. Performance Safeguards

*   **File Size Policy**: Configurable default limits memory consumption by Tree-sitter.
*   **Cycle Detection Budget**: Deterministically bounds cycles instead of hanging. States (`complete`, `bounded`, `failed`) are exposed in the JSON and CLI to communicate incompleteness.

## 12. Security Considerations

*   YAML configuration parsing must strictly use `yaml.safe_load`.
*   Embedded JSON data inside the HTML report must be properly escaped to prevent XSS.
*   Mandatory safety exclusions (e.g., `.docswarm`) cannot be overridden by user configuration.

## 13. Explicit Non-Goals (Deferred)

The following are explicitly **out of scope** for v0.2.0:
*   Go, Java, C# parsers.
*   Multiprocessing / parallel parsing.
*   Full Git history / churn analysis.
*   Differential analysis (`compare`).
*   IDE integrations or Plugin architectures.
*   Arbitrary programmable rule languages or large query languages.
*   Major ML/AI functionality.
*   Parent-directory configuration discovery.

## 14. Definition of Done for v0.2.0

*   All phases completed and code merged.
*   The complete existing regression suite and newly added tests pass (baseline 67 passed / 2 skipped remains green).
*   Offline HTML portability test passes.
*   Configuration system operates strictly, failing on malformed YAML.
*   `.gitignore` is properly respected.
*   PyInstaller executable builds successfully with new dependencies and runs natively on Windows.

## 15. Risks and Mitigations

*   **Risk**: Bounding cycle detection might hide architectural flaws. 
    *   *Mitigation*: The CLI and JSON will explicitly communicate if the analysis was bounded and incomplete, prompting the user to investigate hotspots manually.
*   **Risk**: PyInstaller failing to bundle new HTML templates/JS assets.
    *   *Mitigation*: Update `docswarm.spec` to explicitly collect new static data files via `datas` and test the compiled executable in Phase 7.
