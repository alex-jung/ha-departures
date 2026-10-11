"""Tests for the expected-departure and delay sensors."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_departures.api.data_classes import Departure
from custom_components.ha_departures.config_flow import DeparturesFlowHandler
from custom_components.ha_departures.const import (
    ATTR_DEPARTURE_DELAY,
    ATTR_TIMES,
    CONF_LINES,
    CONF_STOP_IDS,
    DOMAIN,
)
from custom_components.ha_departures.coordinator import (
    DeparturesDataUpdateCoordinator,
)
from custom_components.ha_departures.sensor import (
    DeparturesDelaySensor,
    DeparturesExpectedSensor,
    DeparturesSensor,
)

LINE = {
    "route_id": "route-1",
    "direction_id": "0",
    "route_short_name": "U1",
    "head_sign": "Hauptbahnhof",
    "transport_mode": "SUBWAY",
}

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _departure(
    trip_id: str,
    scheduled_in: timedelta,
    delay: timedelta = timedelta(),
    *,
    real_time: bool = True,
    cancelled: bool = False,
    trip_cancelled: bool = False,
) -> Departure:
    scheduled = dt_util.now() + scheduled_in
    return Departure(
        route_id=LINE["route_id"],
        direction_id=LINE["direction_id"],
        trip_id=trip_id,
        stop_id="stop-1",
        departure=scheduled + delay,
        head_sign=LINE["head_sign"],
        scheduled_departure=scheduled,
        real_time=real_time,
        cancelled=cancelled,
        trip_cancelled=trip_cancelled,
    )


def _stop_time(trip_id: str, scheduled: str, estimated: str) -> dict:
    return {
        "routeId": LINE["route_id"],
        "directionId": LINE["direction_id"],
        "tripId": trip_id,
        "headsign": LINE["head_sign"],
        "realTime": True,
        "place": {
            "stopId": "stop-1",
            "departure": estimated,
            "scheduledDeparture": scheduled,
        },
    }


@pytest.fixture
async def coordinator(hass: HomeAssistant) -> DeparturesDataUpdateCoordinator:
    """Coordinator mit einer Linie, ohne API-Abruf."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        data={CONF_STOP_IDS: ["stop-1"]},
        options={CONF_LINES: [LINE]},
    )
    entry.add_to_hass(hass)
    return DeparturesDataUpdateCoordinator(hass, entry)


def _update(entity) -> None:
    with patch.object(entity, "async_write_ha_state"):
        entity._handle_coordinator_update()


# ---------------------------------------------------------------------------
# Delay sensor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("delay", "expected"),
    [
        (timedelta(minutes=12), 12),
        (timedelta(), 0),
        (timedelta(minutes=-1), -1),
        (timedelta(seconds=90), 2),
    ],
    ids=["late", "on-time", "early", "rounded"],
)
async def test_delay_in_minutes(hass, coordinator, delay, expected):
    """Die Verspätung wird in ganzen Minuten geliefert."""
    coordinator.data = [_departure("trip-1", timedelta(minutes=5), delay)]
    sensor = DeparturesDelaySensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value == expected


async def test_delay_unknown_without_real_time(hass, coordinator):
    """Ohne Echtzeitdaten ist die Verspätung unbekannt, nicht 0."""
    coordinator.data = [_departure("trip-1", timedelta(minutes=5), real_time=False)]
    sensor = DeparturesDelaySensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value is None


async def test_delay_unknown_without_departures(hass, coordinator):
    """Ohne kommende Abfahrten ist die Verspätung unbekannt."""
    coordinator.data = []
    sensor = DeparturesDelaySensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Expected departure sensor
# ---------------------------------------------------------------------------


async def test_expected_uses_real_time(hass, coordinator):
    """Die erwartete Abfahrt ist die Echtzeit, nicht die Planzeit."""
    delayed = _departure("trip-1", timedelta(minutes=5), timedelta(minutes=12))
    coordinator.data = [delayed]
    sensor = DeparturesExpectedSensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value == delayed.departure


async def test_expected_falls_back_to_scheduled(hass, coordinator):
    """Ohne Echtzeit-Abfahrt wird die Planzeit verwendet."""
    departure = _departure("trip-1", timedelta(minutes=5))
    departure.departure = None
    coordinator.data = [departure]
    sensor = DeparturesExpectedSensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value == departure.scheduled_departure


