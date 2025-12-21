"""Tests for the config flow of the integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from apyefa import Line, Location
from apyefa.exceptions import EfaConnectionError, EfaResponseInvalid
from homeassistant import config_entries

from custom_components.ha_departures.const import (
    CONF_ENDPOINT,
    CONF_ERROR_CONNECTION_FAILED,
    CONF_ERROR_INVALID_RESPONSE,
    CONF_ERROR_NO_STOP_FOUND,
    CONF_HUB_NAME,
    CONF_LINES,
    CONF_STOP_NAME,
    DOMAIN,
    EFA_ENDPOINTS,
)
from custom_components.ha_departures.helper import line_hash


def mock_efa_client(stops=None, lines=None):
    """Create a mock EfaClient."""
    client = AsyncMock()
    client.locations_by_name.return_value = stops or []
    client.lines_by_location.return_value = lines or []

    efa = AsyncMock()
    efa.__aenter__.return_value = client
    efa.__aexit__.return_value = None
    return efa


def make_location(id_: str, name: str, coord=(0.0, 0.0)):
    """Create a mock Location object."""
    loc = Mock(spec=Location)
    loc.id = id_
    loc.name = name
    loc.coord = coord
    return loc


def make_line(id_: str, name: str, dest_id: str, dest_name: str):
    """Create a mock Line object."""
    line = Mock(spec=Line)
    line.id = id_
    line.name = name
    line.destination = Mock(spec=Location)
    line.destination.id = dest_id
    line.destination.name = dest_name
    line.destination.type = "stop"

    # simulate .to_dict() used when persisting
    line.to_dict.return_value = {
        "id": id_,
        "name": name,
        "destination": {"id": dest_id, "name": dest_name, "type": "stop"},
        "product": {"class": 1},
    }
    return line


async def create_config_entry(hass):
    """Create a config entry via the config flow."""
    stop = make_location("stop_1", "Test Stop")
    line = make_line("line_1", "S1", "dest_1", "Hauptbahnhof")

    with patch(
        "custom_components.ha_departures.config_flow.EfaClient",
        return_value=mock_efa_client(
            stops=[stop],
            lines=[line],
        ),
    ):
        # STEP 1: user
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

        # STEP 2: submit endpoint + stop name
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ENDPOINT: EFA_ENDPOINTS["General EFA"],
                CONF_STOP_NAME: stop.name,
            },
        )

        # STEP 3: choose stop
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STOP_NAME: stop.id,
            },
        )

        # STEP 4: choose lines
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LINES: [line_hash(line)],
            },
        )

        # STEP 5: hub name
        return await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HUB_NAME: "Mein Hub",
            },
        )


async def test_config_flow_init(hass):
    """Test the first step of the config flow."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_config_flow_success(hass):
    """Test the entire config flow."""

    stop = make_location("stop_1", "Test Stop")
    line = make_line("line_1", "S1", "dest_1", "Hauptbahnhof")

    with patch(
        "custom_components.ha_departures.config_flow.EfaClient",
        return_value=mock_efa_client(
            stops=[stop],
            lines=[line],
        ),
    ):
        # STEP 1: user
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # STEP 2: submit endpoint + stop name
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ENDPOINT: EFA_ENDPOINTS["General EFA"],
                CONF_STOP_NAME: stop.name,
            },
        )

        assert result["step_id"] == "stop"

        # STEP 3: choose stop
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STOP_NAME: stop.id,
            },
        )

        assert result["step_id"] == "lines"

        # STEP 4: choose lines
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LINES: [line_hash(line)],
            },
        )

        assert result["step_id"] == "hubname"

        # STEP 5: hub name
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HUB_NAME: "Mein Hub",
            },
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "Mein Hub"
        assert result["data"]["stop_id"] == stop.id
        assert result["data"]["api_url"] == EFA_ENDPOINTS["General EFA"]
        assert len(result["data"]["lines"]) == 1
        assert result["data"]["lines"][0]["id"] == line.id


async def test_config_flow_step_user_no_stop_found(hass):
    """Test the first step of the config flow."""
    with patch(
        "custom_components.ha_departures.config_flow.EfaClient",
        return_value=mock_efa_client(stops=[]),
    ):
        result = await hass.config_entries.flow.async_init(
            "ha_departures",
            context={"source": config_entries.SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "endpoint": EFA_ENDPOINTS["General EFA"],
                "stop_name": "Unknown",
            },
        )

    assert result["type"] == "form"
    assert result["errors"] == {CONF_ERROR_NO_STOP_FOUND: CONF_ERROR_NO_STOP_FOUND}


