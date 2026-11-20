"""Settings loader for config/config.yaml (decision A-10).

Every limit, timeout and rate the backend uses comes from here. The pydantic
models mirror the YAML file key for key: unknown keys, missing keys and
out-of-range values all fail at load time with a message that names the key.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    model_validator,
)

ENV_VAR = "AEGIS_CONFIG"
RELATIVE_PATH = Path("config") / "config.yaml"


class ConfigError(Exception):
    """The settings file is missing, unreadable or invalid."""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# Shorthands for the common constraints.
def _pos() -> Any:
    return Field(gt=0)


def _non_neg() -> Any:
    return Field(ge=0)


def _pct() -> Any:
    return Field(ge=0, le=100)


class Dims(_Section):
    length: float = _pos()
    width: float = _pos()
    height: float = _pos()


class PayloadSettings(_Section):
    mass_min_kg: float = _pos()
    mass_max_kg: float = _pos()
    dims_max_cm: Dims
    unsecured_shift_cm: float = _pos()
    weight_accuracy_kg: float = _pos()
    release_energy_wh_nominal: float = _pos()
    release_energy_wh_max: float = _pos()
    load_time_s: float = _non_neg()
    secure_time_s: float = _non_neg()
    release_time_s: float = _non_neg()
    reweigh_time_s: float = _non_neg()
    sim_noise_kg: float = _non_neg()
    payload_id_prefix: str = Field(min_length=1)
    mission_id_prefix: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> PayloadSettings:
        if self.mass_min_kg > self.mass_max_kg:
            raise ValueError("payload.mass_min_kg must not exceed payload.mass_max_kg")
        if self.release_energy_wh_nominal > self.release_energy_wh_max:
            raise ValueError(
                "payload.release_energy_wh_nominal must not exceed payload.release_energy_wh_max"
            )
        if self.sim_noise_kg >= self.weight_accuracy_kg:
            raise ValueError(
                "payload.sim_noise_kg must be below payload.weight_accuracy_kg"
            )
        return self


class TimingSettings(_Section):
    status_rate_hz: float = _pos()
    heartbeat_rate_hz: float = _pos()
    command_timeout_s: float = _pos()
    command_max_age_s: float = _pos()
    command_complete_timeout_s: float = _pos()
    release_grace_s: float = _non_neg()
    route_blocked_clear_s: float = _pos()
    stale_after_s: float = _pos()
    ui_command_feedback_max_s: float = _pos()
    fault_report_max_s: float = _pos()
    delivery_confirm_max_s: float = _pos()
    clock_skew_warn_s: float = _pos()

    @model_validator(mode="after")
    def _check(self) -> TimingSettings:
        if self.command_timeout_s > self.command_complete_timeout_s:
            raise ValueError(
                "timing.command_timeout_s must not exceed timing.command_complete_timeout_s"
            )
        return self


class LinkSettings(_Section):
    degraded_latency_ms: float = _pos()
    degraded_loss_pct: float = _pct()
    lost_after_s: float = _pos()
    prerelease_wait_s: float = _non_neg()


class AlertSettings(_Section):
    power_low_pct: float = _pct()
    power_fault_pct: float = _pct()

    @model_validator(mode="after")
    def _check(self) -> AlertSettings:
        if self.power_fault_pct > self.power_low_pct:
            raise ValueError(
                "alerts.power_fault_pct must not exceed alerts.power_low_pct"
            )
        return self


class EventBufferSettings(_Section):
    max_events: int = Field(gt=0)
    file: str = Field(min_length=1)
    batch_size: int = Field(gt=0)

    @model_validator(mode="after")
    def _check(self) -> EventBufferSettings:
        if self.batch_size > self.max_events:
            raise ValueError(
                "event_buffer.batch_size must not exceed event_buffer.max_events"
            )
        return self


class Place(_Section):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class NetworkSettings(_Section):
    link_host: str = Field(min_length=1)
    link_ground_port: int = Field(gt=0, le=65535)
    link_vehicle_port: int = Field(gt=0, le=65535)
    ui_port: int = Field(gt=0, le=65535)
    reconnect_min_s: float = _pos()
    reconnect_max_s: float = _pos()

    @model_validator(mode="after")
    def _check(self) -> NetworkSettings:
        if self.reconnect_min_s > self.reconnect_max_s:
            raise ValueError(
                "network.reconnect_min_s must not exceed network.reconnect_max_s"
            )
        ports = [self.link_ground_port, self.link_vehicle_port, self.ui_port]
        if len(set(ports)) != len(ports):
            raise ValueError(
                "network.link_ground_port, link_vehicle_port and ui_port must all differ"
            )
        return self


class UiSettings(_Section):
    snapshot_debounce_ms: float = _non_neg()
    commands_shown: int = Field(gt=0)


class LinkStandinSettings(_Section):
    base_latency_ms: float = _non_neg()
    jitter_ms: float = _non_neg()
    loss_pct: float = _pct()


class NavStandinSettings(_Section):
    speed_mps: float = _pos()
    route_points: int = Field(ge=2)
    auto_depart: bool


class PowerStandinSettings(_Section):
    start_battery_pct: float = _pct()
    drain_pct_per_min: float = _non_neg()


class StandinSettings(_Section):
    time_scale: float = _pos()
    link: LinkStandinSettings
    nav: NavStandinSettings
    power: PowerStandinSettings


class LoggingSettings(_Section):
    dir: str = Field(min_length=1)


class Settings(_Section):
    version: Literal[1]
    test_mode: bool
    payload: PayloadSettings
    timing: TimingSettings
    link: LinkSettings
    alerts: AlertSettings
    event_buffer: EventBufferSettings
    places: list[Place] = Field(min_length=1)
    network: NetworkSettings
    ui: UiSettings
    standins: StandinSettings
    logging: LoggingSettings

    # The repository root: the folder that contains config/. Set by load_settings.
    _root: Path = PrivateAttr(default_factory=Path.cwd)

    @model_validator(mode="after")
    def _check(self) -> Settings:
        ids = [p.id for p in self.places]
        if len(set(ids)) != len(ids):
            raise ValueError("places ids must be unique")
        return self

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, relative: str) -> Path:
        """Resolve a path from the settings (logging.dir, event_buffer.file)
        against the repository root, never the current working directory."""
        path = Path(relative)
        return path if path.is_absolute() else self._root / path


def find_config(start: Path | None = None) -> Path:
    """Find config/config.yaml from `start` (default: the current folder) upward."""
    here = (start or Path.cwd()).resolve()
    for folder in (here, *here.parents):
        candidate = folder / RELATIVE_PATH
        if candidate.is_file():
            return candidate
    raise ConfigError(f"{RELATIVE_PATH} not found in {here} or any parent folder")


def _format_errors(err: ValidationError) -> str:
    lines = []
    for e in err.errors():
        key = ".".join(str(part) for part in e["loc"]) or "(top level)"
        lines.append(f"  {key}: {e['msg']}")
    return "\n".join(lines)


def load_settings(path: str | Path | None = None) -> Settings:
    """Load and validate the settings file.

    With no path, use the AEGIS_CONFIG environment variable if set, otherwise
    search for config/config.yaml from the current folder upward.
    """
    if path is None:
        env = os.environ.get(ENV_VAR)
        path = Path(env) if env else find_config()
    path = Path(path).resolve()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read settings file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"settings file {path} is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"settings file {path} must be a mapping at the top level")

    try:
        settings = Settings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(
            f"invalid settings in {path}:\n{_format_errors(exc)}"
        ) from exc

    settings._root = _repo_root(path)
    return settings


def _repo_root(config_path: Path) -> Path:
    """The folder that contains config/. For a settings file outside a config/
    folder (a test fixture, AEGIS_CONFIG elsewhere), use the nearest repository
    found upward from it, else the file's own folder."""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    try:
        return find_config(config_path.parent).parent.parent
    except ConfigError:
        return config_path.parent
