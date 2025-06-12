"""Helper function for custom integration."""

from apyefa import Departure, Line, TransportType

from homeassistant.util import slugify


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


def create_unique_id(line: Line | dict[str, str], hub_name: str) -> str | None:
    """Create an unique id for a line."""
    if isinstance(line, dict):
        line = Line.from_dict(line)

    if isinstance(line, Line):
        return f"{slugify(hub_name)}-{line.id}-{line.product}-{line.destination.id}"

    raise ValueError(f"Expected dict or Line object, got {type(line)}")


def get_unique_lines(lines: list[Line]) -> list[Line]:
    """
    Returns a list of unique Line objects from the input list, preserving their original order.
    A Line is considered unique based on its 'id' attribute.

    Args:
        lines (list[Line]): A list of Line objects to filter for uniqueness.

    Returns:
        list[Line]: A list containing only the first occurrence of each unique Line, based on 'id'.
    """
    result: list[Line] = []
    unique_lines = set()

    for line in lines:
        if line.id not in unique_lines:
            unique_lines.add(line.id)
            result.append(line)

    return result


class UnstableDepartureTime:
    """Helper class to handle unstable departure times."""

    MAX_NONE_VALUES = 2

    def __init__(self, attr_planned: str, attr_estimated: str) -> None:
        """Initialize the helper class with planned and estimated attributes.

        Args:
            attr_planned (str): The attribute name for the planned departure time.
            attr_estimated (str): The attribute name for the estimated departure time.

        """
        self._attr_planned = attr_planned
        self._attr_estimated = attr_estimated
        self._planned_departure_time = None
        self._estimated_departure_time = None
        self._none_count_planned = 0

    @property
    def planned_time(self):
        """Retrieve the planned departure time.

        Returns:
            datetime: The planned departure time.

        """
        return self._planned_departure_time

    @property
    def estimated_time(self):
        """Retrieve the estimated departure time.

        Returns:
            datetime: The estimated departure time.

        """
        return self._estimated_departure_time

    @property
    def none_counts(self):
        """Retrieve the count of 'None' values.

        Returns:
            int: The number of 'None' values tracked by the instance.

        """
        return self._none_count

    def clear(self):
        """Reset the departure times and none counts."""
        self._planned_departure_time = None
        self._estimated_departure_time = None
        self._none_count_planned = 0

    def update(self, departure: Departure):
        """Update the departure times and manages the count of consecutive None values.

        Args:
            departure (Departure): An object containing the planned and estimated
                departure times. If None, the times are reset.

        Behavior:
            - If `departure` is None:
                - Resets `_planned_departure_time` and `_estimated_departure_time` to None.
                - Resets `_none_count_planned` to 0.
            - If `departure.planned_time` is not None:
                - Updates `_planned_departure_time` with `departure.planned_time`.
                - Resets `_none_count_planned` to 0.
            - If `departure.planned_time` is None and `_none_count_planned` is less
              than `MAX_NONE_VALUES`:
                - Increments `_none_count_planned`.
            - If `departure.planned_time` is None and `_none_count_planned` reaches
              `MAX_NONE_VALUES`:
                - Resets `_planned_departure_time` to None.
                - Resets `_none_count_planned` to 0.
            - Updates `_estimated_departure_time` with `departure.estimated_time`.

        """
        if departure is None:
            # If the departure is None, reset the times and none counts
            self._planned_departure_time = None
            self._estimated_departure_time = None
            self._none_count_planned = 0
            return

        if departure.planned_time is not None:
            self._planned_departure_time = departure.planned_time
            self._none_count_planned = 0
        elif self._none_count_planned < self.MAX_NONE_VALUES:
            self._none_count_planned += 1
        else:
            self._planned_departure_time = None
            self._none_count_planned = 0

        self._estimated_departure_time = departure.estimated_time

    def to_dict(self):
        """Convert the departure information into a dictionary representation.

        Returns:
            dict: A dictionary containing the planned and estimated departure times,
                  where the keys are defined by `_attr_planned` and `_attr_estimated`,
                  and the values are `_planned_departure_time` and `_estimated_departure_time`, respectively.

        """
        return {
            self._attr_planned: self._planned_departure_time,
            self._attr_estimated: self._estimated_departure_time,
        }
