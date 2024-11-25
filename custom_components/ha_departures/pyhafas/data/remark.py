from .fptf_object import FPTFObject


class Remark(FPTFObject):
    """
    A remark is a textual comment/information, usually added to a Stopover or Leg

    :ivar remark_type: Type/Category of the remark. May have a different meaning depending on the network
    :vartype remark_type: str | None
    :ivar code: Code of the remark. May have a different meaning depending on the network
    :vartype code: str | None
    :ivar subject: Subject of the remark
    :vartype subject: str | None
    :ivar text: Actual content of the remark
    :vartype text: str | None
    :ivar priority: Priority of the remark, higher is better
    :vartype priority: int | None
    :ivar trip_id: ID to a Trip added to this remark (e.g. a replacement train)
    :vartype trip_id: str | None
    """

    def __init__(
        self,
        remark_type: str | None = None,
        code: str | None = None,
        subject: str | None = None,
        text: str | None = None,
        priority: int | None = None,
        trip_id: str | None = None,
    ):
        """

        :param remark_type: Type/Category of the remark. May have a different meaning depending on the network
        :param code: Code of the remark. May have a different meaning depending on the network
        :param subject: Subject of the remark
        :param text: Actual content of the remark
        :param priority: Priority of the remark, higher is better
        :param trip_id: ID to a Trip added to this remark (e.g. a replacement train)
        """
        self.remark_type: str | None = remark_type
        self.code: str | None = code
        self.subject: str | None = subject
        self.text: str | None = text
        self.priority: int | None = priority
        self.trip_id: str | None = trip_id
