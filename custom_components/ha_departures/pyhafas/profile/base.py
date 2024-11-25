import datetime
from hashlib import md5
import json
from zoneinfo import ZoneInfo

import aiohttp

from ..data.hafas_response import HafasResponse
from ..data.leg import Leg
from ..data.stopover import Stopover
from ..data.fptf_object import Mode
from ..data.station import Station
from ..error_codes import ErrorCodesMappingInterface
from ..exceptions import (
    AccessDeniedError,
    AuthenticationError,
    GeneralHafasError,
    JourneysArrivalDepartureTooNearError,
    JourneysTooManyTrainsError,
    LocationNotFoundError,
    TripDataNotFoundError,
)
from .mixins import (
    MixinDateTime,
    MixinLocationRequest,
    MixinParseLid,
    MixinBoardStation,
    MixinTrip,
)


class BaseErrorCodesMapping(ErrorCodesMappingInterface):
    """Mapping of the HaFAS error code to the exception class.

    `default` defines the error when the error code cannot be found in the mapping
    """

    default = GeneralHafasError
    AUTH = AuthenticationError
    R5000 = AccessDeniedError
    LOCATION = LocationNotFoundError
    H500 = JourneysTooManyTrainsError
    H890 = JourneysArrivalDepartureTooNearError
    SQ005 = TripDataNotFoundError
    TI001 = TripDataNotFoundError


