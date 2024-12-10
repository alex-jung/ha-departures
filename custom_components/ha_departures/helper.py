"""Helper function for custom integration."""

from apyefa import Line, TransportType


def transport_to_str(t_type: TransportType):
    """Return human readable german translation of transport type."""
    match t_type:
        case TransportType.BUS:
            return "Bus"
        case TransportType.SUBWAY:
            return "U-Bahn"
        case TransportType.TRAM:
            return "Tram"
        case TransportType.RBUS:
            return "Regional Bus"
        case TransportType.RAIL:
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
