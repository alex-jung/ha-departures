from .base import BaseProfile
from ..data.journey import Journey
from ..data.hafas_response import HafasResponse


class NvvProfile(BaseProfile):
    def __init__(self, ua=None):
        super().__init__(
            "NVV Mobil/5.3.1 (iPhone; IOS 13.1.2; Scale/2.00)" if not ua else ua
        )

        self._base_url = "https://auskunft.nvv.de/bin/mgate.exe"
        self._locale = "de-DE"
        self._req_body = {
            "client": {"id": "NVV", "type": "WEB", "name": "webapp"},
            "ver": "1.39",
            "lang": "deu",
            "auth": {"type": "AID", "aid": "R7aKWQLVBRSoVRtY"},
        }
        self._products = {
            "long_distance_express": [1],  # ICE
            "long_distance": [2],  # IC/EC
            "regional_express": [4],  # RE/RB
            "tram": [32],  # Tram
            "bus": [64, 128],  # Bus
            "anruf_sammel_taxi": [512],  # Group Taxi
            "regio_tram": [1024],  # Tram / regional express hybrid
        }
        self._default_products = [
            "long_distance_express",
            "long_distance",
            "regional_express",
            "bus",
            "tram",
            "anruf_sammel_taxi",
            "regio_tram",
        ]

    def format_journey_request(self, journey: Journey) -> dict:
        """
        Creates the HAFAS (NVV-deployment) request for refreshing journey details

        :param journey: Id of the journey (ctxRecon)
        :return: Request for HAFAS (NVV-deployment)
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

    def parse_journeys_request(self, data: HafasResponse):
        for jny in data.res["outConL"]:
            jny["ctxRecon"] = jny["recon"]["ctx"]

        return super().parse_journeys_request(data)
