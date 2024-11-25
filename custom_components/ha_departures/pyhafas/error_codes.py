from enum import Enum


class ErrorCodesMappingInterface(Enum):
    """
    Mapping of the HaFAS error code to the exception class

    `default` defines the error when the error code cannot be found in the mapping
    """

    default: Exception
