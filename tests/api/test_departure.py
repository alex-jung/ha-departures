"""Tests for the Departure data class."""

from datetime import datetime

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ha_departures.api.data_classes import Departure


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FULL_DICT = {
    "routeId": "route-42",
    "directionId": "0",
    "tripId": "trip-99",
    "headsign": "Hauptbahnhof",
    "realTime": True,
    "cancelled": False,
    "tripCancelled": False,
    "place": {
        "stopId": "stop-7",
        "departure": "2024-06-01T10:30:00+00:00",
        "scheduledDeparture": "2024-06-01T10:28:00+00:00",
        "alerts": [],
    },
}

ALERT_STUB = {"headerText": "Störung", "descriptionText": "Verspätung"}


def _local(iso: str) -> datetime:
    return dt_util.as_local(dt_util.parse_datetime(iso))


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


def test_departure_instantiation_defaults():
    """Departure kann mit Mindestfeldern erzeugt werden; Defaults stimmen."""
    dep = Departure(
        route_id="r1",
        direction_id="0",
        trip_id="t1",
        stop_id="s1",
        departure=None,
        head_sign="Ziel",
        scheduled_departure=None,
        real_time=False,
    )
    assert dep.cancelled is False
    assert dep.trip_cancelled is False
    assert dep.alerts is False


def test_departure_instantiation_all_fields():
    """Departure speichert alle Felder korrekt."""
    dt_now = datetime(2024, 6, 1, 10, 30)
    dep = Departure(
        route_id="r1",
        direction_id="1",
        trip_id="t99",
        stop_id="s5",
        departure=dt_now,
        head_sign="Hauptbahnhof",
        scheduled_departure=dt_now,
        real_time=True,
        cancelled=True,
        trip_cancelled=True,
        alerts=True,
    )
    assert dep.route_id == "r1"
    assert dep.direction_id == "1"
    assert dep.trip_id == "t99"
    assert dep.stop_id == "s5"
    assert dep.departure == dt_now
    assert dep.head_sign == "Hauptbahnhof"
    assert dep.real_time is True
    assert dep.cancelled is True
    assert dep.trip_cancelled is True
    assert dep.alerts is True


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


def test_from_dict_full():
    """from_dict parst ein vollständiges Dictionary korrekt."""
    dep = Departure.from_dict(FULL_DICT)

    assert dep.route_id == "route-42"
    assert dep.direction_id == "0"
    assert dep.trip_id == "trip-99"
    assert dep.stop_id == "stop-7"
    assert dep.head_sign == "Hauptbahnhof"
    assert dep.real_time is True
    assert dep.cancelled is False
    assert dep.trip_cancelled is False


def test_from_dict_parses_departure_time():
    """from_dict wandelt departure-String in lokales datetime um."""
    dep = Departure.from_dict(FULL_DICT)

    assert isinstance(dep.departure, datetime)
    assert dep.departure == _local("2024-06-01T10:30:00+00:00")


def test_from_dict_parses_scheduled_departure():
    """from_dict wandelt scheduledDeparture-String in lokales datetime um."""
    dep = Departure.from_dict(FULL_DICT)

    assert isinstance(dep.scheduled_departure, datetime)
    assert dep.scheduled_departure == _local("2024-06-01T10:28:00+00:00")


def test_from_dict_missing_times():
    """from_dict setzt departure und scheduled_departure auf None wenn nicht vorhanden."""
    data = {**FULL_DICT, "place": {"stopId": "s1"}}
    dep = Departure.from_dict(data)

    assert dep.departure is None
    assert dep.scheduled_departure is None


def test_from_dict_default_ids():
    """from_dict verwendet 'unknown' als Fallback für fehlende IDs."""
    dep = Departure.from_dict({})

    assert dep.route_id == "unknown"
    assert dep.direction_id == "unknown"
    assert dep.trip_id == "unknown"
    assert dep.stop_id == "unknown"


def test_from_dict_default_headsign():
    """from_dict setzt headsign auf leeren String wenn nicht vorhanden."""
    assert Departure.from_dict({}).head_sign == ""


def test_from_dict_real_time_false_by_default():
    """from_dict setzt realTime auf False wenn nicht angegeben."""
    assert Departure.from_dict({}).real_time is False


