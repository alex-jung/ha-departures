from .base import BaseProfile


class DBProfile(BaseProfile):
    def __init__(self, ua=None):
        super().__init__(
            "DB Navigator/19.10.04 (iPhone; iOS 13.1.2; Scale/2.00)" if not ua else ua
        )

        self._base_url = "https://reiseauskunft.bahn.de/bin/mgate.exe"
        self._salt = "bdI8UVj40K5fvxwf"
        self._add_chksum = True

        self._locale = "de-DE"

        self._req_body = {
            "client": {
                "id": "DB",
                "v": "20100000",
                "type": "IPH",
                "name": "DB Navigator",
            },
            "ext": "DB.R21.12.a",
            "ver": "1.15",
            "auth": {"type": "AID", "aid": "n91dB8Z77MLdoR0K"},
        }

        self._products = {
            "long_distance_express": [1],  # ICE
            "long_distance": [2],  # IC/EC
            "regional_express": [4],  # RE/IR
            "regional": [8],  # RB
            "suburban": [16],  # S
            "bus": [32],  # BUS
            "ferry": [64],  # F
            "subway": [128],  # U
            "tram": [256],  # T
            "taxi": [512],  # Group Taxi
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
            "taxi",
        ]
