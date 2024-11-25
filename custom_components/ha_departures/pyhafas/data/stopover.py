import datetime
from .fptf_object import FPTFObject
from .station import Station
from .remark import Remark


class Stopover(FPTFObject):
    """
    FPTF `Stopover` object

    A stopover represents a vehicle stopping at a stop/station at a specific time.

    :ivar stop: Station where the vehicle is stopping
    :vartype stop: Station
    :ivar cancelled: Whether the stop is cancelled
    :vartype cancelled: bool
    :ivar arrival: Planned arrival date and time at the station (maybe `None`)
    :vartype arrival: datetime.datetime | None
    :ivar arrivalDelay: Arrival delay at the station (maybe `None`)
    :vartype arrivalDelay: datetime.timedelta | None
    :ivar arrivalPlatform: Real-time arrival platform at the station (maybe `None`)
    :vartype arrivalPlatform: str | None
    :ivar departure: Planned departure date and time at the station (maybe `None`)
    :vartype departure: datetime.datetime | None
    :ivar departureDelay: Departure delay at the station (maybe `None`)
    :vartype departureDelay: datetime.timedelta | None
    :ivar departurePlatform: Real-time departure platform at the station (maybe `None`)
    :vartype departurePlatform: str | None
    :ivar remarks: (optional) List of remarks
    :vartype remarks: List[Remark]
    """

    def __init__(
        self,
        stop: Station,
        cancelled: bool = False,
        arrival: datetime.datetime | None = None,
        arrival_delay: datetime.timedelta | None = None,
        arrival_platform: str | None = None,
        departure: datetime.datetime | None = None,
        departure_delay: datetime.timedelta | None = None,
        departure_platform: str | None = None,
        remarks: list[Remark] | None = None,
    ):
        """

        :param stop: Station where the vehicle is stopping
        :param cancelled: (optional) Whether the stop is cancelled. Defaults to `False`
        :param arrival: (optional) Planned arrival date and time at the station. Defaults to `None`
        :param arrival_delay: (optional) Arrival delay at the station. Defaults to `None`
        :param arrival_platform: (optional) Real-time arrival platform at the station. Defaults to `None`
        :param departure: (optional) Planned departure date and time at the station. Defaults to `None`
        :param departure_delay: (optional) Departure delay at the station. Defaults to `None`
        :param departure_platform: (optional) Real-time departure platform at the station. Defaults to `None`
        :param remarks: (optional) List of remarks. Defaults to `[]`
        """
        self.stop: Station = stop
        self.cancelled: bool = cancelled
        self.arrival: datetime.datetime | None = arrival
        self.arrivalDelay: datetime.timedelta | None = arrival_delay
        self.arrivalPlatform: str | None = arrival_platform
        self.departure: datetime.datetime | None = departure
        self.departureDelay: datetime.timedelta | None = departure_delay
        self.departurePlatform: str | None = departure_platform
        if remarks is None:
            remarks = []
        self.remarks: list[Remark] = remarks
