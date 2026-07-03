from typing import Final

from nautilus_trader.model.identifiers import ClientId, Venue


MISX: Final[str] = "MISX"

MISX_VENUE: Final[Venue] = Venue(MISX)
MISX_CLIENT_ID: Final[ClientId] = ClientId(MISX)
