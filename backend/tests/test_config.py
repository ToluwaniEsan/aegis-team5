"""Task A0: the settings loader."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aegis.common.config import ConfigError, Settings, find_config, load_settings

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "config.yaml"


def _real() -> dict:
    return yaml.safe_load(REAL_CONFIG.read_text(encoding="utf-8"))


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_real_config_loads():
    settings = load_settings(REAL_CONFIG)
    assert isinstance(settings, Settings)
    assert settings.version == 1
    assert settings.payload.mass_min_kg == 226.8
    assert settings.payload.mass_max_kg == 1000
    assert settings.timing.command_timeout_s == 5.0
    assert [p.id for p in settings.places] == [
        "FOB_ALPHA",
        "OP_BRAVO",
        "OP_CHARLIE",
        "LZ_DELTA",
    ]


def test_settings_cover_every_key_in_the_file():
    """Round-trip: the models hold exactly the keys in config.yaml, no more, no fewer."""
    assert load_settings(REAL_CONFIG).model_dump() == _real()


@pytest.mark.parametrize(
    "fixture, key",
    [
        ("config_unknown_key.yaml", "timing.command_timout_s"),
        ("config_missing_key.yaml", "link.lost_after_s"),
        ("config_out_of_range.yaml", "payload.mass_min_kg"),
    ],
)
def test_broken_copy_fails_naming_the_key(fixture, key):
    with pytest.raises(ConfigError) as err:
        load_settings(FIXTURES / fixture)
    assert key in str(err.value)


@pytest.mark.parametrize(
    "section, key, value",
    [
        ("timing", "command_timeout_s", -1.0),
        ("timing", "status_rate_hz", 0),
        ("link", "degraded_loss_pct", 150),
        ("event_buffer", "max_events", 0),
        ("network", "ui_port", 70000),
    ],
)
def test_out_of_range_value_fails(tmp_path, section, key, value):
    data = _real()
    data[section][key] = value
    with pytest.raises(ConfigError, match=f"{section}.{key}"):
        load_settings(_write(tmp_path, data))


@pytest.mark.parametrize(
    "section, changes, message",
    [
        ("payload", {"sim_noise_kg": 0.5}, "payload.sim_noise_kg"),
        (
            "payload",
            {"release_energy_wh_nominal": 6.0},
            "payload.release_energy_wh_nominal",
        ),
        ("alerts", {"power_fault_pct": 30}, "alerts.power_fault_pct"),
        ("network", {"reconnect_min_s": 10.0}, "network.reconnect_min_s"),
        ("network", {"ui_port": 7101}, "network.link_ground_port"),
        ("event_buffer", {"batch_size": 10000}, "event_buffer.batch_size"),
    ],
)
def test_inconsistent_values_fail(tmp_path, section, changes, message):
    data = _real()
    data[section].update(changes)
    with pytest.raises(ConfigError, match=message):
        load_settings(_write(tmp_path, data))


def test_duplicate_place_ids_fail(tmp_path):
    data = _real()
    data["places"].append(dict(data["places"][0]))
    with pytest.raises(ConfigError, match="places"):
        load_settings(_write(tmp_path, data))


def test_wrong_version_fails(tmp_path):
    data = _real()
    data["version"] = 2
    with pytest.raises(ConfigError, match="version"):
        load_settings(_write(tmp_path, data))


def test_A_10_changing_the_file_changes_the_value_with_no_code_change(tmp_path):
    data = _real()
    data["timing"]["command_timeout_s"] = 7.5
    settings = load_settings(_write(tmp_path, data))
    assert settings.timing.command_timeout_s == 7.5


def test_aegis_config_env_var_wins(tmp_path, monkeypatch):
    data = _real()
    data["timing"]["command_timeout_s"] = 9.0
    monkeypatch.setenv("AEGIS_CONFIG", str(_write(tmp_path, data)))
    assert load_settings().timing.command_timeout_s == 9.0


@pytest.mark.parametrize(
    "start", [REPO_ROOT, REPO_ROOT / "backend", REPO_ROOT / "backend" / "tests"]
)
def test_finds_config_from_repo_root_and_below(start, monkeypatch):
    monkeypatch.delenv("AEGIS_CONFIG", raising=False)
    monkeypatch.chdir(start)
    assert find_config() == REAL_CONFIG
    assert load_settings().root == REPO_ROOT


def test_missing_file_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("AEGIS_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="not found"):
        load_settings()


def test_relative_paths_resolve_from_repo_root_not_cwd(monkeypatch):
    monkeypatch.chdir(REPO_ROOT / "backend")
    settings = load_settings(REAL_CONFIG)
    assert settings.resolve(settings.logging.dir) == REPO_ROOT / "logs"
    assert (
        settings.resolve(settings.event_buffer.file)
        == REPO_ROOT / "logs" / "event_buffer.jsonl"
    )


def test_settings_are_read_only():
    settings = load_settings(REAL_CONFIG)
    with pytest.raises(ValidationError):
        settings.timing.command_timeout_s = 1.0
