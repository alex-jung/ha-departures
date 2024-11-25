import datetime
from .fptf_object import FPTFObject
from .station import Station


class StationBoardLeg(FPTFObject):
    """
    `StationBoardLeg` object

    Returned at Station Board-Requests. This requests do not have enough information for a FPTF `Leg` object.
    With the ID a `trip` request can be made to get detailed information about the trip

    :ivar id: ID of the Leg
    :vartype id: str
    :ivar name: Name of the trip (e.g. ICE 123)
    :vartype name: str
    :ivar station: FPTF `Station` object of the departing/arriving station
    :vartype station: Station
    :ivar date_time: Planned Date and Time of the departure/arrival
    :vartype date_time: datetime.datetime
    :ivar cancelled: Whether the stop or trip cancelled
    :vartype cancelled: bool
    :ivar direction: Direction text of the trip (e.g. Berlin Central Station)
    :vartype direction: str | None
    :ivar delay: Delay at the departure station (maybe `None`)
    :vartype delay: datetime.timedelta | None
    :ivar platform: Real-time platform at the station (maybe `None`)
    :vartype platform: str | None
    """

    def __init__(
        self,
        id: str,
        name: str,
        station: Station,
        date_time: datetime.datetime,
        cancelled: bool,
        direction: str | None = None,
        delay: datetime.timedelta | None = None,
        platform: str | None = None,
    ):
        """
        `StationBoardLeg` object

        :param id: ID of the Leg
        :param name: Name of the trip (e.g. ICE 123)
        :param station: FPTF `Station` object of the departing/arriving station
        :param date_time: Planned Date and Time of the departure/arrival
        :param cancelled: Whether the stop or trip cancelled
        :param direction: (optional) Direction text of the trip (e.g. Berlin Central Station)
        :param delay: (optional) Delay at the departure station. Defaults to `None`
        :param platform: (optional) Real-time platform at the station. Defaults to `None`
        """
        self.id: str = id
        self.name: str = name
        self.station: Station = station
        self.dateTime: datetime.datetime = date_time
        self.cancelled: bool = cancelled
        self.direction: str | None = direction
        self.delay: datetime.timedelta | None = delay
        self.platform: str | None = platform
