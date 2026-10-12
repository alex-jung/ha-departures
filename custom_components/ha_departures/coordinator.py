"""DataUpdateCoordinator for ha_departures integration."""

import logging
from datetime import timedelta

from aiohttp import ClientError, ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

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
    STALE_DATA_TIMEOUT,
    UPDATE_INTERVAL,
)
from .helper import stop_id_matches, unique_stop_ids

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DeparturesDataUpdateCoordinator(TimestampDataUpdateCoordinator[list[Departure]]):
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
        self._query_stop_id: str | None = None

        self._client = MotisApi(REQUEST_API_URL, async_get_clientsession(hass))

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
    def data_age(self) -> timedelta | None:
        """Return the time elapsed since the last successful update."""
        if self.last_update_success_time is None:
            return None

        return dt_util.utcnow() - self.last_update_success_time

    @property
    def has_valid_data(self) -> bool:
        """Return True if the cached data is recent enough to be used."""
        age = self.data_age

        return age is not None and age < timedelta(seconds=STALE_DATA_TIMEOUT)

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
            return await self._fetch_data()
        except (ClientError, TimeoutError) as e:
            _LOGGER.debug("Error fetching data from API. Error: %s", e)
            raise UpdateFailed(f"API request failed: {e}") from e
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            _LOGGER.debug("Unexpected API response. Error: %s", e)
            raise UpdateFailed(f"Unexpected API response: {e}") from e

    async def _fetch_data(self) -> list[Departure]:
        """Fetch data from endpoint."""
        COMMAND = ApiCommand.STOP_TIMES

        # Take only one stop_id and use "radius" parameter
        # to decrease amount of requests to the server. If the API does not
        # know a stop ID (anymore), the next one is tried.
        stop_ids = unique_stop_ids(self._stop_ids)

        if self._query_stop_id in stop_ids:
            stop_ids.remove(self._query_stop_id)
            stop_ids.insert(0, self._query_stop_id)

        times: dict = {}

        for index, stop_id in enumerate(stop_ids):
            PARAMS = {
                "stopId": stop_id,
                "n": str(REQUEST_TIMES_PER_LINE_COUNT * self.lines),
                "radius": str(RADIUS_FOR_STOPS_REQUEST),
            }

            _LOGGER.debug(
                "Fetching stop times for stop_id: %s with params: %s", stop_id, PARAMS
            )

            try:
                times = await self._client.get(
                    COMMAND,
                    params=PARAMS,
                    retry=REQUEST_RETRIES,
                    timeout=REQUEST_TIMEOUT,
                )
            except ClientResponseError as e:
                if e.status != 404 or index == len(stop_ids) - 1:
                    raise

                _LOGGER.warning(
                    "Hub '%s': the API does not know stop ID %s (HTTP 404), "
                    "trying the next one",
                    self._hub_name,
                    stop_id,
                )
                continue

            self._query_stop_id = stop_id

            _LOGGER.debug(
                "Received %s stop times for stop_id: %s",
                len(times.get("stopTimes", [])),
                stop_id,
            )
            break

        return await self.hass.async_add_executor_job(self._process_data, times)

    def _process_data(self, api_response: dict) -> list[Departure]:
        """Process data in a separate thread to avoid blocking the event loop."""
        departures = []
        seen: set[Departure] = set()

        for stop_time in api_response.get("stopTimes", []):
            departure = Departure.from_dict(stop_time)

            if departure not in seen and stop_id_matches(
                departure.stop_id, self.stop_ids
            ):
                seen.add(departure)
                departures.append(departure)

        return departures
