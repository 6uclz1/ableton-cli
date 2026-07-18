# Quality Harness (Phase 2)

Phase 2 adds regression-aware quality gating on top of Phase 1 metrics.

## Scope

Phase 2 includes:

- Phase 1 metrics and threshold checks
- Baseline comparison (`--baseline`) for regression gating
- Internal dependency cycle detection
- Layer violation detection

## CLI

```bash
uv run python tools/quality_harness.py \
  --config .quality-harness.yml \
  --report quality-harness-report.json
```

With baseline comparison:

```bash
uv run python tools/quality_harness.py \
  --config .quality-harness.yml \
  --report quality-harness-report.json \
  --baseline ./baseline-quality-harness-report.json
```

Arguments:

- `--config` default: `.quality-harness.yml`
- `--report` default: `quality-harness-report.json`
- `--baseline` optional baseline report JSON

Exit codes:

- `0`: no fail-level violations
- `1`: fail-level violations detected
- `2`: invalid config/runtime error

## Configuration Schema

```yaml
version: 1
phase: 2
include:
  - "src/**/*.py"
  - "remote_script/**/*.py"
exclude:
  - "**/__pycache__/**"
  - "tests/**"
duplication:
  min_lines: 6
  min_tokens: 40
thresholds:
  file:
    complexity: { warn: 180, fail: 260 }
    imports: { warn: 20, fail: 30 }
    estimated_tokens: { warn: 3000, fail: 12000 }
  function:
    complexity: { warn: 10, fail: 35 }
    nesting: { warn: 3, fail: 6 }
    args: { warn: 6, fail: 13 }
    estimated_tokens: { warn: 260, fail: 950 }
  class:
    complexity: { warn: 70, fail: 400 }
    nesting: { warn: 3, fail: 6 }
    args: { warn: 8, fail: 12 }
    imports: { warn: 8, fail: 12 }
    estimated_tokens: { warn: 1200, fail: 12000 }
    god_class_risk: { warn: 70, fail: 99 }
  duplicates:
    occurrences: { warn: 3, fail: 7 }
parse_errors:
  mode: warn
baseline:
  warning_delta: { warn: 5, fail: 20 }
  failure_delta: { warn: 0.5, fail: 1 }
  new_failures: { warn: 0.5, fail: 1 }
dependencies:
  cycle_count: { warn: 1, fail: 3 }
layers:
  violation_count: { warn: 1, fail: 4 }
  order:
    - name: commands
      include:
        - "src/ableton_cli/commands/**/*.py"
        - "src/ableton_cli/app.py"
        - "src/ableton_cli/cli.py"
    - name: core
      include:
        - "src/ableton_cli/**/*.py"
    - name: remote
      include:
        - "remote_script/**/*.py"
```

## Phase 2 Checks

### Baseline Comparison

When `--baseline` is provided, these deltas are evaluated:

- `baseline.warning_delta`
- `baseline.failure_delta`
- `baseline.new_failures`

`new_failures` is the number of current fail-level violation signatures that do not exist in baseline fail violations.

### Dependency Cycles

- Internal import graph is built from analyzed Python files.
- Strongly connected components (SCC) are treated as cycles.
- Threshold metric: `dependencies.cycle_count`.

### Layer Violations

- Files are mapped to first matching layer in `layers.order`.
- Import direction rule: a lower layer cannot import a higher layer.
- Threshold metric: `layers.violation_count`.

## Report Additions

Phase 2 report includes:

- `dependency_cycles`
- `layer_violations`
- `baseline_comparison` (when baseline used)
- `summary.dependency_cycle_count`
- `summary.layer_violation_count`
- `summary.baseline_used`

## GitHub Actions Example

```yaml
quality-harness:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: \"3.11\"
    - uses: astral-sh/setup-uv@v4
    - run: uv sync --dev
    - run: uv run python tools/quality_harness.py --config .quality-harness.yml --report quality-harness-report.json
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: quality-harness-report
        path: quality-harness-report.json
```

## Module Splitting Policy

When a file or class trips a quality-harness warning (`god_class_risk`,
`estimated_tokens`, `complexity`, `nesting`, `args`, ...), the warning is a
*signal to go find the domain seam*, not a license to cut the file in half
at whatever line makes the metric go quiet. A split that satisfies the
metric while spreading one concern across two files (or worse, two files
that each still mix concerns) is a Goodhart failure: the number improves,
discoverability gets worse, and the next contributor has to check two
places to understand one behavior.

Rules for splitting a module:

1. **Find the seam first.** Read the file's public methods/functions and
   group them by what they're actually about (e.g. "reading the browser
   catalog" vs. "loading an item into a track", or "session clips" vs.
   "arrangement clips"), not by where the file happens to be long. If no
   natural seam exists, the warning may mean the module needs a genuinely
   different fix (extracting a helper, simplifying a function) rather than
   a file split.
2. **Split along the seam, not the metric.** The resulting files' names and
   docstrings should describe a domain ("rack chain traversal and macro
   parameters", "arrangement clip commands"), not a threshold ("kept under
   god-class-risk"). If a docstring cites a metric or threshold as the
   reason for a file's existence, that is itself a defect — replace it with
   a domain description.
3. **Pure moves for the split itself.** Moving code to satisfy this policy
   must not change behavior or public signatures. Behavioral changes are a
   separate, separately-reviewed change.
4. **Never raise a threshold to make a warning disappear.** If a genuinely
   cohesive concern is large, that is data about the domain's real
   complexity, not a bug in the harness config.
5. **A warning is not always a split.** Many of this harness's warnings
   (`complexity`, `nesting`, `args`) are per-function properties that a file
   split does nothing to fix — they require simplifying the function itself.
   Don't split a file to chase a warning that splitting can't actually
   resolve; only `god_class_risk` and gross per-file size responds to
   moving code out of a class/module.

## Known Limitations

1. Complexity is approximate cyclomatic complexity, not cognitive complexity.
2. Duplication detection is normalized-AST equality, not semantic clone detection.
3. `estimated_tokens` is approximate and tokenizer-agnostic.
4. Import resolution is static and best-effort for internal modules.
5. Layer mapping is path-pattern based (first-match rule).
6. Baseline comparison requires a valid prior report with summary/violations fields.
