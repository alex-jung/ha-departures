"""Tests for DeparturesDataUpdateCoordinator data fetching."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_departures.const import CONF_LINES, CONF_STOP_IDS, DOMAIN
from custom_components.ha_departures.coordinator import (
    DeparturesDataUpdateCoordinator,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _stop_time(trip_id: str, stop_id: str = "stop-1") -> dict:
    return {
        "routeId": "route-1",
        "directionId": "0",
        "tripId": trip_id,
        "headsign": "Hauptbahnhof",
        "realTime": True,
        "place": {
            "stopId": stop_id,
            "departure": "2026-10-11T10:30:00+00:00",
            "scheduledDeparture": "2026-10-11T10:28:00+00:00",
        },
    }


@pytest.fixture
async def coordinator(hass: HomeAssistant) -> DeparturesDataUpdateCoordinator:
    """Coordinator mit einer Linie und gemocktem API-Client."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={CONF_STOP_IDS: ["stop-1"]},
        options={CONF_LINES: [{"route_id": "route-1", "direction_id": "0"}]},
    )
    entry.add_to_hass(hass)
    coordinator = DeparturesDataUpdateCoordinator(hass, entry)
    coordinator._client.get = AsyncMock()
    return coordinator


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_client_error_raises_update_failed(coordinator):
    """Netzwerkfehler werden als UpdateFailed weitergereicht."""
    coordinator._client.get.side_effect = ClientError("boom")

    with pytest.raises(UpdateFailed, match="API request failed"):
        await coordinator._async_update_data()


async def test_timeout_raises_update_failed(coordinator):
    """Timeouts werden als UpdateFailed weitergereicht."""
    coordinator._client.get.side_effect = TimeoutError()

    with pytest.raises(UpdateFailed, match="API request failed"):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "response",
    [None, [], "not json"],
    ids=["null", "list", "string"],
)
async def test_unexpected_response_raises_update_failed(coordinator, response):
    """Unerwartete API-Antworten werden als UpdateFailed weitergereicht."""
    coordinator._client.get.return_value = response

    with pytest.raises(UpdateFailed, match="Unexpected API response"):
        await coordinator._async_update_data()


async def test_invalid_json_raises_update_failed(coordinator):
    """Nicht lesbares JSON wird als UpdateFailed weitergereicht."""
    coordinator._client.get.side_effect = ValueError("Expecting value")

    with pytest.raises(UpdateFailed, match="Unexpected API response"):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------


async def test_duplicates_are_removed_and_order_is_kept(coordinator):
    """Doppelte Einträge fallen weg, die Reihenfolge der API bleibt erhalten."""
    coordinator._client.get.return_value = {
        "stopTimes": [
            _stop_time("trip-2"),
            _stop_time("trip-1"),
            _stop_time("trip-2"),
            _stop_time("trip-3", stop_id="other-stop"),
        ]
    }

    departures = await coordinator._async_update_data()

    assert [d.trip_id for d in departures] == ["trip-2", "trip-1"]
