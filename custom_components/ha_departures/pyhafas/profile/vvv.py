from zoneinfo import ZoneInfo
from .base import BaseProfile
from ..data.journey import Journey
from ..data.hafas_response import HafasResponse


class VvvProfile(BaseProfile):
    """
    Profile of the HaFAS of Verkehrsverbund Vorarlberg (VVV)
    https://de.wikipedia.org/wiki/Verkehrsverbund_Vorarlberg
    """

    def __init__(self, ua=None):
        super().__init__(ua)

        self._base_url = "https://fahrplan.vmobil.at/bin/mgate.exe"
        self._salt = "6633673735743766726667323938336A"
        self._timezone: ZoneInfo = ZoneInfo("Europe/Vienna")
        self._add_mic_mac = True
        self._req_body = {
            "client": {
                "id": "VAO",
                "l": "vs_vvv",
                "name": "webapp",
                "type": "WEB",
                "v": "20230901",
            },
            "ext": "VAO.20",
            "ver": "1.59",
            "lang": "de",
            "auth": {"type": "AID", "aid": "wf7mcf9bv3nv8g5f"},
        }
        self._products = {
            "train-and-s-bahn": [1, 2],  # Bahn & S-Bahn
            "u-bahn": [4],  # U-Bahn
            "tram": [16],  # Straßenbahn
            "long-distance-bus": [32],  # Fernbus
            "regional-bus": [64],  # Regionalbus
            "city-bus": [128],  # Stadtbus
            "aerial-lift": [256],  # Seil-/Zahnradbahn
            "ferry": [512],  # Schiff
            "on-call": [1024],  # Anrufsammeltaxi
            "other-bus": [2048],  # sonstige Busse
        }
        self._default_products = [
            "train-and-s-bahn",
            "u-bahn",
            "tram",
            "long-distance-bus",
            "regional-bus",
            "city-bus",
            "aerial-lift",
            "ferry",
            "on-call",
            "other-bus",
        ]

    def format_journey_request(self, journey: Journey) -> dict:
        """
        Creates the HAFAS (VVV-deployment) request for refreshing journey details

        :param journey: Id of the journey (ctxRecon)
        :return: Request for HAFAS (VVV-deployment)
        """
        return {"req": {"outReconL": [{"ctx": journey.id}]}, "meth": "Reconstruction"}

    def parse_journey_request(self, data: HafasResponse) -> Journey:
        """
        Parses the HaFAS response for a journey request
        :param data: Formatted HaFAS response
        :return: List of Journey objects
        """
        date = self.parse_date(data.res["outConL"][0]["date"])
        return Journey(
            data.res["outConL"][0]["recon"]["ctx"],
            date=date,
            duration=self.parse_timedelta(data.res["outConL"][0]["dur"]),
            legs=self.parse_legs(data.res["outConL"][0], data.common, date),
        )

    def parse_journeys_request(self, data: HafasResponse) -> list[Journey]:
        journeys = []

        for jny in data.res["outConL"]:
            date = self.parse_date(jny["date"])

            # skip all 'TRSF' type journeys (propably better handling should be implemented)
            jny["secL"] = [s for s in jny["secL"] if s["type"] != "TRSF"]

            journeys.append(
                Journey(
                    jny["recon"]["ctx"],
                    date=date,
                    duration=self.parse_timedelta(jny["dur"]),
                    legs=self.parse_legs(jny, data.common, date),
                )
            )
        return journeys
