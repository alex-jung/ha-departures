"""Tests for the helper functions in ha_departures."""

from datetime import datetime

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ha_departures.helper import (
    bounding_box,
    normalize_stop_id,
    route_id_matches,
    stop_id_matches,
    str_to_datetime,
    vehicle_class,
)


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


@pytest.mark.parametrize(
    ("stop_id", "expected"),
    [
        ("de-DELFI_de:00001:10:0:12", "de-DELFI_de:00001:10:0:12"),
        ("de-DELFI_de:00001:10:0:12_G", "de-DELFI_de:00001:10:0:12"),
        ("de-DELFI_de:00001:10:0:12_G_G", "de-DELFI_de:00001:10:0:12"),
        ("de-DELFI_de:00001:20_G", "de-DELFI_de:00001:20"),
    ],
)
def test_normalize_stop_id(stop_id, expected):
    """Test that all trailing _G suffixes are removed."""
    assert normalize_stop_id(stop_id) == expected


@pytest.mark.parametrize(
    ("api_stop_id", "configured", "expected"),
    [
        # Configured without suffix, API answers with _G_G
        (
            "de-DELFI_de:00001:10:0:12_G_G",
            ["de-DELFI_de:00001:10:0:10", "de-DELFI_de:00001:10:0:12"],
            True,
        ),
        ("de-DELFI_de:00001:10:0:10_G", ["de-DELFI_de:00001:10:0:10"], True),
        # Configured parent stop, API answers with platform
        ("de-DELFI_de:00001:20:1:1", ["de-DELFI_de:00001:20"], True),
        # Exact match keeps working
        ("de-DELFI_de:00001:30:0:5", ["de-DELFI_de:00001:30:0:5"], True),
        # Configured with suffix, API without
        ("de-DELFI_de:00001:40:2:8", ["de-DELFI_de:00001:40:2:8_G_G"], True),
        # Neighbour stops inside the request radius must not match
        ("de-DELFI_de:00001:50:0:1", ["de-DELFI_de:00001:30:0:5"], False),
        ("de-DELFI_de:00001:10:0:11", ["de-DELFI_de:00001:10:0:12"], False),
        # ":" boundary: "...:10" must not match "...:101"
        ("de-DELFI_de:00001:101", ["de-DELFI_de:00001:10"], False),
        ("de-DELFI_de:00001:10", [], False),
    ],
)
def test_stop_id_matches(api_stop_id, configured, expected):
    """Test matching of API stop IDs against configured stop IDs."""
    assert stop_id_matches(api_stop_id, configured) is expected


