import datetime

from ..exceptions import ProductNotAvailableError
from ..data.station import Station
from ..data.remark import Remark
from ..data.leg import Leg
from ..data.lat_lng import LatLng
from ..data import StationBoardRequestType
from ..data.station_board import StationBoardLeg
from ..data.hafas_response import HafasResponse


class MixinLocationRequest(object):
    def format_location_request(self, term: str, rtype: str = "S"):
        """
        Creates the HaFAS request body for a location search request.

        :param term: Search term
        :param type: Result types. One of ['S' for stations, 'ALL' for addresses and stations]
        :return: Request body for HaFAS
        """
        return {
            "req": {"input": {"field": "S", "loc": {"name": term, "type": rtype}}},
            "meth": "LocMatch",
        }


class MixinParseLid(object):
    def parse_lid(self, lid: str) -> dict:
        """
        Converts the LID given by HaFAS

        Splits the LID (e.g. A=1@O=Siegburg/Bonn) in multiple elements (e.g. A=1 and O=Siegburg/Bonn).
        These are converted into a dict where the part before the equal sign is the key and the part after the value.

        :param lid: Location identifier (given by HaFAS)
        :return: Dict of the elements of the dict
        """
        parsedLid = {}
        for lidElementGroup in lid.split("@"):
            if lidElementGroup:
                parsedLid[lidElementGroup.split("=")[0]] = lidElementGroup.split("=")[1]
        return parsedLid


class MixinBoardStation(object):
    def format_station_board_request(
        self,
        station: Station,
        request_type: StationBoardRequestType,
        date: datetime.datetime,
        max_trips: int,
        duration: int,
        products: dict[str, bool],
        direction: Station | None,
    ) -> dict:
        """
        Creates the HaFAS request for a station board request (departure/arrival)

        :param station: Station to get departures/arrivals for
        :param request_type: ARRIVAL or DEPARTURE
        :param date: Date and time to get departures/arrival for
        :param max_trips: Maximum number of trips that can be returned
        :param products: Allowed products (e.g. ICE,IC)
        :param duration: Time in which trips are searched
        :param direction: Direction (end) station of the train. If none, filter will not be applied
        :return: Request body for HaFAS
        """
        return {
            "req": {
                "type": request_type.value,
                "stbLoc": {"lid": "A=1@L={}@".format(station.id)},
                "dirLoc": (
                    {"lid": "A=1@L={}@".format(direction.id)}
                    if direction is not None
                    else None
                ),
                "maxJny": max_trips,
                "date": date.strftime("%Y%m%d"),
                "time": date.strftime("%H%M%S"),
                "dur": duration,
                "jnyFltrL": [self.format_products_filter(products)],
            },
            "meth": "StationBoard",
        }

    def parse_station_board_request(
        self, data: HafasResponse, departure_arrival_prefix: str
    ) -> list[StationBoardLeg]:
        """
        Parses the HaFAS data for a station board request

        :param data: Formatted HaFAS response
        :param departure_arrival_prefix: Prefix for specifying whether its for arrival or departure (either a for arrival or d for departure)
        :return: List of StationBoardLeg objects
        """
        legs = []
        if not data.res.get("jnyL", False):
            return legs
        else:
            for raw_leg in data.res["jnyL"]:
                date = self.parse_date(raw_leg["date"])

                try:
                    platform = (
                        raw_leg["stbStop"][departure_arrival_prefix + "PltfR"]["txt"]
                        if raw_leg["stbStop"].get(departure_arrival_prefix + "PltfR")
                        is not None
                        else raw_leg["stbStop"][departure_arrival_prefix + "PltfS"][
                            "txt"
                        ]
                    )
                except KeyError:
                    platform = raw_leg["stbStop"].get(
                        departure_arrival_prefix + "PlatfR",
                        raw_leg["stbStop"].get(
                            departure_arrival_prefix + "PlatfS", None
                        ),
                    )

                legs.append(
                    StationBoardLeg(
                        id=raw_leg["jid"],
                        name=data.common["prodL"][raw_leg["prodX"]]["name"],
                        direction=raw_leg.get("dirTxt"),
                        date_time=self.parse_datetime(
                            raw_leg["stbStop"][departure_arrival_prefix + "TimeS"], date
                        ),
                        station=self.parse_lid_to_station(
                            data.common["locL"][raw_leg["stbStop"]["locX"]]["lid"]
                        ),
                        platform=platform,
                        delay=(
                            self.parse_datetime(
                                raw_leg["stbStop"][departure_arrival_prefix + "TimeR"],
                                date,
                            )
                            - self.parse_datetime(
                                raw_leg["stbStop"][departure_arrival_prefix + "TimeS"],
                                date,
                            )
                            if raw_leg["stbStop"].get(
                                departure_arrival_prefix + "TimeR"
                            )
                            is not None
                            else None
                        ),
                        cancelled=bool(
                            raw_leg["stbStop"].get(
                                departure_arrival_prefix + "Cncl", False
                            )
                        ),
                    )
                )
            return legs

    def format_products_filter(self, requested_products: dict) -> dict:
        """
        Create the products filter given to HaFAS

        :param requested_products: Mapping of Products to whether it's enabled or disabled
        :return: value for HaFAS "jnyFltrL" attribute
        """
        products = self._default_products
        for requested_product in requested_products:
            if requested_products[requested_product]:
                try:
                    products.index(requested_product)
                except ValueError:
                    products.append(requested_product)

            elif not requested_products[requested_product]:
                try:
                    products.pop(products.index(requested_product))
                except ValueError:
                    pass
        bitmask_sum = 0
        for product in products:
            try:
                for product_bitmask in self._products[product]:
                    bitmask_sum += product_bitmask
            except KeyError:
                raise ProductNotAvailableError(
                    'The product "{}" is not available in chosen profile.'.format(
                        product
                    )
                )
        return {"type": "PROD", "mode": "INC", "value": str(bitmask_sum)}


