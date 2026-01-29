"""Data classes and enums for API classes."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class API_COMMAND(StrEnum):
    """API command enums."""

    STOPS = "v1/map/stops"
    STOP_TIMES = "v5/stoptimes"
    ONE_TO_ALL = "v1/one-to-all"
    REVERSE_GEOCODE = "v1/reverse-geocode"


@dataclass
class Stop:
    """Data class for a transit stop."""

    id: str
    name: str
    latitude: float
    longitude: float

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Stop":
        """Create a Stop object from a dictionary."""
        return Stop(
            id=data["stopId"],
            name=data["name"],
            latitude=data["lat"],
            longitude=data["lon"],
        )
