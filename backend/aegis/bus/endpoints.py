"""Which side each endpoint lives on (contracts section 2).

A message whose dst is on the other side crosses Team 3's link; a message
whose dst is on the same side never touches it.
"""

from __future__ import annotations

from typing import Literal

from aegis.common.models import ENDPOINTS

Side = Literal["ground", "vehicle", "link"]

SIDES: dict[str, Side] = {
    "ground.command_manager": "ground",
    "ground.status_monitor": "ground",
    "ground.alert_manager": "ground",
    "ground.mission_log": "ground",
    "ground.ui_server": "ground",
    "ground.fault_injector": "ground",
    "team1.integration": "ground",
    "team3.link": "link",
    "vehicle.payload_controller": "vehicle",
    "vehicle.payload_simulator": "vehicle",
    "vehicle.event_buffer": "vehicle",
    "vehicle.link_watch": "vehicle",
    "vehicle.test_agent": "vehicle",
    "team2.nav": "vehicle",
    "team4.power": "vehicle",
}
assert set(SIDES) == set(ENDPOINTS), (
    "SIDES must cover every endpoint in models.Endpoint"
)


def side_of(endpoint: str) -> Side:
    try:
        return SIDES[endpoint]
    except KeyError:
        raise ValueError(f"unknown endpoint {endpoint!r}") from None
