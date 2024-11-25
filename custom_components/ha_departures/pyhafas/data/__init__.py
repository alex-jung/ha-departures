from enum import Enum


class StationBoardRequestType(Enum):
    """
    Mapping of StationBoard request from client to HaFAS
    """

    DEPARTURE = "DEP"
    ARRIVAL = "ARR"

    def __repr__(self):
        return "<%s.%s>" % (self.__class__.__name__, self.name)
