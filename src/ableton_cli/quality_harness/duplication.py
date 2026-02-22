from __future__ import annotations

import ast
import hashlib
import textwrap
from collections import defaultdict

from .models import DuplicateGroup, DuplicateLocation, DuplicationCandidate


def detect_duplicate_groups(
    candidates: list[DuplicationCandidate],
    *,
    min_lines: int,
    min_tokens: int,
) -> list[DuplicateGroup]:
    grouped: dict[str, list[DuplicateLocation]] = defaultdict(list)

    for candidate in candidates:
        if candidate.line_count < min_lines:
            continue
        if candidate.estimated_tokens < min_tokens:
            continue

        normalized = _normalized_ast_dump(candidate.source)
        if normalized is None:
            continue

        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        grouped[fingerprint].append(
            DuplicateLocation(
                path=candidate.path,
                qualname=candidate.qualname,
                lineno=candidate.lineno,
                end_lineno=candidate.end_lineno,
                line_count=candidate.line_count,
                estimated_tokens=candidate.estimated_tokens,
            )
        )

    groups: list[DuplicateGroup] = []
    for fingerprint, locations in grouped.items():
        if len(locations) < 2:
            continue

        ordered_locations = sorted(
            locations, key=lambda item: (item.path, item.lineno, item.qualname)
        )
        groups.append(
            DuplicateGroup(
                fingerprint=fingerprint,
                occurrences=len(ordered_locations),
                line_count=max(item.line_count for item in ordered_locations),
                estimated_tokens=max(item.estimated_tokens for item in ordered_locations),
                locations=ordered_locations,
            )
        )

    return sorted(groups, key=lambda item: (-item.occurrences, item.fingerprint))


def _normalized_ast_dump(source: str) -> str | None:
    dedented = textwrap.dedent(source)
    try:
        tree = ast.parse(dedented)
    except SyntaxError:
        return None

    if not tree.body:
        return None

    first = tree.body[0]
    if not isinstance(first, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None

    normalized = _AstNormalizer().visit(first)
    ast.fix_missing_locations(normalized)
    return ast.dump(normalized, annotate_fields=True, include_attributes=False)


class _AstNormalizer(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        node.name = "_fn"
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        node.name = "_fn"
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        node.id = "_id"
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = "_arg"
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        node.attr = "_attr"
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
        node.value = "_const"
        return node

    def visit_alias(self, node: ast.alias) -> ast.AST:
        node.name = "_module"
        if node.asname is not None:
            node.asname = "_alias"
        return node

    def visit_keyword(self, node: ast.keyword) -> ast.AST:
        node = self.generic_visit(node)
        if node.arg is not None:
            node.arg = "_kw"
        return node
