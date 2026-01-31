"""Tests for the helper functions in ha_departures."""

from datetime import datetime

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ha_departures.helper import bounding_box, str_to_datetime


def test_bounding_box_basic():
    """Test bounding_box with standard coordinates."""
    lat, lon, radius = 52.5, 13.4, 1000
    upper_left, lower_right = bounding_box(lat, lon, radius)

    assert isinstance(upper_left, tuple)
    assert isinstance(lower_right, tuple)
    assert len(upper_left) == 2
    assert len(lower_right) == 2
    assert upper_left[0] > lat
    assert upper_left[1] < lon
    assert lower_right[0] < lat
    assert lower_right[1] > lon


def test_bounding_box_zero_radius():
    """Test bounding_box with zero radius."""
    lat, lon, radius = 40.0, -74.0, 0
    upper_left, lower_right = bounding_box(lat, lon, radius)

    assert upper_left[0] == lat
    assert upper_left[1] == lon
    assert lower_right[0] == lat
    assert lower_right[1] == lon


def test_bounding_box_large_radius():
    """Test bounding_box with large radius."""
    lat, lon, radius = 0.0, 0.0, 100_000
    upper_left, lower_right = bounding_box(lat, lon, radius)

    assert upper_left[0] > 0
    assert lower_right[0] < 0


def test_bounding_box_negative_coordinates():
    """Test bounding_box with negative latitude and longitude."""
    lat, lon, radius = -33.9, 18.4, 5000
    upper_left, lower_right = bounding_box(lat, lon, radius)

    assert upper_left[0] > lat
    assert lower_right[0] < lat


@pytest.mark.parametrize(
    ("lat", "lon", "radius"),
    [
        (51.5, -0.1, 1000),
        (35.7, 139.7, 2000),
        (-37.8, 144.9, 500),
    ],
)
def test_bounding_box_various_locations(lat, lon, radius):
    """Test bounding_box with various real-world coordinates."""
    upper_left, lower_right = bounding_box(lat, lon, radius)

    assert upper_left[0] > lower_right[0]
    assert upper_left[1] < lower_right[1]


def test_str_to_datetime_valid_iso():
    """Test str_to_datetime with a valid ISO 8601 string."""
    iso_str = "2024-06-01T12:34:56+00:00"
    result = str_to_datetime(iso_str)
    expected = dt_util.as_local(dt_util.parse_datetime(iso_str))
    assert isinstance(result, datetime)
    assert result == expected


def test_str_to_datetime_valid_iso_no_tz():
    """Test str_to_datetime with a valid ISO string without timezone."""
    iso_str = "2024-06-01T12:34:56"
    result = str_to_datetime(iso_str)
    expected = dt_util.as_local(dt_util.parse_datetime(iso_str))
    assert isinstance(result, datetime)
    assert result == expected


def test_str_to_datetime_empty_string():
    """Test str_to_datetime with an empty string."""
    assert str_to_datetime("") is None


def test_str_to_datetime_none():
    """Test str_to_datetime with None as input."""
    assert str_to_datetime(None) is None


def test_str_to_datetime_invalid_format():
    """Test str_to_datetime with an invalid date string."""
    assert str_to_datetime("not-a-date") is None


def test_str_to_datetime_invalid_date():
    """Test str_to_datetime with a non-existent date."""
    assert str_to_datetime("2024-02-30T12:00:00") is None


def test_str_to_datetime_leap_second():
    """Test str_to_datetime with a leap second (should be invalid)."""
    assert str_to_datetime("2016-12-31T23:59:60Z") is None
