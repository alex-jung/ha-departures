"""Sensor platform for Public Transport Departures."""

from datetime import datetime, timedelta
import logging

from apyefa import Departure, Line, TransportType

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DIRECTION, ATTR_LINE_ID, ATTR_LINE_NAME, ATTR_TRANSPORT_TYPE
from .helper import create_unique_id

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
        self._planned_departure_time: datetime | None = None
        self._delay: timedelta | None = None
        self._occupancy_level: str | None = None
        self._value = None

        self._attr_name = (
            f"{coordinator.stop_name} - {self._line} - {self._destination.name}"
        )
        self._attr_unique_id = create_unique_id(line)

        self._attr_extra_state_attributes = {
            ATTR_LINE_NAME: self._line,
            ATTR_TRANSPORT_TYPE: self._transport.name,
            ATTR_DIRECTION: line.destination.name,
            ATTR_LINE_ID: line.id,
            # ATTR_OCCUPANCY_LEVEL: self._occupancy_level,
            # ATTR_PLANNED_DEPARTURE_TIME: self._planned_departure_time,
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
            case TransportType.BUS | TransportType.RBUS | TransportType.EXPRESS_BUS:
                return "mdi:bus"
            case TransportType.TRAM:
                return "mdi:tram"
            case TransportType.SUBWAY:
                return "mdi:subway"
            case TransportType.AST:
                return "mdi:taxi"
            case TransportType.SUBURBAN | TransportType.RAIL | TransportType.CITY_RAIL:
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
            return

        self._value = departures[0].estimated_time or departures[0].planned_time

        self.async_write_ha_state()
