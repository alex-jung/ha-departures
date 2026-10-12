"""Tests for DeparturesDataUpdateCoordinator data fetching."""

import logging
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError, ClientResponseError
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


@pytest.fixture
def multi_stop_coordinator(coordinator) -> DeparturesDataUpdateCoordinator:
    """Coordinator mit zwei eindeutigen Stop-IDs ("stop-1" doppelt)."""
    coordinator._stop_ids = ["stop-1", "stop-1_G", "stop-2"]
    return coordinator


def _response_error(status: int) -> ClientResponseError:
    return ClientResponseError(
        request_info=Mock(real_url="http://test.api/stoptimes"),
        history=(),
        status=status,
    )


def _queried_stop_ids(coordinator) -> list[str]:
    return [
        call.kwargs["params"]["stopId"]
        for call in coordinator._client.get.call_args_list
    ]


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


# ---------------------------------------------------------------------------
# Unknown stop IDs
# ---------------------------------------------------------------------------


async def test_unknown_stop_id_falls_back_to_next_one(multi_stop_coordinator, caplog):
    """Kennt die API eine Stop-ID nicht (404), wird die nächste abgefragt."""
    coordinator = multi_stop_coordinator
    coordinator._client.get.side_effect = [
        _response_error(404),
        {"stopTimes": [_stop_time("trip-1", stop_id="stop-2")]},
    ]

    with caplog.at_level(logging.WARNING):
        departures = await coordinator._async_update_data()

    assert [d.trip_id for d in departures] == ["trip-1"]
    assert _queried_stop_ids(coordinator) == ["stop-1", "stop-2"]

    warnings = [r.getMessage() for r in caplog.records if "stop-1" in r.getMessage()]

    assert len(warnings) == 1
    assert "Hub" in warnings[0]


async def test_working_stop_id_is_remembered(multi_stop_coordinator):
    """Nach dem Rückfall fragt das nächste Update nur noch die funktionierende ID ab."""
    coordinator = multi_stop_coordinator
    response = {"stopTimes": [_stop_time("trip-1", stop_id="stop-2")]}
    coordinator._client.get.side_effect = [_response_error(404), response]

    await coordinator._async_update_data()

    coordinator._client.get.reset_mock(side_effect=True)
    coordinator._client.get.return_value = response

    departures = await coordinator._async_update_data()

    assert [d.trip_id for d in departures] == ["trip-1"]
    assert _queried_stop_ids(coordinator) == ["stop-2"]


async def test_all_stop_ids_unknown_raises_update_failed(multi_stop_coordinator):
    """Kennt die API keine der Stop-IDs, schlägt das Update fehl."""
    coordinator = multi_stop_coordinator
    coordinator._client.get.side_effect = _response_error(404)

    with pytest.raises(UpdateFailed, match="API request failed"):
        await coordinator._async_update_data()

    assert _queried_stop_ids(coordinator) == ["stop-1", "stop-2"]


async def test_other_http_error_does_not_try_next_stop_id(multi_stop_coordinator):
    """Andere HTTP-Fehler als 404 führen nicht zur nächsten Stop-ID."""
    coordinator = multi_stop_coordinator
    coordinator._client.get.side_effect = _response_error(500)

    with pytest.raises(UpdateFailed, match="API request failed"):
        await coordinator._async_update_data()

    assert _queried_stop_ids(coordinator) == ["stop-1"]
