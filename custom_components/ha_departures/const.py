"""Constants for Public Transport Departures."""

from typing import Final

NAME = "Public Transport Departures"
DOMAIN = "ha_departures"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "2.0.3"

ISSUE_URL = "https://github.com/alex-jung/ha-departures/issues"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

# Configuration and options
CONF_STOP_NAME = "stop_name"
CONF_STOP_ID = "stop_id"
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
ATTR_STOP_ID: Final = "stop_id"
ATTR_TRANSPORT_TYPE: Final = "transport"
ATTR_DIRECTION: Final = "direction"
ATTR_DIRECTION_TEXT: Final = "direction_text"
ATTR_DEPARTURES: Final = "departures"
ATTR_PROVIDER_URL: Final = "data_provider"
ATTR_PLANNED_DEPARTURE_TIME: Final = "planned_departure_time"
ATTR_PLANNED_DEPARTURE_TIME_1: Final = "planned_departure_time_1"
ATTR_PLANNED_DEPARTURE_TIME_2: Final = "planned_departure_time_2"
ATTR_PLANNED_DEPARTURE_TIME_3: Final = "planned_departure_time_3"
ATTR_PLANNED_DEPARTURE_TIME_4: Final = "planned_departure_time_4"
ATTR_ESTIMATED_DEPARTURE_TIME: Final = "estimated_departure_time"
ATTR_ESTIMATED_DEPARTURE_TIME_1: Final = "estimated_departure_time_1"
ATTR_ESTIMATED_DEPARTURE_TIME_2: Final = "estimated_departure_time_2"
ATTR_ESTIMATED_DEPARTURE_TIME_3: Final = "estimated_departure_time_3"
ATTR_ESTIMATED_DEPARTURE_TIME_4: Final = "estimated_departure_time_4"


# Endpoints
EFA_ENDPOINTS: Final = {
    # Baden-Württemberg
    "Freiburger Verkehrs AG (VAG)": "https://efa.vagfr.de/vagfr3/",
    "Nahverkehrsgesellschaft Baden-Württemberg (nvbw)": "https://www.efa-bw.de/bvb3/",
    "Verkehrsverbund Rhein-Neckar (VRN)": "https://www.vrn.de/mngvrn/",
    "Verkehrs- und Tarifverbund Stuttgart (VVS)": "https://www3.vvs.de/mngvvs/",
    # Bayern
    "MoBY (Bahnland Bayern)": "https://bahnland-bayern.de/efa/",
    "Regensburger Verkehrsverbund (RVV)": "https://efa.rvv.de/efa/",
    "Verkehrsverbund Großraum Nürnberg (VGN)": "https://efa.vgn.de/vgnExt_oeffi/",
    # Mecklenburg-Vorpommern
    "Verkehrsgesellschaft Mecklenburg-Vorpommern mbH (VMV)": "https://fahrplanauskunft-mv.de/vmv-efa/",
    # Nordrhein-Westfalen
    "Der WestfalenTarif": "https://www.westfalenfahrplan.de/nwl-efa/",
    "Aachener Verkehrsverbund (AVV)": "https://avv.efa.de/efa/",
    # Rheinland-Pfalz
    "Rolph.de": "https://mandanten.vrn.de/takt2/",
    # Sachsen
    "Verkehrsverbund Mittelsachsen GmbH (VMS)": "https://efa.vvo-online.de/VMSSL3/",
    # Niedersachsen
    "Vehrkehrsverbund Region Braunschweig (VRB)": "https://bsvg.efa.de/vrbstd_relaunch/",
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
