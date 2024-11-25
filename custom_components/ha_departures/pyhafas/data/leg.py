import datetime
from .station import Station
from .stopover import Stopover
from .remark import Remark
from .fptf_object import FPTFObject, Mode


class Leg(FPTFObject):
    """
    FPTF `Leg` object

    A leg or also named trip is most times part of a journey and defines a journey with only one specific vehicle from A to B.

    :ivar id: ID of the Leg
    :vartype id: str
    :ivar origin: FPTF `Station` object of the origin station
    :vartype origin: Station
    :ivar destination: FPTF `Station` object of the destination station
    :vartype destination: Station
    :ivar departure: Planned Date and Time of the departure
    :vartype departure: datetime.datetime
    :ivar arrival: Planned Date and Time of the arrival
    :vartype arrival: datetime.datetime
    :ivar mode: Type of transport vehicle - Must be a part of the FPTF `Mode` enum. Defaults to `Mode.TRAIN`
    :vartype mode: Mode
    :ivar name: Name of the trip (e.g. ICE 123) (maybe `None`)
    :vartype name: str | None
    :ivar cancelled: Whether the trip is completely cancelled (not only some stops)
    :vartype cancelled: bool
    :ivar distance: Distance of the walk trip in metres. Only set if `mode` is `Mode.WALKING` otherwise None
    :vartype distance: int | None
    :ivar departureDelay: Delay at the departure station (maybe `None`)
    :vartype departureDelay: datetime.timedelta | None
    :ivar departurePlatform: Real-time platform at the departure station (maybe `None`)
    :vartype departurePlatform: str | None
    :ivar arrivalDelay: Delay at the arrival station (maybe `None`)
    :vartype arrivalDelay: datetime.timedelta | None
    :ivar arrivalPlatform: Real-time platform at the arrival station (maybe `None`)
    :vartype arrivalPlatform: str | None
    :ivar stopovers: List of FPTF `Stopover` objects (maybe `None`)
    :vartype stopovers: Optional[List[Stopover]]
    :ivar remarks: (optional) List of remarks
    :vartype remarks: List[Remark]
    """

    def __init__(
        self,
        id: str,
        origin: Station,
        destination: Station,
        departure: datetime.datetime,
        arrival: datetime.datetime,
        mode: Mode = Mode.TRAIN,
        name: str | None = None,
        cancelled: bool = False,
        distance: int | None = None,
        departure_delay: datetime.timedelta | None = None,
        departure_platform: str | None = None,
        arrival_delay: datetime.timedelta | None = None,
        arrival_platform: str | None = None,
        stopovers: list[Stopover] | None = None,
        remarks: list[Remark] | None = None,
    ):
        """
        FPTF `Leg` object

        :param id: Internal ID of the station
        :param origin: FPTF `Station` object of the origin station
        :param destination: FPTF `Station` object of the destination station
        :param departure: Planned date and Time of the departure
        :param arrival: Planned date and Time of the arrival
        :param mode: (optional) Type of transport vehicle - Must be a part of the FPTF `Mode` enum. Defaults to `Mode.TRAIN`
        :param name: (optional) Name of the trip (e.g. ICE 123). Defaults to None
        :param cancelled: (optional) Whether the trip is cancelled. Defaults to False
        :param distance: (optional) Distance of the walk trip in meters. Defaults to None
        :param departure_delay: (optional) Delay at the departure station. Defaults to None
        :param departure_platform: (optional) Real-time platform at the departure station. Defaults to None
        :param arrival_delay: (optional) Delay at the arrival station. Defaults to None
        :param arrival_platform: (optional) Platform at the arrival station. Defaults to None
        :param stopovers: (optional) List of FPTF `Stopover` objects. Defaults to None
        :param remarks: (optional) List of remarks. Defaults to `[]`
        """
        # Mandatory Variables
        self.id = id
        self.origin: Station = origin
        self.destination: Station = destination
        self.departure: datetime.datetime = departure
        self.arrival: datetime.datetime = arrival

        # Optional Variables
        self.mode: Mode = mode
        self.name: str | None = name
        self.cancelled: bool = cancelled
        self.distance: int | None = distance
        self.departureDelay: datetime.timedelta | None = departure_delay
        self.departurePlatform: str | None = departure_platform
        self.arrivalDelay: datetime.timedelta | None = arrival_delay
        self.arrivalPlatform: str | None = arrival_platform
        self.stopovers: list[Stopover] | None = stopovers
        if remarks is None:
            remarks = []
        self.remarks: list[Remark] = remarks
