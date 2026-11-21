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
from .helper import (
    bounding_box,
    normalize_stop_id,
    route_id_matches,
    vehicle_class,
)

_LOGGER = logging.getLogger(__name__)


async def _send_api_request(api: MotisApi, command, params):
    error = CONF_ERROR_CONNECTION_FAILED

    try:
        return await api.get(command, params=params)
    except ClientResponseError as e:
        error = CONF_ERROR_INVALID_RESPONSE
        _LOGGER.error("Client response failty. Error: %s", str(e))
    except (ClientError, TimeoutError) as e:
        _LOGGER.error("Client error occured. Error: %s", str(e))
        error = CONF_ERROR_CONNECTION_FAILED

    raise ValueError(error)


def _extract_lines_from_stop_times(
    stop_times_data: dict[str, Any], unique: bool = True
) -> list[Line]:
    """Extract unique lines from stop times data."""
    lines: list[Line] = []

    for stop_time in stop_times_data.get("stopTimes", []):
        line = Line(
            route_id=stop_time.get("routeId"),
            direction_id=stop_time.get("directionId"),
            head_sign=stop_time.get("headsign"),
            route_short_name=stop_time.get("routeShortName"),
            mode=TransportMode(stop_time.get("mode")),
            route_type=stop_time.get("routeType"),
        )

        lines.append(line)

    return list(set(lines)) if unique else lines


