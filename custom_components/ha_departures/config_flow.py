"""Adds config flow for Public Transport Departures."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError, ClientResponseError
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    LocationSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api.data_classes import ApiCommand, Line, Stop, TransportMode
from .api.motis_api import MotisApi
from .const import (
    CONF_AVAILABLE_LINES,
    CONF_ERROR_CONNECTION_FAILED,
    CONF_ERROR_INVALID_RESPONSE,
    CONF_ERROR_NO_CHANGES_OPTIONS,
    CONF_ERROR_NO_LINE_SELECTED,
    CONF_ERROR_NO_STOP_FOUND,
    CONF_HUB_NAME,
    CONF_LINES,
    CONF_LOCATION,
    CONF_STOP_COORD,
    CONF_STOP_IDS,
    CONF_STOP_NAME,
    DOMAIN,
    REQUEST_API_URL,
    VERSION,
)
from .helper import bounding_box

_LOGGER = logging.getLogger(__name__)


async def _send_api_request(api: MotisApi, command, params):
    error = CONF_ERROR_CONNECTION_FAILED

    try:
        return await api.get(command, params=params)
    except ClientResponseError as e:
        error = CONF_ERROR_INVALID_RESPONSE
        _LOGGER.error("Client response failty. Error: %s", str(e))
    except ClientError as e:
        _LOGGER.error("Client error occured. Error: %s", str(e))
        error = CONF_ERROR_CONNECTION_FAILED

    raise ValueError(error)


class DeparturesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ha_departures."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize."""
        self._url: str = ""
        self._all_stops: list[Stop] = []
        self._stop = None
        self._selected_stops: list[Stop] = []
        self._lines: list[Line] = []
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._api = MotisApi(base_url=REQUEST_API_URL)

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
            location = user_input[CONF_LOCATION]
            latitude = location["latitude"]
            longitude = location["longitude"]
            radius = location.get("radius", 1000)

            box = bounding_box(latitude, longitude, radius)

            try:
                data = await _send_api_request(
                    self._api,
                    ApiCommand.STOPS,
                    {
                        "max": f"{box[0][0]},{box[0][1]}",
                        "min": f"{box[1][0]},{box[1][1]}",
                    },
                )
            except ValueError as err:
                _errors[CONF_LOCATION] = str(err)

            if not _errors:
                self._all_stops = [Stop.from_dict(item) for item in data]
                _LOGGER.debug("%s stop(s) found", len(self._all_stops))

                self._all_stops = list(
                    filter(lambda x: x.name != "unknown", self._all_stops)
                )

                for stop in self._all_stops:
                    _LOGGER.info(
                        "> %s(%s)",
                        stop.name,
                        stop.id,
                    )

                if not self._all_stops:
                    _errors[CONF_LOCATION] = CONF_ERROR_NO_STOP_FOUND
                else:
                    return await self.async_step_stop()

        home_location = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION, default=home_location
                    ): LocationSelector(
                        config={
                            "radius": True,
                        }
                    ),
                },
            ),
            errors=_errors,
        )

    async def async_step_stop(self, user_input=None):
        """Handle step to choose a stop from the available list."""
        _errors: dict[str, str] = {}

        _LOGGER.debug(' Start "step_stop" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            self._selected_stops = list(
                filter(lambda x: x.name == user_input[CONF_STOP_NAME], self._all_stops)
            )

            _LOGGER.debug(" Selected stop(s) ".center(80, "-"))
            for stop in self._selected_stops:
                _LOGGER.debug(">> %s (%s)", stop.name, stop.id)

            self._data.update(
                {
                    CONF_STOP_IDS: [x.id for x in self._selected_stops],
                    CONF_STOP_NAME: user_input[CONF_STOP_NAME],
                    CONF_STOP_COORD: [
                        self._selected_stops[0].latitude,
                        self._selected_stops[0].longitude,
                    ],
                }
            )

            if not _errors:
                return await self.async_step_lines()

        stops = list({x.name for x in self._all_stops})

        return self.async_show_form(
            step_id="stop",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_NAME): SelectSelector(
                        SelectSelectorConfig(
                            options=stops,
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
            selected_lines: list[Line] = []

            for line in user_input.get(CONF_LINES, []):
                (routeId, directionId) = line.split("---")

                selected_lines.append(
                    next(
                        filter(
                            lambda x: x.route_id == routeId
                            and x.direction_id == directionId,
                            self._lines,
                        )
                    )
                )

            if not selected_lines:
                _errors[CONF_LINES] = CONF_ERROR_NO_LINE_SELECTED
            else:
                self._data.update(
                    {
                        CONF_AVAILABLE_LINES: [x.to_dict() for x in self._lines],
                    }
                )
                self._options.update(
                    {
                        CONF_LINES: [x.to_dict() for x in selected_lines],
                    }
                )

                return await self.async_step_hubname()

        self._lines = []

        for stop in self._selected_stops:
            _LOGGER.debug("Fetching stop times for stop: %s", stop.id)

            try:
                stop_times = await _send_api_request(
                    self._api,
                    ApiCommand.STOP_TIMES,
                    {
                        "stopId": str(stop.id),
                        "n": str(1000),
                    },
                )
            except ValueError as err:
                _errors[CONF_LOCATION] = str(err)

            data = stop_times.get("stopTimes", [])

            for stop_time in data:
                line = Line(
                    route_id=stop_time.get("routeId"),
                    direction_id=stop_time.get("directionId"),
                    head_sign=stop_time.get("headsign"),
                    route_short_name=stop_time.get("routeShortName"),
                    mode=TransportMode(stop_time.get("mode")),
                )

                _LOGGER.debug(
                    "Found line: [%s-%s] %s (%s)",
                    line.mode,
                    line.head_sign,
                    line.route_short_name,
                    line.direction_id,
                )

                self._lines.append(line)

        self._lines = list(set(self._lines))  # remove duplicate lines

        line_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=f"{line.mode.capitalize()} {line.route_short_name} - {line.head_sign}",
                value=f"{line.route_id}---{line.direction_id}",
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

        stop_name = self._data.get(CONF_STOP_NAME, "")

        if user_input is not None:
            await self.async_set_unique_id(user_input.get(CONF_HUB_NAME, stop_name))
            self._abort_if_unique_id_configured()

            self._data.update({CONF_HUB_NAME: user_input[CONF_HUB_NAME]})

            return self.async_create_entry(
                title=user_input[CONF_HUB_NAME],
                data=self._data,
                options=self._options,
            )

        return self.async_show_form(
            step_id="hubname",
            data_schema=vol.Schema(
                {vol.Required(CONF_HUB_NAME, default=stop_name): cv.string}
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

        self._lines_selected: list[Line] = [
            Line.from_dict(x) for x in config_entry.options.get(CONF_LINES, [])
        ]
        self._lines_available: list[Line] = [
            Line.from_dict(x) for x in config_entry.data.get(CONF_AVAILABLE_LINES, [])
        ]

        _LOGGER.debug("Start configuration")

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""

        _LOGGER.debug(' Start "step_init" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            lines_user_choose = user_input.get(CONF_LINES, [])

            lines_new_state: list[Line] = []

            for user_option in lines_user_choose:
                (route_id, direction_id) = user_option.split("---")

                lines_new_state.append(
                    next(
                        filter(
                            lambda x: x.route_id == route_id
                            and x.direction_id == direction_id,
                            self._lines_available,
                        )
                    )
                )

            if lines_new_state == self._lines_selected:
                _LOGGER.debug("No changes on entry configuration detected")
                return self.async_abort(reason=CONF_ERROR_NO_CHANGES_OPTIONS)

            return self.async_create_entry(
                title="",
                data={
                    CONF_LINES: [x.to_dict() for x in lines_new_state],
                },
            )

        options_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=f"{line.route_short_name} - {line.head_sign}",
                value=f"{line.route_id}---{line.direction_id}",
            )
            for line in self._lines_available
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "lines",
                        default=[
                            f"{x.route_id}---{x.direction_id}"
                            for x in self._lines_selected
                        ],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options_list,
                            multiple=True,
                            sort=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    )
                }
            ),
        )