def test_from_dict_cancelled_false_by_default():
    """from_dict setzt cancelled und tripCancelled auf False wenn nicht angegeben."""
    dep = Departure.from_dict({})

    assert dep.cancelled is False
    assert dep.trip_cancelled is False


def test_from_dict_cancelled_true():
    """from_dict liest cancelled=True und tripCancelled=True korrekt aus."""
    data = {**FULL_DICT, "cancelled": True, "tripCancelled": True}
    dep = Departure.from_dict(data)

    assert dep.cancelled is True
    assert dep.trip_cancelled is True


def test_from_dict_alerts_false_when_empty():
    """alerts ist False wenn die API eine leere Liste liefert."""
    dep = Departure.from_dict(FULL_DICT)

    assert dep.alerts is False


def test_from_dict_alerts_true_when_non_empty():
    """alerts ist True wenn die API mindestens einen Alert enthält."""
    data = {**FULL_DICT, "place": {**FULL_DICT["place"], "alerts": [ALERT_STUB]}}
    dep = Departure.from_dict(data)

    assert dep.alerts is True


def test_from_dict_alerts_true_with_multiple():
    """alerts ist True bei mehreren Alerts."""
    data = {
        **FULL_DICT,
        "place": {**FULL_DICT["place"], "alerts": [ALERT_STUB, ALERT_STUB]},
    }
    dep = Departure.from_dict(data)

    assert dep.alerts is True


def test_from_dict_alerts_false_when_missing():
    """alerts ist False wenn der alerts-Key fehlt."""
    dep = Departure.from_dict({})

    assert dep.alerts is False


def test_from_dict_empty_dict():
    """from_dict verarbeitet ein leeres Dictionary ohne Exception."""
    assert isinstance(Departure.from_dict({}), Departure)


# ---------------------------------------------------------------------------
# __hash__
# ---------------------------------------------------------------------------


def test_hash_identical_departures_equal():
    """Zwei Departures mit gleichen Schlüsselfeldern haben denselben Hash."""
    assert hash(Departure.from_dict(FULL_DICT)) == hash(Departure.from_dict(FULL_DICT))


def test_hash_different_route_id():
    """Departures mit unterschiedlicher routeId haben verschiedene Hashes."""
    dep_a = Departure.from_dict({**FULL_DICT, "routeId": "route-A"})
    dep_b = Departure.from_dict({**FULL_DICT, "routeId": "route-B"})

    assert hash(dep_a) != hash(dep_b)


def test_hash_different_direction_id():
    """Departures mit unterschiedlicher directionId haben verschiedene Hashes."""
    dep_a = Departure.from_dict({**FULL_DICT, "directionId": "0"})
    dep_b = Departure.from_dict({**FULL_DICT, "directionId": "1"})

    assert hash(dep_a) != hash(dep_b)


def test_hash_different_trip_id():
    """Departures mit unterschiedlicher tripId haben verschiedene Hashes."""
    dep_a = Departure.from_dict({**FULL_DICT, "tripId": "trip-1"})
    dep_b = Departure.from_dict({**FULL_DICT, "tripId": "trip-2"})

    assert hash(dep_a) != hash(dep_b)


def test_hash_different_departure_time():
    """Departures mit unterschiedlicher Abfahrtszeit haben verschiedene Hashes."""
    place_a = {**FULL_DICT["place"], "departure": "2024-06-01T10:30:00+00:00"}
    place_b = {**FULL_DICT["place"], "departure": "2024-06-01T11:00:00+00:00"}

    dep_a = Departure.from_dict({**FULL_DICT, "place": place_a})
    dep_b = Departure.from_dict({**FULL_DICT, "place": place_b})

    assert hash(dep_a) != hash(dep_b)


def test_hash_usable_in_set():
    """Departure-Objekte können in einem Set verwendet werden; Duplikate werden entfernt."""
    dep1 = Departure.from_dict(FULL_DICT)
    dep2 = Departure.from_dict(FULL_DICT)
    dep3 = Departure.from_dict({**FULL_DICT, "tripId": "trip-other"})

    assert len({dep1, dep2, dep3}) == 2


def test_hash_usable_as_dict_key():
    """Departure-Objekte können als Dictionary-Schlüssel verwendet werden."""
    dep = Departure.from_dict(FULL_DICT)
    mapping = {dep: "value"}

    assert mapping[dep] == "value"