@pytest.mark.parametrize(
    ("api_id", "route_type", "api_name", "stored", "stored_name", "expected"),
    [
        # exact / feed prefix missing: no further data needed
        (
            "de-DELFI_de:beg:RE3:_106",
            None,
            None,
            "de-DELFI_de:beg:RE3:_106",
            None,
            True,
        ),
        ("de-DELFI_de:beg:RE3:_106", None, None, "de:beg:RE3:_106", None, True),
        # DELFI changed the route type suffix of an existing line (measured)
        (
            "de-DELFI_de:beg:RE3:_106",
            106,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE3",
            True,
        ),
        ("de-DELFI_2280319_106", 106, "RE25", "de-DELFI_2280319_100", "RE25", True),
        ("de-DELFI_de:beg:RB44:_106", 106, "RB44", "de:beg:RB44:_100", "RB44", True),
        # stored without feed prefix, numeric
        ("de-DELFI_2280319_106", 106, "RE25", "2280319_100", "RE25", True),
        # the suffix has to be the route type the API reports
        (
            "de-DELFI_de:beg:RE3:_106",
            3,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE3",
            False,
        ),
        (
            "de-DELFI_de:beg:RE3:_106",
            None,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE3",
            False,
        ),
        (
            "de-DELFI_de:beg:RE3:_106",
            "106",
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE3",
            True,
        ),
        # short names have to be equal and not empty
        (
            "de-DELFI_de:beg:RE3:_106",
            106,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE2",
            False,
        ),
        ("de-DELFI_de:beg:RE3:_106", 106, "", "de-DELFI_de:beg:RE3:_100", "", False),
        (
            "de-DELFI_de:beg:RE3:_106",
            106,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            None,
            False,
        ),
        # different lines of one feed never match (same short name needed)
        (
            "de-DELFI_6986899_106",
            106,
            "RE22",
            "de-DELFI_de:beg:RE22:_100",
            "RE22",
            False,
        ),
        (
            "de-DELFI_de:beg:RB44:_106",
            106,
            "RB44",
            "de-DELFI_de:beg:RB45:_100",
            "RB45",
            False,
        ),
        (
            "it-Lombardia-Trenord_RE_2",
            2,
            "RE2",
            "it-Lombardia-Trenord_RE_1",
            "RE1",
            False,
        ),
        # nothing remains after the feed tag: the number is the line itself
        (
            "fr-horaires-des-trains-trenitalia-france_6105",
            6105,
            "X",
            "fr-horaires-des-trains-trenitalia-france_9287",
            "X",
            False,
        ),
        # "_" boundary: "12280319" is not "2280319"
        ("de-DELFI_12280319_106", 106, "RE25", "2280319_100", "RE25", False),
        # other kind of vehicle: never a bus for a train line or vice versa
        ("de-DELFI_2280319_3", 3, "RE25", "de-DELFI_2280319_100", "RE25", False),
        ("de-DELFI_2230866_106", 106, "RB45", "de-DELFI_2230866_3", "RB45", False),
        # ICE ("_101") and IC ("_102") of one line number are different trains
        ("de-DELFI_162295_102", 102, "20", "de-DELFI_162295_101", "20", False),
        # bus to bus (DELFI changed "_700" to "_3") is the same kind of vehicle
        ("de-DELFI_de:mvv:X1:_3", 3, "X1", "de-DELFI_de:mvv:X1:_700", "X1", True),
        # on-demand bus is not a scheduled bus
        ("de-DELFI_de:mvv:X1:_715", 715, "X1", "de-DELFI_de:mvv:X1:_700", "X1", False),
        # suffix is not the route type the API reports (same vehicle class)
        (
            "de-DELFI_de:beg:RE3:_106",
            100,
            "RE3",
            "de-DELFI_de:beg:RE3:_100",
            "RE3",
            False,
        ),
        # nothing remains after the feed tag
        ("de-DELFI_106", 106, "RE3", "de-DELFI_100", "RE3", False),
        # other feeds keep the exact match only
        ("de-VBB_de:vbb:RE1:_106", 106, "RE1", "de-VBB_de:vbb:RE1:_100", "RE1", False),
        ("dk-rejseplanen_16448_106", 106, "A", "dk-rejseplanen_16448_100", "A", False),
        # unknown or "other" route types never match
        (
            "de-DELFI_de:mvv:X1:_1700",
            1700,
            "X1",
            "de-DELFI_de:mvv:X1:_1702",
            "X1",
            False,
        ),
    ],
)
def test_route_id_matches(
    *, api_id, route_type, api_name, stored, stored_name, expected
):
    """The route type suffix of a changed route ID is ignored only if safe."""
    assert (
        route_id_matches(api_id, stored, route_type, api_name, stored_name) is expected
    )


@pytest.mark.parametrize(
    ("route_type", "expected"),
    [
        (100, "regional"),
        (106, "regional"),
        ("106", "regional"),
        (101, "high_speed"),
        (102, "long_distance"),
        (3, "bus"),
        (700, "bus"),
        (714, "bus"),
        (715, "on_demand"),
        (12, None),
        (1700, None),
        (9999, None),
        (None, None),
        ("x", None),
    ],
)
def test_vehicle_class(route_type, expected):
    """Route types map to the vehicle classes of the Transitous backend."""
    assert vehicle_class(route_type) == expected
