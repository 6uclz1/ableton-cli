from __future__ import annotations

import ast
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from .models import (
    DependencyAnalysis,
    DependencyCycle,
    DependencyEdge,
    LayerRule,
    LayerViolationRecord,
)


@dataclass(frozen=True)
class _ModuleInfo:
    module: str
    path: Path
    relative_path: str
    is_package: bool


def analyze_dependencies(
    *,
    paths: list[Path],
    root_dir: Path,
    layers: list[LayerRule],
) -> DependencyAnalysis:
    module_infos = [_build_module_info(path=path, root_dir=root_dir) for path in sorted(paths)]
    module_by_name = {info.module: info for info in module_infos if info.module}
    module_names = set(module_by_name)

    edge_set: set[tuple[str, str]] = set()
    for info in module_infos:
        imported_candidates = _collect_import_candidates(info)
        for candidate in imported_candidates:
            imported_module = _match_internal_module(candidate=candidate, module_names=module_names)
            if imported_module is None:
                continue
            if imported_module == info.module:
                edge_set.add((info.module, imported_module))
                continue
            edge_set.add((info.module, imported_module))

    edges = [
        DependencyEdge(
            importer_module=importer,
            importer_path=module_by_name[importer].relative_path,
            imported_module=imported,
            imported_path=module_by_name[imported].relative_path,
        )
        for importer, imported in sorted(edge_set)
        if importer in module_by_name and imported in module_by_name
    ]

    cycles = _detect_cycles(module_by_name=module_by_name, edge_set=edge_set)
    layer_violations = _detect_layer_violations(
        edges=edges,
        layers=layers,
        root_dir=root_dir,
    )
    return DependencyAnalysis(edges=edges, cycles=cycles, layer_violations=layer_violations)


def _build_module_info(*, path: Path, root_dir: Path) -> _ModuleInfo:
    relative_path = _to_relative_path(path=path, root_dir=root_dir)
    module = _module_name_from_relative_path(relative_path)
    is_package = relative_path.endswith("/__init__.py") or relative_path == "__init__.py"
    return _ModuleInfo(
        module=module,
        path=path,
        relative_path=relative_path,
        is_package=is_package,
    )


