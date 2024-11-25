import json

from ..error_codes import ErrorCodesMappingInterface


class HafasResponse:
    """
    The class HafasResponse handles the general parsing and error-checking of a raw HaFAS response

    :ivar raw_hafas_response: The raw response of HaFAS
    :vartype raw_hafas_response: requests.Response
    :ivar data: json parsed raw response of HaFAS
    :vartype data: dict
    """

    def __init__(self, raw_hafas_response, mapping: ErrorCodesMappingInterface):
        """
        Constructor of class HafasResponse

        :param raw_hafas_response: The raw response of HaFAS
        :param mapping: Error Mapping Enum (key is the HaFAS error code, value the error class)
        """
        data = json.loads(raw_hafas_response)
        self.raw_hafas_response = raw_hafas_response
        self.data = data
        self.check_for_errors(mapping)

    def check_for_errors(self, mapping: ErrorCodesMappingInterface):
        """
        Checks if HaFAS response has error messages and handles them

        :param mapping: Error Mapping Enum (key is the HaFAS error code, value the error class)
        """
        error_not_found = False
        if self.data.get("err", "OK") != "OK":
            try:
                raise mapping[self.data["err"]].value(self.data.get("errTxt", ""))
            except KeyError:
                error_not_found = True
        if error_not_found:
            raise mapping["default"].value(self.data.get("errTxt", ""))

        if not self.data.get("svcResL", False):
            raise mapping["default"].value("HaFAS response cannot be parsed")

        if self.data["svcResL"][0].get("err", "OK") != "OK":
            try:
                raise mapping[self.data["svcResL"][0]["err"]].value(
                    self.data["svcResL"][0].get("errTxt", "")
                )
            except KeyError:
                error_not_found = True
        if error_not_found:
            raise mapping["default"].value(self.data["svcResL"][0].get("errTxt", ""))

    @property
    def common(self):
        """
        Returns the "common" data out of HaFAS data

        :return: dict with "common" data
        """
        return self.data["svcResL"][0]["res"]["common"]

    @property
    def res(self):
        """
        Returns the "res" data out of HaFAS data

        :return: dict with "res" data
        """
        return self.data["svcResL"][0]["res"]
