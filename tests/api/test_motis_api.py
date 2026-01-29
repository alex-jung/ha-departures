"""Tests for the Motis API client."""

import pytest
from aiohttp import ClientError, ClientResponseError
from aioresponses import aioresponses

from custom_components.ha_departures.api.data_classes import API_COMMAND
from custom_components.ha_departures.api.motis_api import MotisApi


@pytest.fixture
def mock_api():  # noqa: D103
    return MotisApi(base_url="http://test.api")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command"),
    [
        (API_COMMAND.STOPS),
        (API_COMMAND.STOP_TIMES),
        (API_COMMAND.ONE_TO_ALL),
        (API_COMMAND.REVERSE_GEOCODE),
    ],
)
async def test_get_success(mock_api, command):  # noqa: D103
    params = {"param1": "value1"}
    mock_response = {"data": "value"}

    with aioresponses() as mocked:
        mocked.get(
            f"http://test.api/{command.value}?param1=value1",
            payload=mock_response,
            status=200,
        )

        result = await mock_api.get(command, params)

    assert result == mock_response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command"),
    [
        (API_COMMAND.STOPS),
        (API_COMMAND.STOP_TIMES),
        (API_COMMAND.ONE_TO_ALL),
        (API_COMMAND.REVERSE_GEOCODE),
    ],
)
async def test_get_http_error(mock_api, command):  # noqa: D103
    params = {"param1": "value1"}

    with aioresponses() as mocked:
        mocked.get(
            f"http://test.api/{command.value}?param1=value1",
            status=404,
        )

        with pytest.raises(ClientResponseError):
            await mock_api.get(command, params)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command"),
    [
        (API_COMMAND.STOPS),
        (API_COMMAND.STOP_TIMES),
        (API_COMMAND.ONE_TO_ALL),
        (API_COMMAND.REVERSE_GEOCODE),
    ],
)
async def test_get_network_error(mock_api, command):  # noqa: D103
    params = {"param1": "value1"}

    with aioresponses() as mocked:
        mocked.get(
            f"http://test.api/{command.value}?param1=value1",
            exception=ClientError("boom"),
        )

        with pytest.raises(ClientError):
            await mock_api.get(command, params, retry=0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command"),
    [
        (API_COMMAND.STOPS),
        (API_COMMAND.STOP_TIMES),
        (API_COMMAND.ONE_TO_ALL),
        (API_COMMAND.REVERSE_GEOCODE),
    ],
)
async def test_get_max_retries_exceeded(mock_api, command):  # noqa: D103
    params = {"param1": "value1"}

    with aioresponses() as mocked:
        mocked.get(
            f"http://test.api/{command.value}?param1=value1",
            status=404,
        )
        mocked.get(
            f"http://test.api/{command.value}?param1=value1",
            status=404,
        )

        with pytest.raises(ClientResponseError):
            await mock_api.get(command, params, retry=1)  # Set retry to 1 for testing
