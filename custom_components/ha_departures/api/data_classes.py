"""Data classes and enums for API classes."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from custom_components.ha_departures.helper import str_to_datetime


class ApiCommand(StrEnum):
    """API commanStrEnum."""

    STOPS = "v1/map/stops"
    STOP_TIMES = "v5/stoptimes"
    ONE_TO_ALL = "v1/one-to-all"
    REVERSE_GEOCODE = "v1/reverse-geocode"


class TransportMode(StrEnum):
    """Transport mode enums."""

    BIKE = "BIKE"
    RENTAL = "RENTAL"
    CAR = "CAR"
    CAR_PARKING = "CAR_PARKING"
    CAR_DROPOFF = "CAR_DROPOFF"
    ODM = "ODM"
    RIDE_SHARING = "RIDE_SHARING"
    FLEX = "FLEX"
    TRANSIT = "TRANSIT"
    TRAM = "TRAM"
    SUBWAY = "SUBWAY"
    FERRY = "FERRY"
    AIRPLANE = "AIRPLANE"
    SUBURBAN = "SUBURBAN"
    BUS = "BUS"
    COACH = "COACH"
    RAIL = "RAIL"
    HIGHSPEED_RAIL = "HIGHSPEED_RAIL"
    LONG_DISTANCE = "LONG_DISTANCE"
    NIGHT_RAIL = "NIGHT_RAIL"
    REGIONAL_FAST_RAIL = "REGIONAL_FAST_RAIL"
    REGIONAL_RAIL = "REGIONAL_RAIL"
    CABLE_CAR = "CABLE_CAR"
    FUNICULAR = "FUNICULAR"
    AERIAL_LIFT = "AERIAL_LIFT"
    OTHER = "OTHER"
    AREAL_LIFT = "AREAL_LIFT"
    METRO = "METRO"


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


@dataclass
class StopTime:
    """Data class for a stop time."""

    mode: TransportMode
    real_time: bool
    head_sign: str
    short_name: str
    route_id: str
    direction: str
    arrival_time: str
    departure_time: str
    scheduled_arrival_time: str
    scheduled_departure_time: str
    cancelled: bool

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "StopTime":
        """Create a StopTime object from a dictionary."""
        return StopTime(
            mode=TransportMode(data["mode"]),
            real_time=data["realTime"],
            head_sign=data["headsign"],
            short_name=data["routeShortName"],
            route_id=data["routeId"],
            direction=data["directionId"],
            arrival_time=data["place"]["arrival"],
            departure_time=data["place"]["departure"],
            scheduled_arrival_time=data["place"]["scheduledArrival"],
            scheduled_departure_time=data["place"]["scheduledDeparture"],
            cancelled=data["cancelled"],
        )


@dataclass
class Line:
    """Data class for a transit line."""

    route_id: str
    direction_id: str
    head_sign: str
    route_short_name: str
    mode: TransportMode

    def to_dict(self) -> dict[str, Any]:
        """Convert Line object to dictionary."""
        return {
            "route_id": self.route_id,
            "direction_id": self.direction_id,
            "head_sign": self.head_sign,
            "route_short_name": self.route_short_name,
            "transport_mode": self.mode.value,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Line":
        """Create a Line object from a dictionary."""
        return Line(
            route_id=data["route_id"],
            direction_id=data["direction_id"],
            head_sign=data["head_sign"],
            route_short_name=data["route_short_name"],
            mode=TransportMode(data["transport_mode"]),
        )

    def __hash__(self) -> int:
        """Override hash function for Line class."""
        return hash((self.route_id, self.direction_id))

    def __eq__(self, value: object) -> bool:
        """Override equality check for Line class."""
        if not isinstance(value, Line):
            return NotImplemented
        return (
            self.route_id == value.route_id and self.direction_id == value.direction_id
        )


@dataclass
class Departure:
    """Data class for a departure."""

    route_id: str
    direction_id: str
    trip_id: str
    departure: datetime | None
    scheduled_departure: datetime | None
    real_time: bool

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Departure":
        """Create a Departure object from a dictionary."""

        departure_time = data.get("place", {}).get("departure")
        scheduled_departure_time = data.get("place", {}).get("scheduledDeparture")

        return Departure(
            route_id=data["routeId"],
            direction_id=data["directionId"],
            trip_id=data["tripId"],
            departure=str_to_datetime(departure_time),
            scheduled_departure=str_to_datetime(scheduled_departure_time),
            real_time=data["realTime"],
        )

    def __hash__(self) -> int:
        """Override hash function for Departure class."""
        return hash((self.route_id, self.direction_id, self.trip_id, self.departure))
