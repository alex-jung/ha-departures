"""Tests for the DeparturesSensor entity."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from apyefa import Departure, TransportType
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE

from custom_components.ha_departures.const import (
    ATTR_DIRECTION,
    ATTR_ESTIMATED_DEPARTURE_TIME,
    ATTR_LINE_ID,
    ATTR_LINE_NAME,
    ATTR_PLANNED_DEPARTURE_TIME,
    ATTR_PROVIDER_URL,
    ATTR_TIMES,
    ATTR_TRANSPORT_TYPE,
)
from custom_components.ha_departures.helper import UnstableDepartureTime
from custom_components.ha_departures.sensor import DeparturesSensor

from .conftest import create_mock_coordinator, create_mock_line


async def test_sensor_init(hass):
    """Test initialization of DeparturesSensor."""
    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    assert sensor._line == line.name
    assert sensor._transport == line.product
    assert sensor._line_id == line.id
    assert sensor._destination == line.destination
    assert not sensor._value  # Initial value should be None
    assert sensor._times == []  # Initial times should be empty array
    assert sensor._attr_name == f"Mock Stop-{line.name}-{line.destination.name}"
    assert sensor._attr_unique_id is not None
    assert sensor._attr_extra_state_attributes[ATTR_LINE_NAME] == line.name
    assert sensor._attr_extra_state_attributes[ATTR_LINE_ID] == line.id
    assert sensor._attr_extra_state_attributes[ATTR_TRANSPORT_TYPE] == line.product.name
    assert sensor._attr_extra_state_attributes[ATTR_DIRECTION] == line.destination.name
    assert sensor._attr_extra_state_attributes[ATTR_PROVIDER_URL] == coordinator.api_url
    assert (
        sensor._attr_extra_state_attributes[ATTR_LATITUDE] == coordinator.stop_coord[0]
    )
    assert (
        sensor._attr_extra_state_attributes[ATTR_LONGITUDE] == coordinator.stop_coord[1]
    )
    assert sensor._attr_extra_state_attributes[ATTR_TIMES] == []


@pytest.mark.parametrize(
    ("transport_type", "expected_icon"),
    [
        (TransportType.CITY_BUS, "mdi:bus"),
        (TransportType.REGIONAL_BUS, "mdi:bus"),
        (TransportType.EXPRESS_BUS, "mdi:bus"),
        (TransportType.SUBWAY, "mdi:subway"),
        (TransportType.TRAM, "mdi:tram"),
        (TransportType.AST, "mdi:taxi"),
        (TransportType.SUBURBAN, "mdi:train"),
        (TransportType.TRAIN, "mdi:train"),
        (TransportType.CITY_RAIL, "mdi:train"),
        (TransportType.FERRY, "mdi:train-bus"),
    ],
)
async def test_sensor_native_value_and_icon(hass, transport_type, expected_icon):
    """Test native_value and icon properties of DeparturesSensor."""
    line = create_mock_line()
    line.product = transport_type

    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    # Initially, native_value should be None
    assert sensor.native_value is None

    # Test icon based on transport type
    assert sensor.icon == expected_icon


async def test_sensor_clear_times(hass):
    """Test clearing times in DeparturesSensor."""
    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    time_1 = Mock(spec=UnstableDepartureTime)
    time_2 = Mock(spec=UnstableDepartureTime)
    time_3 = Mock(spec=UnstableDepartureTime)

    # Simulate adding times
    sensor._times = [
        time_1,
        time_2,
        time_3,
    ]
    sensor._value = len(sensor._times)

    assert sensor.native_value == 3

    # Clear times
    sensor.clear_times()

    assert sensor.native_value is None
    assert sensor._attr_extra_state_attributes[ATTR_TIMES] == []

    assert time_1.clear.called
    assert time_2.clear.called
    assert time_3.clear.called


async def test_sensor_calculate_datetime(hass):
    """Test calculation of departure datetime in DeparturesSensor."""

    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    now = datetime.now()

    # Test with both estimated and planned times
    departure = Mock(spec=Departure)
    departure.estimated_time = now + timedelta(minutes=5)
    departure.planned_time = now + timedelta(minutes=10)

    assert sensor._calculate_datetime(departure) == departure.estimated_time

    # Test with only planned time
    departure.estimated_time = None

    assert sensor._calculate_datetime(departure) == departure.planned_time

    # Test with neither time
    departure.planned_time = None

    assert sensor._calculate_datetime(departure) is None


@pytest.mark.parametrize(("departure"), [(None), (1), ({"hello": "world"})])
async def test_sensor_calculate_datetime_not_valid_input(departure):
    """Test calculation of departure datetime in DeparturesSensor with invalid input."""

    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass=None,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    # Test with invalid departure input
    assert sensor._calculate_datetime(departure) is None


async def test_sensor_update_times_first_time(hass):
    """Test updating times in DeparturesSensor."""
    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    dep_1 = Mock(spec=Departure)
    dep_2 = Mock(spec=Departure)
    dep_3 = Mock(spec=Departure)

    dep_1.planned_time = datetime.now() + timedelta(minutes=5)
    dep_1.estimated_time = datetime.now() + timedelta(minutes=3)

    dep_2.planned_time = datetime.now() + timedelta(minutes=15)
    dep_2.estimated_time = None

    dep_3.planned_time = datetime.now() + timedelta(minutes=25)
    dep_3.estimated_time = datetime.now() + timedelta(minutes=20)

    await sensor.async_added_to_hass()

    sensor._update_times([dep_1, dep_2, dep_3])

    assert len(sensor._times) == 3
    assert sensor._attr_extra_state_attributes[ATTR_TIMES] == [
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[0].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[0].estimated_time,
        },
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[1].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[1].estimated_time,
        },
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[2].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[2].estimated_time,
        },
    ]


async def test_sensor_update_times_second_time(hass):
    """Test updating times in DeparturesSensor."""
    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    dep_1 = Mock(spec=Departure)
    dep_2 = Mock(spec=Departure)
    dep_3 = Mock(spec=Departure)

    dep_1.planned_time = datetime.now() + timedelta(minutes=5)
    dep_1.estimated_time = datetime.now() + timedelta(minutes=3)

    dep_2.planned_time = datetime.now() + timedelta(minutes=15)
    dep_2.estimated_time = None

    dep_3.planned_time = datetime.now() + timedelta(minutes=25)
    dep_3.estimated_time = datetime.now() + timedelta(minutes=20)

    sensor._times = [UnstableDepartureTime(dep_1)]

    await sensor.async_added_to_hass()

    assert len(sensor._times) == 1

    dep_1 = Mock(spec=Departure)
    dep_2 = Mock(spec=Departure)
    dep_3 = Mock(spec=Departure)

    dep_1.planned_time = datetime.now() + timedelta(minutes=15)
    dep_1.estimated_time = datetime.now() + timedelta(minutes=16)

    dep_2.planned_time = datetime.now() + timedelta(minutes=15)
    dep_2.estimated_time = None

    dep_3.planned_time = datetime.now() + timedelta(minutes=25)
    dep_3.estimated_time = datetime.now() + timedelta(minutes=20)

    sensor._update_times([dep_1, dep_2, dep_3])

    assert len(sensor._times) == 3
    assert sensor._attr_extra_state_attributes[ATTR_TIMES] == [
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[0].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[0].estimated_time,
        },
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[1].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[1].estimated_time,
        },
        {
            ATTR_PLANNED_DEPARTURE_TIME: sensor._times[2].planned_time,
            ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[2].estimated_time,
        },
    ]


async def test_handle_coordinator_update(hass):
    """Test handling coordinator update in DeparturesSensor."""
    line = create_mock_line()
    coordinator = create_mock_coordinator()

    sensor = DeparturesSensor(
        hass,
        coordinator=coordinator,
        line=line,
    )

    await sensor.async_added_to_hass()

    # Simulate coordinator update
    # departures = [dep_1, dep_2]
    # coordinator.data = departures

    # sensor._handle_coordinator_update()

    # assert len(sensor._times) == 2
    # assert sensor.native_value == sensor._calculate_datetime(departures[0])
    # assert sensor._attr_extra_state_attributes[ATTR_TIMES] == [
    #     {
    #         ATTR_PLANNED_DEPARTURE_TIME: sensor._times[0].planned_time,
    #         ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[0].estimated_time,
    #     },
    #     {
    #         ATTR_PLANNED_DEPARTURE_TIME: sensor._times[1].planned_time,
    #         ATTR_ESTIMATED_DEPARTURE_TIME: sensor._times[1].estimated_time,
    #     },
    # ]
