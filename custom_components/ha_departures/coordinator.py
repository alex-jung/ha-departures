"""DataUpdateCoordinator for ha_departures integration."""

import logging
from datetime import timedelta

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.data_classes import ApiCommand, Departure
from .api.motis_api import MotisApi
from .const import (
    CONF_LINES,
    CONF_STOP_COORD,
    CONF_STOP_IDS,
    DOMAIN,
    RADIUS_FOR_STOPS_REQUEST,
    REQUEST_API_URL,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT,
    REQUEST_TIMES_PER_LINE_COUNT,
    UPDATE_INTERVAL,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DeparturesDataUpdateCoordinator(DataUpdateCoordinator[list[Departure]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

        _LOGGER.debug("Initializing DeparturesDataUpdateCoordinator")

        self._stop_ids: list[str] = config_entry.data.get(CONF_STOP_IDS, [])
        self._stop_coord: tuple = config_entry.data.get(CONF_STOP_COORD, ())
        self._hub_name: str = config_entry.title
        self._lines_count: int = len(config_entry.options.get(CONF_LINES, []))
        self._data: list[Departure] = []

        self._client = MotisApi(REQUEST_API_URL)

    @property
    def stop_coord(self) -> tuple:
        """Return config entry stop coordinates."""
        return self._stop_coord

    @property
    def stop_ids(self) -> list[str]:
        """Return config entry stop IDs."""
        return self._stop_ids

    @property
    def hub_name(self) -> str:
        """Return config entry hub name."""
        return self._hub_name

    @property
    def lines(self) -> int:
        """Return count of lines belong to this config entry."""
        return self._lines_count

    @lines.setter
    def lines(self, new_count: int):
        """Set count of lines belong to this config enttry."""
        self._lines_count = new_count

    async def _async_update_data(self) -> list[Departure]:
        """Perform data fetching."""

        _LOGGER.debug("Updating departure data")

        try:
            self._data = await self.__fetch_data()
        except ClientResponseError as e:
            _LOGGER.info("Error fetching data from API. Error: %s", e)
            raise UpdateFailed(e) from e

        return self._data

    async def __fetch_data(self) -> list[Departure]:
        """Fetch data from endpoint."""
        COMMAND = ApiCommand.STOP_TIMES

        data: list[Departure] = []

        # Take only first stop_id and use "radius" parameter
        # to decrease amount of requests to the server
        stop_id = self._stop_ids[0]

        PARAMS = {
            "stopId": stop_id,
            "n": str(REQUEST_TIMES_PER_LINE_COUNT * self.lines),
            "radius": str(RADIUS_FOR_STOPS_REQUEST),
        }

        _LOGGER.debug(
            "Fetching stop times for stop_id: %s with params: %s", stop_id, PARAMS
        )

        times = await self._client.get(
            COMMAND, params=PARAMS, retry=REQUEST_RETRIES, timeout=REQUEST_TIMEOUT
        )

        _LOGGER.debug(
            "Received %s stop times for stop_id: %s",
            len(times.get("stopTimes", [])),
            stop_id,
        )

        for stop_time in times.get("stopTimes", []):
            departure = Departure.from_dict(stop_time)

            if departure not in data and departure.stop_id in self.stop_ids:
                data.append(departure)

                _LOGGER.debug(
                    "%s: Departure: %s (%s)",
                    stop_id,
                    departure.scheduled_departure,
                    departure.departure,
                )

        return data
