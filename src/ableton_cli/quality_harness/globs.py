from __future__ import annotations


def expand_globstar(pattern: str) -> set[str]:
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
