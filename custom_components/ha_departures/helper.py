"""Helper function for custom integration."""

import logging
import math
import re
from datetime import datetime

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


def str_to_datetime(date: str) -> datetime | None:
    """Convert a time string to a (local) datetime object.

    Args:
        date (str): The date/time string in ISO 8601 format.

    Returns:
        datetime | None: The corresponding (local) datetime object, or None if the input is invalid.

    """
    if not date:
        return None

    try:
        dt = dt_util.parse_datetime(date)

        return dt_util.as_local(dt) if dt else None
    except ValueError:
        _LOGGER.error("Invalid datetime format: %s", date)
        return None


def bounding_box(lat, lon, radius_m):
    """Calculate a bounding box around a point given a radius in meters."""

    meters_per_degree = 111_320

    delta_lat = radius_m / meters_per_degree
    delta_lon = radius_m / (meters_per_degree * math.cos(math.radians(lat)))

    upper_left = (lat + delta_lat, lon - delta_lon)
    lower_right = (lat - delta_lat, lon + delta_lon)

    return upper_left, lower_right


def normalize_stop_id(stop_id: str) -> str:
    """Remove all trailing "_G" suffixes from a stop ID.

    Transitous returns the same stop with a varying number of "_G" suffixes
    (e.g. "...:293", "...:293_G", "...:293_G_G").
    """
    return re.sub(r"(?:_G)+$", "", stop_id)


def stop_id_matches(stop_id: str, configured_ids: list[str]) -> bool:
    """Check whether a stop ID from the API belongs to one of the configured stops.

    A stop matches if its normalized ID equals a configured (normalized) ID or is
    a child of it, e.g. platform "...:9991:1:1" for the configured stop "...:9991".
    The child check respects the ":" boundary, so "...:91" never matches "...:911".
    """
    normalized = normalize_stop_id(stop_id)

    return any(
        normalized == base or normalized.startswith(f"{base}:")
        for base in (normalize_stop_id(c) for c in configured_ids)
    )


_ROUTE_TYPE_SUFFIX = re.compile(r"_(\d{1,4})$")

# Feed whose route IDs end with the route type and change it for existing lines
_ROUTE_TYPE_CHANGING_FEED = "de-DELFI_"

# Vehicle class of a GTFS route type, as the Transitous backend (MOTIS/nigiri,
# src/loader/gtfs/route.cc, to_clasz) classifies the explicitly listed types.
# Types of the same class are the same kind of vehicle, e.g. 100 and 106 are
# both regional trains, while 3 (bus) and 106 (train) or 101 (ICE) and 102 (IC)
# are not. Types nigiri maps to "other" or only by range (1000-1299, ships and
# air) are left out: vehicle_class returns None for them and no ID is healed.
_VEHICLE_CLASS: dict[int, str] = {
    0: "tram",
    1: "subway",
    2: "regional",
    3: "bus",
    4: "ship",
    5: "funicular",
    6: "aerial_lift",
    7: "funicular",
    11: "bus",
    **dict.fromkeys(
        (100, 103, 106, 107, 108, 110, 111, 112, 113, 115, 117), "regional"
    ),
    101: "high_speed",
    **dict.fromkeys((102, 104, 114), "long_distance"),
    105: "night",
    109: "suburban",
    116: "funicular",
    **dict.fromkeys((200, 201, 202, 205, 206, 207, 209), "coach"),
    **dict.fromkeys((203, 204, 208), "bus"),
    **dict.fromkeys((400, 401, 402), "subway"),
    **dict.fromkeys((403, 404), "suburban"),
    **dict.fromkeys((*range(700, 715), 716, 800), "bus"),
    715: "on_demand",
    **dict.fromkeys(range(900, 907), "tram"),
    **dict.fromkeys((1000, 1200), "ship"),
    1100: "air",
    **dict.fromkeys((1300, 1301, 1302, 1304, 1306, 1307), "aerial_lift"),
    1400: "funicular",
    **dict.fromkeys(range(1500, 1508), "on_demand"),
    1551: "ride_sharing",
}


def vehicle_class(route_type: int | str | None) -> str | None:
    """Return the vehicle class of a GTFS route type, None if unknown."""
    try:
        return _VEHICLE_CLASS.get(int(route_type))
    except (TypeError, ValueError):
        return None


def route_id_matches(
    route_id: str,
    configured_route_id: str,
    route_type: int | str | None = None,
    route_short_name: str | None = None,
    configured_short_name: str | None = None,
) -> bool:
    """Check whether a route ID from the API belongs to a configured line.

    Stored route IDs may lack the feed prefix (e.g. "de-DELFI_"), so the API ID
    only has to end with the stored one.

    DELFI route IDs end with the GTFS route type ("..._106"), and the feed
    changes it for existing lines ("..._100" in one feed version, "..._106" in
    the next). Called with the API's ``route_type`` and the short names, such
    a changed ID is accepted if all of this holds:

    * both IDs end with "_<1-4 digits>" and the API's suffix equals the
      ``route_type`` the API reports for this departure,
    * both route types are the same kind of vehicle (``vehicle_class``), so a
      train line never shows a replacement bus and an ICE line never an IC,
    * the short names are equal and not empty,
    * an identifier remains after the feed tag (feeds with plain numeric
      route IDs have no route type suffix, the number is the line itself),
    * the rest of the IDs matches at an "_" boundary.

    Only DELFI (feed tag "de-DELFI") is handled this way: there the change of
    the route type was observed, and its suffix always is the route type.
    Other feeds keep the exact match only.

    Callers use the changed ID only for lines whose exact route ID is not in
    the data.
    """
    if route_id.endswith(configured_route_id):
        return True

    if not route_id.startswith(_ROUTE_TYPE_CHANGING_FEED):
        return False

    api_suffix = _ROUTE_TYPE_SUFFIX.search(route_id)
    stored_suffix = _ROUTE_TYPE_SUFFIX.search(configured_route_id)

    if not (api_suffix and stored_suffix) or str(route_type) != api_suffix.group(1):
        return False

    api_class = vehicle_class(route_type)

    if api_class is None or api_class != vehicle_class(stored_suffix.group(1)):
        return False

    if not route_short_name or route_short_name != configured_short_name:
        return False

    api_base = route_id[: api_suffix.start()]
    stored_base = configured_route_id[: stored_suffix.start()]

    if "_" not in api_base or not api_base.split("_", 1)[1]:
        return False

    return api_base.endswith(stored_base) and (
        len(api_base) == len(stored_base) or api_base[-len(stored_base) - 1] == "_"
    )
