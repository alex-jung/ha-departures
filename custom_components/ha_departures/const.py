"""Constants for Public Transport Departures."""

# Base component constants
from enum import StrEnum


NAME = "Public Transport Departures"
DOMAIN = "ha_departures"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"

ISSUE_URL = "https://github.com/alex-jung/ha-departures/issues"

# Icons
ICON = "mdi:format-quote-close"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
SWITCH = "switch"
PLATFORMS = [BINARY_SENSOR, SENSOR, SWITCH]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

CONF_STATION = "station_name"
CONF_PROFILE = "profile"


# Enums
class PROFILES(StrEnum):
    DB = "Deutsche Bahn"
    KVB = "Kölner Verkehrsvetrieb"
    NASA = "Nahverkehr Sachsen-Anhalt"
    NVV = "Nordhessischer Verkehrs Verbund"
    VSN = "Verkehrsverbund Süd-Niedersachsen"
    VVV = " Verkehrsverbund Vorarlberg"


# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
