"""Tests for DeparturesDataUpdateCoordinator data fetching."""

import logging
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_departures.const import CONF_LINES, CONF_STOP_IDS, DOMAIN
from custom_components.ha_departures.coordinator import (
    DeparturesDataUpdateCoordinator,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _stop_time(
    trip_id: str, stop_id: str = "stop-1", route_id: str = "route-1"
) -> dict:
    return {
        "routeId": route_id,
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


# ---------------------------------------------------------------------------
# Rarely running lines (stop-wide window)
# ---------------------------------------------------------------------------


def _page(stop_times: list[dict], cursor: str | None = None) -> dict:
    page: dict = {"stopTimes": stop_times}

    if cursor:
        page["nextPageCursor"] = cursor

    return page


def _requested_params(coordinator) -> list[dict]:
    return [call.kwargs["params"] for call in coordinator._client.get.call_args_list]


@pytest.fixture
def two_line_coordinator(coordinator) -> DeparturesDataUpdateCoordinator:
    """Coordinator mit der häufigen Linie "route-1" und der seltenen Linie "rare"."""
    coordinator._lines = [
        {"route_id": "route-1", "direction_id": "0"},
        {"route_id": "rare", "direction_id": "0", "route_short_name": "X1"},
    ]
    coordinator._lines_count = 2

    return coordinator


async def test_rare_line_behind_busy_lines_is_loaded_from_next_page(
    two_line_coordinator,
):
    """Liegt eine Linie hinter dem ersten Fenster, wird die nächste Seite geladen."""
    coordinator = two_line_coordinator
    busy = [_stop_time(f"busy-{i}") for i in range(5)]
    rare = _stop_time("rare-1", route_id="rare")
    coordinator._client.get.side_effect = [
        _page(busy, cursor="cursor-1"),
        _page([rare]),
    ]

    departures = await coordinator._async_update_data()

    assert "rare-1" in [d.trip_id for d in departures]

    first, second = _requested_params(coordinator)

    assert "pageCursor" not in first
    assert second["pageCursor"] == "cursor-1"


async def test_no_further_page_when_all_lines_are_in_first_page(two_line_coordinator):
    """Sind alle Linien im ersten Fenster, bleibt es bei einer Anfrage."""
    coordinator = two_line_coordinator
    coordinator._client.get.return_value = _page(
        [_stop_time("busy-1"), _stop_time("rare-1", route_id="rare")],
        cursor="cursor-1",
    )

    await coordinator._async_update_data()

    assert len(_requested_params(coordinator)) == 1


async def test_window_size_is_remembered(two_line_coordinator):
    """Das nächste Update holt das gemessene Fenster in einer einzigen Anfrage."""
    coordinator = two_line_coordinator
    busy = [_stop_time(f"busy-{i}") for i in range(300)]
    rare = _stop_time("rare-1", route_id="rare")
    coordinator._client.get.side_effect = [
        _page(busy, cursor="cursor-1"),
        _page([rare]),
    ]

    await coordinator._async_update_data()

    coordinator._client.get.reset_mock(side_effect=True)
    coordinator._client.get.return_value = _page([*busy, rare])

    departures = await coordinator._async_update_data()

    assert "rare-1" in [d.trip_id for d in departures]

    (params,) = _requested_params(coordinator)

    assert int(params["n"]) > 300
    assert "pageCursor" not in params


async def test_missing_line_limits_requests_and_pauses_search(
    two_line_coordinator, caplog
):
    """Eine Linie, die nie auftaucht, kostet nicht bei jedem Update Zusatzseiten."""
    coordinator = two_line_coordinator
    counter = iter(range(10_000))

    async def _endless(_command, params, **_kwargs):
        return _page(
            [_stop_time(f"busy-{next(counter)}") for _ in range(int(params["n"]))],
            cursor="more",
        )

    coordinator._client.get.side_effect = _endless

    with caplog.at_level(logging.INFO):
        await coordinator._async_update_data()

    loaded = sum(int(p["n"]) for p in _requested_params(coordinator))

    assert loaded <= 1000
    assert len(_requested_params(coordinator)) > 1

    coordinator._client.get.reset_mock()
    coordinator._client.get.side_effect = _endless

    with caplog.at_level(logging.INFO):
        await coordinator._async_update_data()

    assert len(_requested_params(coordinator)) == 1

    warnings = [r for r in caplog.records if "rare" in r.getMessage()]

    assert len(warnings) == 1
    assert "X1" in warnings[0].getMessage()
    # missing lines are normal for rarely running lines, no warning in the log
    assert warnings[0].levelno == logging.INFO


async def test_search_is_repeated_after_pause(two_line_coordinator):
    """Nach der Pause wird erneut nach der fehlenden Linie gesucht."""
    coordinator = two_line_coordinator
    busy = [_stop_time(f"busy-{i}") for i in range(5)]
    coordinator._client.get.return_value = _page(busy, cursor="cursor-1")

    await coordinator._async_update_data()

    assert coordinator._deep_search_after is not None

    coordinator._deep_search_after = dt_util.utcnow() - timedelta(seconds=1)
    coordinator._client.get.reset_mock()

    await coordinator._async_update_data()

    assert len(_requested_params(coordinator)) > 1


async def test_error_on_further_page_keeps_first_page(two_line_coordinator):
    """Scheitert eine Zusatzseite, bleiben die Daten der ersten Seite erhalten."""
    coordinator = two_line_coordinator
    busy = [_stop_time(f"busy-{i}") for i in range(5)]
    coordinator._client.get.side_effect = [
        _page(busy, cursor="cursor-1"),
        ClientError("boom"),
    ]

    departures = await coordinator._async_update_data()

    assert len(departures) == 5
    assert coordinator._deep_search_after is None


# ---------------------------------------------------------------------------
# Changed route type suffix of a stored line
# ---------------------------------------------------------------------------


def _typed(trip_id: str, route_id: str, route_type: int, name: str) -> dict:
    stop_time = _stop_time(trip_id, route_id=route_id)
    stop_time.update({"routeType": route_type, "routeShortName": name})

    return stop_time


@pytest.fixture
def typed_coordinator(coordinator) -> DeparturesDataUpdateCoordinator:
    """Coordinator mit einer DELFI-Linie, gespeichert mit Suffix "_100"."""
    coordinator._lines = [
        {
            "route_id": "de-DELFI_de:beg:RE3:_100",
            "direction_id": "0",
            "route_short_name": "RE3",
        }
    ]

    return coordinator


async def test_line_with_changed_route_type_suffix_is_found(typed_coordinator):
    """Gespeichert "_100", die API liefert "_106": die Linie wird gefunden."""
    changed = _typed("trip-1", "de-DELFI_de:beg:RE3:_106", 106, "RE3")

    assert typed_coordinator._first_positions([_stop_time("other"), changed]) == (
        {},
        {0: 1},
    )


async def test_line_with_other_short_name_is_not_found(typed_coordinator):
    """Gleiche Basis-ID, aber anderer Kurzname: keine Zuordnung."""
    other = _typed("trip-1", "de-DELFI_de:beg:RE3:_106", 106, "RE2")

    assert typed_coordinator._first_positions([other]) == ({}, {})


async def test_changed_line_sets_window_without_warning(typed_coordinator, caplog):
    """Eine nur über den geänderten Suffix gefundene Linie bestimmt das Fenster.

    Nach der exakten ID wird weiter gesucht, aber nicht bei jedem Update.
    """
    coordinator = typed_coordinator
    changed = _typed("trip-1", "de-DELFI_de:beg:RE3:_106", 106, "RE3")
    coordinator._client.get.side_effect = [
        _page([_stop_time("other"), changed], cursor="cursor-1"),
        _page([]),
    ]

    with caplog.at_level(logging.INFO):
        departures = await coordinator._async_update_data()

    assert "trip-1" in [d.trip_id for d in departures]
    assert coordinator._window_n == 1 + 1 + 25
    assert coordinator._deep_search_after is not None
    assert not [r for r in caplog.records if "RE3" in r.getMessage()]


async def test_exact_route_id_wins_over_changed_suffix(coordinator):
    """Liegt eine Route gleicher Klasse vorn, wird trotzdem die eigene gesucht.

    Im DELFI-Feed (routes.txt) stehen Buslinien teils als "_700" und "_3"
    mit gleicher Basis und gleichem Namen nebeneinander.
    """
    coordinator._lines = [
        {
            "route_id": "de-DELFI_de:mvv:X1:_700",
            "direction_id": "0",
            "route_short_name": "X1",
        }
    ]
    neighbour = _typed("neighbour", "de-DELFI_de:mvv:X1:_3", 3, "X1")
    own = _typed("own", "de-DELFI_de:mvv:X1:_700", 700, "X1")
    coordinator._client.get.side_effect = [
        _page([neighbour, _stop_time("other")], cursor="cursor-1"),
        _page([own]),
    ]

    await coordinator._async_update_data()

    assert len(_requested_params(coordinator)) == 2
    assert coordinator._window_n == 2 + 1 + 25
    assert coordinator._deep_search_after is None


async def test_ice_line_ignores_ic_of_same_number(coordinator):
    """ICE ("_101") und IC ("_102") derselben Nummer sind verschiedene Züge.

    Gemessen in München Hbf: Linie 62.
    """
    coordinator._lines = [
        {
            "route_id": "de-DELFI_162319_102",
            "direction_id": "0",
            "route_short_name": "62",
        }
    ]
    ice = _typed("ice", "de-DELFI_162319_101", 101, "62")

    assert coordinator._first_positions([ice]) == ({}, {})
