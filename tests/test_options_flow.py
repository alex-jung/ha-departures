"""Tests for the line selection of the options flow."""

from unittest.mock import Mock

import pytest

from custom_components.ha_departures.api.data_classes import Line, TransportMode
from custom_components.ha_departures.config_flow import (
    DeparturesFlowHandler,
    DeparturesOptionsFlowHandler,
    _extract_lines_from_stop_times,
    _line_label,
    _preselect_lines,
)
from custom_components.ha_departures.const import CONF_AVAILABLE_LINES, CONF_LINES

RAIL = TransportMode.REGIONAL_RAIL
BUS = TransportMode.BUS


def _line(route_id, name="RE3", direction="0", mode=RAIL, route_type=None):
    return Line(
        route_id=route_id,
        direction_id=direction,
        head_sign="München Hbf",
        route_short_name=name,
        mode=mode,
        route_type=route_type,
    )


STORED_RE3 = _line("de-DELFI_de:beg:RE3:_100")
API_RE3 = _line("de-DELFI_de:beg:RE3:_106", route_type=106)


def test_extract_lines_keeps_route_type():
    """Lines from the API carry the route type, it is not stored."""
    lines = _extract_lines_from_stop_times(
        {
            "stopTimes": [
                {
                    "routeId": "de-DELFI_de:beg:RE3:_106",
                    "directionId": "0",
                    "headsign": "München Hbf",
                    "routeShortName": "RE3",
                    "mode": "REGIONAL_RAIL",
                    "routeType": 106,
                }
            ]
        }
    )

    assert lines[0].route_type == 106
    assert "route_type" not in lines[0].to_dict()


def test_exact_line_is_preselected():
    """A line whose route ID is offered as stored is preselected as before."""
    defaults, keep = _preselect_lines([API_RE3], [API_RE3])

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert keep == {}


def test_prefixless_line_migrates_as_before():
    """Old IDs without feed prefix still migrate to the offered ID."""
    stored = _line("de:beg:RE3:_106")
    defaults, keep = _preselect_lines([stored], [API_RE3])

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert keep == {}


def test_changed_route_type_is_preselected_and_kept():
    """A line whose route type suffix changed is preselected, the stored line is kept."""
    defaults, keep = _preselect_lines([STORED_RE3], [API_RE3])

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert keep == {"de-DELFI_de:beg:RE3:_106---0": STORED_RE3}
    assert keep["de-DELFI_de:beg:RE3:_106---0"].route_id == "de-DELFI_de:beg:RE3:_100"


def test_train_line_is_not_preselected_as_bus():
    """A replacement bus of the same name is no successor of a train line."""
    bus = _line("de-DELFI_de:beg:RE3:_3", mode=BUS, route_type=3)
    defaults, keep = _preselect_lines([STORED_RE3], [bus])

    assert defaults == []
    assert keep == {}


@pytest.mark.parametrize(
    "available",
    [
        _line("de-DELFI_de:beg:RE3:_106", direction="1", route_type=106),
        _line("de-DELFI_de:beg:RE3:_106", name="RE30", route_type=106),
        _line("vbb_de:beg:RE3:_106", route_type=106),
    ],
    ids=["other-direction", "other-name", "other-feed"],
)
def test_changed_route_type_needs_same_line(available):
    """Direction, short name and the DELFI feed must match."""
    assert _preselect_lines([STORED_RE3], [available]) == ([], {})


def test_changed_route_type_needs_reported_route_type():
    """The route type the API reports for the offered line decides, not its ID."""
    offered = _line("de-DELFI_de:beg:RE3:_106", route_type=100)

    assert _preselect_lines([STORED_RE3], [offered]) == ([], {})


def test_prefixless_line_wins_over_changed_line():
    """A prefixless stored line keeps its migration, the changed duplicate is not added."""
    prefixless = _line("de:beg:RE3:_106")

    for selected in ([STORED_RE3, prefixless], [prefixless, STORED_RE3]):
        defaults, keep = _preselect_lines(selected, [API_RE3])

        assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
        assert keep == {}


def test_changed_line_does_not_take_a_configured_line():
    """An offered line that is configured itself is not taken by another line."""
    configured_106 = _line("de-DELFI_de:beg:RE3:_106")
    defaults, keep = _preselect_lines([STORED_RE3, configured_106], [API_RE3])

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert keep == {}


def _flow(selected, available):
    entry = Mock(
        options={CONF_LINES: [x.to_dict() for x in selected]},
        data={CONF_AVAILABLE_LINES: [x.to_dict() for x in available]},
    )
    flow = DeparturesOptionsFlowHandler(entry)
    flow.flow_id = "flow"
    flow.handler = "ha_departures"
    flow._lines_available = available
    return flow


async def test_saving_keeps_stored_route_id():
    """Saving with the changed line selected keeps the stored line (same unique ID)."""
    other = _line("de-DELFI_de:beg:RE2:_106", name="RE2", route_type=106)
    flow = _flow([STORED_RE3], [API_RE3, other])
    flow._lines_kept = {"de-DELFI_de:beg:RE3:_106---0": STORED_RE3}

    result = await flow.async_step_init(
        {CONF_LINES: ["de-DELFI_de:beg:RE3:_106---0", "de-DELFI_de:beg:RE2:_106---0"]}
    )

    assert [x["route_id"] for x in result["data"][CONF_LINES]] == [
        "de-DELFI_de:beg:RE3:_100",
        "de-DELFI_de:beg:RE2:_106",
    ]