def _sorted_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return lines in a stable order, so lists can be compared by content."""
    return sorted(
        lines,
        key=lambda x: (
            str(x.get("route_id")),
            str(x.get("direction_id")),
            str(x.get("head_sign")),
        ),
    )


# Symbol per vehicle class (from the GTFS route type, see helper.vehicle_class)
_CLASS_SYMBOL: dict[str, str] = {
    "high_speed": "🚄",
    "long_distance": "🚄",
    "night": "🚆",
    "regional": "🚆",
    "suburban": "🚆",
    "subway": "🚇",
    "tram": "🚊",
    "bus": "🚌",
    "coach": "🚌",
    "on_demand": "🚐",
    "ride_sharing": "🚗",
    "ship": "⛴️",
    "aerial_lift": "🚡",
    "funicular": "🚞",
    "air": "✈️",
}

# Fallback per transport mode, if the API reports no known route type
_MODE_SYMBOL: dict[TransportMode, str] = {
    TransportMode.HIGHSPEED_RAIL: "🚄",
    TransportMode.LONG_DISTANCE: "🚄",
    TransportMode.RAIL: "🚆",
    TransportMode.NIGHT_RAIL: "🚆",
    TransportMode.REGIONAL_FAST_RAIL: "🚆",
    TransportMode.REGIONAL_RAIL: "🚆",
    TransportMode.SUBURBAN: "🚆",
    TransportMode.SUBWAY: "🚇",
    # MOTIS API < v5 name of SUBURBAN
    TransportMode.METRO: "🚆",
    TransportMode.TRAM: "🚊",
    TransportMode.BUS: "🚌",
    TransportMode.COACH: "🚌",
    TransportMode.FLEX: "🚐",
    TransportMode.ODM: "🚐",
    TransportMode.RIDE_SHARING: "🚗",
    TransportMode.FERRY: "⛴️",
    TransportMode.CABLE_CAR: "🚡",
    TransportMode.AERIAL_LIFT: "🚡",
    TransportMode.AREAL_LIFT: "🚡",
    TransportMode.FUNICULAR: "🚞",
    TransportMode.AIRPLANE: "✈️",
}


def _line_label(line: Line) -> str:
    """Return the label of a line in the line selector, with a vehicle symbol.

    The symbol tells e.g. a train from its replacement bus of the same name,
    if the replacement bus is a route of its own. It shows the kind of vehicle
    of the route: taken from the route type, the mode is only used if the route
    type is unknown. Single trips of a route run with another vehicle (GTFS
    trip_route_type) get no symbol of their own. The selector sorts by label,
    so the lines are grouped by vehicle.
    """
    symbol = _CLASS_SYMBOL.get(vehicle_class(line.route_type) or "") or (
        _MODE_SYMBOL.get(line.mode, "")
    )
    label = f"{line.route_short_name} - {line.head_sign}"

    return f"{symbol} {label}" if symbol else label


def _line_value(line: Line) -> str:
    """Return the option value of a line in the line selector."""
    return f"{line.route_id}---{line.direction_id}"


def _preselect_lines(
    selected: list[Line], available: list[Line]
) -> tuple[list[str], dict[str, Line]]:
    """Find the selector values of the configured lines.

    Returns the values to preselect and, for lines whose route ID changed
    (see helper.route_id_matches), the configured line per value. Saving keeps
    the configured line for those, so the sensor keeps its unique ID. A line
    found by its exact or prefixless route ID always wins over a changed one,
    a changed route ID is only used for a value no other configured line has,
    and the preselected values contain no duplicates.
    """
    available_values = {_line_value(line) for line in available}
    found: dict[int, str] = {}
    keep: dict[str, Line] = {}

    for index, old_line in enumerate(selected):
        value = _line_value(old_line)
        if value in available_values:
            found[index] = value
            continue

        # Try suffix match to migrate old route ID format (e.g. missing de-DELFI_ prefix)
        migrated = next(
            (
                _line_value(line)
                for line in available
                if line.route_id.endswith(old_line.route_id)
                and line.direction_id == old_line.direction_id
            ),
            None,
        )
        if migrated:
            found[index] = migrated

    for index, old_line in enumerate(selected):
        if index in found:
            continue

        changed = next(
            (
                _line_value(line)
                for line in available
                if line.direction_id == old_line.direction_id
                and _line_value(line) not in found.values()
                and route_id_matches(
                    line.route_id,
                    old_line.route_id,
                    line.route_type,
                    line.route_short_name,
                    old_line.route_short_name,
                )
            ),
            None,
        )
        if changed:
            found[index] = changed
            keep[changed] = old_line

    defaults = list(dict.fromkeys(found[i] for i in sorted(found)))
    return defaults, keep


async def _fetch_lines(stop_ids: list[str | Stop], unique: bool = True) -> list[Line]:
    """Fetch lines for given stop ids."""

    lines: list[Line] = []

    api = MotisApi(base_url=REQUEST_API_URL)

    for stop_id in stop_ids:
        _LOGGER.debug("Fetching stop times for stop: %s", stop_id)

        try:
            stop_times = await _send_api_request(
                api,
                ApiCommand.STOP_TIMES,
                {
                    "stopId": normalize_stop_id(str(stop_id)),
                    "n": str(1000),
                },
            )

            lines.extend(_extract_lines_from_stop_times(stop_times, unique=unique))
        except ValueError as err:
            _LOGGER.error(
                "Error fetching stop times for stop %s: %s, continuing with next stop if available",
                stop_id,
                err,
            )

    return list(set(lines)) if unique else lines


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
                            lambda x: (
                                x.route_id == routeId and x.direction_id == directionId
                            ),
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

        self._lines = await _fetch_lines(self._selected_stops, unique=True)

        line_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=_line_label(line),
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
        self._lines_kept: dict[str, Line] = {}

        _LOGGER.debug("Start configuration")

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""

        _LOGGER.debug(' Start "step_init" '.center(60, "-"))
        _LOGGER.debug(">> user input: %s", user_input)

        if user_input is not None:
            lines_user_choose = user_input.get(CONF_LINES, [])

            lines_new_state: list[Line] = []

            for user_option in lines_user_choose:
                if user_option in self._lines_kept:
                    lines_new_state.append(self._lines_kept[user_option])
                    continue

                (route_id, direction_id) = user_option.split("---")

                lines_new_state.append(
                    next(
                        filter(
                            lambda x: (
                                x.route_id == route_id
                                and x.direction_id == direction_id
                            ),
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

        self._lines_available = await _fetch_lines(
            self.config_entry.data.get(CONF_STOP_IDS, []), unique=True
        )

        available_lines = [x.to_dict() for x in self._lines_available]

        if _sorted_lines(available_lines) != _sorted_lines(
            self.config_entry.data.get(CONF_AVAILABLE_LINES, [])
        ):
            _LOGGER.debug("Updating config entry data with (new) available lines")

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_AVAILABLE_LINES: available_lines,
                },
            )

        options_list: list[SelectOptionDict] = [
            SelectOptionDict(
                label=_line_label(line),
                value=f"{line.route_id}---{line.direction_id}",
            )
            for line in self._lines_available
        ]

        valid_defaults, self._lines_kept = _preselect_lines(
            self._lines_selected, self._lines_available
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "lines",
                        default=valid_defaults,
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
