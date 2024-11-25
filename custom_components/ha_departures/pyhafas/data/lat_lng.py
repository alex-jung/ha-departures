class LatLng:
    latitude: float
    longitude: float

    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    @property
    def latitude_e6(self) -> int:
        return round(self.latitude * 1e6)

    @property
    def longitude_e6(self) -> int:
        return round(self.longitude * 1e6)
