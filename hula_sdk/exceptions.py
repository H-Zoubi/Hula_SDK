class HulaError(Exception):
    """Base class for hula_sdk errors."""


class HulaConnectionError(HulaError):
    """Raised when connecting to the drone fails."""
