"""Helper function for custom integration."""

import logging
import re
from datetime import datetime

from apyefa import Departure, Line, TransportType

_LOGGER = logging.getLogger(__name__)


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


def line_hash(line: Line) -> str:
    """Return a hash of the line object."""
    return str(hash(f"{line.id}"))


def create_unique_id(line: Line | dict[str, str]) -> str | None:
    """Create an unique id for a line."""
    if isinstance(line, dict):
        line = Line.from_dict(line)

    if isinstance(line, Line):
        return f"{replace_year_in_id(line.id)}-{line.product}-{line.destination.id}"

    raise ValueError(f"Expected dict or Line object, got {type(line)}")


def filter_by_line_id(departures: list[Departure], line_id: str) -> list[Departure]:
    """Filter departures by line id.

    Args:
        departures (list[Departure]): The list of departures to filter.
        line_id (str): The line id to filter by.

    Returns:
        list[Departure]: The filtered list of departures.

    """
    if not line_id:
        _LOGGER.warning(">> No line_id provided, returning all departures")
        return departures

    return [
        departure
        for departure in departures
        if compare_line_ids(departure.line_id, line_id, False)
    ]


def filter_identical_departures(departures: list[Departure]) -> list[Departure]:
    """Filter out identical departures based on their line_id and planned time.

    Args:
        departures (list[Departure]): The list of departures to filter.

    Returns:
        list[Departure]: The filtered list of departures with unique line_id and planned time combinations.

    """
    seen = set()
    unique_departures = []

    for departure in departures:
        key = (departure.line_id, departure.planned_time)
        if key not in seen:
            seen.add(key)
            unique_departures.append(departure)

    return unique_departures


def compare_line_ids(line_id1: str, line_id2: str, compare_year: bool = True) -> bool:
    """Compare two line IDs for equality, with an option to ignore the year component.

    Args:
        line_id1 (str): The first line ID to compare.
        line_id2 (str): The second line ID to compare.
        compare_year (bool, optional): If True, compares the full line IDs including the year.
            If False, compares only the part before the last colon (':'), effectively ignoring the year.
            Defaults to True.

    Returns:
        bool: True if the line IDs are considered equal based on the comparison mode, False otherwise.

    """
    if compare_year:
        return line_id1 == line_id2

    (line_id1, _) = line_id1.rsplit(":", 1)
    (line_id2, _) = line_id2.rsplit(":", 1)

    _LOGGER.debug(">> Comparing line IDs: %s and %s", line_id1, line_id2)

    return line_id1 == line_id2


def replace_year_in_id(line_id: str, xx: bool = True) -> str:
    """Replace the year in the line id with 'xx' or with current year.

    Args:
        line_id (str): The line id to modify.
        xx (bool): If True, replace the year with 'xx', otherwise replace with the current year.

    Returns:
        str: The modified line id with the year replaced by 'xx'.

    """
    if xx:
        current_year = "xx"
    else:
        # Get the current year in two-digit format
        # This is used to replace the year in the line_id
        # Example: "j25" -> "j26" for year 2026
        current_year = datetime.now().strftime("%y")

    return re.sub(r"j2\d{1}", f"j{current_year}", line_id)


def get_unique_lines(lines: list[Line]) -> list[Line]:
    """Return a list of unique Line objects from the input list, preserving their original order."""
    result: list[Line] = []
    unique_lines = set()

    _LOGGER.debug("Starting to filter unique lines from the list")

    for line in lines:
        if (line.id, line.destination.name) not in unique_lines:
            unique_lines.add((line.id, line.destination.name))
            result.append(line)

            _LOGGER.debug(
                'Add line: %s(%s) --> "%s"',
                line.name,
                line.id,
                line.destination.name,
            )
        else:
            _LOGGER.warning(
                'Duplicate line: %s(%s) --> "%s"',
                line.name,
                line.id,
                line.destination.name,
            )

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
