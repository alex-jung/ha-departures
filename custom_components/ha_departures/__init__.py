"""Custom integration to integrate Public Transport Departures with Home Assistant.

For more details about this integration, please refer to
https://github.com/alex-jung/ha-departures
"""

import logging
from datetime import timedelta

from apyefa import Departure, EfaClient, Line
from apyefa.exceptions import EfaConnectionError, EfaResponseInvalid
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_URL,
    CONF_HUB_NAME,
    CONF_LINES,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    DOMAIN,
    STARTUP_MESSAGE,
)

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER: logging.Logger = logging.getLogger(__package__)

PLATFORMS = [Platform.SENSOR]


class DeparturesDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        stop_id: str,
        stop_name: str,
        lines: list[dict],
        hub_name: str,
    ) -> None:
        """Initialize."""
        self._url: str = url
        self._stop_id: str = stop_id
        self._stop_name: str = stop_name
        self._hub_name: str = hub_name
        self._lines = [Line.from_dict(x) for x in lines]
        self._data = list[Departure]

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    @property
    def stop_name(self):
        """Return config entry stop name."""
        return self._stop_name

    @property
    def stop_id(self):
        """Return config entry stop ID."""
        return self._stop_id

    @property
    def hub_name(self):
        """Return config entry hub name."""
        return self._hub_name

    @property
    def lines(self):
        """Return lines/sensors belong to this config entry."""
        return self._lines

    @property
    def api_url(self):
        """Return Provider API URL."""
        return self._url

    async def _async_update_data(self):
        """Fetch data from endpoint."""

        now_time = dt_util.now().strftime("%H:%M")

        async with EfaClient(self._url) as client:
            try:
                self._data = await client.departures_by_location(
                    self._stop_id, arg_date=now_time, realtime=True
                )
            except EfaConnectionError as err:
                _LOGGER.error("Connection to EFA client failed")
                raise UpdateFailed(err) from err
            except EfaResponseInvalid as err:
                _LOGGER.error("EFA response invalid")
                raise UpdateFailed(err) from err

        return self._data


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    url: str = entry.data.get(CONF_API_URL)
    stop_id: str = entry.data.get(CONF_STOP_ID)
    stop_name: str = entry.data.get(CONF_STOP_NAME)
    lines: list[dict] = entry.data.get(CONF_LINES)
    hub_name: str = entry.data.get(CONF_HUB_NAME)

    coordinator = DeparturesDataUpdateCoordinator(
        hass, url, stop_id, stop_name, lines, hub_name
    )

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ha-departures config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 1:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        new_data = {**config_entry.data}

        # Migrate from minor version 1 to 2
        if config_entry.minor_version < 2:
            new_data.update({CONF_HUB_NAME: config_entry.data.get(CONF_STOP_NAME)})

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=2, version=1
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True