@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (EfaConnectionError("fail"), CONF_ERROR_CONNECTION_FAILED),
        (EfaResponseInvalid("bad"), CONF_ERROR_INVALID_RESPONSE),
    ],
)
async def test_config_flow_step_user_connection_error(hass, exception, expected_error):
    """Test the first step of the config flow."""

    efa = AsyncMock()
    efa.__aenter__.side_effect = exception

    with patch(
        "custom_components.ha_departures.config_flow.EfaClient",
        return_value=efa,
    ):
        result = await hass.config_entries.flow.async_init(
            "ha_departures",
            context={"source": config_entries.SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "endpoint": EFA_ENDPOINTS["General EFA"],
                "stop_name": "Test",
            },
        )

    assert result["errors"] == {expected_error: expected_error}


async def test_config_flow_step_user_invalid_response(hass):
    """Test the first step of the config flow."""
    efa = AsyncMock()
    efa.__aenter__.side_effect = EfaResponseInvalid("bad")

    with patch(
        "custom_components.ha_departures.config_flow.EfaClient",
        return_value=efa,
    ):
        result = await hass.config_entries.flow.async_init(
            "ha_departures",
            context={"source": config_entries.SOURCE_USER},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "endpoint": EFA_ENDPOINTS["General EFA"],
                "stop_name": "Test",
            },
        )

    assert result["errors"] == {
        CONF_ERROR_INVALID_RESPONSE: CONF_ERROR_INVALID_RESPONSE
    }


async def test_abort_duplicate_unique_id(hass):
    """Test that duplicate hub_name aborts the flow."""
    with patch(
        "custom_components.ha_departures.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        # 1. Create first flow
        result = await create_config_entry(hass)

        # 2. Create second flow (same hub_name)
        result = await create_config_entry(hass)

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_options_abort_no_changes(hass):
    """Test that options flow aborts when no changes are made."""
    line = make_line("line_1", "S1", "dest_1", "Hauptbahnhof")

    with patch(
        "custom_components.ha_departures.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        # Create config entry
        results = await create_config_entry(hass)

        # Start options flow
        with patch(
            "custom_components.ha_departures.config_flow.EfaClient",
            return_value=mock_efa_client(
                stops=[],
                lines=[line],
            ),
        ):
            result = await hass.config_entries.options.async_init(
                results["result"].entry_id
            )

            assert result["type"] == "form"
            assert result["step_id"] == "init"

            # Submit same data
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_LINES: [line_hash(line)],
                },
            )

            assert result["type"] == "abort"
            assert result["reason"] == "no_changes_configured"


async def test_options_add_line(hass):
    """Test that options flow aborts when no changes are made."""
    line_1 = make_line("line_1", "S1", "dest_1", "Hauptbahnhof")
    line_2 = make_line("line_2", "S2", "dest_2", "Plaerrer")

    with patch(
        "custom_components.ha_departures.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        # Create config entry
        results = await create_config_entry(hass)

        # Start options flow
        with patch(
            "custom_components.ha_departures.config_flow.EfaClient",
            return_value=mock_efa_client(
                stops=[],
                lines=[line_1, line_2],
            ),
        ):
            result = await hass.config_entries.options.async_init(
                results["result"].entry_id
            )

            assert result["type"] == "form"
            assert result["step_id"] == "init"

            # Submit same data
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_LINES: [line_hash(line_1), line_hash(line_2)],
                },
            )

            assert result["type"] == "create_entry"
            updated_entry = hass.config_entries.async_get_entry(
                results["result"].entry_id
            )

            assert len(updated_entry.data["lines"]) == 2


async def test_options_remove_line(hass):
    """Test that options flow aborts when no changes are made."""
    line_1 = make_line("line_1", "S1", "dest_1", "Hauptbahnhof")

    with patch(
        "custom_components.ha_departures.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        # Create config entry
        results = await create_config_entry(hass)

        # Start options flow
        with patch(
            "custom_components.ha_departures.config_flow.EfaClient",
            return_value=mock_efa_client(
                stops=[],
                lines=[line_1],
            ),
        ):
            result = await hass.config_entries.options.async_init(
                results["result"].entry_id
            )

            assert result["type"] == "form"
            assert result["step_id"] == "init"

            # Submit data with line removed
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_LINES: [],
                },
            )

            assert result["type"] == "create_entry"
            updated_entry = hass.config_entries.async_get_entry(
                results["result"].entry_id
            )

            assert len(updated_entry.data["lines"]) == 0
