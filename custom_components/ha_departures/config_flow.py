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
    VERSION,
)
from .helper import create_unique_id, get_unique_lines, line_hash

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

        _LOGGER.debug(" Start CONFIGURATION flow ".center(60, "="))
        _LOGGER.debug(">> ha-departures version: %s", VERSION)
        _LOGGER.debug(
            ">> config flow version %s.%s",
            DeparturesFlowHandler.VERSION,
            DeparturesFlowHandler.MINOR_VERSION,
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        _errors: dict[str, str] = {}

        _LOGGER.debug(' Start "step_user" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

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
                    '%s stop(s) found for "%s":',
                    len(self._all_stops),
                    user_input[CONF_STOP_NAME],
                )

                for stop in self._all_stops:
                    _LOGGER.debug(
                        "> %s(%s)",
                        stop.name,
                        stop.id,
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

        _LOGGER.debug(' Start "step_stop" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            self._stop = next(
                filter(lambda x: x.id == user_input[CONF_STOP_NAME], self._all_stops)
            )

            if not self._stop:
                _LOGGER.error("No stop found")
                return self.async_abort(reason="No stop found")

            _LOGGER.debug(
                "Selected stop: %s(%s)",
                self._stop.name,
                self._stop.id,
            )

            if not _errors:
                return await self.async_step_lines()

        stop_list: list[SelectOptionDict] = [
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
                            options=stop_list,
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

        _LOGGER.debug(' Start "step_lines" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            # filter connections by user input
            connections = list(
                filter(
                    lambda x: line_hash(x) in user_input[CONF_LINES],
                    self._lines,
                )
            )

            for line in connections:
                _LOGGER.debug(
                    "Selected line: %s(%s) -> %s(%s)",
                    line.name,
                    line.id,
                    line.destination.name,
                    line.destination.id,
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

        self._lines = get_unique_lines(self._lines)

        _LOGGER.debug("Step lines: %s unique line(s) found:", len(self._lines))

        for line in self._lines:
            _LOGGER.debug(
                "> %s(%s) --> %s(%s)",
                line.name,
                line.id,
                line.destination.name,
                line.destination.id,
            )

        line_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=f"{line.name} - {line.destination.name}",
                value=line_hash(line),
            )
            for line in self._lines
        ]

        return self.async_show_form(
            step_id="lines",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LINES): SelectSelector(
                        SelectSelectorConfig(
                            options=line_list,
                            multiple=True,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    )
                }
            ),
            errors=_errors,
        )

    async def async_step_hubname(self, user_input=None):
        """Handle step to define a hub name."""

        _LOGGER.debug(' Start "step_hubname" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

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

        _LOGGER.debug(" Start OPTIONS flow ".center(60, "="))
        _LOGGER.debug(">> ha-departures version: %s", VERSION)
        _LOGGER.debug(
            ">> config flow version %s.%s",
            DeparturesFlowHandler.VERSION,
            DeparturesFlowHandler.MINOR_VERSION,
        )
        _LOGGER.debug(
            ">> config entry: %s(uid=%s)", config_entry.title, config_entry.unique_id
        )

        self._connections_selected: list[Line] = [
            Line.from_dict(x) for x in config_entry.data.get(CONF_LINES, [])
        ]
        self._connections: list[Line] = []
        self._stop_name: str = config_entry.data.get(CONF_STOP_NAME)
        self._stop_id: str = config_entry.data.get(CONF_STOP_ID)
        self._url: str = config_entry.data.get(CONF_API_URL)
        self._hub_name: str = config_entry.data.get(CONF_HUB_NAME)

        _LOGGER.debug("Start configuration")

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""

        _LOGGER.debug(' Start "step_init" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            lines_new = user_input.get(CONF_LINES, [])
            lines_old = [line_hash(x) for x in self._connections_selected]

            # hash values of removed and added lines
            lines_hash_removed = list(filter(lambda x: x not in lines_new, lines_old))
            lines_hash_added = list(filter(lambda x: x not in lines_old, lines_new))

            # convert lists of hashes to list of Line objects
            removed_connections: list[Line] = list(
                filter(
                    lambda x: line_hash(x) in lines_hash_removed,
                    self._connections_selected,
                )
            )
            added_connections: list[Line] = list(
                filter(
                    lambda x: line_hash(x) in lines_hash_added,
                    self._connections,
                )
            )

            _LOGGER.debug(" Connections removed ".center(60, "="))
            for line in removed_connections:
                _LOGGER.debug(
                    ">> %s(%s) -> %s(%s)",
                    line.name,
                    line.id,
                    line.destination.name,
                    line.destination.id,
                )

            _LOGGER.debug(" Connections added ".center(60, "="))
            for line in added_connections:
                _LOGGER.debug(
                    ">> %s(%s) -> %s(%s)",
                    line.name,
                    line.id,
                    line.destination.name,
                    line.destination.id,
                )

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
                uid = create_unique_id(line_id)

                _LOGGER.debug('Remove connection "%s"', uid)

                entity_to_remove = connections_map.get(uid)

                if not entity_to_remove:
                    _LOGGER.error('Entity to remove "%s" not found in map', uid)
                else:
                    entity_registry.async_remove(connections_map[uid])

                updated_config = list(
                    filter(
                        lambda x: create_unique_id(x) != uid,
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

        self._connections: list[Line] = []

        async with EfaClient(self._url) as client:
            self._connections = await client.lines_by_location(
                self._stop_id, req_types=[LineRequestType.DEPARTURE_MONITOR]
            )

        line_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=f"{line.name} - {line.destination.name}",
                value=line_hash(line),
            )
            for line in get_unique_lines(self._connections)
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "lines",
                        default=[line_hash(x) for x in self._connections_selected],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=line_list,
                            multiple=True,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    )
                }
            ),
        )
