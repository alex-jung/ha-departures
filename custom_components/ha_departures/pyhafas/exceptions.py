class ProductNotAvailableError(Exception):
    """Requested Product is not available in profile"""
    pass


class GeneralHafasError(Exception):
    """HaFAS returned an general error"""
    pass


class AuthenticationError(Exception):
    """Authentiction data missing or wrong"""
    pass


class AccessDeniedError(Exception):
    """Access is denied"""
    pass


class LocationNotFoundError(Exception):
    """Location/stop not found"""
    pass


class JourneysTooManyTrainsError(Exception):
    """Journeys search: Too many trains, connection is not complete"""
    pass


class JourneysArrivalDepartureTooNearError(Exception):
    """Journeys search: arrival and departure date are too near"""
    pass


class NoDepartureArrivalDataError(Exception):
    """No departure/arrival data available"""
    pass


class TripDataNotFoundError(Exception):
    """No trips found or trip info not available"""
