from .base import BaseProfile
from ..data.journey import Journey
from ..data.hafas_response import HafasResponse


class NasaProfile(BaseProfile):
    def __init__(self, ua=None):
        super().__init__("nasa/6.4.3 (iPad; iOS 17.5.1; Scale/2.00)" if not ua else ua)

        self._base_url = "https://reiseauskunft.insa.de/bin/mgate.exe"
        self._req_body = {
            "client": {
                "id": "NASA",
                "type": "IPH",
                "name": "nasa",
                "v": "6040300",
            },
            "ver": "1.57",
            "lang": "de",
            "auth": {
                "type": "AID",
                "aid": "nasa-apps",
            },
        }

        self._products = {
            "long_distance_express": [1],  # ICE
            "long_distance": [2],  # IC/EC/CNL
            "regional": [8],  # RE/RB
            "suburban": [16],  # S
            "bus": [64, 128],  # BUS
            "tram": [32],  # T
            "tourism_train": [256],  # TT
        }

        self._default_products = [
            "long_distance_express",
            "long_distance",
            "regional",
            "suburban",
            "bus",
            "tram",
            "tourism_train",
        ]

    def format_journey_request(self, journey: Journey) -> dict:
        """
        Creates the HaFAS ( Adapted for NASA ) request for refreshing journey details

        :param journey: Id of the journey (ctxRecon)
        :return: Request for HaFAS ( NASA-Adapted )
        """
        return {"req": {"outReconL": [{"ctx": journey.id}]}, "meth": "Reconstruction"}

    def parse_journey_request(self, data: HafasResponse) -> Journey:
        """
        Parses the HaFAS response for a journey request ( Adapted for NASA )

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
