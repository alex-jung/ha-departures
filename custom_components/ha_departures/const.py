"""Constants for Public Transport Departures."""

from typing import Final

NAME = "Public Transport Departures"
DOMAIN = "ha_departures"
VERSION = "3.0.0"

# Github URLs
GITHUB_REPO_URL = "https://github.com/alex-jung/ha-departures"
GITHUB_ISSUE_URL = f"{GITHUB_REPO_URL}/issues"

# Motis API constants
PROVIDER_URL = "https://transitous.org/"
REQUEST_API_URL = "https://api.transitous.org/api"
REQUEST_HEADER_JSON: Final = "application/json"
REQUEST_TIMEOUT: Final = 10  # seconds
REQUEST_RETRIES: Final = 3  # number of retries for failed requests
REQUEST_TIMES_PER_LINE_COUNT: Final = 20  # number of departure times to fetch per line

# Configuration and options
CONF_STOP_NAME = "stop_name"
CONF_STOP_IDS = "stop_ids"
CONF_STOP_COORD = "stop_coord"
CONF_API_URL = "api_url"
CONF_ENDPOINT = "endpoint"
CONF_LINES = "lines"
CONF_HUB_NAME = "hub_name"
CONF_ERROR_NO_STOP_FOUND = "no_stop_found"
CONF_ERROR_NO_CHANGES_OPTIONS = "no_changes_configured"
CONF_ERROR_INVALID_RESPONSE = "invalid_api_response"
CONF_ERROR_CONNECTION_FAILED = "connection_failed"

# Sensor attributes
ATTR_LINE_NAME: Final = "line_name"
ATTR_LINE_ID: Final = "line_id"
ATTR_TRANSPORT_TYPE: Final = "transport"
ATTR_DIRECTION: Final = "direction"
ATTR_PROVIDER_URL: Final = "data_provider"
ATTR_TIMES: Final = "times"
ATTR_PLANNED_DEPARTURE_TIME: Final = "planned"
ATTR_ESTIMATED_DEPARTURE_TIME: Final = "estimated"

DEPARTURES_PER_SENSOR_LIMIT: Final = 20  # max number of departures per sensor


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
If you have any issues with this you need to open an issue here:
{GITHUB_ISSUE_URL}
-------------------------------------------------------------------
"""
