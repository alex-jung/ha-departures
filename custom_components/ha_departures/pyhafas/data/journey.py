import datetime
from .fptf_object import FPTFObject
from .leg import Leg


class Journey(FPTFObject):
    """
    FPTF `Journey` object

    A journey is a computed set of directions to get from A to B at a specific time. It would typically be the result of a route planning algorithm.

    :ivar id: ID of the Journey
    :vartype id: str
    :ivar date: Starting date of the journey (maybe `None`)
    :vartype date: Optional[datetime.date]
    :ivar duration: Duration of the complete journey (maybe `None`)
    :vartype duration: datetime.timedelta | None
    :ivar legs: Longitude coordinate of the Station (maybe `None`)
    :vartype legs: Optional[List[Leg]]
    """

    def __init__(
        self,
        id: str,
        date: datetime.date | None = None,
        duration: datetime.timedelta | None = None,
        legs: list[Leg] | None = None,
    ):
        """
        FPTF `Journey` object

        :param id: Internal ID of the station
        :param date: (optional) Name of the station
        :param duration: (optional) Latitude coordinate of the station. Defaults to None
        :param legs: (optional) Longitude coordinate of the station. Defaults to None
        """
        self.id: str = id
        self.date: datetime.date | None = date
        self.duration: datetime.timedelta | None = duration
        self.legs: list[Leg] | None = legs