async def test_saving_unchanged_changed_line_reports_no_changes():
    """Leaving the preselected changed line as it is changes nothing."""
    flow = _flow([STORED_RE3], [API_RE3])
    flow._lines_kept = {"de-DELFI_de:beg:RE3:_106---0": STORED_RE3}

    result = await flow.async_step_init({CONF_LINES: ["de-DELFI_de:beg:RE3:_106---0"]})

    assert result["type"] == "abort"


async def test_deselecting_changed_line_removes_it():
    """Deselecting the changed line removes it like any other line."""
    other = _line("de-DELFI_de:beg:RE2:_106", name="RE2", route_type=106)
    flow = _flow([STORED_RE3, other], [API_RE3, other])
    flow._lines_kept = {"de-DELFI_de:beg:RE3:_106---0": STORED_RE3}

    result = await flow.async_step_init({CONF_LINES: ["de-DELFI_de:beg:RE2:_106---0"]})

    assert [x["route_id"] for x in result["data"][CONF_LINES]] == [
        "de-DELFI_de:beg:RE2:_106"
    ]


async def test_open_and_save_keeps_changed_line(monkeypatch):
    """Opening the options preselects the changed line, saving keeps its stored ID."""

    async def fetch(*_args, **_kwargs):
        return [API_RE3]

    monkeypatch.setattr(
        "custom_components.ha_departures.config_flow._fetch_lines", fetch
    )
    flow = _flow([STORED_RE3], [STORED_RE3])
    flow.hass = Mock()
    flow.hass.config_entries.async_get_known_entry.return_value = Mock(
        data={CONF_AVAILABLE_LINES: [STORED_RE3.to_dict()]}
    )

    form = await flow.async_step_init()
    defaults = next(
        key.default() for key in form["data_schema"].schema if key == CONF_LINES
    )
    result = await flow.async_step_init({CONF_LINES: defaults})

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert result["type"] == "abort"


def test_same_line_stored_twice_is_preselected_once():
    """A line stored with and without feed prefix gives one preselected value."""
    defaults, keep = _preselect_lines([_line("de:beg:RE3:_106"), API_RE3], [API_RE3])

    assert defaults == ["de-DELFI_de:beg:RE3:_106---0"]
    assert keep == {}


@pytest.mark.parametrize(
    ("line", "label"),
    [
        (API_RE3, "🚆 RE3 - München Hbf"),
        (_line("x_3", name="RB45", mode=BUS, route_type=3), "🚌 RB45 - München Hbf"),
        (
            _line(
                "x_101",
                name="ICE 25",
                mode=TransportMode.HIGHSPEED_RAIL,
                route_type=101,
            ),
            "🚄 ICE 25 - München Hbf",
        ),
        # the route type of the route decides, not the mode of a single trip
        (
            _line("x_106", mode=TransportMode.HIGHSPEED_RAIL, route_type=106),
            "🚆 RE3 - München Hbf",
        ),
        # without route type the mode is used
        (_line("x", name="607", mode=BUS), "🚌 607 - München Hbf"),
        (_line("x", mode=TransportMode.TRAM), "🚊 RE3 - München Hbf"),
        # METRO is the old API name of SUBURBAN, not a subway
        (_line("x", name="S1", mode=TransportMode.METRO), "🚆 S1 - München Hbf"),
        (_line("x", name="RUF", mode=TransportMode.ODM), "🚐 RUF - München Hbf"),
        # unknown kind of vehicle: no symbol
        (_line("x", mode=TransportMode.OTHER, route_type=1700), "RE3 - München Hbf"),
    ],
)
def test_line_label_shows_vehicle(line, label):
    """The selector shows the kind of vehicle in front of the line."""
    assert _line_label(line) == label


async def test_options_show_vehicle_symbol(monkeypatch):
    """Train and replacement bus of the same name differ in the options."""
    bus = _line("de-DELFI_2230866_3", name="RE3", mode=BUS, route_type=3)

    async def fetch(*_args, **_kwargs):
        return [API_RE3, bus]

    monkeypatch.setattr(
        "custom_components.ha_departures.config_flow._fetch_lines", fetch
    )
    flow = _flow([API_RE3], [API_RE3])
    flow.hass = Mock()
    flow.hass.config_entries.async_get_known_entry.return_value = Mock(
        data={CONF_AVAILABLE_LINES: [API_RE3.to_dict()]}
    )

    form = await flow.async_step_init()
    selector = next(iter(form["data_schema"].schema.values()))
    labels = {o["value"]: o["label"] for o in selector.config["options"]}

    assert labels == {
        "de-DELFI_de:beg:RE3:_106---0": "🚆 RE3 - München Hbf",
        "de-DELFI_2230866_3---0": "🚌 RE3 - München Hbf",
    }


async def test_setup_shows_vehicle_symbol(monkeypatch):
    """Adding a hub shows the kind of vehicle in front of the line, too."""
    bus = _line("de-DELFI_2230866_3", name="RE3", mode=BUS, route_type=3)

    async def fetch(*_args, **_kwargs):
        return [API_RE3, bus]

    monkeypatch.setattr(
        "custom_components.ha_departures.config_flow._fetch_lines", fetch
    )
    flow = DeparturesFlowHandler()
    flow.flow_id = "flow"
    flow.handler = "ha_departures"

    form = await flow.async_step_lines()
    selector = next(iter(form["data_schema"].schema.values()))

    assert sorted(o["label"] for o in selector.config["options"]) == [
        "🚆 RE3 - München Hbf",
        "🚌 RE3 - München Hbf",
    ]