class MixinDateTime(object):
    def parse_datetime(
        self, time_string: str, date: datetime.date
    ) -> datetime.datetime:
        """
        Parses the time format HaFAS returns and combines it with a date

        :param time_string: Time string sent by HaFAS (multiple formats are supported. One example: 234000)
        :param date: Start day of the leg/journey
        :return: Parsed date and time as datetime object
        """
        try:
            hour = int(time_string[-6:-4])
            minute = int(time_string[-4:-2])
            second = int(time_string[-2:])
        except ValueError:
            raise ValueError(f'Time string "{time_string}" has wrong format')

        dateOffset = int(time_string[:2]) if len(time_string) > 6 else 0

        return datetime.datetime(
            date.year, date.month, date.day, hour, minute, second, tzinfo=self._timezone
        ) + datetime.timedelta(days=dateOffset)

    def parse_timedelta(self, time_string: str) -> datetime.timedelta:
        """
        Parses the time HaFAS returns as timedelta object

        Example use case is when HaFAS returns a duration of a leg
        :param time_string: Time string sent by HaFAS (example for format is: 033200)
        :return: Parsed time as timedelta object
        """
        try:
            hours = int(time_string[:2])
            minutes = int(time_string[2:-2])
            seconds = int(time_string[-2:])
        except ValueError:
            raise ValueError(f'Time string "{time_string}" has wrong format')

        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

    def parse_date(self, date_string: str) -> datetime.date:
        """
        Parses the date HaFAS returns

        :param date_string: Date sent by HaFAS
        :return: Parsed date object
        """
        dt = datetime.datetime.strptime(date_string, "%Y%m%d")
        return dt.date()

    def transform_datetime_parameter_timezone(
        self, date_time: datetime.datetime
    ) -> datetime.datetime:
        """
        Transfers datetime parameters incoming by the user to the profile timezone

        :param date_time: datetime parameter incoming by user. Can be timezone aware or unaware
        :return: Timezone aware datetime object in profile timezone
        """
        if (
            date_time.tzinfo is not None
            and date_time.tzinfo.utcoffset(date_time) is not None
        ):
            return date_time.astimezone(self._timezone)
        else:
            return date_time.replace(tzinfo=self._timezone)


class MixinRemark(object):
    def parse_remark(self, remark: dict, common: dict) -> Remark:
        """
        Parses Remark HaFAS returns into Remark object

        :param remark: Remark object given back by HaFAS
        :param common: Common object given back by HaFAS
        :return: Parsed Remark object
        """

        rem = Remark(
            remark_type=remark.get("type"),
            code=remark.get("code") if remark.get("code") != "" else None,
            subject=remark.get("txtS") if remark.get("txtS") != "" else None,
            text=remark.get("txtN") if remark.get("txtN") != "" else None,
            priority=remark.get("prio"),
            trip_id=remark.get("jid"),
        )
        return rem


class MixinTrip(object):
    def format_trip_request(self, trip_id: str) -> dict:
        """
        Creates the HaFAS request for a trip request

        :param trip_id: Id of the trip/leg
        :return: Request body for HaFAS
        """
        return {"req": {"jid": trip_id}, "meth": "JourneyDetails"}

    def parse_trip_request(self, data: HafasResponse) -> Leg:
        """
        Parses the HaFAS data for a trip request

        :param data: Formatted HaFAS response
        :return: Leg objects
        """
        return self.parse_leg(
            data.res["journey"],
            data.common,
            data.res["journey"]["stopL"][0],
            data.res["journey"]["stopL"][-1],
            self.parse_date(data.res["journey"]["date"]),
        )


class MixinNearby(object):
    def format_nearby_request(
        self,
        location: LatLng,
        max_walking_distance: int,
        min_walking_distance: int,
        products: dict[str, bool],
        get_pois: bool,
        get_stops: bool,
        max_locations: int,
    ) -> dict:
        """
        Creates the HaFAS request body for a nearby request.

        :param location: LatLng object containing latitude and longitude
        :param max_walking_distance: Maximum walking distance in meters
        :param min_walking_distance: Minimum walking distance in meters
        :param products: Dictionary of product names to products
        :param get_pois: If true, returns pois
        :param get_stops: If true, returns stops instead of locations
        :param max_locations: Maximum number of locations to return
        :return: Request body for HaFAS
        """
        return {
            "cfg": {"polyEnc": "GPA"},
            "meth": "LocGeoPos",
            "req": {
                "ring": {
                    "cCrd": {
                        "x": location.longitude_e6,
                        "y": location.latitude_e6,
                    },
                    "maxDist": max_walking_distance,
                    "minDist": min_walking_distance,
                },
                "locFltrL": [self.format_products_filter(products)],
                "getPOIs": get_pois,
                "getStops": get_stops,
                "maxLoc": max_locations,
            },
        }

    def parse_nearby_response(self, data: HafasResponse) -> list[Station]:
        stations = []

        for station in data.res["locL"]:
            try:
                latitude: float = station["crd"]["y"] / 1e6
                longitude: float = station["crd"]["x"] / 1e6
            except KeyError:
                latitude: float = 0
                longitude: float = 0
            stations.append(
                self.parse_lid_to_station(
                    station["lid"], station["name"], latitude, longitude
                )
            )

        return stations
