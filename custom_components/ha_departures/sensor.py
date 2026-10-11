"""Sensor platform for Public Transport Departures."""

import logging
from datetime import datetime, timedelta

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from slugify import slugify

from .api.data_classes import Departure, Line, TransportMode
from .const import (
    ATTR_DEPARTURE_ALERTS,
    ATTR_DEPARTURE_CANCELLED,
    ATTR_DIRECTION,
    ATTR_ESTIMATED_DEPARTURE_TIME,
    ATTR_HEAD_SIGN,
    ATTR_LINE_ID,
    ATTR_LINE_NAME,
    ATTR_PLANNED_DEPARTURE_TIME,
    ATTR_PROVIDER_URL,
    ATTR_SCHEDULED_TRACK,
    ATTR_TIMES,
    ATTR_TRACK,
    ATTR_TRANSPORT_TYPE,
    ATTR_TRIP_ID,
    CONF_LINES,
    DEPARTURES_PER_SENSOR_LIMIT,
    PROVIDER_URL,
    SENSOR_REFRESH_INTERVAL,
)
from .coordinator import DeparturesDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry, async_add_entities
):
    """Set up Departures entries."""
    coordinator: DeparturesDataUpdateCoordinator = entry.runtime_data.coordinator

    async_add_entities(
        [
            DeparturesSensor(
                hass,
                coordinator,
                line,
            )
            for line in entry.options.get(CONF_LINES, [])
        ],
        update_before_add=True,
    )


class DeparturesSensor(
    CoordinatorEntity[DeparturesDataUpdateCoordinator], SensorEntity
):
    """ha_departures Sensor class."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        coordinator: DeparturesDataUpdateCoordinator,
        line: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        _LOGGER.info("Create sensor instance for line: %s", line)

        self._hass = hass

        line_obj = Line.from_dict(line)

        self._transport = line_obj.mode
        self._route_name = line_obj.route_short_name
        self._route_id = line_obj.route_id
        self._destination = line_obj.head_sign
        self._direction_id = line_obj.direction_id

        self._times = []
        self._value = None
        self._trip_info = {}

        self._attr_name = (
            f"{coordinator.hub_name}-{self._route_name}-{self._destination}"
        )
        self._attr_unique_id = f"{slugify(coordinator.hub_name)}-{self._route_id}-{self._direction_id}-{slugify(self._destination)}"

        self._attr_extra_state_attributes = {
            ATTR_LINE_NAME: self._route_name,
            ATTR_LINE_ID: self._route_id,
            ATTR_TRANSPORT_TYPE: self._transport.value,
            ATTR_DIRECTION: line_obj.head_sign,
            ATTR_PROVIDER_URL: PROVIDER_URL,
            ATTR_LATITUDE: (
                coordinator.stop_coord[0] if coordinator.stop_coord else None
            ),
            ATTR_LONGITUDE: (
                coordinator.stop_coord[1] if coordinator.stop_coord else None
            ),
            ATTR_TIMES: self._times,
        }

        _LOGGER.debug('ha-departures sensor "%s" created', self.unique_id)
        _LOGGER.debug(">> Transport type: %s", self._transport)
        _LOGGER.debug(">> Route name: %s", self._route_name)
        _LOGGER.debug(">> Route ID: %s", self._route_id)
        _LOGGER.debug(">> Destination: %s", self._destination)
        _LOGGER.debug(">> Direction ID: %s", self._direction_id)
        _LOGGER.debug(">> Stop IDs: %s", coordinator.stop_ids)

    async def async_added_to_hass(self) -> None:
        """Re-evaluate cached data periodically, independent of API updates."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_refresh_from_cache,
                timedelta(seconds=SENSOR_REFRESH_INTERVAL),
            )
        )

    @core.callback
    def _async_refresh_from_cache(self, _now: datetime) -> None:
        """Drop departed entries and update availability from cached data."""
        self._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return True while the last successful update is recent enough.

        Short API outages are bridged with cached data instead of turning
        the sensor unavailable on the first failed request.
        """
        return self.coordinator.has_valid_data

    @property
    def native_value(self):
        """Return value of this sensor."""
        return self._value

    @property
    def icon(self) -> str:
        """Icon of the entity, based on transport type."""
        match self._transport:
            case TransportMode.BIKE:
                return "mdi:bike"
            case TransportMode.RENTAL:
                return "mdi:car-key"
            case TransportMode.CAR:
                return "mdi:car"
            case TransportMode.FLEX:
                return "mdi:bus-clock"
            case TransportMode.TRANSIT:
                return "mdi:bus-transfer"
            case TransportMode.FERRY:
                return "mdi:ferry"
            case TransportMode.AIRPLANE:
                return "mdi:airplane"
            case (
                TransportMode.RAIL
                | TransportMode.HIGHSPEED_RAIL
                | TransportMode.LONG_DISTANCE
                | TransportMode.NIGHT_RAIL
                | TransportMode.REGIONAL_FAST_RAIL
                | TransportMode.REGIONAL_RAIL
                | TransportMode.SUBURBAN
            ):
                return "mdi:train"
            case TransportMode.BUS:
                return "mdi:bus"
            case TransportMode.TRAM:
                return "mdi:tram"
            case TransportMode.SUBWAY | TransportMode.METRO:
                return "mdi:subway"
            case _:
                return "mdi:train-bus"

    @core.callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        debug_title = f" Update '{self._route_name}' -> '{self._destination}' "

        _LOGGER.debug(debug_title.center(70, "="))
        _LOGGER.debug(">> Unique ID: %s", self.unique_id)
        _LOGGER.debug(">> Route ID: %s", self._route_id)
        _LOGGER.debug(">> Direction ID: %s", self._direction_id)

        now = dt_util.now()

        departures = list(
            filter(
                lambda d: (
                    d.route_id.endswith(self._route_id)
                    and d.direction_id == self._direction_id
                    and _is_upcoming(d, now)
                ),
                self.coordinator.data or [],
            )
        )

        _LOGGER.debug("> Departures found: %s", len(departures))

        if not departures:
            self._attr_extra_state_attributes.update({ATTR_TIMES: []})
            self._value = None
            self.async_write_ha_state()

            return

        departures = departures[:DEPARTURES_PER_SENSOR_LIMIT]

        for departure in departures:
            _LOGGER.debug(
                "> Departure: Planned: %s | Estimated: %s",
                departure.scheduled_departure,
                departure.departure,
            )

        self._attr_extra_state_attributes.update(
            {
                ATTR_TIMES: [
                    {
                        ATTR_PLANNED_DEPARTURE_TIME: d.scheduled_departure,
                        ATTR_ESTIMATED_DEPARTURE_TIME: d.departure,
                        ATTR_TRIP_ID: d.trip_id,
                        ATTR_DEPARTURE_CANCELLED: d.cancelled,
                        ATTR_HEAD_SIGN: d.head_sign,
                        ATTR_DEPARTURE_ALERTS: d.alerts,
                        ATTR_SCHEDULED_TRACK: d.scheduled_track,
                        ATTR_TRACK: d.track,
                    }
                    for d in departures
                ],
            }
        )

        self._value = departures[0].scheduled_departure

        self.async_write_ha_state()

        _LOGGER.debug("<< Sensor updated")


def _is_upcoming(departure: Departure, now: datetime) -> bool:
    """Return True if the departure (real-time, else scheduled) is still ahead."""
    departure_time = departure.departure or departure.scheduled_departure

    return departure_time is not None and departure_time > now
