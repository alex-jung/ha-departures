import datetime
from typing import Dict, Optional, Union

from .data.leg import Leg
from .data.station import Station
from .data.station_board import StationBoardLeg
from .data.lat_lng import LatLng
from .data import StationBoardRequestType

from .profile.base import BaseProfile


class HafasClient:
    """The interface between the user's program and pyHaFAS internal code.

    :param profile: `Profile` to be used
    :param ua: (optional, not recommended to change) The user-agent which will be sent to HaFAS. By default "pyhafas", but is often overwritten by profile to emulate the app.
    :param debug: (optional) Whether debug mode should be enabled. Defaults to False.
    """

    def __init__(self, profile: BaseProfile, ua: str = "pyhafas", debug: bool = False):
        self.profile = profile
        self.useragent = ua
        self.debug = debug

    async def async_departures(
        self,
        station: Station | str,
        date: datetime.datetime,
        max_trips: int = -1,
        duration: int = -1,
        products: Dict[str, bool] = {},
        direction: Optional[Union[Station, str]] = None,
    ) -> list[StationBoardLeg]:
        """Return departing trips at the specified station.

        To get detailed information on the trip use the `trip` method with the id
        :param station: FPTF `Station` object or ID of station
        :param date: Date and Time when to search
        :param max_trips: (optional) Maximum number of trips to be returned. Default is "whatever HaFAS wants"
        :param duration: (optional) Minutes after `date` in which is search is made. Default is "whatever HaFAS wants"
        :param products: (optional) Dict of product name(s) and whether it should be enabled or not. Modifies the default products specified in the profile.
        :param direction: (optional) Direction (end) station of the vehicle. Default is any direction station is allowed
        :return: List of FPTF `StationBoardLeg` objects with departing trips
        """

        if not isinstance(station, Station):
            station = Station(id=station)

        if not isinstance(direction, Station) and direction is not None:
            direction = Station(id=direction)

        date = self.profile.transform_datetime_parameter_timezone(date)

        body = self.profile.format_station_board_request(
            station,
            StationBoardRequestType.DEPARTURE,
            date,
            max_trips,
            duration,
            products,
            direction,
        )
        res = await self.profile.async_request(body)

        return self.profile.parse_station_board_request(res, "d")

    async def async_arrivals(
        self,
        station: Station | str,
        date: datetime.datetime,
        max_trips: int = -1,
        duration: int = -1,
        products: Dict[str, bool] = {},
        direction: Optional[Union[Station, str]] = None,
    ) -> list[StationBoardLeg]:
        """Return arriving trips at the specified station.

        To get detailed information on the trip use the `trip` method with the id

        :param station: FPTF `Station` object or ID of station
        :param date: Date and Time when to search
        :param max_trips: (optional) Maximum number of trips to be returned. Default is "whatever HaFAS wants"
        :param duration: (optional) Minutes after `date` in which is search is made. Default is "whatever HaFAS wants"
        :param products: (optional) Dict of product name(s) and whether it should be enabled or not. Modifies the default products specified in the profile.
        :param direction: (optional) Direction (end) station of the vehicle. Default is any direction station is allowed
        :return: List of FPTF `StationBoardLeg` objects with arriving trips
        """
        if not isinstance(station, Station):
            station = Station(id=station)

        if not isinstance(direction, Station) and direction is not None:
            direction = Station(id=direction)

        date = self.profile.transform_datetime_parameter_timezone(date)

        body = self.profile.format_station_board_request(
            station,
            StationBoardRequestType.ARRIVAL,
            date,
            max_trips,
            duration,
            products,
            direction,
        )
        res = await self.profile.request(body)

        return self.profile.parse_station_board_request(res, "a")

    async def async_locations(self, term: str, rtype: str = "S") -> list[Station]:
        """Return stations (and addresses) that are searched with the provided term.

        The further forward the station is in the list, the higher the similarity to the search term.

        :param term: Search term
        :param rtype: Result types. One of ['S' for stations only, 'ALL' for addresses and stations]
        :return: List of FPTF `Station` objects
        """
        body = self.profile.format_location_request(term, rtype)
        res = await self.profile.async_request(body)

        return self.profile.parse_location_request(res)

    async def async_trip(self, id: str) -> Leg:
        """Return detailed information about a trip based on its ID.

        :param id: ID of the trip
        :return: Detailed trip information as FPTF `Leg` object
        """
        body = self.profile.format_trip_request(id)
        res = await self.profile.async_request(body)

        return self.profile.parse_trip_request(res)

    async def async_nearby(
        self,
        location: LatLng,
        max_walking_distance: int = -1,
        min_walking_distance: int = 0,
        products: dict[str, bool] = {},
        get_pois: bool = False,
        get_stops: bool = True,
        max_locations: int = -1,
    ) -> list[Station]:
        """Return stations close to a given latitude/longitude location.

        Distance to stations calculated by HaFAS. The list is ordered by closest to furthest station

        :param location: LatLng object containing latitude and longitude
        :param max_walking_distance: Maximum walking distance in meters
        :param min_walking_distance: Minimum walking distance in meters
        :param products: Dictionary of product names to products
        :param get_pois: If true, returns pois
        :param get_stops: If true, returns stops instead of locations
        :param max_locations: Maximum number of locations to return
        """
        body = self.profile.format_nearby_request(
            location,
            max_walking_distance,
            min_walking_distance,
            products,
            get_pois,
            get_stops,
            max_locations,
        )
        res = await self.profile.request(body)
        return self.profile.parse_nearby_response(res)
