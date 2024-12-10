"""Constants for Public Transport Departures."""

# Base component constants
from typing import Final

NAME = "Public Transport Departures"
DOMAIN = "ha_departures"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"

ISSUE_URL = "https://github.com/alex-jung/ha-departures/issues"

# Device classes

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]


# Configuration and options
CONF_STOP_NAME = "stop_name"
CONF_STOP_ID = "stop_id"
CONF_API_URL = "api_url"
CONF_ENDPOINT = "endpoint"
CONF_LINES = "lines"
CONF_ERROR_NO_STOP_FOUND = "no_stop_found"
CONF_ERROR_NO_CHANGES_OPTIONS = "no_changes_configured"
CONF_ERROR_INVALID_RESPONSE = "invalid_api_response"
CONF_ERROR_CONNECTION_FAILED = "connection_failed"

# Sensor attributes
ATTR_LINE_ID: Final = "line_id"
ATTR_LINE_NAME: Final = "line_name"
ATTR_STOP_ID: Final = "stop_id"
ATTR_TRANSPORT_TYPE: Final = "transport"
ATTR_DIRECTION: Final = "direction"
ATTR_DIRECTION_TEXT: Final = "direction_text"
ATTR_DEPARTURES: Final = "departures"
ATTR_DELAY: Final = "delay"
ATTR_OCCUPANCY_LEVEL: Final = "occupancy_level"
ATTR_PLANNED_DEPARTURE_TIME: Final = "planned_departure_time"
ATTR_ACTUAL_DEPARTURE_TIME: Final = "actual_departure_time"


# Endpoints
EFA_ENDPOINTS: Final = {
    "Verkehrsverbund Großraum Nürnberg(VGN)": "https://efa.vgn.de/vgnExt_oeffi/"
}


# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
