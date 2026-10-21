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


def unique_stop_ids(stop_ids: list) -> list[str]:
    """Return the normalized stop IDs without duplicates, keeping the order.

    The stop list of Transitous contains the same stop several times
    ("...:293", "...:293_G", "...:293_G_G"); all of them are requested alike.
    """
    return list(dict.fromkeys(normalize_stop_id(str(s)) for s in stop_ids))


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
