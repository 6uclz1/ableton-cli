from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContractValidationError(Exception):
    path: str
    message: str


def _matches_type(expected_type: str, value: Any) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    if expected_type == "any":
        return True
    raise RuntimeError(f"Unsupported schema type: {expected_type}")


def _validate_type(expected: str | list[str], value: Any, *, path: str) -> None:
    if isinstance(expected, str):
        expected_types = [expected]
    else:
        expected_types = list(expected)
    if any(_matches_type(name, value) for name in expected_types):
        return
    expected_label = "|".join(expected_types)
    actual_type = type(value).__name__
    raise ContractValidationError(
        path=path,
        message=f"expected {expected_label}, got {actual_type}",
    )


def _validate_one_of(schema: dict[str, Any], value: Any, *, path: str) -> bool:
    raw_options = schema.get("oneOf", schema.get("one_of"))
    if raw_options is None:
        return False
    if not isinstance(raw_options, list) or not raw_options:
        raise RuntimeError("oneOf must be a non-empty list")

    matched_count = 0
    last_error: ContractValidationError | None = None
    for option in raw_options:
        if not isinstance(option, dict):
            raise RuntimeError("oneOf items must be schemas")
        try:
            validate_value(option, value, path=path)
        except ContractValidationError as exc:
            last_error = exc
            continue
        matched_count += 1

    if matched_count == 1:
        return True
    if matched_count == 0:
        message = "does not match any allowed schema"
        if last_error is not None:
            message = f"{message}: {last_error.path} {last_error.message}"
        raise ContractValidationError(path=path, message=message)
    raise ContractValidationError(path=path, message="matches multiple allowed schemas")


def validate_value(schema: dict[str, Any], value: Any, *, path: str) -> None:
    if _validate_one_of(schema, value, path=path):
        return

    expected_type = schema.get("type", "any")
    _validate_type(expected_type, value, path=path)

    if "const" in schema and value != schema["const"]:
        raise ContractValidationError(
            path=path,
            message=f"expected constant {schema['const']!r}",
        )

    if isinstance(expected_type, list):
        is_object = "object" in expected_type and isinstance(value, dict)
        is_array = "array" in expected_type and isinstance(value, list)
        is_string = "string" in expected_type and isinstance(value, str)
    else:
        is_object = expected_type == "object" and isinstance(value, dict)
        is_array = expected_type == "array" and isinstance(value, list)
        is_string = expected_type == "string" and isinstance(value, str)

    minimum = schema.get("minimum")
    if isinstance(minimum, int | float) and isinstance(value, int | float):
        if not isinstance(value, bool) and value < minimum:
            raise ContractValidationError(
                path=path,
                message=f"expected >= {minimum}, got {value}",
            )

    maximum = schema.get("maximum")
    if isinstance(maximum, int | float) and isinstance(value, int | float):
        if not isinstance(value, bool) and value > maximum:
            raise ContractValidationError(
                path=path,
                message=f"expected <= {maximum}, got {value}",
            )

    if is_string:
        min_length = schema.get("minLength", schema.get("min_length"))
        if isinstance(min_length, int) and len(value) < min_length:
            raise ContractValidationError(
                path=path,
                message=f"expected length >= {min_length}, got {len(value)}",
            )

    if is_object:
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ContractValidationError(
                    path=f"{path}.{key}",
                    message="is required",
                )
        properties = schema.get("properties", {})
        additional_properties = schema.get("additional_properties", True)
        for key, item in value.items():
            if key not in properties:
                if additional_properties:
                    continue
                raise ContractValidationError(
                    path=f"{path}.{key}",
                    message="is not allowed",
                )
            child_schema = properties[key]
            validate_value(child_schema, item, path=f"{path}.{key}")
        return

    if is_array:
        items_schema = schema.get("items")
        min_items = schema.get("minItems", schema.get("min_items"))
        if isinstance(min_items, int) and len(value) < min_items:
            raise ContractValidationError(
                path=path,
                message=f"expected at least {min_items} items, got {len(value)}",
            )
        if not isinstance(items_schema, dict):
            return
        for index, item in enumerate(value):
            validate_value(items_schema, item, path=f"{path}[{index}]")
