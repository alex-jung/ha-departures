from .base import BaseProfile
from ..data.journey import Journey
from ..data.hafas_response import HafasResponse


class KvbProfile(BaseProfile):
    def __init__(self, ua=None):
        super().__init__(ua)

        self._base_url = "https://auskunft.kvb.koeln/gate"
        self._locale = "de-DE"
        self._req_body = {
            "client": {
                "id": "HAFAS",
                "l": "vs_webapp",
                "v": "154",
                "type": "WEB",
                "name": "webapp",
            },
            "ext": "DB.R21.12.a",
            "ver": "1.58",
            "lang": "deu",
            "auth": {"type": "AID", "aid": "Rt6foY5zcTTRXMQs"},
        }
        self._products = {
            "s-bahn": [1],
            "stadtbahn": [2],
            "bus": [8],
            "fernverkehr": [32],
            "regionalverkehr": [64],
            "taxibus": [256],
        }
        self._default_products = [
            "s-bahn",
            "stadtbahn",
            "bus",
            "fernverkehr",
            "regionalverkehr",
            "taxibus",
        ]

    def format_journey_request(self, journey: Journey) -> dict:
        """
        Creates the HAFAS (KVB-deployment) request for refreshing journey details
        :param journey: Id of the journey (ctxRecon)
        :return: Request for HAFAS (KVB-deployment)
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
            journeys.append(
                Journey(
                    jny["recon"]["ctx"],
                    date=date,
                    duration=self.parse_timedelta(jny["dur"]),
                    legs=self.parse_legs(jny, data.common, date),
                )
            )
        return journeys
