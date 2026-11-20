"""Export the operator-screen snapshot JSON Schema."""

import json
from pathlib import Path

from aegis.common.ui_models import Snapshot


def export_ui_schema() -> Path:
    destination = Path(__file__).resolve().parents[2] / "contracts" / "ui.schema.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(Snapshot.model_json_schema(), indent=2) + "\n")
    return destination


if __name__ == "__main__":
    export_ui_schema()
