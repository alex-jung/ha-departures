"""Helper function for custom integration."""

from apyefa import Departure, Line, TransportType


def transport_to_str(t_type: TransportType):
    """Return human readable german translation of transport type."""
    match t_type:
        case TransportType.CITY_BUS:
            return "Bus"
        case TransportType.REGIONAL_BUS:
            return "Reginal Bus"
        case TransportType.EXPRESS_BUS:
            return "Express Bus"
        case TransportType.SUBWAY:
            return "U-Bahn"
        case TransportType.TRAM:
            return "Tram"
        case TransportType.TRAIN:
            return "Zug"
        case TransportType.SUBURBAN:
            return "S-Bahn"

    return "Unknown"


def create_unique_id(line: Line | dict[str, str]) -> str | None:
    """Create an unique id for a line."""
    if isinstance(line, dict):
        line = Line.from_dict(line)

    if isinstance(line, Line):
        return f"{line.id}-{line.product}-{line.destination.id}"

    raise ValueError(f"Expected dict or Line object, got {type(line)}")


class UnstableDepartureTime:
    """
    A helper class to manage and track unstable departure times, handling planned and estimated
    departure times with a mechanism to reset values after a certain number of consecutive `None` values.

    Attributes:
        MAX_NONE_VALUES (int): The maximum number of consecutive `None` values allowed before resetting.

    Args:
        attr_planned (str): The attribute name for the planned departure time in the output dictionary.
        attr_estimated (str): The attribute name for the estimated departure time in the output dictionary.

    Properties:
        planned_time: Returns the current planned departure time.
        estimated_time: Returns the current estimated departure time.
        none_counts: Returns the current count of consecutive `None` values.

    Methods:
        update(departure: Departure):
            Updates the planned and estimated departure times based on the provided `Departure` object.
            Resets or increments the `none_count` based on the presence of `None` values.

        to_dict():
            Returns a dictionary representation of the planned and estimated departure times
            using the provided attribute names.
    """

    MAX_NONE_VALUES = 5

    def __init__(self, attr_planned: str, attr_estimated: str) -> None:
        """
        Initialize the helper class with planned and estimated attributes.

        Args:
            attr_planned (str): The attribute name for the planned departure time.
            attr_estimated (str): The attribute name for the estimated departure time.
        """
        self._attr_planned = attr_planned
        self._attr_estimated = attr_estimated
        self._planned_departure_time = None
        self._estimated_departure_time = None
        self._none_count = 0

    @property
    def planned_time(self):
        return self._planned_departure_time

    @property
    def estimated_time(self):
        return self._estimated_departure_time

    @property
    def none_counts(self):
        return self._none_count

    def update(self, departure: Departure):
        if departure is None:
            self._planned_departure_time = None
            self._estimated_departure_time = None
            self._none_count = 0
            return

        if departure.planned_time is not None:
            self._planned_departure_time = departure.planned_time
            self._none_count = 0
        elif self._none_count < self.MAX_NONE_VALUES:
            self._none_count += 1
        else:
            self._planned_departure_time = None
            self._none_count = 0

        if departure.estimated_time is not None:
            self._estimated_departure_time = departure.estimated_time
            self._none_count = 0
        elif self._none_count < self.MAX_NONE_VALUES:
            self._none_count += 1
        else:
            self._estimated_departure_time = None
            self._none_count = 0

    def to_dict(self):
        return {
            self._attr_planned: self._planned_departure_time,
            self._attr_estimated: self._estimated_departure_time,
        }
