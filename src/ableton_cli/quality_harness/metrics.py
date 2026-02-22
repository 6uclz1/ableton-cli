from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

from .models import (
    AnalysisResult,
    ClassMetric,
    DuplicationCandidate,
    FileMetric,
    FunctionMetric,
    ParseErrorRecord,
)


def analyze_python_files(paths: list[Path], *, root_dir: Path) -> AnalysisResult:
    file_metrics: list[FileMetric] = []
    function_metrics: list[FunctionMetric] = []
    class_metrics: list[ClassMetric] = []
    duplication_candidates: list[DuplicationCandidate] = []
    parse_errors: list[ParseErrorRecord] = []

    for path in sorted(paths):
        relative_path = _to_relative_path(path, root_dir)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            parse_errors.append(
                ParseErrorRecord(
                    path=relative_path,
                    error_type=exc.__class__.__name__,
                    message=str(exc),
                )
            )
            continue

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            parse_errors.append(
                ParseErrorRecord(
                    path=relative_path,
                    error_type=exc.__class__.__name__,
                    message=str(exc),
                )
            )
            continue

        complexity, nesting = _compute_complexity_and_nesting(tree, skip_nested_definitions=False)
        file_metrics.append(
            FileMetric(
                path=relative_path,
                complexity=complexity,
                nesting=nesting,
                args=0,
                imports=_count_imports(tree),
                estimated_tokens=_estimate_tokens(source),
                line_count=len(source.splitlines()),
            )
        )

        collector = _ScopedMetricCollector(
            source=source,
            relative_path=relative_path,
        )
        collector.visit(tree)
        function_metrics.extend(collector.function_metrics)
        class_metrics.extend(collector.class_metrics)
        duplication_candidates.extend(collector.duplication_candidates)

    return AnalysisResult(
        files_total=len(paths),
        file_metrics=sorted(file_metrics, key=lambda item: item.path),
        function_metrics=sorted(
            function_metrics, key=lambda item: (item.path, item.lineno, item.qualname)
        ),
        class_metrics=sorted(
            class_metrics, key=lambda item: (item.path, item.lineno, item.qualname)
        ),
        duplication_candidates=sorted(
            duplication_candidates,
            key=lambda item: (item.path, item.lineno, item.qualname),
        ),
        parse_errors=sorted(parse_errors, key=lambda item: item.path),
    )


def compute_god_class_risk(
    *,
    method_count: int,
    public_method_count: int,
    complexity: int,
    estimated_tokens: int,
    args: int,
) -> float:
    if method_count == 0:
        return 0.0

    method_score = min((method_count / 20.0) * 100.0, 100.0)
    public_method_score = min((public_method_count / 15.0) * 100.0, 100.0)
    complexity_score = min((complexity / 120.0) * 100.0, 100.0)
    token_score = min((estimated_tokens / 2000.0) * 100.0, 100.0)
    args_score = min((args / 12.0) * 100.0, 100.0)

    score = (
        method_score * 0.25
        + public_method_score * 0.20
        + complexity_score * 0.30
        + token_score * 0.20
        + args_score * 0.05
    )
    return round(score, 1)


