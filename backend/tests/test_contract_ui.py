"""Compare the frozen UI field contract across both schema generators."""

import json
from pathlib import Path

from aegis.common.ui_models import Snapshot

ROOT = Path(__file__).resolve().parents[2]


def normalize(schema, node):
    if "$ref" in node:
        reference = node["$ref"].removeprefix("#/").split("/")
        resolved = schema
        for part in reference:
            resolved = resolved[part]
        return normalize(schema, resolved)
    if "anyOf" in node:
        choices = [normalize(schema, item) for item in node["anyOf"]]
        return {
            "anyOf": sorted(choices, key=lambda item: json.dumps(item, sort_keys=True))
        }
    if isinstance(node.get("type"), list):
        return normalize(
            schema, {"anyOf": [{**node, "type": item} for item in node["type"]]}
        )
    if "enum" in node:
        return {"enum": sorted(node["enum"], key=str)}
    if "const" in node:
        return {"const": node["const"]}
    result = {"type": node.get("type")}
    if node.get("type") == "object":
        result["properties"] = {
            key: normalize(schema, value)
            for key, value in sorted(node.get("properties", {}).items())
        }
        result["required"] = sorted(node.get("required", []))
        additional = node.get("additionalProperties", True)
        result["additionalProperties"] = (
            normalize(schema, additional)
            if isinstance(additional, dict)
            else additional
        )
    elif node.get("type") == "array":
        result["items"] = normalize(schema, node["items"])
    for key in (
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "multipleOf",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
    ):
        if key in node:
            result[key] = node[key]
    return result


def test_GEN_002_pydantic_schema_matches_checked_in_contract():
    checked = json.loads((ROOT / "contracts/ui.schema.json").read_text())
    assert Snapshot.model_json_schema() == checked


def test_GEN_002_typescript_and_python_snapshot_contracts_match():
    python = json.loads((ROOT / "contracts/ui.schema.json").read_text())
    typescript = json.loads((ROOT / "contracts/ui.from-ts.schema.json").read_text())
    assert normalize(python, python) == normalize(typescript, typescript)


def test_GEN_002_all_captured_fixtures_validate_against_snapshot():
    names = {
        "idle",
        "assigned",
        "secured",
        "travelling",
        "degraded",
        "link_lost",
        "route_blocked",
        "fault_shift",
        "estop_held",
        "at_destination",
        "delivered",
        "queued",
    }
    directory = ROOT / "frontend/src/mock/fixtures"
    assert {path.stem for path in directory.glob("*.json")} == names
    for name in names:
        Snapshot.model_validate_json((directory / f"{name}.json").read_text())


def test_GEN_002_normalization_detects_required_nullable_and_extra_properties():
    base = {
        "type": "object",
        "properties": {"value": {"type": ["number", "null"]}},
        "required": ["value"],
    }
    canonical = normalize(base, base)
    missing_required = {**base, "required": []}
    non_nullable = {**base, "properties": {"value": {"type": "number"}}}
    closed = {**base, "additionalProperties": False}
    assert canonical != normalize(missing_required, missing_required)
    assert canonical != normalize(non_nullable, non_nullable)
    assert canonical != normalize(closed, closed)
