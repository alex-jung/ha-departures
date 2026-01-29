"""Custom exceptions for the HA Departures API client."""


class RequestMaximumRetriesExceeded(Exception):
    """Exception raised when maximum retries for a request are exceeded."""
