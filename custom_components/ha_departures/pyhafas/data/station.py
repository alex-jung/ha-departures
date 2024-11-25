from .fptf_object import FPTFObject


class Station(FPTFObject):
    """
    FPTF `Station` object

    A station is a point where vehicles stop. It may be a larger building or just a small stop without special infrastructure.

    :ivar id: ID of the Station. Typically a number but as a string
    :vartype id: str
    :ivar lid: Location ID of the Station (maybe `None`). Long-form, containing multiple fields
    :vartype lid: str | None
    :ivar name: Name of the Station (maybe `None`)
    :vartype name: str | None
    :ivar latitude: Latitude coordinate of the Station (maybe `None`)
    :vartype latitude: float | None
    :ivar longitude: Longitude coordinate of the Station (maybe `None`)
    :vartype longitude: float | None
    """

    def __init__(
        self,
        id: str,
        lid: str | None = None,
        name: str | None = None,
        latitude: str | None = None,
        longitude: str | None = None,
    ):
        """
        FPTF `Station` object

        :param id: Internal ID of the station
        :param lid: (optional) Internal Location ID of the station. Defaults to None
        :param name: (optional) Name of the station. Defaults to None
        :param latitude: (optional) Latitude coordinate of the station. Defaults to None
        :param longitude: (optional) Longitude coordinate of the station. Defaults to None
        """
        self.id: str = id
        self.lid: str | None = lid
        self.name: str | None = name
        self.latitude: float | None = latitude
        self.longitude: float | None = longitude
