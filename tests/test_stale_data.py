"""Tests for stale-data handling in coordinator and sensor."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_departures.api.data_classes import Departure
from custom_components.ha_departures.const import (
    ATTR_TIMES,
    CONF_LINES,
    CONF_STOP_IDS,
    DOMAIN,
    STALE_DATA_TIMEOUT,
)
from custom_components.ha_departures.coordinator import (
    DeparturesDataUpdateCoordinator,
)
from custom_components.ha_departures.sensor import DeparturesSensor

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
    trip_id: str, scheduled_in: timedelta, delay: timedelta = timedelta()
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
        real_time=True,
    )


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


@pytest.fixture
async def sensor(
    hass: HomeAssistant, coordinator: DeparturesDataUpdateCoordinator
) -> DeparturesSensor:
    """Sensor für LINE, ohne Registrierung in HA."""
    entity = DeparturesSensor(hass, coordinator, LINE)
    entity.hass = hass
    return entity


# ---------------------------------------------------------------------------
# Coordinator: data age
# ---------------------------------------------------------------------------


async def test_no_successful_update_has_no_valid_data(coordinator):
    """Ohne erfolgreichen Abruf gibt es kein Datenalter und keine gültigen Daten."""
    assert coordinator.data_age is None
    assert coordinator.has_valid_data is False


async def test_recent_update_is_valid(coordinator, freezer: FrozenDateTimeFactory):
    """Daten sind bis kurz vor STALE_DATA_TIMEOUT gültig."""
    coordinator.last_update_success_time = dt_util.utcnow()
    freezer.tick(timedelta(seconds=STALE_DATA_TIMEOUT - 1))

    assert coordinator.data_age == timedelta(seconds=STALE_DATA_TIMEOUT - 1)
    assert coordinator.has_valid_data is True


async def test_old_update_is_stale(coordinator, freezer: FrozenDateTimeFactory):
    """Ab STALE_DATA_TIMEOUT gelten die Daten als veraltet."""
    coordinator.last_update_success_time = dt_util.utcnow()
    freezer.tick(timedelta(seconds=STALE_DATA_TIMEOUT))

    assert coordinator.has_valid_data is False


# ---------------------------------------------------------------------------
# Sensor: availability
# ---------------------------------------------------------------------------


async def test_sensor_stays_available_after_failed_update(coordinator, sensor):
    """Ein fehlgeschlagener Abruf macht den Sensor nicht sofort unavailable."""
    coordinator.last_update_success_time = dt_util.utcnow()
    coordinator.last_update_success = False

    assert sensor.available is True


async def test_sensor_unavailable_when_data_is_stale(
    coordinator, sensor, freezer: FrozenDateTimeFactory
):
    """Nach STALE_DATA_TIMEOUT ohne Erfolg wird der Sensor unavailable."""
    coordinator.last_update_success_time = dt_util.utcnow()
    freezer.tick(timedelta(seconds=STALE_DATA_TIMEOUT + 1))

    assert sensor.available is False


# ---------------------------------------------------------------------------
# Sensor: departed entries are dropped from cached data
# ---------------------------------------------------------------------------


async def test_departed_entry_is_dropped_without_new_update(
    coordinator, sensor, freezer: FrozenDateTimeFactory
):
    """Abgefahrene Verbindungen verschwinden ohne neuen API-Abruf."""
    first = _departure("trip-1", timedelta(minutes=2))
    second = _departure("trip-2", timedelta(minutes=12))
    coordinator.data = [first, second]

    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()
        assert sensor.native_value == first.scheduled_departure

        freezer.tick(timedelta(minutes=3))
        sensor._async_refresh_from_cache(dt_util.utcnow())

    assert sensor.native_value == second.scheduled_departure
    assert len(sensor.extra_state_attributes[ATTR_TIMES]) == 1


async def test_delayed_entry_is_kept_after_scheduled_time(
    coordinator, sensor, freezer: FrozenDateTimeFactory
):
    """Verspätete Verbindung bleibt nach der Planzeit bis zur Echtzeit-Abfahrt."""
    delayed = _departure("trip-1", timedelta(minutes=2), delay=timedelta(minutes=10))
    coordinator.data = [delayed]

    freezer.tick(timedelta(minutes=5))

    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()

    assert sensor.native_value == delayed.scheduled_departure


async def test_all_departed_clears_state(
    coordinator, sensor, freezer: FrozenDateTimeFactory
):
    """Sind alle Verbindungen abgefahren, wird der Zustand geleert."""
    coordinator.data = [_departure("trip-1", timedelta(minutes=1))]
    freezer.tick(timedelta(minutes=2))

    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_coordinator_update()

    assert sensor.native_value is None
    assert sensor.extra_state_attributes[ATTR_TIMES] == []
