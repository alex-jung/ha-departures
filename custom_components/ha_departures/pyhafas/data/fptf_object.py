from enum import Enum


class Mode(Enum):
    """
    FPTF `Mode` object

    The mode of a `Leg` specifies the general type of transport vehicle (it can also be a walking leg)
    """

    TRAIN = "train"
    BUS = "bus"
    WATERCRAFT = "watercraft"
    TAXI = "taxi"
    GONDOLA = "gondola"
    AIRCRAFT = "aircraft"
    CAR = "car"
    BICYCLE = "bicycle"
    WALKING = "walking"

    def __repr__(self):
        return "<%s.%s>" % (self.__class__.__name__, self.name)


class FPTFObject:
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
