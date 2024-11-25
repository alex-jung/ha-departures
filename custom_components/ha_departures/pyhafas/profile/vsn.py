from .base import BaseProfile
from ..data.journey import Journey


class VsnProfile(BaseProfile):
    """
    Profile for the HaFAS of "Verkehrsverbund Süd-Niedersachsen" (VSN) - local transportation provider
    """

    def __init__(self, ua=None):
        super().__init__("vsn/5.3.1 (iPad; iOS 13.3; Scale/2.00)" if not ua else ua)

        self._base_url = "https://fahrplaner.vsninfo.de/hafas/mgate.exe"
        self._salt = "SP31mBufSyCLmNxp"
        self._add_mic_mac = True
        self._req_body = {
            "client": {
                "id": "VSN",
                "v": "5030100",
                "type": "IPA",
                "name": "vsn",
                "os": "iOS 13.3",
            },
            "ver": "1.24",
            "lang": "de",
            "auth": {"type": "AID", "aid": "Mpf5UPC0DmzV8jkg"},
        }
        self._products = {
            "long_distance_express": [1],  # ICE
            "long_distance": [2],  # IC/EC/CNL
            "regional_express": [4],  # RE/IR
            "regional": [8],  # NV
            "suburban": [16],  # S
            "bus": [32],  # BUS
            "ferry": [64],  # F
            "subway": [128],  # U
            "tram": [256],  # T
            "anruf_sammel_taxi": [512],  # Group Taxi
        }
        self._default_products = [
            "long_distance_express",
            "long_distance",
            "regional_express",
            "regional",
            "suburban",
            "bus",
            "ferry",
            "subway",
            "tram",
            "anruf_sammel_taxi",
        ]

    def format_journey_request(self, journey: Journey) -> dict:
        """
        Creates the HaFAS (VSN-deployment) request for refreshing journey details

        :param journey: Id of the journey (ctxRecon)
        :return: Request for HaFAS (VSN-deployment)
        """
        return {"req": {"outReconL": [{"ctx": journey.id}]}, "meth": "Reconstruction"}
