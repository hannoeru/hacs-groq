"""Minimal Voluptuous -> JSON Schema conversion.

Home Assistant LLM tools expose `tool.parameters` as a Voluptuous schema.
Some integrations used `voluptuous_openapi` for this conversion, but that
package is not available in all HA runtimes.

This module implements the small subset we need for function-calling tools:
- object parameters with properties
- required/optional keys
- basic scalar types + arrays
- nested objects

It intentionally falls back to permissive schemas when it can't infer a type.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import voluptuous as vol

JsonSchema = dict[str, Any]


def _type_schema(py_type: Any) -> JsonSchema:
    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    return {}


def _convert_value(  # noqa: PLR0911
    value: Any, custom_serializer: Callable[[Any], Any] | None
) -> JsonSchema:
    """Convert a Voluptuous value validator into JSON schema."""

    # Let HA's LLM API serializer handle special types (selectors, etc.)
    if custom_serializer is not None:
        try:
            serialized = custom_serializer(value)
        except Exception:
            serialized = None
        if isinstance(serialized, Mapping):
            return dict(serialized)

    if isinstance(value, vol.Schema):
        return convert(value, custom_serializer=custom_serializer)

    # Nested dict schema
    if isinstance(value, Mapping):
        return _convert_mapping(value, custom_serializer)

    # Arrays (very common shape: [str] / [vol.Coerce(int)] etc.)
    if isinstance(value, list | tuple) and value:
        return {
            "type": "array",
            "items": _convert_value(value[0], custom_serializer),
        }

    # Plain python types
    if value in (str, int, float, bool):
        return _type_schema(value)

    # Common Voluptuous validators we can partially infer
    # Coerce(x) -> treat as x
    if isinstance(value, vol.Coerce):
        return _type_schema(value.type)

    # In([...]) -> infer scalar if possible
    if isinstance(value, vol.In) and hasattr(value, "container"):
        container = value.container
        if isinstance(container, (list, tuple)) and container:
            return {"enum": list(container)}

    # Fallback: allow anything
    return {}


def _key_name(key: Any) -> str:
    if isinstance(key, (vol.Required, vol.Optional)):
        return str(key.schema)
    return str(key)


def _is_required(key: Any) -> bool:
    return isinstance(key, vol.Required)


def _convert_mapping(
    schema_mapping: Mapping[Any, Any],
    custom_serializer: Callable[[Any], Any] | None,
) -> JsonSchema:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for key, value in schema_mapping.items():
        name = _key_name(key)
        properties[name] = _convert_value(value, custom_serializer)
        if _is_required(key):
            required.append(name)

    out: JsonSchema = {
        "type": "object",
        "properties": properties,
        # HA tool schemas are usually closed; but if we fail to infer, this is safer.
        "additionalProperties": True,
    }
    if required:
        out["required"] = required
    return out


def convert(
    schema: Any, custom_serializer: Callable[[Any], Any] | None = None
) -> JsonSchema:
    """Convert a Voluptuous schema into a JSON schema dict."""

    if isinstance(schema, vol.Schema):
        return _convert_value(schema.schema, custom_serializer)
    if isinstance(schema, Mapping):
        return _convert_mapping(schema, custom_serializer)

    # Unknown shape: best-effort
    return {"type": "object", "additionalProperties": True}
