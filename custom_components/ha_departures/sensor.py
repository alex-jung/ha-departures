"""Sensor platform for Public Transport Departures."""

from datetime import datetime
import logging

from apyefa import Departure, Line, TransportType

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DIRECTION,
    ATTR_ESTIMATED_DEPARTURE_TIME,
    ATTR_ESTIMATED_DEPARTURE_TIME_1,
    ATTR_ESTIMATED_DEPARTURE_TIME_2,
    ATTR_ESTIMATED_DEPARTURE_TIME_3,
    ATTR_ESTIMATED_DEPARTURE_TIME_4,
    ATTR_LINE_ID,
    ATTR_LINE_NAME,
    ATTR_PLANNED_DEPARTURE_TIME,
    ATTR_PLANNED_DEPARTURE_TIME_1,
    ATTR_PLANNED_DEPARTURE_TIME_2,
    ATTR_PLANNED_DEPARTURE_TIME_3,
    ATTR_PLANNED_DEPARTURE_TIME_4,
    ATTR_TRANSPORT_TYPE,
)
from .helper import UnstableDepartureTime, create_unique_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry, async_add_entities
):
    """Set up Departures entries."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            DeparturesSensor(hass, coordinator, entry_data)
            for entry_data in coordinator.lines
        ],
        update_before_add=True,
    )


class DeparturesSensor(CoordinatorEntity, SensorEntity):
    """ha_departures Sensor class."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        coordinator,
        line: Line,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._hass = hass
        self._transport = line.product
        self._line = line.name
        self._destination = line.destination
        self._value = None
        self._times = [
            UnstableDepartureTime(
                ATTR_PLANNED_DEPARTURE_TIME, ATTR_ESTIMATED_DEPARTURE_TIME
            ),
            UnstableDepartureTime(
                ATTR_PLANNED_DEPARTURE_TIME_1, ATTR_ESTIMATED_DEPARTURE_TIME_1
            ),
            UnstableDepartureTime(
                ATTR_PLANNED_DEPARTURE_TIME_2, ATTR_ESTIMATED_DEPARTURE_TIME_2
            ),
            UnstableDepartureTime(
                ATTR_PLANNED_DEPARTURE_TIME_3, ATTR_ESTIMATED_DEPARTURE_TIME_3
            ),
            UnstableDepartureTime(
                ATTR_PLANNED_DEPARTURE_TIME_4, ATTR_ESTIMATED_DEPARTURE_TIME_4
            ),
        ]

        self._attr_name = (
            f"{coordinator.stop_name} - {self._line} - {self._destination.name}"
        )
        self._attr_unique_id = create_unique_id(line)

        self._attr_extra_state_attributes = {
            ATTR_LINE_NAME: self._line,
            ATTR_TRANSPORT_TYPE: self._transport.name,
            ATTR_DIRECTION: line.destination.name,
            ATTR_LINE_ID: line.id,
            ATTR_PLANNED_DEPARTURE_TIME: None,
        }

        _LOGGER.debug('ha-departures sensor "%s" created', self.unique_id)

    @property
    def native_value(self):
        """Return value of this sensor."""
        return self._value

    @property
    def icon(self) -> str:
        """Icon of the entity, based on transport type."""
        match self._transport:
            case (
                TransportType.CITY_BUS
                | TransportType.REGIONAL_BUS
                | TransportType.EXPRESS_BUS
            ):
                return "mdi:bus"
            case TransportType.TRAM:
                return "mdi:tram"
            case TransportType.SUBWAY:
                return "mdi:subway"
            case TransportType.AST:
                return "mdi:taxi"
            case TransportType.SUBURBAN | TransportType.TRAIN | TransportType.CITY_RAIL:
                return "mdi:train"
            case _:
                return "mdi:train-bus"

    @core.callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        departures: list[Departure] = list(
            filter(
                lambda x: x.line_name == self._line
                and x.destination.id == self._destination.id,
                self.coordinator.data,
            )
        )

        if not departures:
            _LOGGER.debug("No departures found for %s", self.unique_id)
            self.clear_times()

            return

        _LOGGER.debug(
            "Sensor '%s' received %s departure(s)", self.unique_id, len(departures)
        )

        self._update_times(departures)

        self._value = (
            departures[0].estimated_time
            if departures[0].estimated_time
            else departures[0].planned_time
        )

        self.async_write_ha_state()

    def clear_times(self):
        """Clear all times."""
        for i in range(5):
            self._times[i].clear()

        self._value = None

        self._attr_extra_state_attributes.update(
            {
                ATTR_PLANNED_DEPARTURE_TIME: None,
                ATTR_ESTIMATED_DEPARTURE_TIME: None,
                ATTR_PLANNED_DEPARTURE_TIME_1: None,
                ATTR_ESTIMATED_DEPARTURE_TIME_1: None,
                ATTR_PLANNED_DEPARTURE_TIME_2: None,
                ATTR_ESTIMATED_DEPARTURE_TIME_2: None,
                ATTR_PLANNED_DEPARTURE_TIME_3: None,
                ATTR_ESTIMATED_DEPARTURE_TIME_3: None,
                ATTR_PLANNED_DEPARTURE_TIME_4: None,
                ATTR_ESTIMATED_DEPARTURE_TIME_4: None,
            }
        )

    def _update_times(self, departures: list[Departure]):
        _LOGGER.debug(
            "Updating times for %s-%s:",
            self._line,
            self.extra_state_attributes[ATTR_DIRECTION],
        )

        for i in range(5):
            planned_time = departures[i].planned_time if i < len(departures) else None
            estimated_time = (
                departures[i].estimated_time if i < len(departures) else None
            )

            _LOGGER.debug(
                "Departure %s: %s -> %s",
                i,
                planned_time,
                estimated_time,
            )

            self._times[i].update(departures[i] if i < len(departures) else None)
            self._attr_extra_state_attributes.update(self._times[i].to_dict())

    def _calculate_datetime(self, departure: Departure) -> datetime | None:
        if not departure or not isinstance(departure, Departure):
            return None

        return (
            departure.estimated_time
            if departure.estimated_time
            else departure.planned_time
        )