@pytest.mark.parametrize(
    "cancel",
    [{"cancelled": True}, {"trip_cancelled": True}],
    ids=["stop-cancelled", "trip-cancelled"],
)
async def test_cancelled_trips_are_skipped(hass, coordinator, cancel):
    """Ausgefallene Fahrten werden von Echtzeit- und Verspätungssensor übersprungen."""
    cancelled = _departure("trip-1", timedelta(minutes=2), **cancel)
    running = _departure("trip-2", timedelta(minutes=12), timedelta(minutes=3))
    coordinator.data = [cancelled, running]

    expected = DeparturesExpectedSensor(coordinator, LINE)
    delay = DeparturesDelaySensor(coordinator, LINE)
    main = DeparturesSensor(hass, coordinator, LINE)

    for entity in (expected, delay, main):
        _update(entity)

    assert expected.native_value == running.departure
    assert delay.native_value == 3
    # the main sensor keeps showing the next scheduled trip, cancelled or not
    assert main.native_value == cancelled.scheduled_departure


async def test_expected_unknown_when_all_cancelled(hass, coordinator):
    """Fallen alle Fahrten aus, ist die erwartete Abfahrt unbekannt."""
    coordinator.data = [_departure("trip-1", timedelta(minutes=2), cancelled=True)]
    sensor = DeparturesExpectedSensor(coordinator, LINE)

    _update(sensor)

    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Main sensor
# ---------------------------------------------------------------------------


async def test_times_contain_delay(hass, coordinator):
    """Jeder Eintrag in times enthält die Verspätung in Minuten."""
    coordinator.data = [
        _departure("trip-1", timedelta(minutes=2), timedelta(minutes=4)),
        _departure("trip-2", timedelta(minutes=12), real_time=False),
    ]
    sensor = DeparturesSensor(hass, coordinator, LINE)

    _update(sensor)

    delays = [
        t[ATTR_DEPARTURE_DELAY] for t in sensor.extra_state_attributes[ATTR_TIMES]
    ]
    assert delays == [4, None]


async def test_unique_ids_are_stable(hass, coordinator):
    """Die unique_id des bestehenden Sensors bleibt unverändert."""
    base = "hub-route-1-0-hauptbahnhof"

    assert DeparturesSensor(hass, coordinator, LINE).unique_id == base
    assert DeparturesExpectedSensor(coordinator, LINE).unique_id == f"{base}-expected"
    assert DeparturesDelaySensor(coordinator, LINE).unique_id == f"{base}-delay"


# ---------------------------------------------------------------------------
# Integration setup
# ---------------------------------------------------------------------------


async def test_setup_creates_grouped_sensors(
    hass: HomeAssistant, enable_custom_integrations
):
    """Beim Setup entstehen drei Sensoren pro Linie plus Last-update, alle unter einem Gerät."""
    now = dt_util.utcnow().replace(microsecond=0)
    scheduled = now + timedelta(minutes=10)
    estimated = scheduled + timedelta(minutes=12)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hub",
        version=DeparturesFlowHandler.VERSION,
        minor_version=DeparturesFlowHandler.MINOR_VERSION,
        data={CONF_STOP_IDS: ["stop-1"]},
        options={CONF_LINES: [LINE]},
    )
    entry.add_to_hass(hass)

    response = {
        "stopTimes": [
            _stop_time("trip-1", scheduled.isoformat(), estimated.isoformat())
        ]
    }

    api_get = AsyncMock(return_value=response)

    with patch("custom_components.ha_departures.coordinator.MotisApi.get", api_get):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # sensors use the first refresh instead of requesting their own
    api_get.assert_awaited_once()

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    by_suffix = {e.unique_id.rsplit("-", 1)[-1]: e for e in entities}
    assert len(entities) == 4
    assert by_suffix["update"].entity_category is EntityCategory.DIAGNOSTIC

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert (DOMAIN, entry.entry_id) in device.identifiers
    assert device.name == "Hub"
    assert {e.device_id for e in entities} == {device.id}

    main = hass.states.get(by_suffix["hauptbahnhof"].entity_id)
    expected = hass.states.get(by_suffix["expected"].entity_id)
    delay = hass.states.get(by_suffix["delay"].entity_id)

    assert main.attributes["device_class"] == SensorDeviceClass.TIMESTAMP
    assert main.state == scheduled.isoformat()
    assert expected.state == estimated.isoformat()
    assert delay.state == "12"
    assert delay.attributes["unit_of_measurement"] == "min"
