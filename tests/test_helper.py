"""Tests for the helper functions in ha_departures."""

from datetime import datetime
from unittest.mock import Mock

from apyefa import Line, TransportType

from custom_components.ha_departures.helper import (
    compare_line_ids,
    create_unique_id,
    filter_by_line_id,
    filter_identical_departures,
    get_unique_lines,
    line_hash,
    replace_year_in_id,
    transport_to_str,
)


def test_transport_to_str():
    """Test transport_to_str function."""
    assert transport_to_str(TransportType.CITY_BUS) == "Bus"
    assert transport_to_str(TransportType.REGIONAL_BUS) == "Reginal Bus"
    assert transport_to_str(TransportType.EXPRESS_BUS) == "Express Bus"
    assert transport_to_str(TransportType.SUBWAY) == "U-Bahn"
    assert transport_to_str(TransportType.TRAM) == "Tram"
    assert transport_to_str(TransportType.TRAIN) == "Zug"
    assert transport_to_str(TransportType.SUBURBAN) == "S-Bahn"
    assert transport_to_str(None) == "Unknown"  # Test for None case


def test_line_hash():
    """Test line_hash function."""

    line = Mock()
    line.id = "123"

    assert line_hash(line) == str(hash("123"))  # Check if the hash matches


def test_create_unique_id_line_instance():
    """Test create_unique_id function."""
    line = Mock(Line)
    line.id = "123"
    line.product = "bus"
    line.destination = Mock()
    line.destination.id = "456"

    unique_id = f"{line.id}-bus-456"
    assert create_unique_id(line) == unique_id


def test_filter_by_line_id_ignore_year():
    """Test filter_by_line_id function."""
    departures = [
        Mock(line_id="van:02067: :R:j20"),
        Mock(line_id="van:02067: :R:j21"),
        Mock(line_id="van:02067: :R:j24"),
        Mock(line_id="van:11111: :R:j25"),
    ]
    filtered_departures = filter_by_line_id(departures, "van:02067: :R:j25")
    assert len(filtered_departures) == 3
    assert filtered_departures[0].line_id == "van:02067: :R:j20"
    assert filtered_departures[1].line_id == "van:02067: :R:j21"
    assert filtered_departures[2].line_id == "van:02067: :R:j24"


def test_filter_identical_departures():
    """Test filter_by_line_id with identical departures."""
    departures = [
        Mock(
            line_id="line1", planned_time="2023-10-01T12:00:00Z"
        ),  # identical time and line_id
        Mock(
            line_id="line1", planned_time="2023-10-01T12:00:00Z"
        ),  # identical time and line_id
        Mock(line_id="line2", planned_time="2023-10-01T12:00:00Z"),  # unique line_id
        Mock(
            line_id="line2", planned_time="2025-10-01T23:06:00Z"
        ),  # unique departure time
    ]
    filtered_departures = filter_identical_departures(departures)
    assert len(filtered_departures) == 3  # Should be 3 unique departures


def test_compare_line_ids_compare_with_year():
    """Test compare_line_ids function."""

    assert (
        compare_line_ids("van:02067: :R:j25", "van:02067: :R:j25", compare_year=True)
        is True
    )
    assert (
        compare_line_ids("van:02067: :R:j25", "van:02067: :R:j26", compare_year=True)
        is False
    )


def test_compare_line_ids_compare_without_year():
    """Test compare_line_ids function."""

    assert (
        compare_line_ids("van:02067: :R:j25", "van:02067: :R:j25", compare_year=False)
        is True
    )
    assert (
        compare_line_ids("van:02067: :R:j25", "van:02067: :R:j80", compare_year=False)
        is True
    )


def test_replace_year_in_id_xx_true():
    """Test replace_year_in_id function."""
    assert replace_year_in_id("van:02067: :R:j25", xx=True) == "van:02067: :R:jxx"
    assert replace_year_in_id("van:02067: :R:s25", xx=True) == "van:02067: :R:s25"


def test_replace_year_in_id_xx_false():
    """Test replace_year_in_id function."""
    current_year = datetime.now().strftime("%y")

    assert (
        replace_year_in_id("van:02067: :R:j20", xx=False)
        == f"van:02067: :R:j{current_year}"
    )
    assert replace_year_in_id("van:02067: :R:s25", xx=False) == "van:02067: :R:s25"


def test_get_unique_lines():
    """Test get_unique_lines function."""
    line1 = Mock(Line)
    line1.name = "Line 1"
    line1.id = "line1"
    line1.destination = Mock()
    line1.destination.name = "destination1"

    line2 = Mock(Line)
    line2.name = "Line 2"
    line2.id = "line2"
    line2.destination = Mock()
    line2.destination.name = "destination2"

    line3 = Mock(Line)
    line3.name = "Line 3"
    line3.id = "line1"  # Duplicate of line1
    line3.destination = Mock()
    line3.destination.name = "destination1"  # Same destination as line1

    lines = [line1, line2, line3]
    unique_lines = get_unique_lines(lines)

    assert len(unique_lines) == 2
    assert unique_lines[0].id == "line1"
    assert unique_lines[1].id == "line2"
