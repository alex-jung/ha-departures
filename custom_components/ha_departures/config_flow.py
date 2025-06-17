"""Adds config flow for Public Transport Departures."""

import logging
from copy import deepcopy

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from aiohttp import ConnectionTimeoutError
from apyefa import EfaClient, Line, LineRequestType, Location, LocationFilter
from apyefa.exceptions import EfaConnectionError, EfaResponseInvalid
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_API_URL,
    CONF_ENDPOINT,
    CONF_ERROR_CONNECTION_FAILED,
    CONF_ERROR_INVALID_RESPONSE,
    CONF_ERROR_NO_CHANGES_OPTIONS,
    CONF_ERROR_NO_STOP_FOUND,
    CONF_HUB_NAME,
    CONF_LINES,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    DOMAIN,
    EFA_ENDPOINTS,
)
from .helper import create_unique_id, get_unique_lines

_LOGGER = logging.getLogger(__name__)


class DeparturesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ha_departures."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self._url: str = ""
        self._all_stops: list[Location] = []
        self._stop: Location | None = None
        self._lines: list[Line] = []
        self._data: dict[str, str] = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        _errors: dict[str, str] = {}

        _LOGGER.debug("Start step_user: %s", user_input)

        if user_input is not None:
            self._url = user_input[CONF_ENDPOINT]

            try:
                async with EfaClient(self._url) as client:
                    self._all_stops = await client.locations_by_name(
                        user_input[CONF_STOP_NAME], filters=[LocationFilter.STOPS]
                    )
            except (EfaConnectionError, ConnectionTimeoutError) as err:
                _errors[CONF_ERROR_CONNECTION_FAILED] = CONF_ERROR_CONNECTION_FAILED
                _LOGGER.error('Failed to connect EFA api "%s"', self._url, exc_info=err)
            except EfaResponseInvalid as err:
                _errors[CONF_ERROR_INVALID_RESPONSE] = CONF_ERROR_INVALID_RESPONSE
                _LOGGER.error("Received invalid response from api", exc_info=err)

            if not _errors:
                _LOGGER.debug(
                    "%s stop(s) found for %s",
                    len(self._all_stops),
                    user_input[CONF_STOP_NAME],
                )

                if not self._all_stops:
                    _errors[CONF_ERROR_NO_STOP_FOUND] = CONF_ERROR_NO_STOP_FOUND
                else:
                    return await self.async_step_stop()

        endpoints = [
            SelectOptionDict(label=name, value=url)
            for name, url in EFA_ENDPOINTS.items()
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENDPOINT): SelectSelector(
                        SelectSelectorConfig(
                            options=endpoints,
                            multiple=False,
                            sort=False,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_STOP_NAME): str,
                }
            ),
            errors=_errors,
        )

    async def async_step_stop(self, user_input=None):
        """Handle step to choose a stop from the available list."""
        _errors: dict[str, str] = {}

        _LOGGER.debug("Start step_stop: %s", user_input)

        if user_input is not None:
            self._stop = next(
                filter(lambda x: x.id == user_input[CONF_STOP_NAME], self._all_stops)
            )

            if not self._stop:
                _LOGGER.error("No stop found")
                return self.async_abort(reason="No stop found")

            if not _errors:
                return await self.async_step_lines()

        options: list[SelectOptionDict] = [
            SelectOptionDict(
                label=stop.name,
                value=stop.id,
            )
            for stop in self._all_stops
        ]

        return self.async_show_form(
            step_id="stop",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_NAME): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            multiple=False,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    )
                }
            ),
            errors=_errors,
        )

    async def async_step_lines(self, user_input=None):
        """Handle step to choose needed lines."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            connections: list[Line] = get_unique_lines(self._lines)

            # filter connections by user input
            connections = list(
                filter(lambda x: x.id in user_input[CONF_LINES], connections)
            )

            self._data = {
                CONF_API_URL: self._url,
                CONF_STOP_ID: self._stop.id,
                CONF_STOP_NAME: self._stop.name,
                CONF_LINES: [x.to_dict() for x in connections],
            }

            return await self.async_step_hubname()

        # load all lines for choosen stop location
        self._lines = []

        async with EfaClient(self._url) as client:
            self._lines = await client.lines_by_location(
                self._stop.id, req_types=[LineRequestType.DEPARTURE_MONITOR]
            )

        _directions: dict = {
            x.id: f"{x.name} - {x.destination.name}" for x in self._lines
        }

        return self.async_show_form(
            step_id="lines",
            data_schema=vol.Schema(
                {vol.Required(CONF_LINES): cv.multi_select(_directions)}
            ),
            errors=_errors,
        )

    async def async_step_hubname(self, user_input=None):
        """Handle step to define a hub name."""
        if user_input is not None:
            await self.async_set_unique_id(
                user_input.get(CONF_HUB_NAME, self._stop.name)
            )
            self._abort_if_unique_id_configured()

            self._data.update({CONF_HUB_NAME: user_input[CONF_HUB_NAME]})

            return self.async_create_entry(
                title=user_input[CONF_HUB_NAME],
                data=self._data,
            )

        return self.async_show_form(
            step_id="hubname",
            data_schema=vol.Schema(
                {vol.Required(CONF_HUB_NAME, default=self._stop.name): cv.string}
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return DeparturesOptionsFlowHandler(config_entry)


class DeparturesOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options handler for ha-departures."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._connections_selected: list[Line] = [
            Line.from_dict(x) for x in config_entry.data.get(CONF_LINES, [])
        ]
        self._connections: dict[str, Line] = []
        self._stop_name: str = config_entry.data.get(CONF_STOP_NAME)
        self._stop_id: str = config_entry.data.get(CONF_STOP_ID)
        self._url: str = config_entry.data.get(CONF_API_URL)
        self._hub_name: str = config_entry.data.get(CONF_HUB_NAME)

        _LOGGER.debug("Start configuration")

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            new_selected_ids = user_input[CONF_LINES]
            old_selected_ids = [x.id for x in self._connections_selected]

            removed_connections = list(
                filter(lambda x: x not in new_selected_ids, old_selected_ids)
            )
            added_connections = list(
                filter(
                    lambda x: x not in old_selected_ids,
                    new_selected_ids,
                )
            )

            # convert list of IDs to list of Lines
            removed_connections: list[Line] = [
                self._connections.get(x) for x in removed_connections
            ]
            added_connections: list[Line] = [
                self._connections.get(x) for x in added_connections
            ]

            _LOGGER.debug("Removed: %s", removed_connections)
            _LOGGER.debug("Added: %s", added_connections)

            if not removed_connections and not added_connections:
                _LOGGER.debug("No changes on entry configuration detected")
                return self.async_abort(reason=CONF_ERROR_NO_CHANGES_OPTIONS)

            updated_config = deepcopy(self.config_entry.data[CONF_LINES])

            entity_registry = er.async_get(self.hass)
            entries = er.async_entries_for_config_entry(
                entity_registry, self.config_entry.entry_id
            )

            connections_map = {e.unique_id: e.entity_id for e in entries}

            # remove connection(s)
            for line_id in removed_connections:
                uid = create_unique_id(line_id, self._hub_name)

                _LOGGER.debug("Remove connection with uid:%s", uid)

                entity_to_remove = connections_map.get(uid)

                if not entity_to_remove:
                    _LOGGER.error("Entity to remove %s not found in map", uid)
                else:
                    entity_registry.async_remove(connections_map[uid])

                updated_config = list(
                    filter(
                        lambda x: create_unique_id(x, self._hub_name) != uid,
                        updated_config,
                    )
                )

            # add new connection(s)
            for connection in added_connections:
                updated_config.append(connection.to_dict())

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_LINES: updated_config,
                },
            )

            return self.async_create_entry(data=self.config_entry.data)

        all_lines: list[Line] = []

        async with EfaClient(self._url) as client:
            all_lines = await client.lines_by_location(
                self._stop_id, req_types=[LineRequestType.DEPARTURE_MONITOR]
            )

        self._connections = {x.id: x for x in get_unique_lines(all_lines)}

        connections_dict: dict = {
            x.id: f"{x.name} - {x.destination.name}" for x in self._connections.values()
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "lines", default=[x.id for x in self._connections_selected]
                    ): cv.multi_select(connections_dict),
                }
            ),
        )
