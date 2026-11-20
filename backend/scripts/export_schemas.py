"""Write the JSON Schemas of the contracts to <repo>/contracts/.

    python scripts/export_schemas.py           # write the files
    python scripts/export_schemas.py --check   # fail if a file is out of date

Message half (Zizwe): contracts/messages.schema.json from aegis.common.models.
UI half (Emmanuel, B13): contracts/ui.schema.json from aegis.common.ui_models.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from aegis.common.models import ENVELOPE_ADAPTER
from aegis.common.ui_models import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def messages_schema() -> dict:
    schema = ENVELOPE_ADAPTER.json_schema(mode="validation")
    schema["title"] = (
        "Team 5 message envelope (docs/02-contracts.md sections 2 to 4, 7, 10)"
    )
    return schema


def ui_schema() -> dict:
    return Snapshot.model_json_schema()


def export_ui_schema() -> Path:
    """Write contracts/ui.schema.json (kept for Emmanuel's existing test)."""
    destination = Path(__file__).resolve().parents[2] / "contracts" / "ui.schema.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(ui_schema()), encoding="utf-8")
    return destination


# File name -> schema builder.
SCHEMAS: dict[str, Callable[[], dict]] = {
    "messages.schema.json": messages_schema,
    "ui.schema.json": ui_schema,
}


def render(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if a file is out of date"
    )
    parser.add_argument("--out", type=Path, default=CONTRACTS_DIR)
    args = parser.parse_args(argv)

    stale = []
    for name, build in SCHEMAS.items():
        path = args.out / name
        text = render(build())
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")

    if stale:
        print(
            f"out of date: {', '.join(stale)}. Run python scripts/export_schemas.py",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