class BaseProfile(
    MixinLocationRequest, MixinParseLid, MixinDateTime, MixinBoardStation, MixinTrip
):
    """Profile for a "normal" HaFAS. Only for other profiles usage as basis."""

    def __init__(self, ua=None):
        self._base_url: str = ""
        self._default_user_agent: str = "pyhafas"
        self._add_mic_mac: bool = False
        self._add_chksum: bool = False
        self._salt: str = ""
        self._req_body: dict = {}
        self._products: dict[str, list[int]] = {}
        self._default_products: list[str] = []
        self._locale: str = ""
        self._timezone: ZoneInfo = ZoneInfo("Europe/Berlin")

        if ua:
            self._user_agent = ua
        else:
            self._user_agent = self._default_user_agent

    def calculate_checksum(self, data: str) -> str:
        """Calculate the checksum of the request (required for most profiles).

        :param data: Complete body as string
        :return: Checksum for the request
        """
        return md5((data + self._salt).encode("utf-8")).hexdigest()

    def calculate_mic_mac(self, data: str) -> tuple[str, str]:
        """Calculate the mic-mac for the request (required for some profiles).

        :param data: Complete body as string
        :return: Mic and mac to be sent to HaFAS
        """
        mic = md5(data.encode("utf-8")).hexdigest()
        mac = self.calculate_checksum(mic)
        return mic, mac

    def url_formatter(self, data: str) -> str:
        """Format the URL for HaFAS (adds the checksum or mic-mac).

        :param data: Complete body as string
        :return: Request-URL (maybe with checksum or mic-mac)
        """
        url = self._base_url

        if self._add_chksum or self._add_mic_mac:
            parameters = []
            if self._add_chksum:
                parameters.append(f"checksum={self.calculate_checksum(data)}")
            if self._add_mic_mac:
                parameters.append("mic={}&mac={}".format(*self.calculate_mic_mac(data)))
            url += "?{}".format("&".join(parameters))

        return url

    def parse_lid_to_station(
        self,
        lid: str,
        name: str = "",
        latitude: float = 0,
        longitude: float = 0,
    ) -> Station:
        """Parse the LID given by HaFAS to a station object.

        :param lid: Location identifier (given by HaFAS)
        :param name: Station name (optional, if not given, LID is used)
        :param latitude: Latitude of the station (optional, if not given, LID is used)
        :param longitude: Longitude of the station (optional, if not given, LID is used)
        :return: Parsed LID as station object
        """
        parsedLid = self.parse_lid(lid)
        if latitude == 0 and longitude == 0 and parsedLid["X"] and parsedLid["Y"]:
            latitude = float(float(parsedLid["Y"]) / 1000000)
            longitude = float(float(parsedLid["X"]) / 1000000)

        return Station(
            id=parsedLid.get("L")
            or parsedLid["b"],  # key 'L' not always present; if not, 'b' should be
            lid=lid,
            name=name or parsedLid["O"],
            latitude=latitude,
            longitude=longitude,
        )

    def parse_location_request(self, data: HafasResponse) -> list[Station]:
        """Parse the HaFAS response for a location request.

        :param data: Formatted HaFAS response
        :return: List of Station objects
        """
        stations = []
        for stn in data.res["match"]["locL"]:
            try:
                latitude: float = stn["crd"]["y"] / 1000000
                longitude: float = stn["crd"]["x"] / 1000000
            except KeyError:
                latitude: float = 0
                longitude: float = 0
            stations.append(
                self.parse_lid_to_station(stn["lid"], stn["name"], latitude, longitude)
            )
        return stations

    def parse_leg(
        self,
        journey: dict,
        common: dict,
        departure: dict,
        arrival: dict,
        date: datetime.date,
        jny_type: str = "JNY",
        gis=None,
    ) -> Leg:
        """
        Parses Leg HaFAS returns into Leg object

        Different Types of HaFAS responses can be parsed into a leg object with the multiple variables

        :param journey: Journey object given back by HaFAS (Data of the Leg to parse)
        :param common:  Common object given back by HaFAS
        :param departure: Departure object given back by HaFAS
        :param arrival: Arrival object given back by HaFAS
        :param date: Parsed date of Journey (Departing date)
        :param jny_type: HaFAS Journey type
        :param gis: GIS object given back by HaFAS. Currently only used by "WALK" journey type.
        :return: Parsed Leg object
        """
        leg_origin = self.parse_lid_to_station(common["locL"][departure["locX"]]["lid"])
        leg_destination = self.parse_lid_to_station(
            common["locL"][arrival["locX"]]["lid"]
        )
        if jny_type == "WALK" or jny_type == "TRSF":
            return Leg(
                id=gis["ctx"],
                origin=leg_origin,
                destination=leg_destination,
                departure=self.parse_datetime(departure["dTimeS"], date),
                arrival=self.parse_datetime(arrival["aTimeS"], date),
                mode=Mode.WALKING,
                name=None,
                distance=gis.get("dist") if gis is not None else None,
            )
        else:
            leg_stopovers: list[Stopover] = []
            if "stopL" in journey:
                for stopover in journey["stopL"]:
                    leg_stopovers.append(
                        Stopover(
                            stop=self.parse_lid_to_station(
                                common["locL"][stopover["locX"]]["lid"]
                            ),
                            cancelled=bool(
                                stopover.get("dCncl", stopover.get("aCncl", False))
                            ),
                            departure=(
                                self.parse_datetime(stopover.get("dTimeS"), date)
                                if stopover.get("dTimeS") is not None
                                else None
                            ),
                            departure_delay=(
                                self.parse_datetime(stopover["dTimeR"], date)
                                - self.parse_datetime(stopover["dTimeS"], date)
                                if stopover.get("dTimeR") is not None
                                else None
                            ),
                            departure_platform=stopover.get(
                                "dPlatfR",
                                stopover.get(
                                    "dPlatfS",
                                    stopover.get(
                                        "dPltfR", stopover.get("dPltfS", {})
                                    ).get("txt"),
                                ),
                            ),
                            arrival=(
                                self.parse_datetime(stopover["aTimeS"], date)
                                if stopover.get("aTimeS") is not None
                                else None
                            ),
                            arrival_delay=(
                                self.parse_datetime(stopover["aTimeR"], date)
                                - self.parse_datetime(stopover["aTimeS"], date)
                                if stopover.get("aTimeR") is not None
                                else None
                            ),
                            arrival_platform=stopover.get(
                                "aPlatfR",
                                stopover.get(
                                    "aPlatfS",
                                    stopover.get(
                                        "aPltfR", stopover.get("aPltfS", {})
                                    ).get("txt"),
                                ),
                            ),
                            remarks=[
                                self.parse_remark(common["remL"][msg["remX"]], common)
                                for msg in stopover.get("msgL", [])
                                if msg.get("remX") is not None
                            ],
                        )
                    )

            return Leg(
                id=journey["jid"],
                name=common["prodL"][journey["prodX"]]["name"],
                origin=leg_origin,
                destination=leg_destination,
                cancelled=bool(arrival.get("aCncl", False)),
                departure=self.parse_datetime(departure["dTimeS"], date),
                departure_delay=(
                    self.parse_datetime(departure["dTimeR"], date)
                    - self.parse_datetime(departure["dTimeS"], date)
                    if departure.get("dTimeR") is not None
                    else None
                ),
                departure_platform=departure.get(
                    "dPlatfR",
                    departure.get(
                        "dPlatfS",
                        departure.get("dPltfR", departure.get("dPltfS", {})).get("txt"),
                    ),
                ),
                arrival=self.parse_datetime(arrival["aTimeS"], date),
                arrival_delay=(
                    self.parse_datetime(arrival["aTimeR"], date)
                    - self.parse_datetime(arrival["aTimeS"], date)
                    if arrival.get("aTimeR") is not None
                    else None
                ),
                arrival_platform=arrival.get(
                    "aPlatfR",
                    arrival.get(
                        "aPlatfS",
                        arrival.get("aPltfR", arrival.get("aPltfS", {})).get("txt"),
                    ),
                ),
                stopovers=leg_stopovers,
                remarks=[
                    self.parse_remark(common["remL"][msg["remX"]], common)
                    for msg in journey.get("msgL", {})
                    if msg.get("remX") is not None
                ],
            )

    def parse_legs(self, jny: dict, common: dict, date: datetime.date) -> list[Leg]:
        """
        Parses Legs (when multiple available)

        :param jny: Journeys object returned by HaFAS (contains secL list)
        :param common: Common object returned by HaFAS
        :param date: Parsed date of Journey (Departing date)
        :return: Parsed List of Leg objects
        """
        legs: list[Leg] = []

        for leg in jny["secL"]:
            legs.append(
                self.parse_leg(
                    leg.get("jny", None),
                    common,
                    leg["dep"],
                    leg["arr"],
                    date,
                    leg["type"],
                    leg.get("gis"),
                )
            )

        return legs

    async def async_request(self, body) -> HafasResponse:
        """Send async the request and does a basic parsing of the response and error handling.

        :param body: Reqeust body as dict (without the `requestBody` of the profile)
        :return: HafasRespone object or Exception when HaFAS response returns an error
        """
        data = {"svcReqL": [body]}
        data.update(self._req_body)
        data = json.dumps(data)

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.url_formatter(data),
                data=data,
                headers={
                    "User-Agent": self._user_agent,
                    "Content-Type": "application/json",
                },
                ssl=False,
            )

            return HafasResponse(await response.text(), BaseErrorCodesMapping)

        raise GeneralHafasError
