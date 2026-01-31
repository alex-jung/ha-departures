"""DataUpdateCoordinator for ha_departures integration."""

import logging
from datetime import timedelta

from aiohttp import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.data_classes import ApiCommand, Departure
from .api.motis_api import MotisApi
from .const import (
    DOMAIN,
    REQUEST_API_URL,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT,
    REQUEST_TIMES_PER_LINE_COUNT,
)

SCAN_INTERVAL = timedelta(seconds=60)
_LOGGER: logging.Logger = logging.getLogger(__name__)


class DeparturesDataUpdateCoordinator(DataUpdateCoordinator[list[Departure]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        stop_ids: list[str],
        stop_coord: tuple,
        lines: list[dict],
        hub_name: str,
        config_entry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=SCAN_INTERVAL,
        )

        _LOGGER.debug(
            "Initializing DeparturesDataUpdateCoordinator for stop_ids: %s", stop_ids
        )

        self._stop_ids: list[str] = stop_ids
        self._stop_coord: tuple = stop_coord
        self._hub_name: str = hub_name
        self._lines: list[dict] = lines
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
    def lines(self) -> list[dict]:
        """Return lines belong to this config entry."""
        return self._lines

    async def _async_update_data(self) -> list[Departure]:
        """Perform data fetching."""

        _LOGGER.debug("Updating departure data")

        try:
            self._data = await self.__fetch_data()
        except ClientResponseError as e:
            _LOGGER.error("Response error: %s", e)
            raise UpdateFailed(e) from e

        return self._data

    async def __fetch_data(self) -> list[Departure]:
        """Fetch data from endpoint."""
        COMMAND = ApiCommand.STOP_TIMES

        data: list[Departure] = []

        for stop_id in self._stop_ids:
            PARAMS = {
                "stopId": stop_id,
                "n": str(REQUEST_TIMES_PER_LINE_COUNT * len(self._lines)),
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

                if departure not in data:  # do not add duplicates
                    data.append(departure)

                    _LOGGER.debug(
                        "%s: Departure: %s (%s)",
                        stop_id,
                        departure.scheduled_departure,
                        departure.departure,
                    )

        return data
