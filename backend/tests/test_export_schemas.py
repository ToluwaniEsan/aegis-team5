"""Task A2: the message half of scripts/export_schemas.py."""

import json
import sys
from pathlib import Path

from aegis.common.models import BODIES

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_schemas


def test_schema_covers_every_message_type():
    schema = export_schemas.messages_schema()
    mapping = schema["discriminator"]["mapping"]
    assert set(mapping) == set(BODIES)


def test_export_then_check_passes(tmp_path):
    assert export_schemas.main(["--out", str(tmp_path)]) == 0
    assert json.loads((tmp_path / "messages.schema.json").read_text())
    assert export_schemas.main(["--out", str(tmp_path), "--check"]) == 0


def test_check_fails_when_out_of_date(tmp_path):
    (tmp_path / "messages.schema.json").write_text("{}\n")
    assert export_schemas.main(["--out", str(tmp_path), "--check"]) == 1


def test_checked_in_schema_is_current():
    assert export_schemas.main(["--check"]) == 0