class _ScopedMetricCollector(ast.NodeVisitor):
    def __init__(self, *, source: str, relative_path: str) -> None:
        self._source = source
        self._lines = source.splitlines()
        self._relative_path = relative_path

        self._qualname_parts: list[str] = []
        self._parent_stack: list[ast.AST] = []
        self._direct_method_stack: list[list[FunctionMetric]] = []

        self.function_metrics: list[FunctionMetric] = []
        self.class_metrics: list[ClassMetric] = []
        self.duplication_candidates: list[DuplicationCandidate] = []

    def visit_Module(self, node: ast.Module) -> None:  # noqa: N802
        self._parent_stack.append(node)
        self.generic_visit(node)
        self._parent_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        qualname = self._build_qualname(node.name)
        self._parent_stack.append(node)
        self._qualname_parts.append(node.name)
        self._direct_method_stack.append([])
        self.generic_visit(node)
        methods = self._direct_method_stack.pop()
        self._qualname_parts.pop()
        self._parent_stack.pop()

        source_segment, line_count = _source_segment(node=node, lines=self._lines)
        estimated_tokens = _estimate_tokens(source_segment)
        complexity = sum(item.complexity for item in methods)
        nesting = max((item.nesting for item in methods), default=0)
        args = max((item.args for item in methods), default=0)
        method_names = [item.qualname.rsplit(".", 1)[-1] for item in methods]
        public_method_count = sum(1 for name in method_names if not name.startswith("_"))
        god_class_risk = compute_god_class_risk(
            method_count=len(method_names),
            public_method_count=public_method_count,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            args=args,
        )

        self.class_metrics.append(
            ClassMetric(
                path=self._relative_path,
                qualname=qualname,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                complexity=complexity,
                nesting=nesting,
                args=args,
                imports=_count_imports(node),
                estimated_tokens=estimated_tokens,
                line_count=line_count,
                method_count=len(method_names),
                public_method_count=public_method_count,
                god_class_risk=god_class_risk,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function_node(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function_node(node)

    def _visit_function_node(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = self._build_qualname(node.name)
        immediate_parent = self._parent_stack[-1] if self._parent_stack else None
        is_direct_method = isinstance(immediate_parent, ast.ClassDef)
        parent_class = ".".join(self._qualname_parts) if is_direct_method else None

        source_segment, line_count = _source_segment(node=node, lines=self._lines)
        complexity, nesting = _compute_complexity_and_nesting(node, skip_nested_definitions=True)
        args = _count_arguments(node, is_method=is_direct_method)
        metric = FunctionMetric(
            path=self._relative_path,
            qualname=qualname,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            parent_class=parent_class,
            complexity=complexity,
            nesting=nesting,
            args=args,
            imports=_count_imports(node),
            estimated_tokens=_estimate_tokens(source_segment),
            line_count=line_count,
        )

        self.function_metrics.append(metric)
        self.duplication_candidates.append(
            DuplicationCandidate(
                path=self._relative_path,
                qualname=qualname,
                lineno=metric.lineno,
                end_lineno=metric.end_lineno,
                line_count=metric.line_count,
                estimated_tokens=metric.estimated_tokens,
                source=source_segment,
            )
        )

        if is_direct_method and self._direct_method_stack:
            self._direct_method_stack[-1].append(metric)

        self._parent_stack.append(node)
        self._qualname_parts.append(node.name)
        self.generic_visit(node)
        self._qualname_parts.pop()
        self._parent_stack.pop()

    def _build_qualname(self, local_name: str) -> str:
        if not self._qualname_parts:
            return local_name
        return ".".join([*self._qualname_parts, local_name])


class _ComplexityVisitor(ast.NodeVisitor):
    def __init__(self, *, root: ast.AST, skip_nested_definitions: bool) -> None:
        self._root = root
        self._skip_nested_definitions = skip_nested_definitions
        self._current_nesting = 0

        self.complexity = 1
        self.max_nesting = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if self._skip_nested_definitions and node is not self._root:
            return
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        if self._skip_nested_definitions and node is not self._root:
            return
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        if self._skip_nested_definitions and node is not self._root:
            return
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        self.complexity += 1
        self._visit_control_node(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:  # noqa: N802
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self.complexity += 1
        self._visit_control_node(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self.complexity += 1
        self._visit_control_node(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self.complexity += 1
        self._visit_control_node(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        self.complexity += 1
        self._visit_control_node(node)

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        self.complexity += len(node.cases)
        self._visit_control_node(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        self.complexity += max(len(node.values) - 1, 0)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self._visit_control_node(node)

    def _visit_control_node(self, node: ast.AST) -> None:
        self._current_nesting += 1
        self.max_nesting = max(self.max_nesting, self._current_nesting)
        self.generic_visit(node)
        self._current_nesting -= 1


def _compute_complexity_and_nesting(
    node: ast.AST,
    *,
    skip_nested_definitions: bool,
) -> tuple[int, int]:
    visitor = _ComplexityVisitor(root=node, skip_nested_definitions=skip_nested_definitions)
    visitor.visit(node)
    return visitor.complexity, visitor.max_nesting


def _count_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_method: bool) -> int:
    positional_names = [arg.arg for arg in node.args.posonlyargs] + [
        arg.arg for arg in node.args.args
    ]
    positional_count = len(positional_names)

    if is_method and positional_names and positional_names[0] in {"self", "cls"}:
        positional_count -= 1

    return (
        positional_count
        + len(node.args.kwonlyargs)
        + int(node.args.vararg is not None)
        + int(node.args.kwarg is not None)
    )


def _count_imports(node: ast.AST) -> int:
    modules: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                modules.add(alias.name)
        elif isinstance(child, ast.ImportFrom):
            module_name = child.module if child.module else "." * child.level
            modules.add(module_name)
    return len(modules)


def _estimate_tokens(source: str) -> int:
    if not source.strip():
        return 0

    ignored_tokens = {
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.COMMENT,
        tokenize.ENDMARKER,
    }

    count = 0
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in ignored_tokens:
                continue
            count += 1
    except tokenize.TokenError:
        return 0
    return count


def _source_segment(*, node: ast.AST, lines: list[str]) -> tuple[str, int]:
    lineno = getattr(node, "lineno", 1)
    end_lineno = getattr(node, "end_lineno", lineno)
    if end_lineno < lineno:
        end_lineno = lineno

    start_index = max(lineno - 1, 0)
    end_index = min(end_lineno, len(lines))
    segment_lines = lines[start_index:end_index]
    segment = "\n".join(segment_lines)
    if segment and not segment.endswith("\n"):
        segment += "\n"

    line_count = max(end_lineno - lineno + 1, 0)
    return segment, line_count


def _to_relative_path(path: Path, root_dir: Path) -> str:
    absolute_path = path.resolve()
    absolute_root = root_dir.resolve()
    try:
        return absolute_path.relative_to(absolute_root).as_posix()
    except ValueError:
        return absolute_path.as_posix()
