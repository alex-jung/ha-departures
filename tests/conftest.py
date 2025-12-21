"""Tests conftest file for ha_departures integration."""

from unittest.mock import MagicMock, Mock

from apyefa import Line, Location, TransportType


def create_mock_coordinator(data=None):
    """Create a mock DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.data = data or {}
    coordinator.last_update_success = True
    coordinator.hub_name = "Mock Hub"
    coordinator.async_request_refresh = MagicMock()
    coordinator.stop_name = "Mock Stop"
    coordinator.stop_coord = (0.0, 0.0)

    return coordinator


def create_mock_line():
    """Create a mock Line object."""
    line = Mock(spec=Line)
    line.product = TransportType.CITY_BUS
    line.name = "Test Line"
    line.id = "line-123"
    line.destination = Mock(spec=Location)
    line.destination.id = "dest-456"
    line.destination.name = "Test Destination"

    return line