def _module_name_from_relative_path(relative_path: str) -> str:
    parts = relative_path.split("/")
    if not parts:
        return ""

    if parts[0] in {"src", "remote_script"} and len(parts) > 1:
        parts = parts[1:]

    last = parts[-1]
    if not last.endswith(".py"):
        return ""

    parts[-1] = last[:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(part for part in parts if part)


def _collect_import_candidates(info: _ModuleInfo) -> set[str]:
    candidates: set[str] = set()

    try:
        source = info.path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return candidates

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidates.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved_base = _resolve_from_base(
                module=node.module,
                level=node.level,
                importer_module=info.module,
                importer_is_package=info.is_package,
            )
            if resolved_base is None:
                continue
            if node.module:
                candidates.add(resolved_base)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if resolved_base:
                    candidates.add(f"{resolved_base}.{alias.name}")
                else:
                    candidates.add(alias.name)

    return candidates


def _resolve_from_base(
    *,
    module: str | None,
    level: int,
    importer_module: str,
    importer_is_package: bool,
) -> str | None:
    if level == 0:
        return module or ""

    if importer_is_package:
        importer_package = importer_module
    elif "." in importer_module:
        importer_package = importer_module.rsplit(".", 1)[0]
    else:
        importer_package = ""

    package_parts = importer_package.split(".") if importer_package else []
    remove_count = level - 1
    if remove_count > len(package_parts):
        return None

    base_parts = package_parts[: len(package_parts) - remove_count]
    if module:
        base_parts.extend(module.split("."))

    return ".".join(part for part in base_parts if part)


def _match_internal_module(*, candidate: str, module_names: set[str]) -> str | None:
    if not candidate:
        return None

    if candidate in module_names:
        return candidate

    prefix_matches = [
        module_name for module_name in module_names if candidate.startswith(f"{module_name}.")
    ]
    if prefix_matches:
        return max(prefix_matches, key=len)
    return None


def _detect_cycles(
    *,
    module_by_name: dict[str, _ModuleInfo],
    edge_set: set[tuple[str, str]],
) -> list[DependencyCycle]:
    graph: dict[str, set[str]] = {module: set() for module in module_by_name}
    for source, target in edge_set:
        if source in graph and target in graph:
            graph[source].add(target)

    components = _strongly_connected_components(graph)
    cycles: list[DependencyCycle] = []

    for component in components:
        if len(component) > 1:
            modules = sorted(component)
            paths = sorted(module_by_name[module].relative_path for module in modules)
            cycles.append(DependencyCycle(modules=modules, paths=paths))
            continue

        module = component[0]
        if module in graph[module]:
            paths = [module_by_name[module].relative_path]
            cycles.append(DependencyCycle(modules=[module], paths=paths))

    return sorted(cycles, key=lambda item: ",".join(item.modules))


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    stack_set: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def strong_connect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        stack_set.add(node)

        for neighbor in graph[node]:
            if neighbor not in indices:
                strong_connect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in stack_set:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                popped = stack.pop()
                stack_set.remove(popped)
                component.append(popped)
                if popped == node:
                    break
            components.append(component)

    for node in sorted(graph):
        if node not in indices:
            strong_connect(node)

    return components


def _detect_layer_violations(
    *,
    edges: list[DependencyEdge],
    layers: list[LayerRule],
    root_dir: Path,
) -> list[LayerViolationRecord]:
    if not layers:
        return []

    layer_by_path: dict[str, tuple[int, str]] = {}
    for edge in edges:
        for relative_path in (edge.importer_path, edge.imported_path):
            if relative_path in layer_by_path:
                continue
            mapped = _map_path_to_layer(
                relative_path=relative_path,
                root_dir=root_dir,
                layers=layers,
            )
            if mapped is not None:
                layer_by_path[relative_path] = mapped

    violation_keys: set[tuple[str, str, str, str, str, str]] = set()
    violations: list[LayerViolationRecord] = []
    for edge in edges:
        importer_layer = layer_by_path.get(edge.importer_path)
        imported_layer = layer_by_path.get(edge.imported_path)
        if importer_layer is None or imported_layer is None:
            continue

        from_index, from_layer_name = importer_layer
        to_index, to_layer_name = imported_layer
        if to_index < from_index:
            key = (
                edge.importer_module,
                edge.importer_path,
                edge.imported_module,
                edge.imported_path,
                from_layer_name,
                to_layer_name,
            )
            if key in violation_keys:
                continue
            violation_keys.add(key)
            violations.append(
                LayerViolationRecord(
                    importer_module=edge.importer_module,
                    importer_path=edge.importer_path,
                    imported_module=edge.imported_module,
                    imported_path=edge.imported_path,
                    from_layer=from_layer_name,
                    to_layer=to_layer_name,
                )
            )

    return sorted(
        violations,
        key=lambda item: (
            item.importer_path,
            item.imported_path,
            item.from_layer,
            item.to_layer,
        ),
    )


def _map_path_to_layer(
    *,
    relative_path: str,
    root_dir: Path,
    layers: list[LayerRule],
) -> tuple[int, str] | None:
    absolute_path = (root_dir / relative_path).resolve().as_posix()
    relative_path_obj = PurePosixPath(relative_path)
    for index, layer in enumerate(layers):
        for pattern in layer.include:
            for variant in _expand_globstar(pattern):
                if relative_path_obj.match(variant) or fnmatch(relative_path, variant):
                    return index, layer.name
                if fnmatch(absolute_path, variant):
                    return index, layer.name
    return None


def _expand_globstar(pattern: str) -> set[str]:
    variants = {pattern}
    queue = [pattern]
    while queue:
        current = queue.pop()
        next_variants = {
            current.replace("/**/", "/", 1),
            current.replace("**/", "", 1),
            current.replace("/**", "", 1),
        }
        for candidate in next_variants:
            if candidate == current:
                continue
            if "**" in current and candidate not in variants:
                variants.add(candidate)
                queue.append(candidate)
    return variants


def _to_relative_path(*, path: Path, root_dir: Path) -> str:
    absolute_path = path.resolve()
    absolute_root = root_dir.resolve()
    try:
        return absolute_path.relative_to(absolute_root).as_posix()
    except ValueError:
        return absolute_path.as_posix()
